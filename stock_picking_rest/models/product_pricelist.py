from odoo import _, api, fields, models

class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    easy_import_available = fields.Boolean(
        string='Easy Import Available',
        default=False,
        compute='_compute_easy_import_available',
    )

    def open_pricelist_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Import Pricelist'),
            'res_model': 'product.pricelist.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }
    @api.depends('easy_import_available')
    def _compute_easy_import_available(self):
        for pricelist in self:
            pricelist.easy_import_available = self.env['res.config.settings'].sudo().get_values().get('easy_import_pricelist')