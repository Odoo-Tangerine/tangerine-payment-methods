from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _generate_qr_code(self, silent_errors=False):
        self.ensure_one()
        if self.company_id.country_code == 'VN' and self.qr_code_method == 'sepay_qr' and self.payment_state in ['not_paid', 'partial', 'in_payment']:
            return self.partner_bank_id.build_vietqr_code(self.amount_residual, self.invoice_origin)
        return super()._generate_qr_code(silent_errors)

    qr_code_method = fields.Selection(
        string="Payment QR-code", copy=False,
        selection=lambda self: self.env['res.partner.bank'].get_available_qr_methods_in_sequence(),
        help="Type of QR-code to be generated for the payment of this invoice, "
             "when printing it. If left blank, the first available and usable method "
             "will be used.",
        default='sepay_qr'
    )
