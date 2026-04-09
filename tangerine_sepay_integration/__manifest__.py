{
    'name': 'SePay Integration',
    'version': '15.0.1.0',
    'category': 'Accounting/Payment Providers',
    'summary': """The SePay Integration Module for Odoo enables instant payment authentication via SePay"s payment webhook. Automatic payment QR generation, transaction history recording, etc.""",
    'depends': ['payment', 'sale', 'tangerine_bank_sync'],
    'author': 'Long Duong Nhat',
    'website': 'https://github.com/long-dn',
    'support': 'odoo.tangerine@gmail.com',
    'data': [
        'data/payment_method_data.xml',
        'views/report_invoice_document.xml',
    ],
    'images': ['static/description/thumbnail.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
