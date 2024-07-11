from odoo import _, fields, models

class ResUsers (models.Model):
    _inherit = 'res.users'

# --------------------------------------------------------------------------------
# CAMPOS
# --------------------------------------------------------------------------------

    # INFO: Campo para indicar si el usuario está autorizado a aprobar ordenes de venta a terceros
    is_approve_user = fields.Boolean(
        string = '¿Is Pursache approver user?',
        default = False,
    )