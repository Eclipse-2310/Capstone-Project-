"""
Reproducible Demo Database Builder
Creates a fresh, sanitized database for public hosting, demonstration, and viva presentation.
Ensures private student data from ecommerce.db is NEVER committed or deployed.

Usage:
    python seed_demo.py [target_database_path]
"""

import sys
import os
import database


def build_demo_database(target_db_path="ecommerce_demo.db"):
    print("=" * 60)
    print(f"  BUILDING REPRODUCIBLE DEMO DATABASE: {target_db_path}")
    print("=" * 60)

    # 1. Open connection and initialize schema
    conn = database.get_db_connection(target_db_path)
    database.init_schema(conn)
    database.apply_migrations(conn)

    cursor = conn.cursor()

    # 2. Seed sanitized, clearly labeled demo accounts
    demo_cust_hash = database.hash_password("demopass123")
    demo_admin_hash = database.hash_password("staffpass123")

    cursor.execute("""
        INSERT OR IGNORE INTO Customers (Customer_id, Name, Email, password_hash, role)
        VALUES (1, 'Demo Customer (Student)', 'demo.customer@example.com', ?, 'customer')
    """, (demo_cust_hash,))

    cursor.execute("""
        INSERT OR IGNORE INTO Customers (Customer_id, Name, Email, password_hash, role)
        VALUES (2, 'Demo Warehouse Staff', 'demo.staff@example.com', ?, 'admin')
    """, (demo_admin_hash,))

    # 3. Seed canonical 10 products
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

    # 4. Create one initial sample demo order for demonstration
    cursor.execute("""
        INSERT OR IGNORE INTO Orders (Order_id, Customer_id, Total_Amount, Status, Created_At)
        VALUES (1, 1, 1059.98, 'Placed', DATETIME('now'))
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO Order_Items (Item_id, Order_id, Product_id, Quantity, Price)
        VALUES (1, 1, 1, 1, 999.99)
    """)
    cursor.execute("""
        INSERT OR IGNORE INTO Order_Items (Item_id, Order_id, Product_id, Quantity, Price)
        VALUES (2, 1, 2, 2, 29.99)
    """)

    conn.commit()

    # 5. Verify integrity
    health = database.check_db_health(conn)
    conn.close()

    if health["healthy"]:
        print(f"\nDemo Database built successfully at: {target_db_path}")
        print("Demo Credentials:")
        print("  Customer: demo.customer@example.com / demopass123")
        print("  Staff:    demo.staff@example.com    / staffpass123")
    else:
        print(f"\nWarning: Health checks failed: {health}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "ecommerce_demo.db"
    build_demo_database(target)
