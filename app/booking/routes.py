"""Booking Module routes (Niral) - FR-04, FR-07, FR-09. This implements UC-02 (and UC-05 for admins).

The booking page has two steps, both posted to /booking/new:
    1. action = "preview"  - check dates, availability and delivery, then show the itemised bill
    2. action = "confirm"  - check again, then save the booking and invoice
The second check is needed because someone else may have booked the car in between.
"""
from datetime import date

from flask import (Blueprint, abort, current_app, flash, redirect, render_template,
                   request, url_for)

from ..auth.service import admin_required, current_user, customer_required
from ..billing.calculator import calculate_bill
from ..db import get_db
from ..inventory import service as inventory
from ..models import VERIFICATION_APPROVED
from ..utils import parse_date, rows_to_list

bp = Blueprint("booking", __name__)

# One query that joins the tables to get everything about a booking in a single row.
# LEFT JOIN keeps the booking when there is no delivery zone or no invoice.
BOOKING_QUERY = """
    SELECT b.*, c.fullName AS customerName, v.make, v.model, z.areaName,
           i.invoiceID, i.baseAmount, i.deliveryFee, i.tax, i.totalAmount
    FROM Bookings b
    JOIN Customers c ON c.customerID = b.customerID
    JOIN Vehicles v ON v.vehicleID = b.vehicleID
    LEFT JOIN DeliveryZones z ON z.zoneID = b.zoneID
    LEFT JOIN Invoices i ON i.bookingID = b.bookingID
"""


# --- Helper functions -----------------------------------------------------------------------
def show_form(vehicle, preview=None, alternatives=None):
    if alternatives is None:
        alternatives = []
    return render_template("booking/new.html", vehicle=vehicle, form=request.form, preview=preview,
                           alternatives=alternatives, zones=inventory.get_delivery_zones())


def read_dates_from_form():
    """Returns (start, end) as dates. Raises ValueError with a readable message if they are wrong."""
    try:
        start = parse_date(request.form.get("start_date"))
        end = parse_date(request.form.get("end_date"))
    except ValueError:
        raise ValueError("Please choose valid start and end dates.")
    if end <= start:
        raise ValueError("The end date must be after the start date.")
    if start < date.today():
        raise ValueError("The start date can't be in the past.")
    return start, end


def work_out_delivery():
    """Returns (zone_id, fee, note). If delivery is not possible the booking becomes self-collection."""
    if request.form.get("delivery") != "on":
        return None, 0.0, None
    available, zone_id, fee = inventory.check_delivery(request.form.get("address", ""))
    if available:
        return zone_id, fee, None
    return None, 0.0, "Delivery isn't available to that address. This booking will be self-collection."


def find_alternatives(vehicle_id, start, end):
    """Other vehicles that are free for the dates the customer asked for."""
    alternatives = []
    for other in inventory.get_all_vehicles():
        if other["vehicleID"] != vehicle_id and inventory.is_vehicle_available(other["vehicleID"], start, end):
            alternatives.append(other)
    return alternatives


def save_booking_and_invoice(customer_id, vehicle_id, zone_id, start, end, bill):
    """Saves the booking and its invoice. Returns the bookingID, or None if the car was just taken.

    The steps run in one transaction. BEGIN IMMEDIATE blocks other writers until we finish,
    so two customers cannot both pass the availability check and get the same car (NFR-04).
    """
    db = get_db()
    db.execute("BEGIN IMMEDIATE")
    try:
        if not inventory.is_vehicle_available(vehicle_id, start, end):
            db.execute("ROLLBACK")
            return None
        cursor = db.execute(
            "INSERT INTO Bookings (customerID, vehicleID, zoneID, startDate, endDate, "
            "deliveryRequested, status) VALUES (?, ?, ?, ?, ?, ?, 'Confirmed')",
            (customer_id, vehicle_id, zone_id, start.isoformat(), end.isoformat(),
             1 if zone_id else 0))
        booking_id = cursor.lastrowid
        db.execute(
            "INSERT INTO Invoices (bookingID, baseAmount, deliveryFee, tax, totalAmount) "
            "VALUES (?, ?, ?, ?, ?)",
            (booking_id, bill["base_amount"], bill["delivery_fee"], bill["tax"],
             bill["total"]))
        db.execute("COMMIT")
        return booking_id
    except Exception:
        db.execute("ROLLBACK")
        raise


# --- Routes ---------------------------------------------------------------------------------
@bp.route("/booking/new", methods=["GET", "POST"])
@customer_required
def new_booking():
    user = current_user()
    if user["verificationStatus"] != VERIFICATION_APPROVED:      # UC-02 alternative flow 1a
        flash("Your driver's licence must be approved before you can book.", "error")
        return redirect(url_for("auth.verify"))

    vehicle_id = request.values.get("vehicle_id", type=int)
    vehicle = inventory.get_vehicle(vehicle_id) if vehicle_id else None
    if vehicle is None:
        abort(404)

    if request.method == "GET":
        return show_form(vehicle)

    # --- the form was submitted (POST) ---
    try:
        start, end = read_dates_from_form()
    except ValueError as error:
        flash(str(error), "error")
        return show_form(vehicle)

    # UC-02 step 2 (alternative flow 2a): is the vehicle free for these dates?
    if not inventory.is_vehicle_available(vehicle_id, start, end):
        flash("That vehicle is not available for the selected dates.", "error")
        return show_form(vehicle, alternatives=find_alternatives(vehicle_id, start, end))

    # Steps 3-5: delivery, then the bill
    zone_id, fee, delivery_note = work_out_delivery()
    bill = calculate_bill(vehicle["dailyRate"], start, end, fee, current_app.config["TAX_RATE"])

    if request.form.get("action") != "confirm":
        preview = {"bill": bill, "delivery_note": delivery_note}
        return show_form(vehicle, preview=preview)

    # Steps 6-7: the customer pressed "Confirm booking"
    booking_id = save_booking_and_invoice(user["customerID"], vehicle_id, zone_id, start, end, bill)
    if booking_id is None:
        flash("Sorry, that vehicle was just booked by someone else.", "error")
        return redirect(url_for("inventory.vehicles"))
    flash("Booking confirmed!", "success")
    return redirect(url_for("booking.booking_detail", booking_id=booking_id))


@bp.route("/booking/<int:booking_id>")
def booking_detail(booking_id):
    user = current_user()
    if user is None:
        return redirect(url_for("auth.login"))

    row = get_db().execute(BOOKING_QUERY + " WHERE b.bookingID = ?", (booking_id,)).fetchone()
    if row is None:
        abort(404)
    # A customer may only open their own bookings. (Admins can open any.)
    if user["role"] == "customer" and row["customerID"] != user["customerID"]:
        abort(404)
    return render_template("booking/detail.html", b=dict(row))


@bp.route("/bookings")
@customer_required
def history():                                    # FR-07: rental history
    rows = get_db().execute(
        BOOKING_QUERY + " WHERE b.customerID = ? ORDER BY b.startDate DESC",
        (current_user()["customerID"],)).fetchall()
    return render_template("booking/history.html", bookings=rows_to_list(rows))


@bp.route("/admin/bookings")
@admin_required
def admin_bookings():                             # FR-09 / UC-05
    status = request.args.get("status", "")       # filters come from the URL: ?status=...
    date_from = request.args.get("from", "")
    date_to = request.args.get("to", "")

    # Add each filter only if the admin chose it. "1 = 1" lets every filter start with AND.
    query = BOOKING_QUERY + " WHERE 1 = 1"
    values = []
    if status != "":
        query += " AND b.status = ?"
        values.append(status)
    if date_from != "":
        query += " AND b.endDate > ?"
        values.append(date_from)
    if date_to != "":
        query += " AND b.startDate < ?"
        values.append(date_to)
    query += " ORDER BY b.startDate DESC"

    rows = get_db().execute(query, values).fetchall()
    return render_template("booking/admin_bookings.html", bookings=rows_to_list(rows),
                           status=status, date_from=date_from, date_to=date_to)
