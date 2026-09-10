# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

WARRANTY_LEAD_PARAM = "it_asset_management.warranty_lead_days"
LICENSE_LEAD_PARAM = "it_asset_management.license_lead_days"
REMINDER_TAG = "[ITAM]"


class ItamAsset(models.Model):
    _name = "itam.asset"
    _description = "IT Asset"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "asset_tag desc, id desc"

    # --- Identity -----------------------------------------------------------
    name = fields.Char(
        string="Description", required=True, tracking=True,
        help="Human readable name, e.g. 'Dell Latitude 5440'.",
    )
    asset_tag = fields.Char(
        string="Asset Tag", default=lambda self: _("New"), copy=False,
        readonly=True, index=True, tracking=True,
    )
    serial_no = fields.Char(string="Serial Number", copy=False, tracking=True)
    barcode = fields.Char(copy=False, help="Optional scan code; defaults to the asset tag.")
    image_1920 = fields.Image(string="Photo", max_width=1920, max_height=1920)
    image_128 = fields.Image(related="image_1920", max_width=128, max_height=128, store=True)

    # --- Classification ---------------------------------------------------
    category_id = fields.Many2one(
        "itam.asset.category", string="Category", required=True, tracking=True,
        ondelete="restrict",
    )
    manufacturer = fields.Char(tracking=True)
    model_number = fields.Char(string="Model")
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True, index=True
    )
    currency_id = fields.Many2one(related="company_id.currency_id")
    active = fields.Boolean(default=True)
    color = fields.Integer()

    # --- Lifecycle ------------------------------------------------------
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("available", "Available"),
            ("assigned", "Assigned"),
            ("in_repair", "In Repair"),
            ("retired", "Retired"),
            ("disposed", "Disposed"),
            ("lost", "Lost"),
        ],
        default="draft", required=True, tracking=True, group_expand="_group_expand_state",
    )

    # --- Hardware -----------------------------------------------------
    cpu = fields.Char(string="CPU")
    ram_gb = fields.Integer(string="RAM (GB)")
    storage = fields.Char(string="Storage")
    operating_system = fields.Char(string="Operating System")
    hostname = fields.Char()
    ip_address = fields.Char(string="IP Address")
    mac_address = fields.Char(string="MAC Address")

    # --- Current assignment (mirrors the open assignment line) -----------
    assignment_ids = fields.One2many("itam.asset.assignment", "asset_id", string="Assignment History")
    assigned_employee_id = fields.Many2one(
        "hr.employee", string="Assigned To", compute="_compute_current_assignment",
        store=True, tracking=True,
    )
    assigned_department_id = fields.Many2one(
        "hr.department", string="Department", compute="_compute_current_assignment", store=True
    )
    location_id = fields.Many2one("itam.location", string="Location", tracking=True)
    assigned_date = fields.Date(
        string="Assigned Since", compute="_compute_current_assignment", store=True
    )
    assignment_count = fields.Integer(compute="_compute_counts")

    # --- Purchase & warranty ---------------------------------------------
    purchase_date = fields.Date(tracking=True)
    purchase_price = fields.Monetary(currency_field="currency_id", tracking=True)
    vendor_id = fields.Many2one("res.partner", string="Vendor", tracking=True)
    invoice_ref = fields.Char(string="Invoice Reference")
    po_ref = fields.Char(string="PO Reference")
    warranty_start = fields.Date()
    warranty_end = fields.Date(tracking=True)
    warranty_provider = fields.Char()
    warranty_state = fields.Selection(
        [
            ("no_warranty", "No Warranty"),
            ("valid", "Valid"),
            ("expiring", "Expiring Soon"),
            ("expired", "Expired"),
        ],
        compute="_compute_warranty_state", store=True, tracking=True,
    )

    # --- Related records -----------------------------------------------
    maintenance_log_ids = fields.One2many("itam.maintenance.log", "asset_id", string="Maintenance Logs")
    maintenance_count = fields.Integer(compute="_compute_counts")
    software_install_ids = fields.One2many("itam.software.install", "asset_id", string="Software")
    software_count = fields.Integer(compute="_compute_counts")

    note = fields.Html()

    _sql_constraints = [
        ("asset_tag_uniq", "unique(asset_tag, company_id)", "The asset tag must be unique per company."),
        ("ram_positive", "CHECK(ram_gb >= 0)", "RAM cannot be negative."),
    ]

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends(
        "assignment_ids.date_in", "assignment_ids.date_out",
        "assignment_ids.employee_id",
    )
    def _compute_current_assignment(self):
        for asset in self:
            open_line = asset.assignment_ids.filtered(lambda a: not a.date_in)[:1]
            asset.assigned_employee_id = open_line.employee_id
            asset.assigned_department_id = open_line.department_id
            asset.assigned_date = open_line.date_out

    @api.depends("warranty_end")
    def _compute_warranty_state(self):
        today = fields.Date.context_today(self)
        lead = self._get_lead_days(WARRANTY_LEAD_PARAM)
        for asset in self:
            if not asset.warranty_end:
                asset.warranty_state = "no_warranty"
            elif asset.warranty_end < today:
                asset.warranty_state = "expired"
            elif asset.warranty_end <= today + relativedelta(days=lead):
                asset.warranty_state = "expiring"
            else:
                asset.warranty_state = "valid"

    @api.depends("assignment_ids", "maintenance_log_ids",
                 "software_install_ids", "software_install_ids.uninstall_date")
    def _compute_counts(self):
        for asset in self:
            asset.assignment_count = len(asset.assignment_ids)
            asset.maintenance_count = len(asset.maintenance_log_ids)
            asset.software_count = len(
                asset.software_install_ids.filtered(lambda i: not i.uninstall_date)
            )

    @api.model
    def _group_expand_state(self, states, domain, order):
        return [key for key, _label in self._fields["state"].selection]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _get_lead_days(self, param):
        value = self.env["ir.config_parameter"].sudo().get_param(param, "30")
        try:
            return max(int(value), 0)
        except (TypeError, ValueError):
            return 30

    def _close_open_assignment(self, date=None, condition=None, note=None):
        self.ensure_one()
        open_line = self.assignment_ids.filtered(lambda a: not a.date_in)[:1]
        if open_line:
            open_line.write({
                "date_in": date or fields.Date.context_today(self),
                "condition_in": condition or open_line.condition_in,
                "note": note or open_line.note,
            })
        return open_line

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("asset_tag", _("New")) == _("New"):
                seq = self.env["ir.sequence"].next_by_code("itam.asset") or "/"
                vals["asset_tag"] = seq
            if not vals.get("barcode"):
                vals["barcode"] = vals.get("asset_tag")
        return super().create(vals_list)

    def copy(self, default=None):
        default = dict(default or {})
        default.setdefault("asset_tag", _("New"))
        default.setdefault("barcode", False)
        default.setdefault("serial_no", False)
        return super().copy(default)

    # ------------------------------------------------------------------
    # State actions
    # ------------------------------------------------------------------
    def action_set_available(self):
        for asset in self:
            if asset.state not in ("draft", "in_repair", "assigned"):
                raise UserError(_("Only draft, assigned or in-repair assets can be set to available."))
            if asset.state == "assigned":
                asset._close_open_assignment()
            asset.state = "available"

    def action_open_assign_wizard(self):
        self.ensure_one()
        if self.state not in ("draft", "available"):
            raise UserError(_("This asset is not available for assignment."))
        return self._open_assign_wizard("assign")

    def action_open_return_wizard(self):
        self.ensure_one()
        if self.state != "assigned":
            raise UserError(_("This asset is not currently assigned."))
        return self._open_assign_wizard("return")

    def _open_assign_wizard(self, mode):
        return {
            "type": "ir.actions.act_window",
            "name": _("Assign Asset") if mode == "assign" else _("Return Asset"),
            "res_model": "itam.assign.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_asset_id": self.id, "default_mode": mode},
        }

    def action_send_to_repair(self):
        for asset in self:
            if asset.state not in ("available", "assigned"):
                raise UserError(_("Only available or assigned assets can go into repair."))
            asset.state = "in_repair"

    def action_return_from_repair(self):
        for asset in self:
            if asset.state != "in_repair":
                continue
            asset.state = "assigned" if asset.assigned_employee_id else "available"

    def action_retire(self):
        self._decommission("retired", _("Asset retired."))

    def action_dispose(self):
        self._decommission("disposed", _("Asset disposed."))

    def action_mark_lost(self):
        self._decommission("lost", _("Asset marked as lost."))

    def _decommission(self, state, message):
        for asset in self:
            asset._close_open_assignment(note=message)
            asset.write({"state": state, "active": False})
            asset.message_post(body=message)

    def action_reactivate(self):
        for asset in self:
            asset.write({"state": "available", "active": True})

    # --- Smart buttons ---------------------------------------------------
    def action_view_assignments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Assignment History"),
            "res_model": "itam.asset.assignment",
            "view_mode": "tree,form",
            "domain": [("asset_id", "=", self.id)],
            "context": {"default_asset_id": self.id},
        }

    def action_view_maintenance(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Maintenance Logs"),
            "res_model": "itam.maintenance.log",
            "view_mode": "tree,form,calendar",
            "domain": [("asset_id", "=", self.id)],
            "context": {"default_asset_id": self.id},
        }

    def action_view_software(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Software Installs"),
            "res_model": "itam.software.install",
            "view_mode": "tree,form",
            "domain": [("asset_id", "=", self.id)],
            "context": {"default_asset_id": self.id},
        }

    # ------------------------------------------------------------------
    # Reminders (cron entry point)
    # ------------------------------------------------------------------
    @api.model
    def _cron_expiry_reminder(self):
        self._remind_asset_warranties()
        self.env["itam.software.license"]._remind_license_expiry()

    @api.model
    def _remind_asset_warranties(self):
        today = fields.Date.context_today(self)
        lead = self._get_lead_days(WARRANTY_LEAD_PARAM)
        limit = today + relativedelta(days=lead)
        assets = self.search([
            ("warranty_end", "!=", False),
            ("warranty_end", ">=", today),
            ("warranty_end", "<=", limit),
            ("state", "not in", ("retired", "disposed", "lost")),
        ])
        if not self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False):
            return
        for asset in assets:
            summary = _("%s Warranty expires on %s") % (REMINDER_TAG, asset.warranty_end)
            if asset.activity_ids.filtered(lambda a: a.summary == summary):
                continue
            user = asset._reminder_user()
            asset.activity_schedule(
                act_type_xmlid="mail.mail_activity_data_todo",
                summary=summary,
                note=_("The manufacturer warranty for this asset is about to expire."),
                user_id=user.id,
                date_deadline=asset.warranty_end,
            )

    def _reminder_user(self):
        self.ensure_one()
        if self.assigned_employee_id.user_id:
            return self.assigned_employee_id.user_id
        manager = self.env.ref("it_asset_management.group_itam_manager", raise_if_not_found=False)
        if manager and manager.users:
            return manager.users[0]
        return self.create_uid or self.env.user
