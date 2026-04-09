{
    'name': 'SePay Integration',
    'version': '18.0.1.0',
    'category': 'Accounting/Payment Providers',
    'summary': """The SePay Integration Module for Odoo enables instant payment authentication via SePay"s payment webhook. Automatic payment QR generation, transaction history recording, etc.""",
    'depends': ['payment', 'sale', 'tangerine_bank_sync'],
    'author': 'Long Duong Nhat',
    'support': 'odoo.tangerine@gmail.com',
    'data': [
        'data/payment_method_data.xml',
        'views/report_invoice_document.xml',
        'views/payment_custom_templates.xml',
    ],
    'images': ['static/description/thumbnail.png'],
    'license': 'OPL-1',
    'installable': True,
    'auto_install': False,
    'application': False,
}
