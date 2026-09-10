# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    itam_asset_ids = fields.One2many("itam.asset", "assigned_employee_id", string="IT Assets")
    itam_asset_count = fields.Integer(compute="_compute_itam_asset_count")

    @api.depends("itam_asset_ids")
    def _compute_itam_asset_count(self):
        data = self.env["itam.asset"]._read_group(
            [("assigned_employee_id", "in", self.ids)], ["assigned_employee_id"], ["__count"]
        )
        mapped = {emp.id: count for emp, count in data}
        for emp in self:
            emp.itam_asset_count = mapped.get(emp.id, 0)

    def action_view_itam_assets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("IT Assets"),
            "res_model": "itam.asset",
            "view_mode": "tree,form,kanban",
            "domain": [("assigned_employee_id", "=", self.id)],
            "context": {"search_default_assigned_employee_id": self.id},
        }
