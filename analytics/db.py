"""
InsightIQ — Shared DB Connection Helper
==========================================
Every analytics module (sales.py, customers.py, products.py, operations.py)
imports get_engine() from here instead of each building its own connection.
One place to change the connection logic; every module stays a thin SQL
wrapper.
"""

import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_BASE_DIR, ".env"))

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL not set — check your .env file (see Day 0 setup guide).")
        _engine = create_engine(url)
    return _engine
