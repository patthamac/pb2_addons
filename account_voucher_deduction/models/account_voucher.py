# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp


class AccuontVoucherMultipleReconcile(models.Model):
    _name = 'account.voucher.multiple.reconcile'
    _description = 'Account Voucher Multiple Reconcile'

    account_id = fields.Many2one(
        'account.account',
        string='Reconcile Account',
        required=True)
    amount = fields.Float(
        string='Amount',
        digits_compute=dp.get_precision('Account'),
        required=True)
    comment = fields.Char(string='Comment', required=True)
    voucher_id = fields.Many2one('account.voucher', string='Related Voucher')
    analytic_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account')


class AccountVoucher(models.Model):
    _inherit = 'account.voucher'

    @api.multi
    @api.depends('line_cr_ids', 'line_dr_ids', 'multiple_reconcile_ids')
    def _get_writeoff_amount(self):
        if not self.ids:
            return True
        for voucher in self:
            debit = 0.0
            credit = 0.0
            reconcile_total = 0.0
            if voucher.multiple_reconcile_ids:
                sign = voucher.type == 'payment' and -1 or 1
                for l in voucher.line_dr_ids:
                    debit += l.amount
                for l in voucher.line_cr_ids:
                    credit += l.amount
                if voucher.type == 'receipt':
                    for r in voucher.multiple_reconcile_ids:
                        reconcile_total += r.amount
                elif voucher.type == 'payment':
                    for r in voucher.multiple_reconcile_ids:
                        reconcile_total -= r.amount
                currency = voucher.currency_id or\
                    voucher.company_id.currency_id
                voucher.writeoff_amount = currency.round(
                    voucher.amount - sign * (credit - debit + reconcile_total))
            else:
                sign = voucher.type == 'payment' and -1 or 1
                for l in voucher.line_dr_ids:
                    debit += l.amount
                for l in voucher.line_cr_ids:
                    credit += l.amount
                currency = voucher.currency_id or\
                    voucher.company_id.currency_id
                voucher.writeoff_amount = currency.round(
                    voucher.amount - sign * (credit - debit))

    is_lazada_payment = fields.Boolean('Is Lazada Payment?', readonly=True)
    multiple_reconcile_ids = fields.One2many(
        'account.voucher.multiple.reconcile',
        'voucher_id',
        string='Reconcile Liness')
    writeoff_amount = fields.Float(
        compute=_get_writeoff_amount,
        string='Difference Amount',
        readonly=True,
        help="Computed as the difference between \
        the amount stated in the voucher and the\
         sum of allocation on the voucher lines.")

    @api.model
    def multiple_reconcile_get_hook(self, line_total,
                                    move_id, name,
                                    company_currency, current_currency):
        ded_amount, list_move_line = super(AccountVoucher, self).\
            multiple_reconcile_get_hook(line_total, move_id, name,
                                        company_currency, current_currency)
        voucher = self
        if voucher.multiple_reconcile_ids:
            ctx = dict(self._context.copy())
            ctx.update({'date': voucher.date})
            for line in voucher.multiple_reconcile_ids:
                amount_convert = self.with_context(ctx)._convert_amount(
                    line.amount, voucher.id)  # amount in company currency
                debit = 0.0
                credit = 0.0
                if line.amount < 0.0:
                    if voucher.type == 'receipt':
                        debit = amount_convert
                    else:
                        credit = amount_convert
                else:
                    if voucher.type == 'receipt':
                        credit = amount_convert
                    else:
                        debit = amount_convert

                debit = voucher.company_id.currency_id.round((debit))
                credit = voucher.company_id.currency_id.round((credit))
                if abs(debit) > 0.0:
                    sign = 1
                else:
                    sign = -1
                move_line = {
                    'name': line.comment or name,
                    'account_id': line.account_id.id,
                    'move_id': move_id,
                    'partner_id': voucher.partner_id.id,
                    'date': voucher.date,
                    'credit': abs(credit),
                    'debit': abs(debit),
                    'amount_currency': company_currency !=
                    current_currency and sign * abs(line.amount) or 0.0,
                    'currency_id': company_currency !=
                    current_currency and current_currency or False,
                    'analytic_account_id': line.analytic_id and
                    line.analytic_id.id or False,
                }
                ded_amount += voucher.company_id.currency_id.\
                    round((amount_convert))
                list_move_line.append(move_line)
        return ded_amount, list_move_line

    @api.model
    def action_move_line_writeoff_hook(self, ml_writeoff):
        if self.multiple_reconcile_ids:
            if ml_writeoff:
                for line_tax in ml_writeoff:
                    self.env['account.move.line'].create(line_tax)
            return True
        else:
            return super(AccountVoucher, self).\
                action_move_line_writeoff_hook(ml_writeoff)

    @api.model
    def multiple_reconcile_ded_amount_hook(self, line_total, move_id,
                                           account_id, diff, ded_amount, name,
                                           company_currency, current_currency):
        voucher = self
        list_move_line = []
        if self.multiple_reconcile_ids and diff != ded_amount:
            debit = credit = 0.0
            ctx = dict(self._context.copy())
            ctx.update({'date': voucher.date})
            value1 = self.with_context(ctx).\
                _convert_amount(voucher.writeoff_amount, voucher.id)
            if value1 != 0.0:
                if value1 < 0.0:
                    if voucher.type == 'receipt':
                        debit = value1
                    else:
                        credit = value1
                else:
                    if voucher.type == 'receipt':
                        credit = value1
                    else:
                        debit = value1

                sign = voucher.type == 'payment' and -1 or 1
                move_line = {
                    'name': name,
                    'account_id': account_id,
                    'move_id': move_id,
                    'partner_id': voucher.partner_id.id,
                    'date': voucher.date,
                    'credit': abs(credit),
                    'debit': abs(debit),
                    'amount_currency': company_currency != current_currency and
                    (sign * -1 * voucher.writeoff_amount) or False,
                    'currency_id': company_currency != current_currency and
                    current_currency or False,
                }
                list_move_line.append(move_line)
            return list_move_line
        elif self.multiple_reconcile_ids:
            return list_move_line
        else:
            return super(AccountVoucher, self).\
                multiple_reconcile_ded_amount_hook(line_total, move_id,
                                                   account_id, diff,
                                                   ded_amount, name,
                                                   company_currency,
                                                   current_currency)

    @api.model
    def action_move_line_create_hook(self, rec_list_ids):
        voucher = self
        for rec_ids in rec_list_ids:
            if len(rec_ids) >= 2:
                recs = self.env['account.move.line'].browse(rec_ids)
                if voucher.writeoff_amount == 0.0 and not\
                        voucher.multiple_reconcile_ids:
                    recs.reconcile_partial(type='manual')
                elif voucher.writeoff_amount == 0.0 and \
                        voucher.multiple_reconcile_ids:
                    recs.reconcile_partial(type='manual')
                elif voucher.writeoff_amount == 0.0 or \
                        voucher.multiple_reconcile_ids:
                    recs.reconcile(type='manual')
                else:
                    recs.reconcile_partial(type='manual')
        return True

    @api.multi
    def button_reset_amount(self):
        return self.write({'multiple_reconcile_ids': []})
