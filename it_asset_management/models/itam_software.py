# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ItamSoftware(models.Model):
    _name = "itam.software"
    _description = "Software Title"
    _order = "name"

    name = fields.Char(required=True)
    publisher = fields.Char()
    category = fields.Selection(
        [
            ("os", "Operating System"),
            ("productivity", "Productivity"),
            ("security", "Security"),
            ("developer", "Developer Tools"),
            ("design", "Design"),
            ("other", "Other"),
        ],
        default="other",
    )
    license_ids = fields.One2many("itam.software.license", "software_id", string="Licenses")
    license_count = fields.Integer(compute="_compute_license_count")
    active = fields.Boolean(default=True)
    note = fields.Text()

    @api.depends("license_ids")
    def _compute_license_count(self):
        data = self.env["itam.software.license"]._read_group(
            [("software_id", "in", self.ids)], ["software_id"], ["__count"]
        )
        mapped = {sw.id: count for sw, count in data}
        for sw in self:
            sw.license_count = mapped.get(sw.id, 0)

    def action_view_licenses(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Licenses"),
            "res_model": "itam.software.license",
            "view_mode": "tree,form,kanban",
            "domain": [("software_id", "=", self.id)],
            "context": {"default_software_id": self.id},
        }
