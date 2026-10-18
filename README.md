# YourDreamCar - Smart Vehicle Rental System (ENEL2SE)

## Run it

```
python -m venv venv
venv\Scripts\activate          # Windows   (macOS/Linux: source venv/bin/activate)
pip install -r requirements.txt
python seed.py                 # creates database.db with demo data (run again any time to reset it)
python run.py                  # open http://127.0.0.1:5000
```

Demo logins:

| Role | Email | Password | Notes |
| --- | --- | --- | --- |
| Administrator | admin@yourdreamcar.test | admin123 | |
| Customer | demo@customer.test | demo123 | Approved, can book |
| Customer | pending@customer.test | demo123 | Pending, cannot book until approved |

Run the tests: `python -m unittest discover -s tests -t .`(26 Tests)

## Module responsibilities

| Module | Owner | Files |
| --- | --- | --- |
| Authentication | Mishael | `app/auth/` |
| Inventory, schema and seed data | Kovidh | `app/inventory/`, `schema.sql`, `app/seed.py` |
| Booking | Niral | `app/booking/` |
| Billing | Rahul | `app/billing/calculator.py` |
| Templates and CSS | Nijith | `app/templates/`, `app/static/` |

Responsibilities are as assigned in the project report (Section 1.9.2). The sections were combined into one code base by team leader.

## How the modules talk to each other

Modules call each other's service functions instead of reaching into each other's routes:

- `auth.service`: `login_required`, `admin_required`, `current_user()`
- `inventory.service`: `get_all_vehicles()`, `get_vehicle(id)`, `is_vehicle_available(id, start, end)`, `check_delivery(address)`, `get_delivery_zones()`
- `billing.calculator`: `calculate_bill(daily_rate, start, end, delivery_fee)` returns `{duration, base_amount, delivery_fee, tax, total}`

## Decisions to keep

- **The end date is exclusive.** 20th to 23rd is 3 billable days, and the car can be booked again from the 23rd.
- Only `Available` and `Maintenance` are stored for a vehicle. `Booked` is worked out from the Bookings table.
- Booking confirmation checks availability again inside one `BEGIN IMMEDIATE` transaction (NFR-04).
- The tax rate (15%) is set once, in `config.py`.
- A delivery zone matches when its name appears in the address as whole words (`Berea` does not match `Bereavement`).
- Administrators have their own table with a login (`Administrators`), which was added to the report schema.

## Known limitations

- No cancel-booking feature (the `Cancelled` status exists in the schema and the availability check).
- Delivery zones are matched on the address text; there is no map or distance check.
- No CSRF protection, no login rate limit and no email verification.
- Uploads are checked by file extension only, not by file content.
- The development server (`python run.py`) is for demos, not production.
