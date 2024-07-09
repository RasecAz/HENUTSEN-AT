from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import requests
import os


class ConfigHenutsenWizard(models.Model):
    _name = 'config.henutsen'
    _description = 'Config Henutsen'
    _rec_name = 'last_update'

# --------------------------------------------------------------------------------
# CAMPOS
# --------------------------------------------------------------------------------

    url_bearer = fields.Char(
        string = 'Url Bearer Token'
    )
    url_picking = fields.Char(
        string = 'Url Picking'
    )
    url_packing = fields.Char(
        string = 'Url Packing'
    )
    url_adjustment = fields.Char(
        string = 'Url inventories adjustment'
    )
    url_variants = fields.Char(
        string = 'Url Variants'
    )
    url_cg1 = fields.Char(
        string = 'Url CG1'
    )
    url_product = fields.Char(
        string = 'Url Product'
    )
    api_key = fields.Text(
        string = 'Api user key'
    )
    email_henutsen = fields.Char(
        string = 'Email Henutsen'
    )
    bearer_token = fields.Text(
        string = 'Bearer Token',
        readonly=True
    )
    special_branch = fields.Text(
        string = 'Special branches',
        help='Enter the identification numbers of the special stores, stores registered as branches in Odoo, but that for CG1 are third parties. NOTE: Enter the id as it is registered in the contact (consider the verification digit) separated by comma(,), without spaces. Example: 123-1,231,321-0,432,543'
    )
    url_bearer_qa = fields.Char(
    string = 'Url Bearer Token QA'
    )
    url_picking_qa = fields.Char(
        string = 'Url Picking QA'
    )
    url_packing_qa = fields.Char(
        string = 'Url Packing QA'
    )
    url_adjustment_qa = fields.Char(
        string = 'Url inventories adjustment QA'
    )
    url_variants_qa = fields.Char(
        string = 'Url Variants QA'
    )
    url_cg1_qa = fields.Char(
        string = 'Url CG1 QA'
    )
    url_product_qa = fields.Char(
        string = 'Url Product QA'
    )
    api_key_qa = fields.Text(
        string = 'Api user Key QA'
    )
    email_henutsen_qa = fields.Char(
        string = 'Email QA Henutsen'
    )
    bearer_token_qa = fields.Text(
        string = 'Bearer Token QA',
        readonly=True
    )
    special_branch_qa = fields.Text(
        string = 'Special branches QA',
    )

    last_update = fields.Datetime(
        string = 'Last update',
        readonly=True
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('done', 'Done')
        ],
        default='draft'
    )
    is_production = fields.Boolean(
        string = 'Is production',
        default=True
    )

# --------------------------------------------------------------------------------
# METODOS
# --------------------------------------------------------------------------------

    # INFO: Método para guardar la configuración de los webservices
    def save_data(self):
        self.ensure_one()
        if not self.url_bearer or not self.url_picking or not self.url_packing or not self.url_adjustment or not self.api_key or not self.email_henutsen:
            raise ValidationError(_('Missing data to save the configuration'))
        self.write({
            'url_bearer': self.url_bearer,
            'url_picking': self.url_picking,
            'url_packing': self.url_packing,
            'url_adjustment': self.url_adjustment,
            'url_variants': self.url_variants,
            'url_cg1': self.url_cg1,
            'url_product': self.url_product,
            'api_key': self.api_key,
            'special_branch': self.special_branch,
            'email_henutsen': self.email_henutsen,
            'last_update': fields.Datetime.now(),
            'url_bearer_qa': self.url_bearer_qa,
            'url_picking_qa': self.url_picking_qa,
            'url_packing_qa': self.url_packing_qa,
            'url_adjustment_qa': self.url_adjustment_qa,
            'url_variants_qa': self.url_variants_qa,
            'url_cg1_qa': self.url_cg1_qa,
            'url_product_qa': self.url_product_qa,
            'api_key_qa': self.api_key_qa,
            'special_branch_qa': self.special_branch_qa,
            'email_henutsen_qa': self.email_henutsen_qa,
        })
        self.state = 'done'

    # INFO: Método que se ejecuta con el botón "Generar Bearer Token", para obtener el token de autorización
    def get_bearer(self):
        if not self.api_key or not self.email_henutsen or not self.url_bearer:
            raise ValidationError(_('Missing data to get the token'))
        if self.bearer_token:
            self.bearer_token = False
        api_key = self.api_key
        email = self.email_henutsen
        bearer_url = self.url_bearer
        self.api_key = api_key
        token_url = f'{bearer_url}/{email}?apiKey={api_key}'

        # Envío de la solicitud y obtención de la respuesta
        response = requests.post(token_url)

        # Verificación del código de estado
        if response.status_code == 200:
            # La solicitud fue exitosa, procesa la respuesta JSON
            response_json = response.json()
            bearer_token = response_json["accessToken"]  # accesToken contiene el token
            self.write({'bearer_token': bearer_token})
        else:
            # La solicitud falló, maneja el error
            self.write({'bearer_token': "Error " + str(response.status_code) + ". Response: " + response.text})
            bearer_token = "Error " + str(response.status_code) + ". Response: " + response.text
        return bearer_token
    
    def get_bearer_qa(self):
        if not self.api_key_qa or not self.email_henutsen_qa or not self.url_bearer_qa:
            raise ValidationError(_('Missing data to get the QA token'))
        if self.bearer_token_qa:
            self.bearer_token_qa = False
        api_key = self.api_key_qa
        email = self.email_henutsen_qa
        bearer_url = self.url_bearer_qa
        self.api_key_qa = api_key
        token_url = f'{bearer_url}/{email}?apiKey={api_key}'

        # Envío de la solicitud y obtención de la respuesta
        response = requests.post(token_url)

        # Verificación del código de estado
        if response.status_code == 200:
            # La solicitud fue exitosa, procesa la respuesta JSON
            response_json = response.json()
            bearer_token = response_json["accessToken"]  # accesToken contiene el token
            self.write({'bearer_token_qa': bearer_token})
        else:
            # La solicitud falló, maneja el error
            self.write({'bearer_token_qa': "Error " + str(response.status_code) + ". Response: " + response.text})
            bearer_token = "Error " + str(response.status_code) + ". Response: " + response.text
        return bearer_token

    # INFO: Método que asigna los valores por defecto a los campos de la vista, al momento de ingresar
    @api.model
    def default_get(self, fields_list):
        config = self.env['config.henutsen'].sudo().search([], order='id desc', limit=1)
        defaults = super(ConfigHenutsenWizard, self).default_get(fields_list)
        defaults['url_bearer'] = config.url_bearer if config else None
        defaults['url_picking'] = config.url_picking if config else None
        defaults['url_packing'] = config.url_packing if config else None
        defaults['api_key'] = config.api_key if config else None
        defaults['email_henutsen'] = config.email_henutsen if config else None
        defaults['bearer_token'] = config.bearer_token if config else None
        defaults['id'] = config.id if config else None
        defaults['last_update'] = config.last_update if config else None
        defaults['special_branch'] = config.special_branch if config else None
        defaults['url_adjustment'] = config.url_adjustment if config else None
        defaults['url_variants'] = config.url_variants if config else None
        defaults['url_cg1'] = config.url_cg1 if config else None
        defaults['url_product'] = config.url_product if config else None
        defaults['url_bearer_qa'] = config.url_bearer_qa if config else None
        defaults['url_picking_qa'] = config.url_picking_qa if config else None
        defaults['url_packing_qa'] = config.url_packing_qa if config else None
        defaults['api_key_qa'] = config.api_key_qa if config else None
        defaults['email_henutsen_qa'] = config.email_henutsen_qa if config else None
        defaults['bearer_token_qa'] = config.bearer_token_qa if config else None
        defaults['special_branch_qa'] = config.special_branch_qa if config else None
        defaults['url_adjustment_qa'] = config.url_adjustment_qa if config else None
        defaults['url_variants_qa'] = config.url_variants_qa if config else None
        defaults['url_cg1_qa'] = config.url_cg1_qa if config else None
        defaults['url_product_qa'] = config.url_product_qa if config else None
        defaults['state'] = config.state if config else 'draft'
        return defaults
    
    # INFO: Método que modifica el estado de la configuración de "Confirmado" a "Borrador"
    def modify_config(self):
        self.state = 'draft'