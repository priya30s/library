"""Application entry point. Run with:  python app.py"""
from datetime import date
from decimal import Decimal
import sqlite3
from flask import Flask, jsonify, render_template, request, session, redirect
from flask.json.provider import DefaultJSONProvider
from config import Config
from models import init_db
from routes.auth import bp as auth_bp, login_required
from routes.student import bp as student_bp
from routes.librarian import bp as librarian_bp
from routes.admin import bp as admin_bp


def _json_default(obj):
    """Send dates as 'YYYY-MM-DD' and decimals as numbers."""
    if isinstance(obj, date):          # datetime is a subclass of date
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return DefaultJSONProvider.default(obj)


class AppJSONProvider(DefaultJSONProvider):
    default = staticmethod(_json_default)


init_db()                     # creates library.db on the very first run
app = Flask(__name__)
app.config.from_object(Config)
app.json = AppJSONProvider(app)
for blueprint in (auth_bp, student_bp, librarian_bp, admin_bp):
    app.register_blueprint(blueprint)


# ---------------- HTML pages ----------------
def page(url, template, *roles):
    """Register a page that only the given roles (or any logged-in user) may open."""
    @login_required(*roles, page=True)
    def view(**kwargs):
        return render_template(template, **kwargs)
    app.add_url_rule(url, endpoint=template, view_func=view)


page("/books", "books.html")
page("/books/add", "add_book.html", "librarian", "admin")
page("/books/<int:book_id>", "book_details.html")
page("/books/<int:book_id>/edit", "edit_book.html", "librarian", "admin")
page("/borrowed", "borrowed_books.html")
page("/students", "students.html", "librarian", "admin")
page("/librarians", "librarians.html", "admin")
page("/categories", "categories.html", "admin")
page("/users", "users.html", "admin")
page("/fines", "fines.html")
page("/reports", "reports.html", "librarian", "admin")
page("/profile", "profile.html")


@app.route("/")
def home():
    return redirect("/dashboard" if "user_id" in session else "/login")


@app.route("/login")
def login_page():
    if "user_id" in session:
        return redirect("/dashboard")
    return render_template("login.html")


@app.route("/dashboard")
@login_required(page=True)
def dashboard():
    return render_template(f"{session['role']}_dashboard.html")


# ---------------- error handling ----------------
@app.errorhandler(ValueError)
def bad_input(e):                       # validation problems raised by our code
    return jsonify(error=str(e)), 400


@app.errorhandler(sqlite3.IntegrityError)
def integrity_error(e):
    text = str(e)
    if "UNIQUE" in text:
        msg = "That value already exists (duplicate username, email, ISBN, roll number or name)"
    elif "FOREIGN KEY" in text:
        msg = "This record is in use (it has borrowing history) and cannot be deleted"
    else:
        msg = "The data you sent is not valid"
    return jsonify(error=msg), 400


@app.errorhandler(sqlite3.Error)
def database_error(e):
    app.logger.error("Database error: %s", e)
    return jsonify(error="Database error. Try deleting library.db and restarting the app."), 500


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api"):
        return jsonify(error="Not found"), 404
    return "<h2>Page not found</h2><a href='/dashboard'>Go to dashboard</a>", 404


@app.errorhandler(405)
def not_allowed(e):
    return jsonify(error="Method not allowed"), 405


if __name__ == "__main__":
    app.run(debug=True)
