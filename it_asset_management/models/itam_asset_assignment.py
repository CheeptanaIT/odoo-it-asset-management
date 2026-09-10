# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

CONDITION_SELECTION = [
    ("new", "New"),
    ("good", "Good"),
    ("fair", "Fair"),
    ("poor", "Poor"),
    ("damaged", "Damaged"),
]


class ItamAssetAssignment(models.Model):
    _name = "itam.asset.assignment"
    _description = "IT Asset Assignment"
    _order = "date_out desc, id desc"
    _rec_name = "asset_id"

    asset_id = fields.Many2one(
        "itam.asset", string="Asset", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="asset_id.company_id", store=True)
    employee_id = fields.Many2one("hr.employee", string="Employee")
    department_id = fields.Many2one(
        "hr.department", string="Department", compute="_compute_department",
        store=True, readonly=False,
    )
    location_id = fields.Many2one("itam.location", string="Location")
    date_out = fields.Date(
        string="Assigned On", required=True, default=fields.Date.context_today
    )
    date_in = fields.Date(string="Returned On")
    condition_out = fields.Selection(CONDITION_SELECTION, string="Condition Out", default="good")
    condition_in = fields.Selection(CONDITION_SELECTION, string="Condition In")
    assigned_by = fields.Many2one(
        "res.users", string="Handled By", default=lambda self: self.env.user
    )
    is_open = fields.Boolean(compute="_compute_is_open", store=True, string="Currently Held")
    note = fields.Text()

    @api.depends("employee_id")
    def _compute_department(self):
        for rec in self:
            if rec.employee_id:
                rec.department_id = rec.employee_id.department_id

    @api.depends("date_in")
    def _compute_is_open(self):
        for rec in self:
            rec.is_open = not rec.date_in

    @api.constrains("date_out", "date_in")
    def _check_dates(self):
        for rec in self:
            if rec.date_in and rec.date_out and rec.date_in < rec.date_out:
                raise ValidationError(_("The return date cannot be before the assignment date."))

    @api.constrains("date_in", "asset_id")
    def _check_single_open(self):
        for rec in self:
            if rec.date_in:
                continue
            others = self.search_count([
                ("asset_id", "=", rec.asset_id.id),
                ("date_in", "=", False),
                ("id", "!=", rec.id),
            ])
            if others:
                raise ValidationError(
                    _("Asset %s already has an open assignment. Return it first.")
                    % rec.asset_id.display_name
                )

    def action_print_handover(self):
        return self.env.ref(
            "it_asset_management.action_report_itam_handover"
        ).report_action(self)
