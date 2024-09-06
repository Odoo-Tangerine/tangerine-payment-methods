from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def generate_qr_code(self):
        self.ensure_one()
        if self.company_id.country_code == 'VN' and self.qr_code_method == 'sepay_qr':
            return f'https://qr.sepay.vn/img?acc={self.partner_bank_id.acc_number}&bank={self.partner_bank_id.bank_id.code}&amount={self.amount_residual}&des={self.invoice_origin}'
        return super(AccountMove, self).generate_qr_code()
