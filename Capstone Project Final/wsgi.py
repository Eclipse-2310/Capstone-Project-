"""
WSGI Application Entry Point
Production web server gateway for Gunicorn / Waitress / PythonAnywhere.

Usage:
    gunicorn --workers=1 wsgi:application
    waitress-serve --port=5000 wsgi:application
"""

import os
import sys
import logging

# Ensure project root is in Python sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app as application
import database

# Production Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ecommerce_cms")

# Production Security Verification
if os.getenv("FLASK_ENV") == "production" or os.getenv("ENV") == "production":
    secret = os.getenv("SECRET_KEY")
    if not secret or secret == "capstone-secret-dev-key-change-in-prod-xyz123":
        logger.error("FATAL: Insecure or missing SECRET_KEY in production environment.")
        raise RuntimeError("Production requires a strong, unique SECRET_KEY environment variable.")
    application.config['SESSION_COOKIE_SECURE'] = True
    logger.info("Production configuration loaded: Secure cookies enabled.")
else:
    logger.info("Development configuration loaded.")

# Initialize database schema and migrations on server start
with application.app_context():
    db_path = application.config['DATABASE_PATH']
    conn = database.get_db_connection(db_path)
    database.init_schema(conn)
    database.apply_migrations(conn)
    conn.close()
    logger.info(f"Database initialized and verified at: {db_path}")

if __name__ == "__main__":
    application.run()
