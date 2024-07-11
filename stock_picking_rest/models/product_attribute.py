from odoo import _, api, fields, models
import json, requests
import os
import logging

_logger = logging.getLogger(__name__)

class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    def send_variants_to_henutsen(self):
        all_records = self.sudo().search([])
        attributes_json = []
        for record in all_records:
            attribute_dict = {
                'name': record.name,
                'valuesVariants': [line.name for line in record.value_ids]
            }
            attributes_json.append(attribute_dict)
        json_henutsen = json.dumps(attributes_json)
        config = self.get_config_params()             
        bearer_token = config['bearer_token']
        service_url = config['url_variants']      
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + bearer_token
            }
        response = requests.post(service_url, headers=headers, data=json_henutsen)

        if response.status_code != 200:
            bearer_token = self.get_bearer()
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + bearer_token
            }
            response = requests.post(service_url, headers=headers, data=json_henutsen)
            if response.status_code == 200:
                _logger.info(_('Variants sent successfully'))
            else:
                _logger.warning(_(f'Error sending variants to Henutsen: {response.text}'))
        else:
            _logger.info(_('Variants sent successfully'))
    
    def get_config_params(self):
        config_params = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1)
        if not config_params.api_key or not config_params.email_henutsen or not config_params.url_bearer or not config_params.url_adjustment:
            pass
        if os.environ.get("ODOO_STAGE") == 'production':
            bearer_token = config_params.bearer_token
            if not bearer_token:
                bearer_token = config_params.get_bearer()
            return {
                'url_variants': config_params.url_variants,
                'bearer_token': bearer_token,
            }
        else:
            bearer_token = config_params.bearer_token_qa
            if not bearer_token:
                bearer_token = config_params.get_bearer_qa()
            return {
                'url_variants': config_params.url_variants_qa,
                'bearer_token': bearer_token,
            }

    def get_bearer(self):
        config_params = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1)
        if os.environ.get("ODOO_STAGE") == 'production':
            return config_params.get_bearer()
        else:
            return config_params.get_bearer_qa()