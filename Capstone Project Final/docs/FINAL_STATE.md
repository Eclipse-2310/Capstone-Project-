# Project State Assessment and Verification Test Plan

**Date:** October 25, 2026  
**Role:** QA & Release Engineering  
**Project:** E-Commerce Dispatch and Inventory Management  
**Environment:** Windows (PowerShell), Python 3.10+ target (Active: Python 3.13.7)  

---

> [!WARNING]
> **OneDrive Synchronization Alert**:  
> The project directory is currently inside OneDrive:  
> `C:\Users\shaik\OneDrive\Desktop\College (Rehan)\Capstone Project Final`  
> In accordance with project safety guidelines, we strongly recommend migrating the working folder to a non-synced local path (such as `C:\Projects\Capstone`) to prevent SQLite concurrency deadlocks and `.git` index corruption. We are awaiting user confirmation on whether to remain in this directory or relocate before modifying code.

---

## 1. Current State Inventory

### What Exists
1. **CLI Application:** `main.py` (302 lines) — Monolithic terminal application with an interactive menu (Options 1–9), holding connection and state logic.
2. **Database Initialization:** `init_db.py` (79 lines) — Standalone database setup script defining DDL and seed records (1 customer, 10 products).
3. **Algorithms Module:** `algorithm.py` (80 lines) — `merge_sort_by_price` and `binary_search_by_id`.
4. **Data Structures Module:** `data_structures.py` (109 lines) — `CreateStack`, `DispatchQueue`, and `OrderTracker` (singly linked list).
5. **Database File:** `ecommerce.db` (28 KB SQLite database) — Contains active live records (Customer 1: Anant Shrivastav, 3 Products: Laptop [stock 5], Mouse [stock 50], Keyboard [stock 30], and Order #1 in 'Packed' status).
6. **Documentation:** `docs/AUDIT.md` (comprehensive Phase 1 audit report).

### What Is Missing
1. **Shared Logic Module:** No decoupling layer (e.g. `store.py` or `services.py`) exists. `main.py` mixes console `input()`/`print()` directly with database queries and DSA manipulations.
2. **Web Backend:** No Flask application (`app.py`), routes, session management, or CSRF protection exist.
3. **Web Frontend:** No templates (`templates/`), no CSS design system (`static/css/style.css`), no self-hosted font files (`static/fonts/`), and no client-side interactions exist.
4. **Automated Test Suite:** No `tests/` directory or `pytest` configurations exist.
5. **Database Migration Pipeline:** No `migrations/` directory, forward migration scripts, or rollback scripts exist.
6. **Configuration & Security:** No `.env`, `.env.example`, or dynamic environment-based secret/database configuration exists.
7. **Production & Administration Scripts:** No `create_admin.py`, no `wsgi.py`, and no isolated demo seed script exists.
8. **Git Repository:** Git is **not initialized** (`.git` does not exist). No `.gitignore` exists.

### Contradictions with `docs/AUDIT.md`
- **Zero Contradictions Found:** The codebase remains identical to the state evaluated during the Phase 1 audit. No subsequent phases (Plan, Backend Refactoring, Web Frontend) have been implemented yet.

---

## 2. Status of the 14 Known Audit Issues in Current Code

| # | Known Issue Description | Current Status | File & Line | Evidence in Code |
|---|---|---|---|---|
| **1** | `get_total_price()` reads `'price'`/`'quantity'`, but `__main__` passes `"Price"`/`"Quantity"`. | **NOT FIXED** | `data_structures.py:L25` vs `L86-87` | Lines 86–87 still pass capitalized keys `"Price"` and `"Quantity"`, raising `KeyError` when running `python data_structures.py`. |
| **2** | `init_db.py` f-string uses nested double quotes (fails on Python < 3.12). | **NOT FIXED** | `init_db.py:L72` | Line 72 still contains `print(f"{"ID":<4}{"Name":<30} ...")`. |
| **3** | Schema and seed discrepancy between `init_db.py` (10 products) and `main.py` (3 products). | **NOT FIXED** | `init_db.py:L45` vs `main.py:L60` | Dual DDL and separate seed logic still exist across both files without a canonical source. |
| **4** | Queue starvation in `advance_dispatch()` (head order blocks all behind it until Delivered). | **NOT FIXED** | `main.py:L149-174` | `self.dispatch_queue.peek()` is still held without round-robin progression or stage rotation. |
| **5** | `_sync_queue()` includes `Cancelled` orders (`status != 'Delivered'`). | **NOT FIXED** | `main.py:L68` | Query still reads `WHERE status != 'Delivered'`. |
| **6** | `DispatchQueue.dequeue()` uses list `pop(0)` ($O(n)$ time). | **NOT FIXED** | `data_structures.py:L41` | Still uses `self.queue.pop(0)`. |
| **7** | Binary search re-sorts array before each lookup in $O(n \log n)$. | **NOT FIXED** | `main.py:L83, L235` | Still executes `sorted(products, key=lambda x: x['id'])` prior to binary search. |
| **8** | Cart stock check ignores cumulative in-cart quantity. | **NOT FIXED** | `main.py:L88-97` | Adds separate entries to stack without validating total quantity against inventory. |
| **9** | Order cancellation is unsupported (no status transition, no restocking, no queue eviction). | **NOT FIXED** | `main.py` | No cancellation functions exist in the codebase. |
| **10** | `checkout()` is hardcoded to `customer_id=1` with no user authentication or password hashing. | **NOT FIXED** | `main.py:L106, L269` | Default parameter `customer_id=1` remains hardcoded in CLI checkout. |
| **11** | Product search only supports numeric ID, not product name. | **NOT FIXED** | `main.py:L233-245` | No name/substring search algorithm exists. |
| **12** | Stage "Payment Confirmed" implies external gateway processing without realistic context. | **NOT FIXED** | `data_structures.py:L66` | Milestone list still contains `"Payment Confirmed"`. |
| **13** | Prices stored as `REAL` (floating-point IEEE 754) prone to rounding inaccuracies. | **NOT FIXED** | `init_db.py:L16`, `main.py:L33` | Database schema still uses `REAL` for `Price` and `Total_Amount`. |
| **14** | `PRAGMA foreign_keys = ON` not standardized for web request lifecycles. | **PARTLY FIXED** | `main.py:L10`, `init_db.py:L4` | Present in CLI scripts, but no web framework or connection lifecycle manager exists yet. |

---

## 3. Comprehensive Verification Test Plan (Parts B through E)

This test plan defines how every architectural, algorithmic, database, frontend, and deployment requirement will be verified.

### Part B: Backend and Database Verification Plan
| Category | Requirement / Feature | Verification Method | Execution Details & Test Vectors |
|---|---|---|---|
| **Transactions & Stock** | Checkout Success | `pytest` | Valid cart checkout commits order, generates order items, decrements stock by exact quantity, returns order ID. |
| **Transactions & Stock** | Insufficient Stock Checkout | `pytest` | Quantity requested > available stock fails before commit; zero DB modification. |
| **Transactions & Stock** | Transaction Rollback on Failure | `pytest` | Inject DB error mid-transaction; verify zero orphan records and stock remains intact. |
| **Cart Validation** | Cumulative Stock Limit | `pytest` | Add 4 items of stock 5, then add 4 more; second add must be rejected; cart quantity must equal 4. |
| **Cancellation** | Cancel Order & Restock | `pytest` | Cancel order in 'Placed' stage; verify DB status is 'Cancelled', stock is restored, and order is evicted from queue. |
| **Cancellation** | Prohibited Stage Cancellation | `pytest` | Attempt cancellation on 'Dispatched' or 'Delivered' orders; verify rejection. |
| **Queue Operations** | FIFO Order & No Starvation | `pytest` | Enqueue orders A, B, C; advancing stage of A must allow B and C to advance without waiting for A to deliver. |
| **Queue Operations** | Cancelled Orders Excluded | `pytest` | `_sync_queue` with orders in Placed, Cancelled, Delivered; verify only active non-cancelled orders are loaded. |
| **Queue Operations** | $O(1)$ Time Complexity | `pytest` / Code Analysis | Verify dequeue operates in true $O(1)$ without list shifting. |
| **Algorithms** | Binary Search by ID | `pytest` | Test existing ID, non-existent ID, boundary low/high IDs, and verify correct item dictionary returned. |
| **Algorithms** | Linear Substring Search by Name | `pytest` | Search case-insensitive substring ("lap" -> "Laptop", "KEY" -> "Keyboard", "xyz" -> empty list). |
| **Algorithms** | Merge Sort by Price | `pytest` | Unsorted list sorted ascending; verify stable ordering and $O(n \log n)$ divide-and-conquer logic. |
| **Linked List** | Stage Traversal | `pytest` | Verify `get_next_stage` across every checkpoint; verify terminal stage returns `None`. |
| **Authentication** | Customer Registration & Login | `pytest` | Register unique email with password; verify password hash stored (not plaintext); authenticate with valid password. |
| **Authentication** | Duplicate Email & Wrong Password | `pytest` | Attempt duplicate registration (rejects); attempt login with incorrect password (rejects). |
| **Security & Auth** | Admin Route Authorization | `pytest` | Anonymous request to `/admin/queue` redirects/returns 403; Customer session returns 403; Admin succeeds. |
| **Security & Auth** | CSRF Protection | `pytest` | POST request without CSRF token returns 400 Bad Request; valid token succeeds. |
| **Security & Auth** | SQL Injection Resistance | `pytest` | Search query `' OR '1'='1` and login credentials `' OR 1=1 --` are treated as literal strings. |
| **Database Health** | Pragmas & Constraints | SQLite Script on COPY | Run `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, verify FK enforcement on every web connection. |
| **Database Health** | Migration Idempotence | Migration Test on COPY | Apply migrations 001 to latest; verify row counts before and after; test rollback scripts down to base. |
| **Concurrency** | Simultaneous Checkout Race Condition | `pytest` / Multi-threading | Two threads attempt to checkout the last available unit of product simultaneously; exactly 1 succeeds, stock reaches 0, never negative. |
| **CLI Compatibility** | `main.py` CLI Execution | Automated Subprocess / Manual | Run all 9 CLI options using the shared business logic layer; verify parity with web actions. |
| **Currency** | Formatting Consistency | Code & UI Inspection | Confirm singular, consistent currency format across database, CLI, and web UI. |

---

### Part C: Frontend Verification Plan
| Area | Flow / Requirement | Verification Method | Execution Details & Viewports |
|---|---|---|---|
| **Customer Flow** | Full E2E Purchase Cycle | Browser Automation / Playwright / Manual | Register $\rightarrow$ Login $\rightarrow$ Search Name $\rightarrow$ Sort by Price $\rightarrow$ Product Detail $\rightarrow$ Add to Cart $\rightarrow$ Checkout $\rightarrow$ Order Track $\rightarrow$ Cancel $\rightarrow$ Logout. |
| **Warehouse Flow** | Admin Dispatch Pipeline | Browser Automation / Playwright / Manual | Admin Login $\rightarrow$ View Queue $\rightarrow$ Advance Multi-order Stages $\rightarrow$ View Inventory $\rightarrow$ Verify Customer Route Isolation. |
| **Responsive Design** | Layout & Readability at 3 Breakpoints | Browser Screenshots | Test at Desktop (1440px), Tablet (768px), and Mobile (390px). Verify no horizontal scrollbars, legible text, and accessible tap targets. |
| **Edge States** | Empty & Boundary Conditions | Browser Walkthrough | Empty cart, empty search results, out-of-stock badge, invalid form inputs with server validation messages, 404 and 500 handlers. |
| **Accessibility (a11y)** | Keyboard Navigation & Focus | Browser Manual Pass | Tab through all inputs, buttons, and links without mouse; check visible focus indicators; ensure semantic HTML and labeled inputs. |
| **Design Integrity** | "NOT ALLOWED" Compliance | Visual & Code Review | Zero gradients, zero glassmorphism/blur, no emoji icons, no font icon libraries, restrained color tokens, no em dashes in copy. |
| **Assets & Privacy** | Self-hosted Assets & Legal Copy | Network Tab & Inspection | Zero third-party CDN requests; fonts loaded from `static/fonts/`; Privacy & Terms pages declare student project scope honestly. |

---

### Part D: Production Readiness Plan
| Target Area | Item | Verification Method | Details |
|---|---|---|---|
| **Configuration** | Environment Isolation | Manual & Subprocess | Missing `SECRET_KEY` in production halts startup with descriptive message; `.env.example` provides template. |
| **Sessions** | Secure Cookie Attributes | HTTP Header Check | Cookies configured with `HttpOnly`, `SameSite=Lax`, and `Secure` (in HTTPS context). Basic failed login rate-limiting. |
| **Admin Setup** | Interactive CLI Bootstrap | Terminal Execution | `python create_admin.py` prompts for credentials interactively without hardcoded passwords. |
| **WSGI Entry** | `wsgi.py` Server Entry Point | Execution Test | WSGI application callable exposes Flask instance with locked dependencies in `requirements.txt`. |
| **State Consistency** | Multi-process Queue Parity | Architectural Review & Test | Single-process mode documented and tested, or queue re-hydrated dynamically from database to prevent state divergence. |
| **Health & Backup** | Health Check & Database Backups | HTTP / PowerShell | `/health` route returns DB connectivity status; backup and restore PowerShell scripts verified against data copy. |

---

### Part E: Deployment Verification Plan
| Step | Target | Method | Verification Evidence |
|---|---|---|---|
| **Platform Analysis** | Host Evaluation | Documentation Search & Review | Author `docs/DEPLOY_OPTIONS.md` analyzing 2–3 platforms for SQLite persistence, HTTPS, limits, and pricing. |
| **Deployment Runbook** | Step-by-Step Guide | Markdown Authoring | `docs/DEPLOY.md` with explicit commands, secret configuration instructions, and zero stored user secrets. |
| **Data Sanitation** | Demo Database Guarantee | Database Inspection | Deployment uses canonical demo seed; confirm student data from `ecommerce.db` is never committed or uploaded. |
| **Live Smoke Test** | Deployed Application Audit | Live Web Navigation & Report | Validate SSL padlock, health check, registration, order lifecycle, queue processing, and responsive rendering on live URL; document in `docs/DEPLOY_REPORT.md`. |

---

## 4. Next Actions (Awaiting User Sign-off)

1. User decision on OneDrive migration vs remaining in current workspace.
2. User decision on initial Git repository initialization and `.gitignore` setup.
3. User approval of this State Check and Verification Test Plan to proceed to **Part B: Backend and Database Implementation & Verification**.
