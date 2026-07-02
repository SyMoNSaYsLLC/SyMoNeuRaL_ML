from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
import psycopg
import os
from pathlib import Path

app = Flask(__name__)
app.secret_key = os.urandom(24) # Necessary for flashing messages

# --- Database Configuration ---
DB_URL = "postgresql://symoneural_user:symon_says_secure_password@localhost/symoneural_db"

# --- Flask-Login Configuration ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirect to /login if user is not authenticated

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
            cursor.execute("SELECT * FROM user_profiles WHERE username = %s;", [user_id])
            user_data = cursor.fetchone()
            if user_data:
                return User(id=user_data[0], username=user_data[0], full_name=user_data[1], photo_path=user_data[2], bio=user_data[3], country=user_data[4], date_of_birth=user_data[5], password_hash=user_data[6])
    return None

# --- Database Functions ---
def get_all_profiles():
    with psycopg.connect(DB_URL) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT username, full_name, photo_path, bio, country, date_of_birth, password_hash FROM user_profiles;")
        users_data = cursor.fetchall()
        return [User(id=u[0], username=u[0], full_name=u[1], photo_path=u[2], bio=u[3], country=u[4], date_of_birth=u[5], password_hash=u[6]) for u in users_data]

def get_profile(username):
    with psycopg.connect(DB_URL) as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM user_profiles WHERE username = %s;", [username])
        user_data = cursor.fetchone()
        if user_data:
            return User(id=user_data[0], username=user_data[0], full_name=user_data[1], photo_path=user_data[2], bio=user_data[3], country=user_data[4], date_of_birth=user_data[5], password_hash=user_data[6])
    return None

# --- Routes ---
@app.route("/")
@login_required
def home():
    profiles = get_all_profiles()
    return render_template("index.html", user=current_user, profiles=profiles)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        user = get_profile(request.form['username'])
        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('select_avatar')) # Redirect to avatar selection
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route("/select_avatar", methods=["GET", "POST"])
@login_required
def select_avatar():
    avatars = get_avatar_choices()
    if request.method == 'POST':
        selected_avatar = request.form.get('avatar')
        if selected_avatar:
            with psycopg.connect(DB_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE user_profiles SET photo_path = %s WHERE username = %s;",
                        (f"avatars/{selected_avatar}", current_user.username)
                    )
            flash('Avatar updated successfully!', 'success')
        return redirect(url_for('home'))

    return render_template("select_avatar.html", avatars=avatars)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/user/<username>")
@login_required
def profile(username):
    # Ensure users can only see their own profile, or add admin logic here
    if username != current_user.username:
        return redirect(url_for('profile', username=current_user.username))
        
    profiles = get_all_profiles()
    user = get_profile(username)
    return render_template("index.html", user=user, profiles=profiles)

@app.route("/about")
def about():
    # Reuse same page, defaulting to About tab.
    # If you already fetch users or other data for index, mirror it here as needed.
    return render_template(
        "index.html",
        company_overview=load_company_overview(),
        initial_tab="about",
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port="8080", debug=True)

BASE_DIR = Path(__file__).resolve().parent
AVATAR_DIR = BASE_DIR / "static" / "avatars"

def get_avatar_choices():
    allowed = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    if not AVATAR_DIR.exists():
        return []
    avatars = [
        p.name for p in AVATAR_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in allowed
    ]
    return sorted(avatars, key=str.lower)

