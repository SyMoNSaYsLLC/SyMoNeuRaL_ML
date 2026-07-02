from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
import psycopg
import os
from pathlib import Path
import random

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-change-this")

DB_URL = "postgresql://symoneural_user:symon_says_secure_password@localhost/symoneural_db"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

BASE_DIR = Path(__file__).resolve().parent
AVATAR_DIR = BASE_DIR / "static" / "avatars"
OVERVIEW_TXT_PATH = BASE_DIR / "static" / "docs" / "company-overview.txt"


class User(UserMixin):
    def __init__(self, id, username, full_name, photo_path, bio, country, date_of_birth, password_hash):
        self.id = id
        self.username = username
        self.full_name = full_name
        self.photo_path = photo_path
        self.bio = bio
        self.country = country
        self.date_of_birth = date_of_birth
        self.password_hash = password_hash

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    with psycopg.connect(DB_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT username, full_name, photo_path, bio, country, date_of_birth, password_hash
                FROM user_profiles
                WHERE username = %s;
            """, [user_id])
            row = cursor.fetchone()
            if row:
                return User(
                    id=row[0], username=row[0], full_name=row[1], photo_path=row[2],
                    bio=row[3], country=row[4], date_of_birth=row[5], password_hash=row[6]
                )
    return None


def ensure_app_tables():
    try:
        with psycopg.connect(DB_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute("ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS last_seen TIMESTAMPTZ;")
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id BIGSERIAL PRIMARY KEY,
                        sender_username TEXT NOT NULL REFERENCES user_profiles(username) ON DELETE CASCADE,
                        body TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                """)
    except psycopg.errors.InsufficientPrivilege:
        # DB schema migration must be run by DB owner/admin.
        print("WARN: insufficient DB privileges for schema migration; skipping ensure_app_tables().")


def get_all_profiles():
    with psycopg.connect(DB_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT username, full_name, photo_path, bio, country, date_of_birth, password_hash
                FROM user_profiles
                ORDER BY username;
            """)
            users_data = cursor.fetchall()
            return [
                User(id=u[0], username=u[0], full_name=u[1], photo_path=u[2], bio=u[3], country=u[4], date_of_birth=u[5], password_hash=u[6])
                for u in users_data
            ]


def get_profile(username):
    with psycopg.connect(DB_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT username, full_name, photo_path, bio, country, date_of_birth, password_hash
                FROM user_profiles
                WHERE username = %s;
            """, [username])
            u = cursor.fetchone()
            if u:
                return User(id=u[0], username=u[0], full_name=u[1], photo_path=u[2], bio=u[3], country=u[4], date_of_birth=u[5], password_hash=u[6])
    return None


def get_avatar_choices():
    allowed = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    if not AVATAR_DIR.exists():
        return []
    avatars = [p.name for p in AVATAR_DIR.iterdir() if p.is_file() and p.suffix.lower() in allowed]
    return sorted(avatars, key=str.lower)


def load_company_overview():
    try:
        return OVERVIEW_TXT_PATH.read_text(encoding="utf-8")
    except Exception:
        return "Company overview file not found."


def get_random_default_avatar_path() -> str:
    choices = get_avatar_choices()
    if not choices:
        return "avatars/user.png"
    return f"avatars/{random.choice(choices)}"


ensure_app_tables()


@app.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    return render_template("landing.html")


@app.route("/home")
@login_required
def home():
    return render_template(
        "index.html",
        user=current_user,
        avatars=get_avatar_choices(),
        company_overview=load_company_overview(),
        initial_tab=request.args.get("tab", "overview"),
    )


@app.route("/about")
@login_required
def about():
    return redirect(url_for("home", tab="about"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = get_profile(username)
        if user and user.check_password(password):
            ensure_user_has_avatar(user.username)
            login_user(get_profile(user.username))  # refresh user with avatar
            with psycopg.connect(DB_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("UPDATE user_profiles SET last_seen = NOW() WHERE username = %s;", (user.username,))
            return redirect(url_for("home"))
        flash("Invalid username or password", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        full_name = (request.form.get("full_name") or "").strip()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if not username or not full_name:
            flash("Username and full name are required.", "error")
            return redirect(url_for("register"))
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return redirect(url_for("register"))
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))
        if get_profile(username):
            flash("Username already exists.", "error")
            return redirect(url_for("register"))

        default_avatar = get_random_default_avatar_path()
        with psycopg.connect(DB_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_profiles
                    (username, full_name, photo_path, bio, country, date_of_birth, password_hash, last_seen)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW());
                """, (username, full_name, default_avatar, "", "", None, generate_password_hash(password)))

        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/select_avatar", methods=["GET", "POST"])
@login_required
def select_avatar():
    avatars = get_avatar_choices()
    if request.method == "POST":
        selected_avatar = (request.form.get("avatar") or "").strip()
        if selected_avatar in avatars:
            with psycopg.connect(DB_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE user_profiles SET photo_path = %s WHERE username = %s;",
                        (f"avatars/{selected_avatar}", current_user.username),
                    )
            flash("Avatar updated successfully!", "success")
        else:
            flash("Invalid avatar selection.", "error")
        return redirect(url_for("home", tab="account"))

    return render_template("select_avatar.html", avatars=avatars)


@app.route("/account/password", methods=["POST"])
@login_required
def account_change_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    user = get_profile(current_user.username)
    if not user or not user.check_password(current_password):
        flash("Current password is incorrect.", "error")
        return redirect(url_for("home", tab="account"))
    if len(new_password) < 8:
        flash("New password must be at least 8 characters.", "error")
        return redirect(url_for("home", tab="account"))
    if new_password != confirm_password:
        flash("New passwords do not match.", "error")
        return redirect(url_for("home", tab="account"))

    with psycopg.connect(DB_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE user_profiles SET password_hash = %s WHERE username = %s;",
                (generate_password_hash(new_password), current_user.username),
            )

    flash("Password changed successfully.", "success")
    return redirect(url_for("home", tab="account"))


@app.route("/account/avatar", methods=["POST"])
@login_required
def account_change_avatar():
    avatar = (request.form.get("avatar") or "").strip()
    if avatar not in get_avatar_choices():
        flash("Invalid avatar selection.", "error")
        return redirect(url_for("home", tab="account"))
    with psycopg.connect(DB_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE user_profiles SET photo_path = %s WHERE username = %s;",
                (f"avatars/{avatar}", current_user.username),
            )
    flash("Avatar updated.", "success")
    return redirect(url_for("home", tab="account"))


@app.route("/api/presence/ping", methods=["POST"])
@login_required
def presence_ping():
    with psycopg.connect(DB_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE user_profiles SET last_seen = NOW() WHERE username = %s;", (current_user.username,))
    return jsonify({"ok": True})


@app.route("/api/online", methods=["GET"])
@login_required
def api_online():
    with psycopg.connect(DB_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT username, COALESCE(photo_path, 'avatars/user.png') AS photo_path
                FROM user_profiles
                WHERE last_seen >= NOW() - INTERVAL '120 seconds'
                ORDER BY username ASC;
            """)
            rows = cursor.fetchall()
    return jsonify([{"username": r[0], "photo_path": r[1]} for r in rows])


@app.route("/api/chat/messages", methods=["GET"])
@login_required
def chat_messages_get():
    since_id = int(request.args.get("since_id", 0))
    with psycopg.connect(DB_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, sender_username, body, created_at
                FROM chat_messages
                WHERE id > %s
                ORDER BY id ASC
                LIMIT 100;
            """, (since_id,))
            rows = cursor.fetchall()
    return jsonify([
        {
            "id": r[0],
            "username": r[1],
            "body": r[2],
            "created_at": r[3].isoformat() if hasattr(r[3], "isoformat") else str(r[3]),
        }
        for r in rows
    ])


@app.route("/api/chat/messages", methods=["POST"])
@login_required
def chat_messages_post():
    body = (request.form.get("body") or "").strip()
    if not body:
        return jsonify({"ok": False, "error": "empty"}), 400
    body = body[:500]
    with psycopg.connect(DB_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO chat_messages (sender_username, body) VALUES (%s, %s);", (current_user.username, body))
            cursor.execute("UPDATE user_profiles SET last_seen = NOW() WHERE username = %s;", (current_user.username,))
    return jsonify({"ok": True})


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("landing"))


@app.route("/user/<username>")
@login_required
def profile(username):
    if username != current_user.username:
        return redirect(url_for("profile", username=current_user.username))
    user = get_profile(username)
    return render_template(
        "index.html",
        user=user,
        avatars=get_avatar_choices(),
        company_overview=load_company_overview(),
        initial_tab="overview",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
