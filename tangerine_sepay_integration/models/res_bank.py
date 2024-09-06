from odoo import models, api, _


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    @api.model
    def _get_available_qr_methods(self):
        result = super()._get_available_qr_methods()
        result.append(('sepay_qr', _('QR Code VietQR - SePay'), 50))
        return result
