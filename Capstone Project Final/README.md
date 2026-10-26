# E-Commerce Dispatch and Inventory Management

An academic Capstone Project demonstrating **Data Structures (Stack, Queue, Singly Linked List)**, **Algorithms (Merge Sort, Binary Search, Linear Search)**, and **Database Management Systems (ACID SQL Transactions, Foreign Key Enforcement, Normalization)** in Python.

Provides both an interactive **Command-Line Interface (CLI)** and a modern **Flask Web Application** sharing a unified, decoupled business logic layer.

---

## Technical Specifications
- **Operating System:** Windows (PowerShell commands provided throughout)
- **Minimum Python Version:** **Python 3.10 or newer** (tested on Python 3.13.7)
- **Database Engine:** SQLite 3 (`ecommerce.db`)
- **Web Stack:** Flask 3.1.3, Jinja2, Vanilla CSS with design tokens, self-hosted WOFF2 fonts
- **Test Framework:** Pytest 9.1.1 (28 automated integration and concurrency tests)

---

> [!WARNING]
> **OneDrive Advisory**: If this project folder is located inside Microsoft OneDrive, real-time cloud synchronization can cause file-locking deadlocks on SQLite databases and `.git` indices. For viva presentations and development, it is recommended to work in a local non-synced directory (e.g. `C:\Projects\Capstone`).

---

## Quick Start (PowerShell Instructions)

### 1. Set Up Environment & Install Dependencies
Open PowerShell in the project directory:

```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Upgrade pip and install pinned dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Initialize Database & Canonical Seed
Ensure the database schema, migrations, and canonical 10-product catalog are initialized:

```powershell
python init_db.py
```

### 3. Run the Automated Test Suite (All 28 Tests)
Execute the complete test suite verifying DSA, database transactions, concurrency, security, and web routes:

```powershell
python -m pytest -v
```

---

## Running the Application Interfaces

### A. Run the Interactive Command-Line Interface (CLI)
```powershell
python main.py
```
**Available CLI Features:**
1. Browse Catalog (Sorted by Price via Merge Sort)
2. Search Product by ID (Binary Search in $O(\log n)$)
3. Search Product by Name (Linear Substring Search)
4. Add Item to Cart (Push to Stack LIFO with cumulative inventory check)
5. Undo Last Cart Item (Pop from Stack LIFO)
6. View Current Cart
7. Checkout (Atomic SQL Transaction + Enqueue to FIFO Dispatch Queue)
8. Process Next Dispatch Order (FIFO Round-Robin stage advancement)
9. Track Order Status (SQL JOIN query + Milestone Pipeline display)
10. Cancel Order (Restores warehouse stock in atomic transaction)
11. Switch / Register User Account
12. Exit

---

### B. Run the Web Application
```powershell
python app.py
```
Open your web browser and navigate to:  
👉 **`http://127.0.0.1:5000`**

#### Default Demo Credentials:
- **Student Customer:** `125anant6027@sjcem.edu.in` / `student123`
- **Warehouse Staff Admin:** `admin@sjcem.edu.in` / `admin123`

---

## Production & Administrative Utilities

### 1. Interactively Bootstrap a New Staff Admin Account
To create or promote an admin account without hardcoding credentials:
```powershell
python create_admin.py
```

### 2. Build a Sanitized Demo Database (For Public Deployment)
To generate a sanitized demo database that guarantees private student data is never exposed:
```powershell
python seed_demo.py ecommerce_demo.db
```

### 3. Health Check Endpoint
The web application provides a real-time health endpoint at:
`http://127.0.0.1:5000/health` (returns JSON status confirming SQLite connection and foreign key pragmas).

---

## Academic Documentation & Viva Preparation

Detailed documentation files are available in the [`docs/`](docs/) directory:
- [**docs/VIVA_MAP.md**](docs/VIVA_MAP.md): Comprehensive traceability matrix mapping every feature to its DSA complexity ($O(n \log n)$, $O(\log n)$, $O(1)$) and SQL queries, plus viva defense Q&A.
- [**docs/AUDIT.md**](docs/AUDIT.md): Original Phase 1 system audit documenting the 14 baseline flaws.
- [**docs/VERIFY_REPORT.md**](docs/VERIFY_REPORT.md): Complete verification log confirming resolution of all defects with automated test evidence.
- [**docs/DEPLOY.md**](docs/DEPLOY.md): Production deployment guide for PythonAnywhere and persistent SQLite hosting.
- [**docs/DEPLOY_OPTIONS.md**](docs/DEPLOY_OPTIONS.md): Evaluation of hosting platforms for SQLite persistence.
- [**docs/CHANGELOG.md**](docs/CHANGELOG.md): Technical changelog of all created and modified files.
- [**docs/CONTENT_GAPS.md**](docs/CONTENT_GAPS.md): Analysis of product imagery and typographic design decisions.
