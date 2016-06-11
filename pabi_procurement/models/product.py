# -*- coding: utf-8 -*-

from openerp import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    sale_ok = fields.Boolean(
        default=False,
    )
    cost_method = fields.Selection(
        default='average',
    )
