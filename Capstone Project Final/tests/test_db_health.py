"""
Database Health and Constraints Tests
Verifies:
    - PRAGMA integrity_check
    - PRAGMA foreign_key_check
    - Enforcement of foreign key constraints
    - Presence of foreign key indexes
"""

import sqlite3
import pytest
import database


@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_health.db")
    conn = database.get_db_connection(db_file)
    database.init_schema(conn)
    database.apply_migrations(conn)
    database.seed_canonical_data(conn)
    conn.close()
    return db_file


def test_database_health_and_integrity(temp_db):
    conn = database.get_db_connection(temp_db)
    health = database.check_db_health(conn)
    assert health["healthy"] is True
    assert health["integrity"] == ["ok"]
    assert health["foreign_key_violations"] == []
    assert health["foreign_keys_enabled"] is True
    conn.close()


def test_foreign_key_constraint_enforcement(temp_db):
    conn = database.get_db_connection(temp_db)
    cursor = conn.cursor()

    # Attempt to insert Order for non-existent customer 99999
    with pytest.raises(sqlite3.IntegrityError) as exc_info:
        cursor.execute("INSERT INTO Orders (customer_id, total_amount, status) VALUES (99999, 100.0, 'Placed')")
        conn.commit()

    assert "FOREIGN KEY constraint failed" in str(exc_info.value)
    conn.close()


def test_foreign_key_indexes_exist(temp_db):
    conn = database.get_db_connection(temp_db)
    indexes = [row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()]

    assert "idx_orders_customer_id" in indexes
    assert "idx_order_items_order_id" in indexes
    assert "idx_order_items_product_id" in indexes
    conn.close()
