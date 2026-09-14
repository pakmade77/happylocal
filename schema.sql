-- =====================================================================
-- Happy Local Adventure - Tour Operator ERP Schema
-- Business model: B2B contract-rate day activities, sold to travel
-- agents/DMCs who resell to end travellers. Pricing is per-person and
-- tiered by group size (NOT flat unit price, NOT physical inventory).
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- Company profile (single row) - used on printed invoices. The
-- bank_name/bank_account_number/bank_account_name columns here are kept
-- for backward compatibility with older databases but are superseded by
-- the bank_accounts table below, which supports more than one account.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS company_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    company_name TEXT NOT NULL,
    bank_name TEXT,
    bank_account_number TEXT,
    bank_account_name TEXT,
    default_currency TEXT NOT NULL DEFAULT 'IDR',
    payment_terms_note TEXT,
    cancellation_policy_note TEXT,
    invoice_prefix TEXT NOT NULL DEFAULT 'INV',
    payment_due_days_before_activity INTEGER NOT NULL DEFAULT 5
);

-- ---------------------------------------------------------------------
-- Bank accounts: the company can settle into more than one account
-- (e.g. different banks/currencies). Exactly one is flagged is_primary -
-- that's the one printed on invoices' bank transfer box.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bank_accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_name TEXT NOT NULL,
    account_number TEXT NOT NULL,
    account_name TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Partners: the actual paying customers on contract rates (travel
-- agents / DMCs). Direct walk-in guests are modeled via `customers`
-- with partner_id = NULL.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS partners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    company TEXT,
    email TEXT,
    phone TEXT,
    country TEXT,
    payment_terms_days INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Customers: the end travellers taking the activity. May belong to a
-- partner (agent booked on their behalf) or be direct (partner_id NULL).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    partner_id INTEGER,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    nationality TEXT,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (partner_id) REFERENCES partners(id)
);

-- ---------------------------------------------------------------------
-- Pickup areas served by transfer (Ubud, Sanur, Kuta, Seminyak, ...)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pickup_areas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

-- ---------------------------------------------------------------------
-- Activities: the sellable products (day experiences). No stock/qty -
-- capacity is a function of guide/driver availability per date, not
-- a countable item.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT,                       -- e.g. Village Experience, Dinner, Ceremony
    description TEXT,
    start_time TEXT,                     -- e.g. '08:30'
    duration_note TEXT,                  -- e.g. 'Approx. 4-5 hours'
    inclusions TEXT,                     -- newline-separated list
    exclusions TEXT,                     -- newline-separated list
    rate_valid_from TEXT,                -- contract validity window
    rate_valid_to TEXT,
    currency TEXT NOT NULL DEFAULT 'IDR',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Junction: which pickup areas apply to which activity
CREATE TABLE IF NOT EXISTS activity_pickup_areas (
    activity_id INTEGER NOT NULL,
    pickup_area_id INTEGER NOT NULL,
    PRIMARY KEY (activity_id, pickup_area_id),
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    FOREIGN KEY (pickup_area_id) REFERENCES pickup_areas(id)
);

-- ---------------------------------------------------------------------
-- Price tiers: the core pricing mechanic. Rate PER PERSON depends on
-- total pax count in the booking. max_pax NULL = "and up" (open-ended
-- top tier, e.g. "9 Pax up").
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activity_price_tiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id INTEGER NOT NULL,
    min_pax INTEGER NOT NULL,
    max_pax INTEGER,                     -- NULL = unlimited / "and up"
    price_per_person REAL NOT NULL,
    note TEXT,                           -- e.g. data-gap flags
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    UNIQUE (activity_id, min_pax)
);

-- ---------------------------------------------------------------------
-- Operational resources
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS guides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    languages TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS drivers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    vehicle_info TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

-- ---------------------------------------------------------------------
-- Bookings: one reservation of one activity, on one date, for N pax.
-- price_per_person is snapshotted at booking time from the tier table
-- (so later rate changes don't retroactively alter confirmed bookings).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_code TEXT UNIQUE NOT NULL,
    activity_id INTEGER NOT NULL,
    partner_id INTEGER NOT NULL,
    customer_id INTEGER,
    activity_date TEXT NOT NULL,          -- date the activity takes place
    pickup_time TEXT,
    pax_count INTEGER NOT NULL CHECK (pax_count > 0),
    pickup_area_id INTEGER,
    guide_id INTEGER,
    driver_id INTEGER,
    price_per_person REAL NOT NULL,       -- snapshot from activity_price_tiers
    subtotal REAL NOT NULL,               -- price_per_person * pax_count
    status TEXT NOT NULL DEFAULT 'Pending' -- Pending/Confirmed/Completed/Cancelled
        CHECK (status IN ('Pending','Confirmed','Completed','Cancelled')),
    special_requests TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (activity_id) REFERENCES activities(id),
    FOREIGN KEY (partner_id) REFERENCES partners(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (pickup_area_id) REFERENCES pickup_areas(id),
    FOREIGN KEY (guide_id) REFERENCES guides(id),
    FOREIGN KEY (driver_id) REFERENCES drivers(id)
);

-- ---------------------------------------------------------------------
-- Cancellations: applies the contract's cancellation-fee policy to a
-- cancelled booking. One row per cancelled booking.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cancellations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER UNIQUE NOT NULL,
    cancelled_at TEXT NOT NULL,           -- date cancellation was requested
    days_before_activity INTEGER NOT NULL,
    fee_percentage REAL NOT NULL,         -- 0 / 50 / 100 per contract terms
    fee_amount REAL NOT NULL,
    reason TEXT,
    FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- Invoices: billed to a partner (agent), can consolidate multiple
-- bookings. due_date should respect "full payment 5 days before the
-- activity date" for the earliest activity covered.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number TEXT UNIQUE NOT NULL,
    partner_id INTEGER NOT NULL,
    invoice_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'IDR',
    subtotal REAL NOT NULL DEFAULT 0,
    discount_amount REAL NOT NULL DEFAULT 0,
    total_amount REAL NOT NULL DEFAULT 0,
    paid_amount REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'Draft'
        CHECK (status IN ('Draft','Sent','Partially Paid','Paid','Overdue','Cancelled')),
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (partner_id) REFERENCES partners(id)
);

CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    booking_id INTEGER,                   -- NULL for e.g. manual/cancellation-fee lines
    description TEXT NOT NULL,
    pax_count INTEGER,
    unit_price REAL NOT NULL,
    line_total REAL NOT NULL,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    FOREIGN KEY (booking_id) REFERENCES bookings(id)
);

CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    payment_date TEXT NOT NULL,
    amount REAL NOT NULL,
    method TEXT NOT NULL DEFAULT 'Bank Transfer',
    bank_reference TEXT,
    notes TEXT,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- Expenses: operational cost tracking, optionally tied to a booking
-- for per-booking profitability (guide fee, transport, ingredients,
-- donation/entrance fees, etc.)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_date TEXT NOT NULL,
    booking_id INTEGER,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    FOREIGN KEY (booking_id) REFERENCES bookings(id)
);

-- =====================================================================
-- Reporting views
-- =====================================================================

-- Accounts receivable: what's still owed, per invoice
CREATE VIEW IF NOT EXISTS v_outstanding_invoices AS
SELECT
    i.id AS invoice_id,
    i.invoice_number,
    p.name AS partner_name,
    i.invoice_date,
    i.due_date,
    i.total_amount,
    i.paid_amount,
    (i.total_amount - i.paid_amount) AS balance_due,
    i.status
FROM invoices i
JOIN partners p ON p.id = i.partner_id
WHERE i.status NOT IN ('Paid', 'Cancelled')
ORDER BY i.due_date ASC;

-- Revenue by activity (based on confirmed/completed bookings)
CREATE VIEW IF NOT EXISTS v_revenue_by_activity AS
SELECT
    a.id AS activity_id,
    a.name AS activity_name,
    COUNT(b.id) AS booking_count,
    SUM(b.pax_count) AS total_pax,
    SUM(b.subtotal) AS total_revenue
FROM bookings b
JOIN activities a ON a.id = b.activity_id
WHERE b.status IN ('Confirmed', 'Completed')
GROUP BY a.id
ORDER BY total_revenue DESC;

-- Revenue by partner (agent)
CREATE VIEW IF NOT EXISTS v_revenue_by_partner AS
SELECT
    p.id AS partner_id,
    p.name AS partner_name,
    COUNT(b.id) AS booking_count,
    SUM(b.pax_count) AS total_pax,
    SUM(b.subtotal) AS total_revenue
FROM bookings b
JOIN partners p ON p.id = b.partner_id
WHERE b.status IN ('Confirmed', 'Completed')
GROUP BY p.id
ORDER BY total_revenue DESC;

-- Upcoming bookings needing operational planning (guide/driver assignment)
CREATE VIEW IF NOT EXISTS v_upcoming_bookings AS
SELECT
    b.id AS booking_id,
    b.booking_code,
    a.name AS activity_name,
    b.activity_date,
    b.pickup_time,
    b.pax_count,
    pa.name AS pickup_area,
    p.name AS partner_name,
    g.name AS guide_name,
    d.name AS driver_name,
    b.status
FROM bookings b
JOIN activities a ON a.id = b.activity_id
JOIN partners p ON p.id = b.partner_id
LEFT JOIN pickup_areas pa ON pa.id = b.pickup_area_id
LEFT JOIN guides g ON g.id = b.guide_id
LEFT JOIN drivers d ON d.id = b.driver_id
WHERE b.status IN ('Pending', 'Confirmed')
ORDER BY b.activity_date ASC;

-- Per-booking profitability: revenue vs. tracked direct expenses
CREATE VIEW IF NOT EXISTS v_booking_profitability AS
SELECT
    b.id AS booking_id,
    b.booking_code,
    a.name AS activity_name,
    b.activity_date,
    b.pax_count,
    b.subtotal AS revenue,
    COALESCE(SUM(e.amount), 0) AS direct_expenses,
    b.subtotal - COALESCE(SUM(e.amount), 0) AS gross_margin
FROM bookings b
JOIN activities a ON a.id = b.activity_id
LEFT JOIN expenses e ON e.booking_id = b.id
GROUP BY b.id
ORDER BY b.activity_date DESC;

-- Cancellation fee report
CREATE VIEW IF NOT EXISTS v_cancellations AS
SELECT
    c.id AS cancellation_id,
    b.booking_code,
    a.name AS activity_name,
    p.name AS partner_name,
    b.activity_date,
    c.cancelled_at,
    c.days_before_activity,
    c.fee_percentage,
    c.fee_amount,
    c.reason
FROM cancellations c
JOIN bookings b ON b.id = c.booking_id
JOIN activities a ON a.id = b.activity_id
JOIN partners p ON p.id = b.partner_id
ORDER BY c.cancelled_at DESC;
