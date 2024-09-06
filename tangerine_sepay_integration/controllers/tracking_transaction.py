import logging
import psycopg2
from datetime import datetime
from markupsafe import Markup
from odoo import api, registry, SUPERUSER_ID
from odoo.sql_db import flush_env
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

    @staticmethod
    def _payload_payment_transaction(invoice, payment_id, amount, sepay_ref, partner_id):
        invoice_ref = invoice.name
        transaction_ids = request.env['payment.transaction'].sudo().search([('reference', 'ilike', invoice_ref)], order='create_date desc')
        if transaction_ids:
            names = transaction_ids[0].reference.split('-')
            if len(names) == 1:
                invoice_ref = f'{transaction_ids[0].reference}-1'
            else:
                invoice_ref = f'{transaction_ids[0].reference[:-2]}-{int(names[1]) + 1}'
        return {
            'reference': invoice_ref,
            'payment_id': payment_id,
            'amount': amount,
            'acquirer_id': request.env.ref('payment.payment_acquirer_transfer').id,
            'acquirer_reference': sepay_ref,
            'partner_id': partner_id,
            'state': 'done',
            'currency_id': request.env.ref('base.VND').id,
            'invoice_ids': [(6, 0, invoice.ids)]
        }

    def _create_payment_transaction(self, invoice, payment_id, amount, sepay_ref, partner_id):
        flush_env(request.env)
        db_name = request._cr.dbname
        try:
            db_registry = registry(db_name)
            with db_registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                env['payment.transaction'].sudo().create(
                    self._payload_payment_transaction(invoice, payment_id, amount, sepay_ref, partner_id)
                )
        except psycopg2.Error:
            pass

    @route('/webhook/v1/payment/sepay', type='json', auth='public', methods=['POST'])
    def sepay_callback(self):
        try:
            body = request.jsonrequest
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
            amount = body.get('transferAmount', 0)
            for invoice in invoices.sorted(key=lambda i: i.amount_residual, reverse=True):
                payment = request.env['account.payment'].sudo().create({
                    'currency_id': invoice.currency_id.id,
                    'amount': amount,
                    'payment_type': 'inbound',
                    'partner_id': invoice.commercial_partner_id.id,
                    'partner_type': MAP_INVOICE_TYPE_PARTNER_TYPE[invoice.move_type],
                    'ref': body.get('referenceCode'),
                    'journal_id': journal_id.id,
                    'date': datetime.strptime(body.get('transactionDate'), '%Y-%m-%d %H:%M:%S')
                })
                payment.action_post()
                line_id = payment.line_ids.filtered(lambda l: l.credit)
                invoice.js_assign_outstanding_line(line_id.id)
                message = Markup(f'''
                            Inbound payment from SePay
                            <ul>
                                <li>Total: {amount:,} đ</li>
                                <li>Note: {body.get('content', '')}</li>
                            </ul>
                        ''')
                invoice.message_post(body=message)
                request.env.cr.commit()
                self._create_payment_transaction(
                    invoice,
                    payment.id,
                    amount,
                    body.get('referenceCode'),
                    invoice.commercial_partner_id.id
                )
                _logger.info(f'WEBHOOK SEPAY SUCCESS: Successfully')
            return {'success': 200, 'message': 'Successfully'}
        except Exception as e:
            _logger.exception(f'WEBHOOK AHAMOVE EXCEPTION: {ustr(e)}')
            return {'status': 500, 'message': ustr(e)}
