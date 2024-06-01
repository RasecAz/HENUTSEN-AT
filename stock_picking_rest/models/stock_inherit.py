import json
import requests

from odoo import SUPERUSER_ID, _, fields, models, api
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from odoo.tools.float_utils import float_is_zero
from markupsafe import Markup
from odoo.exceptions import ValidationError

class StockInherit(models.Model):
    _inherit = 'stock.picking'

# ------------------------------------------------------------------------------------------------
# CAMPOS
# ------------------------------------------------------------------------------------------------

    rfid_response = fields.Char(
        string='Resultado envío',
        readonly=True
    )
    response = fields.Char(
        string='Respuesta envío',
        readonly=True
    )
    bearer = fields.Char(
        string='Resultado Bearer Token',
        readonly=True
    )
    json_generado = fields.Text(
        string='Json generado',
        readonly=True
    )
    api_key = fields.Text(
        string='Api Key',
        readonly=True
    )
    send_button_visible = fields.Boolean(
        default=False,
        compute='_compute_send_button_visible',
    )
    cg1_button_visible = fields.Boolean(
        default=False,
        compute='_compute_send_button_visible',
    )
    packing_button_visible = fields.Boolean(
        default=False,
        compute='_compute_send_button_visible',
    )
    endpoint = fields.Text(
        string='Endpoint',
        readonly=True
    )
    total_order = fields.Float(
        string='Total productos',
        compute='_compute_total_order',
        store=True
    )
    

# ------------------------------------------------------------------------------------------------
# METODOS
# ------------------------------------------------------------------------------------------------

    # INFO: Metodo que setea la estructura del json dependiendo del tipo de movimiento
    def _create_debug_json(self):

        #data_json corresponde a la estructura principal del json, mientras que product_list es la lista de los productos"""
        data_json_picking = {}
        product_list = []
        operation_name = self.name
        operacion_origen = self.location_id.company_id.name
        operacion_destino = self.partner_id.name

        #Se recorre cada producto de la operación
        for product in self.move_ids:
            referencia_producto = product.product_id.default_code
            name_producto = product.product_id.name.rstrip()
            cantidad_producto = product.quantity
            variant_list = []

            #Si existen variantes, se recorren y se obtienen los valores de cada una
            if product.product_id.product_tmpl_id.attribute_line_ids:
                for variant in product.product_id.product_tmpl_id.attribute_line_ids:
                    tipo_variante = variant.attribute_id.name
                    atributo_variante = ""
                    refe = product.product_id.display_name
                    attribute_values_string = refe.split("(")[1].split(")")[0]
                    attribute_values = attribute_values_string.split(", ")
                    #Se recorren los valores de las variantes y se comparan con los valores de la lista de variantes
                    for lista in attribute_values:
                        for value in variant.value_ids:
                            if value.name in lista:
                                atributo_variante = value.name
                    variant_list.append({
                        "name": tipo_variante,
                        "value": atributo_variante
                    })
                product_list.append({
                "observation": referencia_producto,
                "quantity": cantidad_producto,
                "productSku": name_producto,
                "variantList": variant_list
            })
            #Si no existen variantes, no se incluye sección de variantList al json
            else:
                product_list.append({
                "observation": referencia_producto,
                "quantity": cantidad_producto,
                "productSku": name_producto
            })
                
        data_json_picking= json.dumps({
            "consecutive": operation_name,
            "sourceLocation": operacion_origen,
            "targetLocation": operacion_destino,
            "productList": product_list
            })
        return data_json_picking

    # INFO: Método que genera el json a CG1 al validar la orden de salida
    def _cg1_json_generator(self):
        cg1_detalle = []
        fecha_operacion = str(self.date.strftime("%Y-%m-%d"))
        es_sucursal = False
        lista_precio = self.sale_id.pricelist_id.name
        items_lista = self.env['product.pricelist'].search([('name', '=', lista_precio)])
        nit_vendedor = self.location_id.company_id.vat
        id_sucursal = self.partner_id.company_registry

        for sucursal in self.location_id.company_id.child_ids:
                sucursales = sucursal.name
                if sucursales == self.partner_id.name:
                    es_sucursal = True
        if es_sucursal:
            nit_cliente = "900538591"
        else:
            nit_cliente = self.partner_id.vat

        for producto in self.move_ids:
            referencia_producto = producto.product_id.default_code
            cantidad_producto = producto.quantity
            precio_producto = None
            for item in items_lista.item_ids:
                if item.product_tmpl_id.name == producto.product_id.name:
                    precio_producto = item.fixed_price
            if not precio_producto:
                raise ValidationError("No se encontró el precio del producto en la lista de precios, verifique la configuración de la lista.")
            cg1_detalle.append({
                "CMPETRM_IND_ITEMS": "I",
                "CMPETRM_ITEMS": referencia_producto,
                "CMPETRM_UNIMED_CAP": "UND",
                "CMPETRM_CANT_PED_1": str(cantidad_producto),
                "CMPETRM_IND_UNIDAD": "1",
                "CMPETRM_LIPRE": lista_precio,
                "CMPETRM_PRECIO_UNI": str(precio_producto),
                "CMPETRM_FECHA": fecha_operacion,
                "CMPETRM_VENDEDOR": nit_vendedor,
                "CMPETRM_MOTIVO": "01"
            })    

        cg1_json = json.dumps({
            "CMPETRM_OC_NRO": self.name.replace("Arist/OUT/", "Odoo-"),
            "CMPETRM_IND_CLI": 2,
            "CMPETRM_TERC": nit_cliente,
            "CMPETRM_SUC": id_sucursal,
            "CMPETRM_FECHA": fecha_operacion,
            "CMPETRM_CO": "001",
            "CMPETRM_LOCAL": "03",
            "Detalle": cg1_detalle
        }, indent=4)

        return cg1_json

    # INFO: Método que genera el Bearer Token con la API Key suministrada
    def _generate_bearer_token(self):
        api_key = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).api_key
        email = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).email_henutsen
        bearer_url = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).url_bearer
        self.api_key = api_key
        token_url = f'{bearer_url}/{email}?apiKey={api_key}'

        # Envío de la solicitud y obtención de la respuesta
        response = requests.post(token_url)

        # Verificación del código de estado
        if response.status_code == 200:
            # La solicitud fue exitosa, procesa la respuesta JSON
            response_json = response.json()
            bearer_token = response_json["accessToken"]  # accesToken contiene el token
            self.bearer = bearer_token
            return bearer_token
        else:
            # La solicitud falló, maneja el error
            self.bearer = "Error" + str(response.status_code)
            raise ValidationError("Error " + str(response.status_code) + "Respuesta: " + response.text)

    # INFO: Método que envía la información a la URL expuesta de Henutsen 
    def _picking_service(self):
        data_json = self._create_debug_json()
        self.json_generado = data_json
        if not self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).api_key or not self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).email_henutsen or not self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).url_picking:
            raise ValidationError('Faltan datos para enviar la información, completelos en la sección de Configuración Henutsen, si no tiene acceso, solicitele a un administrador que actualice esta información')
        bearer_token = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).bearer_token
        if not bearer_token:
            bearer_token = self._generate_bearer_token()
        else:
            bearer_token = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).bearer_token
        service_url = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).url_picking
        self.endpoint = service_url
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + bearer_token
            }

        # Preparación de la solicitud POST con el token
        response = requests.request("POST",service_url, headers=headers, data=data_json)

        if response.status_code == 200:
            # La solicitud fue exitosa, procesa la respuesta (json_response)
            body_mensaje = Markup(f'<h2>¡Generación de códigos RFID en Henutsen exitosa!</h2> <p>Se ha enviado la información a Henutsen, inicie el proceso de etiquetado.</p>')
            self.message_post(body=body_mensaje, message_type='notification')
            self.rfid_response = "SUCCESS"
            self.response = response.text
        else:
            # La solicitud falló, maneja el error
            bearer_token = self._generate_bearer_token()
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + bearer_token
            }
            response = requests.request("POST",service_url, headers=headers, data=data_json)

            if response.status_code == 200:
                self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).sudo().write({'bearer_token': bearer_token})
                body_mensaje = Markup(f'<h2>¡Generación de códigos RFID en Henutsen exitosa!</h2> <p>Se ha enviado la información a Henutsen, inicie el proceso de etiquetado.</p>')
                self.message_post(body=body_mensaje, message_type='notification')
                self.rfid_response = "SUCCESS"
                self.response = response.text
            else:
                self.rfid_response = "FAILED. Error " + str(response.status_code)
                self.response = response.text
        
    # INFO: Método que ejecuta el controlador de la API REST para descargar el json de CG1
    def generate_download_cg1(self):
        url = f'/stock_picking_rest/download_txt/{self.id}'
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "download",
        }
    
    # INFO: Método que envía la información de picking a la URL expuesta de Henutsen
    def send_picking_to_henutsen(self):
        self._picking_service()
    
    # INFO: Método que envía la información de packing a la URL expuesta de Henutsen
    def send_packing_to_henutsen(self):
        operation_name = self.name
        operacion_origen = self.location_id.company_id.name
        operacion_destino = self.partner_id.name
        box_order = []
        data_json_packing = {}
        #self._packing_service()
        for box_list in self.move_line_ids_without_package.mapped('result_package_id'):
            box_id = box_list.name
            product_list = []
            for product in box_list.quant_ids:
                referencia_producto = product.product_id.default_code
                name_producto = product.product_id.name.rstrip()
                cantidad_producto = product.quantity
                variant_list = []
                producto_lista = product.product_id.default_code
                if product.product_id.product_tmpl_id.attribute_line_ids:
                    for variant in product.product_id.product_tmpl_id.attribute_line_ids:
                        tipo_variante = variant.attribute_id.name
                        atributo_variante = ""
                        refe = product.product_id.display_name
                        attribute_values_string = refe.split("(")[1].split(")")[0]
                        attribute_values = attribute_values_string.split(", ")
                        #Se recorren los valores de las variantes y se comparan con los valores de la lista de variantes
                        for lista in attribute_values:
                            for value in variant.value_ids:
                                if value.name in lista:
                                    atributo_variante = value.name
                        variant_list.append({
                            "name": tipo_variante,
                            "value": atributo_variante
                        })
                    product_list.append({
                    "quantity": cantidad_producto,
                    "productSku": name_producto,
                    "variantList": variant_list
                    })
                #Si no existen variantes, no se incluye sección de variantList al json
                else:
                    product_list.append({
                    "quantity": cantidad_producto,
                    "productSku": name_producto
                })
            box_order.append({
                "id": box_id,
                "productList": product_list
            })
        
        data_json_packing = json.dumps({
            "consecutive": operation_name,
            "sourceLocation": operacion_origen,
            "targetLocation": operacion_destino,
            "boxOrders": box_order
        })
        # IMPORTANTE: Todo debe estar configurado en la vista de configuración de Henutsen para que el web service funcione correctamente. El programa es capaz de reconfigurarse si el token expira.
        self.json_generado = data_json_packing
        if not self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).api_key or not self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).email_henutsen or not self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).url_packing:
            raise ValidationError('Faltan datos para enviar la información, completelos en la sección de Configuración Henutsen, si no tiene acceso, solicitele a un administrador que actualice esta información')
        bearer_token = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).bearer_token
        if not bearer_token:
            bearer_token = self._generate_bearer_token()
        else:
            bearer_token = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).bearer_token
        service_url = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).url_packing
        self.endpoint = service_url
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + bearer_token
            }

        # Preparación de la solicitud POST con el token
        response = requests.request("POST",service_url, headers=headers, data=data_json_packing)

        if response.status_code == 200:
            # La solicitud fue exitosa, procesa la respuesta (json_response)
            body_mensaje = Markup(f'<h2>¡Operación exitosa!</h2> <p>Se ha enviado la información a Henutsen.</p>')
            self.message_post(body=body_mensaje, message_type='notification')
            self.rfid_response = "SUCCESS"
            self.response = response.text
        else:
            # La solicitud falló, maneja el error
            bearer_token = self._generate_bearer_token()
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + bearer_token
            }
            # Preparación de la solicitud POST con el token
            response = requests.request("POST",service_url, headers=headers, data=data_json_packing)
            if response.status_code == 200:
                self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).sudo().write({'bearer_token': bearer_token})
                body_mensaje = Markup(f'<h2>¡Operación exitosa!</h2> <p>Se ha enviado la información a Henutsen.</p>')
                self.message_post(body=body_mensaje, message_type='notification')
                self.rfid_response = "SUCCESS"
                self.response = response.text
            else:
                self.rfid_response = "FAILED. Error " + str(response.status_code)
                self.response = response.text       
        
    # INFO: Método que define si los botónes de envío a Henutsen y CG1 son visibles o no
    #  Picking es visible si:
    #       - El tipo de operación es PICK.
    #       - El estado de la operación es 'done' o 'Validada'.
    #       - El destino de la operación es una sucursal.
    #       - La respuesta de RFID no es 'SUCCESS' (Para que el botón desaparezca si la respuesta es exitosa).
    #  Packing es visible si:
    #       - El tipo de operación es PACK.
    #       - El estado de la operación es 'done' o 'Validada'.
    #       - El destino de la operación es una sucursal.
    #       - La respuesta de RFID no es 'SUCCESS' (Para que el botón desaparezca si la respuesta es exitosa).
    #  CG1 es visible si:
    #       - El tipo de operación es OUT.
    #       - El estado de la operación es 'done' o 'Validada'.
    @api.depends('name', 'state', 'partner_id', 'rfid_response')
    def _compute_send_button_visible(self):
        for record in self:
            es_sucursal = False
            es_picking = False
            es_packing = False
            es_salida = False
            proceso_completado = False
            for sucursal in record.location_dest_id.company_id.child_ids:
                sucursales = sucursal.name
                if sucursales == record.partner_id.name:
                    es_sucursal = True

            if record.picking_type_id.sequence_code == "PICK":
                es_picking = True
            if record.picking_type_id.sequence_code == "PACK":
                es_packing = True
            if record.picking_type_id.sequence_code == "OUT":
                es_salida = True

            record.send_button_visible = es_picking and record.state not in ('draft', 'confirmed', 'cancel', 'assigned') and es_sucursal and self.rfid_response != "SUCCESS"
            record.cg1_button_visible = es_salida and record.state not in ('draft', 'confirmed', 'cancel', 'assigned')
            record.packing_button_visible = es_packing and record.state not in ('draft', 'confirmed', 'cancel', 'assigned') and es_sucursal and self.rfid_response != "SUCCESS"

    # INFO: Método que calcula la cantidad total de productos en la orden de salida (Para el vale de entrega) 
    @api.depends('state')
    def _compute_total_order(self):
        for record in self:
            total = 0
            if record.state == 'done':
                for product in record.move_ids:
                    total += product.quantity
                record.total_order = total
    
    # INFO: Método que valida que la cantidad de productos registrada no sea mayor a la cantidad solicitada, sólo aplica para operaciones de picking, packing y salida
    def button_validate(self):
        es_salida = False
        if self.picking_type_id.sequence_code == "PICK" or self.picking_type_id.sequence_code == "PACK" or self.picking_type_id.sequence_code == "OUT":
            es_salida = True        
        for product in self.move_ids:
            if product.quantity > product.product_uom_qty and es_salida:
                raise ValidationError(f'La cantidad del producto "{product.product_id.display_name}" no puede ser mayor a la cantidad solicitada')
        res = super(StockInherit, self).button_validate()
        return res