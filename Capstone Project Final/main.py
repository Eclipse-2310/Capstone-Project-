"""
E-Commerce Dispatch and Inventory Management — CLI Entry Point
Interactive command-line interface for students, evaluators, and viva demonstrations.
Utilizes the shared StoreService (store.py) with full DSA and SQLite integration.
"""

import sys
from store import StoreService
from data_structures import CreateStack


class ECommerceCLI:
    """CLI Controller delegating business logic to shared StoreService."""

    def __init__(self, db_name="ecommerce.db"):
        self.store = StoreService(db_path=db_name)
        self.cart = CreateStack()
        self.current_user = {
            'customer_id': 1,
            'name': 'Anant Shrivastav',
            'email': '125anant6027@sjcem.edu.in',
            'role': 'customer'
        }

    def print_menu(self):
        print("\n" + "=" * 55)
        print("  E-COMMERCE DISPATCH & INVENTORY MANAGEMENT (CLI)")
        print(f"  Active User: {self.current_user['name']} ({self.current_user['email']})")
        print("=" * 55)
        print("1. Browse Catalog (Sorted by Price via Merge Sort)")
        print("2. Search Product by ID (Binary Search)")
        print("3. Search Product by Name (Linear Substring Search)")
        print("4. Add Item to Cart (Push to Stack)")
        print("5. Undo Last Cart Item (Pop from Stack)")
        print("6. View Current Cart")
        print("7. Checkout (SQL Transaction + Enqueue Dispatch)")
        print("8. Process Next Dispatch Order (FIFO Round-Robin)")
        print("9. Track Order Status (SQL JOIN Query)")
        print("10. Cancel Order (Restores Stock in SQL Transaction)")
        print("11. Switch / Register User Account")
        print("12. Exit")

    def run(self):
        while True:
            self.print_menu()
            choice = input("\nEnter choice (1-12): ").strip()

            if choice == '1':
                # Browse catalog sorted by Merge Sort
                print("\nSort by: [1] Price: Low to High | [2] Price: High to Low")
                sub_choice = input("Select (default 1): ").strip()
                sort_mode = 'price_desc' if sub_choice == '2' else 'price_asc'
                products = self.store.search_products(sort_by=sort_mode)

                print("\n{:<4} {:<30} {:<12} {:<6}".format("ID", "Product Name", "Price (Rs)", "Stock"))
                print("-" * 55)
                for p in products:
                    print(f"{p['id']:<4} {p['name']:<30} Rs {p['price']:<9.2f} {p['stock']:<6}")

            elif choice == '2':
                # Binary Search by ID
                try:
                    target_id = int(input("Enter Product ID to search: ").strip())
                    found = self.store.get_product_by_id(target_id)
                    if found:
                        print(f"\n[Found via Binary Search]: {found['name']} | Price: Rs {found['price']:.2f} | Stock: {found['stock']}")
                    else:
                        print(f"\nProduct ID #{target_id} not found.")
                except ValueError:
                    print("Invalid numeric ID.")

            elif choice == '3':
                # Linear Search by Name Substring
                query = input("Enter product name or keyword: ").strip()
                matches = self.store.search_products(name_query=query)
                print(f"\nFound {len(matches)} matching product(s):")
                print("{:<4} {:<30} {:<12} {:<6}".format("ID", "Product Name", "Price (Rs)", "Stock"))
                print("-" * 55)
                for p in matches:
                    print(f"{p['id']:<4} {p['name']:<30} Rs {p['price']:<9.2f} {p['stock']:<6}")

            elif choice == '4':
                # Add to Cart (Push to Stack with cumulative stock validation)
                try:
                    pid = int(input("Enter Product ID: ").strip())
                    qty = int(input("Enter Quantity: ").strip())
                    success, msg = self.store.add_to_cart(self.cart, pid, qty)
                    print(f"\n{msg}")
                except ValueError:
                    print("\nInvalid input: Please enter numeric values.")

            elif choice == '5':
                # Undo Cart Item (Pop from Stack)
                success, msg, _ = self.store.undo_cart(self.cart)
                print(f"\n{msg}")

            elif choice == '6':
                # View Active Cart
                if self.cart.is_empty():
                    print("\nYour cart is empty.")
                else:
                    print("\n--- Active Cart (Top is Last Added) ---")
                    for item in reversed(self.cart.get_items()):
                        print(f"- {item['name']} x{item['quantity']} @ Rs {item['price']:.2f} each")
                    print(f"Total: Rs {self.cart.get_total_price():.2f}")

            elif choice == '7':
                # Checkout with ACID SQL Transaction + Enqueue Dispatch
                success, msg, order_id = self.store.checkout(self.cart, self.current_user['customer_id'])
                print(f"\n{msg}")

            elif choice == '8':
                # Process Next Dispatch Order
                success, msg, oid, status = self.store.advance_dispatch()
                print(f"\n{msg}")

            elif choice == '9':
                # Track Order Invoice and Stage
                try:
                    oid = int(input("Enter Order ID to track: ").strip())
                    data, err = self.store.track_order(oid)
                    if err:
                        print(f"\n{err}")
                    else:
                        print(f"\n=== Order #{data['order_id']} Invoice ===")
                        print(f"Customer : {data['customer_name']} ({data['email']})")
                        print(f"Status   : [{data['status'].upper()}]")
                        print(f"Date     : {data['created_at']}")
                        print("\nItems Ordered:")
                        for itm in data['items']:
                            print(f"  * {itm['name']} (x{itm['quantity']}) - Rs {itm['subtotal']:.2f}")
                        print(f"Grand Total: Rs {data['total_amount']:.2f}")
                        print(f"\nMilestone Pipeline:")
                        print(" -> ".join(
                            f"[{s.upper()}]" if s == data['status'] else s
                            for s in data['all_stages']
                        ))
                except ValueError:
                    print("Invalid numeric Order ID.")

            elif choice == '10':
                # Cancel Order
                try:
                    oid = int(input("Enter Order ID to cancel: ").strip())
                    is_admin = (self.current_user['role'] == 'admin')
                    success, msg = self.store.cancel_order(
                        order_id=oid,
                        customer_id=self.current_user['customer_id'],
                        is_admin=is_admin
                    )
                    print(f"\n{msg}")
                except ValueError:
                    print("Invalid numeric Order ID.")

            elif choice == '11':
                # Switch or Register User
                print("\n[1] Login Existing Account | [2] Register New Account")
                act = input("Select (1/2): ").strip()
                if act == '1':
                    email = input("Email: ").strip()
                    pw = input("Password: ").strip()
                    user, msg = self.store.authenticate_user(email, pw)
                    if user:
                        self.current_user = user
                        print(f"\nWelcome back, {user['name']}!")
                    else:
                        print(f"\n{msg}")
                elif act == '2':
                    name = input("Full Name: ").strip()
                    email = input("Email: ").strip()
                    pw = input("Password (min 6 chars): ").strip()
                    success, msg, new_id = self.store.register_customer(name, email, pw)
                    print(f"\n{msg}")
                    if success:
                        self.current_user = {
                            'customer_id': new_id,
                            'name': name,
                            'email': email,
                            'role': 'customer'
                        }

            elif choice == '12':
                print("\nClosing connection. Goodbye!")
                break
            else:
                print("\nInvalid choice. Please choose 1 to 12.")


def main():
    cli = ECommerceCLI()
    cli.run()


if __name__ == "__main__":
    main()