"""Student lookups used when a librarian issues a book."""
from . import query


def find_by_roll_no(roll_no):
    return query("SELECT s.id, u.full_name FROM students s JOIN users u ON u.id=s.user_id "
                 "WHERE s.roll_no=%s AND u.is_active=1", (roll_no,), one=True)
