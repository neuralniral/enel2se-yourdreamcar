"""Demo data, so everyone tests against the same records."""
from werkzeug.security import generate_password_hash

from .db import get_db


def seed_db():
    db = get_db()

    # Passwords are hashed (NFR-03), never stored as plain text.
    db.execute(
        "INSERT INTO Administrators (fullName, email, passwordHash) VALUES (?, ?, ?)",
        ("Site Admin", "admin@yourdreamcar.test", generate_password_hash("admin123")))

    db.execute(
        "INSERT INTO Customers (fullName, email, passwordHash, verificationStatus) VALUES (?, ?, ?, ?)",
        ("Demo Customer", "demo@customer.test", generate_password_hash("demo123"), "Approved"))
    db.execute(
        "INSERT INTO Customers (fullName, email, passwordHash, verificationStatus) VALUES (?, ?, ?, ?)",
        ("Pending Customer", "pending@customer.test", generate_password_hash("demo123"), "Pending"))

    # make, model, year, seats, transmission, fuelType, imagePath, dailyRate, status
    vehicles = [
        ("Volkswagen", "Polo Vivo", 2022, 5, "Manual", "Petrol", "pvivo.webp", 550, "Available"),
        ("Toyota", "Corolla Cross", 2023, 5, "Automatic", "Hybrid", "corollacross.png", 950, "Available"),
        ("Ford", "Ranger", 2022, 5, "Automatic", "Diesel", "ranger.webp", 1300, "Available"),
        ("Hyundai", "i20", 2021, 5, "Manual", "Petrol", "hyundai20.webp", 500, "Available"),
        ("BMW", "3 Series", 2021, 5, "Automatic", "Petrol", "bmwseries3.jpg", 1800, "Maintenance"),
    ]
    db.executemany(
        "INSERT INTO Vehicles (make, model, year, seats, transmission, fuelType, imagePath, dailyRate, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", vehicles)

    db.executemany(
        "INSERT INTO DeliveryZones (areaName, deliveryFee) VALUES (?, ?)",
        [("Umhlanga", 250), ("Berea", 150), ("Durban North", 200)])
