"""
Concurrency and Race Condition Tests
Verifies that simultaneous checkouts competing for the last unit of a product
result in exactly ONE successful checkout, and stock never goes negative.
"""

import threading
import pytest

import database
from store import StoreService
from data_structures import CreateStack


@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_concurrency.db")
    conn = database.get_db_connection(db_file)
    database.init_schema(conn)
    database.apply_migrations(conn)
    database.seed_canonical_data(conn)

    # Set Product 1 stock to exactly 1
    conn.execute("UPDATE Products SET stock = 1 WHERE product_id = 1;")
    conn.commit()
    conn.close()
    return db_file


def test_concurrent_checkout_on_last_item(temp_db):
    """
    Simulates two buyers submitting checkout simultaneously for the last item.
    Uses a threading.Barrier to synchronize checkout execution.
    """
    barrier = threading.Barrier(2)
    results = []

    def attempt_checkout(thread_id):
        # Each thread creates its own StoreService and Cart to simulate separate requests
        local_store = StoreService(db_path=temp_db)
        cart = CreateStack()
        local_store.add_to_cart(cart, product_id=1, quantity=1)

        # Synchronize threads so they hit checkout at the exact same instant
        barrier.wait()
        success, msg, order_id = local_store.checkout(cart, customer_id=1)
        results.append((thread_id, success, msg, order_id))

    t1 = threading.Thread(target=attempt_checkout, args=("Thread-1",))
    t2 = threading.Thread(target=attempt_checkout, args=("Thread-2",))

    t1.start()
    t2.start()

    t1.join()
    t2.join()

    # Analyze outcomes
    successes = [r for r in results if r[1] is True]
    failures = [r for r in results if r[1] is False]

    assert len(successes) == 1, f"Expected exactly 1 success, got {len(successes)}: {results}"
    assert len(failures) == 1, f"Expected exactly 1 failure, got {len(failures)}: {results}"

    # Verify inventory in database
    conn = database.get_db_connection(temp_db)
    final_stock = conn.execute("SELECT stock FROM Products WHERE product_id = 1").fetchone()["stock"]
    assert final_stock == 0, f"Stock should be 0, but found {final_stock}"
    conn.close()
