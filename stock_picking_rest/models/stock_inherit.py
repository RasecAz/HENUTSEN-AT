import json
import requests
import os
import logging

_logger = logging.getLogger(__name__)

from odoo import SUPERUSER_ID, _, fields, models, api
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from markupsafe import Markup
from odoo.exceptions import ValidationError, UserError
from datetime import datetime

class StockInherit(models.Model):
    _inherit = 'stock.picking'

# ------------------------------------------------------------------------------------------------
# CAMPOS
# ------------------------------------------------------------------------------------------------

    rfid_response = fields.Char(
        string='Request state',
        readonly=True
    )
    response = fields.Char(
        string='Request response',
        readonly=True
    )
    bearer = fields.Char(
        string='Bearer token',
        readonly=True
    )
    json_generado = fields.Text(
        string='Generated JSON',
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
        string='Total products',
        compute='_compute_total_order',
        store=True
    )
    ribbon_visible = fields.Boolean(
        string='Ribbon visible',
        default=False
    )
    ribbon_error = fields.Boolean(
        string='Ribbon error',
        default=False
    )
    is_executed = fields.Boolean(
        string='Is executed',
        default=False
    )
    is_backorder = fields.Boolean(
        string='Is backorder',
        default=False
    )

# ------------------------------------------------------------------------------------------------
# METODOS
# ------------------------------------------------------------------------------------------------

    # INFO: Metodo que setea la estructura del json dependiendo del tipo de movimiento
    def _create_debug_json(self):

        #data_json corresponde a la estructura principal del json, mientras que product_list es la lista de los productos
        data_json_picking = {}
        product_list = []
        operation_name = self.name
        operacion_origen = self.location_id.company_id.name
        operacion_destino = self.partner_id.name
        for move in self.move_ids:
            if move.move_dest_ids and move.move_dest_ids.reference:
                operacion_packing = move.move_dest_ids.reference
                break
            else:
                operacion_packing = ""

        #Se recorre cada producto de la operación
        for product in self.move_ids.move_line_ids:
            lot_name = product.lot_id.name
            if not lot_name:
                lot_name = ""
            referencia_producto = product.product_id.default_code
            name_producto = product.product_id.name.rstrip()
            cantidad_producto = product.quantity
            variant_list = []
            if product.product_id.product_template_attribute_value_ids:
                for variante in product.product_id.product_template_attribute_value_ids:
                    variant_list.append({
                        "name": variante.attribute_id.name,
                        "value": variante.name
                    })
                product_list.append({
                    "observation": name_producto,
                    "quantity": cantidad_producto,
                    "batchNumber": lot_name,
                    "productSku": referencia_producto,
                    "variantList": variant_list
                })
            else:
                product_list.append({
                    "observation": name_producto,
                    "quantity": cantidad_producto,
                    "batchNumber": lot_name,
                    "productSku": referencia_producto
                })           
        data_json_picking= json.dumps({
            "consecutive": operation_name,
            "packingConsecutive": operacion_packing,
            "saleOrder": self.origin,
            "sourceLocation": operacion_origen,
            "targetLocation": operacion_destino,
            "productList": product_list
            })
        return data_json_picking

    # INFO: Método que genera el json a CG1 al validar la orden de salida
    def send_operation_to_cg1(self):
        if not self.is_executed:
            # is_executed se utiliza para evitar que el método se ejecute más de una vez, ya que el request a CG1 tarda
            # bastante en responder.
            self.is_executed = True
            cg1_detalle = {}
            especial_lista = []
            fecha_operacion = datetime.now().strftime("%Y-%m-%d")
            config = self.get_config_params()
            service_url = config['url_cg1']
            headers = {
                    'Content-Type': 'application/json'
                }
            es_sucursal = False
            prefijo = self.picking_type_id.sequence_id.prefix
            lista_precio = self.sale_id.pricelist_id.name
            items_lista = self.env['product.pricelist'].search([('name', '=', lista_precio)])
            nit_vendedor = str(self.location_id.company_id.vat)
            id_sucursal = self.partner_id.company_registry

            # Se obtiene la lista de códigos de clientes especiales desde el modelo config.henutsen, luego se
            # recorre la lista y se compara con el NIT del cliente actual, si el NIT del cliente actual se encuentra
            # en la lista de códigos de clientes especiales, se asigna su NIT, de lo contrario, se asigna el NIT de
            # Aristextil.
            especiales = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).special_branch
            if especiales:
                especial_lista = especiales.split(",")
            for sucursal in self.location_id.company_id.child_ids:
                    sucursales = sucursal.name
                    if sucursales == self.partner_id.name:
                        es_sucursal = True
            if es_sucursal and self.partner_id.vat not in especial_lista:
                nit_cliente = "900538591"
            else:
                nit_cliente = str(self.partner_id.vat)
                id_sucursal = "00"
                nit_vendedor = str(self.sale_id.user_id.partner_id.vat)

            # Se recorre cada producto de la operación y se crea un diccionario con la información necesaria para
            # enviar a CG1, si el producto ya se encuentra en el diccionario, se suma la cantidad, de lo contrario, se
            # crea una nueva entrada en el diccionario. El precio de los productos no debe contener decimales, por lo
            # que se redondea el precio a un entero.
            for producto in self.move_ids:
                referencia_producto = producto.product_id.default_code
                cantidad_producto = producto.quantity
                precio_producto = None
                for item in items_lista.item_ids:
                    if item.product_tmpl_id.name == producto.product_id.name:
                        precio_producto = int(round(item.fixed_price))
                if not precio_producto:
                    precio_producto = 0
                if cantidad_producto != 0:
                    if referencia_producto in cg1_detalle:
                        suma = float(cg1_detalle[referencia_producto]["CMPETRM_CANT_PED_1"]) + cantidad_producto
                        cg1_detalle[referencia_producto]["CMPETRM_CANT_PED_1"] = str(int(round(suma)))
                    else:
                        cg1_detalle[referencia_producto] = {
                            "CMPETRM_IND_ITEMS": "I",
                            "CMPETRM_ITEMS": referencia_producto,
                            "CMPETRM_UNIMED_CAP": "UND",
                            "CMPETRM_CANT_PED_1": str(int(cantidad_producto)),
                            "CMPETRM_IND_UNIDAD": "1",
                            "CMPETRM_LIPRE": lista_precio,
                            "CMPETRM_PRECIO_UNI": str(precio_producto),
                            "CMPETRM_FECHA": fecha_operacion,
                            "CMPETRM_VENDEDOR": nit_vendedor.split("-")[0],
                            "CMPETRM_MOTIVO": "01"
                        }
            cg1_json = json.dumps({
                "CMPETRM_OC_NRO": self.name.replace(prefijo, "", 1),
                "CMPETRM_IND_CLI": 2,
                "CMPETRM_TERC": nit_cliente.split("-")[0],
                "CMPETRM_SUC": id_sucursal,
                "CMPETRM_FECHA": fecha_operacion,
                "CMPETRM_CO": "001",
                "CMPETRM_LOCAL": "03",
                "Detalle": list(cg1_detalle.values())
            })

            _logger.info(cg1_json)
            
            # Se envía la información a CG1, si la respuesta es exitosa, se muestra un mensaje de éxito, de lo contrario,
            # se muestra un mensaje de error. Dependiendo del error, se maneja el caso.
            response = requests.request("POST", service_url, headers=headers, data=cg1_json)

            try:
                response_json = response.json()
                # Si todo es correcto (el response es 200 y la respuesta contiene "ok"), se muestra un mensaje de éxito.
                if response.status_code == 200 and "ok" in response_json:
                    body_mensaje = Markup(_(f'<h2>CG1 Shipment Successful!</h2> <p>The information has been sent to CG1, check the information in the system.</p>'))
                    self.message_post(body=body_mensaje, message_type='notification')
                    self.rfid_response = "SUCCESS"
                    self.ribbon_visible = True
                    self.ribbon_error = False
                    self.response = response.text
                # Si la respuesta contiene "error" o "detail", se muestra un mensaje de error.
                elif "error" in response_json or "detail" in response_json:
                    self.rfid_response = _("FAILED. Error in the response request.")
                    self.ribbon_error = True
                    self.ribbon_visible = False
                    self.response = response.text
                # Si la respuesta no contiene "ok", "error" o "detail", se muestra un mensaje de error desconocido.
                else:
                    self.rfid_response = _("FAILED. Unknown error in the response request.")
                    self.ribbon_error = True
                    self.ribbon_visible = False
                    self.response = response.text
            # Si hay un error al decodificar la respuesta, se muestra un mensaje de error.
            except json.JSONDecodeError:
                self.rfid_response = _("FAILED. Error decoding the response.")
                self.ribbon_error = True
                self.ribbon_visible = False
                self.response = response.text

            # Se formatea el json generado para que sea más legible.
            cg1_json = json.dumps(cg1_json, indent=4)

            self.json_generado = cg1_json
            self.endpoint = service_url
            self.is_executed = False
        
        return True

    # INFO: Método que envía la información de picking a la URL expuesta de Henutsen
    def _picking_service(self):
        data_json = self._create_debug_json()
        config = self.get_config_params()
        self.json_generado = data_json
        bearer_token = config['bearer_token']
        service_url = config['url_picking']
        self.endpoint = service_url
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + bearer_token
            }

        # Preparación de la solicitud POST con el token
        response = requests.request("POST",service_url, headers=headers, data=data_json)

        if response.status_code == 200:
            # La solicitud fue exitosa, procesa la respuesta.
            body_mensaje = Markup(_(f'<h2>¡RFID code generation in Henutsen successful!</h2> <p>The information has been sent to Henutsen, start the labeling process.</p>'))
            self.message_post(body=body_mensaje, message_type='notification')
            self.rfid_response = "SUCCESS"
            self.response = response.text
        else:
            # Si la solicitud falla, el sistema tiene una segunda oportunidad de enviar la solicitud con un nuevo token.
            bearer_token = self.get_bearer()
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + bearer_token
            }
            response = requests.request("POST",service_url, headers=headers, data=data_json)
            # Se repite el llamado al servicio. En este caso, ya se manejan los casos de manera habitual.
            if response.status_code == 200:
                body_mensaje = Markup(_(f'<h2>¡RFID code generation in Henutsen successful!</h2> <p>The information has been sent to Henutsen, start the labeling process.</p>'))
                self.message_post(body=body_mensaje, message_type='notification')
                self.rfid_response = "SUCCESS"
                self.response = response.text
            else:
                self.rfid_response = "FAILED"
                body_mensaje = Markup(f'<h2>¡Envío Errado!</h2> <p>Hubo un error al enviar la información a Henutsen. Detalles {response.text}.</p><br><p>Valide los parámetros del envío e intente de nuevo.</p>')
                self.message_post(body=body_mensaje, message_type='notification')
                self.response = response.text
    
    # INFO: Método que envía la información de picking a la URL expuesta de Henutsen
    # TODO: Eliminar este método, se debe cambiar el nombre de método _picking_service a send_picking_to_henutsen
    #      y revisar todos los llamados.
    def send_picking_to_henutsen(self):
        self._picking_service()  

    # INFO: Método que envía la información de packing a la URL expuesta de Henutsen
    # TODO: Traducir los mensajes de éxito y error a inglés.
    def send_packing_to_henutsen(self):
        operation_name = self.name
        operacion_origen = self.location_id.company_id.name
        operacion_destino = self.partner_id.name
        box_order = []
        data_json_packing = {}
        # Se recorre cada caja de la operación y se crea un diccionario con la información necesaria para
        # enviar a Henutsen.
        for box_list in self.move_line_ids_without_package.mapped('result_package_id'):
            box_id = box_list.name
            product_list = []
            for product in box_list.quant_ids:
                referencia_producto = product.product_id.default_code
                cantidad_producto = product.quantity
                variant_list = []
                if product.product_id.product_template_attribute_value_ids:
                    for variant in product.product_id.product_template_attribute_value_ids:
                        nombre_variante = variant.attribute_id.name
                        valor_variante = variant.name
                        variant_list.append({
                            "name": nombre_variante,
                            "value": valor_variante
                        })
                    product_list.append({
                    "quantity": cantidad_producto,
                    "productSku": referencia_producto,
                    "variantList": variant_list
                    })
                #Si no existen variantes, no se incluye sección de variantList al json
                else:
                    product_list.append({
                    "quantity": cantidad_producto,
                    "productSku": referencia_producto
                })
            box_order.append({
                "id": box_id,
                "weight": str(box_list.package_weight),
                "productList": product_list
            })
        
        data_json_packing = json.dumps({
            "consecutive": operation_name,
            "saleOrder": self.origin,
            "sourceLocation": operacion_origen,
            "targetLocation": operacion_destino,
            "boxOrders": box_order
        })
        # IMPORTANTE: Todo debe estar configurado en la vista de configuración de Henutsen para que el web service 
        # funcione correctamente. El programa es capaz de reconfigurarse si el token expira.
        self.json_generado = data_json_packing
        config = self.get_config_params()
        bearer_token = config['bearer_token']
        service_url = config['url_packing']
        self.endpoint = service_url
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + bearer_token
            }

        # Preparación de la solicitud POST con el token
        response = requests.request("POST",service_url, headers=headers, data=data_json_packing)

        if response.status_code == 200:
            # La solicitud fue exitosa, procesa la respuesta
            success_message = _(f'<h2>¡Operation successfull!</h2> <p>Data has been send to Henutsen.</p>')
            body_mensaje = Markup(success_message)
            self.message_post(body=body_mensaje, message_type='notification')
            self.rfid_response = "SUCCESS"
            self.response = response.text
        else:
            # La solicitud falló, maneja el error de la misma manera que lo hace con el picking, generando un nuevo token
            # y enviando la solicitud nuevamente.
            bearer_token = self.get_bearer()
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + bearer_token
            }
            # Preparación de la solicitud POST con el token
            response = requests.request("POST",service_url, headers=headers, data=data_json_packing)
            if response.status_code == 200:
                body_mensaje = Markup(_(f'<h2>¡Operación Exitosa!</h2> <p>La información ha sido enviada a Henutsen.</p>'))
                self.message_post(body=body_mensaje, message_type='notification')
                self.rfid_response = "SUCCESS"
                self.response = response.text
            else:
                self.rfid_response = "FAILED"
                body_mensaje = Markup(f'<h2>¡Envío Errado!</h2> <p>Hubo un error al enviar la información a Henutsen. Detalles {response.text}.</p><br><p>Valide los parámetros del envío e intente de nuevo.</p>')
                self.message_post(body=body_mensaje, message_type='notification')
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
            is_send_mode = self.env['res.config.settings'].sudo().get_values().get('send_packing_to_henutsen')
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

            record.send_button_visible = es_picking and record.state not in ('draft', 'confirmed', 'cancel', 'assigned') and self.rfid_response != "SUCCESS" and es_sucursal
            record.packing_button_visible = es_packing and record.state not in ('draft', 'confirmed', 'cancel', 'assigned') and self.rfid_response != "SUCCESS" and is_send_mode and es_sucursal
            record.cg1_button_visible = es_salida and record.state not in ('draft', 'confirmed', 'cancel', 'assigned') and self.rfid_response != "SUCCESS" and not record.ribbon_visible

    # INFO: Método que calcula la cantidad total de productos en la orden de salida (Para el vale de entrega).
    @api.depends('state')
    def _compute_total_order(self):
        for record in self:
            total = 0
            for product in record.move_ids:
                total += product.quantity
            record.total_order = total
    
    # INFO: Método que adquiere los parámetros de configuración de Henutsen, se llama en cada método que envía información.
    def get_config_params(self):
        config_params = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1)
        if not config_params.api_key or not config_params.email_henutsen or not config_params.url_bearer or not config_params.url_picking or not config_params.url_packing:
            raise ValidationError(_('Missing data in Henutsen configuration, validate that all fields are complete, if you do not have access, ask an administrator to update this information'))
        if os.environ.get("ODOO_STAGE") == 'production':
            bearer_token = config_params.bearer_token
            if not bearer_token:
                bearer_token = config_params.get_bearer()
            return {
                'url_picking': config_params.url_picking,
                'url_packing': config_params.url_packing,
                'url_cg1': config_params.url_cg1,
                'bearer_token': bearer_token,
            }
        else:
            bearer_token = config_params.bearer_token_qa
            if not bearer_token:
                bearer_token = config_params.get_bearer_qa()
            return {
                'url_picking': config_params.url_picking_qa,
                'url_packing': config_params.url_packing_qa,
                'url_cg1': config_params.url_cg1_qa,
                'bearer_token': bearer_token,
            }

    # INFO: Método que obtiene el token de Henutsen, se llama en cada método que envía información.
    def get_bearer(self):
        config_params = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1)
        if os.environ.get("ODOO_STAGE") == 'production':
            return config_params.get_bearer()
        else:
            return config_params.get_bearer_qa()
    
    # INFO: Método que se ejecuta al presionar el botón de validar la operación. Para este caso, se extiende su funcionalidad
    #       para que, al validar una operación de salida, se realice la validación de la operación de packing más reciente y se
    #       actualicen las cantidades de los productos en la operación de salida.
    # TODO: Revisar cómo se puede buscar la operación más reciente para validar si no han sido validadas las operaciones anteriores.
    def button_validate(self):

        # origin_ids = self.move_ids.move_orig_ids if self.move_ids.move_orig_ids else False
        # if origin_ids and len(origin_ids) > 1:
        #     real_origin_id = self.env['stock.picking'].sudo().search([('name', '=', max(self.move_ids.move_orig_ids, key=lambda x: x.create_date).reference)], limit=1)
        # else:
        #     real_origin_id = origin_ids
        # if real_origin_id and real_origin_id.state != 'done':
        #     raise UserError(_('La operación anterior (%s) no ha sido validada aún.', real_origin_id.name))
        res = super(StockInherit, self).button_validate()
        for record in self:
            if record.picking_type_id.sequence_code == "OUT":
                pass
            else:
                if record.move_ids.move_dest_ids:
                    if len(record.move_ids.move_dest_ids) > 1:
                        most_recent_move = min(record.move_ids.move_dest_ids, key=lambda x: x.create_date).reference
                    else:
                        most_recent_move = record.move_ids.move_dest_ids.reference
                    context = self.env['stock.picking'].sudo().search([('name', '=', most_recent_move)], limit=1)
                    # Este método recomputa las cantidades de los productos. Se llama bajo el contexto de la siguiente operación.
                    context.script_recompute_quantities(origin_reference=record.name)
        return res
    
    # INFO: Método que consume Henutsen para crear las líneas de empaquetado en la operación de packing. Este tipo de funciones se
    #       deben crear con el decorador @api.model para que puedan ser llamadas de manera externa.
    @api.model
    def send_packing(self, data):
        json_str = json.dumps(data)
        _logger.info(json_str)
        context = self.env['stock.picking'].sudo().search([('name', '=', data['consecutive'])], limit=1)
        if not context:
            return {'error': _(f'No Packing operation {data["consecutive"]} found. Check the operation number and try again.')}
        is_recieve_mode = self.env['res.config.settings'].sudo().get_values().get('recieve_packing_from_henutsen')
        if not is_recieve_mode:
            return {'error': _('Aristextil instance is not configured to receive packing from Henutsen.')}
        if context.state == 'done':
            return {'error': _(f'The operation {context.name} has already been validated. It is not possible to perform the packing.')}
        boxes_list = []
        # Se recorre cada caja de la operación y se crea un diccionario con la información necesaria para crear las líneas de empaquetado.
        for box_order in data['boxOrders']:
            product_list = []
            for product in box_order['productList'] if 'productList' in box_order else box_order['ProductList']:
                productos = self.env['product.product'].sudo().search([('default_code', '=', product['productSku'].rstrip())])
                if len(productos) > 1 and 'variantList' not in product or len(productos) > 1 and product['variantList'] == []:
                    return {'error': _(f"Multiple products with the same SKU [{product['productSku']}] were found. Check the SKU or send the product variants and try again.")}
                elif len(productos) > 1 and 'variantList' in product:
                    producto_variante = False
                    for producto in productos:
                        all_variants_match = True
                        for variant in product['variantList']:
                            variant_match = producto.product_template_attribute_value_ids.filtered(
                                lambda v: v.attribute_id.name == variant['name'] and v.name == variant['value']
                            )
                            if not variant_match:
                                all_variants_match = False
                                break

                        if all_variants_match:
                            producto_variante = producto
                            break 
                else:
                    producto_variante = productos
                if not producto_variante:
                    return {'error': _(f"The product {product['productSku']} was not found with the defined variants. Check the variant, SKU and try again.")}
                
                if not 'batchNumber' in product or product['batchNumber'] == '':
                    lote = False
                else:
                    lote = self.env['stock.lot'].sudo().search([('name', '=', product['batchNumber']), ('product_id.id', '=', producto_variante.id), ('company_id.id', '=', context.company_id.id)])
                    if not lote:
                        return {'error': _(f"The batch {product['batchNumber']} was not found or doesnt exist. Check the value sent and try again.")}
                # Nivel 2: lista de productos.
                product_list.append({
                    'product_id': producto_variante,
                    'lot_id': lote,
                    'quantity': product['quantity']
                })
            # Nivel 1: lista de cajas.
            boxes_list.append({
                'id': box_order['id'],
                'weight': box_order['weight'] if 'weight' in box_order else 0.0,
                'product_list': product_list
            })
        # TODO: cambiar este try-except para que se maneje de manera más específica, dejarlos de esta manera no es
        #       una buena práctica.
        #       Adicional, cambiar los mensajes de éxito y error a inglés.
        try:
            for move in context.move_ids:
                move.move_line_ids.sudo().unlink()
            for box in boxes_list:
                try:
                    weight = float(box['weight'])
                except ValueError:
                    weight = 0.0
                box_id = context.env['stock.quant.package'].sudo().create({'name': box['id'],'package_weight': weight})
                for product in box['product_list']:
                    move_context = context.move_ids.filtered(lambda m: m.product_id.id == product['product_id'].id)
                    if move_context:
                        context.move_line_ids.create({
                            'picking_id': context.id,
                            'move_id': move_context.id,
                            'product_id': product['product_id'].id,
                            'location_dest_id': context.location_dest_id.id,
                            'location_id': context.location_id.id,
                            'lot_id': product['lot_id'].id if product['lot_id'] else False,
                            'quantity': product['quantity'],
                            'quantity_product_uom': product['quantity'],
                            'result_package_id': box_id.id
                        })
            body_mensaje = Markup(
                _(f'''
                <h2>¡Productos empacados exitosamente!</h2>
                <p>Los productos se han empacado desde Henutsen, valide la orden y continue con el despacho.</p>
                <ul>
                    <li>Operación: {context.name}</li>
                    <li><strong>Cajas:</strong>
                        <ul>
                            {''.join([f"<li>Caja {box['id']}:" +
                                    "<ul>" +
                                    ''.join([f"<li>Producto: {product['product_id'].display_name}, Lote: '{product['lot_id'].name if product['lot_id'] != False else 'Sin lote'}', Cantidad: {product['quantity']} Unidades.</li>" for product in box['product_list']]) +
                                    "</ul></li>" for box in boxes_list])}
                        </ul>
                    </li>
                </ul>
                '''
            ))
            context.message_post(body=body_mensaje, message_type='notification')
            context.rfid_response = "SUCCESS_PACKING"
            return {
                'success': _(f'Packing of products for operation {context.name} successful!')
            }     
        except ValidationError as e:
            return {'error': _(f'Error creating the packing. Details: {e}. Try again.')}
    
    # INFO: Método que consume Henutsen para enviar la recepción de la orden en tienda. Este tipo de funciones se
    #       deben crear con el decorador @api.model para que puedan ser llamadas de manera externa.
    # TODO: Cambiar los mensajes de éxito y error a inglés.
    @api.model
    def receive_order(self, data):
        json_str = json.dumps(data)
        _logger.info(json_str)
        # Se traen dos contextos, uno corresponde a la operación de recepción y el otro a la operación de despacho. Se requiere
        # la operación de despacho para obtener los lotes de los productos que no tienen lote en la operación de recepción.
        context = self.env['stock.picking'].sudo().search([('purchase_id.partner_ref', '=', data['consecutive']),('picking_type_id.sequence_code', '=', 'IN')], limit=1)
        context_warehouse = self.env['stock.picking'].sudo().search([('origin', '=', data['consecutive']), ('picking_type_id.sequence_code', '=', 'OUT')], limit=1)
        if not context:
            return {'error': _(f'No reception order found with sale order {data["consecutive"]}. Check the order number and try again.')}
        if context.state == 'done':
            return {'error': _(f'The operation {context.name} has already been validated. It is not possible to perform the reception.')}
        product_list = []
        # Se recorre cada producto de la operación y se crea un diccionario con la información necesaria para la recepción.
        for product in data['productList']:
            productos = self.env['product.product'].sudo().search([('default_code', '=', product['productSku'].rstrip())])
            if len(productos) > 1 and 'variantList' not in product or len(productos) > 1 and product['variantList'] == []:
                return {'error': _(f"Multiple products with the same SKU [{product['productSku']}] were found. Check the SKU or send the product variants and try again.")}
            elif len(productos) > 1 and 'variantList' in product:
                producto_variante = False
                for producto in productos:
                    all_variants_match = True
                    for variant in product['variantList']:
                        variant_match = producto.product_template_attribute_value_ids.filtered(
                            lambda v: v.attribute_id.name == variant['name'] and v.name == variant['value']
                        )
                        if not variant_match:
                            all_variants_match = False
                            break

                    if all_variants_match:
                        producto_variante = producto
                        break 
            else:
                producto_variante = productos
            if not producto_variante:
                return {'error': _(f"The product {product['productSku']} was not found with the defined variants. Check the variant, SKU and try again.")}
            
            if not 'batchNumber' in product or product['batchNumber'] == '':
                move_line = context_warehouse.move_line_ids.filtered(lambda line: line.product_id == producto_variante)       
                if move_line:
                    lote = move_line[0].lot_id.name
                else:
                    lote = False
            else:
                lote = context.env['stock.lot'].sudo().search([('name', '=', product['batchNumber']), ('product_id.id', '=', producto_variante.id), ('company_id.id', '=', context.company_id.id)]).name
                if not lote:
                    move_line = context_warehouse.move_line_ids.filtered(lambda line: line.product_id == producto_variante)        
                    if move_line:
                        lote = move_line[0].lot_id.name
                    else:
                        lote = False
            product_list.append({
                'product_id': producto_variante,
                'lot_id': lote,
                'quantity': product['quantity'],
                'missing_quantity': product['missingQuantity']
            })
        product_ids_in_list = [p['product_id'].id for p in product_list]
        moves_not_in_list = context.move_ids.filtered(lambda m: m.product_id.id not in product_ids_in_list)
        for product in product_list:
            move_line = False
            move_context = context.move_ids.filtered(lambda m: m.product_id.id == product['product_id'].id)
            if move_context:
                move_context.product_uom_qty = product['quantity']
            if move_context and product['lot_id']:
                move_line = context.move_line_ids.filtered(lambda ml: ml.move_id.id == move_context.id and ml.lot_id.name == product['lot_id'])
            if not move_line:
                move_line = context.move_line_ids.filtered(lambda ml: ml.move_id.id == move_context.id and not ml.lot_id)
            if move_line:
                move_line.quantity = product['quantity'] - product['missing_quantity']
                move_line.lot_name = product['lot_id']
            elif not move_context or not move_line:
                new_move_line = {
                    'product_id': product['product_id'].id,  # Reemplaza product_id con el ID del producto deseado
                    'name': product['product_id'].display_name,
                    'quantity': product['quantity'] - product['missing_quantity'],
                    'product_uom_qty': product['quantity'],
                    # 'lot_name': product['lot_id'],
                    'location_id': context.location_id.id,
                    'location_dest_id': context.location_dest_id.id,
                    'picking_id': context.id,
                    'company_id': context.company_id.id
                    # 'picking_id': context.id,
                    # 'product_id': product['product_id'].id,
                    # 'location_dest_id': context.location_dest_id.id,
                    # 'location_id': context.location_id.id,
                    # 'lot_name': product['lot_id'],
                    # 'quantity': product['quantity'] - product['missing_quantity'],
                    # 'product_uom_id': product['product_id'].uom_id.id,
                    # 'quantity_product_uom': product['quantity'],
                    # 'company_id': context.company_id.id
                }
                if not move_context:
                    move_context = context.move_ids.create(new_move_line)
    
                # context.update(move_context)
                
        # Se valida que el campo 'complete' sea un booleano y que sea verdadero, si es así, se valida la operación automáticamente.
        if isinstance(data['complete'], bool) and data['complete']:
            context.rfid_response = "COMPLETE"
            # move_not_in_list es una lista de productos que no se encuentran en la lista de productos enviados por planta, en caso de que
            # existan productos en esta lista, se envía un mensaje de notificación al usuario notificando los productos que no se enviaron.
            if moves_not_in_list:
                body_mensaje = Markup(
                    _(f'''
                    <h2>¡Recepción completa!</h2>
                    <p>La recepción de la orden ha sido completada con éxito. Se han actualizado las unidades de acuerdo a lo desplachado. Sin embargo, estos fueron los productos no enviados por planta</p>
                    <li><strong>Productos que no envió planta:</strong>
                        <ul>
                            {''.join([f"<li>Producto: {move.product_id.display_name}. Cantidad pedida: {move.product_uom_qty}</li>" for move in moves_not_in_list])}
                        </ul>
                    </li>
                    '''
                ))
            else:
                body_mensaje = Markup(
                    _(f'''
                    <h2>¡Recepción completa!</h2>
                    <p>La recepción de la orden ha sido completada con éxito. Se han actualizado las unidades de acuerdo a lo desplachado</p>
                    '''
                ))
            context.message_post(body=body_mensaje, message_type='notification')
            # Se eliminan de la orden los productos que no llegaron a tienda y se valida la operación.
            moves_not_in_list.unlink()
            super(StockInherit, context).button_validate()
            return {
                'success': _(f'Order reception without missings, complete for operation {context.name}!')
            }
        body_mensaje = Markup(
            _(f'''
            <h2>¡Se reportaron productos faltantes en la recepción!</h2>
            <p>Valide con Planta las discrepancias. Si desea recibir el pedido con dichos faltantes, presione "Validar".</p>
            <ul>
                <li>Operación: {context.name}</li>
                <li><strong>Productos que llegaron:</strong>
                    <ul>
                        {''.join([f"<li>Producto: {product['product_id'].display_name}, Cantidad esperada: {product['quantity']} Unidades, Cantidad faltante: {product['missing_quantity']} Unidades.</li>" for product in product_list])}
                    </ul>
                </li>
                <li><strong>Productos que no envió planta:</strong>
                    <ul>
                        {''.join([f"<li>Producto: {move.product_id.display_name}. Cantidad pedida: {move.product_uom_qty}</li>" for move in moves_not_in_list])}
                    </ul>
                </li>
            </ul>
            '''
        ))
        context.message_post(body=body_mensaje, message_type='notification')
        context.rfid_response = "MISSING_PRODUCTS"
        return {
            'success': _(f'Missing Products reported in operation {context.name}!'),
        }
    
    # INFO: Método que recomputa las cantidades de los productos en las operaciones de recolección:
    #       - Si la operación es de tipo PICK, se recomputan según la demanda.
    #       - Si la operación tiene origen (no es picking), se recomputan según la operación anterior.
    #       - Si la operación ya fue validada o es una backorder, no se recomputan las cantidades.
    #       Para el segundo caso, se eliminan las líneas de la operación y se crean nuevas líneas con las cantidades de la operación anterior.
    def script_recompute_quantities(self, origin_reference=False):
        if self.backorder_id:
            self.is_backorder = True
        if self.state == 'done':
            return True
        product_move_dict = []
        # for move in self.move_ids:
        #     _logger.warning(move.product_id.name)
        #     if move.move_orig_ids:
        #         if len(move.move_orig_ids) == 1 and move.move_orig_ids.picking_id.backorder_id:
        #             continue
        #         else:
        #             origin_move = move.move_orig_ids
        #             break
        # origin_move = next((move.move_orig_ids for move in self.move_ids if move.move_orig_ids and move.quantity != 0), False)
        # if len(origin_move) > 1:
        #     for move in origin_move:
        #         _logger.warning(move.picking_id)
        #     origin = [move for move in origin_move if not move.picking_id.backorder_id]
        #     origin_move = origin[0]
        #     _logger.warning(origin_move)
        # origin_reference = origin_move.reference if origin_move else False
        _logger.warning(origin_reference)
        for move in self.move_ids:
            product_id = move.product_id.id
            if product_id in product_move_dict:
                move.product_uom_qty, move.quantity = 0, 0
                move.move_line_ids.unlink()
            else:
                product_move_dict.append(product_id)
                if not origin_reference or self.picking_type_id.sequence_code == 'PICK':
                    move.quantity = move.product_uom_qty
                else:
                    if self.is_backorder:
                            return True
                    if len(move.move_orig_ids) > 1:                      
                        most_recent_move = move.move_orig_ids.filtered(lambda x: x.reference == origin_reference)
                    else:
                        most_recent_move = move.move_orig_ids
                    if most_recent_move.quantity == 0:
                        move.write({'quantity': 0})
                    else:
                        if most_recent_move.product_uom_qty != move.product_uom_qty:
                            move.write({'product_uom_qty': most_recent_move.product_uom_qty})
                        move.move_line_ids.unlink()
                        for line in most_recent_move.move_line_ids:                      
                            self.move_line_ids.create({
                                'picking_id': move.picking_id.id,
                                'move_id': move.id,
                                'product_id': line.product_id.id,
                                'quantity': line.quantity,
                                'package_id': line.result_package_id.id if line.result_package_id else False,
                                'result_package_id': line.result_package_id.id if line.result_package_id else False,
                                'quantity_product_uom': line.quantity_product_uom,
                                'product_uom_id': line.product_uom_id.id,
                                'lot_id': line.lot_id.id if line.lot_id else False,
                                'location_id': move.location_id.id,
                                'location_dest_id': move.location_dest_id.id,
                            })

        return True        


class StockMove(models.Model):
    _inherit = 'stock.move'

# ----------------------------------------------------------
# FIELDS
# ----------------------------------------------------------

# ----------------------------------------------------------
# METHODS
# ----------------------------------------------------------

    # INFO: Este método no permite registrar más unidades de las demandadas. Por lo
    #       que se extiende para que no se maneje el error y en su lugar, sólo retorne.
    def _set_product_qty(self):
        return True

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

# ----------------------------------------------------------
# FIELDS
# ----------------------------------------------------------

    default_code_integer = fields.Integer(
        'Default Code Integer', 
        compute='_compute_default_code_integer', 
        store=True
    )

# ----------------------------------------------------------
# METHODS
# ----------------------------------------------------------

    # INFO: Método que transforma el código de producto a un entero para poder ordenar
    #       los productos de manera correcta en los reportes y operaciones detalladas.
    @api.depends('product_id.default_code')
    def _compute_default_code_integer(self):
        for record in self:
            try:
                record.default_code_integer = int(record.product_id.default_code) if record.product_id.default_code else 0
            except (ValueError, TypeError):
                record.default_code_integer = 0