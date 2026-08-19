# Purchase Tracker

A small, self-hosted web app for keeping Target and Walmart purchases and their UPS, USPS, or FedEx tracking numbers in one dashboard.

## Features

- Mobile-friendly dashboard
- Add, edit, and delete purchases
- Target, Walmart, or other stores
- UPS, USPS, FedEx, or other carriers
- Clickable carrier tracking links
- Arrival dates and simple shipment statuses
- Delivered purchase history
- SQLite database; no external database required

## Run with Docker

```bash
docker compose up -d --build
```

Open `http://localhost:5000`.

The SQLite database is stored in the persistent Docker volume `purchase-data`.

Before exposing the app beyond your local network, change `SECRET_KEY` in `docker-compose.yml`.

## Run without Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000`.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Data model

The app intentionally uses one simple `purchases` table. If one order arrives in multiple shipments, add each shipment as a separate purchase entry.
