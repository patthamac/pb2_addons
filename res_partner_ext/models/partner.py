# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    id = fields.Integer(
        string='ID',
        readonly=True,
    )
    name = fields.Char(
        translate=True,
    )
    create_date = fields.Datetime(
        readonly=True,
    )
    is_government = fields.Boolean(
        string='Government',
        compute='_is_government',
    )
    search_key = fields.Char(
        string='Search Key',
        compute='_get_search_key',
        store=True,
    )
    # For group by only,
    single_category_id = fields.Many2one(
        'res.partner.category',
        compute='_get_single_category_id',
        store=True,
    )
    require_taxid = fields.Boolean(
        string='Require Tax ID',
        compute='_get_require_taxbranch',
        store=True,
        multi='taxbranch',
    )
    require_taxbranch = fields.Boolean(
        string='Require Tax Branch ID',
        compute='_get_require_taxbranch',
        store=True,
        multi='taxbranch',
    )
    category_id = fields.Many2one(
        'res.partner.category',
        string='Supplier Category',
    )
    customer_category_id = fields.Many2one(
        'res.partner.category',
        string='Customer Category',
    )
    tag_ids = fields.Many2many(
        'res.partner.tag',
        string='Tags',
    )
    is_shop = fields.Boolean(
        string='Shop',
    )

    @api.one
    @api.constrains('name', 'supplier', 'customer', 'is_shop')
    def _check_partner_name(self):
        partner_ids = self.search([('name', '=', self.name),
                                   '|', ('supplier', '=', True),
                                   ('customer', '=', True)])
        if len(partner_ids) > 1 and not self.is_shop:
            raise ValidationError("Partner Name must be unique!")

    @api.one
    @api.constrains('vat', 'taxbranch', 'category_id', 'is_shop')
    def _check_vat_taxbranch_unique(self):
        if not self.is_government and \
                self.category_id.require_tax_branch_unique:
            partners = self.search([('vat', '=', self.vat),
                                    ('taxbranch', '=', self.taxbranch)])
            if len(partners) > 1 and not self.is_shop:
                raise ValidationError(_(
                    "Tax ID + Tax Branch ID must be unique for "
                    "non-governmental organization!"))

    @api.one
    @api.constrains('vat')
    def _check_vat(self):
        if self.require_taxid and self.vat > 0 and len(self.vat) != 13:
            raise ValidationError(_("Tax ID must be 13 digits!"))

    @api.one
    @api.constrains('taxbranch')
    def _check_taxbranch(self):
        if self.require_taxbranch and self.taxbranch > 0 and \
                len(self.taxbranch) != 5:
            raise ValidationError("Tax Branch ID must be 5 digits!")

    @api.one
    @api.constrains('is_company', 'parent_id', 'child_ids')
    def _check_is_company(self):
        if not self.is_company and self.child_ids:
            raise ValidationError(_("A contact must not have child companies"))

    @api.model
    def create(self, vals):
        partner = super(ResPartner, self).create(vals)
        # Always use same tag as parent.
        if vals.get('parent_id', False):
            partner.category_id = partner.parent_id.category_id
        return partner

    @api.model
    def _pre_category_change(self, vals):
        # Do not allow change of partner tag,
        # if it result in change of its accounting
        check = self.env['ir.config_parameter'].\
            get_param('res_partner_ext.no_partner_tag_change_account')
        check = check and check.lower() or 'false'
        if check == 'true' and vals.get('category_id', False):
            # Test whether index exists to prevent exception
            category = vals.get('category_id')
            if not category:
                return
            for partner in self:
                prev_categ = partner.category_id
                new_category_id = category
                new_categ = \
                    self.env['res.partner.category'].browse(new_category_id)
                if prev_categ:
                    if ((prev_categ.receivable_account_id !=
                         new_categ.receivable_account_id) or
                        (prev_categ.payable_account_id !=
                         new_categ.payable_account_id)):
                        raise ValidationError(
                            _("Changing of Partner Tag is not allowed, as it "
                              "will result in changing of its account code"))

    @api.model
    def _post_category_change(self, vals):
        # Parent's tag change, force change to all childs
        if vals.get('category_id', False):
            for partner in self:
                if partner.child_ids:
                    for child in partner.child_ids:
                        child.category_id = partner.category_id

    @api.multi
    def write(self, vals):
        self._pre_category_change(vals)
        res = super(ResPartner, self).write(vals)
        self._post_category_change(vals)
        return res

    @api.v7
    def onchange_address(self, cr, uid, ids,
                         use_parent_address, parent_id, context=None):
        result = super(ResPartner, self).\
            onchange_address(
                cr,
                uid,
                ids,
                use_parent_address,
                parent_id,
                context=context
            )
        parent = self.browse(cr, uid, parent_id, context=context)
        category_id = parent.category_id.id or False
        if category_id:
            if result.get('value', False):
                result['value'].update(
                    {'category_id': category_id})
            else:
                result.update(
                    {'value': {'category_id': category_id}})
        return result

    @api.one
    @api.depends('category_id')
    def _get_single_category_id(self):
        if self.category_id:
            self.single_category_id = self.category_id.id

    @api.one
    @api.depends('category_id', 'parent_id')
    def _get_require_taxbranch(self):
        if self.parent_id:  # If a contact, never set as required.
            self.require_taxid = False
            self.require_taxbranch = False
        elif self.single_category_id:
            self.require_taxid = self.single_category_id.require_taxid
            self.require_taxbranch = self.single_category_id.require_taxbranch

    @api.one
    @api.depends('category_id')
    def _is_government(self):
        # TODO: set False for now
        self.is_government = False

    @api.one
    @api.depends('name')
    def _get_search_key(self):
        if type(self.id) in (int,):
            self.search_key = '%0*d' % (7, self.id)

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id:
            if self.category_id.receivable_account_id:
                self.property_account_receivable = \
                    self.category_id.receivable_account_id.id
            if self.category_id.payable_account_id:
                self.property_account_payable = \
                    self.category_id.payable_account_id.id
            if self.category_id.fiscal_position_id:
                self.property_account_position = \
                    self.category_id.fiscal_position_id.id
        else:
            self.property_account_receivable = False
            self.property_account_payable = False
            self.property_account_position = False

    @api.multi
    def name_get(self):
        """ Overwrite method, just to add Title """
        res = []
        for record in self:
            if record.title:
                name = "%s %s" % (record.title.name, record.name)
            else:
                name = record.name
            if record.parent_id and not record.is_company:
                name = "%s, %s" % (record.parent_name, name)
            if self._context.get('show_address_only'):
                name = self._display_address(record, without_company=True)
            if self._context.get('show_address'):
                name = name + "\n" + \
                    self._display_address(record, without_company=True)
            name = name.replace('\n\n', '\n')
            name = name.replace('\n\n', '\n')
            if self._context.get('show_email') and record.email:
                name = "%s <%s>" % (name, record.email)
            res.append((record.id, name))
        return res


class ResPartnerCategory(models.Model):

    _inherit = 'res.partner.category'

    parent_id = fields.Many2one(
        'res.partner.category',
        domain="[('parent_id', '=', False)]",
    )
    payable_account_id = fields.Many2one(
        'account.account',
        string='Account Payable',
        domain="[('type', '=', 'payable')]",
        help="This account will be used as default payable account "
        "for a partner, when it is being created.",)
    receivable_account_id = fields.Many2one(
        'account.account',
        string='Account Receivable',
        domain="[('type', '=', 'receivable')]",
        help="This account will be used as default receivable account "
        "for a partner, when it is being created.",)
    require_taxid = fields.Boolean(
        string='Require Tax ID',
        default=False,
        help="When create partner in this category, always require Tax ID")
    require_taxbranch = fields.Boolean(
        string='Require Tax Branch ID',
        default=False,
        help="When create partner in this category, "
        "always require TTax Branch ID")
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position',
        string='Default Fiscal Position',
        help="For customer with this Partner Tag, "
        "it will be default with this Fiscal Position",
    )
    require_tax_branch_unique = fields.Boolean(
        string='Validate Tax/Branch Unique',
        help="Non-Government, checking this flag will ensure that Tax ID "
        "and Branch combination must be unique per company of this category")

    @api.multi
    def name_get(self):
        res = []
        for category in self:
            res.append((category.id, category.name))
        return res


class ResPartnerTag(models.Model):
    _description = 'Partner Tags'
    _name = 'res.partner.tag'

    name = fields.Char(
        string='Name',
        required=True,
    )
    parent_id = fields.Many2one(
        'res.partner.tag',
        string='Parent Tag',
    )
    child_ids = fields.One2many(
        'res.partner.tag',
        'parent_id',
        string='Child Tags',
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )
