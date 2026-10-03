"""
Shared pytest setup: puts every package folder on sys.path so test files
can `import clean`, `import copilot`, `import sales`, etc. exactly the
way app/streamlit_app.py and api/main.py do.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for pkg in ["data_pipeline", "analytics", "ml", "ai"]:
    path = os.path.join(BASE_DIR, pkg)
    if path not in sys.path:
        sys.path.insert(0, path)
