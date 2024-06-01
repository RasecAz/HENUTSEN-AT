
# -*- coding: utf-8 -*-
# ---------------------------------
# Módulo Henutsen RFID - Aristextil
# ---------------------------------
# Este módulo proporciona una integración de RFID en Odoo. Además de algunos ajustes y validaciones en los módulos de stock, sale y purchase, todo bajo solicitud de Aristextil.
# El módulo incluye funcionalidades a los módulos base mencionados, proporciona vistas personalizadas y reportes para facilitar la gestión de estos elementos.
# Depende de los módulos 'base', 'stock', 'product', 'sale' y 'purchase' para su correcto funcionamiento.
# Autor: Wilson Contreras - Audisoft Consulting
# Versión: 17.0.0.1
{
    'name': "Henutsen RFID - Aristextil",

    'summary': "Módulo para la integración de RFID en Odoo",

    'author': "Wilson Contreras - Audisoft Consulting",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','stock','contacts', 'sale', 'purchase'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/stock_inherit_view.xml',
        'views/stock_quant_package_view.xml',
        'views/config_henutsen_view.xml',
        'views/purchase_order_view.xml',
        'views/res_users_view.xml',
        'views/sale_order_view.xml',
        'views/product_template_view.xml',
        'reports/report_deliveryslip.xml',
    ],
    'license': 'LGPL-3',
}

