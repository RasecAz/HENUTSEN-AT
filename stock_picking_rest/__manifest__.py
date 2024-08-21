
# -*- coding: utf-8 -*-
# ---------------------------------
# Henutsen RFID System
# ---------------------------------
# This module provides an RFID integration in Odoo. In addition to some adjustments and validations in the stock, sale and purchase modules, all under Aristextil's request.
# The module includes functionalities to the mentioned base modules, provides custom views and reports to facilitate the management of these elements.
# It depends on the 'base', 'stock', 'product', 'sale' and 'purchase' modules for its correct operation.
# Version: 17.0.0.1
{
    'name': "Henutsen RFID System",

    'summary': "Module for Henutsen-RFID integration in Odoo",

    'author': "Audisoft Consulting",
    'website': "https://www.audisoft.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Inventory',
    'version': '17.0.2.37',

    'depends': ['base','stock','contacts', 'sale', 'purchase'],

    'data': [
        # Security
        'security/ir.model.access.csv',

        # Views
        'views/res_config_settings_view.xml',
        'views/stock_inherit_view.xml',
        'views/stock_quant_package_view.xml',
        'views/config_henutsen_view.xml',
        'views/purchase_order_view.xml',
        'views/res_users_view.xml',
        'views/sale_order_view.xml',
        'views/product_template_view.xml',
        'views/product_pricelist_view.xml',
        'views/stock_move_line_view.xml',

        # Cron jobs
        'data/product_attribute_cron.xml',

        # Wizards
        'wizards/product_pricelist_import_wizard_view.xml',

        # Reports
        'reports/report_deliveryslip.xml',
        'reports/report_stockpicking_operations.xml',
    ],
    'application': True,
    'license': 'LGPL-3',
}

