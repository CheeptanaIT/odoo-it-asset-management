# -*- coding: utf-8 -*-
{
    "name": "IT Asset Management",
    "version": "17.0.1.0.0",
    "summary": "Track IT hardware, assignments, software licenses and repairs",
    "description": """
Simple IT Asset Management (ITAM) for Odoo 17
=============================================
* Hardware asset register with asset tags, lifecycle and warranty tracking
* Assign / return assets to employees with a printable handover form
* Software license catalogue with seat usage tracking
* Maintenance / repair logs
* Automatic activity reminders before warranties and licenses expire
""",
    "author": "Custom Addon",
    "website": "https://example.com",
    "category": "Human Resources/IT Asset Management",
    "license": "LGPL-3",
    "depends": ["mail", "hr"],
    "data": [
        "security/itam_security.xml",
        "security/ir.model.access.csv",
        "data/itam_sequence.xml",
        "data/itam_category_data.xml",
        "data/itam_cron.xml",
        "wizard/itam_assign_wizard_views.xml",
        "report/itam_handover_report.xml",
        "report/itam_handover_templates.xml",
        "views/itam_asset_category_views.xml",
        "views/itam_location_views.xml",
        "views/itam_asset_views.xml",
        "views/itam_software_views.xml",
        "views/itam_software_license_views.xml",
        "views/itam_maintenance_log_views.xml",
        "views/hr_employee_views.xml",
        "views/res_config_settings_views.xml",
        "views/itam_menus.xml",
    ],
    "demo": [],
    "application": True,
    "installable": True,
}
