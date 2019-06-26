# -*- coding: utf-8 -*-
{
    'name': "Patti Report Xlsx",

    'summary': """
        Patti Report Xlsx""",

    'description': """
        This module allows you to print patti report.
    """,

    'author': "Success Metrics",
    'website': "http://www.successmteric.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'purchase', 'account_invoicing', 'account'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}