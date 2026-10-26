"""
Authentication and Security Tests
Verifies:
    - PBKDF2 password hashing with random salt (no plaintext in DB)
    - Registration success and validation (email format, password length)
    - Duplicate email uniqueness constraint
    - Successful authentication and wrong password rejection
    - SQL injection resistance on search and login
"""

import pytest
import database
from store import StoreService


@pytest.fixture
def temp_db(tmp_path):
    db_file = str(tmp_path / "test_auth.db")
    conn = database.get_db_connection(db_file)
    database.init_schema(conn)
    database.apply_migrations(conn)
    database.seed_canonical_data(conn)
    conn.close()
    return db_file


def test_password_hashing_and_verification():
    raw_pw = "SuperSecret123"
    hashed = database.hash_password(raw_pw)

    assert hashed != raw_pw
    assert "$" in hashed
    salt, key = hashed.split("$", 1)
    assert len(salt) == 32  # 16 bytes in hex = 32 chars
    assert len(key) == 64   # sha256 in hex = 64 chars

    assert database.verify_password(raw_pw, hashed) is True
    assert database.verify_password("WrongPassword", hashed) is False
    assert database.verify_password("", hashed) is False


def test_customer_registration_and_login(temp_db):
    store = StoreService(db_path=temp_db)

    # Valid registration
    s1, m1, cid = store.register_customer("Rohan Verma", "rohan@example.com", "mypassword123")
    assert s1 is True
    assert cid is not None

    # Verify password in DB is hashed, NOT plaintext
    conn = store.get_connection()
    user_row = conn.execute("SELECT password_hash FROM Customers WHERE Customer_id = ?", (cid,)).fetchone()
    assert user_row["password_hash"] != "mypassword123"
    assert "$" in user_row["password_hash"]
    conn.close()

    # Login with valid password
    user, msg = store.authenticate_user("rohan@example.com", "mypassword123")
    assert user is not None
    assert user["name"] == "Rohan Verma"
    assert user["role"] == "customer"

    # Login with wrong password
    bad_user, bad_msg = store.authenticate_user("rohan@example.com", "wrongpass")
    assert bad_user is None
    assert "Invalid email or password" in bad_msg


def test_registration_validation_and_duplicate_email(temp_db):
    store = StoreService(db_path=temp_db)

    # Empty name
    s1, m1, _ = store.register_customer("", "valid@example.com", "123456")
    assert s1 is False

    # Invalid email
    s2, m2, _ = store.register_customer("Name", "not-an-email", "123456")
    assert s2 is False

    # Short password
    s3, m3, _ = store.register_customer("Name", "test@example.com", "123")
    assert s3 is False

    # Duplicate email with existing Customer 1
    s4, m4, _ = store.register_customer("Duplicate", "125anant6027@sjcem.edu.in", "password123")
    assert s4 is False
    assert "already exists" in m4


def test_sql_injection_attempts_are_harmless(temp_db):
    store = StoreService(db_path=temp_db)

    # 1. SQL Injection attempt in Login email field
    malicious_email = "' OR '1'='1' --"
    user, msg = store.authenticate_user(malicious_email, "somepassword")
    assert user is None

    # 2. SQL Injection attempt in Name Search
    malicious_query = "Laptop' OR 1=1 --"
    results = store.search_products(name_query=malicious_query)
    # Treated as a literal search string, not SQL code
    assert len(results) == 0
