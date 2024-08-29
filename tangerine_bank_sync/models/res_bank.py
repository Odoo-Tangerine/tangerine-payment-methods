import os
import requests
from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.tools import ustr


class ResBank(models.Model):
    _inherit = 'res.bank'

    short_name = fields.Char(string='Short name')
    bin = fields.Char(string='BIN')
    code = fields.Char(string='Code')
    logo_url = fields.Char(string='Logo URL')

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f'[{rec.code}] - {rec.name}'

    @staticmethod
    def _payload_bank(record):
        return {
            'name': record.get('name'),
            'bin': record.get('bin'),
            'short_name': record.get('shortName'),
            'logo_url': record.get('logo'),
            'code': record.get('code')
        }

    @api.model
    def bank_information_sync(self):
        try:
            res = requests.get(url='https://api.vietqr.io/v2/banks')
            res.raise_for_status()
            data = []
            if res.status_code == 200:
                result = res.json()
                for rec in result.get('data', []):
                    file_name = f"{rec.get('code')}-{rec.get('bin')}.png"
                    file_path = os.path.join(os.path.split(os.path.dirname(__file__))[0], 'static', 'logo', file_name)
                    if not os.path.exists(file_path):
                        res_logo = requests.get(url=rec.get('logo'))
                        with open(file_path, 'wb') as file:
                            file.write(res_logo.content)
                    bank_id = self.search([('code', '=', rec.get('code'))])
                    if bank_id:
                        bank_id.write(self._payload_bank(rec))
                    else:
                        data.append(self._payload_bank(rec))
                if data:
                    self.create(data)
        except Exception as e:
            raise UserError(ustr(e))
