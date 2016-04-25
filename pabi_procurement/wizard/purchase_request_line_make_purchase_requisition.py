# -*- coding: utf-8 -*-
# © 2015 TrinityRoots
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import fields, models, api, _
from openerp.exceptions import Warning as UserError
import ast


class PurchaseRequestLineMakePurchaseRequisition(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.requisition"

    @api.model
    def _get_requisition_line_search_domain(self, requisition, item):
        res = super(PurchaseRequestLineMakePurchaseRequisition, self).\
            _get_requisition_line_search_domain(requisition, item)
        res.append(('id', '=', item.id))  # Use id will ensure no merge
        return res

    @api.model
    def _prepare_purchase_requisition_line(self, pr, item):
        res = super(PurchaseRequestLineMakePurchaseRequisition, self).\
            _prepare_purchase_requisition_line(pr, item)
        taxes = [(4, tax.id) for tax in item.line_id.tax_ids]
        res.update({
            'price_unit': item.price_unit,
            'product_name': item.name,
            'tax_ids': taxes
        })
        return res

    @api.model
    def _prepare_purchase_requisition(self, picking_type_id, company_id):
        res = super(PurchaseRequestLineMakePurchaseRequisition, self).\
            _prepare_purchase_requisition(picking_type_id, company_id)
        pr_line_obj = self.env['purchase.request.line']
        active_id = self._context['active_ids'][0]
        req_id = pr_line_obj.browse(active_id).request_id
        vals = {
            'user_id': req_id.responsible_user_id.id,
            'description': req_id.description,
            'objective': req_id.objective,
            'currency_id': req_id.currency_id.id,
            'currency_rate': req_id.currency_rate,
            'purchase_type_id': req_id.purchase_type_id.id,
            'purchase_method_id': req_id.purchase_method_id.id,
            'total_budget_value': req_id.total_budget_value,
            'purchase_prototype_id': req_id.purchase_prototype_id.id,
        }
        res.update(vals)
        return res

    @api.model
    def _prepare_item(self, line):
        res = super(PurchaseRequestLineMakePurchaseRequisition, self).\
            _prepare_item(line)
        res.update({'price_unit': line.price_unit,
                    'tax_ids': line.tax_ids.ids})
        return res

    @api.model
    def _prepare_attachment_line(self, line, requisition_id):
        return {
            'requisition_id': requisition_id,
            'name': line.name,
            'file_url': line.file_url,
            'file': line.file,
        }

    @api.model
    def _prepare_committee_line(self, line, requisition_id):
        return {
            'requisition_id': requisition_id,
            'name': line.name,
            'sequence': line.sequence,
            'responsible': line.responsible,
            'position': line.position,
            'committee_type': line.committee_type,
        }

    @api.model
    def _prepare_all_attachments(self, requisition, requests):
        attachments = []
        for request in requests:
            for line in request.attachment_ids:
                attachment_line = self._prepare_attachment_line(line,
                                                                requisition.id)
                attachments.append([0, False, attachment_line])
        return attachments

    @api.model
    def _prepare_all_committees(self, requisition, requests):
        committees = []
        for request in requests:
            for line in request.committee_ids:
                committee_line = self._prepare_committee_line(line,
                                                              requisition.id)
                committees.append([0, False, committee_line])
        return committees

    @api.multi
    def check_status_request_line(self):
        for item in self.item_ids:
            if item.request_id.state != 'approved':
                raise UserError(
                    _("Some Request hasn't been accepted yet : %s"
                      % (item.request_id.name,))
                )
        return True

    @api.multi
    def make_purchase_requisition(self):
        res = False
        if self.check_status_request_line():
            res = super(PurchaseRequestLineMakePurchaseRequisition, self).\
                make_purchase_requisition()
            domain = ast.literal_eval(res['domain'])
            requisition_id = list(set(domain[0][2]))[0]
            requisition = self.env['purchase.requisition'].\
                browse(requisition_id)
            requests = [item.line_id.request_id for item in self.item_ids]
            requests = list(set(requests))  # remove duplicated requests
            # Merge attachment and committee into Purchase Requisition
            committees = self._prepare_all_committees(requisition, requests)
            attachments = self._prepare_all_attachments(requisition, requests)
            requisition.write({
                'committee_ids': committees,
                'attachment_ids': attachments
            })
        return res


class PurchaseRequestLineMakePurchaseRequisitionItem(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.requisition.item"

    price_unit = fields.Float(
        'Unit Price',
        track_visibility='onchange',
    )
    tax_ids = fields.Many2many(
        'account.tax',
        'purchase_request_make_requisition_taxes_rel',
        'item_id',
        'tax_id',
        string='Taxes',
        readonly=True,
    )
