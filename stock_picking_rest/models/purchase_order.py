from odoo import api, fields, models
from odoo.exceptions import UserError

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

# --------------------------------------------------------------------------------
# CAMPOS
# --------------------------------------------------------------------------------

    price_in_pricelist = fields.Monetary(
        string = "Precio en lista",
        compute='_compute_price_in_pricelist'
    )

    stock_in_warehouse = fields.Float(
        string = "Stock en planta",
        compute='_compute_price_in_pricelist'
    )

    stock_state = fields.Selection(
        selection = [
            ('available', 'Disponible'),
            ('not_available', 'No disponible'),
            ('in_zero', 'En cero')
        ],
        default = 'available',
    )
# --------------------------------------------------------------------------------
# METODOS
# --------------------------------------------------------------------------------

    # INFO: Método para calcular el precio en lista del producto (IMPORTANTE: la lista debe estar asociada a la sucursal de la compañía, más no a la compañía en sí)
    @api.depends('product_id', 'product_qty')
    def _compute_price_in_pricelist(self):
        for line in self:
            stock_quant = 0
            stock_available = 0
            precio_en_lista = None
            pricelist = line.order_id.company_id.partner_id.property_product_pricelist
            product = line.product_id
            if pricelist and product:
                for item in pricelist.item_ids:
                    if item.product_tmpl_id.name == product.name:
                        precio_en_lista = item.fixed_price
                if not precio_en_lista:
                    line.price_in_pricelist = 0
                else:
                    line.price_in_pricelist = precio_en_lista
            else:
                line.price_in_pricelist = 0          
            main_company = line.company_id.parent_id.id
            if not main_company:
                location = self.env['stock.location'].sudo().search([('company_id', '=', line.company_id.id),('name', '=', 'Existencias')], limit=1)
            else:
                location = self.env['stock.location'].sudo().search([('company_id', '=', main_company),('name', '=', 'Existencias')], limit=1)
            for ubicacion in location.child_internal_location_ids:
                internal_location = ubicacion.complete_name
                stock = self.env['stock.quant'].sudo().search([('location_id.complete_name', '=', internal_location),('product_id.id', '=', product.id)])
                if not stock:
                    stock_available = 0
                else:
                    for stock in stock:
                        stock_available = stock.available_quantity
                        stock_quant += stock_available
            line.stock_in_warehouse = stock_quant

    # INFO: Método para validar que la cantidad de productos ingresados en la orden de compra, no sea mayor al stock en planta
    @api.onchange('product_qty', 'stock_in_warehouse')
    def _onchange_product_qty(self):
        for line in self:
            if line.product_qty > line.stock_in_warehouse:
                line.stock_state = 'not_available'
            elif line.product_qty == line.stock_in_warehouse:
                line.stock_state = 'in_zero'
            else:
                line.stock_state = 'available'
            
# decoration-danger="state not in ('done', 'cancel') and scheduled_date &lt; current_date"