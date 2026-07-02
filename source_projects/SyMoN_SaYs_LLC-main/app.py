from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
import psycopg
import psycopg.errors
import os
import random
import json
from pathlib import Path
from functools import lru_cache

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-change-this")

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://symoneural_user:symon_says_secure_password@localhost/symoneural_db"
)

DB_AUTO_MIGRATE = os.getenv("DB_AUTO_MIGRATE", "0").strip() == "1"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

PROJECT_ROOT = Path(__file__).resolve().parent
UI_CONTENT_PATH = PROJECT_ROOT / "static" / "data" / "ui_content.json"
AVATAR_DIR = PROJECT_ROOT / "static" / "avatars"
DEFAULT_AVATAR = "user.png"
ALLOWED_AVATAR_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}

@lru_cache(maxsize=1)
def load_ui_content() -> dict:
    try:
        with UI_CONTENT_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def deep_get(data: dict, path: str, default=None):
    cur = data
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur

@app.context_processor
def inject_ui_content():
    content = load_ui_content()

    def ui_get(path: str, default=""):
        return deep_get(content, path, default)

    return {"ui_content": content, "ui_get": ui_get}

def _available_avatars() -> list[str]:
    if not AVATAR_DIR.is_dir():
        return []
    files = [
        p.name for p in AVATAR_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in ALLOWED_AVATAR_EXTS
    ]
    return sorted(files, key=str.casefold)

def get_curated_avatars() -> list[str]:
    ui = _load_ui_content()
    curated = ui.get("avatars", {}).get("curated", [])
    curated = [str(x).strip() for x in curated if str(x).strip()]

    available = set(_available_avatars())
    curated_existing = sorted({a for a in curated if a in available}, key=str.casefold)

    if curated_existing:
        return curated_existing

    # Fallback: only default avatar if curated list is empty/invalid.
    if DEFAULT_AVATAR in available:
        return [DEFAULT_AVATAR]

    # Final fallback: first available avatar if default missing.
    all_available = sorted(available, key=str.casefold)
    return all_available[:1]

def normalize_avatar_selection(selected: str | None) -> str | None:
    selected = (selected or "").strip()
    allowed = get_curated_avatars()
    if selected in allowed:
        return selected
    return allowed[0] if allowed else None


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
                return User(row[0], row[0], row[1], row[2], row[3], row[4], row[5], row[6])
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
        print("WARN: insufficient privilege for migrations; run DB migration as table owner/admin.")


def get_profile(username):
    with psycopg.connect(DB_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT username, full_name, photo_path, bio, country, date_of_birth, password_hash
                FROM user_profiles
                WHERE username = %s;
            """, [username])
            row = cursor.fetchone()
            if row:
                return User(row[0], row[0], row[1], row[2], row[3], row[4], row[5], row[6])
    return None


def get_avatar_choices():
    allowed = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    if not AVATAR_DIR.exists():
        return []
    return sorted(
        [p.name for p in AVATAR_DIR.iterdir() if p.is_file() and p.suffix.lower() in allowed],
        key=str.lower
    )


def get_random_default_avatar_path() -> str:
    avatars = get_avatar_choices()
    if not avatars:
        return "avatars/user.png"
    return f"avatars/{random.choice(avatars)}"


def ensure_user_has_avatar(username: str):
    with psycopg.connect(DB_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT photo_path FROM user_profiles WHERE username = %s;", (username,))
            row = cursor.fetchone()
            if row and (row[0] is None or str(row[0]).strip() == ""):
                cursor.execute(
                    "UPDATE user_profiles SET photo_path = %s WHERE username = %s;",
                    (get_random_default_avatar_path(), username),
                )


def load_company_overview():
    try:
        return OVERVIEW_TXT_PATH.read_text(encoding="utf-8")
    except Exception:
        return "Company overview file not found."


ensure_app_tables()


@app.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    return render_template("landing.html")


@app.route("/home")
@login_required
def home():
    avatars = get_curated_avatars()
    return render_template(
        "index.html",
        user=current_user,
        avatars=avatars,
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
            user = get_profile(user.username)
            login_user(user)
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
        confirm = request.form.get("confirm_password") or ""

        if not username or not full_name:
            flash("Username and full name are required.", "error")
            return redirect(url_for("register"))
        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return redirect(url_for("register"))
        if password != confirm:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))
        if get_profile(username):
            flash("Username already exists.", "error")
            return redirect(url_for("register"))

        with psycopg.connect(DB_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_profiles
                    (username, full_name, photo_path, bio, country, date_of_birth, password_hash, last_seen)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW());
                """, (
                    username,
                    full_name,
                    get_random_default_avatar_path(),
                    "",
                    "",
                    None,
                    generate_password_hash(password),
                ))

        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/select-avatar", methods=["GET", "POST"])
def select_avatar():
    avatars = get_curated_avatars()
    if request.method == "POST":
        chosen = normalize_avatar_selection(request.form.get("avatar"))
        if not chosen:
            flash("No avatar is currently available.", "error")
            return redirect(url_for("home", tab="account"))

        # save chosen (keep your existing DB update logic)
        # user.photo_path = f"avatars/{chosen}"
        return redirect(url_for("home", tab="account"))

    return render_template("select_avatar.html", avatars=avatars)


@app.post("/account/change-avatar")
def account_change_avatar():
    chosen = normalize_avatar_selection(request.form.get("avatar"))
    if not chosen:
        flash("No avatar is currently available.", "error")
        return redirect(url_for("home", tab="account"))

    # save chosen (keep your existing DB update logic)
    # user.photo_path = f"avatars/{chosen}"
    flash("Avatar updated.", "success")
    return redirect(url_for("home", tab="account"))


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

    flash("Password updated.", "success")
    return redirect(url_for("home", tab="account"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("landing"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
