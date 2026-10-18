"""Unit tests for the billing formulas (FR-06).  Run: python -m unittest discover -s tests -t ."""
import unittest

from config import TAX_RATE
from app.billing.calculator import calculate_bill


class BillingTests(unittest.TestCase):
    def test_three_days_no_delivery(self):
        """TC-01 | Unit | FR-06 | Three-day bill with no delivery: R1000 x 3 + 15% tax = R3450."""
        b = calculate_bill(1000, "2026-10-20", "2026-10-23", 0, tax_rate=0.15)
        self.assertEqual(b["duration"], 3)
        self.assertEqual(b["base_amount"], 3000.00)
        self.assertEqual(b["tax"], 450.00)
        self.assertEqual(b["total"], 3450.00)

    def test_delivery_fee_is_taxed(self):
        """TC-02 | Unit | FR-06 | The delivery fee is taxed too, and the tax rate comes from config.py."""
        b = calculate_bill(950, "2026-10-20", "2026-10-23", 250, tax_rate=0.15)
        self.assertEqual(b["tax"], 465.00)   # (2850 + 250) * 0.15
        self.assertEqual(b["total"], 3565.00)
        default = calculate_bill(1000, "2026-10-20", "2026-10-21")
        self.assertEqual(default["tax"], round(1000 * TAX_RATE, 2))

    def test_end_must_be_after_start(self):
        """TC-03 | Unit | FR-06 | An end date equal to or before the start date is rejected."""
        with self.assertRaises(ValueError):
            calculate_bill(500, "2026-10-20", "2026-10-20", 0, tax_rate=0.15)
        with self.assertRaises(ValueError):
            calculate_bill(500, "2026-10-20", "2026-10-19", 0, tax_rate=0.15)

    def test_default_tax_rate_comes_from_config(self):
        """TC-26 | Unit | FR-06 | When no tax rate is passed in, the rate in config.py is used."""
        b = calculate_bill(1000, "2026-10-20", "2026-10-21")
        self.assertEqual(b["tax"], round(1000 * TAX_RATE, 2))


if __name__ == "__main__":
    unittest.main()
