from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import formatLang

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    main_location_id = fields.Many2one(
        'stock.location',
        string = "Main location",
        readonly = True,
    )

    update_buttons_visibility = fields.Boolean(
        string = "Update buttons visibility",
        compute = '_compute_update_buttons_visibility',
    )

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

    def recompute_price_lines_and_stock(self):
        location = self.main_location_id if self.main_location_id else self.compute_main_location_id()
        for line in self.order_line:
            line.compute_price_in_pricelist()
            line.compute_stock_lines(location)
            line.onchange_product_qty()
    
    def compute_main_location_id(self):
        main_company = self.company_id.parent_id.id or self.company_id.id
        location = self.env['stock.location'].sudo().search([
        ('company_id', '=', main_company),
        ('name', '=', 'Existencias')
        ], limit=1)
        self.main_location_id = location.id if location else False
        return location
    
    @api.onchange('partner_id','order_line')
    def _compute_update_buttons_visibility(self):
        for order in self:
            order.update_buttons_visibility = False
            if order.partner_id and order.order_line:
                order.update_buttons_visibility = True

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

# --------------------------------------------------------------------------------
# CAMPOS
# --------------------------------------------------------------------------------

    main_location_id = fields.Many2one(
        'stock.location',
        string = "Main location",
        readonly = True,
    )

    price_in_pricelist = fields.Monetary(
        string = "Price in pricelist",
        compute = 'compute_price_in_pricelist',
    )

    stock_in_warehouse = fields.Float(
        string = "Stock in warehouse",
        compute = 'compute_stock_lines',
    )
    total_inline = fields.Monetary(
        string = "Total in line",
        compute='_compute_total_inline'
    )
    stock_state = fields.Selection(
        selection = [
            ('available', 'avaliable'),
            ('not_available', 'not avaliable'),
            ('in_zero', 'in zero'),
            ('not_calculated', 'not calculated'),
        ],
        default = 'not_calculated',
    )
# --------------------------------------------------------------------------------
# METODOS
# --------------------------------------------------------------------------------
    # INFO: Método para calcular el precio en lista del producto (IMPORTANTE: la lista debe estar asociada a la sucursal de la compañía, más no a la compañía en sí)
    @api.depends('product_id', 'product_qty')
    def compute_price_in_pricelist(self):
        for line in self:
            pricelist = line.order_id.company_id.partner_id.property_product_pricelist
            product = line.product_id
            if not product.attribute_line_ids:
                price_in_pricelist = line.env['product.pricelist.item'].sudo().search([('pricelist_id', '=', pricelist.id),('product_tmpl_id', '=', product.product_tmpl_id.id)], limit=1).fixed_price
            else:
                price_in_pricelist = line.env['product.pricelist.item'].sudo().search([('pricelist_id', '=', pricelist.id),('product_id', '=', product.id)], limit=1).fixed_price
            if not price_in_pricelist:
                price_in_pricelist = line.env['product.pricelist.item'].sudo().search([('pricelist_id', '=', pricelist.id),('product_tmpl_id', '=', product.product_tmpl_id.id)], limit=1).fixed_price
            if not price_in_pricelist:
                price_in_pricelist = 0
            line.price_in_pricelist = price_in_pricelist
    
    @api.depends('product_id', 'product_qty')
    def compute_stock_lines(self, location=False):
        if not location:
            location = self.order_id.main_location_id if self.order_id.main_location_id else self.order_id.compute_main_location_id()
        for line in self:
            product = line.product_id
            if location:
                location_ids = location.sudo().child_internal_location_ids.ids
                stock_data = self.env['stock.quant'].sudo().read_group(
                    [('location_id', 'in', location_ids), ('product_id', '=', product.id)],
                    ['product_id', 'quantity'],
                    ['product_id']
                )
                stock_quant = sum(stock['quantity'] for stock in stock_data) if stock_data else 0
            else:
                stock_quant = 0

            line.stock_in_warehouse = stock_quant
            self.onchange_product_qty()

    @api.depends('product_qty', 'price_in_pricelist')
    def _compute_total_inline(self):
        for line in self:
            line.total_inline = line.product_qty * line.price_in_pricelist
            
    # INFO: Método para validar que la cantidad de productos ingresados en la orden de compra, no sea mayor al stock en planta
    def onchange_product_qty(self):
        for line in self:
            if line.product_qty > line.stock_in_warehouse:
                line.stock_state = 'not_available'
            elif line.product_qty == line.stock_in_warehouse:
                line.stock_state = 'in_zero'
            else:
                line.stock_state = 'available'
                