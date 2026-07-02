#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/home/google/Desktop/SyMoNeuRaLSQLDB_APP"
cd "$PROJECT_ROOT"

TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$PROJECT_ROOT/.backup_unify_ui_$TS"
mkdir -p "$BACKUP_DIR/templates" "$BACKUP_DIR/static"

echo "[1/5] Backing up templates + styles..."
for f in templates/landing.html templates/index.html templates/login.html templates/register.html templates/select_avatar.html static/styles.css; do
  [[ -f "$f" ]] && cp -f "$f" "$BACKUP_DIR/$f"
done

echo "[2/5] Writing unified styles..."
cat > static/styles.css <<'CSSEOF'
:root{
  --bg:#070b1f; --card:#121a3d; --line:#2ee6ff; --line2:#ad47ff;
  --text:#dfe7ff; --muted:#9caae3; --ink:#bfcaf7;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;font-family:Inter,Segoe UI,Arial,sans-serif;color:var(--text);
background:radial-gradient(1200px 800px at 70% 0%, #1b1d59 0%, var(--bg) 60%)}
.bg-grid{position:fixed;inset:0;pointer-events:none;opacity:.12;
background-image:linear-gradient(to right,#4d5aa533 1px,transparent 1px),linear-gradient(to bottom,#4d5aa533 1px,transparent 1px);
background-size:40px 40px}
.layout{max-width:1180px;margin:20px auto;padding:0 20px 28px}
.topbar{display:flex;justify-content:space-between;align-items:center;padding:20px 28px;position:sticky;top:0;backdrop-filter:blur(6px);z-index:2}
.brand{display:flex;gap:12px;align-items:center}
.logo{width:38px;height:38px;border-radius:10px;display:grid;place-items:center;background:linear-gradient(135deg,var(--line2),#6a5cff);font-weight:800}
.brand h1{margin:0;font-size:1.08rem}.brand p{margin:2px 0 0;color:var(--muted);font-size:.84rem}

.panel{
  margin-top:18px;padding:22px;border-radius:16px;border:1px solid #6f7ad14f;
  background:
    radial-gradient(900px 340px at 0% 0%, #2ee6ff16 0%, transparent 60%),
    radial-gradient(900px 340px at 100% 100%, #ad47ff1a 0%, transparent 60%),
    linear-gradient(160deg,#121a3d,#0d1432);
  box-shadow:0 20px 50px #00000066;
}
.narrow{max-width:560px;margin:30px auto}
.tabs{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.tab-btn,.tab-link,button{
  border:1px solid #4d5aa577;background:#0c1230;color:var(--text);padding:8px 12px;border-radius:10px;cursor:pointer;text-decoration:none
}
.tab-btn.active{border-color:var(--line);box-shadow:0 0 0 1px var(--line) inset,0 0 14px #2ee6ff44}
.tab-link.cta-primary{
  background:linear-gradient(135deg,#00d7ff 0%, #8d4bff 100%);
  border-color:transparent;color:#fff;font-weight:600;box-shadow:0 8px 22px #7a4dff4a
}
.tab-panel{display:none}.tab-panel.active{display:block}

input,select{
  width:100%;margin:6px 0;padding:11px 12px;border-radius:10px;border:1px solid #44509b99;background:#0a0f29;color:#fff
}
.action-row{display:flex;gap:10px;flex-wrap:wrap;margin-top:18px}
ul{color:var(--ink)}
h2,h3,h4{margin:0 0 10px}
p{color:#c5d0ff}

.landing-layout{display:flex;justify-content:center}
.landing-panel{width:min(1020px,100%);margin-top:28px;padding:34px 36px}
.landing-badge{display:inline-block;padding:6px 12px;border:1px solid #6f7ad180;border-radius:999px;color:#a9b5e9;font-size:.82rem;margin-bottom:14px}
.landing-header{display:grid;grid-template-columns:84px 1fr;gap:18px;align-items:center}
.landing-header h2{
  font-size:2rem;line-height:1.1;margin:0 0 6px;
  background:linear-gradient(90deg,#dfe7ff 0%, #7deaff 45%, #cf9bff 100%);
  -webkit-background-clip:text;background-clip:text;color:transparent;text-align:center
}
.landing-lead{text-align:center}
.brand-icon{width:76px;height:76px;border-radius:12px;border:1px solid #5a66bb66;box-shadow:0 0 20px #ad47ff33}
.landing-featured{margin:18px auto 16px;border:1px solid #6f7ad173;border-radius:14px;overflow:hidden;box-shadow:0 0 0 1px #2ee6ff25 inset,0 12px 34px #00000066}
.landing-featured img{display:block;width:100%;height:auto}
.core-services{margin:2px 0 0;padding-left:20px}
.core-services li{margin:8px 0}
.landing-panel .action-row{margin-top:24px;justify-content:center}

.hero-card{display:grid;grid-template-columns:1.1fr .9fr;gap:20px;border:1px solid #5862b34d;border-radius:18px;padding:22px;background:linear-gradient(160deg,#11183b,#0d1230 70%)}
.hero-image-wrap{border-radius:14px;overflow:hidden;border:1px solid #6c74c466;box-shadow:0 0 0 1px #2ee6ff2e inset,0 0 28px #ad47ff2a}
.hero-image{display:block;width:100%;height:100%;object-fit:cover}

.scroll-window{border:1px solid #5a66bb55;border-radius:12px;background:#0b1130cc;overflow:auto;padding:10px}
.about-window{max-height:62vh}
.doc-text{white-space:pre-wrap;word-break:break-word;line-height:1.45;margin:0;padding:12px;border-radius:10px;border:1px solid #5a66bb55;background:#0b1130cc;color:#dbe3ff}

.avatar-window{max-height:58vh}
.avatar-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:14px}
.avatar-option{position:relative;display:flex;flex-direction:column;align-items:center;gap:8px;padding:12px;border-radius:12px;border:1px solid #5862b34d;background:linear-gradient(160deg,#101738,#0b1130);cursor:pointer}
.avatar-option input[type="radio"]{position:absolute;opacity:0}
.avatar-option img{width:76px;height:76px;object-fit:cover;border-radius:50%;border:2px solid #7b86d055}
.avatar-option:has(input[type="radio"]:checked){border-color:#2ee6ff;box-shadow:0 0 0 1px #2ee6ff inset,0 0 18px #2ee6ff44}

.chat-wrap{display:grid;grid-template-columns:220px 1fr;gap:12px}
.chat-messages{height:260px;overflow:auto;border:1px solid #5a66bb55;border-radius:10px;padding:8px;background:#0b1130cc}

@media (max-width:960px){
  .hero-card{grid-template-columns:1fr}
  .chat-wrap{grid-template-columns:1fr}
  .topbar{padding:16px 20px}
}
@media (max-width:760px){
  .landing-panel{padding:22px 18px}
  .landing-header{grid-template-columns:1fr}
}
CSSEOF

echo "[3/5] Writing unified templates..."
cat > templates/landing.html <<'HTMLEOF'
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SyMoNeuRaL | System Integration & Automation</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
<div class="bg-grid"></div>
<main class="layout landing-layout">
  <section class="panel landing-panel">
    <div class="landing-badge">Lake Norman, NC • System Integration & Automation</div>
    <div class="landing-header">
      <img src="{{ url_for('static', filename='brand/symonicon.png') }}" alt="SyMoNeuRaL Icon" class="brand-icon">
      <div>
        <h2>SyMoNeuRaL</h2>
        <p class="landing-lead">Professional integration and automation solutions that improve reliability, reduce manual effort, and modernize operations.</p>
      </div>
    </div>
    <div class="landing-featured">
      <img src="{{ url_for('static', filename='brand/symoneural.jpg') }}" alt="SyMoNeuRaL featured architecture">
    </div>
    <h3>Core Services</h3>
    <ul class="core-services">
      <li>System integration across software, devices, and workflows</li>
      <li>Process automation and orchestration</li>
      <li>Legacy modernization and migration planning</li>
      <li>Deployment standardization and operational support</li>
    </ul>
    <div class="action-row">
      <a class="tab-link cta-primary" href="{{ url_for('register') }}">Create Account</a>
      <a class="tab-link" href="{{ url_for('login') }}">Client Login</a>
      <a class="tab-link" href="mailto:gmcdonald@symoneural.com,bhesley@symoneural.com?subject=Service%20Request&body=Hello%20SyMoNeuRaL%20Team,%0D%0A%0D%0APlease%20provide%20information%20about%20your%20needs:%0D%0A-%20Business%20or%20project%20overview%0D%0A-%20Current%20systems%20and%20tools%0D%0A-%20Goals%20and%20timeline%0D%0A-%20Preferred%20budget%20range%0D%0A%0D%0AWe%20will%20review%20and%20provide%20a%20quote.%0D%0A">Request Service</a>
    </div>
  </section>
</main>
</body>
</html>
HTMLEOF

cat > templates/login.html <<'HTMLEOF'
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Login | SyMoNeuRaL</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
<div class="bg-grid"></div>
<main class="layout">
  <section class="panel narrow">
    <h2>Client Login</h2>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}{% for category, message in messages %}<p>{{ message }}</p>{% endfor %}{% endif %}
    {% endwith %}
    <form method="post" action="{{ url_for('login') }}">
      <input name="username" placeholder="Username" required>
      <input type="password" name="password" placeholder="Password" required>
      <button type="submit">Sign In</button>
    </form>
    <div class="action-row">
      <a class="tab-link cta-primary" href="{{ url_for('register') }}">Create Account</a>
      <a class="tab-link" href="{{ url_for('landing') }}">Back to Home</a>
    </div>
  </section>
</main>
</body>
</html>
HTMLEOF

cat > templates/register.html <<'HTMLEOF'
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Create Account | SyMoNeuRaL</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
<div class="bg-grid"></div>
<main class="layout">
  <section class="panel narrow">
    <h2>Create Account</h2>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% if messages %}{% for category, message in messages %}<p>{{ message }}</p>{% endfor %}{% endif %}
    {% endwith %}
    <form method="post">
      <input name="full_name" placeholder="Full name" required>
      <input name="username" placeholder="Username" required>
      <input type="password" name="password" placeholder="Password (min 8)" minlength="8" required>
      <input type="password" name="confirm_password" placeholder="Confirm password" minlength="8" required>
      <button type="submit">Create Account</button>
    </form>
    <div class="action-row">
      <a class="tab-link" href="{{ url_for('login') }}">Already have an account? Login</a>
    </div>
  </section>
</main>
</body>
</html>
HTMLEOF

cat > templates/select_avatar.html <<'HTMLEOF'
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Select Avatar | SyMoNeuRaL</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
</head>
<body>
<div class="bg-grid"></div>
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
      <div class="action-row">
        <button type="submit">Save Avatar</button>
        <a class="tab-link" href="{{ url_for('home', tab='account') }}">Back</a>
      </div>
    </form>
  </section>
</main>
</body>
</html>
HTMLEOF

cat > templates/index.html <<'HTMLEOF'
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" /><meta name="viewport" content="width=device-width, initial-scale=1.0" />
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
    {% if messages %}<section class="panel">{% for category, message in messages %}<p>{{ message }}</p>{% endfor %}</section>{% endif %}
  {% endwith %}

  <section id="overview" class="tab-panel">
    <div class="hero-card">
      <div>
        <h2>System Integration & Automation — Lake Norman, NC</h2>
        <p>Business-focused engineering to unify systems and improve operational reliability.</p>
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
      <div class="scroll-window about-window"><pre class="doc-text">{{ company_overview }}</pre></div>
    </article>
  </section>

  <section id="account" class="tab-panel">
    <article class="panel">
      <h3>Account Settings</h3>
      <p>Current avatar:
        <img src="{{ url_for('static', filename=user.photo_path or 'avatars/user.png') }}" alt="avatar" style="width:36px;height:36px;border-radius:50%;vertical-align:middle;">
      </p>
      <div class="action-row"><a class="tab-link" href="{{ url_for('select_avatar') }}">Open Avatar Picker</a></div>
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
        <div><h4>Online Users</h4><ul id="onlineUsers"></ul></div>
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
const buttons=document.querySelectorAll('.tab-btn');
const panels=document.querySelectorAll('.tab-panel');
const initialTab="{{ initial_tab|default('overview') }}";
function activateTab(tab){buttons.forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));panels.forEach(p=>p.classList.toggle('active',p.id===tab));}
buttons.forEach(btn=>btn.addEventListener('click',()=>activateTab(btn.dataset.tab)));activateTab(initialTab);

let lastId=0;
async function ping(){try{await fetch('/api/presence/ping',{method:'POST'});}catch(_){}}
async function loadOnline(){try{const r=await fetch('/api/online');const d=await r.json();document.getElementById('onlineUsers').innerHTML=d.map(u=>`<li>${u.username}</li>`).join('');}catch(_){}}
async function loadMessages(){try{const r=await fetch('/api/chat/messages?since_id='+lastId);const d=await r.json();const box=document.getElementById('chatMessages');d.forEach(m=>{lastId=m.id;const row=document.createElement('div');row.textContent=`[${m.created_at}] ${m.username}: ${m.body}`;box.appendChild(row);});box.scrollTop=box.scrollHeight;}catch(_){}}
const f=document.getElementById('chatForm');
if(f){f.addEventListener('submit',async(e)=>{e.preventDefault();const i=document.getElementById('chatInput');const body=i.value.trim();if(!body)return;const fd=new FormData();fd.append('body',body);await fetch('/api/chat/messages',{method:'POST',body:fd});i.value='';loadMessages();});
setInterval(ping,20000);setInterval(loadOnline,5000);setInterval(loadMessages,2000);ping();loadOnline();loadMessages();}
</script>
</body>
</html>
HTMLEOF

echo "[4/5] Ensuring icon/image assets..."
mkdir -p static/brand

# Keep existing files if present; only copy from project root when missing.
if [[ ! -f static/brand/symonicon.png ]]; then
  if [[ -f symonicon.png ]]; then
    cp -f symonicon.png static/brand/symonicon.png
  else
    echo "WARN: symonicon.png not found at project root; keeping existing static/brand file if present."
  fi
fi

if [[ ! -f static/brand/symoneural.jpg ]]; then
  if [[ -f SyMoNeuRaL.jpg ]]; then
    cp -f SyMoNeuRaL.jpg static/brand/symoneural.jpg
  else
    echo "WARN: SyMoNeuRaL.jpg not found at project root; keeping existing static/brand file if present."
  fi
fi

echo "[5/5] Done."
echo "Backup saved to: $BACKUP_DIR"
echo "Now run: flask run"