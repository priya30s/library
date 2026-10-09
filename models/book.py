"""Book catalogue queries."""
from . import query, transaction


def search(q="", category_id=None, available_only=False):
    """Smart search: every word typed must match the title, author or ISBN."""
    sql = ("SELECT b.*, c.name AS category FROM books b "
           "LEFT JOIN categories c ON c.id=b.category_id WHERE 1=1")
    params = []
    for term in (q or "").split():
        sql += " AND (b.title LIKE %s OR b.author LIKE %s OR b.isbn LIKE %s)"
        params += [f"%{term}%"] * 3
    if category_id:
        sql += " AND b.category_id=%s"
        params.append(category_id)
    if available_only:
        sql += " AND b.available_copies>0"
    return query(sql + " ORDER BY b.title", params)


def get(book_id):
    return query("SELECT b.*, c.name AS category FROM books b "
                 "LEFT JOIN categories c ON c.id=b.category_id WHERE b.id=%s", (book_id,), one=True)


def _clean(data):
    d = {k: str(data.get(k) or "").strip() for k in ["title", "author", "isbn", "publisher", "description"]}
    if not (d["title"] and d["author"] and d["isbn"]):
        raise ValueError("Title, author and ISBN are required")
    try:
        d["total_copies"] = int(data.get("total_copies"))
        d["publish_year"] = int(data["publish_year"]) if data.get("publish_year") else None
        d["category_id"] = int(data["category_id"]) if data.get("category_id") else None
    except (TypeError, ValueError):
        raise ValueError("Copies, year and category must be valid numbers")
    if d["total_copies"] < 0:
        raise ValueError("Total copies cannot be negative")
    for k in ("publisher", "description"):
        d[k] = d[k] or None
    return d


def create(data):
    d = _clean(data)
    with transaction() as cur:
        cur.execute("INSERT INTO books (title,author,isbn,category_id,publisher,publish_year,description,"
                    "total_copies,available_copies) VALUES (%(title)s,%(author)s,%(isbn)s,%(category_id)s,"
                    "%(publisher)s,%(publish_year)s,%(description)s,%(total_copies)s,%(total_copies)s)", d)
        return cur.lastrowid


def update(book_id, data):
    d = _clean(data)
    d["id"] = book_id
    with transaction() as cur:
        cur.execute("SELECT total_copies, available_copies FROM books WHERE id=%s", (book_id,))
        old = cur.fetchone()
        if not old:
            raise ValueError("Book not found")
        # keep "available" in step when the total number of copies changes
        d["available"] = old["available_copies"] + d["total_copies"] - old["total_copies"]
        if d["available"] < 0:
            raise ValueError("Total copies cannot be less than the copies currently borrowed")
        cur.execute("UPDATE books SET title=%(title)s, author=%(author)s, isbn=%(isbn)s, "
                    "category_id=%(category_id)s, publisher=%(publisher)s, publish_year=%(publish_year)s, "
                    "description=%(description)s, total_copies=%(total_copies)s, "
                    "available_copies=%(available)s WHERE id=%(id)s", d)


def delete(book_id):
    with transaction() as cur:
        cur.execute("DELETE FROM books WHERE id=%s", (book_id,))
        if cur.rowcount == 0:
            raise ValueError("Book not found")
