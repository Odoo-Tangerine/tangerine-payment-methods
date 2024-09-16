from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _generate_qr_code(self, silent_errors=False):
        self.ensure_one()
        if self.company_id.country_code == 'VN' and self.qr_code_method == 'sepay_qr':
            return self.partner_bank_id.build_vietqr_code(self.amount_residual, self.invoice_origin)
        return super()._generate_qr_code(silent_errors)
