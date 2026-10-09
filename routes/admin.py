"""Admin API: dashboard, librarians, categories, users."""
from flask import Blueprint, session, jsonify
from models import query, scalar, transaction, user as user_model
from models.borrowing import list_borrowings
from services.book_service import make_table, most_borrowed_table, recent_table, low_stock_table
from services.fine_service import fine_rows
from .auth import login_required, get_json, to_int

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@bp.get("/dashboard")
@login_required("admin")
def dashboard():
    cards = [
        {"label": "Total users", "value": scalar("SELECT COUNT(*) FROM users")},
        {"label": "Students", "value": scalar("SELECT COUNT(*) FROM students")},
        {"label": "Librarians", "value": scalar("SELECT COUNT(*) FROM librarians")},
        {"label": "Total books", "value": scalar("SELECT COUNT(*) FROM books")},
        {"label": "Borrowed books", "value": scalar("SELECT COUNT(*) FROM borrowings WHERE status<>'returned'")},
        {"label": "Overdue books", "value": len(list_borrowings(status="overdue"))},
        {"label": "Total fines", "value": f"₹{sum(r['amount'] for r in fine_rows()):.2f}"},
    ]
    recent = list_borrowings()[:8]
    tables = [
        make_table("Recent transactions", ["Student", "Book", "Issued", "Due", "Status"],
                   [[r["student_name"], r["title"], r["issue_date"], r["due_date"], r["status"].replace("_", " ")]
                    for r in recent]),
        low_stock_table(), most_borrowed_table(), recent_table(),
    ]
    return jsonify(cards=cards, tables=tables)


# ---------- librarians ----------
@bp.get("/librarians")
@login_required("admin")
def librarians():
    return jsonify(user_model.list_accounts("librarian"))


@bp.post("/librarians")
@login_required("admin")
def add_librarian():
    user_model.create_account("librarian", get_json())
    return jsonify(message="Librarian added"), 201


@bp.put("/librarians/<int:pid>")
@login_required("admin")
def edit_librarian(pid):
    user_model.update_account("librarian", pid, get_json())
    return jsonify(message="Librarian updated")


@bp.delete("/librarians/<int:pid>")
@login_required("admin")
def remove_librarian(pid):
    user_model.delete_account("librarian", pid)
    return jsonify(message="Librarian deleted")


# ---------- categories ----------
@bp.post("/categories")
@login_required("admin")
def add_category():
    d = get_json(["name"])
    with transaction() as cur:
        cur.execute("INSERT INTO categories (name, description) VALUES (%s,%s)",
                    (d["name"].strip(), (d.get("description") or "").strip() or None))
    return jsonify(message="Category added"), 201


@bp.put("/categories/<int:cid>")
@login_required("admin")
def edit_category(cid):
    d = get_json(["name"])
    with transaction() as cur:
        cur.execute("UPDATE categories SET name=%s, description=%s WHERE id=%s",
                    (d["name"].strip(), (d.get("description") or "").strip() or None, cid))
    return jsonify(message="Category updated")


@bp.delete("/categories/<int:cid>")
@login_required("admin")
def remove_category(cid):
    with transaction() as cur:
        cur.execute("DELETE FROM categories WHERE id=%s", (cid,))
        if cur.rowcount == 0:
            raise ValueError("Category not found")
    return jsonify(message="Category deleted")


# ---------- users ----------
@bp.get("/users")
@login_required("admin")
def users():
    return jsonify(query("SELECT id, username, full_name, email, role, is_active, created_at "
                         "FROM users ORDER BY role, full_name"))


@bp.put("/users/<int:uid>/toggle")
@login_required("admin")
def toggle_user(uid):
    if uid == session["user_id"]:
        raise ValueError("You cannot disable your own account")
    with transaction() as cur:
        cur.execute("UPDATE users SET is_active = 1 - is_active WHERE id=%s", (uid,))
        if cur.rowcount == 0:
            raise ValueError("User not found")
    return jsonify(message="User status changed")
