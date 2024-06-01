from odoo import _, api, fields, models

class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

# ------------------------------------------------------------------------------------------------
# CAMPOS
# ------------------------------------------------------------------------------------------------

    # INFO: Campo para indicar el peso total de la caja (Para el vale de entrega)
    package_weight = fields.Float(
        string='Peso total (Kg)',
        help='Ingrese el peso en kilogramos de la caja, posterior al embalaje de los productos',
    )