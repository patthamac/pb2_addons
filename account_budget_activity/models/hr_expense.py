# -*- coding: utf-8 -*-
from openerp import api, models, _
from openerp.exceptions import ValidationError
from .account_activity import ActivityCommon


class HRExpenseExpense(models.Model):
    _inherit = 'hr.expense.expense'

    @api.model
    def _prepare_inv_line(self, account_id, exp_line):
        res = super(HRExpenseExpense, self)._prepare_inv_line(account_id,
                                                              exp_line)
        AnayticAccount = self.env['account.analytic.account']
        dimensions = AnayticAccount._analytic_dimensions()
        for d in dimensions:
            res.update({d: exp_line[d].id})
        return res

    @api.multi
    def write(self, vals):
        if vals.get('state', False) == 'draft':
            for expense in self:
                for line in expense.line_ids:
                    Analytic = self.env['account.analytic.account']
                    line.analytic_account = \
                        Analytic.create_matched_analytic(line)
                expense.line_ids._create_analytic_line(reverse=True)
        # Create negative amount for the remain product_qty - open_invoiced_qty
        if vals.get('state') in ('cancelled',):
            self.filtered(lambda x: x.state not in ('cancelled',)).\
                line_ids._create_analytic_line(reverse=False)
        return super(HRExpenseExpense, self).write(vals)


class HRExpenseLine(ActivityCommon, models.Model):
    _inherit = 'hr.expense.line'

    # temp_invoiced_qty = fields.Float(
    #     string='Temporary Invoiced Quantity',
    #     digits=(12, 6),
    #     compute='_compute_temp_invoiced_qty',
    #     store=True,
    #     copy=False,
    #     default=0.0,
    #     help="This field is used to keep the previous invoice qty, "
    #     "for calculate release commitment amount",
    # )

    @api.model
    def _get_non_product_account_id(self):
        if 'activity_id' in self:
            if not self.activity_id.account_id:
                raise ValidationError(
                    _('No Account Code assigned to Activity - %s') %
                    (self.activity_id.name,))
            else:
                return self.activity_id.account_id.id
        else:
            return super(HRExpenseLine, self)._get_non_product_account_id()

    # ================= Expense Commitment =====================
    @api.model
    def _price_subtotal(self, line_qty):
        line_price = self.unit_amount
        taxes = self.tax_ids.compute_all(line_price, line_qty,
                                         self.product_id,
                                         self.expense_id.partner_id)
        cur = self.expense_id.currency_id
        return cur.round(taxes['total'])

    @api.model
    def _prepare_analytic_line(self, reverse=False, currency=False):
        # general_account_id = self._get_account_id_from_po_line()
        general_journal = self.env['account.journal'].search(
            [('type', '=', 'purchase')], limit=1)
        if not general_journal:
            raise Warning(_('Define an accounting journal for purchase'))
        if not general_journal.is_budget_commit:
            return False
        if not general_journal.exp_commitment_analytic_journal_id or \
                not general_journal.exp_commitment_account_id:
            raise ValidationError(
                _("No analytic journal for expense commitments defined on the "
                  "accounting journal '%s'") % general_journal.name)

        # Use EXP Commitment Account
        general_account_id = general_journal.exp_commitment_account_id.id
        journal_id = general_journal.exp_commitment_analytic_journal_id.id
        line_qty = 0.0
        if 'diff_qty' in self._context:
            line_qty = self._context.get('diff_qty')
        else:
            line_qty = self.unit_quantity - self.open_invoiced_qty
        if not line_qty:
            return False
        sign = reverse and -1 or 1
        company_currency = self.env.user.company_id.currency_id
        currency = currency or company_currency
        return {
            'name': self.name,
            'product_id': self.product_id.id,
            'account_id': self.analytic_account.id,
            'unit_amount': line_qty,
            'product_uom_id': self.uom_id.id,
            'amount': currency.compute(sign * self._price_subtotal(line_qty),
                                       company_currency),
            'general_account_id': general_account_id,
            'journal_id': journal_id,
            'ref': self.expense_id.name,
            'user_id': self._uid,
            # Expense
            'expense_id': self.expense_id.id,
        }

    @api.one
    def _create_analytic_line(self, reverse=False):
        vals = self._prepare_analytic_line(
            reverse=reverse, currency=self.expense_id.currency_id)
        if vals:
            self.env['account.analytic.line'].sudo().create(vals)

    # # When partial open_invoiced_qty
    # @api.multi
    # @api.depends('open_invoiced_qty')
    # def _compute_temp_invoiced_qty(self):
    #     # As inoviced_qty increased, release the commitment
    #     for rec in self:
    #         # On compute filed of temp_purchased_qty, ORM is not working
    #         self._cr.execute("""
    #             select temp_invoiced_qty
    #             from hr_expense_line where id = %s
    #         """, (rec.id,))
    #         result = self._cr.fetchone()
    #         temp_invoiced_qty = result and result[0] or 0.0
    #         diff_qty = (rec.open_invoiced_qty - temp_invoiced_qty)
    #         if rec.expense_state not in ('cancelled',):
    #             x = 1
    #             rec.with_context(diff_qty=diff_qty).\
    #                 _create_analytic_line(reverse=False)
    #         rec.temp_invoiced_qty = rec.open_invoiced_qty

    # ======================================================
