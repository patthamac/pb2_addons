# -*- coding: utf-8 -*-
# © <YEAR(S)> <AUTHOR(S)>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Sequence Number by Document Type",
    "summary": "",
    "version": "8.0.1.0.0",
    "category": "Accounting & Finance",
    "description": """

New menu, > Settings > Technical > Sequences & Identifiers > Doctype

For, Customer Payment, Supplier Payment, Sales Receipt and Purchase Receipt.

If Sequence is specified, document will be using this sequence instead of
sequence of Journal. Journal's sequence will still be used for Journal Entries

If Sequence is not specified, it will be using sequence of Journal as normal.

    """,
    "website": "https://ecosoft.co.th/",
    "author": "Kitti U.",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        'l10n_th_fields',
        'account_voucher',
        'account_voucher_action_move_line_create_hooks',
        'purchase_split_quote2order',
        'sale_split_quote2order',
        'hr_expense_advance_clearing',

    ],
    "data": [
        "security/ir.model.access.csv",
        "views/doctype_view.xml",
        "views/ir_sequence_view.xml",
        "data/ir_sequence_data.xml",
        "data/doctype_data.xml",
    ],
}
