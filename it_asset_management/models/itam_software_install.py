# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ItamSoftwareInstall(models.Model):
    _name = "itam.software.install"
    _description = "Software Install / Seat"
    _order = "install_date desc, id desc"
    _rec_name = "license_id"

    license_id = fields.Many2one(
        "itam.software.license", string="License", required=True, ondelete="cascade", index=True
    )
    software_id = fields.Many2one(related="license_id.software_id", store=True)
    company_id = fields.Many2one(related="license_id.company_id", store=True)
    asset_id = fields.Many2one("itam.asset", string="Installed On", ondelete="cascade")
    employee_id = fields.Many2one("hr.employee", string="User")
    install_date = fields.Date(default=fields.Date.context_today, required=True)
    uninstall_date = fields.Date()
    is_active = fields.Boolean(compute="_compute_is_active", store=True)
    note = fields.Char()

    @api.depends("uninstall_date")
    def _compute_is_active(self):
        for rec in self:
            rec.is_active = not rec.uninstall_date

    @api.constrains("asset_id", "employee_id")
    def _check_target(self):
        for rec in self:
            if not rec.asset_id and not rec.employee_id:
                raise ValidationError(_("Set an asset or an employee for the install."))

    @api.constrains("license_id", "uninstall_date")
    def _check_seats(self):
        for rec in self:
            if rec.uninstall_date:
                continue
            lic = rec.license_id
            if lic.seats_total and lic.seats_used > lic.seats_total:
                raise ValidationError(
                    _("No seats left on license '%s' (%s/%s used).")
                    % (lic.name, lic.seats_used, lic.seats_total)
                )

    def action_uninstall(self):
        self.filtered(lambda r: not r.uninstall_date).write(
            {"uninstall_date": fields.Date.context_today(self)}
        )
