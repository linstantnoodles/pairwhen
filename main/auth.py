import functools
import os

from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash
import pymysql

bp = Blueprint("auth", __name__)

def connect_to_database():
    connection = pymysql.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        db=os.getenv("DATABASE"),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db


def login_required(view):
    """View decorator that redirects anonymous users to the login page."""
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(**kwargs)
    return wrapped_view

@bp.before_app_request
def load_logged_in_user():
    """If a user id is stored in the session, load the user object from
    the database into ``g.user``."""
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        with get_db().cursor() as cursor:
            cursor.execute("SELECT email, name, timezone FROM `users` WHERE id = %s", (user_id,))
        g.user = cursor.fetchone()

def current_user():
    if g.user:
        return g.user
    return None

@bp.route("/signup", methods=("GET", "POST"))
def signup():
    """signup a new user.

    Validates that the username is not already taken. Hashes the
    password for security.
    """
    email = ""
    name = ""
    if request.method == "POST":
        email = request.form["email"]
        name = request.form["name"]
        password = request.form["password"]
        timezone = request.form["timezone"]

        db = get_db()
        error = None
        if not email:
            error = "email is required."
        elif not password:
            error = "Password is required."
        elif len(password) < 6:
            error = "Password needs to have at least 6 characters."
        elif not name:
            error = "Name is required."
        elif not timezone:
            error = "Timezone is required."

        with db.cursor() as cursor:
            res = cursor.execute("SELECT `id` FROM `users` WHERE `email` = %s", (email,))
            if cursor.fetchone() is not None:
                error = "{0} already exists.".format(email)
        if error is None:
            user_id = None
            with db.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO `users` (email, password, name, timezone) VALUES (%s, %s, %s, %s)",
                    (email, generate_password_hash(password), name, timezone),
                )
                user_id = cursor.lastrowid
            db.commit()
            session.clear()
            session["user_id"] = user_id
            return redirect(url_for("dashboard"))
        flash(error)
    return render_template("signup.html", current_user=current_user(), email=email, name=name)

@bp.route("/login", methods=("GET", "POST"))
def login():
    """Log in a signuped user by adding the user id to the session."""
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        db = get_db()
        error = None
        user = None
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM `users` WHERE email = %s", (email,))
            user = cursor.fetchone()
        if user is None:
            error = "Invalid email or password."
        elif not check_password_hash(user["password"], password):
            error = "Invalid email or password."
        if error is None:
            # store the user id in a new session and return to the index
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        flash(error)
    return render_template("login.html", current_user=current_user())


@bp.route("/logout")
def logout():
    """Clear the current session, including the stored user id."""
    session.clear()
    return redirect(url_for("index"))
