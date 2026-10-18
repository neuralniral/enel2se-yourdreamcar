"""Create (or reset) database.db with the shared demo data.

    python seed.py

WARNING: this drops and recreates every table.
"""
from app import create_app
from app.db import init_db
from app.seed import seed_db

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        init_db()
        seed_db()
    print("Database reset and seeded.")
    print("  admin    : admin@yourdreamcar.test   / admin123")
    print("  customer : demo@customer.test        / demo123   (Approved)")
    print("  customer : pending@customer.test     / demo123   (Pending, blocked from booking)")
