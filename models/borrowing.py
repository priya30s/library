"""Borrowing queries. Fines for books that are still out are calculated live."""
from . import query
from services.fine_service import calc_fine

ACTIVE = ("issued", "return_requested")

BASE = """SELECT br.id, br.book_id, br.student_id, br.issue_date, br.due_date, br.return_date, br.status,
          b.title, b.author, u.full_name AS student_name, s.roll_no, f.amount AS recorded_fine
          FROM borrowings br JOIN books b ON b.id=br.book_id
          JOIN students s ON s.id=br.student_id JOIN users u ON u.id=s.user_id
          LEFT JOIN fines f ON f.borrowing_id=br.id"""


def list_borrowings(student_id=None, status=None):
    sql, params = BASE + " WHERE 1=1", []
    if student_id:
        sql += " AND br.student_id=%s"
        params.append(student_id)
    if status == "overdue":
        sql += " AND br.status IN ('issued','return_requested') AND br.due_date < CURDATE()"
    elif status == "active":
        sql += " AND br.status IN ('issued','return_requested')"
    elif status in ("issued", "return_requested", "returned"):
        sql += " AND br.status=%s"
        params.append(status)
    rows = query(sql + " ORDER BY br.id DESC", params)
    for r in rows:
        if r["status"] in ACTIVE:
            r["days_overdue"], r["fine"] = calc_fine(r["due_date"])
        else:
            r["days_overdue"], r["fine"] = 0, float(r["recorded_fine"] or 0)
        r["is_overdue"] = r["status"] in ACTIVE and r["days_overdue"] > 0
        del r["recorded_fine"]
    return rows
