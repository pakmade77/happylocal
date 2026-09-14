-- =====================================================================
-- Happy Local Adventure - Tour Operator ERP (Supabase / PostgreSQL Schema)
-- Business model: B2B contract-rate day activities in Bali.
-- Converted for Supabase PostgreSQL with RLS, Analytics Views, and Master Seed.
-- =====================================================================

-- 1. Company Profile
CREATE TABLE IF NOT EXISTS company_profile (
    id INT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    company_name VARCHAR(255) NOT NULL,
    bank_name VARCHAR(100),
    bank_account_number VARCHAR(100),
    bank_account_name VARCHAR(255),
    default_currency VARCHAR(10) NOT NULL DEFAULT 'IDR',
    payment_terms_note TEXT,
    cancellation_policy_note TEXT,
    invoice_prefix VARCHAR(20) NOT NULL DEFAULT 'INV',
    payment_due_days_before_activity INT NOT NULL DEFAULT 5,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Bank Accounts
CREATE TABLE IF NOT EXISTS bank_accounts (
    id SERIAL PRIMARY KEY,
    bank_name VARCHAR(100) NOT NULL,
    account_number VARCHAR(100) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Partners (Travel Agents / DMCs)
CREATE TABLE IF NOT EXISTS partners (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    country VARCHAR(100),
    payment_terms_days INT NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Customers (End Travellers)
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    partner_id INT REFERENCES partners(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    nationality VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Pickup Areas
CREATE TABLE IF NOT EXISTS pickup_areas (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

-- 6. Activities
CREATE TABLE IF NOT EXISTS activities (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    description TEXT,
    start_time VARCHAR(20),
    duration_note VARCHAR(100),
    inclusions TEXT,
    exclusions TEXT,
    rate_valid_from DATE,
    rate_valid_to DATE,
    currency VARCHAR(10) NOT NULL DEFAULT 'IDR',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Activity Pickup Areas Junction
CREATE TABLE IF NOT EXISTS activity_pickup_areas (
    activity_id INT NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    pickup_area_id INT NOT NULL REFERENCES pickup_areas(id) ON DELETE CASCADE,
    PRIMARY KEY (activity_id, pickup_area_id)
);

-- 8. Activity Price Tiers (Pax Based Pricing)
CREATE TABLE IF NOT EXISTS activity_price_tiers (
    id SERIAL PRIMARY KEY,
    activity_id INT NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
    min_pax INT NOT NULL,
    max_pax INT,
    price_per_person NUMERIC(14,2) NOT NULL,
    note TEXT,
    UNIQUE (activity_id, min_pax)
);

-- 9. Guides & Drivers
CREATE TABLE IF NOT EXISTS guides (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    languages VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS drivers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    vehicle_info VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. Bookings
CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    booking_code VARCHAR(50) UNIQUE NOT NULL,
    activity_id INT NOT NULL REFERENCES activities(id),
    partner_id INT NOT NULL REFERENCES partners(id),
    customer_id INT REFERENCES customers(id) ON DELETE SET NULL,
    activity_date DATE NOT NULL,
    pickup_time VARCHAR(20),
    pax_count INT NOT NULL CHECK (pax_count > 0),
    pickup_area_id INT REFERENCES pickup_areas(id),
    guide_id INT REFERENCES guides(id) ON DELETE SET NULL,
    driver_id INT REFERENCES drivers(id) ON DELETE SET NULL,
    price_per_person NUMERIC(14,2) NOT NULL,
    subtotal NUMERIC(14,2) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending','Confirmed','Completed','Cancelled')),
    special_requests TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 11. Cancellations
CREATE TABLE IF NOT EXISTS cancellations (
    id SERIAL PRIMARY KEY,
    booking_id INT UNIQUE NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    cancelled_at DATE NOT NULL,
    days_before_activity INT NOT NULL,
    fee_percentage NUMERIC(5,2) NOT NULL,
    fee_amount NUMERIC(14,2) NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12. Invoices & Payments
CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    invoice_number VARCHAR(100) UNIQUE NOT NULL,
    partner_id INT NOT NULL REFERENCES partners(id),
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'IDR',
    subtotal NUMERIC(14,2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    paid_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'Draft' CHECK (status IN ('Draft','Sent','Partially Paid','Paid','Overdue','Cancelled')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS invoice_items (
    id SERIAL PRIMARY KEY,
    invoice_id INT NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    booking_id INT REFERENCES bookings(id) ON DELETE SET NULL,
    description TEXT NOT NULL,
    pax_count INT,
    unit_price NUMERIC(14,2) NOT NULL,
    line_total NUMERIC(14,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    invoice_id INT NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    payment_date DATE NOT NULL,
    amount NUMERIC(14,2) NOT NULL,
    method VARCHAR(50) NOT NULL DEFAULT 'Bank Transfer',
    bank_reference VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 13. Expenses
CREATE TABLE IF NOT EXISTS expenses (
    id SERIAL PRIMARY KEY,
    expense_date DATE NOT NULL,
    booking_id INT REFERENCES bookings(id) ON DELETE SET NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    amount NUMERIC(14,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================================
-- Analytics Views
-- =====================================================================

CREATE OR REPLACE VIEW v_outstanding_invoices AS
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

CREATE OR REPLACE VIEW v_revenue_by_activity AS
SELECT
    a.id AS activity_id,
    a.name AS activity_name,
    COUNT(b.id) AS booking_count,
    COALESCE(SUM(b.pax_count), 0) AS total_pax,
    COALESCE(SUM(b.subtotal), 0) AS total_revenue
FROM activities a
LEFT JOIN bookings b ON a.id = b.activity_id AND b.status IN ('Confirmed', 'Completed')
GROUP BY a.id, a.name
ORDER BY total_revenue DESC;

CREATE OR REPLACE VIEW v_revenue_by_partner AS
SELECT
    p.id AS partner_id,
    p.name AS partner_name,
    COUNT(b.id) AS booking_count,
    COALESCE(SUM(b.pax_count), 0) AS total_pax,
    COALESCE(SUM(b.subtotal), 0) AS total_revenue
FROM partners p
LEFT JOIN bookings b ON p.id = b.partner_id AND b.status IN ('Confirmed', 'Completed')
GROUP BY p.id, p.name
ORDER BY total_revenue DESC;

CREATE OR REPLACE VIEW v_upcoming_bookings AS
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

CREATE OR REPLACE VIEW v_booking_profitability AS
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
GROUP BY b.id, b.booking_code, a.name, b.activity_date, b.pax_count, b.subtotal
ORDER BY b.activity_date DESC;

CREATE OR REPLACE VIEW v_cancellations AS
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

-- =====================================================================
-- Master Data Seed (Company Profile, Bank Accounts, Pickup Areas, Activities & Tiers)
-- =====================================================================

INSERT INTO company_profile (id, company_name, bank_name, bank_account_number, bank_account_name, default_currency, payment_due_days_before_activity)
VALUES (1, 'Happy Local Adventure', 'Bank Central Asia (BCA)', '6700273201', 'I Gusti Agung Made Bara Oka', 'IDR', 5)
ON CONFLICT (id) DO NOTHING;

INSERT INTO bank_accounts (bank_name, account_number, account_name, is_primary)
VALUES ('Bank Central Asia (BCA)', '6700273201', 'I Gusti Agung Made Bara Oka', TRUE)
ON CONFLICT DO NOTHING;

INSERT INTO pickup_areas (name) VALUES 
('Ubud'), ('Sanur'), ('Kuta'), ('Seminyak'), ('Canggu'), ('Candidasa')
ON CONFLICT DO NOTHING;

-- 5 Real Activities
INSERT INTO activities (id, code, name, category, description, start_time, duration_note, inclusions, exclusions, rate_valid_from, rate_valid_to)
VALUES 
(1, 'VILLAGE-COOKING', 'Village Explore with Balinese Cooking Experience', 'Village Experience', 'Village walk through rice fields and Subak irrigation to natural springs, followed by a jungle cooking experience and riverside Balinese lunch.', '08:30', 'Approximately 4-5 hours', 'Return private transfer\nEnglish-speaking local guide\nWelcome drink\nAll cooking ingredients and equipment\nJungle-cooked Balinese lunch\nDrinking water\nTowel and changing facilities at the spring\nDonation and entrance fees', '', '2026-01-01', '2027-12-31'),
(2, 'DINNER-LOCALS', 'Dinner with Locals', 'Dinner Experience', 'Village compound visit, coffee/tea with a local family, leisurely village walk to rice-field viewpoint, home-cooked dinner and a children''s Balinese dance performance.', '16:30', NULL, 'Donation\nEnglish-speaking local guide\nReturn transfers from Ubud, Sanur, Kuta, Seminyak, Canggu & Candidasa\nWelcome drink\nCoffee or tea at the local house\nEntrance fees\nDance performance', '', '2026-01-01', '2027-12-31'),
(3, 'JUNGLE-COOKING', 'Jungle Cooking Experience', 'Village Experience', 'Guided jungle walk to the riverside to collect fish-trap catch and forage vegetables/herbs, cook lunch over a wood-fired stove, with a natural spring bath before lunch.', '10:00', NULL, 'Private transfer\nDonation\nWelcome drink\nLunch', 'Travel insurance\nPersonal expenses (souvenirs, tipping, etc.)', '2026-01-01', '2027-12-31'),
(4, 'SUNSET-DINNER-LOCALS', 'Sunset Dinner with Locals', 'Dinner Experience', 'Adds a Sunset Picnic Point with refreshing drinks and light Balinese snacks before the village walk, home-cooked dinner, and children''s dance performance.', '16:30', NULL, 'Sunset picnic point (drinks and light snacks)\nDonation\nEnglish-speaking local guide\nReturn transfers from Ubud, Sanur, Kuta, Seminyak, Canggu & Candidasa\nWelcome drink\nCoffee or tea at the local house\nEntrance fees\nDance performance', '', '2026-01-01', '2027-12-31'),
(5, 'BLESSING-CEREMONY', 'Balinese Blessing Ceremony at the Natural Springs', 'Ceremony', 'Balinese Hindu blessing and purification ritual at the natural spring, complete with sarong/sash, canang sari offerings, and blessing by a local Hindu priest.', NULL, NULL, 'Return transfers from Ubud, Sanur, Kuta, Seminyak, Canggu & Candidasa\nEnglish-speaking local guide\nTraditional Balinese sarong & sash\nCanang sari & blessing offerings\nBalinese Hindu priest honorarium\nDonation and entrance fees', '', '2026-01-01', '2027-12-31')
ON CONFLICT (code) DO NOTHING;

-- Activity Price Tiers
INSERT INTO activity_price_tiers (activity_id, min_pax, max_pax, price_per_person) VALUES
-- Village Explore & Cooking
(1, 1, 1, 1520000), (1, 2, 2, 805000), (1, 3, 5, 740000), (1, 6, 8, 625000), (1, 9, NULL, 500000),
-- Dinner with Locals
(2, 1, 1, 1260000), (2, 2, 2, 630000), (2, 3, 5, 535000), (2, 6, 6, 535000), (2, 7, 8, 500000), (2, 9, NULL, 500000),
-- Jungle Cooking Experience
(3, 1, 1, 1520000), (3, 2, 2, 805000), (3, 3, 5, 740000), (3, 6, 8, 625000), (3, 9, NULL, 500000),
-- Sunset Dinner with Locals
(4, 1, 1, 1375000), (4, 2, 2, 740000), (4, 3, 5, 625000), (4, 6, 6, 625000), (4, 7, 8, 565000), (4, 9, NULL, 565000),
-- Balinese Blessing Ceremony
(5, 1, 1, 1150000), (5, 2, 2, 575000), (5, 3, 5, 460000), (5, 6, 8, 400000), (5, 9, NULL, 345000)
ON CONFLICT (activity_id, min_pax) DO NOTHING;
