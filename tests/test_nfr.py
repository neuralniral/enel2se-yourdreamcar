"""Non-functional requirement checks (NFR-01, NFR-02, NFR-04, NFR-05)."""
import re
import time

from tests.base import AppTestCase, START, END
from app.billing.calculator import calculate_bill
from app.booking.routes import save_booking_and_invoice
from app.db import get_db
from app.utils import parse_date

TIME_LIMIT_SECONDS = 3.0


class NonFunctionalTests(AppTestCase):
    def test_billing_module_does_not_depend_on_flask(self):
        """TC-08 | Unit | NFR-05 | The billing module imports nothing from Flask, so it can change on its own."""
        with open("app/billing/calculator.py", encoding="utf-8") as source:
            self.assertIsNone(re.search(r"^\s*(from|import)\s+flask", source.read(), re.M))

    def test_second_confirmation_for_same_vehicle_is_refused(self):
        """TC-15 | Integration | NFR-04 | The save step re-checks availability: a second booking for the same dates is refused."""
        bill = calculate_bill(950, START, END)
        with self.app.app_context():
            first = save_booking_and_invoice(1, 2, None, parse_date(START), parse_date(END), bill)
            second = save_booking_and_invoice(3, 2, None, parse_date(START), parse_date(END), bill)
            count = get_db().execute("SELECT COUNT(*) FROM Bookings").fetchone()[0]
        self.assertIsNotNone(first)
        self.assertIsNone(second)
        self.assertEqual(count, 1)

    def test_catalogue_loads_within_three_seconds(self):
        """TC-24 | System | NFR-01 | The vehicle catalogue loads in under 3 seconds (average of 20 requests)."""
        start = time.perf_counter()
        for _ in range(20):
            self.assertEqual(self.client.get("/vehicles").status_code, 200)
        average = (time.perf_counter() - start) / 20
        print("  catalogue average: {:.1f} ms".format(average * 1000))
        self.assertLess(average, TIME_LIMIT_SECONDS)

    def test_booking_takes_five_screens_or_fewer(self):
        """TC-25 | System | NFR-02 | A logged-in, approved customer can finish a booking in 5 screens or fewer."""
        self.login("demo@customer.test", "demo123")
        screens = 0
        self.assertEqual(self.client.get("/vehicles").status_code, 200)               # 1 catalogue
        screens += 1
        self.assertEqual(self.client.get("/vehicles/2").status_code, 200)             # 2 vehicle details
        screens += 1
        self.assertEqual(self.client.get("/booking/new?vehicle_id=2").status_code, 200)   # 3 booking form
        screens += 1
        r = self.client.post("/booking/new", data=self.booking_data("preview"))       # 4 bill
        self.assertIn(b"Your itemised bill", r.data)
        screens += 1
        r = self.client.post("/booking/new", data=self.booking_data("confirm"))
        self.assertEqual(self.client.get(r.headers["Location"]).status_code, 200)     # 5 confirmation
        screens += 1
        self.assertLessEqual(screens, 5)
