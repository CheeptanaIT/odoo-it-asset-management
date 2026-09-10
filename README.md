# IT Asset Management for Odoo 17

Two addons live in this folder:

| Module | Depends on | Edition |
|---|---|---|
| `it_asset_management` | `mail`, `hr` | Community or Enterprise |
| `itam_account_asset` | `it_asset_management`, `account_asset` | **Enterprise only** (optional bridge) |

## What it does

* **Hardware register** – asset tag (`ITAM/00001`, auto sequence), serial, category,
  manufacturer, hardware specs, photo, barcode.
* **Lifecycle** – Draft → Available → Assigned / In Repair → Retired / Disposed / Lost,
  driven from the form status bar.
* **Assignment** – assign / return an asset to an employee through a wizard; every
  hand-out is kept as history and can be printed as a **handover / return form** (PDF).
* **Software licenses** – catalogue of titles, licenses with seat counts, and per-seat
  installs on assets or employees. Seat usage bar + "no seats left" state; a seat over the
  limit is refused.
* **Maintenance logs** – preventive / corrective / upgrade / inspection jobs with cost,
  warranty flag, and a Start/Done flow that moves the asset in and out of *In Repair*.
* **Reminders** – a daily cron creates a To-Do activity a configurable number of days
  before a warranty or a license expires (idempotent – no duplicates).
* **Reporting** – pivot / graph on assets by category & status, and on maintenance cost.
* **Security** – *IT Asset Management / User* and *… / Manager* groups; multi-company
  record rules; decommission actions restricted to managers.
* English UI with a Thai translation (`i18n/th.po`).

## Install

1. Copy `it_asset_management/` (and optionally `itam_account_asset/`) into your Odoo
   addons path, e.g. `c:\xampp\htdocs\odoo\custom_addon`.
2. Add that path to `addons_path` in your Odoo config.
3. Update the app list and install **IT Asset Management**.

```
odoo -c odoo.conf -d <db> -i it_asset_management --stop-after-init
```

## Run the tests

```
odoo -c odoo.conf -d <db> -i it_asset_management --test-enable --stop-after-init
```

`it_asset_management/tests/test_itam_flow.py` covers the tag sequence, assign/return,
double-assignment guard, warranty state, license seats, the expiry cron, and the
maintenance state round-trip.

## Configuration

*IT Assets → Configuration*:
* **Categories** – default set (Laptop, Desktop, Monitor, Phone, Server, Network,
  Peripheral) is created on install.
* **Locations** – optional hierarchical places.
* **Settings** – warranty / license reminder lead time (days).
