from odoo import _, api, fields, models

class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

# ------------------------------------------------------------------------------------------------
# CAMPOS
# ------------------------------------------------------------------------------------------------

    # INFO: Campo para indicar el peso total de la caja (Para el vale de entrega)
    package_weight = fields.Float(
        string='Total weight (Kg)',
        help='Insert the weight in kilograms of the box, after packaging the products',
    )