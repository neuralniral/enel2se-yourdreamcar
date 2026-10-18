"""Fixed text values for the status columns. If one changes, change the CHECK in schema.sql too."""
VERIFICATION_PENDING = "Pending"
VERIFICATION_APPROVED = "Approved"
VERIFICATION_REJECTED = "Rejected"

# Stored in the Vehicles table (set by an administrator)
VEHICLE_AVAILABLE = "Available"
VEHICLE_MAINTENANCE = "Maintenance"

# Not stored. Worked out from the Bookings table (see get_display_status in inventory/service.py)
VEHICLE_BOOKED = "Booked"

BOOKING_CONFIRMED = "Confirmed"
BOOKING_CANCELLED = "Cancelled"
