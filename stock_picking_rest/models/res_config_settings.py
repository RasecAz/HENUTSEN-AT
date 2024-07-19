from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    recieve_packing_from_henutsen = fields.Boolean(
        "Recieve Packing From Henutsen",
        help="If checked, the system will be able to recieve packing from Henutsen",
        default=True
    )

    send_packing_to_henutsen = fields.Boolean(
        "Send Packing To Henutsen",
        help="If checked, the system will be able to send packing to Henutsen",
        default=False
    )

    easy_import_pricelist = fields.Boolean(
        "Easy Import Pricelist",
        help="If checked, the system will be enable the easy import pricelist mode",
        default=False
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res['recieve_packing_from_henutsen'] = self.env['ir.config_parameter'].sudo().get_param('recieve_packing_from_henutsen')
        res['send_packing_to_henutsen'] = self.env['ir.config_parameter'].sudo().get_param('send_packing_to_henutsen')
        res['easy_import_pricelist'] = self.env['ir.config_parameter'].sudo().get_param('easy_import_pricelist')
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('recieve_packing_from_henutsen', self.recieve_packing_from_henutsen)
        self.env['ir.config_parameter'].sudo().set_param('send_packing_to_henutsen', self.send_packing_to_henutsen)
        self.env['ir.config_parameter'].sudo().set_param('easy_import_pricelist', self.easy_import_pricelist)