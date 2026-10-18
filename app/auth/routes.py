"""Authentication routes (Mishael): /register, /login, /logout, /verify, /admin/verifications.

GET shows a page, POST handles the submitted form."""
from flask import (Blueprint, abort, current_app, flash, redirect, render_template, request,
                   send_from_directory, url_for)

from ..db import get_db
from . import service
from .service import admin_required, current_user, customer_required

bp = Blueprint("auth", __name__)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            new_id = service.register_customer(
                request.form.get("full_name", ""),
                request.form.get("email", ""),
                request.form.get("password", ""))
            service.log_in("customer", new_id)
            flash("Account created. Upload your driver's licence to start booking.", "success")
            return redirect(url_for("auth.verify"))
        except ValueError as error:          # raised by register_customer for bad input
            flash(str(error), "error")
    return render_template("auth/register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        result = service.authenticate(request.form.get("email", ""), request.form.get("password", ""))
        if result is None:
            flash("Incorrect email or password.", "error")
        else:
            role, user_id = result
            service.log_in(role, user_id)
            if role == "admin":
                return redirect(url_for("booking.admin_bookings"))
            return redirect(url_for("inventory.vehicles"))
    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    service.log_in(None, None)
    flash("You have been logged out.", "success")
    return redirect(url_for("inventory.vehicles"))


@bp.route("/verify", methods=["GET", "POST"])
@customer_required
def verify():
    if request.method == "POST":
        try:
            service.save_licence(current_user()["customerID"], request.files.get("licence"))
            flash("Licence uploaded. An administrator will review it.", "success")
        except ValueError as error:
            flash(str(error), "error")
        return redirect(url_for("auth.verify"))
    return render_template("auth/verify.html")


@bp.route("/admin/verifications")
@admin_required
def admin_verifications():
    return render_template("auth/admin_verifications.html", pending=service.pending_verifications())


@bp.route("/admin/verifications/<int:customer_id>/<decision>", methods=["POST"])
@admin_required
def admin_decide(customer_id, decision):
    if decision == "approve":
        service.set_verification(customer_id, "Approved")
        flash("Customer approved.", "success")
    elif decision == "reject":
        service.set_verification(customer_id, "Rejected")
        flash("Customer rejected.", "success")
    else:
        abort(404)
    return redirect(url_for("auth.admin_verifications"))


@bp.route("/admin/verifications/<int:customer_id>/document")
@admin_required
def admin_document(customer_id):
    row = get_db().execute(
        "SELECT licenceDocumentPath FROM Customers WHERE customerID = ?", (customer_id,)).fetchone()
    if row is None or row["licenceDocumentPath"] is None:
        flash("No document on file.", "error")
        return redirect(url_for("auth.admin_verifications"))
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], row["licenceDocumentPath"])
