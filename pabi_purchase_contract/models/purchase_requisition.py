# -*- coding: utf-8 -*-
import openerp
import base64
import time
import re
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning as UserError
from openerp.tools import float_compare


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    @api.one
    @api.depends('contract_ids')
    def _count_contract(self):
        PContract = self.env['purchase.contract']
        contract = PContract.search([('pd_id', '=', self.id)])
        self.count_contract = len(contract)

    contract_ids = fields.One2many(
        'purchase.contract',
        'pd_id',
        string='Contract',
        readonly=False,
    )
    count_contract = fields.Integer(
        string='Count Contract',
        compute='_count_contract',
        store=True,
    )

    @api.multi
    def contract_open(self):
        return {
            'name': _('Purchase Contracts'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'purchase.contract',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': "[('pd_id', '=', "+str(self.id)+")]",
        }
