"""
Store Module (Shared Business Logic Layer)
Contains pure business logic, database queries, and data structure integrations.
Zero print() or input() calls.
Shared uniformly by both the CLI (main.py) and the Web Frontend (app.py).
"""

from datetime import datetime
import sqlite3

import database
from data_structures import CreateStack, DispatchQueue, OrderTracker
from algorithm import merge_sort_by_price, binary_search_by_id, linear_search_by_name


class StoreService:
    """
    Central service orchestrating database transactions, cart stack operations,
    dispatch queue management, and order milestone tracking.
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or database.DEFAULT_DB_PATH
        self.dispatch_queue = DispatchQueue()
        self.tracker = OrderTracker()
        self.sync_queue_from_db()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a configured SQLite connection with foreign keys enabled."""
        return database.get_db_connection(self.db_path)

    def sync_queue_from_db(self):
        """
        Populates in-memory FIFO dispatch queue from SQLite.
        Excludes 'Delivered' and 'Cancelled' orders to prevent dead or cancelled jobs from entering the warehouse pipeline.
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT order_id
                FROM Orders
                WHERE status NOT IN ('Delivered', 'Cancelled')
                ORDER BY order_id ASC
            """)
            self.dispatch_queue = DispatchQueue()
            for (order_id,) in cursor.fetchall():
                self.dispatch_queue.enqueue(order_id)
        finally:
            conn.close()

    # -------------------------------------------------------------------------
    # Catalog, Searching, and Sorting
    # -------------------------------------------------------------------------
    def get_all_products(self, conn: sqlite3.Connection = None) -> list:
        """Fetches all products from SQLite as a list of dicts."""
        local_conn = conn or self.get_connection()
        try:
            cursor = local_conn.cursor()
            cursor.execute("SELECT product_id, name, price, stock FROM Products ORDER BY product_id ASC")
            rows = cursor.fetchall()
            return [
                {
                    'id': row['product_id'],
                    'name': row['name'],
                    'price': float(row['price']),
                    'stock': int(row['stock'])
                }
                for row in rows
            ]
        finally:
            if not conn:
                local_conn.close()

    def get_product_by_id(self, product_id: int, conn: sqlite3.Connection = None) -> dict:
        """
        Locates product using Binary Search over pre-sorted product list.
        Demonstrates algorithm.binary_search_by_id.
        """
        products = self.get_all_products(conn)
        # Products are pre-ordered by product_id ASC from SQL query
        return binary_search_by_id(products, product_id)

    def search_products(self, name_query: str = None, id_query: int = None,
                        sort_by: str = None, in_stock_only: bool = False,
                        conn: sqlite3.Connection = None) -> list:
        """
        Searches, filters, and sorts the product catalog.
        Integrates:
            - algorithm.linear_search_by_name (for substring search)
            - algorithm.binary_search_by_id (for exact ID lookup)
            - algorithm.merge_sort_by_price (for ascending/descending price sort)
        """
        products = self.get_all_products(conn)

        # 1. Filter by ID if specified
        if id_query is not None:
            found = binary_search_by_id(products, id_query)
            products = [found] if found else []

        # 2. Filter by Name Substring if specified (Linear Search)
        elif name_query:
            products = linear_search_by_name(products, name_query)

        # 3. Filter in-stock only
        if in_stock_only:
            products = [p for p in products if p['stock'] > 0]

        # 4. Sort via Merge Sort
        if sort_by == 'price_asc':
            products = merge_sort_by_price(products, reverse=False)
        elif sort_by == 'price_desc':
            products = merge_sort_by_price(products, reverse=True)

        return products

    # -------------------------------------------------------------------------
    # Cart Operations (Stack LIFO)
    # -------------------------------------------------------------------------
    def add_to_cart(self, cart: CreateStack, product_id: int, quantity: int, conn: sqlite3.Connection = None) -> tuple:
        """
        Validates inventory stock and pushes item onto the Cart Stack (LIFO).
        Prevents cumulative cart quantity from exceeding physical warehouse stock.
        Returns: (success: bool, message: str)
        """
        if quantity <= 0:
            return False, "Quantity must be greater than zero."

        product = self.get_product_by_id(product_id, conn)
        if not product:
            return False, f"Product ID #{product_id} not found."

        # Calculate cumulative quantity of this product already in cart
        current_in_cart = sum(item['quantity'] for item in cart.item if item['id'] == product_id)
        if current_in_cart + quantity > product['stock']:
            available = product['stock'] - current_in_cart
            return False, f"Cannot add {quantity} units. Available in stock: {available} (Already in cart: {current_in_cart})."

        cart.push({
            'id': product['id'],
            'name': product['name'],
            'price': product['price'],
            'quantity': quantity
        })
        return True, f"Added {quantity}x '{product['name']}' to cart."

    def undo_cart(self, cart: CreateStack) -> tuple:
        """Pops and returns the last added item from the Cart Stack (LIFO)."""
        popped = cart.pop()
        if popped:
            return True, f"Removed '{popped['name']}' (x{popped['quantity']}) from cart.", popped
        return False, "Cart is already empty.", None

    # -------------------------------------------------------------------------
    # Order Placement (Atomic SQL Transaction + FIFO Enqueue)
    # -------------------------------------------------------------------------
    def checkout(self, cart: CreateStack, customer_id: int, conn: sqlite3.Connection = None) -> tuple:
        """
        Commits active cart items to SQLite in an ACID transaction:
            1. Re-validates live stock inside transaction
            2. Inserts parent record into Orders
            3. Inserts each item into Order_Items
            4. Decrements inventory in Products
            5. Enqueues new order_id into DispatchQueue
            6. Clears the cart
        Returns: (success: bool, message: str, order_id: int or None)
        """
        if cart.is_empty():
            return False, "Your cart is empty.", None

        local_conn = conn or self.get_connection()
        try:
            cursor = local_conn.cursor()
            cursor.execute("BEGIN TRANSACTION;")

            # 1. Aggregate cart items by product ID
            aggregated = {}
            for item in cart.item:
                pid = item['id']
                aggregated[pid] = aggregated.get(pid, 0) + item['quantity']

            # 2. Check and lock stock inside transaction
            for pid, req_qty in aggregated.items():
                cursor.execute("SELECT name, stock FROM Products WHERE product_id = ?", (pid,))
                prod_row = cursor.fetchone()
                if not prod_row:
                    local_conn.rollback()
                    return False, f"Product ID #{pid} no longer exists.", None
                if prod_row['stock'] < req_qty:
                    local_conn.rollback()
                    return False, f"Insufficient stock for '{prod_row['name']}'. Available: {prod_row['stock']}, Requested: {req_qty}.", None

            total_amount = cart.get_total_price()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 3. Insert parent Order
            cursor.execute("""
                INSERT INTO Orders (customer_id, total_amount, status, created_at)
                VALUES (?, ?, 'Placed', ?)
            """, (customer_id, total_amount, now_str))
            order_id = cursor.lastrowid

            # 4. Insert Order Items and decrement inventory
            for item in cart.item:
                cursor.execute("""
                    INSERT INTO Order_Items (order_id, product_id, quantity, price)
                    VALUES (?, ?, ?, ?)
                """, (order_id, item['id'], item['quantity'], item['price']))

                cursor.execute("""
                    UPDATE Products
                    SET stock = stock - ?
                    WHERE product_id = ?
                """, (item['quantity'], item['id']))

            local_conn.commit()

            # 5. Update in-memory Queue and reset Cart
            self.dispatch_queue.enqueue(order_id)
            cart.clear()
            return True, f"Order #{order_id} placed successfully for Rs {total_amount:.2f}.", order_id

        except Exception as e:
            local_conn.rollback()
            return False, f"Checkout failed due to error: {str(e)}", None
        finally:
            if not conn:
                local_conn.close()

    # -------------------------------------------------------------------------
    # Warehouse Dispatch Processing (Fair Round-Robin Stage Advancement)
    # -------------------------------------------------------------------------
    def advance_dispatch(self, conn: sqlite3.Connection = None) -> tuple:
        """
        Advances the order at the head of the dispatch queue to its next stage.
        
        Fix for Queue Starvation:
            If the order transitions to an intermediate stage (e.g. 'Order Confirmed' or 'Packed'),
            it is dequeued from the head and re-enqueued at the rear (Round-Robin stage rotation).
            This guarantees that subsequent orders behind it are processed in subsequent turns.
            Only upon reaching 'Delivered' is the order permanently dequeued.
            
        Returns: (success: bool, message: str, order_id: int or None, new_status: str or None)
        """
        if self.dispatch_queue.is_empty():
            return False, "Warehouse dispatch line is empty. No pending orders.", None, None

        order_id = self.dispatch_queue.dequeue()
        local_conn = conn or self.get_connection()
        try:
            cursor = local_conn.cursor()
            cursor.execute("SELECT status FROM Orders WHERE order_id = ?", (order_id,))
            row = cursor.fetchone()

            if not row:
                return False, f"Order #{order_id} record not found.", None, None

            current_status = row['status']
            if current_status in ('Delivered', 'Cancelled'):
                return False, f"Order #{order_id} is already '{current_status}' and was cleared from queue.", order_id, current_status

            next_status = self.tracker.get_next_stage(current_status)
            if not next_status:
                return False, f"Order #{order_id} cannot advance further from '{current_status}'.", order_id, current_status

            cursor.execute("UPDATE Orders SET status = ? WHERE order_id = ?", (next_status, order_id))
            local_conn.commit()

            if next_status == 'Delivered':
                return True, f"Order #{order_id} delivered successfully (cleared from warehouse queue).", order_id, next_status
            else:
                # Rotate order to rear of queue for next station
                self.dispatch_queue.enqueue(order_id)
                return True, f"Order #{order_id} advanced: [{current_status}] -> [{next_status}].", order_id, next_status

        finally:
            if not conn:
                local_conn.close()

    # -------------------------------------------------------------------------
    # Order Cancellation and Stock Restocking
    # -------------------------------------------------------------------------
    def cancel_order(self, order_id: int, customer_id: int = None, is_admin: bool = False, conn: sqlite3.Connection = None) -> tuple:
        """
        Cancels an order and restores warehouse stock in an atomic SQL transaction:
            - Cancellation is strictly permitted only in 'Placed' stage (before packing/dispatch).
            - Non-admin customers can only cancel their own orders.
            - Restores product stock for all line items.
            - Evicts the cancelled order from the in-memory dispatch queue.
        Returns: (success: bool, message: str)
        """
        local_conn = conn or self.get_connection()
        try:
            cursor = local_conn.cursor()
            cursor.execute("BEGIN TRANSACTION;")

            cursor.execute("SELECT customer_id, status FROM Orders WHERE order_id = ?", (order_id,))
            order = cursor.fetchone()
            if not order:
                local_conn.rollback()
                return False, f"Order #{order_id} not found."

            if not is_admin and customer_id is not None and order['customer_id'] != customer_id:
                local_conn.rollback()
                return False, "Unauthorized: You do not own this order."

            current_status = order['status']
            if current_status != 'Placed':
                local_conn.rollback()
                return False, f"Cannot cancel order #{order_id}. Orders can only be cancelled while in 'Placed' stage (Current: {current_status})."

            # 1. Update status to Cancelled
            cursor.execute("UPDATE Orders SET status = 'Cancelled' WHERE order_id = ?", (order_id,))

            # 2. Restore stock
            cursor.execute("SELECT product_id, quantity FROM Order_Items WHERE order_id = ?", (order_id,))
            items = cursor.fetchall()
            for itm in items:
                cursor.execute("""
                    UPDATE Products
                    SET stock = stock + ?
                    WHERE product_id = ?
                """, (itm['quantity'], itm['product_id']))

            local_conn.commit()

            # 3. Evict from in-memory dispatch queue
            self.dispatch_queue.remove(order_id)
            return True, f"Order #{order_id} has been cancelled and inventory has been restored."

        except Exception as e:
            local_conn.rollback()
            return False, f"Cancellation failed: {str(e)}"
        finally:
            if not conn:
                local_conn.close()

    # -------------------------------------------------------------------------
    # Order Tracking & Inspection
    # -------------------------------------------------------------------------
    def track_order(self, order_id: int, conn: sqlite3.Connection = None) -> tuple:
        """
        Fetches invoice data and milestone stage information for an order using SQL JOINs.
        Returns: (order_dict or None, error_str or None)
        """
        local_conn = conn or self.get_connection()
        try:
            cursor = local_conn.cursor()
            cursor.execute("""
                SELECT O.order_id, O.customer_id, C.name as customer_name, C.email,
                       O.total_amount, O.status, O.created_at
                FROM Orders O
                JOIN Customers C ON O.customer_id = C.customer_id
                WHERE O.order_id = ?
            """, (order_id,))
            order = cursor.fetchone()
            if not order:
                return None, f"Order #{order_id} not found."

            cursor.execute("""
                SELECT P.name, OI.quantity, OI.price, (OI.quantity * OI.price) as subtotal
                FROM Order_Items OI
                JOIN Products P ON OI.product_id = P.product_id
                WHERE OI.order_id = ?
            """, (order_id,))
            items = cursor.fetchall()

            all_stages = self.tracker.get_all_stages()
            current_status = order['status']

            # Determine progress index in linked list
            current_index = -1
            if current_status in all_stages:
                current_index = all_stages.index(current_status)

            line_items = [
                {
                    'name': itm['name'],
                    'quantity': itm['quantity'],
                    'price': float(itm['price']),
                    'subtotal': float(itm['subtotal'])
                }
                for itm in items
            ]

            return {
                'order_id': order['order_id'],
                'customer_id': order['customer_id'],
                'customer_name': order['customer_name'],
                'email': order['email'],
                'total_amount': float(order['total_amount']),
                'status': current_status,
                'created_at': order['created_at'],
                'items': line_items,
                'line_items': line_items,
                'all_stages': all_stages,
                'current_stage_index': current_index,
                'is_cancellable': (current_status == 'Placed')
            }, None
        finally:
            if not conn:
                local_conn.close()

    def get_customer_orders(self, customer_id: int, conn: sqlite3.Connection = None) -> list:
        """Fetches all orders placed by a specific customer in reverse chronological order."""
        local_conn = conn or self.get_connection()
        try:
            cursor = local_conn.cursor()
            cursor.execute("""
                SELECT order_id, total_amount, status, created_at
                FROM Orders
                WHERE customer_id = ?
                ORDER BY order_id DESC
            """, (customer_id,))
            rows = cursor.fetchall()
            return [
                {
                    'order_id': r['order_id'],
                    'total_amount': float(r['total_amount']),
                    'status': r['status'],
                    'created_at': r['created_at'],
                    'is_cancellable': (r['status'] == 'Placed')
                }
                for r in rows
            ]
        finally:
            if not conn:
                local_conn.close()

    # -------------------------------------------------------------------------
    # Authentication & User Management
    # -------------------------------------------------------------------------
    def register_customer(self, name: str, email: str, password: str, conn: sqlite3.Connection = None) -> tuple:
        """
        Registers a new customer with a PBKDF2-hashed password.
        Returns: (success: bool, message: str, customer_id: int or None)
        """
        if not name or not name.strip():
            return False, "Name cannot be empty.", None
        if not email or "@" not in email or "." not in email:
            return False, "Please provide a valid email address.", None
        if not password or len(password) < 6:
            return False, "Password must be at least 6 characters long.", None

        clean_name = name.strip()
        clean_email = email.strip().lower()

        local_conn = conn or self.get_connection()
        try:
            cursor = local_conn.cursor()
            pw_hash = database.hash_password(password)

            cursor.execute("""
                INSERT INTO Customers (Name, Email, password_hash, role)
                VALUES (?, ?, ?, 'customer')
            """, (clean_name, clean_email, pw_hash))
            local_conn.commit()
            return True, "Registration successful.", cursor.lastrowid
        except sqlite3.IntegrityError:
            return False, f"An account with email '{clean_email}' already exists.", None
        finally:
            if not conn:
                local_conn.close()

    def authenticate_user(self, email: str, password: str, conn: sqlite3.Connection = None) -> tuple:
        """
        Authenticates customer or admin using constant-time password hash verification.
        Returns: (user_dict or None, message: str)
        """
        if not email or not password:
            return None, "Email and password are required."

        clean_email = email.strip().lower()
        local_conn = conn or self.get_connection()
        try:
            cursor = local_conn.cursor()
            cursor.execute("""
                SELECT Customer_id, Name, Email, password_hash, role
                FROM Customers
                WHERE LOWER(Email) = ?
            """, (clean_email,))
            user = cursor.fetchone()

            if not user or not user['password_hash']:
                return None, "Invalid email or password."

            if database.verify_password(password, user['password_hash']):
                return {
                    'customer_id': user['Customer_id'],
                    'name': user['Name'],
                    'email': user['Email'],
                    'role': user['role']
                }, "Authentication successful."
            return None, "Invalid email or password."
        finally:
            if not conn:
                local_conn.close()
