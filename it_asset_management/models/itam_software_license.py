# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models

LICENSE_LEAD_PARAM = "it_asset_management.license_lead_days"
REMINDER_TAG = "[ITAM]"


class ItamSoftwareLicense(models.Model):
    _name = "itam.software.license"
    _description = "Software License"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "expiry_date, name"

    name = fields.Char(required=True, tracking=True)
    software_id = fields.Many2one(
        "itam.software", string="Software", required=True, ondelete="restrict", tracking=True
    )
    license_key = fields.Char(copy=False, groups="it_asset_management.group_itam_user")
    license_type = fields.Selection(
        [
            ("perpetual", "Perpetual"),
            ("subscription", "Subscription"),
            ("oem", "OEM"),
            ("volume", "Volume"),
            ("open_source", "Open Source"),
            ("trial", "Trial"),
        ],
        default="subscription", tracking=True,
    )
    seats_total = fields.Integer(string="Seats", default=1, tracking=True)
    seats_used = fields.Integer(compute="_compute_seats", store=True)
    seats_available = fields.Integer(compute="_compute_seats", store=True)
    seat_usage = fields.Float(
        string="Seat Usage (%)", compute="_compute_seats", store=True, group_operator="avg"
    )

    purchase_date = fields.Date(tracking=True)
    expiry_date = fields.Date(tracking=True)
    vendor_id = fields.Many2one("res.partner", string="Vendor")
    purchase_price = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(related="company_id.currency_id")
    invoice_ref = fields.Char()

    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True, index=True
    )
    state = fields.Selection(
        [
            ("active", "Active"),
            ("expiring", "Expiring Soon"),
            ("expired", "Expired"),
            ("depleted", "No Seats Left"),
        ],
        compute="_compute_state", store=True, tracking=True,
    )
    install_ids = fields.One2many("itam.software.install", "license_id", string="Installs")
    active = fields.Boolean(default=True)
    note = fields.Text()

    _sql_constraints = [
        ("seats_positive", "CHECK(seats_total >= 0)", "Seats cannot be negative."),
    ]

    @api.depends("seats_total", "install_ids.uninstall_date")
    def _compute_seats(self):
        for lic in self:
            used = len(lic.install_ids.filtered(lambda i: not i.uninstall_date))
            lic.seats_used = used
            lic.seats_available = lic.seats_total - used
            lic.seat_usage = (used / lic.seats_total * 100.0) if lic.seats_total else 0.0

    @api.depends("expiry_date", "seats_available")
    def _compute_state(self):
        today = fields.Date.context_today(self)
        lead = self.env["itam.asset"]._get_lead_days(LICENSE_LEAD_PARAM)
        for lic in self:
            if lic.expiry_date and lic.expiry_date < today:
                lic.state = "expired"
            elif lic.seats_available <= 0 and lic.seats_total:
                lic.state = "depleted"
            elif lic.expiry_date and lic.expiry_date <= today + relativedelta(days=lead):
                lic.state = "expiring"
            else:
                lic.state = "active"

    @api.model
    def _remind_license_expiry(self):
        today = fields.Date.context_today(self)
        lead = self.env["itam.asset"]._get_lead_days(LICENSE_LEAD_PARAM)
        limit = today + relativedelta(days=lead)
        if not self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False):
            return
        licenses = self.search([
            ("expiry_date", "!=", False),
            ("expiry_date", ">=", today),
            ("expiry_date", "<=", limit),
        ])
        manager = self.env.ref("it_asset_management.group_itam_manager", raise_if_not_found=False)
        fallback = manager.users[0] if manager and manager.users else self.env.user
        for lic in licenses:
            summary = _("%s License '%s' expires on %s") % (REMINDER_TAG, lic.name, lic.expiry_date)
            if lic.activity_ids.filtered(lambda a: a.summary == summary):
                continue
            lic.activity_schedule(
                act_type_xmlid="mail.mail_activity_data_todo",
                summary=summary,
                note=_("Renew or decommission this software license."),
                user_id=(lic.create_uid or fallback).id,
                date_deadline=lic.expiry_date,
            )

    def action_view_installs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Installs"),
            "res_model": "itam.software.install",
            "view_mode": "tree,form",
            "domain": [("license_id", "=", self.id)],
            "context": {"default_license_id": self.id},
        }
