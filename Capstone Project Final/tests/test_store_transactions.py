"""
Integration and Transactional Tests for StoreService
Verifies:
    - Checkout transactional atomicity and stock decrement
    - Rollback upon injected failure
    - Cumulative cart limit validation (4 + 4 against stock 5)
    - Order cancellation and inventory restocking
    - Queue starvation resolution (round-robin multi-order advancement)
    - Sync queue excluding Cancelled and Delivered orders
"""

import os
import shutil
import sqlite3
import pytest

import database
from store import StoreService
from data_structures import CreateStack


@pytest.fixture
def temp_db(tmp_path):
    """Provides an isolated test database initialized with canonical schema and seed data."""
    db_file = str(tmp_path / "test_store.db")
    conn = database.get_db_connection(db_file)
    database.init_schema(conn)
    database.apply_migrations(conn)
    database.seed_canonical_data(conn)
    conn.close()
    return db_file


def test_cumulative_cart_quantity_validation(temp_db):
    """Verifies issue #8: Adding 4 + 4 against stock of 5 is rejected on second add."""
    store = StoreService(db_path=temp_db)
    cart = CreateStack()

    # Product 1 has stock 10 in canonical seed
    # Set Product 1 stock to exactly 5 for this test
    conn = store.get_connection()
    conn.execute("UPDATE Products SET stock = 5 WHERE product_id = 1;")
    conn.commit()
    conn.close()

    # First add: 4 units against stock 5 -> must succeed
    s1, m1 = store.add_to_cart(cart, product_id=1, quantity=4)
    assert s1 is True
    assert "Added 4x" in m1
    assert len(cart.item) == 1

    # Second add: 4 more units (total 8 > stock 5) -> must be rejected cleanly
    s2, m2 = store.add_to_cart(cart, product_id=1, quantity=4)
    assert s2 is False
    assert "Available in stock: 1 (Already in cart: 4)" in m2
    assert len(cart.item) == 1  # Stack remains untouched


def test_checkout_transaction_success_and_stock_decrement(temp_db):
    """Verifies atomic checkout, order item creation, and stock decrement."""
    store = StoreService(db_path=temp_db)
    cart = CreateStack()

    # Get initial stock of product 2 (Mouse, stock 50) and 3 (Keyboard, stock 30)
    conn = store.get_connection()
    initial_p2 = conn.execute("SELECT stock FROM Products WHERE product_id = 2").fetchone()["stock"]
    initial_p3 = conn.execute("SELECT stock FROM Products WHERE product_id = 3").fetchone()["stock"]
    conn.close()

    store.add_to_cart(cart, product_id=2, quantity=3)
    store.add_to_cart(cart, product_id=3, quantity=2)

    success, msg, order_id = store.checkout(cart, customer_id=1)
    assert success is True
    assert order_id is not None
    assert cart.is_empty() is True

    # Verify database state
    conn = store.get_connection()
    order = conn.execute("SELECT * FROM Orders WHERE order_id = ?", (order_id,)).fetchone()
    assert order is not None
    assert order["status"] == "Placed"

    p2_stock = conn.execute("SELECT stock FROM Products WHERE product_id = 2").fetchone()["stock"]
    p3_stock = conn.execute("SELECT stock FROM Products WHERE product_id = 3").fetchone()["stock"]
    assert p2_stock == initial_p2 - 3
    assert p3_stock == initial_p3 - 2

    # Verify enqueued in dispatch queue
    assert order_id in store.dispatch_queue.to_list()
    conn.close()


def test_checkout_rollback_on_insufficient_stock(temp_db):
    """Verifies checkout fails gracefully and rolls back if stock was depleted prior to commit."""
    store = StoreService(db_path=temp_db)
    cart = CreateStack()

    # Add 2 units of Laptop (id 1)
    store.add_to_cart(cart, product_id=1, quantity=2)

    # In another transaction, deplete laptop stock to 0
    conn = store.get_connection()
    conn.execute("UPDATE Products SET stock = 0 WHERE product_id = 1")
    conn.commit()
    conn.close()

    # Checkout must fail and rollback
    success, msg, order_id = store.checkout(cart, customer_id=1)
    assert success is False
    assert "Insufficient stock" in msg
    assert order_id is None

    # Cart remains intact for user correction
    assert not cart.is_empty()


def test_order_cancellation_and_restocking(temp_db):
    """Verifies issue #9: Cancelling order in 'Placed' restores stock and evicts from queue."""
    store = StoreService(db_path=temp_db)
    cart = CreateStack()

    conn = store.get_connection()
    initial_stock = conn.execute("SELECT stock FROM Products WHERE product_id = 2").fetchone()["stock"]
    conn.close()

    store.add_to_cart(cart, product_id=2, quantity=5)
    success, msg, order_id = store.checkout(cart, customer_id=1)
    assert success is True

    # Confirm stock was decremented
    conn = store.get_connection()
    post_checkout_stock = conn.execute("SELECT stock FROM Products WHERE product_id = 2").fetchone()["stock"]
    assert post_checkout_stock == initial_stock - 5
    conn.close()

    # Cancel the order
    cancel_success, cancel_msg = store.cancel_order(order_id=order_id, customer_id=1)
    assert cancel_success is True
    assert "inventory has been restored" in cancel_msg

    # Confirm status is Cancelled and stock is fully restored
    conn = store.get_connection()
    order_row = conn.execute("SELECT status FROM Orders WHERE order_id = ?", (order_id,)).fetchone()
    assert order_row["status"] == "Cancelled"

    restored_stock = conn.execute("SELECT stock FROM Products WHERE product_id = 2").fetchone()["stock"]
    assert restored_stock == initial_stock
    conn.close()

    # Confirm evicted from dispatch queue
    assert order_id not in store.dispatch_queue.to_list()


def test_cancellation_rejected_for_packed_or_dispatched_orders(temp_db):
    """Verifies that orders already processed past 'Placed' cannot be cancelled."""
    store = StoreService(db_path=temp_db)
    cart = CreateStack()

    store.add_to_cart(cart, product_id=2, quantity=1)
    _, _, order_id = store.checkout(cart, customer_id=1)

    # Advance order to 'Packed'
    conn = store.get_connection()
    conn.execute("UPDATE Orders SET status = 'Packed' WHERE order_id = ?", (order_id,))
    conn.commit()
    conn.close()

    # Customer attempt to cancel must fail
    success, msg = store.cancel_order(order_id=order_id, customer_id=1)
    assert success is False
    assert "Orders can only be cancelled while in 'Placed' stage" in msg


def test_queue_no_starvation_round_robin_advancement(temp_db):
    """Verifies issue #4: Advancing intermediate stages rotates orders so Order 2 is not starved."""
    store = StoreService(db_path=temp_db)

    # Clear queue and create 2 orders
    store.dispatch_queue = store.dispatch_queue.__class__()

    cart1 = CreateStack()
    store.add_to_cart(cart1, 2, 1)
    _, _, o1 = store.checkout(cart1, customer_id=1)

    cart2 = CreateStack()
    store.add_to_cart(cart2, 3, 1)
    _, _, o2 = store.checkout(cart2, customer_id=1)

    assert store.dispatch_queue.to_list() == [o1, o2]

    # Advance 1: advances o1 from 'Placed' to 'Order Confirmed', rotates o1 to rear
    s1, m1, oid1, st1 = store.advance_dispatch()
    assert s1 is True
    assert oid1 == o1
    assert st1 == "Order Confirmed"
    # Order 2 is now at the head of the queue! No starvation!
    assert store.dispatch_queue.peek() == o2
    assert store.dispatch_queue.to_list() == [o2, o1]

    # Advance 2: advances o2 from 'Placed' to 'Order Confirmed', rotates o2 to rear
    s2, m2, oid2, st2 = store.advance_dispatch()
    assert s2 is True
    assert oid2 == o2
    assert st2 == "Order Confirmed"
    assert store.dispatch_queue.peek() == o1


def test_sync_queue_excludes_cancelled_and_delivered_orders(temp_db):
    """Verifies issue #5: Sync queue strictly omits Cancelled and Delivered orders."""
    conn = database.get_db_connection(temp_db)
    cursor = conn.cursor()
    # Insert mock orders with various statuses
    cursor.execute("INSERT INTO Orders (customer_id, total_amount, status) VALUES (1, 100, 'Placed')")
    o_placed = cursor.lastrowid
    cursor.execute("INSERT INTO Orders (customer_id, total_amount, status) VALUES (1, 100, 'Cancelled')")
    o_cancelled = cursor.lastrowid
    cursor.execute("INSERT INTO Orders (customer_id, total_amount, status) VALUES (1, 100, 'Delivered')")
    o_delivered = cursor.lastrowid
    conn.commit()
    conn.close()

    store = StoreService(db_path=temp_db)
    active_queue = store.dispatch_queue.to_list()

    assert o_placed in active_queue
    assert o_cancelled not in active_queue
    assert o_delivered not in active_queue
