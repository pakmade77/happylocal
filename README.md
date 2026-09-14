# Happy Local Adventure — Tour Operator ERP

An ERP built specifically around **Happy Local Adventure**'s actual business,
derived from its contract rate sheet (`Happy Local Adventure Activities.pdf`,
validity 01 Jan 2026 – 31 Dec 2027).

## 1. Business Analysis

### What kind of business this is
Happy Local Adventure sells **day-activity experiences in Bali** on a
**B2B contract-rate basis**: travel agents/DMCs book activities for their
clients at fixed net rates, not walk-in retail. This is **not** an inventory
business — there is no stock to deplete. Capacity is driven by guide and
driver availability on a given date, not by a countable SKU.

### Products (5 bookable activities)
| Code | Activity | Start Time | Notes |
|---|---|---|---|
| `VILLAGE-COOKING` | Village Explore with Balinese Cooking Experience | 08:30 | Rice-field walk, natural springs, jungle cooking, riverside lunch |
| `DINNER-LOCALS` | Dinner with Locals | 16:30 | Family compound visit, village walk, home-cooked dinner, dance |
| `JUNGLE-COOKING` | Jungle Cooking Experience | 10:00 | Fish-trap collection, foraging, wood-fired cooking, spring bath |
| `SUNSET-DINNER-LOCALS` | Sunset Dinner with Locals | 16:30 | Adds a Sunset Picnic Point (drinks/snacks) before dinner |
| `BLESSING-CEREMONY` | Balinese Blessing Ceremony at the Natural Springs | n/a | Temple ceremony + spring cleansing ritual |

### Pricing model — the central design constraint
Every activity is priced **per person, tiered by total group size** (e.g. 1
pax pays far more per head than a 9+ pax group). This rules out a flat
`unit_price` field — the schema needs a **price-tier table per activity**,
and the price actually charged must be resolved at booking time from the
group size.

**Data gap found:** the "Dinner with Locals" table in the source PDF jumps
from 5 pax straight to 7 pax, with no 6-pax rate given. The seed data carries
the 5-pax rate through 6 pax and flags it with a note in
`activity_price_tiers.note` — **confirm the real 6-pax rate with the vendor**
before using this commercially.

### Commercial terms that must be enforced, not just stated
- **Cancellation fees:** 7+ days before the activity → 50% fee; less than 7
  days (down to 1 day) before → 100% fee. Implemented in `cancel_booking()`.
- **Payment terms:** full payment must land 5 days before the activity date.
  Implemented as the default invoice due-date rule in `generate_invoice()`.
- **Transfers:** round-trip private car transfer is included in all rates —
  not a separately priced line item.
- **Pickup areas:** Dinner with Locals, Sunset Dinner with Locals, and the
  Blessing Ceremony explicitly serve Ubud, Sanur, Kuta, Seminyak, Canggu &
  Candidasa. Village Explore/Cooking and Jungle Cooking only mention "private
  transfer" without listing areas — modeled as no fixed pickup-area
  restriction.
- **Settlement:** bank transfer to BCA, account 6700273201 (I Gusti Agung
  Made Bara Oka) — stored in `company_profile` and printed on every invoice.

### Core business processes
1. Partner (agent) management
2. Activity/rate catalog management (tiered pricing, validity window)
3. Booking creation with automatic tier-based pricing
4. Cancellation handling with contractual fee calculation
5. Invoice consolidation and bank-transfer payment recording
6. Operational scheduling (guide/driver assignment per booking)
7. Expense tracking for per-booking profitability
8. Reporting for management decisions

### Key Performance Indicators
- Revenue by activity / by partner
- Outstanding invoices (accounts receivable)
- Upcoming bookings requiring guide/driver assignment
- Cancellation fees charged
- Gross margin per booking (revenue vs. direct expenses)

## 2. ERP Module Design

### Database Layer (`schema.sql`)
- **Master data:** `company_profile`, `partners`, `customers`, `pickup_areas`,
  `activities`, `activity_pickup_areas`, `activity_price_tiers`, `guides`,
  `drivers`.
- **Transactions:** `bookings` (snapshots the resolved per-person price at
  booking time so later rate changes don't retroactively alter confirmed
  bookings), `cancellations`, `invoices`, `invoice_items`, `payments`,
  `expenses`.
- **Reporting views:** `v_revenue_by_activity`, `v_revenue_by_partner`,
  `v_outstanding_invoices`, `v_upcoming_bookings`, `v_cancellations`,
  `v_booking_profitability`.

### Booking Engine
`get_price_per_person()` resolves the correct tier for a given activity and
pax count; `create_booking()` snapshots that price into the booking;
`cancel_booking()` computes days-before-activity and applies the 50%/100%
contract fee automatically.

### Invoicing Layer
`generate_invoice()` consolidates one or more bookings for a partner into a
single invoice, with the due date auto-set to 5 days before the earliest
activity covered (per the payment terms). `record_payment()` tracks partial
payments and rolls the invoice status through
Draft → Sent → Partially Paid → Paid. `render_invoice_html()` produces a
printable HTML invoice with the bank transfer box and T&C footer baked in
(open it in a browser and print to PDF).

### Reporting Layer
`report(--type ...)` prints revenue, receivables, operations schedule,
cancellations, and profitability straight from the SQL views above.

## 3. Files Included
- `schema.sql` — full database schema + reporting views
- `app.py` — CLI ERP: booking engine, invoicing, reporting
- `README.md` — this document

## 4. How to Run

```bash
# Initialize the database and load the contract rate sheet as seed data
python app.py init
python app.py seed

# Browse the catalog and its pax price tiers
python app.py list-activities

# Quote a price without booking
python app.py quote --activity VILLAGE-COOKING --pax 4

# Create a booking (partner id 1 is the seeded sample agent)
python app.py book --activity JUNGLE-COOKING --partner-id 1 --pax 6 \
    --date 2026-03-15 --pickup-area Ubud --pickup-time 09:15

# Cancel a booking (contract fee applied automatically)
python app.py cancel-booking --booking-id 1 --cancel-date 2026-03-10 --reason "Client rescheduled"

# Consolidate bookings into an invoice, due 5 days before the earliest activity
python app.py invoice --partner-id 1 --booking-ids 1 2

# Record a bank-transfer payment
python app.py pay --invoice-id 1 --amount 5000000 --method "Bank Transfer" --reference "BCA-TRX-001"

# Render a printable HTML invoice
python app.py invoice-html --invoice-id 1

# Reports
python app.py report --type revenue-by-activity
python app.py report --type revenue-by-partner
python app.py report --type outstanding
python app.py report --type upcoming
python app.py report --type cancellations
python app.py report --type profitability
```

## 5. Recommended Next Steps
- Confirm the missing 6-pax rate for "Dinner with Locals" with the vendor.
- Add user authentication and role separation (sales vs. operations vs. finance).
- Add a guide/driver day-schedule conflict check (prevent double-booking a resource).
- Add automated overdue-invoice detection (due_date passed and balance > 0 → `Overdue`).
- Add multi-currency support if selling in USD/EUR alongside IDR.
- Connect to a web frontend / dashboard with charts.
- Add PDF export (e.g. via a headless browser or a PDF library) instead of HTML-only invoices.
