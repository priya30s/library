"""Student API: dashboard, borrow, return, history, fines."""
from datetime import date, timedelta
from flask import Blueprint, session, jsonify
from models import scalar
from models.borrowing import list_borrowings, ACTIVE
from services.book_service import borrow_book, request_return, make_table, most_borrowed_table, recent_table
from services.fine_service import fine_rows, outstanding
from config import Config
from .auth import login_required, get_json, to_int

bp = Blueprint("student", __name__, url_prefix="/api/student")


@bp.get("/dashboard")
@login_required("student")
def dashboard():
    rows = list_borrowings(student_id=session["profile_id"])
    active = [r for r in rows if r["status"] in ACTIVE]
    soon = date.today() + timedelta(days=3)
    due_soon = [r for r in active if not r["is_overdue"] and r["due_date"] <= soon]
    overdue = [r for r in active if r["is_overdue"]]
    cards = [
        {"label": "Currently borrowed", "value": len(active)},
        {"label": "Total ever borrowed", "value": len(rows)},
        {"label": "Due soon (3 days)", "value": len(due_soon)},
        {"label": "Overdue books", "value": len(overdue)},
        {"label": "Total fines", "value": f"₹{outstanding(fine_rows(session['profile_id'])):.2f}"},
    ]
    tables = [
        make_table("My current books", ["Book", "Due date", "Status"],
                   [[r["title"], r["due_date"], "OVERDUE - fine ₹%.2f" % r["fine"] if r["is_overdue"] else "On time"]
                    for r in active]),
        most_borrowed_table(), recent_table(),
    ]
    return jsonify(cards=cards, tables=tables)


@bp.post("/borrow")
@login_required("student")
def borrow():
    d = get_json(["book_id"])
    result = borrow_book(session["profile_id"], to_int(d["book_id"], "book"), issued_by=None)
    return jsonify(result), 201


@bp.get("/borrowings")
@login_required("student")
def borrowings():
    return jsonify(list_borrowings(student_id=session["profile_id"]))


@bp.post("/return/<int:borrowing_id>")
@login_required("student")
def return_book(borrowing_id):
    request_return(borrowing_id, session["profile_id"])
    return jsonify(message="Return requested. Hand the book to the librarian.")


@bp.get("/fines")
@login_required("student")
def fines():
    rows = fine_rows(session["profile_id"])
    return jsonify(rows=rows, outstanding=outstanding(rows), fine_per_day=Config.FINE_PER_DAY)
