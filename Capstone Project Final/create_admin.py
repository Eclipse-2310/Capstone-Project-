"""
Admin Bootstrap CLI Tool
Allows interactive creation of a staff administrator account without hardcoding credentials.
Run:
    python create_admin.py
"""

import sys
import getpass
import database


def bootstrap_admin():
    print("=" * 55)
    print("  WAREHOUSE STAFF ADMIN BOOTSTRAP")
    print("=" * 55)

    name = input("Enter Admin Full Name: ").strip()
    if not name:
        print("Error: Name cannot be empty.", file=sys.stderr)
        sys.exit(1)

    email = input("Enter Admin Email Address: ").strip().lower()
    if not email or "@" not in email or "." not in email:
        print("Error: Invalid email format.", file=sys.stderr)
        sys.exit(1)

    password = getpass.getpass("Enter Admin Password (min 8 chars): ")
    if len(password) < 8:
        print("Error: Admin password must be at least 8 characters long.", file=sys.stderr)
        sys.exit(1)

    confirm_password = getpass.getpass("Confirm Admin Password: ")
    if password != confirm_password:
        print("Error: Passwords do not match.", file=sys.stderr)
        sys.exit(1)

    conn = database.get_db_connection()
    try:
        cursor = conn.cursor()
        pw_hash = database.hash_password(password)

        cursor.execute("SELECT Customer_id FROM Customers WHERE LOWER(Email) = ?", (email,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE Customers
                SET Name = ?, password_hash = ?, role = 'admin'
                WHERE Customer_id = ?
            """, (name, pw_hash, existing['Customer_id']))
            print(f"\nSuccess: Existing account '{email}' upgraded to Administrator.")
        else:
            cursor.execute("""
                INSERT INTO Customers (Name, Email, password_hash, role)
                VALUES (?, ?, ?, 'admin')
            """, (name, email, pw_hash))
            print(f"\nSuccess: New Administrator account '{email}' created with ID #{cursor.lastrowid}.")

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Failed to create admin account: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    bootstrap_admin()
