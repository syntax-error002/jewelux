import os
import math
import json
import uuid
from datetime import datetime
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, abort)
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import config


class Pagination:
    def __init__(self, items, page, per_page, total):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = max(1, math.ceil(total / per_page))
        self.has_prev = page > 1
        self.has_next = page < self.pages
        self.prev_num = page - 1
        self.next_num = page + 1
    def iter_pages(self, left_edge=1, right_edge=1, left_current=2, right_current=2):
        last = 0
        for num in range(1, self.pages + 1):
            if (num <= left_edge or
                (self.page - left_current - 1 < num < self.page + right_current) or
                num > self.pages - right_edge):
                if last + 1 != num:
                    yield None
                yield num
                last = num

app = Flask(__name__)
app.config.from_object(config['development'])
app.config['MYSQL_PASSWORD']='Rishi@2207'
# ── Hardcoded DB credentials (edit here if your password changes) ──
app.config['MYSQL_PASSWORD'] = 'Rishi@2207'
# ──────────────────────────────────────────────────────────────────
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

mysql = MySQL(app)

# ─── Helpers ────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return ('.' in filename and
            filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS'])

def save_image(file):
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return filename
    return None

def get_cart_count():
    if 'user_id' not in session:
        return 0
    cur = mysql.connection.cursor()
    cur.execute("SELECT COALESCE(SUM(quantity),0) as cnt FROM cart WHERE user_id=%s", (session['user_id'],))
    row = cur.fetchone()
    cur.close()
    return int(row['cnt']) if row else 0

def get_wishlist_ids():
    if 'user_id' not in session:
        return []
    cur = mysql.connection.cursor()
    cur.execute("SELECT product_id FROM wishlist WHERE user_id=%s", (session['user_id'],))
    rows = cur.fetchall()
    cur.close()
    return [r['product_id'] for r in rows]

def generate_order_number():
    return f"JWL{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"

def format_inr(amount):
    return f"₹{amount:,.2f}"

app.jinja_env.globals.update(get_cart_count=get_cart_count, format_inr=format_inr)

# ─── Auth decorators ─────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            abort(403)
        return f(*args, **kwargs)
    return decorated

# ─── Context processor ───────────────────────────────────────────────────────

@app.template_global()
def img_url(path):
    """Return full image URL — handles both external (Unsplash) and local uploads."""
    if not path:
        return ''
    if path.startswith('http://') or path.startswith('https://'):
        return path
    return url_for('static', filename=f'uploads/products/{path}')

@app.context_processor
def inject_globals():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories ORDER BY name")
    categories = cur.fetchall()
    cur.close()
    return dict(categories=categories, current_year=datetime.now().year)

# ─── Error Handlers ──────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

@app.errorhandler(500)
def server_error(e):
    return render_template('errors/500.html'), 500

# ═══════════════════════════════════════════════════════════════════════════════
#  PUBLIC ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.*, c.name as category_name,
               (SELECT image_path FROM product_images WHERE product_id=p.id AND is_primary=1 LIMIT 1) as image
        FROM products p LEFT JOIN categories c ON p.category_id=c.id
        WHERE p.is_featured=1 AND p.is_active=1
        ORDER BY p.created_at DESC LIMIT 8
    """)
    featured = cur.fetchall()
    cur.execute("SELECT * FROM categories ORDER BY name")
    categories = cur.fetchall()
    cur.execute("""
        SELECT p.*, c.name as category_name,
               (SELECT image_path FROM product_images WHERE product_id=p.id AND is_primary=1 LIMIT 1) as image
        FROM products p LEFT JOIN categories c ON p.category_id=c.id
        WHERE p.is_active=1 ORDER BY p.created_at DESC LIMIT 4
    """)
    new_arrivals = cur.fetchall()
    cur.close()
    return render_template('index.html', featured=featured,
                           categories=categories, new_arrivals=new_arrivals)

# ─── Shop ─────────────────────────────────────────────────────────────────────

@app.route('/shop')
def shop():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    min_price = request.args.get('min_price', '', type=str)
    max_price = request.args.get('max_price', '', type=str)
    sort = request.args.get('sort', 'newest')
    per_page = app.config['PRODUCTS_PER_PAGE']

    where = ["p.is_active=1"]
    params = []

    if category:
        where.append("c.slug=%s")
        params.append(category)
    if min_price:
        where.append("COALESCE(p.sale_price, p.price) >= %s")
        params.append(float(min_price))
    if max_price:
        where.append("COALESCE(p.sale_price, p.price) <= %s")
        params.append(float(max_price))

    where_clause = " AND ".join(where)

    sort_map = {
        'newest': 'p.created_at DESC',
        'oldest': 'p.created_at ASC',
        'price_asc': 'COALESCE(p.sale_price, p.price) ASC',
        'price_desc': 'COALESCE(p.sale_price, p.price) DESC',
        'name': 'p.name ASC'
    }
    order_by = sort_map.get(sort, 'p.created_at DESC')

    base_query = f"""
        FROM products p
        LEFT JOIN categories c ON p.category_id=c.id
        WHERE {where_clause}
    """

    cur = mysql.connection.cursor()
    cur.execute(f"SELECT COUNT(*) as total {base_query}", params)
    total = cur.fetchone()['total']
    total_pages = math.ceil(total / per_page)
    offset = (page - 1) * per_page

    cur.execute(f"""
        SELECT p.*, c.name as category_name, c.slug as category_slug,
               (SELECT image_path FROM product_images WHERE product_id=p.id AND is_primary=1 LIMIT 1) as image
        {base_query}
        ORDER BY {order_by}
        LIMIT %s OFFSET %s
    """, params + [per_page, offset])
    products = cur.fetchall()
    cur.close()

    wishlist_ids = get_wishlist_ids()
    return render_template('shop.html', products=products,
                           total=total, page=page, total_pages=total_pages,
                           category=category, min_price=min_price,
                           max_price=max_price, sort=sort,
                           wishlist_ids=wishlist_ids)

# ─── AJAX live search ─────────────────────────────────────────────────────────

@app.route('/search')
def search():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.id, p.name, p.slug, p.price, p.sale_price, c.name as category,
               (SELECT image_path FROM product_images WHERE product_id=p.id AND is_primary=1 LIMIT 1) as image
        FROM products p LEFT JOIN categories c ON p.category_id=c.id
        WHERE p.is_active=1 AND (p.name LIKE %s OR p.description LIKE %s OR c.name LIKE %s)
        LIMIT 8
    """, (f'%{q}%', f'%{q}%', f'%{q}%'))
    results = cur.fetchall()
    cur.close()
    data = []
    for r in results:
        data.append({
            'id': r['id'],
            'name': r['name'],
            'slug': r['slug'],
            'price': float(r['sale_price'] or r['price']),
            'original_price': float(r['price']),
            'category': r['category'],
            'image': r['image'] or 'placeholder.jpg',
            'url': url_for('product_detail', slug=r['slug'])
        })
    return jsonify(data)

# ─── Product detail ───────────────────────────────────────────────────────────

@app.route('/product/<slug>')
def product_detail(slug):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.*, c.name as category_name, c.slug as category_slug
        FROM products p LEFT JOIN categories c ON p.category_id=c.id
        WHERE p.slug=%s AND p.is_active=1
    """, (slug,))
    product = cur.fetchone()
    if not product:
        abort(404)

    cur.execute("SELECT * FROM product_images WHERE product_id=%s ORDER BY sort_order", (product['id'],))
    images = cur.fetchall()

    cur.execute("""
        SELECT p.*, c.name as category_name,
               (SELECT image_path FROM product_images WHERE product_id=p.id AND is_primary=1 LIMIT 1) as image
        FROM products p LEFT JOIN categories c ON p.category_id=c.id
        WHERE p.category_id=%s AND p.id!=%s AND p.is_active=1
        ORDER BY RAND() LIMIT 4
    """, (product['category_id'], product['id']))
    related = cur.fetchall()
    cur.close()

    wishlist_ids = get_wishlist_ids()
    in_wishlist = product['id'] in wishlist_ids
    return render_template('product.html', product=product, images=images,
                           related=related, in_wishlist=in_wishlist)

# ═══════════════════════════════════════════════════════════════════════════════
#  CART ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/cart')
@login_required
def cart():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.id, c.quantity, p.id as product_id, p.name, p.slug,
               p.price, p.sale_price, p.stock,
               (SELECT image_path FROM product_images WHERE product_id=p.id AND is_primary=1 LIMIT 1) as image
        FROM cart c JOIN products p ON c.product_id=p.id
        WHERE c.user_id=%s
    """, (session['user_id'],))
    items = cur.fetchall()
    cur.close()

    subtotal = sum((i['sale_price'] or i['price']) * i['quantity'] for i in items)
    shipping = 0 if subtotal >= 10000 else 499
    total = subtotal + shipping
    return render_template('cart.html', items=items, subtotal=subtotal,
                           shipping=shipping, total=total)

@app.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    data = request.get_json()
    product_id = data.get('product_id')
    quantity = int(data.get('quantity', 1))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, stock FROM products WHERE id=%s AND is_active=1", (product_id,))
    product = cur.fetchone()
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404

    cur.execute("SELECT id, quantity FROM cart WHERE user_id=%s AND product_id=%s",
                (session['user_id'], product_id))
    existing = cur.fetchone()

    if existing:
        new_qty = existing['quantity'] + quantity
        if new_qty > product['stock']:
            return jsonify({'success': False, 'message': 'Not enough stock'}), 400
        cur.execute("UPDATE cart SET quantity=%s WHERE id=%s", (new_qty, existing['id']))
    else:
        if quantity > product['stock']:
            return jsonify({'success': False, 'message': 'Not enough stock'}), 400
        cur.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (%s,%s,%s)",
                    (session['user_id'], product_id, quantity))

    mysql.connection.commit()
    cur.execute("SELECT COALESCE(SUM(quantity),0) as cnt FROM cart WHERE user_id=%s", (session['user_id'],))
    count = int(cur.fetchone()['cnt'])
    cur.close()
    return jsonify({'success': True, 'cart_count': count, 'message': 'Added to cart!'})

@app.route('/cart/update', methods=['POST'])
@login_required
def update_cart():
    data = request.get_json()
    cart_id = data.get('cart_id')
    quantity = int(data.get('quantity', 1))

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.id, p.stock, p.price, p.sale_price
        FROM cart c JOIN products p ON c.product_id=p.id
        WHERE c.id=%s AND c.user_id=%s
    """, (cart_id, session['user_id']))
    item = cur.fetchone()

    if not item:
        return jsonify({'success': False}), 404
    if quantity > item['stock']:
        return jsonify({'success': False, 'message': 'Not enough stock'}), 400
    if quantity < 1:
        return jsonify({'success': False, 'message': 'Minimum quantity is 1'}), 400

    cur.execute("UPDATE cart SET quantity=%s WHERE id=%s", (quantity, cart_id))
    mysql.connection.commit()

    unit_price = float(item['sale_price'] or item['price'])
    item_total = unit_price * quantity

    cur.execute("""
        SELECT COALESCE(SUM(COALESCE(p.sale_price,p.price)*c.quantity),0) as subtotal
        FROM cart c JOIN products p ON c.product_id=p.id WHERE c.user_id=%s
    """, (session['user_id'],))
    subtotal = float(cur.fetchone()['subtotal'])
    shipping = 0 if subtotal >= 10000 else 499
    cur.execute("SELECT COALESCE(SUM(quantity),0) as cnt FROM cart WHERE user_id=%s", (session['user_id'],))
    count = int(cur.fetchone()['cnt'])
    cur.close()

    return jsonify({
        'success': True,
        'item_total': item_total,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': subtotal + shipping,
        'cart_count': count
    })

@app.route('/cart/remove', methods=['POST'])
@login_required
def remove_from_cart():
    data = request.get_json()
    cart_id = data.get('cart_id')

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM cart WHERE id=%s AND user_id=%s", (cart_id, session['user_id']))
    mysql.connection.commit()

    cur.execute("""
        SELECT COALESCE(SUM(COALESCE(p.sale_price,p.price)*c.quantity),0) as subtotal
        FROM cart c JOIN products p ON c.product_id=p.id WHERE c.user_id=%s
    """, (session['user_id'],))
    subtotal = float(cur.fetchone()['subtotal'])
    shipping = 0 if subtotal >= 10000 else 499
    cur.execute("SELECT COALESCE(SUM(quantity),0) as cnt FROM cart WHERE user_id=%s", (session['user_id'],))
    count = int(cur.fetchone()['cnt'])
    cur.close()

    return jsonify({
        'success': True,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': subtotal + shipping,
        'cart_count': count
    })

# ─── Wishlist ─────────────────────────────────────────────────────────────────

@app.route('/wishlist/toggle', methods=['POST'])
@login_required
def toggle_wishlist():
    data = request.get_json()
    product_id = data.get('product_id')
    cur = mysql.connection.cursor()
    cur.execute("SELECT id FROM wishlist WHERE user_id=%s AND product_id=%s",
                (session['user_id'], product_id))
    existing = cur.fetchone()
    if existing:
        cur.execute("DELETE FROM wishlist WHERE id=%s", (existing['id'],))
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True, 'in_wishlist': False})
    else:
        cur.execute("INSERT INTO wishlist (user_id, product_id) VALUES (%s,%s)",
                    (session['user_id'], product_id))
        mysql.connection.commit()
        cur.close()
        return jsonify({'success': True, 'in_wishlist': True})

@app.route('/wishlist')
@login_required
def wishlist():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.*, c.name as category_name,
               (SELECT image_path FROM product_images WHERE product_id=p.id AND is_primary=1 LIMIT 1) as image
        FROM wishlist w JOIN products p ON w.product_id=p.id
        LEFT JOIN categories c ON p.category_id=c.id
        WHERE w.user_id=%s ORDER BY w.added_at DESC
    """, (session['user_id'],))
    items = cur.fetchall()
    cur.close()
    return render_template('wishlist.html', items=items)

# ─── Checkout ─────────────────────────────────────────────────────────────────

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.id, c.quantity, p.id as product_id, p.name, p.slug,
               p.price, p.sale_price, p.stock
        FROM cart c JOIN products p ON c.product_id=p.id
        WHERE c.user_id=%s
    """, (session['user_id'],))
    items = cur.fetchall()

    if not items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('cart'))

    subtotal = sum((i['sale_price'] or i['price']) * i['quantity'] for i in items)
    shipping = 0 if subtotal >= 10000 else 499
    total = subtotal + shipping

    cur.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
    user = cur.fetchone()

    if request.method == 'POST':
        order_number = generate_order_number()
        cur.execute("""
            INSERT INTO orders (user_id, order_number, total_amount,
                shipping_name, shipping_email, shipping_phone,
                shipping_address, shipping_city, shipping_country, payment_method, notes)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (session['user_id'], order_number, total,
              request.form['name'], request.form['email'],
              request.form.get('phone', ''),
              request.form['address'], request.form['city'],
              request.form.get('country', 'India'),
              request.form.get('payment', 'COD'),
              request.form.get('notes', '')))
        order_id = cur.lastrowid

        for item in items:
            price = float(item['sale_price'] or item['price'])
            cur.execute("""
                INSERT INTO order_items (order_id, product_id, product_name, product_price, quantity, subtotal)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (order_id, item['product_id'], item['name'], price,
                  item['quantity'], price * item['quantity']))
            cur.execute("UPDATE products SET stock=stock-%s WHERE id=%s",
                        (item['quantity'], item['product_id']))

        cur.execute("DELETE FROM cart WHERE user_id=%s", (session['user_id'],))
        mysql.connection.commit()
        cur.close()
        flash(f'Order placed successfully! Order #{order_number}', 'success')
        return redirect(url_for('order_success', order_number=order_number))

    cur.close()
    return render_template('checkout.html', items=items, user=user,
                           subtotal=subtotal, shipping=shipping, total=total)

@app.route('/order/success/<order_number>')
@login_required
def order_success(order_number):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM orders WHERE order_number=%s AND user_id=%s",
                (order_number, session['user_id']))
    order = cur.fetchone()
    cur.close()
    if not order:
        abort(404)
    return render_template('order_success.html', order=order)

# ═══════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['full_name']
            session['is_admin'] = bool(user['is_admin'])
            flash(f"Welcome back, {user['full_name'].split()[0]}!", 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('index'))
        flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        confirm = request.form['confirm_password']

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'danger')
            return render_template('auth/register.html')

        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            flash('Email already registered.', 'danger')
            cur.close()
            return render_template('auth/register.html')

        pw_hash = generate_password_hash(password)
        cur.execute("INSERT INTO users (full_name, email, password_hash) VALUES (%s,%s,%s)",
                    (full_name, email, pw_hash))
        mysql.connection.commit()
        user_id = cur.lastrowid
        cur.close()

        session['user_id'] = user_id
        session['user_name'] = full_name
        session['is_admin'] = False
        flash('Account created successfully! Welcome to JEWELUX.', 'success')
        return redirect(url_for('index'))
    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# ═══════════════════════════════════════════════════════════════════════════════
#  USER DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/dashboard')
@login_required
def dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
    user = cur.fetchone()
    cur.execute("""
        SELECT o.*, COUNT(oi.id) as item_count
        FROM orders o LEFT JOIN order_items oi ON o.id=oi.order_id
        WHERE o.user_id=%s GROUP BY o.id ORDER BY o.created_at DESC LIMIT 5
    """, (session['user_id'],))
    recent_orders = cur.fetchall()
    cur.execute("SELECT COUNT(*) as cnt FROM orders WHERE user_id=%s", (session['user_id'],))
    order_count = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM wishlist WHERE user_id=%s", (session['user_id'],))
    wishlist_count = cur.fetchone()['cnt']
    cur.close()
    return render_template('dashboard/index.html', user=user,
                           recent_orders=recent_orders,
                           order_count=order_count, wishlist_count=wishlist_count)

@app.route('/dashboard/orders')
@login_required
def my_orders():
    page = request.args.get('page', 1, type=int)
    per_page = app.config['ORDERS_PER_PAGE']
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) as total FROM orders WHERE user_id=%s", (session['user_id'],))
    total = cur.fetchone()['total']
    total_pages = math.ceil(total / per_page)
    offset = (page - 1) * per_page
    cur.execute("""
        SELECT o.*, COUNT(oi.id) as item_count
        FROM orders o LEFT JOIN order_items oi ON o.id=oi.order_id
        WHERE o.user_id=%s GROUP BY o.id ORDER BY o.created_at DESC
        LIMIT %s OFFSET %s
    """, (session['user_id'], per_page, offset))
    orders = cur.fetchall()
    cur.close()
    return render_template('dashboard/orders.html', orders=orders,
                           page=page, total_pages=total_pages)

@app.route('/dashboard/order/<int:order_id>')
@login_required
def order_detail(order_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM orders WHERE id=%s AND user_id=%s", (order_id, session['user_id']))
    order = cur.fetchone()
    if not order:
        abort(404)
    cur.execute("SELECT * FROM order_items WHERE order_id=%s", (order_id,))
    items = cur.fetchall()
    cur.close()
    return render_template('dashboard/order_detail.html', order=order, items=items)

@app.route('/dashboard/profile', methods=['GET', 'POST'])
@login_required
def profile():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
    user = cur.fetchone()
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        city = request.form.get('city', '').strip()
        country = request.form.get('country', 'India').strip()
        cur.execute("""
            UPDATE users SET full_name=%s, phone=%s, address=%s, city=%s, country=%s
            WHERE id=%s
        """, (full_name, phone, address, city, country, session['user_id']))

        if request.form.get('new_password'):
            if not check_password_hash(user['password_hash'], request.form['current_password']):
                flash('Current password is incorrect.', 'danger')
                cur.close()
                return render_template('dashboard/profile.html', user=user)
            new_pw = request.form['new_password']
            if len(new_pw) < 8:
                flash('New password must be at least 8 characters.', 'danger')
                cur.close()
                return render_template('dashboard/profile.html', user=user)
            cur.execute("UPDATE users SET password_hash=%s WHERE id=%s",
                        (generate_password_hash(new_pw), session['user_id']))

        mysql.connection.commit()
        session['user_name'] = full_name
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    cur.close()
    return render_template('dashboard/profile.html', user=user)

# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN PANEL
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/admin')
@admin_required
def admin_index():
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) as cnt FROM products")
    product_count = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM orders")
    order_count = cur.fetchone()['cnt']
    cur.execute("SELECT COUNT(*) as cnt FROM users")
    user_count = cur.fetchone()['cnt']
    cur.execute("SELECT COALESCE(SUM(total_amount),0) as rev FROM orders WHERE status!='cancelled'")
    revenue = cur.fetchone()['rev']
    cur.execute("""
        SELECT o.*, u.full_name, u.email FROM orders o
        JOIN users u ON o.user_id=u.id
        ORDER BY o.created_at DESC LIMIT 10
    """)
    recent_orders = cur.fetchall()
    cur.execute("""
        SELECT status, COUNT(*) as cnt FROM orders GROUP BY status
    """)
    order_stats = {r['status']: r['cnt'] for r in cur.fetchall()}
    cur.execute("SELECT id, name, stock FROM products WHERE stock <= 5 ORDER BY stock ASC LIMIT 10")
    low_stock = cur.fetchall()
    for o in recent_orders:
        o['customer_name'] = o.get('full_name') or 'Unknown'
        o['customer_email'] = o.get('email', '')
        o['item_count'] = 1
    cur.close()
    stats = {'revenue': revenue, 'orders': order_count, 'products': product_count, 'customers': user_count}
    return render_template('admin/index.html', stats=stats, recent_orders=recent_orders,
                           low_stock=low_stock, order_stats=order_stats)

# Products CRUD
@app.route('/admin/products')
@admin_required
def admin_products():
    page = request.args.get('page', 1, type=int)
    per_page = 15
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) as total FROM products")
    total = cur.fetchone()['total']
    total_pages = math.ceil(total / per_page)
    offset = (page - 1) * per_page
    cur.execute("""
        SELECT p.*, c.name as category_name,
               (SELECT image_path FROM product_images WHERE product_id=p.id AND is_primary=1 LIMIT 1) as image
        FROM products p LEFT JOIN categories c ON p.category_id=c.id
        ORDER BY p.created_at DESC LIMIT %s OFFSET %s
    """, (per_page, offset))
    items = cur.fetchall()
    products = Pagination(items, page, per_page, total)
    cur.execute("SELECT * FROM categories ORDER BY name")
    categories = cur.fetchall()
    cur.close()
    return render_template('admin/products.html', products=products, categories=categories)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories ORDER BY name")
    categories = cur.fetchall()
    if request.method == 'POST':
        name = request.form['name'].strip()
        slug = name.lower().replace(' ', '-').replace("'", '')
        slug = ''.join(c if c.isalnum() or c == '-' else '' for c in slug)
        description = request.form.get('description', '')
        price = float(request.form['price'])
        sale_price = request.form.get('sale_price') or None
        stock = int(request.form.get('stock', 0))
        category_id = request.form.get('category_id') or None
        material = request.form.get('material', '')
        weight = request.form.get('weight', '')
        is_featured = 1 if request.form.get('is_featured') else 0

        # Ensure unique slug
        base_slug = slug
        counter = 1
        while True:
            cur.execute("SELECT id FROM products WHERE slug=%s", (slug,))
            if not cur.fetchone():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        cur.execute("""
            INSERT INTO products (name, slug, description, price, sale_price, stock,
                category_id, material, weight, is_featured)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (name, slug, description, price, sale_price, stock,
              category_id, material, weight, is_featured))
        product_id = cur.lastrowid

        files = request.files.getlist('images')
        for i, file in enumerate(files):
            filename = save_image(file)
            if filename:
                is_primary = 1 if i == 0 else 0
                cur.execute("""
                    INSERT INTO product_images (product_id, image_path, is_primary, sort_order)
                    VALUES (%s,%s,%s,%s)
                """, (product_id, filename, is_primary, i))

        mysql.connection.commit()
        cur.close()
        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_products'))
    cur.close()
    return render_template('admin/product_form.html', categories=categories, product=None)

@app.route('/admin/products/edit/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products WHERE id=%s", (product_id,))
    product = cur.fetchone()
    if not product:
        abort(404)
    cur.execute("SELECT * FROM categories ORDER BY name")
    categories = cur.fetchall()
    cur.execute("SELECT * FROM product_images WHERE product_id=%s ORDER BY sort_order", (product_id,))
    images = cur.fetchall()

    if request.method == 'POST':
        name = request.form['name'].strip()
        description = request.form.get('description', '')
        price = float(request.form['price'])
        sale_price = request.form.get('sale_price') or None
        stock = int(request.form.get('stock', 0))
        category_id = request.form.get('category_id') or None
        material = request.form.get('material', '')
        weight = request.form.get('weight', '')
        is_featured = 1 if request.form.get('is_featured') else 0
        is_active = 1 if request.form.get('is_active') else 0

        cur.execute("""
            UPDATE products SET name=%s, description=%s, price=%s, sale_price=%s,
                stock=%s, category_id=%s, material=%s, weight=%s,
                is_featured=%s, is_active=%s
            WHERE id=%s
        """, (name, description, price, sale_price, stock, category_id,
              material, weight, is_featured, is_active, product_id))

        files = request.files.getlist('images')
        for i, file in enumerate(files):
            filename = save_image(file)
            if filename:
                has_primary = any(img['is_primary'] for img in images)
                is_primary = 1 if not has_primary and i == 0 else 0
                cur.execute("""
                    INSERT INTO product_images (product_id, image_path, is_primary, sort_order)
                    VALUES (%s,%s,%s,%s)
                """, (product_id, filename, is_primary, len(images) + i))

        mysql.connection.commit()
        flash('Product updated successfully!', 'success')
        return redirect(url_for('admin_products'))

    cur.close()
    return render_template('admin/product_form.html', categories=categories,
                           product=product, images=images)

@app.route('/admin/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM products WHERE id=%s", (product_id,))
    mysql.connection.commit()
    cur.close()
    flash('Product deleted.', 'info')
    return redirect(url_for('admin_products'))

@app.route('/admin/products/image/delete/<int:image_id>', methods=['POST'])
@admin_required
def admin_delete_image(image_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM product_images WHERE id=%s", (image_id,))
    img = cur.fetchone()
    if img:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], img['image_path'])
        if os.path.exists(file_path):
            os.remove(file_path)
        cur.execute("DELETE FROM product_images WHERE id=%s", (image_id,))
        mysql.connection.commit()
    cur.close()
    return jsonify({'success': True})

# Orders management
@app.route('/admin/orders')
@admin_required
def admin_orders():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', '')
    per_page = app.config['ORDERS_PER_PAGE']
    where = "1=1"
    params = []
    if status_filter:
        where = "o.status=%s"
        params.append(status_filter)
    cur = mysql.connection.cursor()
    cur.execute(f"SELECT COUNT(*) as total FROM orders o WHERE {where}", params)
    total = cur.fetchone()['total']
    total_pages = math.ceil(total / per_page)
    offset = (page - 1) * per_page
    cur.execute(f"""
        SELECT o.*, u.full_name, u.email,
               (SELECT COUNT(*) FROM order_items WHERE order_id=o.id) as item_count
        FROM orders o
        JOIN users u ON o.user_id=u.id
        WHERE {where} ORDER BY o.created_at DESC LIMIT %s OFFSET %s
    """, params + [per_page, offset])
    rows = cur.fetchall()
    for o in rows:
        o["customer_name"] = o.get("full_name") or "Unknown"
        o["customer_email"] = o.get("email", "")
    cur.close()
    orders = Pagination(rows, page, per_page, total)
    return render_template("admin/orders.html", orders=orders, status_filter=status_filter)

@app.route('/admin/orders/<int:order_id>')
@admin_required
def admin_order_detail(order_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT o.*, u.full_name, u.email, u.phone FROM orders o
        JOIN users u ON o.user_id=u.id WHERE o.id=%s
    """, (order_id,))
    order = cur.fetchone()
    if not order:
        abort(404)
    order["customer_name"] = order.get("full_name") or "Unknown"
    order["customer_email"] = order.get("email", "")
    cur.execute("""
        SELECT oi.*,
               (SELECT image_path FROM product_images WHERE product_id=oi.product_id AND is_primary=1 LIMIT 1) as image
        FROM order_items oi WHERE oi.order_id=%s
    """, (order_id,))
    items = cur.fetchall()
    cur.close()
    return render_template("admin/order_detail.html", order=order, items=items)

@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@admin_required
def admin_update_order_status(order_id):
    status = request.form.get('status')
    valid = ['pending','confirmed','processing','shipped','delivered','cancelled']
    if status not in valid:
        return jsonify({'success': False}), 400
    cur = mysql.connection.cursor()
    cur.execute("UPDATE orders SET status=%s WHERE id=%s", (status, order_id))
    mysql.connection.commit()
    cur.close()
    flash('Order status updated.', 'success')
    return redirect(url_for('admin_order_detail', order_id=order_id))

# Users management
@app.route('/admin/users')
@admin_required
def admin_users():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) as total FROM users")
    total = cur.fetchone()['total']
    total_pages = math.ceil(total / per_page)
    offset = (page - 1) * per_page
    # search/filter
    q = request.args.get('q', '')
    role = request.args.get('role', '')
    where = 'WHERE 1=1'
    params = []
    if q:
        where += ' AND (u.full_name LIKE %s OR u.email LIKE %s)'
        params += [f'%{q}%', f'%{q}%']
    if role == 'admin':
        where += ' AND u.is_admin=1'
    elif role == 'user':
        where += ' AND u.is_admin=0'
    cur.execute(f'SELECT COUNT(*) as total FROM users u {where}', params)
    total = cur.fetchone()['total']
    total_pages = math.ceil(total / per_page) if total else 1
    offset = (page - 1) * per_page
    cur.execute(f"""
        SELECT u.*, COUNT(o.id) as order_count FROM users u
        LEFT JOIN orders o ON u.id=o.user_id
        {where} GROUP BY u.id ORDER BY u.created_at DESC LIMIT %s OFFSET %s
    """, params + [per_page, offset])
    users_list = cur.fetchall()
    # map full_name -> name for template
    for u in users_list:
        u["name"] = u.get("full_name") or u.get("name") or "Unknown"
    cur.close()
    users = Pagination(users_list, page, per_page, total)
    return render_template("admin/users.html", users=users)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
