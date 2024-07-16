from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import formatLang

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.depends_context('lang')
    @api.depends('order_line.taxes_id', 'order_line.price_subtotal', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals(self):
        res = super(PurchaseOrder, self)._compute_tax_totals()
        for order in self:

            amount_total = 0
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            for line in order_lines:
                amount_total += line.total_inline
            order.tax_totals['amount_total'] = amount_total
            order.tax_totals['amount_untaxed'] = amount_total
            order.tax_totals['formatted_amount_total'] = formatLang(self.env, amount_total, currency_obj=order.currency_id or order.company_id.currency_id)
            order.tax_totals['formatted_amount_untaxed'] = formatLang(self.env, amount_total, currency_obj=order.currency_id or order.company_id.currency_id)
            order.amount_total = amount_total

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

# --------------------------------------------------------------------------------
# CAMPOS
# --------------------------------------------------------------------------------

    price_in_pricelist = fields.Monetary(
        string = "Price in pricelist",
        compute='_compute_price_in_pricelist'
    )

    stock_in_warehouse = fields.Float(
        string = "Stock in warehouse",
        compute='_compute_price_in_pricelist'
    )
    total_inline = fields.Monetary(
        string = "Total in line",
        compute='_compute_total_inline'
    )
    stock_state = fields.Selection(
        selection = [
            ('available', 'avaliable'),
            ('not_available', 'not avaliable'),
            ('in_zero', 'in zero')
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
            pricelist = line.order_id.company_id.partner_id.property_product_pricelist
            product = line.product_id
            if not product.attribute_line_ids:
                price_in_pricelist = line.env['product.pricelist.item'].search([('pricelist_id', '=', pricelist.id),('product_tmpl_id', '=', product.product_tmpl_id.id)], limit=1).fixed_price
            else:
                price_in_pricelist = line.env['product.pricelist.item'].search([('pricelist_id', '=', pricelist.id),('product_id', '=', product.id)], limit=1).fixed_price
            if not price_in_pricelist:
                price_in_pricelist = line.env['product.pricelist.item'].search([('pricelist_id', '=', pricelist.id),('product_tmpl_id', '=', product.product_tmpl_id.id)], limit=1).fixed_price
            if not price_in_pricelist:
                price_in_pricelist = 0
            line.price_in_pricelist = price_in_pricelist
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

    def _compute_total_inline(self):
        for line in self:
            line.total_inline = line.product_qty * line.price_in_pricelist
            
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
                