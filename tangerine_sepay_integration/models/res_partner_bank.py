from odoo import models, api, _
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    def _get_qr_code_generation_params(self, qr_method, amount, currency, debtor_partner, free_communication, structured_communication):
        if qr_method == 'sepay_qr':
            return {}
        return super()._get_qr_code_generation_params(qr_method, amount, currency, debtor_partner, free_communication, structured_communication)

    @api.model
    def _get_available_qr_methods(self):
        result = super()._get_available_qr_methods()
        result.append(('sepay_qr', _('QR Code VietQR - SePay'), 50))
        return result

    def build_vietqr_code(self, amount, order):
        self.ensure_one()
        if not self.acc_number or not self.bank_id.code or not amount or amount <= 0 or not order:
            return False
        return f'https://qr.sepay.vn/img?acc={self.acc_number}&bank={self.bank_id.code}&amount={amount}&des={order}&template=compact'