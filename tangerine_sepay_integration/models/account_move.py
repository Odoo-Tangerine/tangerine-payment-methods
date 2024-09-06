from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _generate_qr_code(self, silent_errors=False):
        self.ensure_one()
        if self.company_id.country_code == 'VN' and self.qr_code_method == 'sepay_qr':
            return f'https://qr.sepay.vn/img?acc={self.partner_bank_id.acc_number}&bank={self.partner_bank_id.bank_id.code}&amount={self.amount_residual}&des={self.invoice_origin}&template=compact'
        return super()._generate_qr_code(silent_errors)
