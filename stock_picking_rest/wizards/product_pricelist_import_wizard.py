from odoo import _, api, fields, models
import base64
import xlrd
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ProductPricelistImport(models.TransientModel):
    _name = 'product.pricelist.import.wizard'
    _description = 'Product Pricelist Import'

    file = fields.Binary('File', required=True)
    file_name = fields.Char('File Name', required=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', required=False)

    def import_pricelist(self):
        self.ensure_one()
        if not self.pricelist_id:
            pricelist = self.env['product.pricelist'].browse(self.env.context.get('active_id'))
        else:
            pricelist = self.pricelist_id
        if not self.file:
            raise UserError(_('File not detected. Please select a file to import.'))
        if not self.file_name.endswith('.xlsx') and not self.file_name.endswith('.xls'):
            raise UserError(_('File must be an Excel file.'))
        pricelist_name = pricelist.name
        if not self.file_name.startswith(pricelist_name):
            raise UserError(_('This file does not correspond to the selected pricelist.'))
        data = base64.b64decode(self.file)
        workbook = xlrd.open_workbook(file_contents=data)
        sheet = workbook.sheet_by_index(0)
        product_obj = self.env['product.product']
        for row in range(1, sheet.nrows):
            code = str(int(sheet.cell(row, 0).value) if isinstance(sheet.cell(row, 0).value, float) else sheet.cell(row, 0).value) 
            price = sheet.cell(row, 1).value
            # Buscar todos los productos que coincidan con el código
            products = product_obj.search([('default_code', '=', code)])
            if not products:
                _logger.warning(f'No existe el producto {code}, verifique la lista y el producto en Odoo')
            for product in products:
                # Filtrar los ítems de la lista de precios que correspondan a cada producto
                items_in_pricelist = pricelist.item_ids.filtered(lambda item: item.product_tmpl_id.id == product.product_tmpl_id.id)
                if not items_in_pricelist:
                    self.env['product.pricelist.item'].create({
                        'pricelist_id': pricelist.id,
                        'product_tmpl_id': product.product_tmpl_id.id,
                        'fixed_price': price,
                        'min_quantity': 0,
                    })
                else:
                    for item in items_in_pricelist:
                        item.fixed_price = price
        return True
    
    @api.model
    def default_get(self, fields):
        res = super(ProductPricelistImport, self).default_get(fields)
        pricelist = self.env['product.pricelist'].browse(self.env.context.get('active_id'))
        res['pricelist_id'] = pricelist.id if pricelist else None
        return res