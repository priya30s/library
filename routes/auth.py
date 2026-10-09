"""Login/logout, profile, and read-only endpoints shared by every logged-in user."""
from functools import wraps
from flask import Blueprint, request, session, jsonify, redirect
from models import user as user_model, book as book_model, query

bp = Blueprint("auth", __name__)


def login_required(*roles, page=False):
    """Protect a route. With no roles any logged-in user may enter.
    page=True redirects (for HTML pages); otherwise a JSON error is returned (for the API)."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect("/login") if page else (jsonify(error="Please log in first"), 401)
            if roles and session["role"] not in roles:
                return redirect("/dashboard") if page else (jsonify(error="Access denied"), 403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def get_json(required=()):
    """Read the JSON body and make sure the required fields are not empty."""
    data = request.get_json(silent=True) or {}
    for field in required:
        if not str(data.get(field, "")).strip():
            raise ValueError(field.replace("_", " ").capitalize() + " is required")
    return data


def to_int(value, label="value"):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid {label}")


@bp.post("/api/login")
def login():
    d = get_json(["username", "password"])
    user = user_model.authenticate(str(d["username"]).strip(), str(d["password"]))
    if not user:
        return jsonify(error="Invalid username or password"), 401
    session.clear()
    session.update(user_id=user["id"], role=user["role"], name=user["full_name"],
                   profile_id=user_model.profile_id(user["id"], user["role"]))
    return jsonify(redirect="/dashboard")


@bp.get("/logout")
def logout():
    session.clear()
    return redirect("/login")


@bp.get("/api/me")
@login_required()
def me():
    return jsonify(user_model.get_user(session["user_id"]))


@bp.put("/api/me")
@login_required()
def update_me():
    user_model.update_own_profile(session["user_id"], get_json())
    return jsonify(message="Profile updated")


@bp.post("/api/me/password")
@login_required()
def change_password():
    d = get_json(["current_password", "new_password"])
    user_model.change_password(session["user_id"], d["current_password"], d["new_password"])
    return jsonify(message="Password changed")


# ---- read-only catalogue endpoints (any logged-in user) ----
@bp.get("/api/books")
@login_required()
def list_books():
    category = request.args.get("category") or None
    return jsonify(book_model.search(request.args.get("q", ""), category and to_int(category, "category"),
                                     request.args.get("available") == "1"))


@bp.get("/api/books/<int:book_id>")
@login_required()
def book_detail(book_id):
    book = book_model.get(book_id)
    if not book:
        return jsonify(error="Book not found"), 404
    return jsonify(book)


@bp.get("/api/categories")
@login_required()
def list_categories():
    return jsonify(query("SELECT c.*, COUNT(b.id) AS book_count FROM categories c "
                         "LEFT JOIN books b ON b.category_id=c.id GROUP BY c.id ORDER BY c.name"))
