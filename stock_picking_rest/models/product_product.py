from odoo import _, api, fields, models

class ProductProduct(models.Model):
    _inherit = 'product.product'

# --------------------------------------------------------------------------------
# CAMPOS
# --------------------------------------------------------------------------------

    name_rtrim = fields.Char(
        compute='_compute_name_rtrim', 
        store=True
    )

# --------------------------------------------------------------------------------
# METODOS
# --------------------------------------------------------------------------------

    # INFO: Método para quitar espacios en blanco a la derecha del nombre del producto
    @api.depends('name')
    def _compute_name_rtrim(self):
        for record in self:
            record.name_rtrim = record.name.rstrip() if record.name else ''