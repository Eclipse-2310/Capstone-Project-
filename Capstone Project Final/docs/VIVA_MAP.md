# Academic Viva Traceability Map

**Project:** E-Commerce Dispatch and Inventory Management  
**Core Disciplines:** Python Programming, Data Structures & Algorithms (DSA), Relational Database Management Systems (RDBMS)

---

## 1. Feature, DSA, and DBMS Traceability Matrix

| Feature / Screen | Invocation (CLI / Route) | Python Module & Function | Data Structure / Algorithm | Time & Space Complexity | Database Tables & SQL Queries | Academic Note & Viva Justification |
|---|---|---|---|---|---|---|
| **Catalog Price Sorting** | CLI Option 1<br>`GET /?sort=price_asc` | `algorithm.py`<br>`merge_sort_by_price()` | **Merge Sort**<br>(Divide & Conquer) | **Time:** $O(n \log n)$<br>**Space:** $O(n)$ auxiliary | `SELECT product_id, name, price, stock FROM Products ORDER BY product_id ASC` | Demonstrates divide-and-conquer recursion in Python. DBMS could sort via `ORDER BY price`, but merge sort showcases recursive splitting and sublist merging. |
| **Product ID Lookup** | CLI Option 2<br>`GET /?id=<id>` | `algorithm.py`<br>`binary_search_by_id()` | **Binary Search**<br>(Logarithmic Search) | **Time:** $O(\log n)$<br>**Space:** $O(1)$ | Fetches catalog pre-ordered by primary key index | SQLite DBMS engine already locates primary keys in $O(\log n)$ via its B-Tree index. Binary search is implemented in Python to demonstrate search halving on sorted contiguous in-memory structures. |
| **Product Substring Search** | CLI Option 3<br>`GET /?name=<query>` | `algorithm.py`<br>`linear_search_by_name()` | **Linear Search**<br>(Sequential Scan) | **Time:** $O(n \times m)$<br>**Space:** $O(k)$ results | Reads catalog in memory | Demonstrates sequential iteration and string matching over unindexed fields. Equivalent to SQL `LIKE '%query%'`. |
| **Shopping Cart Layering** | CLI Option 4<br>`POST /cart/add` | `store.py`<br>`StoreService.add_to_cart()` | **Stack (LIFO)**<br>`CreateStack.push()` | **Time:** $O(1)$ push<br>**Space:** $O(k)$ items | `SELECT name, stock FROM Products WHERE product_id = ?` | Stack models user action history. Validates cumulative stock (`current_in_cart + req <= stock`) to prevent checkout errors. |
| **Cart Undo Operation** | CLI Option 5<br>`POST /cart/undo` | `store.py`<br>`StoreService.undo_cart()` | **Stack (LIFO)**<br>`CreateStack.pop()` | **Time:** $O(1)$ pop<br>**Space:** $O(1)$ | None (pure in-memory stack modification) | Classic textbook use case for Stack: undoing the most recently added item in reverse chronological order. |
| **Atomic Checkout** | CLI Option 7<br>`POST /checkout` | `store.py`<br>`StoreService.checkout()` | **Queue (FIFO)**<br>`DispatchQueue.enqueue()` | **Time:** $O(1)$ enqueue<br>**Space:** $O(1)$ | `BEGIN TRANSACTION`<br>`INSERT INTO Orders`<br>`INSERT INTO Order_Items`<br>`UPDATE Products SET stock = stock - ?`<br>`COMMIT` | Multi-table ACID transaction. If stock is insufficient, transaction rolls back cleanly with zero orphan rows. Successfully placed order enters warehouse FIFO dispatch queue. |
| **Order Milestone Pipeline** | CLI Option 9<br>`GET /orders/<id>` | `data_structures.py`<br>`OrderTracker` | **Singly Linked List**<br>`StatusNode`, traversal | **Time:** $O(k)$ stages<br>**Space:** $O(k)$ nodes | `SELECT O.*, C.name, OI.*, P.name FROM Orders O JOIN Customers C ... JOIN Order_Items ...` | Linear sequence of immutable milestones: `Placed -> Order Confirmed -> Packed -> Dispatched -> Delivered`. Traversal pointer walks nodes to find the immediate successor stage. |
| **Warehouse Dispatch Advancement** | CLI Option 8<br>`POST /admin/queue/advance` | `store.py`<br>`StoreService.advance_dispatch()` | **Queue (FIFO)**<br>`DispatchQueue.dequeue()` | **Time:** $O(1)$ deque<br>**Space:** $O(1)$ | `UPDATE Orders SET status = ? WHERE order_id = ?` | Re-implemented using `collections.deque` for true $O(1)$ enqueue/dequeue (avoiding Python list $O(n)$ shifts). Intermediate stages rotate order to rear (Round-Robin) to prevent head-order starvation. |
| **Order Cancellation & Restock** | CLI Option 10<br>`POST /orders/<id>/cancel` | `store.py`<br>`StoreService.cancel_order()` | **Queue Eviction**<br>`DispatchQueue.remove()` | **Time:** $O(n)$ search<br>**Space:** $O(1)$ | `BEGIN TRANSACTION`<br>`UPDATE Orders SET status = 'Cancelled'`<br>`UPDATE Products SET stock = stock + ?`<br>`COMMIT` | Permitted only while order is in 'Placed' milestone. Restores inventory count atomically and removes order from warehouse queue. |
| **Customer Authentication** | CLI Option 11<br>`POST /login` | `store.py`<br>`StoreService.authenticate_user()` | Cryptographic Hash<br>(PBKDF2-HMAC-SHA256) | **Time:** $O(1)$<br>**Space:** $O(1)$ | `SELECT Customer_id, password_hash, role FROM Customers WHERE LOWER(Email) = ?` | 100,000 hash iterations with 16-byte random salt. Verification uses constant-time string comparison (`hmac.compare_digest`) to prevent timing attacks. |

---

## 2. Key Viva Defense Questions & Answers

### Q1: Why did you use `collections.deque` instead of a standard Python list for `DispatchQueue`?
> **Answer:** In Python, a standard `list` is a dynamic contiguous array. Calling `list.pop(0)` takes $O(n)$ linear time because all remaining $n-1$ elements must be shifted one memory address to the left. `collections.deque` is implemented internally as a doubly linked list of fixed-size blocks, providing guaranteed $O(1)$ amortized append and $O(1)$ popleft, which strictly complies with the theoretical computer science definition of a Queue.

### Q2: How did you solve the Queue Starvation problem in warehouse dispatch?
> **Answer:** In the original design, `advance_dispatch()` only dequeued an order when it reached `'Delivered'`. An order with 5 stages blocked all subsequent orders from moving. We resolved this by implementing **Round-Robin Stage Rotation**: when an order advances to an intermediate stage (e.g. `'Order Confirmed'` or `'Packed'`), it is dequeued from the front and re-enqueued at the rear. This allows every pending order in the queue to be processed at each station without starvation.

### Q3: Why does your code implement Binary Search if the SQLite database already has indexes?
> **Answer:** In a production database, primary key lookups (`SELECT * FROM Products WHERE product_id = ?`) are resolved in $O(\log n)$ by the SQLite B-Tree index. We retain the Python `binary_search_by_id()` in `algorithm.py` to demonstrate the binary search divide-and-conquer algorithm on contiguous array structures in memory, and we fetch the catalog pre-sorted to eliminate redundant $O(n \log n)$ array sorting.

### Q4: How is stock concurrency managed during simultaneous checkouts?
> **Answer:** SQLite uses page-level transaction locks (`BEGIN TRANSACTION`). Inside the transaction, live stock is verified immediately before decrementing. If two threads compete for the final unit of stock, the first thread decrements stock to 0 and commits. The second thread detects that stock is 0, issues an automatic `ROLLBACK`, and informs the buyer that inventory is depleted. Stock never goes negative.

### Q5: How do the CLI and Web App stay consistent?
> **Answer:** Both interfaces share a unified business logic module (`store.py`). Neither `main.py` nor `app.py` writes ad-hoc SQL queries or duplicates data structures. The SQLite database serves as the single source of truth, and foreign keys are enforced on every connection via `PRAGMA foreign_keys = ON;`.
