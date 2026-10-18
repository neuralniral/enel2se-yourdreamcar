"""Billing Module (Rahul) - FR-06, report sections 3.4.4 and 4.4.3.

Plain functions with no Flask code, so they can be tested on their own (tests/test_billing.py).

    subtotal = dailyRate x days + deliveryFee
    tax      = subtotal x taxRate
    total    = subtotal + tax
"""
from config import TAX_RATE

from ..utils import parse_date


def rental_days(start, end):
    """Billable days. The end date is not counted: 20 Oct -> 23 Oct is 3 days."""
    days = (parse_date(end) - parse_date(start)).days
    if days < 1:
        raise ValueError("The end date must be after the start date.")
    return days


def calculate_bill(daily_rate, start, end, delivery_fee=0, tax_rate=TAX_RATE):
    """Returns a dictionary with duration, base_amount, delivery_fee, tax and total."""
    duration = rental_days(start, end)
    base_amount = round(float(daily_rate) * duration, 2)
    delivery_fee = round(float(delivery_fee or 0), 2)
    subtotal = base_amount + delivery_fee
    tax = round(subtotal * tax_rate, 2)
    total = round(subtotal + tax, 2)
    return {
        "duration": duration,
        "base_amount": base_amount,
        "delivery_fee": delivery_fee,
        "tax": tax,
        "total": total,
    }
