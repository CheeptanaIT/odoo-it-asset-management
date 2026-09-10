# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ItamLocation(models.Model):
    _name = "itam.location"
    _description = "IT Asset Location"
    _parent_store = True
    _parent_name = "parent_id"
    _order = "complete_name"

    name = fields.Char(required=True)
    parent_id = fields.Many2one(
        "itam.location", string="Parent Location", ondelete="cascade", index=True
    )
    parent_path = fields.Char(index=True, unaccent=False)
    complete_name = fields.Char(
        compute="_compute_complete_name", recursive=True, store=True
    )
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    asset_ids = fields.One2many("itam.asset", "location_id", string="Assets")
    asset_count = fields.Integer(compute="_compute_asset_count")
    note = fields.Text()
    active = fields.Boolean(default=True)

    @api.depends("name", "parent_id.complete_name")
    def _compute_complete_name(self):
        for loc in self:
            if loc.parent_id:
                loc.complete_name = "%s / %s" % (loc.parent_id.complete_name, loc.name)
            else:
                loc.complete_name = loc.name

    @api.depends("complete_name")
    def _compute_display_name(self):
        for loc in self:
            loc.display_name = loc.complete_name or loc.name

    @api.depends("asset_ids")
    def _compute_asset_count(self):
        data = self.env["itam.asset"]._read_group(
            [("location_id", "in", self.ids)], ["location_id"], ["__count"]
        )
        mapped = {loc.id: count for loc, count in data}
        for loc in self:
            loc.asset_count = mapped.get(loc.id, 0)

    @api.constrains("parent_id")
    def _check_parent_recursion(self):
        if self._has_cycle():
            raise ValidationError(_("You cannot create recursive locations."))
