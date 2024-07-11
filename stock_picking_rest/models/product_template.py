import os
import logging
import requests
import json

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

# --------------------------------------------------------------------------------
# METHODS
# --------------------------------------------------------------------------------

    def write (self, vals):
        product = super(ProductTemplate, self).write(vals)
        self.send_product_to_henutsen()
        return product

    def send_product_to_henutsen(self):
        self.ensure_one()
        config_params = self.get_config_params()
        url = config_params['url_product']
        bearer_token = config_params['bearer_token']
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {bearer_token}'
        }
        if not self.name or not self.default_code:
            return
        data = {
            'ProductSku': self.default_code,
            'Description': self.name
        }
        
        data_json = json.dumps(data)
        response = requests.post(url, headers=headers, data=data_json)

        if response.status_code == 200:
            _logger.info(f'Product {self.default_code} succesfully sent to Henutsen. Details: {response.text}')
            _logger.info(data)
        else:
            bearer_token = self.get_bearer()
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {bearer_token}'
            }
            response = requests.post(url, headers=headers, data=data_json)
            if response.status_code == 200:
                _logger.info(f'Product {self.default_code} succesfully sent to Henutsen. Details: {response.text}')
                _logger.info(data)
            else:
                _logger.warning(f'Error sending product {self.default_code} to Henutsen. Details: {response.text}')
                _logger.warning(data)
                _logger.warning(response.status_code)
            


    def get_config_params(self):
        config_params = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1)
        if not config_params.api_key or not config_params.email_henutsen or not config_params.url_bearer or not config_params.url_picking or not config_params.url_packing:
            raise ValidationError(_('Missing data in Henutsen configuration, validate that all fields are complete, if you do not have access, ask an administrator to update this information'))
        if os.environ.get("ODOO_STAGE") == 'production':
            bearer_token = config_params.bearer_token
            if not bearer_token:
                bearer_token = config_params.get_bearer()
            return {
                'url_product': config_params.url_product,
                'bearer_token': bearer_token,
            }
        else:
            bearer_token = config_params.bearer_token_qa
            if not bearer_token:
                bearer_token = config_params.get_bearer_qa()
            return {
                'url_product': config_params.url_product_qa,
                'bearer_token': bearer_token,
            }

    def get_bearer(self):
        config_params = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1)
        if os.environ.get("ODOO_STAGE") == 'production':
            return config_params.get_bearer()
        else:
            return config_params.get_bearer_qa()