"""
Happy Local Adventure - Tour Operator ERP
==========================================
A lightweight CLI-driven ERP for a Bali day-activity tour operator that
sells on B2B contract rates (per-person, tiered by group size).

Modules covered:
  - Database layer   : schema.sql (SQLite)
  - Booking engine    : tier-based price lookup, booking, cancellation fees
  - Invoicing         : consolidate bookings into partner invoices, record
                         payments, render a printable HTML invoice
  - Reporting         : revenue, receivables, operations schedule,
                         cancellations, profitability

Run `python app.py --help` for the full command list.
"""

import argparse
import os
import random
import sqlite3
from datetime import datetime, timedelta

DB_PATH = "erp.db"
SCHEMA_PATH = "schema.sql"

# Brand logo (Happy Local Adventure) - embedded as base64 so both the CLI-
# generated invoice HTML and the Flask UI (web.py) can brand documents/pages
# without a separate static-file route. 128x128 PNG, transparent background.
LOGO_PNG_BASE64 = "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"
LOGO_DATA_URI = "data:image/png;base64," + LOGO_PNG_BASE64


# =====================================================================
# Connection helpers
# =====================================================================

_migrated = False


def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    global _migrated
    if not _migrated:
        _ensure_migrations(conn)
        _migrated = True
    return conn


def _ensure_migrations(conn):
    """Idempotent in-place upgrades for databases created before a column
    was added, so an existing erp.db never has to be dropped/reseeded when
    app.py gains a new setting. No-op on a not-yet-initialized database -
    init_db() creates fresh columns correctly via schema.sql."""
    table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'company_profile'"
    ).fetchone()
    if not table_exists:
        return
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(company_profile)")}
    if "invoice_prefix" not in cols:
        conn.execute("ALTER TABLE company_profile ADD COLUMN invoice_prefix TEXT NOT NULL DEFAULT 'INV'")
    if "payment_due_days_before_activity" not in cols:
        conn.execute("ALTER TABLE company_profile ADD COLUMN payment_due_days_before_activity INTEGER NOT NULL DEFAULT 5")

    bank_accounts_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'bank_accounts'"
    ).fetchone()
    if not bank_accounts_exists:
        conn.execute(
            """CREATE TABLE bank_accounts (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   bank_name TEXT NOT NULL,
                   account_number TEXT NOT NULL,
                   account_name TEXT NOT NULL,
                   is_primary INTEGER NOT NULL DEFAULT 0,
                   created_at TEXT DEFAULT CURRENT_TIMESTAMP
               )"""
        )
        # Carry the old single-account fields over as the first (primary)
        # row, so existing invoices keep printing the same bank details.
        company = conn.execute("SELECT * FROM company_profile WHERE id = 1").fetchone()
        if company and company["bank_name"]:
            conn.execute(
                "INSERT INTO bank_accounts (bank_name, account_number, account_name, is_primary) VALUES (?, ?, ?, 1)",
                (company["bank_name"], company["bank_account_number"], company["bank_account_name"]),
            )
    conn.commit()


def init_db():
    if not os.path.exists(SCHEMA_PATH):
        raise FileNotFoundError("schema.sql not found")
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn = connect_db()
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()
    print("Database initialized successfully.")


def parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d").date()


# =====================================================================
# Seed data - transcribed directly from the "Happy Local Adventure"
# contract rate sheet (validity 01 Jan 2026 - 31 Dec 2027).
# =====================================================================

PICKUP_AREAS = ["Ubud", "Sanur", "Kuta", "Seminyak", "Canggu", "Candidasa"]

ACTIVITIES = [
    {
        "code": "VILLAGE-COOKING",
        "name": "Village Explore with Balinese Cooking Experience",
        "category": "Village Experience",
        "description": (
            "Village walk through rice fields and Subak irrigation to natural "
            "springs, followed by a jungle cooking experience and riverside "
            "Balinese lunch."
        ),
        "start_time": "08:30",
        "duration_note": "Approximately 4-5 hours",
        "inclusions": (
            "Return private transfer\nEnglish-speaking local guide\nWelcome drink\n"
            "All cooking ingredients and equipment\nJungle-cooked Balinese lunch\n"
            "Drinking water\nTowel and changing facilities at the spring\n"
            "Donation and entrance fees"
        ),
        "exclusions": "",
        "pickup_areas": [],  # not specified in source document
        "tiers": [
            (1, 1, 1520000), (2, 2, 805000), (3, 5, 740000),
            (6, 8, 625000), (9, None, 500000),
        ],
    },
    {
        "code": "DINNER-LOCALS",
        "name": "Dinner with Locals",
        "category": "Dinner Experience",
        "description": (
            "Village compound visit, coffee/tea with a local family, leisurely "
            "village walk to rice-field viewpoint, home-cooked dinner and a "
            "children's Balinese dance performance."
        ),
        "start_time": "16:30",
        "duration_note": None,
        "inclusions": (
            "Donation\nEnglish-speaking local guide\n"
            "Return transfers from Ubud, Sanur, Kuta, Seminyak, Canggu & Candidasa\n"
            "Welcome drink\nCoffee or tea at the local house\nEntrance fees\n"
            "Dance performance"
        ),
        "exclusions": "",
        "pickup_areas": PICKUP_AREAS,
        "tiers": [
            (1, 1, 1260000), (2, 2, 630000), (3, 5, 535000),
            # NOTE: source PDF has no explicit 6-pax rate (table jumps 5 -> 7).
            # Modeled here as carrying the 5-pax rate through 6 pax; flagged
            # for confirmation with the vendor before using commercially.
            (6, 6, 535000),
            (7, 8, 500000), (9, None, 500000),
        ],
    },
    {
        "code": "JUNGLE-COOKING",
        "name": "Jungle Cooking Experience",
        "category": "Village Experience",
        "description": (
            "Guided jungle walk to the riverside to collect fish-trap catch and "
            "forage vegetables/herbs, cook lunch over a wood-fired stove, with a "
            "natural spring bath before lunch."
        ),
        "start_time": "10:00",
        "duration_note": None,
        "inclusions": "Private transfer\nDonation\nWelcome drink\nLunch",
        "exclusions": "Travel insurance\nPersonal expenses (souvenirs, tipping, etc.)",
        "pickup_areas": [],
        "tiers": [
            (1, 1, 1375000), (2, 2, 935000), (3, 5, 750000),
            (6, 6, 650000), (7, 7, 600000), (8, None, 500000),
        ],
    },
    {
        "code": "SUNSET-DINNER-LOCALS",
        "name": "Sunset Dinner with Locals",
        "category": "Dinner Experience",
        "description": (
            "Village compound visit and coffee/tea, village walk to rice-field "
            "viewpoint, Sunset Picnic Point with drinks and Balinese snacks "
            "overlooking Nusa Islands, then home-cooked dinner with dance "
            "performance."
        ),
        "start_time": "16:30",
        "duration_note": None,
        "inclusions": (
            "Donation\nEnglish-speaking local guide\n"
            "Return transfers from Ubud, Sanur, Kuta, Seminyak, Canggu & Candidasa\n"
            "Welcome drink\nCoffee or tea at the local house\nEntrance fees\n"
            "Dance performance"
        ),
        "exclusions": "",
        "pickup_areas": PICKUP_AREAS,
        "tiers": [
            (1, 1, 1300000), (2, 2, 700000), (3, 5, 600000),
            (6, None, 500000),
        ],
    },
    {
        "code": "BLESSING-CEREMONY",
        "name": "Balinese Blessing Ceremony at the Natural Springs",
        "category": "Ceremony",
        "description": (
            "Sarong-and-sash temple attire, offering-making, temple ceremony led "
            "by a local priest, and a cleansing ritual at the sacred spring water "
            "spouts, finishing with a blessing and short prayer."
        ),
        "start_time": None,
        "duration_note": None,
        "inclusions": (
            "Sarong and sash\nEnglish-speaking local guide\n"
            "Return transfer from Ubud, Sanur, Kuta, Seminyak, Canggu & Candidasa\n"
            "Welcome drink"
        ),
        "exclusions": "Meals\nPersonal expenses (souvenirs, tipping, etc.)",
        "pickup_areas": PICKUP_AREAS,
        "tiers": [
            (1, 1, 1474000), (2, 2, 737000), (3, 5, 591000),
            (6, None, 500000),
        ],
    },
]


def seed_data():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM company_profile")
    if cur.fetchone()[0] == 0:
        cur.execute(
            """INSERT INTO company_profile
               (id, company_name, bank_name, bank_account_number, bank_account_name,
                default_currency, payment_terms_note, cancellation_policy_note)
               VALUES (1, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "Happy Local Adventure",
                "BCA",
                "6700273201",
                "I Gusti Agung Made Bara Oka",
                "IDR",
                "Full payment must be received 5 days prior to the activity date.",
                "Cancellation 7+ days prior to the activity: 50% fee. "
                "Cancellation within 7 days (as little as 1 day) prior: 100% fee.",
            ),
        )

    cur.execute("SELECT COUNT(*) FROM bank_accounts")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT INTO bank_accounts (bank_name, account_number, account_name, is_primary) "
            "VALUES (?, ?, ?, 1)",
            ("BCA", "6700273201", "I Gusti Agung Made Bara Oka"),
        )

    cur.execute("SELECT COUNT(*) FROM pickup_areas")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO pickup_areas (name) VALUES (?)",
            [(a,) for a in PICKUP_AREAS],
        )

    area_ids = {row["name"]: row["id"] for row in cur.execute("SELECT id, name FROM pickup_areas")}

    cur.execute("SELECT COUNT(*) FROM activities")
    if cur.fetchone()[0] == 0:
        for act in ACTIVITIES:
            cur.execute(
                """INSERT INTO activities
                   (code, name, category, description, start_time, duration_note,
                    inclusions, exclusions, rate_valid_from, rate_valid_to, currency)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    act["code"], act["name"], act["category"], act["description"],
                    act["start_time"], act["duration_note"], act["inclusions"],
                    act["exclusions"], "2026-01-01", "2027-12-31", "IDR",
                ),
            )
            activity_id = cur.lastrowid

            for area_name in act["pickup_areas"]:
                cur.execute(
                    "INSERT INTO activity_pickup_areas (activity_id, pickup_area_id) VALUES (?, ?)",
                    (activity_id, area_ids[area_name]),
                )

            for min_pax, max_pax, price in act["tiers"]:
                note = "data gap in source PDF - confirm with vendor" if act["code"] == "DINNER-LOCALS" and min_pax == 6 else None
                cur.execute(
                    """INSERT INTO activity_price_tiers
                       (activity_id, min_pax, max_pax, price_per_person, note)
                       VALUES (?, ?, ?, ?, ?)""",
                    (activity_id, min_pax, max_pax, price, note),
                )

    cur.execute("SELECT COUNT(*) FROM partners")
    if cur.fetchone()[0] == 0:
        cur.execute(
            """INSERT INTO partners (code, name, company, email, phone, country, payment_terms_days)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("AGT-001", "Wayan Sudiarta", "Bali Sunrise Tours", "wayan@balisunrisetours.example",
             "+62-812-0000-0000", "Indonesia", 0),
        )

    cur.execute("SELECT COUNT(*) FROM guides")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO guides (name, phone, languages) VALUES (?, ?, ?)",
                    ("Made Sujana", "+62-813-1111-1111", "English, Indonesian"))

    cur.execute("SELECT COUNT(*) FROM drivers")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO drivers (name, phone, vehicle_info) VALUES (?, ?, ?)",
                    ("Ketut Arta", "+62-813-2222-2222", "Toyota Avanza - DK 1234 XX"))

    conn.commit()
    conn.close()
    print("Sample/contract data loaded successfully.")


# =====================================================================
# Demo dataset - a larger, realistic-looking spread of bookings,
# cancellations, expenses, invoices and payments across the last ~30
# days and the next ~2 weeks, so dashboards/reports have real numbers
# to show instead of an empty database. Safe to run once; re-running
# after bookings already exist is a no-op (delete erp.db and reseed to
# regenerate from scratch).
# =====================================================================

EXTRA_PARTNERS = [
    ("AGT-002", "Ni Luh Kadek", "Ubud Travel Collective", "kadek@ubudtravel.example",
     "+62-812-1111-2222", "Indonesia", 0),
    ("AGT-003", "James Whitfield", "Southern Cross Holidays", "james@southerncross.example",
     "+61-4-1234-5678", "Australia", 7),
    ("AGT-004", "Yuki Tanaka", "Sakura Bali Tours", "yuki@sakurabali.example",
     "+81-90-1234-5678", "Japan", 0),
    ("AGT-005", "Lena Fischer", "EuroBali DMC", "lena@eurobali.example",
     "+49-151-1234567", "Germany", 14),
]

EXTRA_GUIDES = [
    ("Nyoman Ariawan", "+62-813-3333-1111", "English, Indonesian"),
    ("Putu Ardana", "+62-813-3333-2222", "English, Japanese, Indonesian"),
]

EXTRA_DRIVERS = [
    ("Wayan Sutrisna", "+62-813-4444-1111", "Toyota Hiace - DK 5678 XX"),
    ("Made Putra", "+62-813-4444-2222", "Suzuki APV - DK 9012 XX"),
]

CANCEL_REASONS = ["Client rescheduled", "Weather concerns", "Change of itinerary", "Flight changed"]

PAX_DISTRIBUTION = [1, 2, 2, 3, 3, 4, 4, 5, 6, 6, 7, 8, 9, 10, 12]


def seed_demo_data():
    conn = connect_db()
    cur = conn.cursor()
    existing = cur.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    conn.close()
    if existing > 5:
        print("Demo data already present (bookings exist) - skipping. "
              "Delete erp.db and re-run init/seed/seed-demo to regenerate.")
        return

    random.seed(7)

    conn = connect_db()
    cur = conn.cursor()
    partner_ids = [row["id"] for row in cur.execute("SELECT id FROM partners")]
    for p in EXTRA_PARTNERS:
        cur.execute(
            """INSERT INTO partners (code, name, company, email, phone, country, payment_terms_days)
               VALUES (?, ?, ?, ?, ?, ?, ?)""", p,
        )
        partner_ids.append(cur.lastrowid)

    for name, phone, lang in EXTRA_GUIDES:
        cur.execute("INSERT INTO guides (name, phone, languages) VALUES (?, ?, ?)", (name, phone, lang))
    for name, phone, info in EXTRA_DRIVERS:
        cur.execute("INSERT INTO drivers (name, phone, vehicle_info) VALUES (?, ?, ?)", (name, phone, info))
    conn.commit()
    conn.close()

    today = datetime.now().date()
    start_range = today - timedelta(days=30)
    end_range = today + timedelta(days=14)
    total_days = (end_range - start_range).days

    for act in ACTIVITIES:
        code = act["code"]
        areas = act["pickup_areas"]
        n_bookings = random.randint(16, 22)
        for _ in range(n_bookings):
            activity_date = start_range + timedelta(days=random.randint(0, total_days))
            pax = random.choice(PAX_DISTRIBUTION)
            partner_id = random.choice(partner_ids)
            pickup = random.choice(areas) if areas else None
            try:
                booking_id = create_booking(code, partner_id, pax, activity_date.isoformat(), pickup_area=pickup)
            except Exception:
                continue

            conn = connect_db()
            c2 = conn.cursor()
            if activity_date < today:
                if random.random() < 0.08:
                    cancel_date = max(activity_date - timedelta(days=random.choice([1, 3, 7, 10])), start_range)
                    conn.close()
                    try:
                        cancel_booking(booking_id, cancel_date.isoformat(), reason=random.choice(CANCEL_REASONS))
                    except Exception:
                        pass
                else:
                    c2.execute("UPDATE bookings SET status = 'Completed' WHERE id = ?", (booking_id,))
                    for category, lo, hi in [
                        ("Guide fee", 150000, 250000),
                        ("Transport", 100000, 180000),
                        ("Ingredients / Donation", 50000, 150000),
                    ]:
                        amount = random.randint(lo, hi)
                        c2.execute(
                            """INSERT INTO expenses (expense_date, booking_id, category, description, amount)
                               VALUES (?, ?, ?, ?, ?)""",
                            (activity_date.isoformat(), booking_id, category,
                             f"{category} for booking {booking_id}", amount),
                        )
                    conn.commit()
                    conn.close()
            else:
                if random.random() < 0.15:
                    c2.execute("UPDATE bookings SET status = 'Pending' WHERE id = ?", (booking_id,))
                conn.commit()
                conn.close()

    # Consolidate each partner's confirmed/completed bookings into invoices
    # (batches of 3), then simulate payment behaviour: fully paid, partially
    # paid, or left open (some of those will age into Overdue automatically).
    conn = connect_db()
    cur = conn.cursor()
    for partner_id in partner_ids:
        booking_rows = cur.execute(
            """SELECT id FROM bookings WHERE partner_id = ? AND status IN ('Completed', 'Confirmed')
               ORDER BY activity_date""",
            (partner_id,),
        ).fetchall()
        batch = []
        for row in booking_rows:
            batch.append(row["id"])
            if len(batch) == 3:
                _invoice_and_maybe_pay(partner_id, batch)
                batch = []
        if batch:
            _invoice_and_maybe_pay(partner_id, batch)
    conn.close()

    refresh_overdue_invoices()
    print("Demo dataset generated: partners, guides, drivers, bookings, cancellations, "
          "expenses, invoices and payments.")


def _invoice_and_maybe_pay(partner_id, booking_ids):
    try:
        invoice_id = generate_invoice(partner_id, booking_ids)
    except Exception:
        return
    conn = connect_db()
    invoice = conn.execute("SELECT total_amount FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    conn.close()

    roll = random.random()
    if roll < 0.55:
        record_payment(invoice_id, invoice["total_amount"], method="Bank Transfer",
                        reference=f"BCA-{invoice_id:05d}")
    elif roll < 0.8:
        partial = round(invoice["total_amount"] * random.uniform(0.3, 0.7), -3)
        record_payment(invoice_id, partial, method="Bank Transfer", reference=f"BCA-{invoice_id:05d}")
    # else: left unpaid - a genuine open/overdue invoice for the A/R report


def refresh_overdue_invoices():
    """Flip Sent/Partially Paid invoices whose due date has passed to Overdue."""
    conn = connect_db()
    today = datetime.now().date().isoformat()
    conn.execute(
        """UPDATE invoices SET status = 'Overdue'
           WHERE due_date < ? AND status NOT IN ('Paid', 'Cancelled', 'Overdue')
             AND (total_amount - paid_amount) > 0""",
        (today,),
    )
    conn.commit()
    conn.close()


# =====================================================================
# Catalog management (activities / products + their price tiers)
# =====================================================================

def create_activity(code, name, category=None, description=None, start_time=None,
                     duration_note=None, inclusions=None, exclusions=None,
                     rate_valid_from=None, rate_valid_to=None, currency="IDR"):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO activities
           (code, name, category, description, start_time, duration_note,
            inclusions, exclusions, rate_valid_from, rate_valid_to, currency)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (code, name, category, description, start_time, duration_note,
         inclusions, exclusions, rate_valid_from, rate_valid_to, currency),
    )
    activity_id = cur.lastrowid
    conn.commit()
    conn.close()
    return activity_id


def update_activity(activity_id, **fields):
    """Update only the given columns, e.g. update_activity(3, name='New name')."""
    if not fields:
        return
    conn = connect_db()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE activities SET {set_clause} WHERE id = ?", (*fields.values(), activity_id))
    conn.commit()
    conn.close()


def set_activity_active(activity_id, is_active):
    conn = connect_db()
    conn.execute("UPDATE activities SET is_active = ? WHERE id = ?", (1 if is_active else 0, activity_id))
    conn.commit()
    conn.close()


def add_price_tier(activity_id, min_pax, max_pax, price_per_person, note=None):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO activity_price_tiers (activity_id, min_pax, max_pax, price_per_person, note)
           VALUES (?, ?, ?, ?, ?)""",
        (activity_id, min_pax, max_pax, price_per_person, note),
    )
    tier_id = cur.lastrowid
    conn.commit()
    conn.close()
    return tier_id


def update_price_tier(tier_id, min_pax, max_pax, price_per_person, note=None):
    conn = connect_db()
    conn.execute(
        """UPDATE activity_price_tiers SET min_pax = ?, max_pax = ?, price_per_person = ?, note = ?
           WHERE id = ?""",
        (min_pax, max_pax, price_per_person, note, tier_id),
    )
    conn.commit()
    conn.close()


def delete_price_tier(tier_id):
    conn = connect_db()
    conn.execute("DELETE FROM activity_price_tiers WHERE id = ?", (tier_id,))
    conn.commit()
    conn.close()


# =====================================================================
# Client management (partners / travel agents - the invoiced clients)
# =====================================================================

def next_partner_code(conn):
    n = conn.execute("SELECT COUNT(*) AS n FROM partners").fetchone()["n"] + 1
    return f"AGT-{n:03d}"


def create_partner(name, code=None, company=None, email=None, phone=None,
                    country=None, payment_terms_days=0):
    conn = connect_db()
    cur = conn.cursor()
    code = code or next_partner_code(conn)
    cur.execute(
        """INSERT INTO partners (code, name, company, email, phone, country, payment_terms_days)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (code, name, company, email, phone, country, payment_terms_days),
    )
    partner_id = cur.lastrowid
    conn.commit()
    conn.close()
    return partner_id


def update_partner(partner_id, **fields):
    if not fields:
        return
    conn = connect_db()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE partners SET {set_clause} WHERE id = ?", (*fields.values(), partner_id))
    conn.commit()
    conn.close()


def set_partner_active(partner_id, is_active):
    conn = connect_db()
    conn.execute("UPDATE partners SET is_active = ? WHERE id = ?", (1 if is_active else 0, partner_id))
    conn.commit()
    conn.close()


def get_unbilled_bookings(partner_id=None):
    """Confirmed/Completed bookings that have never been added to an invoice -
    the automation source for one-click client invoicing, and the guard
    against accidentally billing the same booking twice."""
    conn = connect_db()
    query = """SELECT b.* FROM bookings b
               WHERE b.status IN ('Confirmed', 'Completed')
                 AND b.id NOT IN (SELECT booking_id FROM invoice_items WHERE booking_id IS NOT NULL)"""
    params = []
    if partner_id is not None:
        query += " AND b.partner_id = ?"
        params.append(partner_id)
    query += " ORDER BY b.activity_date"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


# =====================================================================
# Booking engine
# =====================================================================

def get_price_per_person(conn, activity_id, pax_count):
    row = conn.execute(
        """SELECT price_per_person FROM activity_price_tiers
           WHERE activity_id = ? AND min_pax <= ?
             AND (max_pax IS NULL OR max_pax >= ?)""",
        (activity_id, pax_count, pax_count),
    ).fetchone()
    if not row:
        raise ValueError(f"No price tier found for activity_id={activity_id}, pax={pax_count}")
    return row["price_per_person"]


def quote(activity_code, pax_count):
    conn = connect_db()
    activity = conn.execute("SELECT * FROM activities WHERE code = ?", (activity_code,)).fetchone()
    if not activity:
        conn.close()
        raise ValueError(f"Activity not found: {activity_code}")
    price = get_price_per_person(conn, activity["id"], pax_count)
    conn.close()
    subtotal = price * pax_count
    print(f"{activity['name']} | {pax_count} pax @ IDR {price:,.0f} = IDR {subtotal:,.0f}")
    return price, subtotal


def next_booking_code(conn):
    n = conn.execute("SELECT COUNT(*) AS n FROM bookings").fetchone()["n"] + 1
    return f"BK-{datetime.now().strftime('%Y%m%d')}-{n:04d}"


def create_booking(activity_code, partner_id, pax_count, activity_date, pickup_area=None,
                    pickup_time=None, customer_id=None, special_requests=None):
    conn = connect_db()
    cur = conn.cursor()

    activity = cur.execute("SELECT * FROM activities WHERE code = ?", (activity_code,)).fetchone()
    if not activity:
        conn.close()
        raise ValueError(f"Activity not found: {activity_code}")

    partner = cur.execute("SELECT * FROM partners WHERE id = ?", (partner_id,)).fetchone()
    if not partner:
        conn.close()
        raise ValueError(f"Partner not found: {partner_id}")

    price = get_price_per_person(conn, activity["id"], pax_count)
    subtotal = price * pax_count

    pickup_area_id = None
    if pickup_area:
        row = cur.execute("SELECT id FROM pickup_areas WHERE name = ?", (pickup_area,)).fetchone()
        if not row:
            conn.close()
            raise ValueError(f"Pickup area not found: {pickup_area}")
        pickup_area_id = row["id"]

    booking_code = next_booking_code(conn)
    cur.execute(
        """INSERT INTO bookings
           (booking_code, activity_id, partner_id, customer_id, activity_date, pickup_time,
            pax_count, pickup_area_id, price_per_person, subtotal, status, special_requests)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Confirmed', ?)""",
        (booking_code, activity["id"], partner_id, customer_id, activity_date, pickup_time,
         pax_count, pickup_area_id, price, subtotal, special_requests),
    )
    booking_id = cur.lastrowid
    conn.commit()
    conn.close()
    print(f"Booking {booking_code} created (id={booking_id}): {activity['name']} on {activity_date}, "
          f"{pax_count} pax, subtotal IDR {subtotal:,.0f}")
    return booking_id


def update_booking(booking_id, activity_date=None, pax_count=None, pickup_area=None,
                    pickup_time=None, status=None, special_requests=None):
    """Edit an existing booking's operational details. Changing pax_count
    re-resolves price_per_person/subtotal from the tier table (tiered
    pricing means a different pax count can land in a different tier) -
    everything else is a plain field update."""
    conn = connect_db()
    booking = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not booking:
        conn.close()
        raise ValueError(f"Booking not found: {booking_id}")

    fields = {}
    if activity_date is not None:
        fields["activity_date"] = activity_date
    if pickup_time is not None:
        fields["pickup_time"] = pickup_time or None
    if special_requests is not None:
        fields["special_requests"] = special_requests or None
    if status is not None:
        if status not in ("Pending", "Confirmed", "Completed", "Cancelled"):
            conn.close()
            raise ValueError(f"Invalid status: {status}")
        fields["status"] = status

    if pickup_area is not None:
        pickup_area_id = None
        if pickup_area:
            row = conn.execute("SELECT id FROM pickup_areas WHERE name = ?", (pickup_area,)).fetchone()
            if not row:
                conn.close()
                raise ValueError(f"Pickup area not found: {pickup_area}")
            pickup_area_id = row["id"]
        fields["pickup_area_id"] = pickup_area_id

    if pax_count is not None and pax_count != booking["pax_count"]:
        price = get_price_per_person(conn, booking["activity_id"], pax_count)
        fields["pax_count"] = pax_count
        fields["price_per_person"] = price
        fields["subtotal"] = price * pax_count

    if not fields:
        conn.close()
        return

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE bookings SET {set_clause} WHERE id = ?", (*fields.values(), booking_id))
    conn.commit()
    conn.close()
    print(f"Booking {booking['booking_code']} updated: {', '.join(fields.keys())}")


def cancel_booking(booking_id, cancelled_at, reason=None):
    conn = connect_db()
    cur = conn.cursor()
    booking = cur.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not booking:
        conn.close()
        raise ValueError(f"Booking not found: {booking_id}")

    activity_date = parse_date(booking["activity_date"])
    cancel_date = parse_date(cancelled_at)
    days_before = (activity_date - cancel_date).days

    # Contract policy: 7+ days notice -> 50% fee; less than 7 days -> 100% fee.
    if days_before >= 7:
        fee_pct = 50.0
    else:
        fee_pct = 100.0
    fee_amount = booking["subtotal"] * fee_pct / 100.0

    cur.execute("UPDATE bookings SET status = 'Cancelled' WHERE id = ?", (booking_id,))
    cur.execute(
        """INSERT INTO cancellations
           (booking_id, cancelled_at, days_before_activity, fee_percentage, fee_amount, reason)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (booking_id, cancelled_at, days_before, fee_pct, fee_amount, reason),
    )
    conn.commit()
    conn.close()
    print(f"Booking {booking['booking_code']} cancelled ({days_before} days before activity): "
          f"{fee_pct:.0f}% fee = IDR {fee_amount:,.0f}")
    return fee_amount


# =====================================================================
# Company settings (profile, bank/account, invoice preferences)
# =====================================================================

def get_company_profile():
    conn = connect_db()
    row = conn.execute("SELECT * FROM company_profile WHERE id = 1").fetchone()
    conn.close()
    return row


def update_company_profile(**fields):
    if not fields:
        return
    conn = connect_db()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE company_profile SET {set_clause} WHERE id = 1", tuple(fields.values()))
    conn.commit()
    conn.close()


def list_bank_accounts():
    conn = connect_db()
    rows = conn.execute("SELECT * FROM bank_accounts ORDER BY is_primary DESC, id").fetchall()
    conn.close()
    return rows


def get_primary_bank_account():
    conn = connect_db()
    row = conn.execute("SELECT * FROM bank_accounts WHERE is_primary = 1 LIMIT 1").fetchone()
    if not row:
        row = conn.execute("SELECT * FROM bank_accounts ORDER BY id LIMIT 1").fetchone()
    conn.close()
    return row


def add_bank_account(bank_name, account_number, account_name, is_primary=False):
    conn = connect_db()
    cur = conn.cursor()
    if is_primary:
        cur.execute("UPDATE bank_accounts SET is_primary = 0")
    cur.execute(
        "INSERT INTO bank_accounts (bank_name, account_number, account_name, is_primary) VALUES (?, ?, ?, ?)",
        (bank_name, account_number, account_name, 1 if is_primary else 0),
    )
    account_id = cur.lastrowid
    # The very first account is always primary, regardless of the checkbox,
    # so there's never a bank-details box with nothing to print.
    count = conn.execute("SELECT COUNT(*) AS n FROM bank_accounts").fetchone()["n"]
    if count == 1:
        cur.execute("UPDATE bank_accounts SET is_primary = 1 WHERE id = ?", (account_id,))
    conn.commit()
    conn.close()
    return account_id


def set_primary_bank_account(account_id):
    conn = connect_db()
    conn.execute("UPDATE bank_accounts SET is_primary = 0")
    conn.execute("UPDATE bank_accounts SET is_primary = 1 WHERE id = ?", (account_id,))
    conn.commit()
    conn.close()


def delete_bank_account(account_id):
    conn = connect_db()
    row = conn.execute("SELECT is_primary FROM bank_accounts WHERE id = ?", (account_id,)).fetchone()
    conn.execute("DELETE FROM bank_accounts WHERE id = ?", (account_id,))
    if row and row["is_primary"]:
        nxt = conn.execute("SELECT id FROM bank_accounts ORDER BY id LIMIT 1").fetchone()
        if nxt:
            conn.execute("UPDATE bank_accounts SET is_primary = 1 WHERE id = ?", (nxt["id"],))
    conn.commit()
    conn.close()


# =====================================================================
# Invoicing
# =====================================================================

def next_invoice_number(conn):
    n = conn.execute("SELECT COUNT(*) AS n FROM invoices").fetchone()["n"] + 1
    row = conn.execute("SELECT invoice_prefix FROM company_profile WHERE id = 1").fetchone()
    prefix = (row["invoice_prefix"] if row and row["invoice_prefix"] else "INV")
    return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{n:04d}"


def generate_invoice(partner_id, booking_ids, invoice_date=None, notes=None):
    conn = connect_db()
    cur = conn.cursor()

    invoice_date = invoice_date or datetime.now().date().isoformat()
    bookings = []
    for bid in booking_ids:
        b = cur.execute("SELECT * FROM bookings WHERE id = ? AND partner_id = ?", (bid, partner_id)).fetchone()
        if not b:
            conn.close()
            raise ValueError(f"Booking {bid} not found for partner {partner_id}")
        already_billed = cur.execute(
            "SELECT 1 FROM invoice_items WHERE booking_id = ?", (bid,)
        ).fetchone()
        if already_billed:
            conn.close()
            raise ValueError(f"Booking {b['booking_code']} (id={bid}) is already on an invoice")
        bookings.append(b)

    if not bookings:
        conn.close()
        raise ValueError("No bookings supplied for invoice")

    # Payment terms: full payment N days before the earliest activity date
    # covered, N being the configurable company setting (contract default: 5).
    company = cur.execute("SELECT payment_due_days_before_activity FROM company_profile WHERE id = 1").fetchone()
    due_days = company["payment_due_days_before_activity"] if company and company["payment_due_days_before_activity"] is not None else 5
    earliest_activity = min(parse_date(b["activity_date"]) for b in bookings)
    due_date = (earliest_activity - timedelta(days=due_days)).isoformat()

    subtotal = sum(b["subtotal"] for b in bookings)
    total_amount = subtotal  # discount_amount left at 0 unless adjusted later

    currency_row = cur.execute("SELECT default_currency FROM company_profile WHERE id = 1").fetchone()
    currency = (currency_row["default_currency"] if currency_row and currency_row["default_currency"] else "IDR")

    invoice_number = next_invoice_number(conn)
    cur.execute(
        """INSERT INTO invoices
           (invoice_number, partner_id, invoice_date, due_date, currency,
            subtotal, discount_amount, total_amount, paid_amount, status, notes)
           VALUES (?, ?, ?, ?, ?, ?, 0, ?, 0, 'Sent', ?)""",
        (invoice_number, partner_id, invoice_date, due_date, currency, subtotal, total_amount, notes),
    )
    invoice_id = cur.lastrowid

    for b in bookings:
        activity = cur.execute("SELECT name FROM activities WHERE id = ?", (b["activity_id"],)).fetchone()
        description = f"{activity['name']} - {b['activity_date']} ({b['booking_code']})"
        cur.execute(
            """INSERT INTO invoice_items (invoice_id, booking_id, description, pax_count, unit_price, line_total)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (invoice_id, b["id"], description, b["pax_count"], b["price_per_person"], b["subtotal"]),
        )

    conn.commit()
    conn.close()
    print(f"Invoice {invoice_number} created (id={invoice_id}), total IDR {total_amount:,.0f}, due {due_date}")
    return invoice_id


def record_payment(invoice_id, amount, payment_date=None, method="Bank Transfer", reference=None, notes=None):
    conn = connect_db()
    cur = conn.cursor()
    invoice = cur.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    if not invoice:
        conn.close()
        raise ValueError(f"Invoice not found: {invoice_id}")

    payment_date = payment_date or datetime.now().date().isoformat()
    cur.execute(
        """INSERT INTO payments (invoice_id, payment_date, amount, method, bank_reference, notes)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (invoice_id, payment_date, amount, method, reference, notes),
    )

    new_paid = invoice["paid_amount"] + amount
    if new_paid >= invoice["total_amount"]:
        status = "Paid"
    elif new_paid > 0:
        status = "Partially Paid"
    else:
        status = invoice["status"]

    cur.execute("UPDATE invoices SET paid_amount = ?, status = ? WHERE id = ?",
                (new_paid, status, invoice_id))
    conn.commit()
    conn.close()
    print(f"Payment of IDR {amount:,.0f} recorded on invoice {invoice['invoice_number']}. "
          f"Status: {status} (paid IDR {new_paid:,.0f} of IDR {invoice['total_amount']:,.0f})")


def update_invoice(invoice_id, invoice_date=None, due_date=None, discount_amount=None,
                    notes=None, status=None):
    """Edit an invoice's own fields (dates, discount, notes, manual status
    override). Line items aren't editable here - they're a snapshot of the
    bookings billed at generation time. Changing discount_amount re-derives
    total_amount = subtotal - discount_amount."""
    conn = connect_db()
    invoice = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    if not invoice:
        conn.close()
        raise ValueError(f"Invoice not found: {invoice_id}")

    fields = {}
    if invoice_date is not None:
        fields["invoice_date"] = invoice_date
    if due_date is not None:
        fields["due_date"] = due_date
    if notes is not None:
        fields["notes"] = notes or None
    if status is not None:
        valid_statuses = ("Draft", "Sent", "Partially Paid", "Paid", "Overdue", "Cancelled")
        if status not in valid_statuses:
            conn.close()
            raise ValueError(f"Invalid status: {status}")
        fields["status"] = status
    if discount_amount is not None:
        discount_amount = float(discount_amount)
        if discount_amount < 0:
            conn.close()
            raise ValueError("Discount amount cannot be negative")
        fields["discount_amount"] = discount_amount
        fields["total_amount"] = invoice["subtotal"] - discount_amount

    if not fields:
        conn.close()
        return

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE invoices SET {set_clause} WHERE id = ?", (*fields.values(), invoice_id))
    conn.commit()
    conn.close()
    print(f"Invoice {invoice['invoice_number']} updated: {', '.join(fields.keys())}")


INVOICE_HTML_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Invoice {invoice_number}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', Arial, Helvetica, sans-serif; color: #1c1c1c; margin: 0; padding: 48px; background: #fff; }}
  .muted {{ color: #6b6b6b; }}

  .header {{ display:flex; justify-content:space-between; align-items:flex-start; border-bottom: 3px solid #0b4972; padding-bottom: 18px; margin-bottom: 26px; }}
  .header .brand {{ display:flex; align-items:center; gap:14px; }}
  .header .brand img {{ width:56px; height:56px; flex-shrink:0; }}
  .header h1 {{ margin: 0; font-size: 1.6em; color: #14151a; }}
  .doc-title {{ text-align:right; }}
  .doc-title .label {{ font-size: 1.9em; font-weight: 800; letter-spacing: 0.03em; color: #d9840f; line-height:1; }}
  .status-pill {{ display:inline-block; margin-top:8px; padding: 3px 12px; border-radius: 20px; font-size: 0.78em; font-weight:700; border: 1.5px solid; }}
  .status-Paid, .status-Confirmed, .status-Completed, .status-Active {{ color: #1a7a35; border-color:#1a7a35; }}
  .status-Sent, .status-Draft, .status-PartiallyPaid, .status-Pending {{ color: #a56b00; border-color:#a56b00; }}
  .status-Overdue, .status-Cancelled, .status-Inactive {{ color: #b03434; border-color:#b03434; }}

  .meta-grid {{ display:flex; gap: 32px; margin-bottom: 26px; }}
  .meta-grid .box {{ flex:1; }}
  .meta-grid .box .k {{ font-size: 0.72em; text-transform:uppercase; letter-spacing:0.05em; color:#8a8a8a; margin-bottom:4px; }}
  .meta-grid .box .v {{ font-size: 0.95em; }}

  table {{ width: 100%; border-collapse: collapse; margin-top: 6px; }}
  th, td {{ border-bottom: 1px solid #e4e4e4; padding: 9px 8px; text-align: left; font-size: 0.92em; }}
  th {{ background: #f7f6f4; color:#555; text-transform:uppercase; font-size:0.72em; letter-spacing:0.04em; border-bottom: 2px solid #ddd; }}

  .totals {{ width: 300px; margin-left: auto; margin-top: 14px; }}
  .totals td {{ border: none; padding: 5px 4px; font-size: 0.92em; }}
  .totals .grand-total td {{ font-weight: 800; font-size: 1.15em; border-top: 2px solid #14151a; padding-top:10px; }}
  .totals .balance td {{ color: #b03434; }}
  .totals .balance.paid td {{ color: #1a7a35; }}

  .bank-box {{ margin-top: 32px; padding: 16px 18px; background: #fff8e9; border: 1px solid #f2e2b8; border-radius: 8px; }}
  .bank-box .title {{ font-weight: 700; color:#14151a; margin-bottom:6px; }}
  .terms {{ margin-top: 22px; padding-top: 14px; border-top: 1px solid #e4e4e4; font-size: 0.85em; color: #555; line-height:1.5; }}
</style>
</head>
<body>
  <div class="header">
    <div class="brand">
      <img src="{logo_data_uri}" alt="">
      <h1>{company_name}</h1>
    </div>
    <div class="doc-title">
      <div class="label">INVOICE</div>
      <div class="status-pill status-{status_class}">{status}</div>
    </div>
  </div>

  <div class="meta-grid">
    <div class="box">
      <div class="k">Bill To</div>
      <div class="v"><strong>{partner_name}</strong><br>{partner_company}</div>
    </div>
    <div class="box">
      <div class="k">Invoice No.</div>
      <div class="v">{invoice_number}</div>
    </div>
    <div class="box">
      <div class="k">Invoice Date</div>
      <div class="v">{invoice_date}</div>
    </div>
    <div class="box">
      <div class="k">Due Date</div>
      <div class="v">{due_date}</div>
    </div>
  </div>

  <table>
    <tr><th>Description</th><th>Pax</th><th>Unit Price (IDR)</th><th>Line Total (IDR)</th></tr>
    {rows}
  </table>

  <table class="totals">
    <tr><td>Subtotal</td><td style="text-align:right">IDR {subtotal:,.0f}</td></tr>
    <tr><td>Discount</td><td style="text-align:right">IDR {discount_amount:,.0f}</td></tr>
    <tr class="grand-total"><td>Total Due</td><td style="text-align:right">IDR {total_amount:,.0f}</td></tr>
    <tr><td>Paid</td><td style="text-align:right">IDR {paid_amount:,.0f}</td></tr>
    <tr class="grand-total balance{balance_paid_class}"><td>Balance</td><td style="text-align:right">IDR {balance:,.0f}</td></tr>
  </table>

  <div class="bank-box">
    <div class="title">Bank Transfer Details</div>
    Bank: {bank_name}<br>
    Account Number: {bank_account_number}<br>
    Account Name: {bank_account_name}
  </div>

  <div class="terms">
    <strong>Terms &amp; Conditions</strong><br>
    {payment_terms_note}<br>
    {cancellation_policy_note}
  </div>
</body>
</html>
"""


def render_invoice_html(invoice_id, out_path):
    conn = connect_db()
    invoice = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    if not invoice:
        conn.close()
        raise ValueError(f"Invoice not found: {invoice_id}")

    partner = conn.execute("SELECT * FROM partners WHERE id = ?", (invoice["partner_id"],)).fetchone()
    items = conn.execute("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice_id,)).fetchall()
    company = conn.execute("SELECT * FROM company_profile WHERE id = 1").fetchone()
    bank = conn.execute("SELECT * FROM bank_accounts WHERE is_primary = 1 LIMIT 1").fetchone() \
        or conn.execute("SELECT * FROM bank_accounts ORDER BY id LIMIT 1").fetchone()
    conn.close()

    rows = "".join(
        f"<tr><td>{it['description']}</td><td>{it['pax_count'] or ''}</td>"
        f"<td>{it['unit_price']:,.0f}</td><td>{it['line_total']:,.0f}</td></tr>"
        for it in items
    )
    balance = invoice["total_amount"] - invoice["paid_amount"]

    html = INVOICE_HTML_TEMPLATE.format(
        logo_data_uri=LOGO_DATA_URI,
        company_name=company["company_name"] if company else "Happy Local Adventure",
        invoice_number=invoice["invoice_number"],
        invoice_date=invoice["invoice_date"],
        due_date=invoice["due_date"],
        status=invoice["status"],
        status_class=invoice["status"].replace(" ", ""),
        partner_name=partner["name"],
        partner_company=partner["company"] or "",
        rows=rows,
        subtotal=invoice["subtotal"],
        discount_amount=invoice["discount_amount"],
        total_amount=invoice["total_amount"],
        paid_amount=invoice["paid_amount"],
        balance=balance,
        balance_paid_class=" paid" if balance <= 0 else "",
        bank_name=bank["bank_name"] if bank else "Not set",
        bank_account_number=bank["account_number"] if bank else "-",
        bank_account_name=bank["account_name"] if bank else "-",
        payment_terms_note=company["payment_terms_note"] if company else "",
        cancellation_policy_note=company["cancellation_policy_note"] if company else "",
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Invoice HTML written to {out_path}")


# =====================================================================
# Reporting
# =====================================================================

def _print_rows(title, rows):
    print(title)
    print("-" * len(title))
    if not rows:
        print("(no data)")
        return
    for row in rows:
        print(dict(row))


def report(report_type):
    conn = connect_db()
    if report_type == "revenue-by-activity":
        _print_rows("Revenue by Activity", conn.execute("SELECT * FROM v_revenue_by_activity").fetchall())
    elif report_type == "revenue-by-partner":
        _print_rows("Revenue by Partner", conn.execute("SELECT * FROM v_revenue_by_partner").fetchall())
    elif report_type == "outstanding":
        _print_rows("Outstanding Invoices (Accounts Receivable)",
                    conn.execute("SELECT * FROM v_outstanding_invoices").fetchall())
    elif report_type == "upcoming":
        _print_rows("Upcoming Bookings", conn.execute("SELECT * FROM v_upcoming_bookings").fetchall())
    elif report_type == "cancellations":
        _print_rows("Cancellations", conn.execute("SELECT * FROM v_cancellations").fetchall())
    elif report_type == "profitability":
        _print_rows("Booking Profitability", conn.execute("SELECT * FROM v_booking_profitability").fetchall())
    else:
        raise ValueError(f"Unknown report type: {report_type}")
    conn.close()


def list_activities():
    conn = connect_db()
    activities = conn.execute("SELECT * FROM activities ORDER BY name").fetchall()
    for a in activities:
        print(f"\n{a['code']} - {a['name']} (start {a['start_time'] or 'n/a'})")
        tiers = conn.execute(
            "SELECT * FROM activity_price_tiers WHERE activity_id = ? ORDER BY min_pax", (a["id"],)
        ).fetchall()
        for t in tiers:
            pax_label = f"{t['min_pax']}+" if t["max_pax"] is None else f"{t['min_pax']}-{t['max_pax']}"
            flag = f"  [{t['note']}]" if t["note"] else ""
            print(f"  {pax_label} pax: IDR {t['price_per_person']:,.0f}{flag}")
    conn.close()


# =====================================================================
# CLI
# =====================================================================

def main():
    parser = argparse.ArgumentParser(description="Happy Local Adventure - Tour Operator ERP")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize the database from schema.sql")
    sub.add_parser("seed", help="Load contract-rate activities and sample master data")
    sub.add_parser("seed-demo", help="Generate a larger realistic demo dataset (bookings, invoices, payments)")
    sub.add_parser("list-activities", help="List activities and their pax price tiers")

    p = sub.add_parser("quote", help="Quote the price for an activity at a given pax count")
    p.add_argument("--activity", required=True, help="Activity code, e.g. VILLAGE-COOKING")
    p.add_argument("--pax", type=int, required=True)

    p = sub.add_parser("book", help="Create a booking")
    p.add_argument("--activity", required=True)
    p.add_argument("--partner-id", type=int, required=True)
    p.add_argument("--pax", type=int, required=True)
    p.add_argument("--date", required=True, help="Activity date, YYYY-MM-DD")
    p.add_argument("--pickup-area")
    p.add_argument("--pickup-time")
    p.add_argument("--customer-id", type=int)
    p.add_argument("--notes")

    p = sub.add_parser("cancel-booking", help="Cancel a booking and apply the contract cancellation fee")
    p.add_argument("--booking-id", type=int, required=True)
    p.add_argument("--cancel-date", required=True, help="YYYY-MM-DD")
    p.add_argument("--reason")

    p = sub.add_parser("invoice", help="Generate an invoice from one or more bookings")
    p.add_argument("--partner-id", type=int, required=True)
    p.add_argument("--booking-ids", type=int, nargs="+", required=True)
    p.add_argument("--invoice-date")
    p.add_argument("--notes")

    p = sub.add_parser("pay", help="Record a payment against an invoice")
    p.add_argument("--invoice-id", type=int, required=True)
    p.add_argument("--amount", type=float, required=True)
    p.add_argument("--date")
    p.add_argument("--method", default="Bank Transfer")
    p.add_argument("--reference")
    p.add_argument("--notes")

    p = sub.add_parser("invoice-html", help="Render a printable HTML invoice")
    p.add_argument("--invoice-id", type=int, required=True)
    p.add_argument("--out", default=None, help="Output path (default: invoice_<number>.html)")

    p = sub.add_parser("report", help="Run a report")
    p.add_argument("--type", required=True, choices=[
        "revenue-by-activity", "revenue-by-partner", "outstanding",
        "upcoming", "cancellations", "profitability",
    ])

    args = parser.parse_args()

    if args.command == "init":
        init_db()
    elif args.command == "seed":
        seed_data()
    elif args.command == "seed-demo":
        seed_demo_data()
    elif args.command == "list-activities":
        list_activities()
    elif args.command == "quote":
        quote(args.activity, args.pax)
    elif args.command == "book":
        create_booking(args.activity, args.partner_id, args.pax, args.date,
                        pickup_area=args.pickup_area, pickup_time=args.pickup_time,
                        customer_id=args.customer_id, special_requests=args.notes)
    elif args.command == "cancel-booking":
        cancel_booking(args.booking_id, args.cancel_date, reason=args.reason)
    elif args.command == "invoice":
        generate_invoice(args.partner_id, args.booking_ids, invoice_date=args.invoice_date, notes=args.notes)
    elif args.command == "pay":
        record_payment(args.invoice_id, args.amount, payment_date=args.date,
                        method=args.method, reference=args.reference, notes=args.notes)
    elif args.command == "invoice-html":
        conn = connect_db()
        inv = conn.execute("SELECT invoice_number FROM invoices WHERE id = ?", (args.invoice_id,)).fetchone()
        conn.close()
        out_path = args.out or f"invoice_{inv['invoice_number']}.html"
        render_invoice_html(args.invoice_id, out_path)
    elif args.command == "report":
        report(args.type)


if __name__ == "__main__":
    main()
