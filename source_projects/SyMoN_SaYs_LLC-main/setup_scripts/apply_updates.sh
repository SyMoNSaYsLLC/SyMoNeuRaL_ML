#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/home/google/Desktop/SyMoNeuRaLSQLDB_APP"
cd "$PROJECT_ROOT"

TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$PROJECT_ROOT/.backup_$TS"
mkdir -p "$BACKUP_DIR" "$PROJECT_ROOT/scripts" "$PROJECT_ROOT/static/brand" "$PROJECT_ROOT/static/docs"

echo "[1/8] Backing up current files..."
for f in app.py static/styles.css templates/index.html templates/login.html templates/select_avatar.html; do
  if [[ -f "$f" ]]; then
    mkdir -p "$BACKUP_DIR/$(dirname "$f")"
    cp -f "$f" "$BACKUP_DIR/$f"
  fi
done

echo "[2/8] Moving review -> docs (if needed)..."
if [[ -d "$PROJECT_ROOT/review" && ! -d "$PROJECT_ROOT/docs" ]]; then
  mv "$PROJECT_ROOT/review" "$PROJECT_ROOT/docs"
fi

echo "[3/8] Copying brand/doc assets..."
if [[ -f "$PROJECT_ROOT/SyMoNeuRaL.jpg" ]]; then
  cp -f "$PROJECT_ROOT/SyMoNeuRaL.jpg" "$PROJECT_ROOT/static/brand/symoneural.jpg"
elif [[ -f "$PROJECT_ROOT/SyMoNeuRaL.jpg" ]]; then
  cp -f "$PROJECT_ROOT/SyMoNeuRaL.jpg" "$PROJECT_ROOT/static/brand/symoneural.jpg"
fi

if [[ -f "$PROJECT_ROOT/SymonSaysKickoffv3.txt" ]]; then
  cp -f "$PROJECT_ROOT/SymonSaysKickoffv3.txt" "$PROJECT_ROOT/static/docs/company-overview.txt"
elif [[ -f "$PROJECT_ROOT/docs/SymonSaysKickoffv3.txt" ]]; then
  cp -f "$PROJECT_ROOT/docs/SymonSaysKickoffv3.txt" "$PROJECT_ROOT/static/docs/company-overview.txt"
fi

echo "[4/8] Writing app.py..."
cat > "$PROJECT_ROOT/app.py" <<'PYEOF'
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
import psycopg
import os
from pathlib import Path

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


ensure_app_tables()


@app.route("/")
def landing():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    return render_template("landing.html")


@app.route("/home")
@login_required
def home():
    profiles = get_all_profiles()
    return render_template(
        "index.html",
        user=current_user,
        profiles=profiles,
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

        with psycopg.connect(DB_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO user_profiles
                    (username, full_name, photo_path, bio, country, date_of_birth, password_hash, last_seen)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW());
                """, (username, full_name, "avatars/user.png", "", "", None, generate_password_hash(password)))

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
    profiles = get_all_profiles()
    user = get_profile(username)
    return render_template(
        "index.html",
        user=user,
        profiles=profiles,
        avatars=get_avatar_choices(),
        company_overview=load_company_overview(),
        initial_tab="overview",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
PYEOF

echo "[5/8] Writing templates..."
mkdir -p "$PROJECT_ROOT/templates"

cat > "$PROJECT_ROOT/templates/landing.html" <<'HTMLEOF'
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SyMoNeuRaL</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
  <main class="layout">
    <section class="panel">
      <h2>Welcome to SyMoNeuRaL</h2>
      <p>Edge systems integration and sustainable silicon lifecycle services.</p>
      <div class="action-row">
        <a class="tab-link" href="{{ url_for('register') }}">Create Account</a>
        <a class="tab-link" href="{{ url_for('login') }}">Login</a>
        <a class="tab-link" href="mailto:saysupport@symoneural.com?subject=Service%20Request">Request Service by Email</a>
      </div>
    </section>
  </main>
</body>
</html>
HTMLEOF

cat > "$PROJECT_ROOT/templates/register.html" <<'HTMLEOF'
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Create Account | SyMoNeuRaL</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
  <main class="layout">
    <section class="panel narrow">
      <h2>Create Account</h2>
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          {% for category, message in messages %}
            <p>{{ message }}</p>
          {% endfor %}
        {% endif %}
      {% endwith %}
      <form method="post">
        <input name="full_name" placeholder="Full name" required>
        <input name="username" placeholder="Username" required>
        <input type="password" name="password" placeholder="Password (min 8)" minlength="8" required>
        <input type="password" name="confirm_password" placeholder="Confirm password" minlength="8" required>
        <button type="submit">Create Account</button>
      </form>
      <p><a href="{{ url_for('login') }}">Already have an account? Login</a></p>
    </section>
  </main>
</body>
</html>
HTMLEOF

cat > "$PROJECT_ROOT/templates/login.html" <<'HTMLEOF'
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Login | SyMoNeuRaL</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
  <main class="layout">
    <section class="panel narrow">
      <h2>Login</h2>
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
          {% for category, message in messages %}
            <p>{{ message }}</p>
          {% endfor %}
        {% endif %}
      {% endwith %}
      <form method="post" action="{{ url_for('login') }}">
        <input name="username" placeholder="Username" required>
        <input type="password" name="password" placeholder="Password" required>
        <button type="submit">Sign In</button>
      </form>
      <div class="action-row">
        <a class="tab-link" href="{{ url_for('register') }}">Create Account</a>
        <a class="tab-link" href="mailto:saysupport@symoneural.com?subject=Service%20Request">Request Service by Email</a>
        <a class="tab-link" href="{{ url_for('landing') }}">Back to Home</a>
      </div>
    </section>
  </main>
</body>
</html>
HTMLEOF

cat > "$PROJECT_ROOT/templates/select_avatar.html" <<'HTMLEOF'
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Select Avatar | SyMoNeuRaL</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
  <main class="layout">
    <section class="panel">
      <h3>Select Avatar</h3>
      <form method="post">
        <div class="scroll-window avatar-window">
          <div class="avatar-grid">
            {% for avatar in avatars %}
            <label class="avatar-option">
              <input type="radio" name="avatar" value="{{ avatar }}" required>
              <img src="{{ url_for('static', filename='avatars/' ~ avatar) }}" alt="{{ avatar }}">
              <span>{{ avatar.rsplit('.', 1)[0] }}</span>
            </label>
            {% endfor %}
          </div>
        </div>
        <div class="action-row" style="margin-top:12px;">
          <button type="submit">Save Avatar</button>
          <a class="tab-link" href="{{ url_for('home', tab='account') }}">Back</a>
        </div>
      </form>
    </section>
  </main>
</body>
</html>
HTMLEOF

cat > "$PROJECT_ROOT/templates/index.html" <<'HTMLEOF'
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SyMoNeuRaL | Dashboard</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
  <div class="bg-grid"></div>

  <header class="topbar">
    <div class="brand">
      <span class="logo">S</span>
      <div>
        <h1>SyMoNeuRaL</h1>
        <p>Welcome, {{ user.full_name or user.username }}</p>
      </div>
    </div>

    <nav class="tabs">
      <button class="tab-btn" data-tab="overview">Quick Overview</button>
      <button class="tab-btn" data-tab="about">About</button>
      <button class="tab-btn" data-tab="account">Account</button>
      <a class="tab-link" href="{{ url_for('logout') }}">Logout</a>
    </nav>
  </header>

  <main class="layout">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}
        <section class="panel">
          {% for category, message in messages %}
            <p>{{ message }}</p>
          {% endfor %}
        </section>
      {% endif %}
    {% endwith %}

    <section id="overview" class="tab-panel">
      <div class="hero-card">
        <div class="hero-text">
          <h2>High-Density Edge Computing + Sustainable Silicon Lifecycle</h2>
          <p>System integration for embedded devices and PCs/laptops, bridging legacy hardware with modern AI requirements.</p>
          <ul>
            <li>Machine + OS integration tailored to customer needs</li>
            <li>Full-stack software automation for operations</li>
            <li>Reliable deployment workflows</li>
          </ul>
        </div>
        <div class="hero-image-wrap">
          <img src="{{ url_for('static', filename='brand/symoneural.jpg') }}" alt="SyMoNeuRaL architecture" class="hero-image">
        </div>
      </div>

      <section class="panel">
        <h3>User Profiles</h3>
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>Username</th><th>Name</th><th>Country</th></tr>
            </thead>
            <tbody>
              {% for p in profiles %}
              <tr>
                <td>{{ p.username }}</td>
                <td>{{ p.full_name }}</td>
                <td>{{ p.country }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </section>
    </section>

    <section id="about" class="tab-panel">
      <article class="panel">
        <h3>Company Overview (Source Document)</h3>
        <div class="scroll-window about-window">
          <pre class="doc-text">{{ company_overview }}</pre>
        </div>
      </article>
    </section>

    <section id="account" class="tab-panel">
      <article class="panel">
        <h3>Account Settings</h3>
        <p>Current avatar: <img src="{{ url_for('static', filename=user.photo_path or 'avatars/user.png') }}" alt="avatar" style="width:36px;height:36px;border-radius:50%;vertical-align:middle;"></p>
        <div class="action-row">
          <a class="tab-link" href="{{ url_for('select_avatar') }}">Open Avatar Picker</a>
        </div>
      </article>

      <article class="panel">
        <h3>Change Password</h3>
        <form method="post" action="{{ url_for('account_change_password') }}">
          <input type="password" name="current_password" placeholder="Current password" required>
          <input type="password" name="new_password" placeholder="New password (min 8)" minlength="8" required>
          <input type="password" name="confirm_password" placeholder="Confirm new password" minlength="8" required>
          <button type="submit">Update Password</button>
        </form>
      </article>

      <article class="panel">
        <h3>Quick Avatar Change</h3>
        <form method="post" action="{{ url_for('account_change_avatar') }}">
          <select name="avatar" required>
            {% for a in avatars %}
            <option value="{{ a }}" {% if user.photo_path and user.photo_path.endswith('/' ~ a) %}selected{% endif %}>{{ a }}</option>
            {% endfor %}
          </select>
          <button type="submit">Update Avatar</button>
        </form>
      </article>

      <article class="panel">
        <h3>Team Chat</h3>
        <div class="chat-wrap">
          <div>
            <h4>Online</h4>
            <ul id="onlineUsers"></ul>
          </div>
          <div>
            <div id="chatMessages" class="chat-messages"></div>
            <form id="chatForm">
              <input id="chatInput" name="body" placeholder="Type a message..." maxlength="500" required>
              <button type="submit">Send</button>
            </form>
          </div>
        </div>
      </article>
    </section>
  </main>

  <script>
    const buttons = document.querySelectorAll('.tab-btn');
    const panels = document.querySelectorAll('.tab-panel');
    const initialTab = "{{ initial_tab|default('overview') }}";

    function activateTab(tabName) {
      buttons.forEach(b => b.classList.toggle('active', b.dataset.tab === tabName));
      panels.forEach(p => p.classList.toggle('active', p.id === tabName));
    }

    buttons.forEach(btn => btn.addEventListener('click', () => activateTab(btn.dataset.tab)));
    activateTab(initialTab);

    let lastId = 0;
    async function ping(){ try { await fetch('/api/presence/ping', {method:'POST'}); } catch(_) {} }
    async function loadOnline(){
      try {
        const r = await fetch('/api/online'); const data = await r.json();
        document.getElementById('onlineUsers').innerHTML = data.map(u => `<li>${u.username}</li>`).join('');
      } catch(_) {}
    }
    async function loadMessages(){
      try {
        const r = await fetch('/api/chat/messages?since_id=' + lastId); const data = await r.json();
        const box = document.getElementById('chatMessages');
        data.forEach(m => {
          lastId = m.id;
          const row = document.createElement('div');
          row.textContent = `[${m.created_at}] ${m.username}: ${m.body}`;
          box.appendChild(row);
        });
        box.scrollTop = box.scrollHeight;
      } catch(_) {}
    }

    const f = document.getElementById('chatForm');
    if (f){
      f.addEventListener('submit', async (e)=>{
        e.preventDefault();
        const input = document.getElementById('chatInput');
        const body = input.value.trim();
        if (!body) return;
        const fd = new FormData(); fd.append('body', body);
        await fetch('/api/chat/messages', {method:'POST', body:fd});
        input.value = '';
        loadMessages();
      });

      setInterval(ping, 20000);
      setInterval(loadOnline, 5000);
      setInterval(loadMessages, 2000);
      ping(); loadOnline(); loadMessages();
    }
  </script>
</body>
</html>
HTMLEOF

echo "[6/8] Writing styles..."
mkdir -p "$PROJECT_ROOT/static"
cat > "$PROJECT_ROOT/static/styles.css" <<'CSSEOF'
:root{
  --bg:#070b1f; --card:#121a3d; --line:#2ee6ff; --line2:#ad47ff; --text:#e8ecff; --muted:#99a3d7;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:radial-gradient(1200px 800px at 70% 0%, #1b1d59 0%, var(--bg) 60%);color:var(--text)}
.bg-grid{position:fixed;inset:0;pointer-events:none;opacity:.12;background-image:linear-gradient(to right,#4d5aa533 1px,transparent 1px),linear-gradient(to bottom,#4d5aa533 1px,transparent 1px);background-size:40px 40px}
.layout{max-width:1180px;margin:20px auto;padding:0 20px 28px}
.topbar{display:flex;justify-content:space-between;align-items:center;padding:20px 32px;position:sticky;top:0;backdrop-filter:blur(6px);z-index:2}
.brand{display:flex;gap:12px;align-items:center}
.logo{width:38px;height:38px;border-radius:10px;display:grid;place-items:center;background:linear-gradient(135deg,var(--line2),#6a5cff);font-weight:800}
.brand h1{margin:0;font-size:1.1rem}.brand p{margin:2px 0 0;color:var(--muted);font-size:.84rem}
.tabs{display:flex;gap:8px;align-items:center}
.tab-btn,.tab-link,button{border:1px solid #4d5aa577;background:#0c1230;color:var(--text);padding:8px 12px;border-radius:10px;cursor:pointer;text-decoration:none}
.tab-btn.active{border-color:var(--line);box-shadow:0 0 0 1px var(--line) inset,0 0 14px #2ee6ff44}
.panel{margin-top:18px;padding:18px;border-radius:14px;border:1px solid #5a66bb44;background:linear-gradient(160deg,#121a3d,#0e1433)}
.narrow{max-width:520px;margin:auto}
.tab-panel{display:none}.tab-panel.active{display:block}
.hero-card{display:grid;grid-template-columns:1.1fr .9fr;gap:20px;background:linear-gradient(160deg,#11183b,#0d1230 70%);border:1px solid #5862b34d;border-radius:18px;padding:22px;box-shadow:0 20px 50px #00000066}
.hero-image-wrap{border-radius:14px;overflow:hidden;border:1px solid #6c74c466;box-shadow:0 0 0 1px #2ee6ff2e inset,0 0 28px #ad47ff2a}
.hero-image{display:block;width:100%;height:100%;object-fit:cover}
.table-wrap{overflow:auto}
table{width:100%;border-collapse:collapse}
th,td{padding:10px;border-bottom:1px solid #44509b66;text-align:left}
input,select{width:100%;margin:6px 0;padding:10px;border-radius:10px;border:1px solid #44509b99;background:#0a0f29;color:#fff}
.action-row{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}
.scroll-window{border:1px solid #5a66bb55;border-radius:12px;background:#0b1130cc;overflow:auto;padding:10px}
.avatar-window{max-height:58vh}.about-window{max-height:62vh}
.doc-text{white-space:pre-wrap;word-break:break-word;line-height:1.45;margin:0;padding:12px;border-radius:10px;border:1px solid #5a66bb55;background:#0b1130cc;color:#dbe3ff}
.avatar-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:14px}
.avatar-option{position:relative;display:flex;flex-direction:column;align-items:center;gap:8px;padding:12px;border-radius:12px;border:1px solid #5862b34d;background:linear-gradient(160deg,#101738,#0b1130);cursor:pointer}
.avatar-option input[type="radio"]{position:absolute;opacity:0}
.avatar-option img{width:76px;height:76px;object-fit:cover;border-radius:50%;border:2px solid #7b86d055}
.avatar-option:has(input[type="radio"]:checked){border-color:#2ee6ff;box-shadow:0 0 0 1px #2ee6ff inset,0 0 18px #2ee6ff44}
.chat-wrap{display:grid;grid-template-columns:220px 1fr;gap:12px}
.chat-messages{height:260px;overflow:auto;border:1px solid #5a66bb55;border-radius:10px;padding:8px;background:#0b1130cc}
@media (max-width:960px){.hero-card{grid-template-columns:1fr}.chat-wrap{grid-template-columns:1fr}}
CSSEOF

echo "[7/8] Ensuring .gitignore..."
cat > "$PROJECT_ROOT/.gitignore" <<'GITEOF'
.symondbvenv/
__pycache__/
*.pyc
GITEOF

echo "[8/8] Done."
echo "Backup created at: $BACKUP_DIR"
echo "Next:"
echo "  cd $PROJECT_ROOT"
echo "  chmod +x scripts/apply_symoneural_updates.sh"
echo "  flask run"