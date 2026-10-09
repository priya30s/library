"""Users and their role profiles (students / librarians)."""
import re
from werkzeug.security import generate_password_hash, check_password_hash
from . import query, transaction

# role -> (profile table, extra columns stored there)
PROFILE = {
    "student": ("students", ["roll_no", "department"]),
    "librarian": ("librarians", ["employee_id"]),
}


def valid_email(email):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or ""))


def check_new_password(pw):
    if len(pw or "") < 6:
        raise ValueError("Password must be at least 6 characters")


def authenticate(username, password):
    u = query("SELECT * FROM users WHERE username=%s", (username,), one=True)
    if u and u["is_active"] and check_password_hash(u["password_hash"], password):
        return u
    return None


def profile_id(user_id, role):
    """id of the row in students/librarians for this user (None for admin)."""
    if role not in PROFILE:
        return None
    row = query(f"SELECT id FROM {PROFILE[role][0]} WHERE user_id=%s", (user_id,), one=True)
    return row["id"] if row else None


def get_user(user_id):
    u = query("SELECT id,username,email,full_name,phone,role,is_active,created_at "
              "FROM users WHERE id=%s", (user_id,), one=True)
    if u and u["role"] in PROFILE:
        table, extra = PROFILE[u["role"]]
        u.update(query(f"SELECT {','.join(extra)} FROM {table} WHERE user_id=%s",
                       (user_id,), one=True) or {})
    return u


def update_own_profile(user_id, data):
    name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip()
    if not name:
        raise ValueError("Full name is required")
    if not valid_email(email):
        raise ValueError("Enter a valid email address")
    with transaction() as cur:
        cur.execute("UPDATE users SET full_name=%s, email=%s, phone=%s WHERE id=%s",
                    (name, email, (data.get("phone") or "").strip() or None, user_id))


def change_password(user_id, current, new):
    check_new_password(new)
    with transaction() as cur:
        cur.execute("SELECT password_hash FROM users WHERE id=%s", (user_id,))
        row = cur.fetchone()
        if not row or not check_password_hash(row["password_hash"], current or ""):
            raise ValueError("Current password is incorrect")
        cur.execute("UPDATE users SET password_hash=%s WHERE id=%s",
                    (generate_password_hash(new), user_id))


def _clean(role, data, creating):
    extra = PROFILE[role][1]
    d = {k: str(data.get(k) or "").strip() for k in ["full_name", "username", "email", "phone"] + extra}
    if not d["full_name"]:
        raise ValueError("Full name is required")
    if not valid_email(d["email"]):
        raise ValueError("Enter a valid email address")
    if not d[extra[0]]:
        raise ValueError(extra[0].replace("_", " ").title() + " is required")
    if creating:
        if len(d["username"]) < 3:
            raise ValueError("Username must be at least 3 characters")
        check_new_password(data.get("password"))
    elif data.get("password"):
        check_new_password(data.get("password"))
    return d


def list_accounts(role):
    table, extra = PROFILE[role]
    cols = ",".join(f"p.{c}" for c in extra)
    return query(f"SELECT p.id, u.username, u.email, u.full_name, u.phone, u.is_active, {cols} "
                 f"FROM {table} p JOIN users u ON u.id=p.user_id ORDER BY u.full_name")


def create_account(role, data):
    d = _clean(role, data, creating=True)
    table, extra = PROFILE[role]
    with transaction() as cur:
        cur.execute("INSERT INTO users (username,email,password_hash,full_name,phone,role) "
                    "VALUES (%s,%s,%s,%s,%s,%s)",
                    (d["username"], d["email"], generate_password_hash(data["password"]),
                     d["full_name"], d["phone"] or None, role))
        cols = ",".join(extra)
        marks = ",".join(["%s"] * len(extra))
        cur.execute(f"INSERT INTO {table} (user_id,{cols}) VALUES (%s,{marks})",
                    [cur.lastrowid] + [d[c] or None for c in extra])


def update_account(role, pid, data):
    d = _clean(role, data, creating=False)
    table, extra = PROFILE[role]
    with transaction() as cur:
        cur.execute(f"SELECT user_id FROM {table} WHERE id=%s", (pid,))
        row = cur.fetchone()
        if not row:
            raise ValueError("Record not found")
        cur.execute("UPDATE users SET full_name=%s,email=%s,phone=%s WHERE id=%s",
                    (d["full_name"], d["email"], d["phone"] or None, row["user_id"]))
        if data.get("password"):
            cur.execute("UPDATE users SET password_hash=%s WHERE id=%s",
                        (generate_password_hash(data["password"]), row["user_id"]))
        sets = ",".join(f"{c}=%s" for c in extra)
        cur.execute(f"UPDATE {table} SET {sets} WHERE id=%s", [d[c] or None for c in extra] + [pid])


def delete_account(role, pid):
    table = PROFILE[role][0]
    with transaction() as cur:
        cur.execute(f"SELECT user_id FROM {table} WHERE id=%s", (pid,))
        row = cur.fetchone()
        if not row:
            raise ValueError("Record not found")
        cur.execute("DELETE FROM users WHERE id=%s", (row["user_id"],))  # profile row cascades
