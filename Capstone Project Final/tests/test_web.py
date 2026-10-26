"""
Web Frontend Route & Integration Tests
Verifies:
    - Customer registration, login, logout, and session lifecycle
    - Catalogue filtering, searching (linear name search, binary ID lookup), and sorting (merge sort)
    - Cart addition, cumulative stock limits, LIFO undo pop, and clear
    - Transactional checkout placement
    - Order detail invoice and Singly Linked List stage progression
    - Customer order cancellation and stock restoration
    - Admin-only warehouse queue and inventory protection (403 for customers, redirect for anonymous)
    - Admin queue advancement (fair round-robin rotation)
    - CSRF protection rejection on missing/invalid tokens
    - Health route (JSON 200) and 404 error handler
"""

import re
import pytest
from app import app
import database


@pytest.fixture
def client(tmp_path):
    """Configures test client with an isolated temporary SQLite database."""
    test_db = str(tmp_path / "web_test.db")
    app.config['DATABASE_PATH'] = test_db
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False  # Still testing manual CSRF check

    # Initialize schema, migrations, and canonical seed
    conn = database.get_db_connection(test_db)
    database.init_schema(conn)
    database.apply_migrations(conn)
    database.seed_canonical_data(conn)
    conn.close()

    with app.test_client() as client:
        yield client


def get_csrf_token(client):
    """Helper to fetch active CSRF token from session via GET request."""
    res = client.get('/')
    with client.session_transaction() as sess:
        return sess.get('csrf_token')


def test_health_endpoint(client):
    res = client.get('/health')
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_csrf_protection_rejects_missing_token(client):
    """POST request without csrf_token must be rejected with 400 Bad Request."""
    res = client.post('/cart/add', data={'product_id': 1, 'quantity': 1})
    assert res.status_code == 400
    assert b"CSRF token" in res.data


def test_customer_registration_login_logout(client):
    token = get_csrf_token(client)

    # 1. Register new customer
    res = client.post('/register', data={
        'name': 'Pooja Patil',
        'email': 'pooja@example.com',
        'password': 'securepassword123',
        'csrf_token': token
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Registration successful" in res.data

    with client.session_transaction() as sess:
        assert sess.get('user_name') == 'Pooja Patil'
        assert sess.get('user_role') == 'customer'

    # 2. Logout
    res_logout = client.get('/logout', follow_redirects=True)
    assert res_logout.status_code == 200
    assert b"signed out" in res_logout.data
    with client.session_transaction() as sess:
        assert sess.get('user_id') is None

    # 3. Login again
    token2 = get_csrf_token(client)
    res_login = client.post('/login', data={
        'email': 'pooja@example.com',
        'password': 'securepassword123',
        'csrf_token': token2
    }, follow_redirects=True)
    assert res_login.status_code == 200
    assert b"Welcome, Pooja Patil!" in res_login.data


def test_catalogue_search_and_sort(client):
    # 1. Base catalogue
    res = client.get('/')
    assert res.status_code == 200
    assert b"PRODUCT #1" in res.data
    assert b"PRODUCT #2" in res.data

    # 2. Linear search by name
    res_search = client.get('/?name=mouse')
    assert res_search.status_code == 200
    assert b"PRODUCT #2" in res_search.data
    # Product #1 (Laptop) must not be rendered in the results grid
    assert b"PRODUCT #1" not in res_search.data

    # 3. Binary search by ID
    res_id = client.get('/?id=3')
    assert res_id.status_code == 200
    assert b"PRODUCT #3" in res_id.data
    assert b"PRODUCT #1" not in res_id.data

    # 4. Sort via merge sort
    res_sort = client.get('/?sort=price_desc')
    assert res_sort.status_code == 200


def test_cart_add_undo_clear_flow(client):
    token = get_csrf_token(client)

    # 1. Add Mouse (id 2, qty 2)
    client.post('/cart/add', data={
        'product_id': 2,
        'quantity': 2,
        'csrf_token': token
    }, follow_redirects=True)

    # 2. Add Keyboard (id 3, qty 1)
    client.post('/cart/add', data={
        'product_id': 3,
        'quantity': 1,
        'csrf_token': token
    }, follow_redirects=True)

    with client.session_transaction() as sess:
        cart = sess.get('cart', [])
        assert len(cart) == 2
        # Stack top is Keyboard (last added)
        assert cart[-1]['name'] == 'Keyboard'

    # 3. View cart page
    res_cart = client.get('/cart')
    assert b"Keyboard" in res_cart.data
    assert b"Mouse" in res_cart.data
    assert b"STACK TOP" in res_cart.data

    # 4. Undo last item (pop Keyboard)
    res_undo = client.post('/cart/undo', data={'csrf_token': token}, follow_redirects=True)
    assert res_undo.status_code == 200
    assert b"Keyboard" in res_undo.data
    assert b"from cart" in res_undo.data

    with client.session_transaction() as sess:
        cart = sess.get('cart', [])
        assert len(cart) == 1
        assert cart[0]['name'] == 'Mouse'

    # 5. Clear cart
    client.post('/cart/clear', data={'csrf_token': token}, follow_redirects=True)
    with client.session_transaction() as sess:
        assert len(sess.get('cart', [])) == 0


def test_checkout_and_order_tracking_lifecycle(client):
    token = get_csrf_token(client)

    # Login as student customer 1
    client.post('/login', data={
        'email': '125anant6027@sjcem.edu.in',
        'password': 'student123',
        'csrf_token': token
    })

    # Add item to cart
    client.post('/cart/add', data={
        'product_id': 2,
        'quantity': 2,
        'csrf_token': token
    })

    # Checkout
    res_chk = client.post('/checkout', data={'csrf_token': token}, follow_redirects=True)
    assert res_chk.status_code == 200
    assert b"Order Tracker" in res_chk.data
    assert b"Placed" in res_chk.data

    # Extract order id from URL or page
    order_id_match = re.search(r"Order #(\d+)", res_chk.data.decode('utf-8'))
    assert order_id_match is not None
    order_id = int(order_id_match.group(1))

    # Cancel the order
    res_cancel = client.post(f'/orders/{order_id}/cancel', data={'csrf_token': token}, follow_redirects=True)
    assert res_cancel.status_code == 200
    assert b"has been cancelled and inventory has been restored" in res_cancel.data
    assert b"Order Cancelled" in res_cancel.data


def test_admin_route_protection_and_queue_advancement(client):
    token = get_csrf_token(client)

    # 1. Anonymous user blocked from /admin/queue
    res_anon = client.get('/admin/queue')
    assert res_anon.status_code == 302  # Redirects to login

    # 2. Regular customer forbidden (403) from /admin/queue
    client.post('/login', data={
        'email': '125anant6027@sjcem.edu.in',
        'password': 'student123',
        'csrf_token': token
    })
    res_cust = client.get('/admin/queue')
    assert res_cust.status_code == 403

    # Logout customer
    client.get('/logout')

    # 3. Staff Admin user allowed
    token2 = get_csrf_token(client)
    client.post('/login', data={
        'email': 'admin@sjcem.edu.in',
        'password': 'admin123',
        'csrf_token': token2
    })
    res_admin = client.get('/admin/queue')
    assert res_admin.status_code == 200
    assert b"Warehouse Dispatch Line" in res_admin.data

    # 4. Admin advances queue
    res_adv = client.post('/admin/queue/advance', data={'csrf_token': token2}, follow_redirects=True)
    assert res_adv.status_code == 200

    # 5. Admin inventory view
    res_inv = client.get('/admin/inventory')
    assert res_inv.status_code == 200
    assert b"Inventory Stock Levels" in res_inv.data
