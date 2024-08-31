import logging
from datetime import datetime, timedelta
from odoo.tools import ustr
from odoo.http import request, Controller, route

_logger = logging.getLogger(__name__)

MAP_INVOICE_TYPE_PARTNER_TYPE = {
    'out_invoice': 'customer',
    'out_refund': 'customer',
    'out_receipt': 'customer',
    'in_invoice': 'supplier',
    'in_refund': 'supplier',
    'in_receipt': 'supplier',
}


class SePayTrackingTransaction(Controller):
    @route('/webhook/v1/payment/sepay', type='json', auth='public', methods=['POST'])
    def sepay_callback(self):
        try:
            body = request.dispatcher.jsonrequest
            _logger.info(f'WEBHOOK SEPAY START - BODY: {body}')
            if not body.get('code') or not body.get('transferAmount'):
                _logger.error(f'WEBHOOK SEPAY ERROR: The value of field code is required.')
                return {'success': 400, 'message': 'The value of field code is required.'}
            order_id = request.env['sale.order'].sudo().search([('name', '=', body.get('code'))], limit=1)
            if not order_id:
                _logger.error(f'WEBHOOK SEPAY ERROR: The code not found.')
                return {'success': 404, 'message': 'The code not found.'}
            invoices = order_id.invoice_ids.filtered(lambda i: i.state == 'posted' and i.amount_residual > 0)
            if not invoices:
                _logger.error(f'WEBHOOK SEPAY ERROR: No invoice found with posted status and amount due.')
                return {'success': 404, 'error': '[Payment Webhook] - No invoice found with posted status and amount due'}
            journal_id = request.env['account.journal'].sudo().search([
                '&',
                '&',
                ('type', '=', 'bank'),
                ('company_id', '=', order_id.company_id.id),
                ('code', 'ilike', 'BNK%')
            ])
            if not journal_id:
                _logger.error(f'WEBHOOK SEPAY ERROR: Journal of the bank not found.')
                return {'success': 404, 'error': '[Payment Webhook] - Journal of the bank not found'}
            payment_method_id = request.env['account.payment.method'].sudo().search([
                ('payment_type', '=', 'inbound'),
                ('code', '=', 'electronic')
            ])
            if not payment_method_id:
                _logger.error(f'WEBHOOK SEPAY ERROR: Payment method electronic not found')
                return {'success': 404, 'error': '[Payment Webhook] - Payment method electronic not found'}
            amount = body.get('transferAmount', 0)
            for invoice in invoices.sorted(key=lambda i: i.amount_residual, reverse=True):
                residual_amount = invoice.amount_residual
                if residual_amount > 0:
                    payment_vals = {
                        'currency_id': invoice.currency_id.id,
                        'amount': min(residual_amount, amount),
                        'payment_type': 'inbound',
                        'partner_id': invoice.commercial_partner_id.id,
                        'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[invoice.move_type],
                        'ref': body.get('referenceCode'),
                        'payment_method_id': payment_method_id.id,
                        'journal_id': journal_id.id
                    }
                    if body.get('transactionDate'):
                        payment_vals.update({
                            'date': datetime.strptime(body.get('transactionDate'), '%Y-%m-%d %H:%M:%S')
                        })
                    payment = request.env['account.payment'].sudo().create(payment_vals)
                    payment.action_post()
                    line_id = payment.line_ids.filtered(lambda l: l.credit)
                    invoice.js_assign_outstanding_line(line_id.id)
                    amount -= residual_amount
                    message = f'''
                                Received payment webhook
                                <ul>
                                    <li>Total: {amount}</li>
                                    <li>Content: {body.get('content', '')}</li>
                                    <li>Reference: {body.get('referenceCode', '')}</li>
                                    <li>Time: {datetime.now() + timedelta(hours=7)}</li>
                                </ul>
                            '''
                    invoice.message_post(body=message)
                if amount <= 0:
                    break
                _logger.info(f'WEBHOOK SEPAY SUCCESS: Successfully')
            return {'success': 200, 'message': 'Successfully'}
        except Exception as e:
            _logger.exception(f'WEBHOOK AHAMOVE EXCEPTION: {ustr(e)}')
            return {'status': 500, 'message': ustr(e)}
