# -*- coding: utf-8 -*-
from datetime import date, timedelta

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestItamFlow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.category = cls.env["itam.asset.category"].create({"name": "Test Laptop", "code": "TL"})
        cls.employee = cls.env["hr.employee"].create({"name": "Alice Tester"})
        cls.employee2 = cls.env["hr.employee"].create({"name": "Bob Tester"})
        cls.asset = cls.env["itam.asset"].create({
            "name": "ThinkPad X1",
            "category_id": cls.category.id,
        })

    # ------------------------------------------------------------------
    def test_asset_tag_sequence(self):
        self.assertTrue(self.asset.asset_tag.startswith("ITAM/"))
        self.assertEqual(self.asset.barcode, self.asset.asset_tag)
        copy = self.asset.copy()
        self.assertNotEqual(copy.asset_tag, self.asset.asset_tag)
        self.assertTrue(copy.asset_tag.startswith("ITAM/"))

    def _assign(self, asset, employee, assign_date=None):
        wiz = self.env["itam.assign.wizard"].create({
            "mode": "assign",
            "asset_id": asset.id,
            "employee_id": employee.id,
            "date": assign_date or date.today(),
            "print_form": False,
        })
        wiz.action_confirm()

    def test_assign_and_return(self):
        self.asset.action_set_available()
        self._assign(self.asset, self.employee)
        self.assertEqual(self.asset.state, "assigned")
        self.assertEqual(self.asset.assigned_employee_id, self.employee)
        open_lines = self.asset.assignment_ids.filtered(lambda a: not a.date_in)
        self.assertEqual(len(open_lines), 1)

        wiz = self.env["itam.assign.wizard"].create({
            "mode": "return",
            "asset_id": self.asset.id,
            "date": date.today(),
            "condition": "good",
            "print_form": False,
        })
        wiz.action_confirm()
        self.assertEqual(self.asset.state, "available")
        self.assertFalse(self.asset.assigned_employee_id)
        self.assertTrue(all(a.date_in for a in self.asset.assignment_ids))

    def test_double_open_assignment_blocked(self):
        self.asset.action_set_available()
        self._assign(self.asset, self.employee)
        with self.assertRaises(ValidationError):
            self.env["itam.asset.assignment"].create({
                "asset_id": self.asset.id,
                "employee_id": self.employee2.id,
                "date_out": date.today(),
            })

    # ------------------------------------------------------------------
    def test_warranty_state(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "it_asset_management.warranty_lead_days", "30"
        )
        no_w = self.env["itam.asset"].create({"name": "NW", "category_id": self.category.id})
        self.assertEqual(no_w.warranty_state, "no_warranty")

        valid = self.env["itam.asset"].create({
            "name": "V", "category_id": self.category.id,
            "warranty_end": date.today() + timedelta(days=200),
        })
        self.assertEqual(valid.warranty_state, "valid")

        expiring = self.env["itam.asset"].create({
            "name": "E", "category_id": self.category.id,
            "warranty_end": date.today() + timedelta(days=10),
        })
        self.assertEqual(expiring.warranty_state, "expiring")

        expired = self.env["itam.asset"].create({
            "name": "X", "category_id": self.category.id,
            "warranty_end": date.today() - timedelta(days=1),
        })
        self.assertEqual(expired.warranty_state, "expired")

    # ------------------------------------------------------------------
    def test_license_seats(self):
        software = self.env["itam.software"].create({"name": "Office"})
        lic = self.env["itam.software.license"].create({
            "name": "Office VL", "software_id": software.id, "seats_total": 2,
        })
        self.env["itam.software.install"].create({"license_id": lic.id, "employee_id": self.employee.id})
        self.env["itam.software.install"].create({"license_id": lic.id, "employee_id": self.employee2.id})
        self.assertEqual(lic.seats_used, 2)
        self.assertEqual(lic.seats_available, 0)
        self.assertEqual(lic.state, "depleted")
        with self.assertRaises(ValidationError):
            self.env["itam.software.install"].create({"license_id": lic.id, "asset_id": self.asset.id})

    # ------------------------------------------------------------------
    def test_cron_reminder_idempotent(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "it_asset_management.warranty_lead_days", "30"
        )
        asset = self.env["itam.asset"].create({
            "name": "Soon", "category_id": self.category.id, "state": "available",
            "warranty_end": date.today() + timedelta(days=5),
        })
        self.env["itam.asset"]._cron_expiry_reminder()
        first = asset.activity_ids
        self.assertEqual(len(first), 1)
        self.env["itam.asset"]._cron_expiry_reminder()
        self.assertEqual(asset.activity_ids, first)

    # ------------------------------------------------------------------
    def test_maintenance_state_roundtrip(self):
        self.asset.action_set_available()
        self._assign(self.asset, self.employee)
        log = self.env["itam.maintenance.log"].create({
            "asset_id": self.asset.id, "maintenance_type": "corrective",
        })
        self.assertTrue(log.name.startswith("ITAM/MNT/"))
        log.action_start()
        self.assertEqual(self.asset.state, "in_repair")
        log.action_done()
        self.assertEqual(self.asset.state, "assigned")
