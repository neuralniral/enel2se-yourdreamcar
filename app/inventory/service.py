"""Inventory Module functions (Kovidh) - FR-01, FR-04 (availability), FR-05, FR-08.

The Booking module calls these directly:
    get_all_vehicles, get_vehicle, is_vehicle_available, check_delivery, get_delivery_zones

Date rule: the end date is exclusive. A booking 1 Nov -> 5 Nov is billed for 4 days and another
customer can start a booking on the 5th.

Customers see three statuses. Available and Maintenance are stored (an admin sets them).
Booked is not stored: it is worked out from the Bookings table, because it changes with the
calendar and a stored value would have to be reset every time a rental ended.
"""
import os
import re
import time
from datetime import date

from flask import current_app

from ..db import get_db
from ..models import VEHICLE_AVAILABLE, VEHICLE_BOOKED, VEHICLE_MAINTENANCE
from ..utils import parse_date, rows_to_list


# --- Reading vehicles -----------------------------------------------------------------------
def get_display_status(vehicle):
    """Returns (status, booked_until) for today, e.g. ("Booked", "2026-10-23") or ("Available", None)."""
    if vehicle["status"] == VEHICLE_MAINTENANCE:
        return VEHICLE_MAINTENANCE, None

    today = date.today().isoformat()
    row = get_db().execute(
        "SELECT endDate FROM Bookings "
        "WHERE vehicleID = ? AND status = 'Confirmed' AND startDate <= ? AND endDate > ?",
        (vehicle["vehicleID"], today, today)).fetchone()
    if row is not None:
        return VEHICLE_BOOKED, row["endDate"]
    return VEHICLE_AVAILABLE, None


def add_status_info(vehicle):
    """Adds two keys to the vehicle dictionary: displayStatus and bookedUntil."""
    status, booked_until = get_display_status(vehicle)
    vehicle["displayStatus"] = status
    vehicle["bookedUntil"] = booked_until
    return vehicle


def get_all_vehicles():
    rows = get_db().execute("SELECT * FROM Vehicles ORDER BY make, model").fetchall()
    vehicles = []
    for row in rows:
        vehicles.append(add_status_info(dict(row)))
    return vehicles


def get_vehicle(vehicle_id):
    """Returns one vehicle as a dictionary, or None if it doesn't exist."""
    row = get_db().execute("SELECT * FROM Vehicles WHERE vehicleID = ?", (vehicle_id,)).fetchone()
    if row is None:
        return None
    return add_status_info(dict(row))


def get_upcoming_bookings(vehicle_id):
    """Date ranges already taken (today or later). Shown on the vehicle page."""
    rows = get_db().execute(
        "SELECT startDate, endDate FROM Bookings "
        "WHERE vehicleID = ? AND status = 'Confirmed' AND endDate > ? ORDER BY startDate",
        (vehicle_id, date.today().isoformat())).fetchall()
    return rows_to_list(rows)


# --- Availability for a date range (FR-04, NFR-04) ------------------------------------------
def is_vehicle_available(vehicle_id, start, end):
    """True if the vehicle can be booked for start -> end.

    Two ranges overlap when each starts before the other ends:
        existing.startDate < new.end   AND   existing.endDate > new.start
    """
    # ISO dates ("2026-11-05") sort in date order, so they can be compared as text
    start = parse_date(start).isoformat()
    end = parse_date(end).isoformat()
    db = get_db()

    vehicle = db.execute(
        "SELECT status FROM Vehicles WHERE vehicleID = ?", (vehicle_id,)).fetchone()
    if vehicle is None or vehicle["status"] != VEHICLE_AVAILABLE:
        return False

    clash = db.execute(
        "SELECT bookingID FROM Bookings WHERE vehicleID = ? AND status != 'Cancelled' "
        "AND startDate < ? AND endDate > ?",
        (vehicle_id, end, start)).fetchone()
    return clash is None


def has_active_booking(vehicle_id):
    """True if the vehicle has a confirmed booking that hasn't finished yet."""
    row = get_db().execute(
        "SELECT bookingID FROM Bookings WHERE vehicleID = ? AND status = 'Confirmed' AND endDate > ?",
        (vehicle_id, date.today().isoformat())).fetchone()
    return row is not None


# --- Delivery (FR-05) -----------------------------------------------------------------------
def get_delivery_zones():
    rows = get_db().execute("SELECT * FROM DeliveryZones ORDER BY areaName").fetchall()
    return rows_to_list(rows)


def check_delivery(address):
    """Returns (available, zone_id, fee). A zone matches if its name is in the address."""
    address = (address or "").lower()
    for zone in get_delivery_zones():
        # \b = word boundary, so the zone "Berea" does not match "Bereavement Road"
        name = re.escape(zone["areaName"].lower())
        if re.search(r"\b" + name + r"\b", address):
            return True, zone["zoneID"], zone["deliveryFee"]
    return False, None, 0.0


# --- Vehicle photos -------------------------------------------------------------------------
def save_vehicle_image(vehicle_id, uploaded_file):
    """Saves an uploaded photo into static/images/vehicles/. Raises ValueError for a bad file type."""
    if "." not in uploaded_file.filename:
        raise ValueError("Images must be PNG, JPG or WEBP.")
    extension = uploaded_file.filename.rsplit(".", 1)[1].lower()
    if extension not in current_app.config["IMAGE_EXTENSIONS"]:
        raise ValueError("Images must be PNG, JPG or WEBP.")

    folder = os.path.join(current_app.static_folder, "images", "vehicles")
    # The timestamp in the name stops the browser showing an old cached picture.
    new_name = "vehicle_" + str(vehicle_id) + "_" + str(int(time.time())) + "." + extension
    uploaded_file.save(os.path.join(folder, new_name))

    db = get_db()
    old = db.execute("SELECT imagePath FROM Vehicles WHERE vehicleID = ?", (vehicle_id,)).fetchone()
    db.execute("UPDATE Vehicles SET imagePath = ? WHERE vehicleID = ?", (new_name, vehicle_id))

    # Delete the previous uploaded photo (the sample images that ship with the project are kept)
    if old is not None and old["imagePath"] is not None and old["imagePath"].startswith("vehicle_"):
        old_file = os.path.join(folder, old["imagePath"])
        if os.path.exists(old_file):
            os.remove(old_file)
