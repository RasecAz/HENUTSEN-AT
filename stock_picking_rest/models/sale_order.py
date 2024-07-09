from odoo import _, api, fields, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

# --------------------------------------------------------------------------------
# CAMPOS
# --------------------------------------------------------------------------------

    state = fields.Selection(selection_add=[
        ('pending', 'Pending Approval'),
    ])
    
    button_confirm_invisible = fields.Boolean(
        compute='_compute_button_confirm_invisible'
    )

    button_approve_invisible = fields.Boolean(
        compute='_compute_button_approve_invisible'
    )

# --------------------------------------------------------------------------------
# METODOS
# --------------------------------------------------------------------------------

    # INFO: Método que define si el botón de aprobar orden de venta es visible o no
    #   No es visible si:
    #       - El destino de la orden de venta es una sucursal.
    #       - El usuario está autorizado a aprobar ordenes de venta a terceros y la orden de venta no está en estado 'draft' o 'sent'.
    @api.depends('name', 'state', 'partner_id')
    def _compute_button_approve_invisible(self):
        for order in self:
            es_sucursal = False
            for sucursal in order.company_id.child_ids:
                sucursales = sucursal.name
                if sucursales == order.partner_id.name:
                    es_sucursal = True
            if es_sucursal:
                order.button_approve_invisible = True
            elif not order.env.user.is_approve_user and order.state == 'draft' or not order.env.user.is_approve_user and order.state == 'sent':
                order.button_approve_invisible = False
            else:
                order.button_approve_invisible = True
    
    # INFO: Método para pasar la orden de venta a estado 'Pendiente de Aprobación'
    def action_approve(self):
        for order in self:
            order.state = 'pending'

    # INFO: Método que define si el botón de confirmar orden de venta es visible o no
    #   Es visible si:
    #       - El destino de la orden de venta es una sucursal y la orden de venta no está en estado 'sale'.
    #       - El usuario está autorizado a aprobar ordenes de venta a terceros y la orden de venta está en estado 'pending', 'draft' o 'sent'.
    @api.depends('name', 'state', 'partner_id')
    def _compute_button_confirm_invisible(self):
        for order in self:
            es_sucursal = False
            for sucursal in order.company_id.child_ids:
                sucursales = sucursal.name
                if sucursales == order.partner_id.name:
                    es_sucursal = True
            if es_sucursal and order.state != 'sale':
                order.button_confirm_invisible = False
            elif order.env.user.is_approve_user and order.state == 'pending' or order.env.user.is_approve_user and order.state == 'draft' or order.env.user.is_approve_user and order.state == 'sent':
                order.button_confirm_invisible = False
            else:
                order.button_confirm_invisible = True

    # INFO: Este método es llamado por el botón "Confirmar" de la orden de venta, si el estado de la orden de venta no está en 'draft', 'sent' o 'pending', no se puede confirmar.
    def _can_be_confirmed(self):
        self.ensure_one()
        return self.state in {'draft', 'sent', 'pending'}
