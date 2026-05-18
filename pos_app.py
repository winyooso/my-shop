from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import sqlite3
from datetime import datetime, date
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data.db')

app = Flask(__name__)


def db_connect():
    # Connect to SQLite and return connection with row access by name
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    # Initialize database tables
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        cost REAL NOT NULL DEFAULT 0,
        price REAL NOT NULL DEFAULT 0,
        qty INTEGER NOT NULL DEFAULT 0,
        low_stock_threshold INTEGER NOT NULL DEFAULT 0
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP NOT NULL,
        total REAL NOT NULL,
        payment REAL NOT NULL
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS sale_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        product_id INTEGER,
        name TEXT NOT NULL,
        qty INTEGER NOT NULL,
        price REAL NOT NULL,
        cost REAL NOT NULL,
        line_total REAL NOT NULL,
        FOREIGN KEY(sale_id) REFERENCES sales(id)
    )
    ''')
    conn.commit()
    conn.close()


init_db()


BASE_HTML = '''
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Single-user POS & Inventory</title>
  <style>
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;max-width:1100px;margin:20px auto;padding:0 16px;color:#111}
    header{display:flex;justify-content:space-between;align-items:center}
    nav a{margin-right:12px;color:#0366d6;text-decoration:none}
    table{width:100%;border-collapse:collapse;margin-top:12px}
    th,td{padding:8px;border-bottom:1px solid #e6e6e6;text-align:left}
    .muted{color:#666;font-size:0.9em}
    .btn{display:inline-block;padding:6px 10px;border-radius:6px;background:#0366d6;color:white;text-decoration:none}
    .danger{background:#d9534f}
    .small{font-size:0.9em;padding:4px 8px}
    .low{color:#d9534f;font-weight:600}
    input[type=number]{width:120px}
    .pos-items{margin-top:12px}
    .flex{display:flex;gap:8px;align-items:center}
    .right{text-align:right}
    .card{border:1px solid #eee;padding:12px;border-radius:8px;margin-top:12px}
  </style>
</head>
<body>
  <header>
    <h1>POS & Inventory</h1>
    <nav>
      <a href="/">Home</a>
      <a href="/inventory">Inventory</a>
      <a href="/pos">POS</a>
      <a href="/report">Daily Report</a>
    </nav>
  </header>
  <main>
    {% block content %}{% endblock %}
  </main>
</body>
</html>
'''


@app.route('/')
def index():
    # Simple landing page
    return render_template_string(BASE_HTML + '''
    {% block content %}
    <p class="muted">Single-user Point-of-Sale and Inventory app (SQLite-backed).</p>
    <div class="card">
      <h3>Quick Actions</h3>
      <div class="flex">
        <a class="btn" href="/inventory">Manage Inventory</a>
        <a class="btn" href="/pos">Open POS</a>
        <a class="btn" href="/report">End-of-day Report</a>
      </div>
    </div>
    {% endblock %}
    ''')


@app.route('/inventory', methods=['GET'])
def inventory():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('SELECT * FROM products ORDER BY name')
    products = cur.fetchall()
    conn.close()
    return render_template_string(BASE_HTML + '''
    {% block content %}
    <h2>Inventory</h2>
    <form method="post" action="/inventory/add" style="margin-top:8px">
      <strong>Add Product</strong>
      <div class="flex" style="margin-top:8px;gap:6px;flex-wrap:wrap">
        <input name="name" placeholder="Name" required>
        <input name="cost" type="number" step="0.01" placeholder="Cost" required>
        <input name="price" type="number" step="0.01" placeholder="Price" required>
        <input name="qty" type="number" step="1" placeholder="Qty" required>
        <input name="low" type="number" step="1" placeholder="Low-stock threshold" required>
        <button class="btn small" type="submit">Add</button>
      </div>
    </form>

    <table>
      <thead><tr><th>Name</th><th>Cost</th><th>Price</th><th>Qty</th><th>Low</th><th></th></tr></thead>
      <tbody>
        {% for p in products %}
        <tr>
          <td>{{p['name']}}</td>
          <td>${{"{:.2f}".format(p['cost'])}}</td>
          <td>${{"{:.2f}".format(p['price'])}}</td>
          <td>{% if p['qty'] <= p['low_stock_threshold'] %}<span class="low">{{p['qty']}}</span>{% else %}{{p['qty']}}{% endif %}</td>
          <td>{{p['low_stock_threshold']}}</td>
          <td>
            <form method="post" action="/inventory/edit/{{p['id']}}" style="display:inline-block">
              <input name="name" value="{{p['name']}}" required>
              <input name="cost" type="number" step="0.01" value="{{p['cost']}}" required>
              <input name="price" type="number" step="0.01" value="{{p['price']}}" required>
              <input name="qty" type="number" step="1" value="{{p['qty']}}" required>
              <input name="low" type="number" step="1" value="{{p['low_stock_threshold']}}" required>
              <button class="small" type="submit">Save</button>
            </form>
            <form method="post" action="/inventory/delete/{{p['id']}}" style="display:inline-block;margin-left:6px" onsubmit="return confirm('Delete product?')">
              <button class="small danger" type="submit">Delete</button>
            </form>
          </td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
    {% endblock %}
    ''', products=products)


@app.route('/inventory/add', methods=['POST'])
def add_product():
    # Add new product to inventory
    name = request.form['name'].strip()
    cost = float(request.form['cost'])
    price = float(request.form['price'])
    qty = int(request.form['qty'])
    low = int(request.form.get('low', 0))
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('INSERT INTO products (name,cost,price,qty,low_stock_threshold) VALUES (?,?,?,?,?)',
                (name, cost, price, qty, low))
    conn.commit()
    conn.close()
    return redirect(url_for('inventory'))


@app.route('/inventory/edit/<int:pid>', methods=['POST'])
def edit_product(pid):
    # Update product fields
    name = request.form['name'].strip()
    cost = float(request.form['cost'])
    price = float(request.form['price'])
    qty = int(request.form['qty'])
    low = int(request.form.get('low', 0))
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('UPDATE products SET name=?,cost=?,price=?,qty=?,low_stock_threshold=? WHERE id=?',
                (name, cost, price, qty, low, pid))
    conn.commit()
    conn.close()
    return redirect(url_for('inventory'))


@app.route('/inventory/delete/<int:pid>', methods=['POST'])
def delete_product(pid):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('DELETE FROM products WHERE id=?', (pid,))
    conn.commit()
    conn.close()
    return redirect(url_for('inventory'))


@app.route('/pos')
def pos():
    # POS page serves product data as JSON for the client UI
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('SELECT * FROM products ORDER BY name')
    products = cur.fetchall()
    conn.close()
    return render_template_string(BASE_HTML + '''
    {% block content %}
    <h2>Point of Sale</h2>
    <div class="card">
      <div style="display:flex;gap:12px;flex-wrap:wrap">
        <div style="flex:1;min-width:260px">
          <h4>Products</h4>
          <div style="max-height:320px;overflow:auto;">
            <table>
              <thead><tr><th>Name</th><th>Price</th><th>Qty</th><th></th></tr></thead>
              <tbody>
                {% for p in products %}
                <tr>
                  <td>{{p['name']}}</td>
                  <td>${{"{:.2f}".format(p['price'])}}</td>
                  <td>{% if p['qty'] <= p['low_stock_threshold'] %}<span class="low">{{p['qty']}}</span>{% else %}{{p['qty']}}{% endif %}</td>
                  <td><button class="small" onclick="addItem({{p['id']}},'{{p['name'].replace("'","\'\'")}}',{{p['price']}},{{p['qty']}})">Add</button></td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
        </div>
        <div style="flex:1;min-width:280px">
          <h4>Sale</h4>
          <div id="sale" class="pos-items card"></div>
          <div class="card">
            <div class="flex">
              <div><strong>Total:</strong></div>
              <div class="right" id="total">$0.00</div>
            </div>
            <div style="margin-top:8px" class="flex">
              <div>Payment:</div>
              <input id="payment" type="number" step="0.01" value="0">
              <button class="btn" onclick="checkout()">Checkout</button>
            </div>
            <div style="margin-top:8px">Change: <span id="change">$0.00</span></div>
            <div id="msg" class="muted" style="margin-top:8px"></div>
          </div>
        </div>
      </div>
    </div>

    <script>
      let items = [];
      function addItem(id,name,price,stock){
        let found = items.find(i=>i.id===id);
        if(found){
          if(found.qty+1>stock){ alert('Not enough stock'); return; }
          found.qty++;
        } else {
          if(stock<=0){ alert('Out of stock'); return; }
          items.push({id:id,name:name,price:price,qty:1});
        }
        renderSale();
      }
      function renderSale(){
        const el = document.getElementById('sale');
        el.innerHTML='';
        let total=0;
        items.forEach((it,idx)=>{
          let row = document.createElement('div');
          row.className='flex';
          row.style.justifyContent='space-between';
          let left = document.createElement('div');
          left.innerText=it.name + ' x ' + it.qty;
          let right = document.createElement('div');
          right.innerHTML = '$' + (it.price*it.qty).toFixed(2) + ' <button onclick="dec('+idx+')" class="small">-</button> <button onclick="inc('+idx+')" class="small">+</button> <button onclick="rem('+idx+')" class="small danger">x</button>';
          row.appendChild(left); row.appendChild(right);
          el.appendChild(row);
          total += it.price*it.qty;
        });
        document.getElementById('total').innerText = '$' + total.toFixed(2);
        document.getElementById('change').innerText = '$0.00';
      }
      function inc(i){ items[i].qty++; renderSale(); }
      function dec(i){ items[i].qty = Math.max(1, items[i].qty-1); renderSale(); }
      function rem(i){ items.splice(i,1); renderSale(); }
      async function checkout(){
        if(items.length===0){ alert('No items'); return; }
        let payment = parseFloat(document.getElementById('payment').value) || 0;
        let resp = await fetch('/pos/checkout',{
          method:'POST',headers:{'Content-Type':'application/json'},
          body: JSON.stringify({items:items,payment:payment})
        });
        let data = await resp.json();
        if(!resp.ok){ document.getElementById('msg').innerText = data.error || 'Checkout failed'; return; }
        document.getElementById('msg').innerText = 'Sale recorded. Receipt ID: ' + data.sale_id;
        document.getElementById('change').innerText = '$' + Number(data.change).toFixed(2);
        items = [];
        renderSale();
      }
    </script>
    {% endblock %}
    ''', products=products)


@app.route('/pos/checkout', methods=['POST'])
def checkout():
    # Process checkout: verify stock, deduct, create sale and sale_items
    payload = request.get_json()
    items = payload.get('items', [])
    payment = float(payload.get('payment', 0))
    if not items:
        return jsonify({'error': 'No items'}), 400
    conn = db_connect()
    cur = conn.cursor()
    try:
        # Verify stock
        for it in items:
            cur.execute('SELECT qty,price,cost FROM products WHERE id=?', (it['id'],))
            row = cur.fetchone()
            if not row:
                raise Exception(f"Product {it['id']} not found")
            if row['qty'] < int(it['qty']):
                raise Exception(f"Insufficient stock for {it.get('name','')}")
        # Calculate totals
        total = 0.0
        for it in items:
            total += float(it['price']) * int(it['qty'])
        if payment < total:
            raise Exception('Payment insufficient')
        ts = datetime.now()
        cur.execute('INSERT INTO sales (timestamp,total,payment) VALUES (?,?,?)', (ts, total, payment))
        sale_id = cur.lastrowid
        # Insert sale items and deduct stock
        for it in items:
            pid = it['id']
            qty = int(it['qty'])
            cur.execute('SELECT price,cost FROM products WHERE id=?', (pid,))
            row = cur.fetchone()
            price = float(row['price'])
            cost = float(row['cost'])
            line_total = price * qty
            cur.execute('INSERT INTO sale_items (sale_id,product_id,name,qty,price,cost,line_total) VALUES (?,?,?,?,?,?,?)',
                        (sale_id, pid, it.get('name',''), qty, price, cost, line_total))
            cur.execute('UPDATE products SET qty = qty - ? WHERE id = ?', (qty, pid))
        conn.commit()
        change = payment - total
        return jsonify({'sale_id': sale_id, 'change': round(change,2)})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()


@app.route('/report')
def report():
    # Daily report for selected date (default today)
    qdate = request.args.get('d')
    if qdate:
        try:
            day = datetime.strptime(qdate, '%Y-%m-%d').date()
        except:
            day = date.today()
    else:
        day = date.today()
    start = datetime(day.year, day.month, day.day, 0, 0, 0)
    end = datetime(day.year, day.month, day.day, 23, 59, 59)
    conn = db_connect()
    cur = conn.cursor()
    # Total revenue and gross profit (revenue - cost)
    cur.execute('SELECT SUM(total) as revenue FROM sales WHERE timestamp BETWEEN ? AND ?', (start, end))
    revenue = cur.fetchone()['revenue'] or 0.0
    cur.execute('SELECT SUM(si.line_total) as rev, SUM(si.qty * si.cost) as cost_sum FROM sale_items si JOIN sales s ON si.sale_id=s.id WHERE s.timestamp BETWEEN ? AND ?', (start, end))
    row = cur.fetchone()
    gross_profit = (row['rev'] or 0.0) - (row['cost_sum'] or 0.0)
    # Top-selling items
    cur.execute('''
    SELECT si.name, SUM(si.qty) as qty, SUM(si.line_total) as revenue
    FROM sale_items si JOIN sales s ON si.sale_id=s.id
    WHERE s.timestamp BETWEEN ? AND ?
    GROUP BY si.name ORDER BY qty DESC LIMIT 10
    ''', (start, end))
    tops = cur.fetchall()
    # Sales log
    cur.execute('SELECT * FROM sales WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp', (start, end))
    sales = cur.fetchall()
    # For each sale get items
    sales_log = []
    for s in sales:
        cur.execute('SELECT name,qty,line_total FROM sale_items WHERE sale_id=?', (s['id'],))
        items = cur.fetchall()
        sales_log.append({'id': s['id'], 'timestamp': s['timestamp'], 'total': s['total'], 'payment': s['payment'], 'items': items})
    conn.close()
    return render_template_string(BASE_HTML + '''
    {% block content %}
    <h2>Daily Report</h2>
    <form method="get" action="/report">
      <label>Select date: <input type="date" name="d" value="{{day.isoformat()}}"></label>
      <button class="small" type="submit">View</button>
    </form>
    <div class="card">
      <div><strong>Revenue:</strong> ${{"{:.2f}".format(revenue)}}</div>
      <div><strong>Gross profit:</strong> ${{"{:.2f}".format(gross_profit)}}</div>
    </div>
    <div class="card">
      <h4>Top-selling items</h4>
      <table><thead><tr><th>Item</th><th>Qty</th><th>Revenue</th></tr></thead>
        <tbody>
        {% for t in tops %}
          <tr><td>{{t['name']}}</td><td>{{t['qty']}}</td><td>${{"{:.2f}".format(t['revenue'])}}</td></tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
    <div class="card">
      <h4>Sales log</h4>
      {% for s in sales_log %}
        <div style="margin-bottom:8px">
          <div><strong>#{{s['id']}}</strong> at {{s['timestamp']}} — ${{"{:.2f}".format(s['total'])}}</div>
          <div class="muted">
            {% for it in s['items'] %}
              {{it['name']}} x {{it['qty']}} ( ${{"{:.2f}".format(it['line_total'])}} )<br>
            {% endfor %}
          </div>
        </div>
      {% endfor %}
    </div>
    {% endblock %}
    ''', day=day, revenue=revenue, gross_profit=gross_profit, tops=tops, sales_log=sales_log)


if __name__ == '__main__':
    # Run the app
    app.run(host='0.0.0.0', port=5000, debug=True)
