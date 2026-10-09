"""Borrow / return business rules plus small helpers shared by the dashboards."""
from datetime import date, timedelta
from config import Config
from models import query, transaction
from services.fine_service import calc_fine

ACTIVE_SQL = "status IN ('issued','return_requested')"


def borrow_book(student_id, book_id, issued_by=None):
    """Issue a book: checks stock and limits, then lowers available copies."""
    today = date.today()
    due = today + timedelta(days=Config.LOAN_DAYS)
    with transaction() as cur:
        cur.execute("SELECT title, available_copies FROM books WHERE id=%s", (book_id,))
        book = cur.fetchone()
        if not book:
            raise ValueError("Book not found")
        if book["available_copies"] <= 0:
            raise ValueError("No copies of this book are available right now")
        cur.execute(f"SELECT COUNT(*) AS n FROM borrowings WHERE student_id=%s AND {ACTIVE_SQL}", (student_id,))
        if cur.fetchone()["n"] >= Config.MAX_ACTIVE_BORROWINGS:
            raise ValueError(f"Limit reached: only {Config.MAX_ACTIVE_BORROWINGS} books can be borrowed at a time")
        cur.execute(f"SELECT id FROM borrowings WHERE student_id=%s AND book_id=%s AND {ACTIVE_SQL}",
                    (student_id, book_id))
        if cur.fetchone():
            raise ValueError("This book is already borrowed by the student")
        cur.execute("INSERT INTO borrowings (book_id,student_id,issued_by,issue_date,due_date,status) "
                    "VALUES (%s,%s,%s,%s,%s,'issued')", (book_id, student_id, issued_by, today, due))
        cur.execute("UPDATE books SET available_copies=available_copies-1 WHERE id=%s", (book_id,))
    return {"title": book["title"], "due_date": due.isoformat()}


def request_return(borrowing_id, student_id):
    """Student asks to return a book; the librarian accepts it later."""
    with transaction() as cur:
        cur.execute("UPDATE borrowings SET status='return_requested' "
                    "WHERE id=%s AND student_id=%s AND status='issued'", (borrowing_id, student_id))
        if cur.rowcount == 0:
            raise ValueError("This borrowing cannot be returned")


def accept_return(borrowing_id, received_by):
    """Librarian accepts a book: stores the return, calculates the fine, restores stock."""
    with transaction() as cur:
        cur.execute("SELECT * FROM borrowings WHERE id=%s", (borrowing_id,))
        br = cur.fetchone()
        if not br or br["status"] == "returned":
            raise ValueError("This borrowing was not found or is already returned")
        today = date.today()
        days, amount = calc_fine(br["due_date"], today)
        cur.execute("UPDATE borrowings SET status='returned', return_date=%s WHERE id=%s", (today, borrowing_id))
        cur.execute("INSERT INTO `returns` (borrowing_id,returned_on,received_by,fine_amount) VALUES (%s,%s,%s,%s)",
                    (borrowing_id, today, received_by, amount))
        if amount > 0:
            cur.execute("INSERT INTO fines (borrowing_id,student_id,days_overdue,amount) VALUES (%s,%s,%s,%s)",
                        (borrowing_id, br["student_id"], days, amount))
        cur.execute("UPDATE books SET available_copies=available_copies+1 WHERE id=%s", (br["book_id"],))
    return {"days_overdue": days, "fine": amount}


# ---- helpers that build the generic "table" blocks shown on dashboards ----
def make_table(title, headers, rows):
    return {"title": title, "headers": headers,
            "rows": [["" if c is None else str(c) for c in r] for r in rows]}


def most_borrowed_table(limit=5):
    rows = query("SELECT b.title, b.author, COUNT(br.id) AS n FROM books b JOIN borrowings br ON br.book_id=b.id "
                 "GROUP BY b.id, b.title, b.author ORDER BY n DESC, b.title LIMIT %s", (limit,))
    return make_table("Most borrowed books", ["Title", "Author", "Times borrowed"],
                      [[r["title"], r["author"], r["n"]] for r in rows])


def recent_table(limit=5):
    rows = query("SELECT title, author, created_at FROM books ORDER BY created_at DESC, id DESC LIMIT %s", (limit,))
    return make_table("Recently added books", ["Title", "Author", "Added on"],
                      [[r["title"], r["author"], r["created_at"].date()] for r in rows])


def low_stock_table(limit=8):
    rows = query("SELECT title, available_copies, total_copies FROM books WHERE available_copies<=%s "
                 "ORDER BY available_copies, title LIMIT %s", (Config.LOW_STOCK_LIMIT, limit))
    return make_table("Low availability alerts", ["Title", "Available", "Total copies"],
                      [[r["title"], r["available_copies"], r["total_copies"]] for r in rows])
