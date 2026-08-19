import os
import sqlite3
from datetime import date, datetime
from urllib.parse import quote

from flask import Flask, flash, g, redirect, render_template, request, url_for


STORES = ("Target", "Walmart", "Other")
CARRIERS = ("UPS", "USPS", "FedEx", "Other")
STATUSES = ("Ordered", "Shipped", "In Transit", "Out for Delivery", "Delivered")


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "purchase-tracker-dev-key"),
        DATABASE=os.environ.get(
            "DATABASE", os.path.join(app.instance_path, "purchase-tracker.sqlite")
        ),
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        db = get_db()
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store TEXT NOT NULL,
                item TEXT NOT NULL,
                order_number TEXT,
                carrier TEXT,
                tracking_number TEXT,
                order_date TEXT,
                arrival_date TEXT,
                status TEXT NOT NULL DEFAULT 'Ordered',
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        db.commit()

    with app.app_context():
        init_db()

    @app.template_filter("pretty_date")
    def pretty_date(value):
        if not value:
            return "—"
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%b %-d, %Y")
        except (ValueError, TypeError):
            return value

    def tracking_url(carrier, tracking_number):
        if not tracking_number:
            return None
        number = quote(tracking_number.strip())
        links = {
            "UPS": f"https://www.ups.com/track?tracknum={number}",
            "USPS": f"https://tools.usps.com/go/TrackConfirmAction?tLabels={number}",
            "FedEx": f"https://www.fedex.com/fedextrack/?trknbr={number}",
        }
        return links.get(carrier)

    @app.context_processor
    def template_helpers():
        return {"tracking_url": tracking_url}

    def get_purchase_or_404(purchase_id):
        purchase = get_db().execute(
            "SELECT * FROM purchases WHERE id = ?", (purchase_id,)
        ).fetchone()
        if purchase is None:
            from flask import abort

            abort(404)
        return purchase

    def validate_form(form):
        errors = []
        if not form.get("item", "").strip():
            errors.append("Item is required.")
        if form.get("store") not in STORES:
            errors.append("Choose a valid store.")
        if form.get("carrier") not in CARRIERS:
            errors.append("Choose a valid carrier.")
        if form.get("status") not in STATUSES:
            errors.append("Choose a valid status.")
        return errors

    def form_values(form):
        return (
            form.get("store", "Target").strip(),
            form.get("item", "").strip(),
            form.get("order_number", "").strip(),
            form.get("carrier", "UPS").strip(),
            form.get("tracking_number", "").strip(),
            form.get("order_date", "").strip(),
            form.get("arrival_date", "").strip(),
            form.get("status", "Ordered").strip(),
            form.get("notes", "").strip(),
        )

    @app.route("/")
    def index():
        rows = get_db().execute(
            """
            SELECT * FROM purchases
            ORDER BY
                CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END,
                CASE WHEN arrival_date IS NULL OR arrival_date = '' THEN 1 ELSE 0 END,
                arrival_date ASC,
                id DESC
            """
        ).fetchall()

        today = date.today().isoformat()
        sections = {
            "Arriving Today": [],
            "Coming Soon": [],
            "Waiting for Shipment": [],
            "Delivered": [],
        }

        for row in rows:
            if row["status"] == "Delivered":
                sections["Delivered"].append(row)
            elif row["arrival_date"] == today:
                sections["Arriving Today"].append(row)
            elif row["arrival_date"]:
                sections["Coming Soon"].append(row)
            else:
                sections["Waiting for Shipment"].append(row)

        return render_template("index.html", sections=sections, today=today)

    @app.route("/add", methods=("GET", "POST"))
    def add_purchase():
        if request.method == "POST":
            errors = validate_form(request.form)
            if not errors:
                db = get_db()
                db.execute(
                    """
                    INSERT INTO purchases
                    (store, item, order_number, carrier, tracking_number,
                     order_date, arrival_date, status, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    form_values(request.form),
                )
                db.commit()
                flash("Purchase added.", "success")
                return redirect(url_for("index"))
            for error in errors:
                flash(error, "error")

        defaults = {
            "store": "Target",
            "carrier": "UPS",
            "status": "Ordered",
            "order_date": date.today().isoformat(),
        }
        return render_template(
            "form.html",
            title="Add Purchase",
            purchase=request.form if request.method == "POST" else defaults,
            stores=STORES,
            carriers=CARRIERS,
            statuses=STATUSES,
        )

    @app.route("/edit/<int:purchase_id>", methods=("GET", "POST"))
    def edit_purchase(purchase_id):
        purchase = get_purchase_or_404(purchase_id)
        if request.method == "POST":
            errors = validate_form(request.form)
            if not errors:
                db = get_db()
                db.execute(
                    """
                    UPDATE purchases
                    SET store = ?, item = ?, order_number = ?, carrier = ?,
                        tracking_number = ?, order_date = ?, arrival_date = ?,
                        status = ?, notes = ?
                    WHERE id = ?
                    """,
                    (*form_values(request.form), purchase_id),
                )
                db.commit()
                flash("Purchase updated.", "success")
                return redirect(url_for("index"))
            for error in errors:
                flash(error, "error")
            purchase = request.form

        return render_template(
            "form.html",
            title="Edit Purchase",
            purchase=purchase,
            stores=STORES,
            carriers=CARRIERS,
            statuses=STATUSES,
        )

    @app.post("/delete/<int:purchase_id>")
    def delete_purchase(purchase_id):
        get_purchase_or_404(purchase_id)
        db = get_db()
        db.execute("DELETE FROM purchases WHERE id = ?", (purchase_id,))
        db.commit()
        flash("Purchase deleted.", "success")
        return redirect(url_for("index"))

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
