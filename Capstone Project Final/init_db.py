"""
Database Initialization Script
Sets up the canonical SQLite schema, applies migrations, and seeds the product catalog.
Safe and repeatable: Uses INSERT OR IGNORE to preserve existing rows.
Compatible with Python 3.10+.
"""

import sys
import database


def initialize():
    print("Initializing Database Setup...")
    conn = database.get_db_connection()

    # 1. Ensure schema and run any pending numbered migrations
    database.init_schema(conn)
    database.apply_migrations(conn)

    # 2. Seed canonical records (preserves existing rows via INSERT OR IGNORE)
    database.seed_canonical_data(conn)

    # 3. Health validation
    health = database.check_db_health(conn)
    if not health["healthy"]:
        print(f"Database health check failed: {health}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    print("Database Setup Completed Successfully.")

    # 4. Display products table safely (Python 3.10+ compatible f-string)
    rows = conn.execute("SELECT product_id, name, price, stock FROM Products ORDER BY product_id ASC").fetchall()
    print("\n--- Products in the Database ---")
    print(f"{'ID':<4}{'Name':<30} {'Price (Rs)':<12}{'Stock':<6}")
    print("-" * 55)
    for row in rows:
        print(f"{row['product_id']:<4}{row['name']:<30} {row['price']:<12.2f} {row['stock']:<6}")

    conn.close()


if __name__ == "__main__":
    initialize()