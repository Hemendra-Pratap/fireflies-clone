from pathlib import Path
import sqlite3
import sys

# Ensure backend root is on sys.path so app module can be imported regardless of CWD
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings

db_url = settings.database_url
print("DB URL:", db_url)

# Extract file path from sqlite:/// URL
if db_url.startswith("sqlite:///"):
    db_path = db_url[len("sqlite:///"):]
else:
    db_path = db_url

con = sqlite3.connect(db_path)
cur = con.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("tables:", cur.fetchall())
try:
    cur.execute("SELECT version_num FROM alembic_version")
    print("alembic_version:", cur.fetchone())
except Exception as e:
    print("alembic_version query error:", e)
con.close()

