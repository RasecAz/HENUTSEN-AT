from odoo import _, api, fields, models

class ResUsers (models.Model):
    _inherit = 'res.users'

# --------------------------------------------------------------------------------
# CAMPOS
# --------------------------------------------------------------------------------

    # INFO: Campo para indicar si el usuario está autorizado a aprobar ordenes de venta a terceros
    is_approve_user = fields.Boolean(
        string = '¿Autorizado a aprobar ordenes de venta a terceros?',
        default = False,
    )