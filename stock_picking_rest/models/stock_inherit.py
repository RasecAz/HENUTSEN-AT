import json
import requests
import os
import logging

_logger = logging.getLogger(__name__)

from odoo import SUPERUSER_ID, _, fields, models, api
from odoo.addons.stock.models.stock_move import PROCUREMENT_PRIORITIES
from markupsafe import Markup
from odoo.exceptions import ValidationError
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
        for move in self.move_ids:
            if move.move_dest_ids and move.move_dest_ids.reference:
                operacion_packing = move.move_dest_ids.reference
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
            "sourceLocation": operacion_origen,
            "targetLocation": operacion_destino,
            "productList": product_list
            })
        return data_json_picking

    # INFO: Método que genera el json a CG1 al validar la orden de salida
    def send_operation_to_cg1(self):
        if not self.is_executed:
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
            
            response = requests.request("POST", service_url, headers=headers, data=cg1_json)

            try:
                response_json = response.json()
                if response.status_code == 200 and "ok" in response_json:
                    # trad: <h2>¡Envío a CG1 Exitoso!</h2> <p>Se ha enviado la información a CG1, consulte la información en el sistema.</p>
                    body_mensaje = Markup(_(f'<h2>CG1 Shipment Successful!</h2> <p>The information has been sent to CG1, check the information in the system.</p>'))
                    self.message_post(body=body_mensaje, message_type='notification')
                    self.rfid_response = "SUCCESS"
                    self.ribbon_visible = True
                    self.response = response.text
                elif "error" in response_json or "detail" in response_json:
                    self.rfid_response = _("FAILED. Error in the response request.")
                    self.ribbon_error = True
                    self.ribbon_visible = False
                    self.response = response.text
                else:
                    self.rfid_response = _("FAILED. Unknown error in the response request.")
                    self.ribbon_error = True
                    self.ribbon_visible = False
                    self.response = response.text
            except json.JSONDecodeError:
                self.rfid_response = _("FAILED. Error decoding the response.")
                self.ribbon_error = True
                self.ribbon_visible = False
                self.response = response.text

            cg1_json = json.dumps(cg1_json, indent=4)

            self.json_generado = cg1_json
            self.endpoint = service_url
            self.is_executed = False
        
        return True

    # INFO: Método que envía la información a la URL expuesta de Henutsen 
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
            # La solicitud fue exitosa, procesa la respuesta (json_response)
            # TRAD: <h2>¡Generación de códigos RFID en Henutsen exitosa!</h2> <p>Se ha enviado la información a Henutsen, inicie el proceso de etiquetado.</p>
            body_mensaje = Markup(f'<h2>¡RFID code generation in Henutsen successful!</h2> <p>The information has been sent to Henutsen, start the labeling process.</p>')
            self.message_post(body=body_mensaje, message_type='notification')
            self.rfid_response = "SUCCESS"
            self.response = response.text
        else:
            # La solicitud falló, maneja el error
            bearer_token = self.get_bearer()
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + bearer_token
            }
            response = requests.request("POST",service_url, headers=headers, data=data_json)

            if response.status_code == 200:
                # TRAD: <h2>¡Generación de códigos RFID en Henutsen exitosa!</h2> <p>Se ha enviado la información a Henutsen, inicie el proceso de etiquetado.</p>
                body_mensaje = Markup(f'<h2>¡RFID code generation in Henutsen successful!</h2> <p>The information has been sent to Henutsen, start the labeling process.</p>')
                self.message_post(body=body_mensaje, message_type='notification')
                self.rfid_response = "SUCCESS"
                self.response = response.text
            else:
                self.rfid_response = "FAILED. Error " + str(response.status_code)
                self.response = response.text
    
    # INFO: Método que envía la información de picking a la URL expuesta de Henutsen
    def send_picking_to_henutsen(self):
        self._picking_service()    
        
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
            record.cg1_button_visible = es_salida and record.state not in ('draft', 'confirmed', 'cancel', 'assigned') and self.rfid_response != "SUCCESS"

    # INFO: Método que calcula la cantidad total de productos en la orden de salida (Para el vale de entrega) 
    @api.depends('state')
    def _compute_total_order(self):
        for record in self:
            total = 0
            if record.state == 'done':
                for product in record.move_ids:
                    total += product.quantity
                record.total_order = total
    
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

    def get_bearer(self):
        config_params = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1)
        if os.environ.get("ODOO_STAGE") == 'production':
            return config_params.get_bearer()
        else:
            return config_params.get_bearer_qa()
        
    def button_validate(self):
        for move in self.move_ids:
            if move.move_dest_ids:
                for move_dest_id in move.move_dest_ids:
                    if move_dest_id.product_qty < move.quantity:
                        move_dest_id.product_qty = move.quantity
                        move_dest_id.quantity = move.quantity
                        # move_dest_id.product_uom_qty = move.quantity
        res = super(StockInherit, self).button_validate()
        return res
    
    @api.model
    def send_packing(self, data):
        json_str = json.dumps(data)
        _logger.info(json_str)
        context = self.env['stock.picking'].sudo().search([('name', '=', data['consecutive'])], limit=1)
        if not context:
            return {'error': _(f'No Packing operation {data["consecutive"]} found. Check the operation number and try again.')}
        if context.state == 'done':
            return {'error': _(f'The operation {context.name} has already been validated. It is not possible to perform the packing.')}
        boxes_list = []
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
                product_list.append({
                    'product_id': producto_variante,
                    'lot_id': lote,
                    'quantity': product['quantity']
                })
            boxes_list.append({
                'id': box_order['id'],
                'product_list': product_list
            })
        try:
            for move in context.move_ids:
                move.move_line_ids.sudo().unlink()
            for box in boxes_list:
                box_id = context.env['stock.quant.package'].sudo().create({'name': box['id']})
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
                        # english: 
            body_mensaje = Markup(
                _(f'''
                <h2>¡Proceso de Packing Exitoso!</h2>
                <p>Se han recibido las líneas de empaquetado desde Henutsen</p>
                <ul>
                    <li>Operación: {context.name}</li>
                    <li><strong>Cajas:</strong>
                        <ul>
                            {''.join([f"<li>Caja {box['id']}:" +
                                    "<ul>" +
                                    ''.join([f"<li>Producto: {product['product_id'].name}, Lote: '{product['lot_id'].name if product['lot_id'] != False else 'Sin lote'}', Cantidad: {product['quantity']} Unidades.</li>" for product in box['product_list']]) +
                                    "</ul></li>" for box in boxes_list])}
                        </ul>
                    </li>
                </ul>
                '''
            ))
            context.message_post(body=body_mensaje, message_type='notification')
            context.rfid_response = "SUCCESS_PACKING"
            # english: 
            return {
                'success': _(f'Packing of products for operation {context.name} successful!')
            }     
        except ValidationError as e:
            return {'error': _(f'Error creating the packing. Details: {e}. Try again.')}

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _set_product_qty(self):
        return True