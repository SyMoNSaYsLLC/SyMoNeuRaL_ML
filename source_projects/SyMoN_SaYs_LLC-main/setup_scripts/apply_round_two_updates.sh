#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/home/google/Desktop/SyMoNeuRaLSQLDB_APP"
cd "$PROJECT_ROOT"

TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$PROJECT_ROOT/.backup_professional_now_$TS"
mkdir -p "$BACKUP_DIR/templates" "$BACKUP_DIR/static"

echo "[1/7] Backup files..."
for f in app.py templates/landing.html templates/index.html static/styles.css; do
  [[ -f "$f" ]] && cp -f "$f" "$BACKUP_DIR/$f"
done

echo "[2/7] Ensure brand/doc asset paths..."
mkdir -p static/brand static/docs

# icon
if [[ -f symonicon.png ]]; then
  cp -f symonicon.png static/brand/symonicon.png
fi

# featured image
if [[ -f SyMoNeuRaL.jpg ]]; then
  cp -f SyMoNeuRaL.jpg static/brand/symoneural.jpg
elif [[ -f SyMoNeuRaL.jpg ]]; then
  cp -f SyMoNeuRaL.jpg static/brand/symoneural.jpg
fi

# about doc
if [[ -f SymonSaysKickoffv3.txt ]]; then
  cp -f SymonSaysKickoffv3.txt static/docs/company-overview.txt
elif [[ -f docs/SymonSaysKickoffv3.txt ]]; then
  cp -f docs/SymonSaysKickoffv3.txt static/docs/company-overview.txt
fi

echo "[3/7] Write app.py..."
cat > app.py <<'PYEOF'
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
import psycopg
import psycopg.errors
import os
import random
from pathlib import Path

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-change-this")

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://symoneural_user:symon_says_secure_password@localhost/symoneural_db"
)

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


@app.route("/select_avatar", methods=["GET", "POST"])
@login_required
def select_avatar():
    avatars = get_avatar_choices()

    if request.method == "POST":
        selected = (request.form.get("avatar") or "").strip()
        if selected in avatars:
            with psycopg.connect(DB_URL) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE user_profiles SET photo_path = %s WHERE username = %s;",
                        (f"avatars/{selected}", current_user.username),
                    )
            flash("Avatar updated.", "success")
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

    flash("Password updated.", "success")
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
                ORDER BY username;
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
        {"id": r[0], "username": r[1], "body": r[2], "created_at": r[3].isoformat()}
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
            cursor.execute(
                "INSERT INTO chat_messages (sender_username, body) VALUES (%s, %s);",
                (current_user.username, body),
            )
            cursor.execute(
                "UPDATE user_profiles SET last_seen = NOW() WHERE username = %s;",
                (current_user.username,),
            )

    return jsonify({"ok": True})


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("landing"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
PYEOF

echo "[4/7] Write landing template..."
cat > templates/landing.html <<'HTMLEOF'
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SyMoNeuRaL | System Integration & Automation</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
  <main class="layout">
    <section class="panel">
      <div class="landing-header">
        <img src="{{ url_for('static', filename='brand/symonicon.png') }}" alt="SyMoNeuRaL Icon" class="brand-icon">
        <div>
          <h2>SyMoNeuRaL — System Integration & Automation</h2>
          <p>
            Professional system integration and automation services for organizations in the Lake Norman, NC region.
            We design practical solutions that improve reliability, reduce manual effort, and support long-term growth.
          </p>
        </div>
      </div>

      <div class="landing-featured">
        <img src="{{ url_for('static', filename='brand/symoneural.jpg') }}" alt="SyMoNeuRaL featured architecture">
      </div>

      <h3>Core Services</h3>
      <ul>
        <li>System integration across software, devices, and operational workflows</li>
        <li>Process automation and workflow orchestration</li>
        <li>Legacy modernization and migration planning</li>
        <li>Deployment standardization and operational support</li>
      </ul>

      <div class="action-row">
        <a class="tab-link" href="{{ url_for('register') }}">Create Account</a>
        <a class="tab-link" href="{{ url_for('login') }}">Client Login</a>
        <a class="tab-link"
           href="mailto:gmcdonald@symoneural.com,bhesley@symoneural.com?subject=Service%20Request&body=Hello%20SyMoNeuRaL%20Team,%0D%0A%0D%0APlease%20provide%20information%20about%20your%20needs:%0D%0A-%20Business%20or%20project%20overview%0D%0A-%20Current%20systems%20and%20tools%0D%0A-%20Goals%20and%20timeline%0D%0A-%20Preferred%20budget%20range%0D%0A%0D%0AWe%20will%20review%20and%20provide%20a%20quote.%0D%0A">
          Request Service
        </a>
      </div>
    </section>
  </main>
</body>
</html>
HTMLEOF

echo "[5/7] Write index template..."
cat > templates/index.html <<'HTMLEOF'
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
      <button class="tab-btn" data-tab="chat">Chat Session</button>
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
          <h2>System Integration & Automation — Lake Norman, NC</h2>
          <p>Business-focused engineering services to unify systems, modernize operations, and improve reliability.</p>
          <ul>
            <li>End-to-end systems integration</li>
            <li>Workflow automation and orchestration</li>
            <li>Legacy modernization with controlled rollout</li>
            <li>Operational stability and support</li>
          </ul>
        </div>
        <div class="hero-image-wrap">
          <img src="{{ url_for('static', filename='brand/symoneural.jpg') }}" alt="SyMoNeuRaL architecture" class="hero-image">
        </div>
      </div>
    </section>

    <section id="about" class="tab-panel">
      <article class="panel">
        <h3>Company Overview</h3>
        <div class="scroll-window about-window">
          <pre class="doc-text">{{ company_overview }}</pre>
        </div>
      </article>
    </section>

    <section id="account" class="tab-panel">
      <article class="panel">
        <h3>Account Settings</h3>
        <p>
          Current avatar:
          <img src="{{ url_for('static', filename=user.photo_path or 'avatars/user.png') }}"
               alt="avatar" style="width:36px;height:36px;border-radius:50%;vertical-align:middle;">
        </p>
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
    </section>

    <section id="chat" class="tab-panel">
      <article class="panel">
        <h3>Online Team Chat</h3>
        <div class="chat-wrap">
          <div>
            <h4>Online Users</h4>
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
        const r = await fetch('/api/online');
        const data = await r.json();
        document.getElementById('onlineUsers').innerHTML = data.map(u => `<li>${u.username}</li>`).join('');
      } catch(_) {}
    }
    async function loadMessages(){
      try {
        const r = await fetch('/api/chat/messages?since_id=' + lastId);
        const data = await r.json();
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
        const fd = new FormData();
        fd.append('body', body);
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

echo "[6/7] Write styles..."
cat > static/styles.css <<'CSSEOF'
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
.tab-panel{display:none}.tab-panel.active{display:block}
.hero-card{display:grid;grid-template-columns:1.1fr .9fr;gap:20px;background:linear-gradient(160deg,#11183b,#0d1230 70%);border:1px solid #5862b34d;border-radius:18px;padding:22px;box-shadow:0 20px 50px #00000066}
.hero-image-wrap{border-radius:14px;overflow:hidden;border:1px solid #6c74c466;box-shadow:0 0 0 1px #2ee6ff2e inset,0 0 28px #ad47ff2a}
.hero-image{display:block;width:100%;height:100%;object-fit:cover}
input,select{width:100%;margin:6px 0;padding:10px;border-radius:10px;border:1px solid #44509b99;background:#0a0f29;color:#fff}
.action-row{display:flex;gap:10px;flex-wrap:wrap;margin-top:10px}
.scroll-window{border:1px solid #5a66bb55;border-radius:12px;background:#0b1130cc;overflow:auto;padding:10px}
.about-window{max-height:62vh}
.doc-text{white-space:pre-wrap;word-break:break-word;line-height:1.45;margin:0;padding:12px;border-radius:10px;border:1px solid #5a66bb55;background:#0b1130cc;color:#dbe3ff}
.chat-wrap{display:grid;grid-template-columns:220px 1fr;gap:12px}
.chat-messages{height:260px;overflow:auto;border:1px solid #5a66bb55;border-radius:10px;padding:8px;background:#0b1130cc}
.landing-header{display:grid;grid-template-columns:72px 1fr;gap:14px;align-items:start}
.brand-icon{width:64px;height:64px;border-radius:12px;border:1px solid #5a66bb66;box-shadow:0 0 20px #ad47ff33}
.landing-featured{margin:14px 0 10px;border:1px solid #5a66bb66;border-radius:14px;overflow:hidden}
.landing-featured img{display:block;width:100%;height:auto}
@media (max-width:960px){.hero-card{grid-template-columns:1fr}.chat-wrap{grid-template-columns:1fr}.topbar{padding:16px 20px}}
CSSEOF

echo "[7/7] Done."
echo "Backup: $BACKUP_DIR"
echo "Run:"
echo "  flask run"