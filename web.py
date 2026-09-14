"""
Happy Local Adventure — Tour Operator ERP Web Controller
========================================================
Flask web application serving modern Jinja2 templates, dispatch calendar,
booking engine, settlements, and reporting analytics.
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify, session
)

import app as erp

flask_app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)
flask_app.secret_key = "happy-local-adventure-secret-key-2026-auth"

ACCESS_PASSWORD = os.getenv("APP_PASSWORD", "Bara-Kayaraya")
LOGO_DATA_URI = erp.LOGO_DATA_URI


@flask_app.before_request
def check_auth():
    # Allow login page and static assets without session
    if request.endpoint in ("login", "static") or (request.path.startswith("/static/")):
        return None
    if not session.get("authenticated"):
        return redirect(url_for("login", next=request.path))


@flask_app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("authenticated"):
        return redirect(url_for("index"))
    error = None
    if request.method == "POST":
        pwd = request.form.get("password", "").strip()
        if pwd == ACCESS_PASSWORD:
            session["authenticated"] = True
            next_url = request.args.get("next") or url_for("index")
            flash("Welcome! Authentication successful.")
            return redirect(next_url)
        else:
            error = "Password tidak sesuai. Silakan coba lagi."
    return render_template("login.html", error=error, logo_data_uri=LOGO_DATA_URI)


@flask_app.route("/logout")
def logout():
    session.pop("authenticated", None)
    flash("Anda telah berhasil logout.")
    return redirect(url_for("login"))


def get_db():
    conn = erp.connect_db()
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------
# SVG Revenue Trend Chart Generator (Lightweight, No External Libraries)
# ---------------------------------------------------------------------
def generate_revenue_trend_svg(values, labels, width=680, height=220):
    if not values or not any(values):
        return "<p class='muted' style='text-align:center; padding:32px 0;'>No revenue data in this period</p>"

    pad_l, pad_r, pad_t, pad_b = 64, 24, 20, 32
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b
    raw_max = max(values) or 1
    magnitude = 10 ** max(0, len(str(int(raw_max))) - 2)
    nice_max = max(magnitude, -(-int(raw_max) // magnitude) * magnitude)

    n = len(values)
    step_x = plot_w / (n - 1) if n > 1 else 0
    pts = []
    for i, v in enumerate(values):
        x = pad_l + i * step_x
        y = pad_t + plot_h - (v / nice_max) * plot_h
        pts.append((x, y))

    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    base_y = pad_t + plot_h
    area_path = (f"M{pts[0][0]:.1f},{base_y:.1f} " +
                 " ".join(f"L{x:.1f},{y:.1f}" for x, y in pts) +
                 f" L{pts[-1][0]:.1f},{base_y:.1f} Z")

    gridlines, grid_labels = "", ""
    for frac in (0.0, 0.5, 1.0):
        gy = pad_t + plot_h - frac * plot_h
        gval = nice_max * frac
        gridlines += f'<line x1="{pad_l}" y1="{gy:.1f}" x2="{width - pad_r}" y2="{gy:.1f}" stroke="var(--border)" stroke-width="1"/>'
        grid_labels += f'<text x="{pad_l - 10}" y="{gy + 4:.1f}" text-anchor="end" font-size="10" fill="var(--ink-muted)">IDR {gval / 1_000_000:.1f}M</text>'

    x_labels = ""
    label_idxs = sorted(set([0, n // 2, n - 1])) if n > 2 else list(range(n))
    for idx in label_idxs:
        x_labels += f'<text x="{pts[idx][0]:.1f}" y="{height - 8}" text-anchor="middle" font-size="10" fill="var(--ink-muted)">{labels[idx]}</text>'

    dots = ""
    for i, (x, y) in enumerate(pts):
        dots += (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="var(--accent)">'
                 f'<title>{labels[i]}: IDR {values[i]:,.0f}</title></circle>')

    return f"""
    <svg width="100%" height="{height}" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet" style="overflow:visible;display:block">
      <defs>
        <linearGradient id="revAreaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.3"/>
          <stop offset="100%" stop-color="var(--accent)" stop-opacity="0.0"/>
        </linearGradient>
      </defs>
      {gridlines}
      <path d="{area_path}" fill="url(#revAreaGrad)" stroke="none"/>
      <polyline points="{poly}" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      {dots}
      {grid_labels}
      {x_labels}
    </svg>
    """


# ---------------------------------------------------------------------
# Application Routes
# ---------------------------------------------------------------------

@flask_app.route("/")
def index():
    conn = get_db()
    today = datetime.now().date()
    today_str = today.isoformat()

    # Total Revenue (Confirmed / Completed)
    rev_row = conn.execute(
        "SELECT COALESCE(SUM(subtotal), 0) AS total FROM bookings WHERE status IN ('Confirmed', 'Completed')"
    ).fetchone()
    total_revenue = rev_row["total"] if rev_row else 0

    # Upcoming Bookings Stats
    up_row = conn.execute(
        "SELECT COUNT(*) AS c, COALESCE(SUM(pax_count), 0) AS pax FROM bookings WHERE activity_date >= ? AND status IN ('Pending', 'Confirmed')",
        (today_str,)
    ).fetchone()
    upcoming_count = up_row["c"] if up_row else 0
    total_pax_upcoming = up_row["pax"] if up_row else 0

    # Outstanding Invoices
    inv_row = conn.execute(
        "SELECT COUNT(*) AS c, COALESCE(SUM(total_amount - paid_amount), 0) AS balance FROM invoices WHERE status NOT IN ('Paid', 'Cancelled')"
    ).fetchone()
    pending_invoices_count = inv_row["c"] if inv_row else 0
    outstanding_balance = inv_row["balance"] if inv_row else 0

    # Partners Count
    partner_row = conn.execute("SELECT COUNT(*) AS c FROM partners WHERE is_active = 1").fetchone()
    partner_count = partner_row["c"] if partner_row else 0

    # 30-Day Revenue Trend Data
    start_date = today - timedelta(days=29)
    trend_rows = conn.execute(
        """SELECT activity_date, SUM(subtotal) AS rev FROM bookings
           WHERE activity_date >= ? AND activity_date <= ? AND status IN ('Confirmed', 'Completed')
           GROUP BY activity_date""",
        (start_date.isoformat(), today_str)
    ).fetchall()
    by_day = {r["activity_date"]: r["rev"] for r in trend_rows}

    dates = [(start_date + timedelta(days=i)) for i in range(30)]
    labels = [d.strftime("%d %b") for d in dates]
    values = [by_day.get(d.isoformat(), 0) for d in dates]
    chart_svg = generate_revenue_trend_svg(values, labels)

    # Activity & Partners Data for Quick Booking
    activities = conn.execute("SELECT id, name, category, code FROM activities WHERE is_active = 1 ORDER BY id").fetchall()
    partners = conn.execute("SELECT id, name, code, company FROM partners WHERE is_active = 1 ORDER BY name").fetchall()

    # Activity Tiers JSON for dynamic JS calculation
    tiers_rows = conn.execute("SELECT activity_id, min_pax, max_pax, price_per_person FROM activity_price_tiers ORDER BY min_pax").fetchall()
    tiers_map = {}
    for t in tiers_rows:
        aid = t["activity_id"]
        if aid not in tiers_map:
            tiers_map[aid] = []
        tiers_map[aid].append({
            "min_pax": t["min_pax"],
            "max_pax": t["max_pax"],
            "price": t["price_per_person"]
        })

    # Upcoming Tours
    upcoming_tours = conn.execute(
        """SELECT b.id, b.booking_code, a.name AS activity_name, b.activity_date, b.pickup_time,
                  b.pax_count, p.name AS partner_name, g.name AS guide_name, d.name AS driver_name, b.status
           FROM bookings b
           JOIN activities a ON a.id = b.activity_id
           JOIN partners p ON p.id = b.partner_id
           LEFT JOIN guides g ON g.id = b.guide_id
           LEFT JOIN drivers d ON d.id = b.driver_id
           WHERE b.activity_date >= ? AND b.status IN ('Pending', 'Confirmed')
           ORDER BY b.activity_date ASC, b.pickup_time ASC LIMIT 10""",
        (today_str,)
    ).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        title="Dashboard",
        active_page="dashboard",
        logo_data_uri=LOGO_DATA_URI,
        total_revenue=total_revenue,
        upcoming_count=upcoming_count,
        total_pax_upcoming=total_pax_upcoming,
        outstanding_balance=outstanding_balance,
        pending_invoices_count=pending_invoices_count,
        partner_count=partner_count,
        chart_svg=chart_svg,
        activities_list=activities,
        partners_list=partners,
        tiers_json=json.dumps(tiers_map),
        today_date=today_str,
        upcoming_tours=upcoming_tours
    )


@flask_app.route("/calendar")
def calendar_view():
    offset = int(request.args.get("offset", 0))
    conn = get_db()
    today = datetime.now().date()
    start_date = today + timedelta(days=offset)

    days_data = []
    for i in range(7):
        curr = start_date + timedelta(days=i)
        curr_str = curr.isoformat()
        b_rows = conn.execute(
            """SELECT b.booking_code, a.name AS activity_name, b.pax_count, b.pickup_time,
                      g.name AS guide_name, d.name AS driver_name, b.status
               FROM bookings b
               JOIN activities a ON a.id = b.activity_id
               LEFT JOIN guides g ON g.id = b.guide_id
               LEFT JOIN drivers d ON d.id = b.driver_id
               WHERE b.activity_date = ? AND b.status != 'Cancelled'
               ORDER BY b.pickup_time ASC""",
            (curr_str,)
        ).fetchall()

        days_data.append({
            "date_str": curr.strftime("%d %b"),
            "day_name": curr.strftime("%a"),
            "is_today": (curr == today),
            "bookings": b_rows
        })

    guides = conn.execute("SELECT name, languages, phone FROM guides WHERE is_active = 1").fetchall()
    drivers = conn.execute("SELECT name, vehicle_info, phone FROM drivers WHERE is_active = 1").fetchall()
    conn.close()

    return render_template(
        "calendar.html",
        title="Dispatch Operations Calendar",
        active_page="calendar",
        logo_data_uri=LOGO_DATA_URI,
        calendar_days=days_data,
        guides_list=guides,
        drivers_list=drivers,
        prev_offset=offset - 7,
        next_offset=offset + 7
    )


@flask_app.route("/activities")
def activities():
    conn = get_db()
    act_rows = conn.execute("SELECT * FROM activities WHERE is_active = 1 ORDER BY id").fetchall()
    activities_with_tiers = []
    for a in act_rows:
        tiers = conn.execute(
            "SELECT min_pax, max_pax, price_per_person FROM activity_price_tiers WHERE activity_id = ? ORDER BY min_pax",
            (a["id"],)
        ).fetchall()
        activities_with_tiers.append({
            "id": a["id"],
            "code": a["code"],
            "name": a["name"],
            "category": a["category"],
            "description": a["description"],
            "start_time": a["start_time"],
            "duration_note": a["duration_note"],
            "rate_valid_from": a["rate_valid_from"],
            "rate_valid_to": a["rate_valid_to"],
            "tiers": tiers
        })
    conn.close()

    return render_template(
        "activities.html",
        title="Activities & Contract Rates",
        active_page="activities",
        logo_data_uri=LOGO_DATA_URI,
        activities_with_tiers=activities_with_tiers
    )


@flask_app.route("/activities/<int:activity_id>/edit")
def edit_activity_view(activity_id):
    conn = get_db()
    activity = conn.execute("SELECT * FROM activities WHERE id = ?", (activity_id,)).fetchone()
    if not activity:
        conn.close()
        flash("Activity not found.")
        return redirect(url_for("activities"))

    tiers = conn.execute(
        "SELECT * FROM activity_price_tiers WHERE activity_id = ? ORDER BY min_pax ASC",
        (activity_id,)
    ).fetchall()
    conn.close()

    return render_template(
        "activity_edit.html",
        title=f"Edit {activity['name']}",
        active_page="activities",
        logo_data_uri=LOGO_DATA_URI,
        activity=activity,
        tiers=tiers
    )


@flask_app.route("/activities/<int:activity_id>/update", methods=["POST"])
def update_activity(activity_id):
    try:
        code = request.form["code"].strip().upper()
        name = request.form["name"].strip()
        category = request.form["category"].strip()
        start_time = request.form.get("start_time", "").strip() or None
        duration_note = request.form.get("duration_note", "").strip() or None
        valid_from = request.form.get("rate_valid_from", "").strip() or None
        valid_to = request.form.get("rate_valid_to", "").strip() or None
        description = request.form.get("description", "").strip() or None
        inclusions = request.form.get("inclusions", "").strip() or None
        exclusions = request.form.get("exclusions", "").strip() or None

        conn = get_db()
        conn.execute(
            """UPDATE activities
               SET code = ?, name = ?, category = ?, start_time = ?, duration_note = ?,
                   rate_valid_from = ?, rate_valid_to = ?, description = ?, inclusions = ?, exclusions = ?
               WHERE id = ?""",
            (code, name, category, start_time, duration_note, valid_from, valid_to, description, inclusions, exclusions, activity_id)
        )
        conn.commit()
        conn.close()
        flash(f"Activity '{name}' updated successfully.")
    except Exception as e:
        flash(f"Error updating activity: {str(e)}")

    return redirect(url_for("edit_activity_view", activity_id=activity_id))


@flask_app.route("/activities/<int:activity_id>/tiers/update", methods=["POST"])
def update_activity_tiers(activity_id):
    conn = get_db()
    try:
        tiers = conn.execute("SELECT id FROM activity_price_tiers WHERE activity_id = ?", (activity_id,)).fetchall()
        for t in tiers:
            tid = t["id"]
            min_k = f"tier_min_{tid}"
            max_k = f"tier_max_{tid}"
            price_k = f"tier_price_{tid}"

            if min_k in request.form and price_k in request.form:
                min_pax = int(request.form[min_k])
                max_pax = int(request.form[max_k]) if request.form.get(max_k) else None
                price = float(request.form[price_k])

                conn.execute(
                    "UPDATE activity_price_tiers SET min_pax = ?, max_pax = ?, price_per_person = ? WHERE id = ?",
                    (min_pax, max_pax, price, tid)
                )

        conn.commit()
        flash("Price tiers updated successfully.")
    except Exception as e:
        flash(f"Error updating price tiers: {str(e)}")
    finally:
        conn.close()

    return redirect(url_for("edit_activity_view", activity_id=activity_id))


@flask_app.route("/activities/<int:activity_id>/tiers/add", methods=["POST"])
def add_activity_tier(activity_id):
    try:
        min_pax = int(request.form["min_pax"])
        max_pax = int(request.form["max_pax"]) if request.form.get("max_pax") else None
        price = float(request.form["price_per_person"])

        conn = get_db()
        conn.execute(
            """INSERT INTO activity_price_tiers (activity_id, min_pax, max_pax, price_per_person)
               VALUES (?, ?, ?, ?)""",
            (activity_id, min_pax, max_pax, price)
        )
        conn.commit()
        conn.close()
        flash(f"New pricing tier ({min_pax}-{max_pax or '+'} pax @ IDR {price:,.0f}) added.")
    except Exception as e:
        flash(f"Error adding tier: {str(e)}")

    return redirect(url_for("edit_activity_view", activity_id=activity_id))


@flask_app.route("/activities/<int:activity_id>/tiers/<int:tier_id>/delete")
def delete_activity_tier(activity_id, tier_id):
    try:
        conn = get_db()
        conn.execute("DELETE FROM activity_price_tiers WHERE id = ? AND activity_id = ?", (tier_id, activity_id))
        conn.commit()
        conn.close()
        flash("Pricing tier deleted.")
    except Exception as e:
        flash(f"Error deleting tier: {str(e)}")

    return redirect(url_for("edit_activity_view", activity_id=activity_id))


@flask_app.route("/activities/create", methods=["POST"])
def create_activity():
    try:
        code = request.form["code"].strip().upper()
        name = request.form["name"].strip()
        category = request.form["category"].strip()
        start_time = request.form.get("start_time", "").strip() or "08:30"
        description = request.form.get("description", "").strip() or None

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO activities (code, name, category, start_time, description, rate_valid_from, rate_valid_to)
               VALUES (?, ?, ?, ?, ?, '2026-01-01', '2027-12-31')""",
            (code, name, category, start_time, description)
        )
        act_id = cur.lastrowid
        # Add default starter tiers
        cur.execute("INSERT INTO activity_price_tiers (activity_id, min_pax, max_pax, price_per_person) VALUES (?, 1, 1, 1500000)", (act_id,))
        cur.execute("INSERT INTO activity_price_tiers (activity_id, min_pax, max_pax, price_per_person) VALUES (?, 2, 3, 950000)", (act_id,))
        cur.execute("INSERT INTO activity_price_tiers (activity_id, min_pax, max_pax, price_per_person) VALUES (?, 4, 8, 750000)", (act_id,))
        cur.execute("INSERT INTO activity_price_tiers (activity_id, min_pax, max_pax, price_per_person) VALUES (?, 9, NULL, 600000)", (act_id,))
        conn.commit()
        conn.close()
        flash(f"Activity {name} ({code}) created. You can now customize its rates.")
        return redirect(url_for("edit_activity_view", activity_id=act_id))
    except Exception as e:
        flash(f"Error creating activity: {str(e)}")
        return redirect(url_for("activities"))


@flask_app.route("/bookings")
def bookings():
    conn = get_db()
    today_str = datetime.now().date().isoformat()

    bookings_list = conn.execute(
        """SELECT b.id, b.booking_code, a.name AS activity_name, b.activity_date, b.pax_count,
                  p.name AS partner_name, b.price_per_person, b.subtotal, b.status,
                  g.name AS guide_name, d.name AS driver_name
           FROM bookings b
           JOIN activities a ON a.id = b.activity_id
           JOIN partners p ON p.id = b.partner_id
           LEFT JOIN guides g ON g.id = b.guide_id
           LEFT JOIN drivers d ON d.id = b.driver_id
           ORDER BY b.activity_date DESC, b.id DESC"""
    ).fetchall()

    activities_list = conn.execute("SELECT id, name FROM activities WHERE is_active = 1").fetchall()
    partners_list = conn.execute("SELECT id, name, company, code FROM partners WHERE is_active = 1").fetchall()
    guides_list = conn.execute("SELECT id, name, languages FROM guides WHERE is_active = 1").fetchall()
    drivers_list = conn.execute("SELECT id, name, vehicle_info FROM drivers WHERE is_active = 1").fetchall()
    pickup_areas = conn.execute("SELECT id, name FROM pickup_areas ORDER BY name").fetchall()

    conn.close()

    return render_template(
        "bookings.html",
        title="Bookings Management",
        active_page="bookings",
        logo_data_uri=LOGO_DATA_URI,
        bookings_list=bookings_list,
        activities_list=activities_list,
        partners_list=partners_list,
        guides_list=guides_list,
        drivers_list=drivers_list,
        pickup_areas=pickup_areas,
        today_date=today_str
    )


@flask_app.route("/bookings/create", methods=["POST"])
def create_booking_route():
    try:
        activity_id = int(request.form["activity_id"])
        partner_id = int(request.form["partner_id"])
        pax_count = int(request.form["pax_count"])
        activity_date = request.form["activity_date"]
        pickup_area_id = int(request.form["pickup_area_id"]) if request.form.get("pickup_area_id") else None
        pickup_time = request.form.get("pickup_time") or None
        guide_id = int(request.form["guide_id"]) if request.form.get("guide_id") else None
        driver_id = int(request.form["driver_id"]) if request.form.get("driver_id") else None
        special_requests = request.form.get("special_requests") or None

        conn = get_db()
        act = conn.execute("SELECT code FROM activities WHERE id = ?", (activity_id,)).fetchone()
        if not act:
            conn.close()
            flash("Error: Activity not found.")
            return redirect(url_for("bookings"))

        rate = erp.get_price_per_person(conn, act["code"], pax_count)
        if not rate:
            conn.close()
            flash("Error: No valid rate found for this group size.")
            return redirect(url_for("bookings"))

        b_id, code, subtotal = erp.create_booking(
            conn,
            activity_code=act["code"],
            partner_id=partner_id,
            activity_date=activity_date,
            pax_count=pax_count,
            pickup_area_id=pickup_area_id,
            pickup_time=pickup_time,
            guide_id=guide_id,
            driver_id=driver_id,
            special_requests=special_requests
        )
        conn.close()
        flash(f"Booking {code} successfully created (Total: IDR {subtotal:,.0f}).")
    except Exception as e:
        flash(f"Failed to create booking: {str(e)}")

    return redirect(url_for("bookings"))


@flask_app.route("/quick-booking", methods=["POST"])
def create_quick_booking():
    try:
        activity_id = int(request.form["activity_id"])
        partner_id = int(request.form["partner_id"])
        pax_count = int(request.form["pax_count"])
        activity_date = request.form["activity_date"]

        conn = get_db()
        act = conn.execute("SELECT code FROM activities WHERE id = ?", (activity_id,)).fetchone()
        if not act:
            conn.close()
            flash("Error: Selected activity not found.")
            return redirect(url_for("index"))

        b_id, code, subtotal = erp.create_booking(
            conn,
            activity_code=act["code"],
            partner_id=partner_id,
            activity_date=activity_date,
            pax_count=pax_count
        )
        conn.close()
        flash(f"Quick Booking {code} confirmed! Total: IDR {subtotal:,.0f}")
    except Exception as e:
        flash(f"Error creating quick booking: {str(e)}")

    return redirect(url_for("index"))


@flask_app.route("/clients")
def clients():
    conn = get_db()
    partners_list = conn.execute("SELECT * FROM partners ORDER BY name").fetchall()
    conn.close()

    return render_template(
        "clients.html",
        title="Partners & Agents",
        active_page="clients",
        logo_data_uri=LOGO_DATA_URI,
        partners_list=partners_list
    )


@flask_app.route("/clients/create", methods=["POST"])
def create_partner_route():
    try:
        code = request.form["code"].strip().upper()
        name = request.form["name"].strip()
        company = request.form.get("company", "").strip() or None
        email = request.form.get("email", "").strip() or None
        phone = request.form.get("phone", "").strip() or None
        payment_terms = int(request.form.get("payment_terms_days", 0))

        conn = get_db()
        conn.execute(
            """INSERT INTO partners (code, name, company, email, phone, payment_terms_days)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (code, name, company, email, phone, payment_terms)
        )
        conn.commit()
        conn.close()
        flash(f"Partner {name} ({code}) added successfully.")
    except Exception as e:
        flash(f"Error adding partner: {str(e)}")

    return redirect(url_for("clients"))


@flask_app.route("/invoices")
def invoices():
    conn = get_db()
    today_str = datetime.now().date().isoformat()

    invoices_list = conn.execute(
        """SELECT i.id, i.invoice_number, p.name AS partner_name, i.invoice_date,
                  i.due_date, i.total_amount, i.paid_amount, (i.total_amount - i.paid_amount) AS balance_due,
                  i.status, (i.due_date < ? AND i.status NOT IN ('Paid', 'Cancelled')) AS is_overdue
           FROM invoices i
           JOIN partners p ON p.id = i.partner_id
           ORDER BY i.id DESC""",
        (today_str,)
    ).fetchall()

    conn.close()

    return render_template(
        "invoices.html",
        title="Invoices & Settlements",
        active_page="invoices",
        logo_data_uri=LOGO_DATA_URI,
        invoices_list=invoices_list,
        today_date=today_str
    )


@flask_app.route("/invoices/<int:invoice_id>")
def view_invoice(invoice_id):
    conn = get_db()
    inv = conn.execute(
        """SELECT i.*, p.name AS partner_name, p.company AS partner_company, p.email AS partner_email
           FROM invoices i
           JOIN partners p ON p.id = i.partner_id
           WHERE i.id = ?""",
        (invoice_id,)
    ).fetchone()

    if not inv:
        conn.close()
        flash("Invoice not found.")
        return redirect(url_for("invoices"))

    items = conn.execute("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice_id,)).fetchall()
    bank = conn.execute("SELECT * FROM bank_accounts WHERE is_primary = 1 LIMIT 1").fetchone()
    if not bank:
        bank = conn.execute("SELECT bank_name, bank_account_number AS account_number, bank_account_name AS account_name FROM company_profile WHERE id = 1").fetchone()

    conn.close()

    return render_template(
        "invoice_view.html",
        invoice=inv,
        items=items,
        bank=bank or {},
        logo_data_uri=LOGO_DATA_URI
    )


@flask_app.route("/invoices/pay", methods=["POST"])
def record_payment_route():
    try:
        invoice_id = int(request.form["invoice_id"])
        payment_date = request.form["payment_date"]
        amount = float(request.form["amount"])
        bank_ref = request.form.get("bank_reference", "").strip() or None

        conn = get_db()
        new_status = erp.record_payment(
            conn,
            invoice_id=invoice_id,
            amount=amount,
            payment_date=payment_date,
            bank_reference=bank_ref
        )
        conn.close()
        flash(f"Payment of IDR {amount:,.0f} recorded. Invoice status: {new_status}.")
    except Exception as e:
        flash(f"Error recording payment: {str(e)}")

    return redirect(url_for("invoices"))


@flask_app.route("/reports")
def reports():
    view_type = request.args.get("view", "revenue_activity")
    conn = get_db()

    report_data = []
    max_val = 1
    total_sum = 0
    total_pax = 0

    if view_type == "revenue_activity":
        report_data = conn.execute("SELECT * FROM v_revenue_by_activity").fetchall()
        if report_data:
            max_val = max([r["total_revenue"] for r in report_data] or [1]) or 1
            total_sum = sum([r["total_revenue"] for r in report_data])
            total_pax = sum([r["total_pax"] for r in report_data])
    elif view_type == "revenue_partner":
        report_data = conn.execute("SELECT * FROM v_revenue_by_partner").fetchall()
        if report_data:
            max_val = max([r["total_revenue"] for r in report_data] or [1]) or 1
            total_sum = sum([r["total_revenue"] for r in report_data])
            total_pax = sum([r["total_pax"] for r in report_data])
    elif view_type == "profitability":
        report_data = conn.execute("SELECT * FROM v_booking_profitability LIMIT 50").fetchall()
        if report_data:
            total_sum = sum([r["revenue"] for r in report_data])
            max_val = max([r["revenue"] for r in report_data] or [1]) or 1
    elif view_type == "cancellations":
        report_data = conn.execute("SELECT * FROM v_cancellations").fetchall()
        if report_data:
            total_sum = sum([r["fee_amount"] for r in report_data])

    conn.close()

    return render_template(
        "reports.html",
        title="Management Reports",
        active_page="reports",
        logo_data_uri=LOGO_DATA_URI,
        current_view=view_type,
        report_data=report_data,
        max_val=max_val,
        total_sum=total_sum,
        total_pax=total_pax
    )


@flask_app.route("/settings")
def settings_view():
    conn = get_db()
    company = conn.execute("SELECT * FROM company_profile WHERE id = 1").fetchone()
    bank_accounts = conn.execute("SELECT * FROM bank_accounts ORDER BY is_primary DESC, id ASC").fetchall()
    guides = conn.execute("SELECT * FROM guides ORDER BY name ASC").fetchall()
    drivers = conn.execute("SELECT * FROM drivers ORDER BY name ASC").fetchall()
    conn.close()

    return render_template(
        "settings.html",
        title="ERP Settings",
        active_page="settings",
        logo_data_uri=LOGO_DATA_URI,
        company=company or {},
        bank_accounts=bank_accounts,
        guides=guides,
        drivers=drivers
    )


@flask_app.route("/settings/company", methods=["POST"])
def update_company_profile():
    try:
        name = request.form["company_name"].strip()
        prefix = request.form["invoice_prefix"].strip().upper()
        due_days = int(request.form["due_days"])
        currency = request.form["default_currency"].strip().upper()
        terms_note = request.form.get("payment_terms_note", "").strip()

        conn = get_db()
        conn.execute(
            """UPDATE company_profile
               SET company_name = ?, invoice_prefix = ?, payment_due_days_before_activity = ?,
                   default_currency = ?, payment_terms_note = ?
               WHERE id = 1""",
            (name, prefix, due_days, currency, terms_note)
        )
        conn.commit()
        conn.close()
        flash("Company profile updated successfully.")
    except Exception as e:
        flash(f"Error updating company profile: {str(e)}")

    return redirect(url_for("settings_view"))


@flask_app.route("/settings/bank/add", methods=["POST"])
def add_bank_account():
    try:
        bank_name = request.form["bank_name"].strip()
        acc_num = request.form["account_number"].strip()
        acc_name = request.form["account_name"].strip()
        is_primary = 1 if request.form.get("is_primary") else 0

        conn = get_db()
        if is_primary:
            conn.execute("UPDATE bank_accounts SET is_primary = 0")
        conn.execute(
            """INSERT INTO bank_accounts (bank_name, account_number, account_name, is_primary)
               VALUES (?, ?, ?, ?)""",
            (bank_name, acc_num, acc_name, is_primary)
        )
        conn.commit()
        conn.close()
        flash(f"Bank account {bank_name} - {acc_num} added.")
    except Exception as e:
        flash(f"Error adding bank account: {str(e)}")

    return redirect(url_for("settings_view"))


@flask_app.route("/settings/guide/add", methods=["POST"])
def add_guide():
    dest = "calendar_view" if request.form.get("redirect_to") == "calendar" else "settings_view"
    try:
        name = request.form["name"].strip()
        phone = request.form.get("phone", "").strip() or None
        languages = request.form.get("languages", "").strip() or None

        conn = get_db()
        conn.execute("INSERT INTO guides (name, phone, languages) VALUES (?, ?, ?)", (name, phone, languages))
        conn.commit()
        conn.close()
        flash(f"Guide {name} registered successfully.")
    except Exception as e:
        flash(f"Error adding guide: {str(e)}")

    return redirect(url_for(dest))


@flask_app.route("/settings/driver/add", methods=["POST"])
def add_driver():
    dest = "calendar_view" if request.form.get("redirect_to") == "calendar" else "settings_view"
    try:
        name = request.form["name"].strip()
        phone = request.form.get("phone", "").strip() or None
        vehicle_info = request.form.get("vehicle_info", "").strip() or None

        conn = get_db()
        conn.execute("INSERT INTO drivers (name, phone, vehicle_info) VALUES (?, ?, ?)", (name, phone, vehicle_info))
        conn.commit()
        conn.close()
        flash(f"Driver {name} registered successfully.")
    except Exception as e:
        flash(f"Error adding driver: {str(e)}")

    return redirect(url_for(dest))


if __name__ == "__main__":
    if not os.path.exists(erp.DB_PATH):
        print("Database not found, initializing and seeding sample data...")
        c = erp.connect_db()
        erp.init_db(c)
        erp.seed_contract_rates(c)
        erp.seed_demo_data(c)
        c.close()
    flask_app.run(host="0.0.0.0", port=5000, debug=False)