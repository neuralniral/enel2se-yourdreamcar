"""Inventory routes (Kovidh): /vehicles, /admin/vehicles, /admin/delivery-zones"""
import sqlite3

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..auth.service import admin_required
from ..db import get_db
from . import service

bp = Blueprint("inventory", __name__)


# --- Pages for customers (no login needed) --------------------------------------------------
@bp.route("/vehicles")
def vehicles():
    return render_template("inventory/vehicles.html", vehicles=service.get_all_vehicles())


@bp.route("/vehicles/<int:vehicle_id>")
def vehicle_detail(vehicle_id):
    vehicle = service.get_vehicle(vehicle_id)
    if vehicle is None:
        abort(404)
    return render_template("inventory/vehicle_detail.html", vehicle=vehicle,
                           upcoming=service.get_upcoming_bookings(vehicle_id))


# --- Administrator: vehicles ----------------------------------------------------------------
def read_vehicle_form():
    """Collects the vehicle fields from the submitted form."""
    form = request.form
    return {
        "make": form.get("make", "").strip(),
        "model": form.get("model", "").strip(),
        "year": form.get("year", type=int),            # None if left blank
        "seats": form.get("seats", type=int),
        "transmission": form.get("transmission", "").strip(),
        "fuelType": form.get("fuelType", "").strip(),
        "dailyRate": form.get("dailyRate", type=float),
        "status": form.get("status", "Available"),
    }


def vehicle_form_is_valid(vehicle):
    if vehicle["make"] == "" or vehicle["model"] == "":
        return False
    if vehicle["dailyRate"] is None or vehicle["dailyRate"] < 0:
        return False
    return vehicle["status"] in ("Available", "Maintenance")


def save_photo_if_given(vehicle_id):
    """Saves the photo if one was uploaded; shows a message if the file is rejected."""
    photo = request.files.get("image")
    if photo is not None and photo.filename != "":
        try:
            service.save_vehicle_image(vehicle_id, photo)
        except ValueError as error:
            flash(str(error), "error")


@bp.route("/admin/vehicles", methods=["GET", "POST"])
@admin_required
def admin_vehicles():
    if request.method == "POST":
        vehicle = read_vehicle_form()
        if not vehicle_form_is_valid(vehicle):
            flash("Make, model and a valid daily rate are required.", "error")
        else:
            cursor = get_db().execute(
                "INSERT INTO Vehicles (make, model, year, seats, transmission, fuelType, dailyRate, status) "
                "VALUES (:make, :model, :year, :seats, :transmission, :fuelType, :dailyRate, :status)",
                vehicle)
            save_photo_if_given(cursor.lastrowid)
            flash("Vehicle added.", "success")
        return redirect(url_for("inventory.admin_vehicles"))
    return render_template("inventory/admin_vehicles.html", vehicles=service.get_all_vehicles())


@bp.route("/admin/vehicles/<int:vehicle_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_vehicle_edit(vehicle_id):
    existing = service.get_vehicle(vehicle_id)
    if existing is None:
        abort(404)

    if request.method == "POST":
        vehicle = read_vehicle_form()
        if not vehicle_form_is_valid(vehicle):
            flash("Make, model and a valid daily rate are required.", "error")
        else:
            vehicle["vehicleID"] = vehicle_id
            get_db().execute(
                "UPDATE Vehicles SET make = :make, model = :model, year = :year, seats = :seats, "
                "transmission = :transmission, fuelType = :fuelType, dailyRate = :dailyRate, "
                "status = :status WHERE vehicleID = :vehicleID", vehicle)
            save_photo_if_given(vehicle_id)
            flash("Vehicle updated.", "success")
            return redirect(url_for("inventory.admin_vehicles"))
    return render_template("inventory/admin_vehicle_edit.html", vehicle=existing)


@bp.route("/admin/vehicles/<int:vehicle_id>/delete", methods=["POST"])
@admin_required
def admin_vehicle_delete(vehicle_id):
    if service.has_active_booking(vehicle_id):
        flash("This vehicle has an active booking. Set its status to Maintenance instead.", "error")
        return redirect(url_for("inventory.admin_vehicles"))
    try:
        get_db().execute("DELETE FROM Vehicles WHERE vehicleID = ?", (vehicle_id,))
        flash("Vehicle removed.", "success")
    except sqlite3.IntegrityError:
        # Foreign key: old bookings still point to this vehicle
        flash("This vehicle has booking history. Set its status to Maintenance instead.", "error")
    return redirect(url_for("inventory.admin_vehicles"))


# --- Administrator: delivery zones ----------------------------------------------------------
@bp.route("/admin/delivery-zones", methods=["GET", "POST"])
@admin_required
def admin_zones():
    if request.method == "POST":
        name = request.form.get("areaName", "").strip()
        fee = request.form.get("deliveryFee", type=float)
        if name == "" or fee is None or fee < 0:
            flash("Area name and a valid fee are required.", "error")
        else:
            try:
                get_db().execute("INSERT INTO DeliveryZones (areaName, deliveryFee) VALUES (?, ?)", (name, fee))
                flash("Delivery zone added.", "success")
            except sqlite3.IntegrityError:
                flash("That area already exists.", "error")
        return redirect(url_for("inventory.admin_zones"))
    return render_template("inventory/admin_zones.html", zones=service.get_delivery_zones())


@bp.route("/admin/delivery-zones/<int:zone_id>/update", methods=["POST"])
@admin_required
def admin_zone_update(zone_id):
    fee = request.form.get("deliveryFee", type=float)
    if fee is None or fee < 0:
        flash("Enter a valid fee.", "error")
    else:
        get_db().execute("UPDATE DeliveryZones SET deliveryFee = ? WHERE zoneID = ?", (fee, zone_id))
        flash("Fee updated.", "success")
    return redirect(url_for("inventory.admin_zones"))


@bp.route("/admin/delivery-zones/<int:zone_id>/delete", methods=["POST"])
@admin_required
def admin_zone_delete(zone_id):
    try:
        get_db().execute("DELETE FROM DeliveryZones WHERE zoneID = ?", (zone_id,))
        flash("Delivery zone removed.", "success")
    except sqlite3.IntegrityError:
        flash("This zone is used by existing bookings and can't be removed.", "error")
    return redirect(url_for("inventory.admin_zones"))
