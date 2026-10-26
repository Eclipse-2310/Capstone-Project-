# Production Deployment Options Evaluation

**Project:** E-Commerce Dispatch and Inventory Management  
**Stack:** Python 3.10+, Flask, SQLite3, Jinja2  
**Constraint:** Must support persistent SQLite storage so that customer accounts, live stock levels, and order milestones persist across server restarts.

---

## Comparative Platform Analysis

| Platform | Persistent Disk? | SQLite Supported? | Free Tier Limits & Policies | HTTPS / SSL | Setup Effort | Recommendation |
|---|---|---|---|---|---|---|
| **PythonAnywhere** | **Yes (Native persistent Linux storage)** | **Yes (Full native support)** | 512 MB storage, 1 web app (`user.pythonanywhere.com`), requires 1-click renewal every 3 months. No outbound internet to non-allowlist sites on free tier (does not affect local SQLite). | Automatic SSL certificate on custom subdomain. | **Low** (Simple web dashboard, git clone, bash console). | **RECOMMENDED** |
| **Render.com** | **No on free tier** (Free instances use ephemeral disks; files reset on sleep/deploy). Paid disk costs $1+/month. | Only on paid tier ($7/mo service + $0.25/GB disk). Free tier resets SQLite on restart. | Free instance spins down after 15 min idle; 50-second cold start; ephemeral filesystem wipes SQLite changes. | Automatic Let's Encrypt SSL. | **Moderate** (GitHub auto-deploy). | Not recommended for free SQLite. |
| **Fly.io** | **Yes (via Fly Volumes)** | **Yes** (attach persistent volume to `/data/ecommerce.db`). | Free allowance includes up to 3GB persistent volume storage; requires credit card for account verification. | Automatic Wildcard SSL. | **Moderate / High** (Requires `flyctl` CLI tool and Dockerfile configuration). | Good technical alternative if card is available. |

---

## Detailed Evaluation

### Option 1: PythonAnywhere (Recommended)
- **Persistent Filesystem:** Native Linux user home directory (`/home/username/`). Files and SQLite databases do not vanish on reboot or reload.
- **SQLite Viability:** Ideal. Single-worker WSGI process operates cleanly with SQLite write locks.
- **Cost:** 100% Free.
- **Setup Complexity:** Lowest. We clone the repository on PythonAnywhere, create a virtual environment, run `seed_demo.py`, and point the web configuration to `wsgi.py`.

### Option 2: Render.com
- **Limitation:** The free tier uses containerized ephemeral disks. Every time the free server spins down or a commit is deployed, the container re-images, resetting `ecommerce.db` to its initial git state and erasing newly registered users and placed orders.
- **Conclusion:** Violates our persistence acceptance criteria on the free tier unless a paid Persistent Disk is added.

### Option 3: Fly.io
- **Capabilities:** Excellent modern container runner with persistent block volumes.
- **Limitation:** Requires installing the `flyctl` command-line utility, authoring a custom Dockerfile, and entering payment card details for spam prevention during account registration.

---

## QA Recommendation
We recommend **PythonAnywhere** for your viva demonstration. It provides genuine filesystem persistence for SQLite, zero ephemeral data loss, free subdomains with HTTPS, and straightforward configuration via `wsgi.py`.
