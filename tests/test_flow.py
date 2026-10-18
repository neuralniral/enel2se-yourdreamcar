"""Integration and system tests: they use the app like a browser (log in, post forms, read pages)."""
import io
from datetime import date, timedelta

from tests.base import AppTestCase, START, END
from app.db import get_db


class BookingFlowTests(AppTestCase):
    def test_full_booking_with_delivery(self):
        """TC-16 | System | FR-04, FR-05, FR-06, FR-07 | Book a vehicle with delivery: bill, confirmation, invoice and history."""
        self.login("demo@customer.test", "demo123")
        r = self.client.post("/booking/new", data=self.booking_data(
            "preview", delivery="on", address="12 Beach Rd, Umhlanga"))
        self.assertIn(b"3,565.00", r.data)  # (950*3 + 250) * 1.15
        r = self.client.post("/booking/new", data=self.booking_data(
            "confirm", delivery="on", address="12 Beach Rd, Umhlanga"))
        self.assertEqual(r.status_code, 302)
        page = self.client.get(r.headers["Location"])
        self.assertIn(b"3,565.00", page.data)
        self.assertIn(b"Umhlanga", page.data)
        self.assertIn(b"Corolla Cross", self.client.get("/bookings").data)

    def test_unverified_customer_blocked(self):
        """TC-17 | System | FR-03, FR-04 | A customer who is not Approved is sent to the verification page."""
        self.login("pending@customer.test", "demo123")
        r = self.client.post("/booking/new", data=self.booking_data("confirm"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/verify", r.headers["Location"])
        with self.app.app_context():
            self.assertEqual(get_db().execute("SELECT COUNT(*) FROM Bookings").fetchone()[0], 0)

    def test_delivery_outside_zone_falls_back_to_self_collection(self):
        """TC-18 | System | FR-05, FR-06 | Delivery to an address outside the zones becomes self-collection, no fee."""
        self.login("demo@customer.test", "demo123")
        r = self.client.post("/booking/new", data=self.booking_data(
            "preview", delivery="on", address="1 Main St, Pietermaritzburg"))
        self.assertIn(b"self-collection", r.data)
        self.assertIn(b"3,277.50", r.data)  # 2850 * 1.15

    def test_history_shows_only_own_bookings(self):
        """TC-19 | System | FR-07 | The rental history lists the customer's own bookings and nobody else's."""
        self.login("demo@customer.test", "demo123")
        self.client.post("/booking/new", data=self.booking_data("confirm"))
        self.assertIn(b"Corolla Cross", self.client.get("/bookings").data)
        other = self.app.test_client()
        self.login("pending@customer.test", "demo123", client=other)
        self.assertNotIn(b"Corolla Cross", other.get("/bookings").data)

    def test_admin_can_list_and_filter_bookings(self):
        """TC-20 | System | FR-09 | An administrator can see all bookings and filter them by status."""
        self.login("demo@customer.test", "demo123")
        self.client.post("/booking/new", data=self.booking_data("confirm"))
        admin = self.admin_client()
        self.assertIn(b"Demo Customer", admin.get("/admin/bookings").data)
        self.assertIn(b"Demo Customer", admin.get("/admin/bookings?status=Confirmed").data)
        self.assertNotIn(b"Demo Customer", admin.get("/admin/bookings?status=Cancelled").data)

    def test_customer_cannot_reach_admin_pages(self):
        """TC-21 | System | FR-08, FR-09 | Admin pages redirect a customer to the login page."""
        self.login("demo@customer.test", "demo123")
        for url in ("/admin/bookings", "/admin/vehicles", "/admin/verifications", "/admin/delivery-zones"):
            self.assertEqual(self.client.get(url).status_code, 302, url)

    def test_register_upload_and_admin_approval(self):
        """TC-22 | System | FR-02, FR-03, FR-04 | New customer registers, uploads a licence, is approved, then can book."""
        self.client.post("/register", data={"full_name": "New Person", "email": "new@x.test", "password": "secret1"})
        self.client.post("/verify", data={"licence": (io.BytesIO(b"%PDF-fake"), "licence.pdf")},
                         content_type="multipart/form-data")
        admin = self.admin_client()
        self.assertIn(b"New Person", admin.get("/admin/verifications").data)
        self.assertEqual(admin.post("/admin/verifications/2/maybe").status_code, 404)   # invalid decision
        with self.app.app_context():
            cid = get_db().execute("SELECT customerID FROM Customers WHERE email='new@x.test'").fetchone()[0]
        admin.post(f"/admin/verifications/{cid}/approve")
        r = self.client.post("/booking/new", data=self.booking_data("preview"))
        self.assertIn(b"Your itemised bill", r.data)

    def test_vehicle_pages_show_booked_status_and_images(self):
        """TC-23 | System | FR-01 | The catalogue shows photos and the Booked status; the detail page lists booked dates."""
        with self.app.app_context():
            get_db().execute(
                "INSERT INTO Bookings (customerID, vehicleID, startDate, endDate) VALUES (1, 1, ?, ?)",
                ((date.today() - timedelta(days=1)).isoformat(), (date.today() + timedelta(days=2)).isoformat()))
        page = self.client.get("/vehicles").data
        self.assertIn(b"Booked", page)
        self.assertIn(b"pvivo.webp", page)
        self.assertIn(b"Already booked on", self.client.get("/vehicles/1").data)
