"""Authentication tests: registration, login, driver licence and password storage (FR-02, FR-03, NFR-03)."""
import io

from tests.base import AppTestCase
from app.db import get_db

NEW = {"full_name": "New Person", "email": "new@x.test", "password": "secret1"}


class AuthTests(AppTestCase):
    def _customer(self, email):
        with self.app.app_context():
            return get_db().execute("SELECT * FROM Customers WHERE email = ?", (email,)).fetchone()

    def test_register_creates_account_and_logs_in(self):
        """TC-11 | Integration | FR-02 | Registering creates a Pending customer and logs them in."""
        r = self.client.post("/register", data=NEW)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self._customer("new@x.test")["verificationStatus"], "Pending")
        self.assertIn(b"My bookings", self.client.get("/vehicles").data)

    def test_wrong_password_rejected(self):
        """TC-12 | Integration | FR-02 | A wrong password or unknown email is refused with one generic message."""
        for email, password in [("demo@customer.test", "wrong"), ("nobody@x.test", "demo123")]:
            r = self.client.post("/login", data={"email": email, "password": password})
            self.assertIn(b"Incorrect email or password", r.data)

    def test_licence_upload_sets_pending(self):
        """TC-13 | Integration | FR-03 | Uploading a licence stores the file; a wrong file type is refused."""
        self.client.post("/register", data=NEW)
        bad = self.client.post("/verify", data={"licence": (io.BytesIO(b"x"), "licence.exe")},
                               content_type="multipart/form-data", follow_redirects=True)
        self.assertIn(b"Allowed file types", bad.data)
        good = self.client.post("/verify", data={"licence": (io.BytesIO(b"%PDF-fake"), "licence.pdf")},
                                content_type="multipart/form-data", follow_redirects=True)
        self.assertIn(b"Licence uploaded", good.data)
        self.assertTrue(self._customer("new@x.test")["licenceDocumentPath"].endswith(".pdf"))

    def test_passwords_are_hashed(self):
        """TC-14 | Integration | NFR-03 | Stored passwords are hashes, not the text the customer typed."""
        stored = self._customer("demo@customer.test")["passwordHash"]
        self.assertNotIn("demo123", stored)
