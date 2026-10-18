-- RentalDB schema (report Section 4.3), with fixes agreed in the build plan:
--  * Administrators gets email + passwordHash so admins can log in
--  * Customers gets licenceDocumentPath (was in the class diagram, missing from the schema)
--  * Vehicles gets spec columns for FR-01; status is Available / Maintenance only
--    ("rented" is derived from bookings by date)
--  * Date convention: endDate is EXCLUSIVE (checkout day is not billed, same-day turnover allowed)

DROP TABLE IF EXISTS Invoices;
DROP TABLE IF EXISTS Bookings;
DROP TABLE IF EXISTS DeliveryZones;
DROP TABLE IF EXISTS Vehicles;
DROP TABLE IF EXISTS Administrators;
DROP TABLE IF EXISTS Customers;

CREATE TABLE Customers (
    customerID          INTEGER PRIMARY KEY AUTOINCREMENT,
    fullName            TEXT NOT NULL,
    email               TEXT NOT NULL UNIQUE,
    passwordHash        TEXT NOT NULL,
    verificationStatus  TEXT NOT NULL DEFAULT 'Pending'
                        CHECK (verificationStatus IN ('Pending', 'Approved', 'Rejected')),
    licenceDocumentPath TEXT
);

CREATE TABLE Administrators (
    adminID      INTEGER PRIMARY KEY AUTOINCREMENT,
    fullName     TEXT NOT NULL,
    email        TEXT NOT NULL UNIQUE,
    passwordHash TEXT NOT NULL
);

CREATE TABLE Vehicles (
    vehicleID    INTEGER PRIMARY KEY AUTOINCREMENT,
    make         TEXT NOT NULL,
    model        TEXT NOT NULL,
    year         INTEGER,
    seats        INTEGER,
    transmission TEXT,
    fuelType     TEXT,
    imagePath    TEXT,                 -- file name inside app/static/images/vehicles/ (NULL = placeholder)
    dailyRate    REAL NOT NULL CHECK (dailyRate >= 0),
    status       TEXT NOT NULL DEFAULT 'Available'   -- only what an admin sets. 'Booked' is NOT stored:
                 CHECK (status IN ('Available', 'Maintenance'))  -- it is worked out from the Bookings table
);

CREATE TABLE DeliveryZones (
    zoneID      INTEGER PRIMARY KEY AUTOINCREMENT,
    areaName    TEXT NOT NULL UNIQUE,
    deliveryFee REAL NOT NULL CHECK (deliveryFee >= 0)
);

CREATE TABLE Bookings (
    bookingID         INTEGER PRIMARY KEY AUTOINCREMENT,
    customerID        INTEGER NOT NULL REFERENCES Customers(customerID),
    vehicleID         INTEGER NOT NULL REFERENCES Vehicles(vehicleID),
    zoneID            INTEGER REFERENCES DeliveryZones(zoneID),   -- NULL when no delivery
    startDate         TEXT NOT NULL,                              -- ISO YYYY-MM-DD
    endDate           TEXT NOT NULL,                              -- exclusive
    deliveryRequested INTEGER NOT NULL DEFAULT 0,
    status            TEXT NOT NULL DEFAULT 'Confirmed'
                      CHECK (status IN ('Confirmed', 'Cancelled')),
    CHECK (endDate > startDate)
);

CREATE TABLE Invoices (
    invoiceID   INTEGER PRIMARY KEY AUTOINCREMENT,
    bookingID   INTEGER NOT NULL UNIQUE REFERENCES Bookings(bookingID),
    baseAmount  REAL NOT NULL,
    deliveryFee REAL NOT NULL,
    tax         REAL NOT NULL,
    totalAmount REAL NOT NULL
);

CREATE INDEX idx_bookings_vehicle_dates ON Bookings(vehicleID, startDate, endDate);
