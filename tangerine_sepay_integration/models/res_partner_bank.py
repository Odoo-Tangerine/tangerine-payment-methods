from odoo import models, api, _
from odoo.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    @api.model
    def _get_available_qr_methods(self):
        result = super()._get_available_qr_methods()
        result.append(('sepay_qr', _('QR Code VietQR - SePay'), 50))
        return result

    def build_vietqr_code(self, amount, order):
        self.ensure_one()
        if not self.acc_number:
            raise ValidationError(_('The account number of the bank account receive is required'))
        elif not self.bank_id.code:
            raise ValidationError(_('The bank code of the bank account receive is required'))
        elif not amount:
            raise ValidationError(_('The money is required'))
        elif not order:
            raise ValidationError(_('The reference code is required'))
        return f'https://qr.sepay.vn/img?acc={self.acc_number}&bank={self.bank_id.code}&amount={amount}&des={order}&template=compact'