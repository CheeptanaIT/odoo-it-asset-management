# -*- coding: utf-8 -*-
from odoo import _, fields, models
from odoo.exceptions import UserError


class ItamAsset(models.Model):
    _inherit = "itam.asset"

    account_asset_id = fields.Many2one(
        "account.asset", string="Depreciation Asset", copy=False, readonly=True
    )
    account_asset_state = fields.Selection(related="account_asset_id.state", string="Depreciation Status")
    account_asset_book_value = fields.Monetary(
        related="account_asset_id.book_value", string="Book Value", currency_field="currency_id"
    )

    def action_create_account_asset(self):
        self.ensure_one()
        if self.account_asset_id:
            return self._open_account_asset()
        if not self.purchase_price:
            raise UserError(_("Set a purchase price before creating a depreciation asset."))

        model = self.category_id.account_asset_model_id
        vals = {
            "name": "%s (%s)" % (self.name, self.asset_tag),
            "original_value": self.purchase_price,
            "acquisition_date": self.purchase_date or fields.Date.context_today(self),
            "company_id": self.company_id.id,
        }
        if model:
            vals["state"] = "draft"
            asset = model.copy(vals)
        else:
            years = self.category_id.default_depreciation_years or 3
            vals.update({
                "method_number": years,
                "method_period": "12",
            })
            asset = self.env["account.asset"].create(vals)
        self.account_asset_id = asset.id
        self.message_post(body=_("Linked to depreciation asset %s.") % asset.display_name)
        return self._open_account_asset()

    def _open_account_asset(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Depreciation Asset"),
            "res_model": "account.asset",
            "res_id": self.account_asset_id.id,
            "view_mode": "form",
        }
