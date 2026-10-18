"""Authentication Module functions (Mishael) - FR-02, FR-03, NFR-03.

Other modules import: login_required, admin_required, current_user.

Login state is kept in Flask's session (a signed cookie): session["role"] and session["user_id"].
"""
import os
import sqlite3
from functools import wraps

from flask import current_app, flash, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..db import get_db
from ..models import VERIFICATION_PENDING


def log_in(role, user_id):
    """Remembers who is logged in. log_in(None, None) logs the user out."""
    session.clear()
    if role is not None:
        session["role"] = role          # "customer" or "admin"
        session["user_id"] = user_id


def current_user():
    """Returns the logged-in user as a dictionary (with an extra "role" key), or None."""
    role = session.get("role")
    user_id = session.get("user_id")
    if role is None or user_id is None:
        return None

    db = get_db()
    if role == "customer":
        row = db.execute("SELECT * FROM Customers WHERE customerID = ?", (user_id,)).fetchone()
    else:
        row = db.execute("SELECT * FROM Administrators WHERE adminID = ?", (user_id,)).fetchone()
    if row is None:
        return None

    user = dict(row)
    user["role"] = role
    return user


# --- Decorators: put @customer_required or @admin_required above a route to protect it ----
def customer_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None or user["role"] != "customer":
            flash("Please log in as a customer to continue.", "error")
            return redirect(url_for("auth.login"))
        return route_function(*args, **kwargs)
    return wrapper


login_required = customer_required      # the name used in the shared contract


def admin_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None or user["role"] != "admin":
            flash("Administrator access required.", "error")
            return redirect(url_for("auth.login"))
        return route_function(*args, **kwargs)
    return wrapper


# --- Accounts -------------------------------------------------------------------------------
def register_customer(full_name, email, password):
    """Creates a customer and returns the new customerID. Raises ValueError if input is bad."""
    full_name = full_name.strip()
    email = email.strip().lower()
    if full_name == "" or "@" not in email:
        raise ValueError("Please enter your name and a valid email.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")

    try:
        cursor = get_db().execute(
            "INSERT INTO Customers (fullName, email, passwordHash) VALUES (?, ?, ?)",
            (full_name, email, generate_password_hash(password)))
    except sqlite3.IntegrityError:      # email is UNIQUE, so a duplicate fails
        raise ValueError("An account with that email already exists.")
    return cursor.lastrowid


def authenticate(email, password):
    """Returns (role, id) if the email and password are correct, otherwise None."""
    email = email.strip().lower()
    db = get_db()

    customer = db.execute("SELECT * FROM Customers WHERE email = ?", (email,)).fetchone()
    if customer is not None and check_password_hash(customer["passwordHash"], password):
        return "customer", customer["customerID"]

    admin = db.execute("SELECT * FROM Administrators WHERE email = ?", (email,)).fetchone()
    if admin is not None and check_password_hash(admin["passwordHash"], password):
        return "admin", admin["adminID"]

    return None


# --- Driver verification --------------------------------------------------------------------
def save_licence(customer_id, uploaded_file):
    """Saves the uploaded licence and sets the status to Pending. Raises ValueError if bad."""
    if uploaded_file is None or uploaded_file.filename == "":
        raise ValueError("Please choose a file.")
    if "." not in uploaded_file.filename:
        raise ValueError("Allowed file types: PDF, PNG, JPG.")
    extension = uploaded_file.filename.rsplit(".", 1)[1].lower()
    if extension not in current_app.config["ALLOWED_EXTENSIONS"]:
        raise ValueError("Allowed file types: PDF, PNG, JPG.")

    # We pick the file name ourselves instead of trusting the uploaded one.
    filename = "licence_" + str(customer_id) + "." + extension
    uploaded_file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))

    get_db().execute(
        "UPDATE Customers SET licenceDocumentPath = ?, verificationStatus = ? WHERE customerID = ?",
        (filename, VERIFICATION_PENDING, customer_id))


def set_verification(customer_id, status):
    """status must be 'Approved' or 'Rejected'."""
    if status not in ("Approved", "Rejected"):
        raise ValueError("status must be Approved or Rejected")
    get_db().execute(
        "UPDATE Customers SET verificationStatus = ? WHERE customerID = ?", (status, customer_id))


def pending_verifications():
    rows = get_db().execute(
        "SELECT customerID, fullName, email, licenceDocumentPath FROM Customers "
        "WHERE verificationStatus = 'Pending' AND licenceDocumentPath IS NOT NULL").fetchall()
    result = []
    for row in rows:
        result.append(dict(row))
    return result
