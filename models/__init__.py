"""Database helpers (SQLite). All queries use placeholders (%s) so user input can
never be injected into SQL. The helpers below turn %s into SQLite's ? marker, so the
rest of the code stays simple."""
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from config import Config

# Read DATE / TIMESTAMP columns back as Python date / datetime objects
sqlite3.register_converter("DATE", lambda b: date.fromisoformat(b.decode()))
sqlite3.register_converter("TIMESTAMP", lambda b: datetime.fromisoformat(b.decode()))


def _dict_row(cursor, row):
    return {col[0]: val for col, val in zip(cursor.description, row)}


def get_conn():
    conn = sqlite3.connect(Config.DB_PATH, timeout=10, isolation_level=None,
                           detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = _dict_row
    conn.execute("PRAGMA foreign_keys = ON")      # enforce foreign keys
    conn.create_function("CURDATE", 0, lambda: date.today().isoformat())
    conn.create_function("NOW", 0, lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    return conn


def _value(v):
    if isinstance(v, datetime):
        return v.isoformat(sep=" ")
    if isinstance(v, date):
        return v.isoformat()
    return v


def _prepare(sql, params):
    if isinstance(params, dict):
        return re.sub(r"%\((\w+)\)s", r":\1", sql), {k: _value(v) for k, v in params.items()}
    return sql.replace("%s", "?"), tuple(_value(v) for v in params)


class Cursor:
    """Thin wrapper so every query goes through _prepare()."""
    def __init__(self, cur):
        self._cur = cur

    def execute(self, sql, params=()):
        self._cur.execute(*_prepare(sql, params))
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    @property
    def rowcount(self):
        return self._cur.rowcount


def query(sql, params=(), one=False):
    """Run a SELECT. Returns a list of dicts (or one dict / None if one=True)."""
    conn = get_conn()
    try:
        rows = Cursor(conn.cursor()).execute(sql, params).fetchall()
        return (rows[0] if rows else None) if one else rows
    finally:
        conn.close()


def scalar(sql, params=()):
    """Return the first column of the first row (handy for COUNT/SUM)."""
    row = query(sql, params, one=True)
    return list(row.values())[0] if row else None


@contextmanager
def transaction():
    """Use `with transaction() as cur:` - commits on success, rolls back on error."""
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")        # lock the file so two users cannot clash
        yield Cursor(conn.cursor())
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def init_db():
    """Create library.db from database.sql the first time the app runs."""
    if os.path.exists(Config.DB_PATH):
        return
    conn = sqlite3.connect(Config.DB_PATH)
    try:
        with open(Config.SCHEMA_FILE, encoding="utf-8") as f:
            conn.executescript(f.read())
    except Exception:
        conn.close()
        os.remove(Config.DB_PATH)             # do not leave a half-built database behind
        raise
    conn.close()
