from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import requests


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
        string = 'Url Ajuste inventarios'
    )
    url_variants = fields.Char(
        string = 'Url Variantes'
    )
    api_key = fields.Text(
        string = 'Api Key usuario'
    )
    email_henutsen = fields.Char(
        string = 'Email Henutsen'
    )
    bearer_token = fields.Text(
        string = 'Bearer Token',
        readonly=True
    )
    last_update = fields.Datetime(
        string = 'Última actualización',
        readonly=True
    )
    state = fields.Selection(
        [
            ('draft', 'Borrador'),
            ('done', 'Guardado')
        ],
        default='draft'
    )

# --------------------------------------------------------------------------------
# METODOS
# --------------------------------------------------------------------------------

    # INFO: Método para guardar la configuración de los webservices
    def save_data(self):
        self.ensure_one()
        if not self.url_bearer or not self.url_picking or not self.url_packing or not self.url_adjustment or not self.api_key or not self.email_henutsen:
            raise ValidationError('Faltan datos para guardar la configuración')
        self.write({
            'url_bearer': self.url_bearer,
            'url_picking': self.url_picking,
            'url_packing': self.url_packing,
            'url_adjustment': self.url_adjustment,
            'url_variants': self.url_variants,
            'api_key': self.api_key,
            'email_henutsen': self.email_henutsen,
            'last_update': fields.Datetime.now()
        })
        self.state = 'done'

    # INFO: Método que se ejecuta con el botón "Generar Bearer Token", para obtener el token de autorización
    def get_bearer(self):
        if not self.api_key or not self.email_henutsen or not self.url_bearer:
            raise ValidationError('Faltan datos para obtener el token')
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
            self.write({'bearer_token': "Error " + str(response.status_code) + ". Respuesta: " + response.text})

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
        defaults['url_adjustment'] = config.url_adjustment if config else None
        defaults['url_variants'] = config.url_variants if config else None
        defaults['state'] = config.state if config else 'draft'
        return defaults
    
    # INFO: Método que modifica el estado de la configuración de "Confirmado" a "Borrador"
    def modify_config(self):
        self.state = 'draft'