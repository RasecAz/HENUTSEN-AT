from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import requests, json


class StockQuant(models.Model):
    _inherit = 'stock.quant'

# --------------------------------------------------------------------------------
# CAMPOS
# --------------------------------------------------------------------------------

    id_ajuste = fields.Char(
        string='ID Ajuste', 
        readonly=True
    )

# --------------------------------------------------------------------------------
# METODOS
# --------------------------------------------------------------------------------

    # INFO: Método que capta la información de los ajustes de tienda desde Henutsen y los asigna a la sección de ajustes de inventario en Odoo
    @api.model
    def adjust_inventory(self, data):
        for product_data in data['productList']:
            variante_list_json = []
            variante_list_odoo = []
            variante_list_debug = []
            producto_variante = False
            producto = False
            bodega = False
            producto_variante = self.env['product.product'].sudo().search([('default_code', '=', product_data['nameProd'].rstrip())])
            # Buscar el quant para la ubicación y el producto
            compañia = self.env['res.company'].sudo().search([('name', '=', data['location'].rstrip())], limit=1)
            compañia = compañia.id
            location = self.env['stock.location'].sudo().search([('company_id', '=', compañia),('name', '=', product_data['stockIn'].rstrip())], limit=1)
            if not location:
                return {'error': 'No se encontró la ubicación especificada'}
            bodega = location.complete_name
            producto_variante = self.env['product.product'].sudo().search([('default_code', '=', product_data['nameProd'].rstrip())])
            if 'variantList' in product_data:
                producto = self.env['product.product'].sudo().search([('default_code', '=', product_data['nameProd'].rstrip())])
                if not producto:
                    return {'error': 'No se encontró el producto, valide su SKU: ' + product_data['nameProd']}
                for variante in product_data['variantList']:
                    if 'name' in variante or 'value' in variante:
                        variante_list_json.append(variante['value'])
            # Validar que las variantes enviadas en Henutsen coincidan con las variantes en Odoo, en caso de no tener variantes, se busca el producto por nombre
                for variante in product_data['variantList']:
                    if 'name' in variante or 'value' in variante:
                        for opciones_producto in producto:
                            for variante in opciones_producto.product_template_attribute_value_ids:
                                variante_list_odoo.append(variante.name)
                                variante_list_debug.append(variante.name)
    
                            if set(variante_list_json) == set(variante_list_odoo):
                                producto_variante = opciones_producto
                            else:
                                pass
                            variante_list_odoo = []                               
            else:
                producto_variante = self.env['product.product'].sudo().search([('default_code', '=', product_data['nameProd'].rstrip())], limit=1)
            if not producto_variante:
                if 'variantList' in product_data:
                    cadena = ', '.join(variante_list_json)
                    cadena_odoo = ', '.join('({} {})'.format(variante_list_debug[i], variante_list_debug[i+1]) for i in range(0, len(variante_list_debug), 2))
                    return {'error': f'No se encontró el producto especificado, Valide las variantes y atributos enviados. Variantes enviadas en Henutsen: ({cadena}). Opciones disponibles: {cadena_odoo}'}
                else:
                    return {'error': f'No se encontró el producto especificado. Valide el SKU del producto en Odoo: {product_data["nameProd"]}'}
            if not product_data['batchNumber']:
                ajuste_id = self.env['stock.quant'].sudo().search([('location_id.complete_name', '=', bodega),('product_id.id', '=', producto_variante.id)], limit=1)
            else:
                ajuste_id = self.env['stock.quant'].sudo().search([('location_id.complete_name', '=', bodega),('product_id.id', '=', producto_variante.id),('lot_id.name', '=', product_data['batchNumber'])], limit=1)
                if not ajuste_id:
                    ajuste_id = self.env['stock.quant'].sudo().search([('location_id.complete_name', '=', bodega),('product_id.id', '=', producto_variante.id)], limit=1)
            if not ajuste_id:
                return {'error': f'La ubicación {bodega} no tiene existencias del producto {producto_variante.name}'}
            quant = ajuste_id.available_quantity

            if not quant:
                return {'error': 'La ubicación no tiene existencias del producto'}

            if quant < product_data['quantity']:
                return {'error': 'La cantidad a ajustar es mayor a la cantidad actual de existencias en la ubicación, valide si está enviando solo los faltantes'}
            stock_con_diferencia = quant - product_data['quantity']
            # Ajustar la cantidad en el quant
            ajuste_id.sudo().write({'id_ajuste': data['idAdjustment'], 'inventory_quantity': stock_con_diferencia, 'inventory_diff_quantity': - product_data['quantity']})
            # ajuste_id.action_apply_inventory()

        return {'success': f'Ajuste de productos en la ubicación {bodega} exitoso!'}
    
    # INFO: Método que aplica los ajustes de inventario en Odoo y los envía a Henutsen en caso de que el ajuste haya sido creado desde allá
    def action_apply_inventory(self):

        for quant in self:
            variant_list = []
            data = []
            # Si el ajuste tiene un ID de ajuste, se envía la información a Henutsen, en caso contrario, solo se ajusta en Odoo
            if quant.id_ajuste:
                bearer_token = quant.env['config.henutsen'].sudo().search([], order='id desc', limit=1).bearer_token
                url_adjustment = quant.env['config.henutsen'].sudo().search([], order='id desc', limit=1).url_adjustment
                service_url = f'{url_adjustment}?idAdjustment={quant.id_ajuste}'
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {bearer_token}'
                }
                lote = quant.lot_id.name if quant.lot_id.name else ""                
                if quant.product_id.product_template_attribute_value_ids:
                    for variante_atributo in quant.product_id.product_template_attribute_value_ids:
                        variantValue = variante_atributo.name
                        variantName = variante_atributo.attribute_id.name
                        variant_list.append({"name": variantName, "value": variantValue})
                    data = json.dumps({
                        "productSku": quant.product_id.default_code,
                        "batchNumber": lote,
                        "quantity": quant.quantity - quant.inventory_quantity,
                        "variantList": variant_list,
                    })
                else:
                    data = json.dumps({
                        "productSku": quant.product_id.default_code,
                        "batchNumber": lote,
                        "quantity": quant.quantity - quant.inventory_quantity,
                    })
                response = requests.put(service_url, headers=headers, data=data)
                if response.status_code == 200:
                    pass
                else:
                    bearer_token = quant.get_bearer()
                    headers = {
                        'Content-Type': 'application/json',
                        'Authorization': f'Bearer {bearer_token}'
                    }
                    response = requests.put(service_url, headers=headers, data=data)
                    if response.status_code == 200:
                        pass
                    else:
                        raise ValidationError("Error al enviar información a Henutsen. Detalles: " + response.text)
            # Una vez que se haya enviado la información a Henutsen, se ajusta en Odoo y se limpia el campo de ID de ajuste 
            quant.id_ajuste = False
        res = super(StockQuant, self).action_apply_inventory()
        return res
    
    # INFO: Método que limpia el campo de ID de ajuste en caso de que se cancele el ajuste, para que no se envíe a Henutsen
    def action_clear_inventory_quantity(self):
        res = super(StockQuant, self).action_clear_inventory_quantity()
        self.id_ajuste = False
        return res
    
    # INFO: Método que obtiene el token de autorización para consumir los servicios de Henutsen
    def get_bearer(self):
        # Validar que exista la api_key y el email en el módulo de configuración Henutsen, en caso de que sea así, asigna los valores para obtener el token
        if not self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).api_key or not self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).email_henutsen or not self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).url_bearer:
            raise ValidationError('Faltan datos para obtener el token, completelos en la sección de Ajustes WS Henutsen, si no tiene acceso, solicitele a un administrador que actualice esta información')
        api_key = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).api_key
        email = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).email_henutsen
        bearer_url = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).url_bearer
        token_url = f'{bearer_url}/{email}?apiKey={api_key}'
        response = requests.post(token_url)
        # Validar que el token se haya obtenido correctamente
        if response.status_code == 200:
            response_json = response.json()
            bearer_token = response_json["accessToken"]
            self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).write({'bearer_token': bearer_token})
            return bearer_token
        # En caso de que no se haya obtenido el token, se genera error con información adicional
        else:
            raise ValidationError('Error al obtener el token de autorización. Mensaje: ' + response.text + ". Valide la api_key y el email en la sección de Ajustes WS Henutsen, si no tiene acceso, solicitele a un administrador que actualice esta información")