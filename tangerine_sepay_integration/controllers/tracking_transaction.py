import logging
import psycopg2
from markupsafe import Markup
from datetime import datetime
from odoo import api, registry, SUPERUSER_ID, Command
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
    def _payload_payment_transaction(reference, payment_id, amount, sepay_ref, partner_id):
        reference_name = reference.name
        transaction_ids = request.env['payment.transaction'].sudo().search([('reference', 'ilike', reference.name)], order='create_date desc')
        if transaction_ids:
            names = transaction_ids[0].reference.split('-')
            if len(names) == 1:
                reference_name = f'{transaction_ids[0].reference}-1'
            else:
                reference_name = f'{transaction_ids[0].reference[:-2]}-{int(names[1]) + 1}'
        payload = {
            'reference': reference_name,
            'payment_id': payment_id,
            'amount': amount,
            'payment_method_id': request.env.ref('tangerine_sepay_integration.payment_method_sepay').id,
            'provider_id': request.env.ref('payment.payment_provider_transfer').id,
            'provider_reference': sepay_ref,
            'partner_id': partner_id,
            'currency_id': request.env.ref('base.VND').id,
        }
        if reference._name == 'sale.order':
            payload['sale_order_ids'] = [Command.set(reference.ids)]
        else:
            payload['invoice_ids']: [Command.set(reference.ids)]
        return payload

    def _handle_payment_transaction(self, reference, payment_id, amount, sepay_ref, partner_id):
        request.env.flush_all()
        db_name = request._cr.dbname
        try:
            db_registry = registry(db_name)
            with db_registry.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                transaction_id = env['payment.transaction'].sudo().search([
                    ('reference', '=', reference.name),
                    ('provider_code', '=', 'custom'),
                    ('state', '=', 'pending')
                ])
                if transaction_id:
                    transaction_id.write({
                        'payment_id': payment_id,
                        'provider_reference': sepay_ref,
                        'amount': amount
                    })
                else:
                    transaction_id = env['payment.transaction'].sudo().create(
                        self._payload_payment_transaction(reference, payment_id, amount, sepay_ref, partner_id)
                    )
                transaction_id._set_done()
        except psycopg2.Error:
            pass

    @staticmethod
    def _get_journal(order, body):
        domain = [
            ('type', '=', 'bank'),
            ('company_id', '=', order.company_id.id),
            ('code', 'ilike', 'BNK%')
        ]
        if body.get('accountNumber'):
            bank_account_id = request.env['res.partner.bank'].sudo().search([('acc_number', '=', body.get('accountNumber'))])
            if bank_account_id:
                domain.append(('bank_account_id', '=', bank_account_id.id))
        journal_id = request.env['account.journal'].sudo().search(domain)
        if not journal_id:
            _logger.error(f'WEBHOOK SEPAY ERROR: Journal of the bank not found.')
            return {'success': 404, 'error': '[Payment Webhook] - Journal of the bank not found'}
        if len(journal_id) > 1:
            journal_id = journal_id[0]
        return journal_id

    @staticmethod
    def _get_order(data):
        order_id = request.env['sale.order'].sudo().search([('name', '=', data.get('code'))])
        if not order_id:
            _logger.error(f'WEBHOOK SEPAY ERROR: The code not found.')
            return {'success': 404, 'message': 'The code not found.'}
        if order_id.state == 'sent':
            order_id.action_confirm()
        return order_id

    @staticmethod
    def _get_bank_account(account_number):
        return request.env['res.partner.bank'].sudo().search([('acc_number', '=', account_number)])

    def _register_inbound_payment(self, acc_number, amount, date, partner_id, memo, journal_id, currency_id, ref):
        bank_account_id = self._get_bank_account(acc_number)
        return request.env['account.payment'].sudo().create({
            'currency_id': currency_id.id,
            'amount': amount,
            'payment_type': 'inbound',
            'partner_id': partner_id.id,
            'partner_type': 'customer',
            'ref': memo,
            'journal_id': journal_id.id,
            'partner_bank_id': bank_account_id.id if bank_account_id else False,
            'date': datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        })

    def _process_invoices_payment(self, body, invoices, journal_id, amount):
        amount_transaction = amount
        for invoice in invoices.sorted(key=lambda i: i.amount_residual, reverse=True):
            if amount <= 0:
                break
            payment_id = self._register_inbound_payment(
                acc_number=body.get('accountNumber'),
                amount=min(amount, invoice.amount_residual),
                date=body.get('transactionDate'),
                partner_id=invoice.partner_id,
                memo=invoice.name,
                journal_id=journal_id,
                currency_id=invoice.currency_id,
                ref=body.get('referenceCode')
            )
            payment_id.action_post()
            line_id = payment_id.line_ids.filtered(lambda l: l.credit)
            invoice.js_assign_outstanding_line(line_id.id)
            invoice.message_post(body=Markup(f'''
                Inbound payment from SePay
                <ul>
                    <li>Total: {amount:,} đ</li>
                    <li>Note: {body.get('content', '')}</li>
                </ul>
            '''))
            amount -= invoice.amount_residual
            request.env.cr.commit()

            self._handle_payment_transaction(
                reference=invoice,
                payment_id=payment_id.id,
                amount=amount_transaction,
                sepay_ref=body.get('referenceCode'),
                partner_id=invoice.partner_id.id,
            )

    def _process_no_invoice_payment(self, body, order_id, journal_id, amount):
        payment_id = self._register_inbound_payment(
            acc_number=body.get('accountNumber'),
            amount=body.get('transferAmount'),
            date=body.get('transactionDate'),
            partner_id=order_id.partner_invoice_id,
            memo=order_id.name,
            journal_id=journal_id,
            currency_id=order_id.currency_id,
            ref=body.get('referenceCode')
        )
        payment_id.action_post()
        request.env.cr.commit()
        self._handle_payment_transaction(
            order_id,
            payment_id.id,
            body.get('transferAmount'),
            body.get('referenceCode'),
            order_id.partner_invoice_id.id,
        )

    @route('/webhook/v1/payment/sepay', type='json', auth='public', methods=['POST'])
    def sepay_callback(self):
        try:
            request.update_env(SUPERUSER_ID)
            body = request.dispatcher.jsonrequest
            _logger.info(f'WEBHOOK SEPAY START - BODY: {body}')
            if not body.get('code') or not body.get('transferAmount'):
                _logger.error(f'WEBHOOK SEPAY ERROR: The value of field code is required.')
                return {'success': 400, 'message': 'The value of field code is required.'}
            order_id = self._get_order(body)
            journal_id = self._get_journal(order_id, body)
            invoices = order_id.invoice_ids.filtered(lambda i: i.state == 'posted' and i.amount_residual > 0)
            amount = body.get('transferAmount', 0)
            if not invoices:
                self._process_no_invoice_payment(body, order_id, journal_id, amount)
            else:
                self._process_invoices_payment(body, invoices, journal_id, amount)
            _logger.info(f'WEBHOOK SEPAY SUCCESS: Successfully')
            return {'success': 200, 'message': 'Successfully'}
        except Exception as e:
            _logger.exception(f'WEBHOOK SEPAY EXCEPTION: {ustr(e)}')
            return {'status': 500, 'message': ustr(e)}
