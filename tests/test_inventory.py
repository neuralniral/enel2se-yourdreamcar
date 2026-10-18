"""Inventory tests: availability, delivery zones and administrator management."""
from tests.base import AppTestCase
from app.db import get_db
from app.inventory import service


class AvailabilityTests(AppTestCase):
    def _book(self, vehicle_id, start, end):
        get_db().execute(
            "INSERT INTO Bookings (customerID, vehicleID, startDate, endDate) VALUES (1, ?, ?, ?)",
            (vehicle_id, start, end))

    def test_overlap_is_rejected(self):
        """TC-04 | Unit | FR-04, NFR-04 | Any overlap with an existing booking is rejected (4 patterns)."""
        with self.app.app_context():
            self.assertTrue(service.is_vehicle_available(1, "2026-11-01", "2026-11-04"))
            self._book(1, "2026-11-01", "2026-11-05")
            for s, e in [("2026-11-03", "2026-11-06"), ("2026-10-30", "2026-11-02"),
                         ("2026-11-02", "2026-11-04"), ("2026-10-30", "2026-11-10")]:
                self.assertFalse(service.is_vehicle_available(1, s, e), (s, e))

    def test_back_to_back_is_allowed(self):
        """TC-05 | Unit | FR-04 | A booking may start on the day the previous one ends (end date is exclusive)."""
        with self.app.app_context():
            self._book(1, "2026-11-01", "2026-11-05")
            self.assertTrue(service.is_vehicle_available(1, "2026-11-05", "2026-11-08"))
            self.assertTrue(service.is_vehicle_available(1, "2026-10-28", "2026-11-01"))

    def test_delivery_zone_matching(self):
        """TC-06 | Unit | FR-05 | An address containing a zone name (any letter case) gets that zone's fee."""
        with self.app.app_context():
            ok, zone_id, fee = service.check_delivery("12 Beach Rd, umhlanga, 4319")
            self.assertTrue(ok)
            self.assertEqual(fee, 250)

    def test_delivery_outside_zones(self):
        """TC-07 | Unit | FR-05 | An address outside every zone, or only a partial word match, gets no delivery."""
        with self.app.app_context():
            self.assertEqual(service.check_delivery("1 Main St, Pietermaritzburg"), (False, None, 0.0))
            self.assertEqual(service.check_delivery("4 Bereavement Road"), (False, None, 0.0))


class AdminInventoryTests(AppTestCase):
    """Administrator vehicle and delivery-zone management (FR-08)."""

    def _one(self, sql, args=()):
        with self.app.app_context():
            return get_db().execute(sql, args).fetchone()

    def test_admin_adds_vehicle(self):
        """TC-09 | Integration | FR-08, FR-01 | An administrator can add a vehicle and customers then see it."""
        data = {"make": "Kia", "model": "Picanto", "year": "2023", "seats": "4", "transmission": "Manual",
                "fuelType": "Petrol", "dailyRate": "450", "status": "Available"}
        self.admin_client().post("/admin/vehicles", data=data)
        self.assertIsNotNone(self._one("SELECT 1 FROM Vehicles WHERE model = 'Picanto'"))
        self.assertIn(b"Picanto", self.client.get("/vehicles").data)

    def test_admin_manages_delivery_zones(self):
        """TC-10 | Integration | FR-08, FR-05 | An administrator can add a zone, change its fee and remove it."""
        admin = self.admin_client()
        admin.post("/admin/delivery-zones", data={"areaName": "Pinetown", "deliveryFee": "300"})
        zone_id = self._one("SELECT zoneID FROM DeliveryZones WHERE areaName = 'Pinetown'")["zoneID"]
        admin.post(f"/admin/delivery-zones/{zone_id}/update", data={"deliveryFee": "320"})
        self.assertEqual(self._one("SELECT deliveryFee FROM DeliveryZones WHERE zoneID = ?", (zone_id,))[0], 320)
        admin.post(f"/admin/delivery-zones/{zone_id}/delete")
        self.assertIsNone(self._one("SELECT 1 FROM DeliveryZones WHERE zoneID = ?", (zone_id,)))
