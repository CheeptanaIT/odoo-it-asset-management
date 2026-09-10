# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ItamMaintenanceLog(models.Model):
    _name = "itam.maintenance.log"
    _description = "IT Asset Maintenance Log"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "request_date desc, id desc"

    name = fields.Char(
        string="Reference", default=lambda self: _("New"), copy=False, readonly=True
    )
    asset_id = fields.Many2one(
        "itam.asset", string="Asset", required=True, ondelete="cascade", index=True, tracking=True
    )
    company_id = fields.Many2one(related="asset_id.company_id", store=True)
    currency_id = fields.Many2one(related="company_id.currency_id")
    maintenance_type = fields.Selection(
        [
            ("preventive", "Preventive"),
            ("corrective", "Corrective"),
            ("upgrade", "Upgrade"),
            ("inspection", "Inspection"),
        ],
        default="corrective", required=True, tracking=True,
    )
    state = fields.Selection(
        [
            ("new", "New"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        default="new", required=True, tracking=True,
    )
    request_date = fields.Date(default=fields.Date.context_today, required=True, tracking=True)
    date_start = fields.Date()
    date_done = fields.Date()
    handled_by = fields.Selection(
        [("internal", "Internal"), ("vendor", "Vendor")], default="internal"
    )
    technician_id = fields.Many2one("res.users", string="Technician")
    vendor_id = fields.Many2one("res.partner", string="Vendor")
    under_warranty = fields.Boolean(
        compute="_compute_under_warranty", store=True, readonly=False, tracking=True
    )
    cost = fields.Monetary(currency_field="currency_id")
    description = fields.Text()
    resolution = fields.Text()
    asset_state_before = fields.Char(copy=False)

    @api.depends("asset_id", "asset_id.warranty_start", "asset_id.warranty_end", "request_date")
    def _compute_under_warranty(self):
        for log in self:
            asset = log.asset_id
            date = log.request_date
            if not asset.warranty_end or not date:
                log.under_warranty = False
                continue
            start_ok = (not asset.warranty_start) or asset.warranty_start <= date
            log.under_warranty = start_ok and date <= asset.warranty_end

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("itam.maintenance.log") or _("New")
        return super().create(vals_list)

    def action_start(self):
        for log in self:
            if log.state != "new":
                continue
            log.asset_state_before = log.asset_id.state
            log.write({"state": "in_progress", "date_start": fields.Date.context_today(self)})
            if log.asset_id.state in ("available", "assigned"):
                log.asset_id.state = "in_repair"

    def action_done(self):
        for log in self:
            if log.state not in ("new", "in_progress"):
                continue
            log.write({"state": "done", "date_done": fields.Date.context_today(self)})
            if log.asset_id.state == "in_repair":
                previous = log.asset_state_before
                if previous not in ("available", "assigned"):
                    previous = "assigned" if log.asset_id.assigned_employee_id else "available"
                log.asset_id.state = previous

    def action_cancel(self):
        for log in self:
            log.state = "cancelled"
            if log.asset_id.state == "in_repair" and log.asset_state_before:
                log.asset_id.state = log.asset_state_before

    def action_reset(self):
        self.write({"state": "new"})
