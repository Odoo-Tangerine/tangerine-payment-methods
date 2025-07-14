# -*- coding: utf-8 -*-
{
    'name': 'Bank Information Vietnam',
    'summary': """Providing the latest API to synchronize banking information in Vietnam.""",
    'author': 'Long Duong Nhat',
    'category': 'Extra Tools',
    'support': 'odoo.tangerine@gmail.com',
    'version': '18.0.1.0',
    'depends': ['base'],
    'data': [
        'data/ir_cron.xml',
        'views/res_bank_views.xml'
    ],
    'images': ['static/description/thumbnail.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
    'post_init_hook': '_bank_post_init_hook',
}