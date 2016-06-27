# -*- coding: utf-8 -*-

from openerp import models, fields, api


class HRExpense(models.Model):
    _inherit = 'hr.expense.expense'

    apweb_ref_url = fields.Char(
        string='PABI Web Ref.',
        readonly=True, states={'draft': [('readonly', False)]},
    )
    create_uid = fields.Many2one(
        'res.users',
        string='Prepared by',
        readonly=True,
    )
    date = fields.Date(
        string='Approved Date',
    )
    user_valid = fields.Many2one(
        string='Accepted By',
    )
    date_back = fields.Date(
        string='Back from seminar',
        readonly=True, states={'draft': [('readonly', False)]},
    )
    date_due = fields.Date(
        string='Due Date',
        related='advance_due_history_ids.date_due',
        store=True,
        readonly=True, states={'draft': [('readonly', False)]},
    )
    employee_bank_id = fields.Many2one(
        'res.bank.master',
        string='Bank',
        readonly=True, states={'draft': [('readonly', False)]},
    )
    state = fields.Selection(
        [('draft', 'Draft'),
         ('cancelled', 'Rejected'),
         ('confirm', 'Wait for Accept'),
         ('accepted', 'Accepted'),
         ('done', 'Waiting Payment'),
         ('paid', 'Paid'),
         ]
    )
    advance_type = fields.Selection(
        [('buy_product', 'Buy Product/Material'),
         ('attend_seminar', 'Attend Seminar'),
         ],
        readonly=True, states={'draft': [('readonly', False)]},
    )
    advance_due_history_ids = fields.One2many(
        'hr.expense.advance.due.history',
        'expense_id',
        string='Due History',
        readonly=True,
    )
    attendee_employee_ids = fields.One2many(
        'hr.expense.attendee.employee',
        'expense_id',
        string='Attendee / Employee',
        copy=True,
    )
    attendee_external_ids = fields.One2many(
        'hr.expense.attendee.external',
        'expense_id',
        string='Attendee / External',
        copy=True,
    )
    project_id = fields.Many2one(
        'res.project',
        string='Project',
        compute='_compute_project_section',
        store=True,
        help="Show project, only if all lines use the same project",
    )
    section_id = fields.Many2one(
        'res.section',
        string='Section',
        compute='_compute_project_section',
        store=True,
        help="Show section, only if all lines use the same section",
    )

    @api.multi
    @api.depends('line_ids.project_id', 'line_ids.section_id')
    def _compute_project_section(self):
        for rec in self:
            projects = self.line_ids.\
                filtered(lambda x: x.project_id).mapped('project_id')
            sections = self.line_ids.\
                filtered(lambda x: x.section_id).mapped('section_id')
            rec.project_id = len(projects) == 1 and projects[0] or False
            rec.section_id = len(sections) == 1 and sections[0] or False


class HRExpenseAdvanceDueHistory(models.Model):
    _name = 'hr.expense.advance.due.history'
    _order = 'write_date desc'

    expense_id = fields.Many2one(
        'hr.expense',
        string='Expense',
        ondelete='cascade',
        index=True,
    )
    date_due = fields.Date(
        string='New Due Date',
        readonly=True,
    )
    write_uid = fields.Many2one(
        'res.users',
        string='Updated By',
        readonly=True,
    )
    write_date = fields.Datetime(
        string='Updated Date',
        readonly=True,
    )


class HRExpenseAttendeeEmployee(models.Model):
    _name = 'hr.expense.attendee.employee'
    _order = 'sequence, id'

    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    expense_id = fields.Many2one(
        'hr.expense',
        string='Expense',
        ondelete='cascade',
        index=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
    )
    position_id = fields.Many2one(
        'hr.position',
        string='Position',
    )
    section_id = fields.Many2one(
        'res.section',
        string='Section',
    )
    project_id = fields.Many2one(
        'res.project',
        string='Project',
    )
    # TODO: may display section_id and project_id in same column to save space


class HRExpenseAttendeeExternal(models.Model):
    _name = 'hr.expense.attendee.external'
    _order = 'sequence, id'

    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    expense_id = fields.Many2one(
        'hr.expense',
        string='Expense',
        ondelete='cascade',
        index=True,
    )
    attendee_name = fields.Char(
        string='Attendee Name',
    )
    position = fields.Char(
        string='Position',
    )


class HRExpenseRule(models.Model):
    _name = "hr.expense.rule"

    activity_id = fields.Many2one(
        'account.activity',
        string='Activity',
        required=True,
    )
    position = fields.Char(
        string='Position',
    )
    condition_1 = fields.Char(
        string='Condition 1',
    )
    condition_2 = fields.Char(
        string='Condition 2',
    )
    uom = fields.Char(
        string='UoM',
    )
    amount = fields.Float(
        string='Amount',
        default=0.0,
        required=True,
    )
    _sql_constraints = [
        ('rule_unique',
         'unique(activity_id, position, condition_1, condition_2, uom)',
         'Expense Regulation must be unique!'),
    ]
