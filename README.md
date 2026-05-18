Single-user POS & Inventory (Flask + SQLite)

Setup

- Requires Python 3.8+ and pip.
- Install dependency:

```
pip install Flask
```

Run

```
python pos_app.py
# Open http://localhost:5000 in your browser
```

Storage

- Data persists in `data.db` in the same folder (SQLite).

Features

- Inventory: add/edit/delete products (name, cost, price, qty, low-stock threshold).
- POS: select products, adjust qty, accept payment, auto-deduct stock on checkout.
- Daily Report: revenue, gross profit, top-selling items, and sales log for selected date.

Notes

- Single-user, no authentication. Intended for local/offline use.
- Keep backups of `data.db` for safety.
