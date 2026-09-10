# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ItamAssetCategory(models.Model):
    _name = "itam.asset.category"
    _description = "IT Asset Category"
    _parent_store = True
    _parent_name = "parent_id"
    _order = "complete_name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(help="Short code used as a prefix on generated asset tags.")
    parent_id = fields.Many2one(
        "itam.asset.category", string="Parent Category", ondelete="cascade", index=True
    )
    parent_path = fields.Char(index=True, unaccent=False)
    complete_name = fields.Char(
        compute="_compute_complete_name", recursive=True, store=True
    )
    default_depreciation_years = fields.Integer(
        string="Depreciation Duration (years)",
        default=3,
        help="Default useful life proposed when creating a linked accounting asset.",
    )
    asset_ids = fields.One2many("itam.asset", "category_id", string="Assets")
    asset_count = fields.Integer(compute="_compute_asset_count")
    note = fields.Text()
    active = fields.Boolean(default=True)

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for cat in self:
            if cat.parent_id:
                cat.complete_name = "%s / %s" % (cat.parent_id.complete_name, cat.name)
            else:
                cat.complete_name = cat.name

    @api.depends("complete_name")
    def _compute_display_name(self):
        for cat in self:
            cat.display_name = cat.complete_name or cat.name

    @api.depends("asset_ids")
    def _compute_asset_count(self):
        data = self.env["itam.asset"]._read_group(
            [("category_id", "in", self.ids)], ["category_id"], ["__count"]
        )
        mapped = {cat.id: count for cat, count in data}
        for cat in self:
            cat.asset_count = mapped.get(cat.id, 0)

    @api.constrains("parent_id")
    def _check_parent_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_("You cannot create recursive categories."))

    def action_view_assets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Assets"),
            "res_model": "itam.asset",
            "view_mode": "tree,form,kanban",
            "domain": [("category_id", "child_of", self.id)],
            "context": {"default_category_id": self.id},
        }
