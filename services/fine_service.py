"""Fine calculation:  fine = overdue days x FINE_PER_DAY."""
from datetime import date
from config import Config
from models import query


def calc_fine(due_date, returned_on=None):
    """Return (days_overdue, fine_amount). Uses today if the book is not returned yet."""
    days = max(((returned_on or date.today()) - due_date).days, 0)
    return days, float(days * Config.FINE_PER_DAY)


def fine_rows(student_id=None):
    """Recorded fines (from returned books) + fines still growing on overdue books."""
    rows = []
    sql = ("SELECT f.id, f.days_overdue, f.amount, f.paid, b.title, u.full_name, s.roll_no FROM fines f "
           "JOIN borrowings br ON br.id=f.borrowing_id JOIN books b ON b.id=br.book_id "
           "JOIN students s ON s.id=f.student_id JOIN users u ON u.id=s.user_id")
    params = ()
    if student_id:
        sql += " WHERE f.student_id=%s"
        params = (student_id,)
    for r in query(sql + " ORDER BY f.id DESC", params):
        rows.append({"id": r["id"], "title": r["title"], "student": r["full_name"], "roll_no": r["roll_no"],
                     "days": r["days_overdue"], "amount": float(r["amount"]),
                     "state": "Paid" if r["paid"] else "Unpaid"})
    sql = ("SELECT b.title, u.full_name, s.roll_no, br.due_date FROM borrowings br "
           "JOIN books b ON b.id=br.book_id JOIN students s ON s.id=br.student_id JOIN users u ON u.id=s.user_id "
           "WHERE br.status IN ('issued','return_requested') AND br.due_date < CURDATE()")
    if student_id:
        sql += " AND br.student_id=%s"
    for r in query(sql, params):
        days, amount = calc_fine(r["due_date"])
        rows.append({"id": None, "title": r["title"], "student": r["full_name"], "roll_no": r["roll_no"],
                     "days": days, "amount": amount, "state": "Accruing"})
    return rows


def outstanding(rows):
    return sum(r["amount"] for r in rows if r["state"] != "Paid")
