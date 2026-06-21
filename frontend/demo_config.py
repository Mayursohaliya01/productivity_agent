"""
=============================================================================
DEMO MODE CONFIG — REMOVE BEFORE PRODUCTION
=============================================================================
DEMO_MODE shows demo credentials on the login page — it does NOT auto-login.
Users must enter username/password manually. Backend DEMO_SEED populates sample data.
=============================================================================
"""

import os

from dotenv import load_dotenv

load_dotenv()

# --- DEMO FLAGS ---
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in ("1", "true", "yes")

# --- DEMO LOGIN (must match backend/seed_demo.py) ---
DEMO_USERNAME = "Mayur"
DEMO_PASSWORD = "demo123"
