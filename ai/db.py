"""
InsightIQ — Shared DB Connection Helper (ml package)
=======================================================
Same helper as analytics/db.py, duplicated here so ml/ has no import
dependency on the analytics/ package — the two phases stay independently
runnable, which matters if you're grading/demoing them separately.
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
