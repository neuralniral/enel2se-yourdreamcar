"""Shared test setup: every test gets its own fresh, seeded temporary database."""
import os
import shutil
import tempfile
import unittest
from datetime import date, timedelta

from app import create_app
from app.db import init_db
from app.seed import seed_db

START = (date.today() + timedelta(days=5)).isoformat()
END = (date.today() + timedelta(days=8)).isoformat()      # 3 days


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.app = create_app({
            "TESTING": True,
            "DATABASE": os.path.join(self.tmp, "test.db"),
            "UPLOAD_FOLDER": os.path.join(self.tmp, "uploads"),
        })
        with self.app.app_context():
            init_db()
            seed_db()
        self.client = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def login(self, email, password, client=None):
        return (client or self.client).post("/login", data={"email": email, "password": password})

    def admin_client(self):
        admin = self.app.test_client()
        self.login("admin@yourdreamcar.test", "admin123", client=admin)
        return admin

    def booking_data(self, action, vehicle_id=2, **extra):
        data = {"vehicle_id": vehicle_id, "start_date": START, "end_date": END, "action": action}
        data.update(extra)
        return data
