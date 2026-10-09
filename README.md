# Library Management System (Flask + SQLite)

HTML/CSS/JavaScript frontend · Python Flask backend · SQLite database (no server to install).

## 1. Architecture
Browser (HTML + JS `fetch`) → Flask routes (`routes/`) → services (`services/`: borrow/return/fine rules)
→ models (`models/`: SQL) → SQLite file `library.db`.
Pages are rendered by Flask templates; all data comes from JSON API endpoints (`/api/...`).
Access is protected by sessions + a `login_required(role)` decorator on every page and API route.
`database.sql` holds the tables, relationships, constraints and sample data. The app runs it
automatically the first time it starts and creates `library.db`.

## 2. Install and run
```
python -m pip install Flask
python app.py
```
Open http://127.0.0.1:5000 . That's all - no database setup needed.
(Optional: use a virtual environment: `python -m venv venv`, then `venv\Scripts\activate`.)

To reset all data back to the sample data: stop the app, delete `library.db`, run `python app.py` again.

## 3. Run in VS Code
File → Open Folder → `library_management`. Open a terminal (Ctrl+`) and run the two commands above.

## 4. Sample logins
| Role | Username | Password |
|---|---|---|
| Admin | admin | admin123 |
| Librarian | librarian | lib123 |
| Student | student1 / student2 / student3 | student123 |

## 5. Rules (change in `config.py`)
Fine ₹5/day · loan period 14 days · max 3 books per student · "low stock" at 2 copies or fewer.

## 6. Testing steps
**Student (student1):** Dashboard shows an overdue book and fine → Browse Books, search "python" or "algo" →
open a book → Borrow → copies drop by one → My Books → click Return (status becomes "Return requested") → My Fines.
**Librarian:** Add Book → it appears in Books → Issue / Return: issue a book to roll no `EC2024002` →
filter "Overdue" → Accept return on the late book → a fine is recorded → Fines → Mark paid → Reports.
**Admin:** Dashboard totals → Librarians (add one, log in as them) → Categories (add/rename/delete) →
Users (disable a student; they can no longer log in) → Transactions.
**Security check:** while logged in as a student, open `/librarians` or `/api/admin/users` - access is refused.

## 7. Common errors
| Error | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'flask'` | Run `python -m pip install Flask` |
| "Database error" on the login page | Stop the app, delete `library.db`, run `python app.py` again |
| Login says invalid password | Delete `library.db` and restart so the sample users are recreated |
| Port 5000 already in use | Change to `app.run(debug=True, port=5001)` in `app.py` |
| `python` not recognised | Reinstall Python and tick "Add Python to PATH" |
