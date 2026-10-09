"""Librarian API (the admin may use these too): books, students, issue/return, fines, reports."""
from flask import Blueprint, session, jsonify, request
from models import query, scalar, transaction, book as book_model, user as user_model
from models.student import find_by_roll_no
from models.borrowing import list_borrowings
from config import Config
from services.book_service import (borrow_book, accept_return, make_table, most_borrowed_table,
                                   recent_table, low_stock_table)
from services.fine_service import fine_rows, outstanding
from .auth import login_required, get_json, to_int

bp = Blueprint("librarian", __name__, url_prefix="/api")
STAFF = ("librarian", "admin")


@bp.get("/librarian/dashboard")
@login_required("librarian")
def dashboard():
    cards = [
        {"label": "Total books", "value": scalar("SELECT COUNT(*) FROM books")},
        {"label": "Available copies", "value": int(scalar("SELECT COALESCE(SUM(available_copies),0) FROM books"))},
        {"label": "Borrowed books", "value": scalar("SELECT COUNT(*) FROM borrowings WHERE status<>'returned'")},
        {"label": "Overdue books", "value": len(list_borrowings(status="overdue"))},
        {"label": "Total students", "value": scalar("SELECT COUNT(*) FROM students")},
    ]
    overdue = list_borrowings(status="overdue")
    tables = [
        make_table("Overdue alerts", ["Student", "Book", "Due date", "Days late", "Fine"],
                   [[r["student_name"], r["title"], r["due_date"], r["days_overdue"], "₹%.2f" % r["fine"]]
                    for r in overdue]),
        low_stock_table(), most_borrowed_table(), recent_table(),
    ]
    return jsonify(cards=cards, tables=tables)


# ---------- books (add / edit / delete) ----------
@bp.post("/books")
@login_required(*STAFF)
def add_book():
    return jsonify(id=book_model.create(get_json()), message="Book added"), 201


@bp.put("/books/<int:book_id>")
@login_required(*STAFF)
def edit_book(book_id):
    book_model.update(book_id, get_json())
    return jsonify(message="Book updated")


@bp.delete("/books/<int:book_id>")
@login_required(*STAFF)
def remove_book(book_id):
    book_model.delete(book_id)
    return jsonify(message="Book deleted")


# ---------- students ----------
@bp.get("/librarian/students")
@login_required(*STAFF)
def students():
    return jsonify(user_model.list_accounts("student"))


@bp.post("/librarian/students")
@login_required(*STAFF)
def add_student():
    user_model.create_account("student", get_json())
    return jsonify(message="Student added"), 201


@bp.put("/librarian/students/<int:pid>")
@login_required(*STAFF)
def edit_student(pid):
    user_model.update_account("student", pid, get_json())
    return jsonify(message="Student updated")


@bp.delete("/librarian/students/<int:pid>")
@login_required(*STAFF)
def remove_student(pid):
    user_model.delete_account("student", pid)
    return jsonify(message="Student deleted")


# ---------- issue / return ----------
@bp.post("/librarian/issue")
@login_required(*STAFF)
def issue():
    d = get_json(["roll_no", "book_id"])
    student = find_by_roll_no(str(d["roll_no"]).strip())
    if not student:
        raise ValueError("No active student found with that roll number")
    result = borrow_book(student["id"], to_int(d["book_id"], "book"), issued_by=session["user_id"])
    return jsonify(message=f"Issued '{result['title']}' to {student['full_name']}. Due {result['due_date']}"), 201


@bp.get("/librarian/borrowings")
@login_required(*STAFF)
def borrowings():
    return jsonify(list_borrowings(status=request.args.get("status") or None))


@bp.post("/librarian/return/<int:borrowing_id>")
@login_required(*STAFF)
def accept(borrowing_id):
    r = accept_return(borrowing_id, session["user_id"])
    msg = "Book returned."
    if r["fine"] > 0:
        msg += f" Late by {r['days_overdue']} day(s) - fine ₹{r['fine']:.2f} recorded."
    return jsonify(message=msg)


# ---------- fines ----------
@bp.get("/librarian/fines")
@login_required(*STAFF)
def fines():
    rows = fine_rows()
    return jsonify(rows=rows, outstanding=outstanding(rows), fine_per_day=Config.FINE_PER_DAY)


@bp.post("/librarian/fines/<int:fine_id>/pay")
@login_required(*STAFF)
def pay_fine(fine_id):
    with transaction() as cur:
        cur.execute("UPDATE fines SET paid=1, paid_on=NOW() WHERE id=%s AND paid=0", (fine_id,))
        if cur.rowcount == 0:
            raise ValueError("Fine not found or already paid")
    return jsonify(message="Fine marked as paid")


# ---------- reports ----------
@bp.get("/librarian/reports")
@login_required(*STAFF)
def reports():
    fines_all = fine_rows()
    collected = float(scalar("SELECT COALESCE(SUM(amount),0) FROM fines WHERE paid=1"))
    cards = [
        {"label": "Total borrowings", "value": scalar("SELECT COUNT(*) FROM borrowings")},
        {"label": "Active borrowings", "value": scalar("SELECT COUNT(*) FROM borrowings WHERE status<>'returned'")},
        {"label": "Fines collected", "value": f"₹{collected:.2f}"},
        {"label": "Fines outstanding", "value": f"₹{outstanding(fines_all):.2f}"},
    ]
    cats = query("SELECT c.name, COUNT(b.id) AS titles, COALESCE(SUM(b.total_copies),0) AS total, "
                 "COALESCE(SUM(b.available_copies),0) AS avail FROM categories c "
                 "LEFT JOIN books b ON b.category_id=c.id GROUP BY c.id, c.name ORDER BY c.name")
    months = query("SELECT strftime('%Y-%m', issue_date) AS m, COUNT(*) AS n FROM borrowings "
                   "WHERE issue_date >= date('now','localtime','-6 months') GROUP BY m ORDER BY m DESC")
    top = query("SELECT u.full_name, s.roll_no, COUNT(*) AS n FROM borrowings br JOIN students s ON s.id=br.student_id "
                "JOIN users u ON u.id=s.user_id GROUP BY s.id, u.full_name, s.roll_no ORDER BY n DESC LIMIT 5")
    overdue = list_borrowings(status="overdue")
    tables = [
        make_table("Books per category", ["Category", "Titles", "Total copies", "Available copies"],
                   [[r["name"], r["titles"], r["total"], r["avail"]] for r in cats]),
        make_table("Borrowings per month (last 6 months)", ["Month", "Books issued"], [[r["m"], r["n"]] for r in months]),
        most_borrowed_table(),
        make_table("Most active students", ["Student", "Roll no", "Books borrowed"],
                   [[r["full_name"], r["roll_no"], r["n"]] for r in top]),
        make_table("Overdue books", ["Student", "Book", "Due date", "Days late", "Fine"],
                   [[r["student_name"], r["title"], r["due_date"], r["days_overdue"], "₹%.2f" % r["fine"]]
                    for r in overdue]),
    ]
    return jsonify(cards=cards, tables=tables)
