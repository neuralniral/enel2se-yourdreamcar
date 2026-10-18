"""Small helpers used by more than one module."""
from datetime import date, datetime


def parse_date(value):
    """Turns a date, datetime or text like '2026-10-20' into a date. Raises ValueError if invalid."""
    if isinstance(value, datetime):      # check datetime first, it is a kind of date
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def rows_to_list(rows):
    """Turns database rows into a list of dictionaries."""
    return [dict(row) for row in rows]
