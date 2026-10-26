"""
Database Module
Canonical schema definition, connection management, migrations,
password security (PBKDF2-SHA256), and database integrity helpers.
"""

import os
import sqlite3
import hashlib
import hmac
import secrets

DEFAULT_DB_PATH = os.getenv("DATABASE_PATH", "ecommerce.db")


def hash_password(password: str) -> str:
    """
    Hashes a password using PBKDF2-HMAC-SHA256 with 100,000 iterations and random salt.
    Returns format: 'salt$hash' (both in hexadecimal).
    """
    if not password:
        raise ValueError("Password cannot be empty.")
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100_000
    )
    return f"{salt}${key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verifies a plaintext password against a stored 'salt$hash' using constant-time comparison.
    """
    if not password or not stored_hash or '$' not in stored_hash:
        return False
    try:
        salt, expected_key = stored_hash.split('$', 1)
        actual_key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100_000
        )
        return hmac.compare_digest(actual_key.hex(), expected_key)
    except Exception:
        return False


def get_db_connection(db_path: str = None) -> sqlite3.Connection:
    """
    Creates and configures an SQLite connection with Foreign Keys strictly enabled.
    Returns connection with sqlite3.Row row factory for clean dict-like column access.
    """
    target_path = db_path or os.getenv("DATABASE_PATH", DEFAULT_DB_PATH)
    conn = sqlite3.connect(target_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection):
    """
    Creates base canonical schema if tables do not exist.
    """
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS Customers(
            Customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Email TEXT NOT NULL UNIQUE,
            password_hash TEXT,
            role TEXT NOT NULL DEFAULT 'customer' CHECK(role IN ('customer', 'admin'))
        );

        CREATE TABLE IF NOT EXISTS Products(
            Product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Price REAL NOT NULL CHECK(Price > 0),
            Stock INTEGER CHECK(Stock >= 0)
        );

        CREATE TABLE IF NOT EXISTS Orders(
            Order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            Customer_id INTEGER NOT NULL,
            Total_Amount REAL NOT NULL,
            Status TEXT NOT NULL CHECK(Status IN('Placed', 'Order Confirmed', 'Packed', 'Dispatched', 'Delivered', 'Cancelled')),
            Created_At TEXT NOT NULL DEFAULT(DATETIME('now')),
            FOREIGN KEY(Customer_id) REFERENCES Customers(Customer_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS Order_Items(
            Item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            Order_id INTEGER NOT NULL,
            Product_id INTEGER NOT NULL,
            Quantity INTEGER NOT NULL CHECK(Quantity > 0),
            Price REAL NOT NULL CHECK(Price > 0),
            FOREIGN KEY(Order_id) REFERENCES Orders(Order_id) ON DELETE CASCADE,
            FOREIGN KEY(Product_id) REFERENCES Products(Product_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS schema_migrations(
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT(DATETIME('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON Orders(Customer_id);
        CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON Order_Items(Order_id);
        CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON Order_Items(Product_id);
    """)
    conn.commit()


def apply_migrations(conn: sqlite3.Connection, migrations_dir: str = "migrations"):
    """
    Applies any unapplied numbered SQL migrations in ascending numerical order.
    """
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations(
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT(DATETIME('now'))
        )
    """)
    conn.commit()

    if not os.path.exists(migrations_dir):
        return

    # Check already applied
    applied = {row[0] for row in cursor.execute("SELECT version FROM schema_migrations").fetchall()}

    sql_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql") and not f.endswith("_rollback.sql")])
    for filename in sql_files:
        version_part = filename.split("_")[0]
        try:
            version_int = int(version_part)
        except ValueError:
            continue

        if version_int not in applied:
            filepath = os.path.join(migrations_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                sql_content = f.read()

            try:
                # Wrap each migration in a transaction
                cursor.execute("BEGIN TRANSACTION;")
                cursor.executescript(sql_content)
                cursor.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version_int,))
                conn.commit()
            except Exception as e:
                conn.rollback()
                # If error is due to column already existing, mark as applied
                if "duplicate column name" in str(e).lower():
                    cursor.execute("INSERT OR IGNORE INTO schema_migrations (version) VALUES (?)", (version_int,))
                    conn.commit()
                else:
                    raise RuntimeError(f"Migration {filename} failed: {e}") from e


def seed_canonical_data(conn: sqlite3.Connection, include_demo_admin: bool = True):
    """
    Seeds initial canonical catalog (10 products) and existing demo accounts using INSERT OR IGNORE.
    Existing live rows are preserved.
    """
    cursor = conn.cursor()

    # 1. Existing student customer with verified demo password 'student123'
    student_pw_hash = hash_password("student123")
    cursor.execute("""
        INSERT OR IGNORE INTO Customers (Customer_id, Name, Email, password_hash, role)
        VALUES (1, 'Anant Shrivastav', '125anant6027@sjcem.edu.in', ?, 'customer')
    """, (student_pw_hash,))

    # Update password for customer 1 if null
    cursor.execute("""
        UPDATE Customers
        SET password_hash = ?, role = 'customer'
        WHERE Customer_id = 1 AND (password_hash IS NULL OR password_hash = '')
    """, (student_pw_hash,))

    # 2. Demo Admin Account for warehouse/staff
    if include_demo_admin:
        admin_pw_hash = hash_password("admin123")
        cursor.execute("""
            INSERT OR IGNORE INTO Customers (Customer_id, Name, Email, password_hash, role)
            VALUES (999, 'Warehouse Staff Admin', 'admin@sjcem.edu.in', ?, 'admin')
        """, (admin_pw_hash,))

    # 3. Canonical 10 Products with exact Indian Rupee pricing
    canonical_products = [
        (1, 'Laptop', 999.99, 10),
        (2, 'Mouse', 29.99, 50),
        (3, 'Keyboard', 79.99, 30),
        (4, 'Monitor', 199.99, 20),
        (5, 'Printer', 149.99, 15),
        (6, 'Webcam', 49.99, 25),
        (7, 'Headphones', 89.99, 40),
        (8, 'Speakers', 59.99, 35),
        (9, 'External Hard Drive', 129.99, 18),
        (10, 'USB Flash Drive', 19.99, 100)
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO Products (Product_id, Name, Price, Stock)
        VALUES (?, ?, ?, ?)
    """, canonical_products)

    conn.commit()


def check_db_health(conn: sqlite3.Connection) -> dict:
    """
    Performs SQLite integrity and foreign key checks.
    Returns status dictionary.
    """
    cursor = conn.cursor()
    integrity = cursor.execute("PRAGMA integrity_check;").fetchall()
    fk_check = cursor.execute("PRAGMA foreign_key_check;").fetchall()
    fk_enabled = cursor.execute("PRAGMA foreign_keys;").fetchone()[0] == 1

    integrity_ok = len(integrity) == 1 and integrity[0][0] == "ok"
    fk_ok = len(fk_check) == 0

    return {
        "healthy": integrity_ok and fk_ok and fk_enabled,
        "integrity": [row[0] for row in integrity],
        "foreign_key_violations": [list(row) for row in fk_check],
        "foreign_keys_enabled": fk_enabled
    }
