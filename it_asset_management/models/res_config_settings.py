# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    itam_warranty_lead_days = fields.Integer(
        string="Warranty Reminder Lead (days)",
        default=30,
        config_parameter="it_asset_management.warranty_lead_days",
    )
    itam_license_lead_days = fields.Integer(
        string="License Reminder Lead (days)",
        default=30,
        config_parameter="it_asset_management.license_lead_days",
    )
