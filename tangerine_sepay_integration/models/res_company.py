from odoo import models, fields


class Company(models.Model):
    _inherit = 'res.company'

    default_bank_account_id = fields.Many2one('res.partner.bank', string='Default Bank Account')
