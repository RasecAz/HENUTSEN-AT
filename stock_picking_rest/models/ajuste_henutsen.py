from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import requests, json
import os


class StockQuant(models.Model):
    _inherit = 'stock.quant'

# --------------------------------------------------------------------------------
# CAMPOS
# --------------------------------------------------------------------------------

    id_ajuste = fields.Char(
        string='ID Adjustment', 
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
                return {'error': _('Location not found, validate the location name')}
            bodega = location.complete_name
            producto_variante = self.env['product.product'].sudo().search([('default_code', '=', product_data['nameProd'].rstrip())])
            if 'variantList' in product_data:
                producto = self.env['product.product'].sudo().search([('default_code', '=', product_data['nameProd'].rstrip())])
                if not producto:
                    return {'error': _('Product not found, check de SKU code: ' + product_data['nameProd'])}
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
                    return {'error': _(f'No product found, validate the variants and attributes sent. Variants sent in Henutsen: ({cadena}). Available options: {cadena_odoo}')}
                else:
                    return {'error': _(f"Product not found, check de SKU code in Odoo: {product_data['nameProd']}")}
            if not product_data['batchNumber']:
                ajuste_id = self.env['stock.quant'].sudo().search([('location_id.complete_name', '=', bodega),('product_id.id', '=', producto_variante.id)], limit=1)
            else:
                ajuste_id = self.env['stock.quant'].sudo().search([('location_id.complete_name', '=', bodega),('product_id.id', '=', producto_variante.id),('lot_id.name', '=', product_data['batchNumber'])], limit=1)
                if not ajuste_id:
                    ajuste_id = self.env['stock.quant'].sudo().search([('location_id.complete_name', '=', bodega),('product_id.id', '=', producto_variante.id)], limit=1)
            if not ajuste_id:
                return {'error': _(f'Location {bodega} does not have stock of product {producto_variante.name}')}
            quant = ajuste_id.available_quantity

            if not quant:
                return {'error': _('Location does not have stock of product')}

            if quant < product_data['quantity']:
                return {'error': _('The quantity to adjust is greater than the current quantity of stock in the location, validate if you are sending only the missing ones')}
            stock_con_diferencia = quant - product_data['quantity']
            # Ajustar la cantidad en el quant
            ajuste_id.sudo().write({'id_ajuste': data['idAdjustment'], 'inventory_quantity': stock_con_diferencia, 'inventory_diff_quantity': - product_data['quantity']})
        return {'success': _(f'Adjustment of products in the location {bodega} successful!')}
    
    # INFO: Método que aplica los ajustes de inventario en Odoo y los envía a Henutsen en caso de que el ajuste haya sido creado desde allá
    def action_apply_inventory(self):

        for quant in self:
            variant_list = []
            data = []
            # Si el ajuste tiene un ID de ajuste, se envía la información a Henutsen, en caso contrario, solo se ajusta en Odoo
            if quant.id_ajuste:
                config_params = quant.get_config_params()
                url_adjustment = config_params['url_adjustment']
                bearer_token = config_params['bearer_token']
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
                        # english: 
                        raise ValidationError(_("Error sending information to Henutsen. Details: " + response.text))
            # Una vez que se haya enviado la información a Henutsen, se ajusta en Odoo y se limpia el campo de ID de ajuste 
            quant.id_ajuste = False
        res = super(StockQuant, self).action_apply_inventory()
        return res
    
    # INFO: Método que limpia el campo de ID de ajuste en caso de que se cancele el ajuste, para que no se envíe a Henutsen
    def action_clear_inventory_quantity(self):
        res = super(StockQuant, self).action_clear_inventory_quantity()
        self.id_ajuste = False
        return res
    
    def get_config_params(self):
        config_params = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1)
        if not config_params.api_key or not config_params.email_henutsen or not config_params.url_bearer or not config_params.url_adjustment:

            raise ValidationError(_('Faltan datos en la configuración de Henutsen, valide que todos los campos estén completos, si no tiene acceso, solicitele a un administrador que actualice esta información'))
        if os.environ.get("ODOO_STAGE") == 'production':
            bearer_token = config_params.bearer_token
            if not bearer_token:
                bearer_token = config_params.get_bearer()
            return {
                'url_adjustment': config_params.url_adjustment,
                'bearer_token': bearer_token,
            }
        else:
            bearer_token = config_params.bearer_token_qa
            if not bearer_token:
                bearer_token = config_params.get_bearer_qa()
            return {
                'url_adjustment': config_params.url_adjustment_qa,
                'bearer_token': bearer_token,
            }
    
    def get_bearer(self):
        config_params = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1)
        if os.environ.get("ODOO_STAGE") == 'production':
            return config_params.get_bearer()
        else:
            return config_params.get_bearer_qa()