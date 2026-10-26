"""
Flask Web Application Entry Point
E-Commerce Dispatch and Inventory Management Capstone
Features:
    - Session-based user authentication and cart stack management
    - CSRF protection on all POST forms
    - Request-scoped database connections (PRAGMA foreign_keys = ON)
    - Full integration with shared StoreService, DSA modules, and SQLite
"""

import os
import secrets
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, abort, g, jsonify
)

import database
from store import StoreService
from data_structures import CreateStack

app = Flask(__name__)

# Security & Session Configuration
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "capstone-secret-dev-key-change-in-prod-xyz123")
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['DATABASE_PATH'] = os.getenv("DATABASE_PATH", database.DEFAULT_DB_PATH)

# Central Store Service
store = StoreService(db_path=app.config['DATABASE_PATH'])


# -----------------------------------------------------------------------------
# Database Request Lifecycle & Connection Management
# -----------------------------------------------------------------------------
@app.before_request
def before_request():
    """Opens a request-scoped SQLite connection with Foreign Keys strictly enabled."""
    g.db = database.get_db_connection(app.config['DATABASE_PATH'])
    
    # Initialize CSRF token in session if not present
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(24)

    # Initialize cart list in session if not present
    if 'cart' not in session:
        session['cart'] = []

    # CSRF Verification on all POST requests
    if request.method == 'POST':
        submitted_token = request.form.get('csrf_token')
        expected_token = session.get('csrf_token')
        if not submitted_token or submitted_token != expected_token:
            abort(400, description="Invalid or missing CSRF token. Please refresh and try again.")


@app.teardown_appcontext
def teardown_db(exception=None):
    """Safely closes the request-scoped database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


@app.context_processor
def inject_global_template_vars():
    """Injects active cart count and user role across all templates."""
    cart = session.get('cart', [])
    cart_count = sum(item.get('quantity', 0) for item in cart)
    return {
        'cart_count': cart_count,
        'current_user_name': session.get('user_name'),
        'current_user_role': session.get('user_role')
    }


# -----------------------------------------------------------------------------
# Authorization Decorators
# -----------------------------------------------------------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash("Staff sign in required.", "warning")
            return redirect(url_for('login', next=request.url))
        if session.get('user_role') != 'admin':
            abort(403, description="Access Restricted: This section requires warehouse staff privileges.")
        return f(*args, **kwargs)
    return decorated_function


# Helper: Hydrate CreateStack from session cart list
def get_cart_stack() -> CreateStack:
    cart_stack = CreateStack()
    for item in session.get('cart', []):
        cart_stack.push(item)
    return cart_stack


def save_cart_stack(cart_stack: CreateStack):
    session['cart'] = cart_stack.get_items()
    session.modified = True


# -----------------------------------------------------------------------------
# Customer Storefront Routes
# -----------------------------------------------------------------------------
@app.route('/')
def catalogue():
    """Product Catalogue with Name Search, ID Lookup, and Merge Sort."""
    name_query = request.args.get('name', '').strip()
    id_str = request.args.get('id', '').strip()
    sort_by = request.args.get('sort', '').strip()
    in_stock = (request.args.get('in_stock') == '1')

    id_query = None
    if id_str.isdigit():
        id_query = int(id_str)

    products = store.search_products(
        name_query=name_query,
        id_query=id_query,
        sort_by=sort_by,
        in_stock_only=in_stock,
        conn=g.db
    )

    return render_template(
        'catalogue.html',
        products=products,
        name_query=name_query,
        id_query=id_str,
        sort_by=sort_by,
        in_stock=in_stock
    )


@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """Detailed Product View with stock indicators and cart addition form."""
    product = store.get_product_by_id(product_id, conn=g.db)
    if not product:
        abort(404, description=f"Product #{product_id} not found in catalog.")

    cart_stack = get_cart_stack()
    current_in_cart = sum(item['quantity'] for item in cart_stack.item if item['id'] == product_id)

    return render_template(
        'product_detail.html',
        product=product,
        current_in_cart=current_in_cart
    )


# -----------------------------------------------------------------------------
# Cart Routes (Stack LIFO)
# -----------------------------------------------------------------------------
@app.route('/cart')
def view_cart():
    """Displays cart items in reverse chronological order (Stack Top first)."""
    cart_stack = get_cart_stack()
    # Reversed so stack top appears first
    cart_items = list(reversed(cart_stack.get_items()))
    total_price = cart_stack.get_total_price()

    return render_template(
        'cart.html',
        cart_items=cart_items,
        total_price=total_price
    )


@app.route('/cart/add', methods=['POST'])
def add_to_cart():
    """Validates cumulative inventory limits and pushes item onto cart stack."""
    try:
        product_id = int(request.form.get('product_id', 0))
        quantity = int(request.form.get('quantity', 0))
    except (ValueError, TypeError):
        flash("Invalid product or quantity input.", "error")
        return redirect(url_for('catalogue'))

    cart_stack = get_cart_stack()
    success, msg = store.add_to_cart(cart_stack, product_id, quantity, conn=g.db)

    if success:
        save_cart_stack(cart_stack)
        flash(msg, "success")
        return redirect(url_for('view_cart'))
    else:
        flash(msg, "error")
        return redirect(url_for('product_detail', product_id=product_id))


@app.route('/cart/undo', methods=['POST'])
def undo_cart():
    """Pops the most recently added item from the Cart Stack (LIFO Undo)."""
    cart_stack = get_cart_stack()
    success, msg, popped = store.undo_cart(cart_stack)

    if success:
        save_cart_stack(cart_stack)
        flash(msg, "success")
    else:
        flash(msg, "warning")

    return redirect(url_for('view_cart'))


@app.route('/cart/clear', methods=['POST'])
def clear_cart():
    """Clears all items from the active cart stack."""
    session['cart'] = []
    session.modified = True
    flash("Cart cleared.", "success")
    return redirect(url_for('view_cart'))


# -----------------------------------------------------------------------------
# Checkout & Order Placement
# -----------------------------------------------------------------------------
@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """
    Submits cart order to SQLite in an ACID transaction:
        - Re-validates live stock
        - Creates parent order and order item records
        - Enqueues into warehouse FIFO queue
    """
    cart_stack = get_cart_stack()
    if cart_stack.is_empty():
        flash("Your cart is empty. Please select products first.", "warning")
        return redirect(url_for('catalogue'))

    if request.method == 'GET':
        cart_items = list(reversed(cart_stack.get_items()))
        total_price = cart_stack.get_total_price()
        return render_template('checkout.html', cart_items=cart_items, total_price=total_price)

    # POST: Execute Transactional Checkout
    customer_id = session.get('user_id')
    success, msg, order_id = store.checkout(cart_stack, customer_id, conn=g.db)

    if success:
        session['cart'] = []
        session.modified = True
        flash(f"{msg} Your order is in the warehouse dispatch line.", "success")
        return redirect(url_for('order_detail', order_id=order_id))
    else:
        flash(msg, "error")
        return redirect(url_for('view_cart'))


# -----------------------------------------------------------------------------
# Customer Orders & OrderTracker Linked List Inspection
# -----------------------------------------------------------------------------
@app.route('/orders')
@login_required
def list_orders():
    """Lists orders placed by the currently authenticated customer."""
    customer_id = session.get('user_id')
    orders = store.get_customer_orders(customer_id, conn=g.db)
    return render_template('orders.html', orders=orders)


@app.route('/orders/<int:order_id>')
@login_required
def order_detail(order_id):
    """
    Displays full invoice and the OrderTracker Linked List visual progress bar.
    Non-admin customers can only view their own orders.
    """
    order, err = store.track_order(order_id, conn=g.db)
    if err or not order:
        abort(404, description=err or "Order not found.")

    # Restrict viewing to order owner or warehouse staff
    if session.get('user_role') != 'admin' and order['customer_id'] != session.get('user_id'):
        abort(403, description="Unauthorized: You do not have permission to view this order.")

    return render_template('order_detail.html', order=order)


@app.route('/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    """
    Cancels an order while in 'Placed' stage, restoring warehouse stock atomically.
    """
    is_admin = (session.get('user_role') == 'admin')
    customer_id = session.get('user_id')

    success, msg = store.cancel_order(
        order_id=order_id,
        customer_id=customer_id,
        is_admin=is_admin,
        conn=g.db
    )

    if success:
        flash(msg, "success")
    else:
        flash(msg, "error")

    return redirect(url_for('order_detail', order_id=order_id))


# -----------------------------------------------------------------------------
# Warehouse Operations (Staff Admin Only)
# -----------------------------------------------------------------------------
@app.route('/admin/queue')
@admin_required
def admin_queue():
    """Displays active FIFO warehouse queue with head order action card."""
    # Ensure in-memory queue is synchronized with SQLite
    store.sync_queue_from_db()
    queue_ids = store.dispatch_queue.to_list()

    queue_orders = []
    for oid in queue_ids:
        data, _ = store.track_order(oid, conn=g.db)
        if data:
            queue_orders.append(data)

    return render_template('admin_queue.html', queue_orders=queue_orders)


@app.route('/admin/queue/advance', methods=['POST'])
@admin_required
def advance_dispatch():
    """Advances front order to its next milestone stage via fair Round-Robin rotation."""
    success, msg, oid, new_status = store.advance_dispatch(conn=g.db)
    if success:
        flash(msg, "success")
    else:
        flash(msg, "warning")
    return redirect(url_for('admin_queue'))


@app.route('/admin/inventory')
@admin_required
def admin_inventory():
    """Displays live warehouse inventory stock levels and SQLite check constraint status."""
    products = store.get_all_products(conn=g.db)
    return render_template('admin_inventory.html', products=products)


# -----------------------------------------------------------------------------
# Authentication Routes
# -----------------------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Customer & Staff Sign In."""
    if request.method == 'GET':
        if session.get('user_id'):
            return redirect(url_for('catalogue'))
        return render_template('login.html')

    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    user, msg = store.authenticate_user(email, password, conn=g.db)
    if user:
        session['user_id'] = user['customer_id']
        session['user_name'] = user['name']
        session['user_email'] = user['email']
        session['user_role'] = user['role']
        flash(f"Welcome, {user['name']}!", "success")

        next_url = request.args.get('next')
        if next_url and next_url.startswith('/'):
            return redirect(next_url)
        if user['role'] == 'admin':
            return redirect(url_for('admin_queue'))
        return redirect(url_for('catalogue'))
    else:
        flash(msg, "error")
        return render_template('login.html'), 401


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Customer Registration."""
    if request.method == 'GET':
        if session.get('user_id'):
            return redirect(url_for('catalogue'))
        return render_template('register.html')

    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    success, msg, customer_id = store.register_customer(name, email, password, conn=g.db)
    if success:
        session['user_id'] = customer_id
        session['user_name'] = name
        session['user_email'] = email.lower()
        session['user_role'] = 'customer'
        flash("Registration successful. Welcome to the portal!", "success")
        return redirect(url_for('catalogue'))
    else:
        flash(msg, "error")
        return render_template('register.html'), 400


@app.route('/logout')
def logout():
    """Terminates session."""
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for('catalogue'))


# -----------------------------------------------------------------------------
# Informational & Health Routes
# -----------------------------------------------------------------------------
@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/terms')
def terms():
    return render_template('terms.html')


@app.route('/health')
def health():
    """Health endpoint returning database connectivity status."""
    try:
        health_status = database.check_db_health(g.db)
        status_code = 200 if health_status["healthy"] else 503
        return jsonify({
            "status": "healthy" if health_status["healthy"] else "degraded",
            "database": "connected",
            "integrity": health_status["integrity"],
            "foreign_keys_enabled": health_status["foreign_keys_enabled"]
        }), status_code
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500


# -----------------------------------------------------------------------------
# Error Handlers
# -----------------------------------------------------------------------------
@app.errorhandler(400)
def bad_request(e):
    return render_template('error.html', error_code=400, error_title="Bad Request", error_message=getattr(e, 'description', 'Invalid request.')), 400


@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', error_code=403, error_title="Forbidden", error_message=getattr(e, 'description', 'Access restricted.')), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error_code=404, error_title="Page Not Found", error_message=getattr(e, 'description', 'The requested resource was not found.')), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error_code=500, error_title="Server Error", error_message="An internal system error occurred. All operations have been rolled back safely."), 500


if __name__ == '__main__':
    # Initialize schema and seed data on startup
    with app.app_context():
        conn = database.get_db_connection(app.config['DATABASE_PATH'])
        database.init_schema(conn)
        database.apply_migrations(conn)
        database.seed_canonical_data(conn)
        conn.close()

    app.run(host='127.0.0.1', port=5000, debug=False)
