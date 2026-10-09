"""Application settings. The database is a single SQLite file (library.db) that is
created automatically the first time you run the app - nothing to install."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # SQLite database file and the script used to create it on first run
    DB_PATH = os.path.join(BASE_DIR, "library.db")
    SCHEMA_FILE = os.path.join(BASE_DIR, "database.sql")

    # Library rules
    FINE_PER_DAY = 5             # rupees charged per overdue day
    LOAN_DAYS = 14               # days a book can be kept
    MAX_ACTIVE_BORROWINGS = 3    # books one student may hold at a time
    LOW_STOCK_LIMIT = 2          # "low availability" alert threshold
