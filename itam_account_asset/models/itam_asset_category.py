# -*- coding: utf-8 -*-
from odoo import fields, models


class ItamAssetCategory(models.Model):
    _inherit = "itam.asset.category"

    account_asset_model_id = fields.Many2one(
        "account.asset",
        string="Depreciation Model",
        domain="[('state', '=', 'model')]",
        help="Accounting asset model used as a template when creating the linked "
        "depreciation asset for this category.",
    )
