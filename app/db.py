"""Database helpers. SQLite through Python's built-in sqlite3 module (no ORM).

Each request gets one connection, stored in Flask's `g`, and it is closed when the request ends.
"""
import os
import sqlite3

from flask import current_app, g


def get_db():
    if "db" not in g:
        # isolation_level=None = autocommit. Multi-step changes start their own transaction
        # (see save_booking_and_invoice in booking/routes.py).
        g.db = sqlite3.connect(current_app.config["DATABASE"], isolation_level=None)
        g.db.row_factory = sqlite3.Row                 # read columns by name: row["dailyRate"]
        g.db.execute("PRAGMA foreign_keys = ON")       # SQLite ignores foreign keys unless asked
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Drops and recreates every table from schema.sql (used by seed.py and the tests)."""
    db = get_db()
    schema_path = os.path.join(current_app.config["BASE_DIR"], "schema.sql")
    with open(schema_path, encoding="utf-8") as schema_file:
        db.executescript(schema_file.read())


def init_app(app):
    app.config.setdefault("BASE_DIR", os.path.abspath(os.path.join(app.root_path, "..")))
    app.teardown_appcontext(close_db)
