{
    'name': 'SePay On Website',
    'version': '17.0.1.0',
    'category': 'Hidden',
    'summary': """The SePay On Website Module support QR code initialization on eCommerce. The module is an alternative solution to reduce dependencies when you do not need to use the eCommerce module (website_sale) in SePay Integration.""",
    'depends': ['tangerine_sepay_integration', 'website_sale'],
    'author': 'Long Duong Nhat',
    'support': 'odoo.tangerine@gmail.com',
    'data': [
        'views/website_sale_templates.xml'
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
