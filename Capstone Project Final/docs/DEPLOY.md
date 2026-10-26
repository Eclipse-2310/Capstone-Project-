# Production Deployment Runbook (PythonAnywhere & WSGI)

**Target Host:** PythonAnywhere (Recommended for Persistent SQLite)  
**Security Guarantee:** Private student credentials from `ecommerce.db` are never uploaded. Deployment initializes a fresh database using `seed_demo.py`.

---

## Step-by-Step Deployment Instructions

### Step 1: Create a Free Account
1. Open [pythonanywhere.com](https://www.pythonanywhere.com) and click **Create a Beginner Account**.
2. Choose a username (your live URL will be `https://<username>.pythonanywhere.com`).
3. Confirm your email address.

### Step 2: Open a Bash Console and Clone the Repository
1. On your PythonAnywhere Dashboard, navigate to the **Consoles** tab and click **Bash**.
2. Clone your GitHub repository (or upload your project archive):
   ```bash
   git clone -b redesign <your-github-repo-url> capstone
   cd capstone
   ```

### Step 3: Set Up a Python 3.10+ Virtual Environment
Run the following commands inside the Bash console:
```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Build the Demo Database
Initialize the fresh, sanitized demo database (preserves privacy, seeds 10 products and demo accounts):
```bash
python seed_demo.py ecommerce_prod.db
```

### Step 5: Interactively Bootstrap the Administrator Account
Run the interactive admin creation tool. You will be prompted to type your secret password:
```bash
DATABASE_PATH=ecommerce_prod.db python create_admin.py
```

### Step 6: Configure the Web App in PythonAnywhere Dashboard
1. Go to the **Web** tab on PythonAnywhere and click **Add a new web app**.
2. Select **Manual configuration (including virtualenvs)** and choose **Python 3.10**.
3. Under **Virtualenv**, enter the path to your virtual environment:
   `/home/<username>/capstone/.venv`
4. Under **Code**, set **Source code** to:
   `/home/<username>/capstone`
5. Click on the link to edit the **WSGI configuration file** (`/var/www/<username>_pythonanywhere_com_wsgi.py`).
6. Replace the entire contents of that file with:
   ```python
   import sys
   import os

   path = '/home/<username>/capstone'
   if path not in sys.path:
       sys.path.insert(0, path)

   # Set Environment Variables
   os.environ['DATABASE_PATH'] = '/home/<username>/capstone/ecommerce_prod.db'
   os.environ['SECRET_KEY'] = 'generate-a-random-32-char-string-here'
   os.environ['FLASK_ENV'] = 'production'

   from wsgi import application
   ```
   *(Replace `<username>` with your actual PythonAnywhere username)*.
7. Save the file.

### Step 7: Reload and Verify Live URL
1. Return to the **Web** tab and click the green **Reload <username>.pythonanywhere.com** button.
2. Open your public URL: `https://<username>.pythonanywhere.com`.
3. Check the health route: `https://<username>.pythonanywhere.com/health`.
4. Log in as staff using the admin credentials you created in Step 5.
