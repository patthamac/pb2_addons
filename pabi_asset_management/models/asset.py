# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp import tools
from openerp.exceptions import ValidationError
from openerp.addons.pabi_chartfield.models.chartfield \
    import ChartFieldAction

# Map state vs status
# 'draft': ['cancel'],
# 'open': ['normal', 'deliver', 'transfer', 'break', 'to_dispose'],
# 'removed': ['dispose', 'lost'],
# 'close': ['expire'],


class AccountAssetStatus(models.Model):
    _name = 'account.asset.status'
    _description = 'This non-UI model keeps the required status map of asset'

    sequence = fields.Integer(
        string='Sequence',
        required=True,
        default=1,
    )
    code = fields.Char(
        string='Code',
        size=10,
        index=True,
    )
    name = fields.Char(
        string='Status',
        size=100,
        required=True,
    )
    map_state = fields.Selection(
        [('draft', 'Draft'),
         ('open', 'Running'),
         ('close', 'Close'),
         ('removed', 'Removed'), ],
        string='Asset State Mapping',
        required=True,
    )


class AccountAsset(ChartFieldAction, models.Model):
    _name = 'account.asset'
    _inherit = ['account.asset', 'mail.thread']

    name = fields.Char(
        default='/',
        readonly=False,
        states={},  # Always editable
    )
    type = fields.Selection(
        # Need this way of doing default, because default_type in context will
        # cause problem compute depreciation table, it set line type wrongly
        default=lambda self: self._context.get('type') or 'normal',
    )
    profile_type = fields.Selection(
        [('normal', 'Normal'),
         ('normal_nod', 'Normal (No-Depre)'),
         ('ait', 'AIT'),
         ('auc', 'AUC'),
         ('lva', 'Low-Value'),
         ('atm', 'ATM')],
        related='profile_id.profile_type',
        string='Asset Profile Type',
        store=True,
        readonly=True,
    )
    status = fields.Many2one(
        'account.asset.status',
        string='Asset Status',
        default=lambda self: self.env.ref('pabi_asset_management.'
                                          'asset_status_cancel'),
        domain="[('map_state', '=', state)]",
        required=False,
        index=True,
        help="Status vs State\n"
        "Draft → ยกเลิก\n"
        "Running → ใช้งานปกติ, ส่งมอบ, โอนเป็นครุภัณฑ์, ชำรุด, รอจำหน่าย\n"
        "Removed → จำหน่าย, สูญหาย\n"
        "Close → หมดอายุการใช้งาน"
    )
    status_code = fields.Char(
        string='Status Code',
        related='status.code',
        readonly=True,
        store=True,
    )
    deliver_to = fields.Char(
        string='Deliver to',
        help="If status is chagned to 'delivery', this field is required",
    )
    deliver_date = fields.Date(
        string='Delivery date',
        help="If status is chagned to 'delivery', this field is required",
    )
    code = fields.Char(
        string='Code',  # Rename
        default='/',
    )
    code2 = fields.Char(
        string='Code (legacy)',
        help="Code in Legacy System",
    )
    product_id = fields.Many2one(
        'product.product',
        string='Asset Type',
        domain=[('asset_profile_id', '!=', False)],
        readonly=True,
        states={'draft': [('readonly', False)]},
        help="This asset is created from this product class",
    )
    move_id = fields.Many2one(
        'stock.move',
        string='Move',
        readonly=True,
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking',
        related='move_id.picking_id',
        store=True,
        readonly=True,
    )
    date_picking = fields.Datetime(
        string='Picking Date',
        related='move_id.picking_id.date_done',
        readonly=True,
    )
    purchase_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        related='move_id.purchase_line_id.order_id',
        store=True,
        readonly=True,
    )
    uom_id = fields.Many2one(
        'product.uom',
        string='Unit of Measure',
        related='move_id.product_uom',
        store=True,
        readonly=True,
    )
    no_depreciation = fields.Boolean(
        string='No Depreciation',
        related='profile_id.no_depreciation',
        readonly=True,
    )
    # Additional Info
    asset_purchase_method_id = fields.Many2one(
        'asset.purchase.method',
        string='Purchase Method',
    )
    purchase_request_id = fields.Many2one(
        'purchase.request',
        string='Purchase Request',
        related='move_id.purchase_line_id.quo_line_id.requisition_line_id.'
        'purchase_request_lines.request_id',
        readonly=True,
        help="PR of this asset",
    )
    pr_requester_id = fields.Many2one(
        'res.users',
        string='PR Requester',
        related='purchase_request_id.requested_by',
        readonly=True,
        help="PR Requester of this asset",
    )
    date_request = fields.Date(
        string='PR Approved Date',
        related='move_id.purchase_line_id.quo_line_id.requisition_line_id.'
        'purchase_request_lines.request_id.date_approve',
        readonly=True,
        help="PR's Approved Date",
    )
    doc_request_id = fields.Many2one(
        'account.asset.request',
        string='Asset Request',
        readonly=True,
    )
    responsible_user_id = fields.Many2one(
        'res.users',
        string='Responsible Person',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    owner_project_id = fields.Many2one(
        'res.project',
        string='Project',
        readonly=True,
        help="Owner project of the budget structure",
    )
    owner_section_id = fields.Many2one(
        'res.section',
        string='Section',
        readonly=True,
        help="Owner section of the budget structure",
    )
    purchase_value = fields.Float(
        default=0.0,  # to avoid false
    )
    requester_id = fields.Many2one(
        'res.users',
        string='Requester',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    location_id = fields.Many2one(
        'account.asset.location',
        string='Building',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    room = fields.Char(
        string='Room',
        readonly=True,
        states={'draft': [('readonly', False)]},
    )
    serial_number = fields.Char(
        string='Serial Number',
        readonly=False,
    )
    warranty_start_date = fields.Date(
        string='Warranty Start Date',
        default=lambda self: fields.Date.context_today(self),
        track_visibility='onchange',
        readonly=False,
    )
    warranty_expire_date = fields.Date(
        string='Warranty Expire Date',
        default=lambda self: fields.Date.context_today(self),
        track_visibility='onchange',
        readonly=False,
    )
    # Transfer Asset
    target_asset_ids = fields.Many2many(
        'account.asset',
        'account_asset_source_target_rel',
        'source_asset_id', 'target_asset_id',
        string='Transferred to Asset',
        help="In case of transfer, this field show asset created by this one",
        readonly=True,
    )
    source_asset_count = fields.Integer(
        string='Source Asset Count',
        compute='_compute_source_asset_count',
    )
    source_asset_ids = fields.Many2many(
        'account.asset',
        'account_asset_source_target_rel',
        'target_asset_id', 'source_asset_id',
        string='Source Assets',
        help="List of source asset that has been transfer to this one",
    )
    image = fields.Binary(
        string='Image',
    )
    repair_note_ids = fields.One2many(
        'asset.repair.note',
        'asset_id',
        string='Repair Notes',
    )
    depreciation_summary_ids = fields.One2many(
        'account.asset.depreciation.summary',
        'asset_id',
        string='Depreciation Summary',
        readonly=True,
    )
    parent_type = fields.Selection(
        [('ait', 'AIT'),
         ('auc', 'AUC'),
         ('atm', 'ATM'),
         ],
        string='Parent Type',
    )
    _sql_constraints = [('code_uniq', 'unique(code)',
                         'Asset Code must be unique!')]

    @api.multi
    def validate_asset_to_request(self):
        invalid_assets = len(self.filtered(lambda l: l.doc_request_id or
                                           l.type != 'normal' or
                                           l.state != 'open'))
        if invalid_assets > 0:
            raise ValidationError(
                _('Please select only running assets '
                  'that has not been requested yet!'))
        return True

    @api.multi
    def validate_asset_to_removal(self):
        invalid_assets = len(self.filtered(lambda l: l.type != 'normal' or
                                           l.state != 'open'))
        if invalid_assets > 0:
            raise ValidationError(
                _('Please select only running assets!'))
        return True

    @api.multi
    def write(self, vals):
        Status = self.env['account.asset.status']
        # Status follow state
        if 'state' in vals and vals.get('state', False):
            if vals.get('state') == 'close':
                vals['status'] = Status.search([('code', '=', 'expire')]).id
            if vals.get('state') == 'open':
                vals['status'] = Status.search([('code', '=', 'normal')]).id
            if vals.get('state') == 'draft':
                vals['status'] = Status.search([('code', '=', 'cancel')]).id
            # For removed, the state will be set in remove wizard
        # Validate status change must be within status map
        elif 'status' in vals and vals.get('status', False):
            status = Status.browse(vals.get('status'))
            for asset in self:
                if status.map_state != asset.state:
                    raise ValidationError(_('Invalid change of asset status'))
        res = super(AccountAsset, self).write(vals)
        # # Following code repeat the compute depre, but w/o it, value is zero
        # for asset in self:
        #     if asset.profile_id.open_asset and \
        #             self._context.get('create_asset_from_move_line'):
        #         asset.compute_depreciation_board()
        # # --
        return res

    @api.multi
    def open_source_asset(self):
        self.ensure_one()
        action = self.env.ref('account_asset_management.account_asset_action')
        result = action.read()[0]
        assets = self.with_context(active_test=False).\
            search([('target_asset_ids', 'in', [self.id])])
        dom = [('id', 'in', assets.ids)]
        result.update({'domain': dom, 'context': {'active_test': False}})
        return result

    @api.multi
    def open_depreciation_lines(self):
        self.ensure_one()
        action = self.env.ref('pabi_asset_management.'
                              'action_account_asset_line')
        result = action.read()[0]
        dom = [('asset_id', '=', self.id)]
        result.update({'domain': dom})
        return result

    @api.multi
    @api.depends()
    def _compute_source_asset_count(self):
        for asset in self:
            _ids = self.with_context(active_test=False).\
                search([('target_asset_ids', 'in', [asset.id])])._ids
            asset.source_asset_count = len(_ids)

    @api.model
    def create(self, vals):
        # Case Parent Assets, AIT, AUC, ATM
        type = vals.get('type', False)
        ptype = vals.get('parent_type', False)
        if ptype and type == 'view':
            sequence_code = 'parent.asset.%s' % (ptype)
            vals['name'] = self.env['ir.sequence'].next_by_code(sequence_code)
        # Normal Case
        product_id = vals.get('product_id', False)
        if product_id:
            product = self.env['product.product'].browse(product_id)
            sequence = product.sequence_id
            if not sequence:
                raise ValidationError(
                    _('No asset sequence setup for selected product!'))
            vals['code'] = self.env['ir.sequence'].next_by_id(sequence.id)
        # # Init Salvage Value from Category
        profile_id = vals.get('profile_id', False)
        if profile_id:
            profile = self.env['account.asset.profile'].browse(profile_id)
            if not profile.no_depreciation:
                vals['salvage_value'] = profile.salvage_value
        asset = super(AccountAsset, self).create(vals)
        asset.update_related_dimension(vals)
        return asset

    @api.multi
    def name_get(self):
        res = []
        for record in self:
            if record.code and record.code != '/':
                name = "[%s] %s" % (record.code, record.name)
            else:
                name = record.name
            res.append((record.id, name))
        return res

    @api.multi
    def compute_depreciation_board(self):
        assets = self.filtered(lambda l: not l.no_depreciation)
        return super(AccountAsset, assets).compute_depreciation_board()

    @api.multi
    def onchange_profile_id(self, profile_id):
        res = super(AccountAsset, self).onchange_profile_id(profile_id)
        asset_profile = self.env['account.asset.profile'].browse(profile_id)
        if asset_profile and not asset_profile.no_depreciation:
            res['value']['salvage_value'] = asset_profile.salvage_value
        return res

    # Method used in change owner and transfer

    @api.model
    def _prepare_asset_reverse_moves(self, assets):
        AccountMoveLine = self.env['account.move.line']
        default = {'move_id': False,
                   'parent_asset_id': False,
                   'asset_profile_id': False,
                   'product_id': False,
                   'partner_id': False,
                   'stock_move_id': False,
                   }
        asset_move_lines_dict = []
        depre_move_lines_dict = []
        for asset in assets:
            account_asset_id = asset.profile_id.account_asset_id.id
            account_depre_id = asset.profile_id.account_depreciation_id.id
            # Getting the origin move_line (1 asset value and 1 depreciation)
            # Asset
            asset_lines = AccountMoveLine.search([  # Should have 1 line
                ('asset_id', '=', asset.id),
                ('account_id', '=', account_asset_id),
                # Same Owner
                ('project_id', '=', asset.owner_project_id.id),
                ('section_id', '=', asset.owner_section_id.id),
            ], order='id asc')
            if asset_lines:
                asset_line_dict = asset_lines[0].copy_data(default)[0]
                debit = sum(asset_lines.mapped('debit'))
                credit = sum(asset_lines.mapped('credit'))
                if debit > credit:
                    asset_line_dict['credit'] = debit - credit
                    asset_line_dict['debit'] = False
                else:
                    asset_line_dict['credit'] = False
                    asset_line_dict['debit'] = credit - debit
                asset_move_lines_dict.append(asset_line_dict)
            # Depre
            depre_lines = AccountMoveLine.search([
                ('asset_id', '=', asset.id),
                ('account_id', '=', account_depre_id),
                # Same Owner
                ('project_id', '=', asset.owner_project_id.id),
                ('section_id', '=', asset.owner_section_id.id),
            ], order='id asc')
            if depre_lines:
                depre_line_dict = depre_lines[0].copy_data(default)[0]
                debit = sum(depre_lines.mapped('debit'))
                credit = sum(depre_lines.mapped('credit'))
                if debit > credit:
                    asset_line_dict['credit'] = debit - credit
                    asset_line_dict['debit'] = False
                else:
                    asset_line_dict['credit'] = False
                    asset_line_dict['debit'] = credit - debit
                depre_move_lines_dict.append(depre_line_dict)
            # Validation
            # if not asset_move_lines_dict:
            #     raise ValidationError(
            #         _('No Asset Value. Something went wrong!\nIt is likely '
            #         'that, the asset owner do not match with account move.'))
            return (asset_move_lines_dict, depre_move_lines_dict)

    @api.model
    def _prepare_asset_target_move(self, move_lines_dict, new_owner=None):
        if new_owner is None:
            new_owner = {}
        debit = sum(x['debit'] for x in move_lines_dict)
        credit = sum(x['credit'] for x in move_lines_dict)
        if not move_lines_dict:
            raise ValidationError(
                _('Error on function _prepare_asset_target_move.\n'
                  'Invalid or no journal entry in original asset.'))
        move_line_dict = move_lines_dict[0].copy()
        move_line_dict.update({
            'analytic_account_id': False,  # To refresh dimension
            'credit': debit,
            'debit': credit,
        })
        if new_owner:
            move_line_dict.update({
                'project_id': new_owner.get('owner_project_id', False),
                'section_id': new_owner.get('owner_section_id', False),
            })
        return move_line_dict


class AccountAssetProfile(models.Model):
    _inherit = 'account.asset.profile'

    product_categ_id = fields.Many2one(
        'product.category',
        string='Product Category',
        ondelete='restrict',
        required=True,
        help="Grouping of this asset category",
    )
    account_asset_id = fields.Many2one(
        domain=[('type', '=', 'other'), ('user_type.for_asset', '=', True)],
    )
    no_depreciation = fields.Boolean(
        string='No Depreciation',
        compute='_compute_no_depreciation',
        store=True,
        help="If profile type is other than normal, No Depreciation is true",
    )
    salvage_value = fields.Float(
        string='Salvage Value',
        default=0.0,
        help="Default salvage value used when create asset from move line",
    )
    profile_type = fields.Selection(
        [('normal', 'Normal'),
         ('normal_nod', 'Normal (No-Depre)'),
         ('ait', 'AIT'),
         ('auc', 'AUC'),
         ('lva', 'Low-Value'),
         ('atm', 'ATM')],
        string='Asset Profile Type',
        required=True,
        default='normal',
    )

    @api.multi
    @api.depends('profile_type')
    def _compute_no_depreciation(self):
        for rec in self:
            rec.no_depreciation = \
                rec.profile_type != 'normal' and True or False

    @api.multi
    def write(self, vals):
        res = super(AccountAssetProfile, self).write(vals)
        if 'product_categ_id' in vals:
            Product = self.env['product.product']
            for asset_profile in self:
                products = Product.search([
                    ('asset', '=', True),
                    ('asset_profile_id', '=', asset_profile.id)])
                products.write({'categ_id': asset_profile.product_categ_id.id})
        return res


class AccountAssetLine(models.Model):
    _inherit = 'account.asset.line'

    type = fields.Selection(
        [('create', 'Purchase Value'),
         ('depreciate', 'Depreciation'),
         ('remove', 'Asset Removal'),
         ],
    )
    fiscalyear_id = fields.Many2one(
        'account.fiscalyear',
        string='Fiscalyear',
        compute='_compute_fiscalyear_id',
        store=True,
    )
    amount_accumulated = fields.Float(
        string='Accumulated Amount',
        compute='_compute_amount_accumulated',
        store=True,
    )

    @api.multi
    @api.depends('amount', 'depreciated_value')
    def _compute_amount_accumulated(self):
        for rec in self:
            rec.amount_accumulated = rec.amount + rec.depreciated_value

    @api.multi
    @api.depends('line_date')
    def _compute_fiscalyear_id(self):
        Fiscal = self.env['account.fiscalyear']
        for rec in self:
            rec.fiscalyear_id = Fiscal.find(dt=rec.line_date)

    @api.multi
    def _setup_move_line_data(self, depreciation_date,
                              period, account, type, move):
        move_line_data = super(AccountAssetLine, self).\
            _setup_move_line_data(depreciation_date,
                                  period, account, type, move)
        asset = self.asset_id
        move_line_data.update({'section_id': asset.owner_section_id.id,
                               'project_id': asset.owner_project_id.id})
        return move_line_data


class AssetRepairNote(models.Model):
    _name = 'asset.repair.note'

    asset_id = fields.Many2one(
        'account.asset',
        string='Asset',
        ondelete='cascade',
        index=True,
    )
    purchase_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
    )
    date = fields.Date(
        string='Date',
        default=lambda self: fields.Date.context_today(self),
    )
    note = fields.Text(
        string='Note',
    )


class AccountAssetDepreciationSummary(models.Model):
    _name = 'account.asset.depreciation.summary'
    _auto = False
    _rec_name = 'fiscalyear_id'
    _description = 'Fiscal Year depreciation summary of asset'
    _order = 'fiscalyear_id'

    asset_id = fields.Many2one(
        'account.asset',
        string='Asset',
        readonly=True,
    )
    fiscalyear_id = fields.Many2one(
        'account.fiscalyear',
        string='fiscalyear',
        readonly=True,
    )
    amount_depreciate = fields.Float(
        string='Depreciation Amount',
        readonly=True,
    )

    def init(self, cr):

        _sql = """
            select min(id) as id, asset_id, fiscalyear_id,
            sum(amount) as amount_depreciate
            from account_asset_line a
            where type = 'depreciate' and fiscalyear_id is not null
            group by asset_id, fiscalyear_id
        """

        tools.drop_view_if_exists(cr, self._table)
        cr.execute(
            """CREATE or REPLACE VIEW %s as (%s)""" %
            (self._table, _sql,))
