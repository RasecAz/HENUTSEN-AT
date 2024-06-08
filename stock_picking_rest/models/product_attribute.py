from odoo import _, api, fields, models
import json, requests

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
        config = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1)
        if not config:
           pass
        else:             
            bearer_token = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).bearer_token
            if not bearer_token:
                config.get_bearer()
                bearer_token = config.bearer_token
            service_url = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1).url_variants
            if not service_url:
                pass
            else:      
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + bearer_token
                    }
                response = requests.post(service_url, headers=headers, data=json_henutsen)

                if response.status_code != 200:
                    config.get_bearer()
                    bearer_token = config.bearer_token
                    headers = {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + bearer_token
                    }
                    response = requests.post(service_url, headers=headers, data=json_henutsen)
                    if response.status_code == 200:
                        print(response.text)
                else:
                    print(response.text)    
