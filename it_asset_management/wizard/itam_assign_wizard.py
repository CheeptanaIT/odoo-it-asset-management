# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError

CONDITION_SELECTION = [
    ("new", "New"),
    ("good", "Good"),
    ("fair", "Fair"),
    ("poor", "Poor"),
    ("damaged", "Damaged"),
]


class ItamAssignWizard(models.TransientModel):
    _name = "itam.assign.wizard"
    _description = "Assign / Return IT Asset"

    mode = fields.Selection(
        [("assign", "Assign"), ("return", "Return")], required=True, default="assign"
    )
    asset_id = fields.Many2one("itam.asset", required=True, readonly=True)
    employee_id = fields.Many2one("hr.employee", string="Employee")
    location_id = fields.Many2one("itam.location", string="Location")
    date = fields.Date(required=True, default=fields.Date.context_today)
    condition = fields.Selection(CONDITION_SELECTION, default="good")
    note = fields.Text()
    print_form = fields.Boolean(string="Print Handover Form", default=True)

    @api.onchange("asset_id")
    def _onchange_asset_id(self):
        if self.mode == "return" and self.asset_id:
            self.location_id = self.asset_id.location_id

    def action_confirm(self):
        self.ensure_one()
        if self.mode == "assign":
            return self._do_assign()
        return self._do_return()

    def _do_assign(self):
        asset = self.asset_id
        if asset.state not in ("draft", "available"):
            raise UserError(_("This asset is not available for assignment."))
        if not self.employee_id:
            raise UserError(_("Select an employee to assign the asset to."))
        assignment = self.env["itam.asset.assignment"].create({
            "asset_id": asset.id,
            "employee_id": self.employee_id.id,
            "location_id": self.location_id.id or False,
            "date_out": self.date,
            "condition_out": self.condition,
            "note": self.note,
        })
        asset.state = "assigned"
        if self.location_id:
            asset.location_id = self.location_id
        asset.message_post(
            body=_("Assigned to %s on %s.") % (self.employee_id.display_name, self.date)
        )
        return self._maybe_print(assignment)

    def _do_return(self):
        asset = self.asset_id
        open_line = asset.assignment_ids.filtered(lambda a: not a.date_in)[:1]
        if not open_line:
            raise UserError(_("This asset has no open assignment to return."))
        open_line.write({
            "date_in": self.date,
            "condition_in": self.condition,
            "location_id": self.location_id.id or open_line.location_id.id,
            "note": self.note or open_line.note,
        })
        asset.state = "available"
        asset.message_post(body=_("Returned on %s.") % self.date)
        return self._maybe_print(open_line)

    def _maybe_print(self, assignment):
        if self.print_form:
            return self.env.ref(
                "it_asset_management.action_report_itam_handover"
            ).report_action(assignment)
        return {"type": "ir.actions.act_window_close"}
