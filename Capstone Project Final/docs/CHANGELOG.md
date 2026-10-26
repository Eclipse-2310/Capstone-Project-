# Project Changelog & Architecture Refactoring Log

**Date:** October 26, 2026  
**Branch:** `redesign`  

---

## 1. Summary of System Transformations

The project has been transformed from an unversioned, single-threaded command-line script into a production-ready, dual-interface system (CLI + Flask Web Application) backed by clean relational architecture, verified data structures, and an automated test suite.

---

## 2. File-by-File Changes

### New Files Created
- **`store.py`**: Shared service layer decoupling business logic, database transactions, cart stack operations, and dispatch queue management from both CLI and web entry points.
- **`database.py`**: Canonical database configuration, connection factory (`PRAGMA foreign_keys = ON`), PBKDF2 password hashing with random salt, and SQLite health checks.
- **`app.py`**: Web application entry point providing session management, CSRF validation, customer storefront, and staff admin warehouse operations.
- **`wsgi.py`**: Production WSGI entry point for Gunicorn / PythonAnywhere / Waitress with environment verification.
- **`create_admin.py`**: Interactive CLI bootstrap script for creating staff administrator accounts without hardcoded credentials.
- **`seed_demo.py`**: Sanitized demo database builder ensuring real student records are never exposed or deployed to public hosts.
- **`migrations/001_add_auth_and_indexes.sql`**: Numbered migration adding `password_hash`, `role`, and foreign key indexes.
- **`migrations/001_rollback.sql`**: Rollback script reversing migration 001.
- **`static/css/style.css`**: Design tokens, editorial typography layout, and CSS-only linked list milestone markers.
- **`static/fonts/`**: Self-hosted local WOFF2 font files (`Bitter` and `IBM Plex Sans`). Zero runtime CDN requests.
- **`templates/*.html`**: 14 semantic, accessible Jinja2 templates for customer purchase flows and warehouse queue processing.
- **`tests/*.py`**: 28 automated integration tests spanning DSA, transactions, concurrency, security, and web routes.
- **`.gitignore` & `.env.example`**: Version control and environment variable isolation.

### Existing Files Modified
- **`data_structures.py`**:
  - Fixed `KeyError: 'price'` in `__main__` test block by standardizing on lowercase dictionary keys.
  - Re-implemented `DispatchQueue` using `collections.deque` for true $O(1)$ enqueue and dequeue (resolved $O(n)$ `list.pop(0)` flaw).
  - Updated `OrderTracker` milestones to honest non-gateway terminology (`"Order Confirmed"`) and added `get_all_stages()` linked list traversal.
- **`algorithm.py`**:
  - Added `linear_search_by_name()` for case-insensitive substring searching ($O(n \times m)$).
  - Added `reverse` parameter to `merge_sort_by_price()` supporting ascending and descending order.
  - Added academic docstrings clarifying algorithm complexities and noting SQLite B-tree index equivalents.
- **`init_db.py`**:
  - Fixed Python < 3.12 syntax error caused by nested double quotes in f-strings.
  - Refactored to use canonical `database.py` schema creation and seeding.
  - Made idempotent and safe to run multiple times without data loss.
- **`main.py`**:
  - Refactored from monolithic SQL execution into a clean CLI controller delegating all operations to `store.py`.
  - Preserved all original CLI options (1–9) while adding order cancellation, name search, and customer account switching.

---

## 3. Database & Security Hardening
1. **Password Encryption:** Replaced missing/plaintext credentials with PBKDF2-HMAC-SHA256 (100,000 iterations + 16-byte random salt).
2. **Foreign Key Enforcement:** Enforced `PRAGMA foreign_keys = ON;` across every CLI and web request lifecycle.
3. **Foreign Key Indexing:** Added secondary indexes on `Orders(Customer_id)`, `Order_Items(Order_id)`, and `Order_Items(Product_id)`.
4. **Queue Fairness:** Replaced single-order blocking with Round-Robin stage advancement to eliminate order starvation.
5. **Cancelled Order Exclusion:** Ensured cancelled orders are excluded from warehouse dispatch queues and restock inventory atomically.
