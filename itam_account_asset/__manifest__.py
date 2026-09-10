# -*- coding: utf-8 -*-
{
    "name": "IT Asset Management - Accounting Bridge",
    "version": "18.0.1.0.0",
    "summary": "Link IT assets to accounting depreciation (account.asset)",
    "description": """
Bridge between IT Asset Management and Odoo Accounting Assets.
Adds a 'Create Depreciation' action on IT assets that creates and links an
account.asset record pre-filled from the purchase information.

Note: account_asset is an Odoo Enterprise module. Install this bridge only on
Enterprise databases.
""",
    "author": "Custom Addon",
    "category": "Human Resources/IT Asset Management",
    "license": "LGPL-3",
    "depends": ["it_asset_management", "account_asset"],
    "data": [
        "views/itam_asset_views.xml",
        "views/itam_asset_category_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
