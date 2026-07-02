# SyMoNeuRaLSQLDB_APP

Production-oriented Flask application for:
- authentication (login/register/logout)
- user profile + avatar selection
- account security (password changes)
- dashboard tabs (overview/about/account/chat)
- team chat + online presence
- JSON-driven UI copy/content

---

## 1) System Overview

### Core stack
- **Backend:** Flask (`app.py`)
- **Templates:** Jinja2 (`templates/`)
- **Static assets:** CSS/images/avatars/data (`static/`)
- **Runtime server (prod):** Gunicorn
- **Edge proxy (prod):** Nginx
- **Service management (prod):** systemd
- **Database:** SQL DB (permissions required for schema changes)

### Key directories
- `app.py` — main application entrypoint/routes/startup checks
- `templates/` — `landing.html`, `login.html`, `register.html`, `index.html`, `select_avatar.html`
- `static/styles.css` — unified site styling
- `static/avatars/` — avatar images
- `static/brand/` — brand images
- `static/data/ui_content.json` — centralized UI text/content config
- `setup_scripts/` — project update scripts
- `.backup_*` — script-created backup snapshots

---

## 2) Features by Module

### A) Landing
- Brand headline/summary
- Core services list
- CTA links (Create Account, Login, Request Service)
- Structured data support via JSON-LD (if enabled in template)

### B) Auth
- Register with password/confirm
- Login
- Flash message support for errors/success

### C) Dashboard
- Tabbed layout: Overview / About / Account / Chat
- Overview content + hero media
- About panel with company overview text
- Account management and quick avatar selection
- Chat panel with online users and message feed

### D) Account
- Current avatar display
- Quick avatar embedded picker
- Full avatar library route (`select_avatar`)
- Password update form

### E) Chat + Presence
- Polling endpoints for online users/messages
- Message submit form
- Presence ping intervals from dashboard JS

### F) JSON-driven content
- UI labels/headlines are sourced from `static/data/ui_content.json`
- Enables content updates without editing HTML templates

---

## 3) Environment and Requirements

- Linux host
- Python 3.10+ recommended
- Virtual environment (`venv`)
- Optional production packages:
  - `gunicorn`
  - `nginx`
  - `systemd` (standard on most Linux distros)

Install dependencies:

```bash
python3 -m venv .symondbvenv
source .symondbvenv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

---

## 4) Configuration Model

### Runtime mode toggle
The app supports migration behavior through:

- `DB_AUTO_MIGRATE=0` → normal runtime (recommended)
- `DB_AUTO_MIGRATE=1` → maintenance mode for schema updates (admin only)

> Keep `DB_AUTO_MIGRATE=0` for all normal production service runs.

### Recommended environment variables
Define these in your shell/systemd as needed:

- `FLASK_ENV` (optional for local only)
- `DATABASE_URL` (or project DB settings)
- `DB_AUTO_MIGRATE` (`0` in prod)
- any app-specific secret/session variables your app requires

---

## 5) Local Development Workflow

```bash
cd /home/google/Desktop/SyMoNeuRaLSQLDB_APP
source .symondbvenv/bin/activate
flask run
```

Notes:
- Flask dev server is for development only.
- Use Gunicorn for production.

---

## 6) Production Deployment Workflow

## 6.1 Start app with Gunicorn (manual test)
```bash
cd /home/google/Desktop/SyMoNeuRaLSQLDB_APP
source .symondbvenv/bin/activate
DB_AUTO_MIGRATE=0 gunicorn -w 3 -b 127.0.0.1:8000 app:app
```

## 6.2 systemd service (persistent)
Create:

`/etc/systemd/system/symoneural.service`

```ini
[Unit]
Description=SyMoNeuRaLSQLDB Gunicorn Service
After=network.target

[Service]
User=google
Group=www-data
WorkingDirectory=/home/google/Desktop/SyMoNeuRaLSQLDB_APP
Environment="PATH=/home/google/Desktop/SyMoNeuRaLSQLDB_APP/.symondbvenv/bin"
Environment="DB_AUTO_MIGRATE=0"
ExecStart=/home/google/Desktop/SyMoNeuRaLSQLDB_APP/.symondbvenv/bin/gunicorn -w 3 -b 127.0.0.1:8000 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable/start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now symoneural
sudo systemctl status symoneural
```

View logs:
```bash
journalctl -u symoneural -f
```

## 6.3 Nginx reverse proxy
Create:

`/etc/nginx/sites-available/symoneural`

```nginx
server {
    listen 80;
    server_name _;

    client_max_body_size 20m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120;
    }
}
```

Enable:
```bash
sudo ln -sf /etc/nginx/sites-available/symoneural /etc/nginx/sites-enabled/symoneural
sudo nginx -t
sudo systemctl reload nginx
```

---

## 7) Database Migration / Schema Maintenance

### Important
Schema changes are **admin tasks**, not user login tasks.

### Standard runtime
```bash
DB_AUTO_MIGRATE=0
```

### One-time maintenance window (admin only)
Run with privileged DB credentials:
```bash
cd /home/google/Desktop/SyMoNeuRaLSQLDB_APP
source .symondbvenv/bin/activate
DB_AUTO_MIGRATE=1 gunicorn -w 1 -b 127.0.0.1:8000 app:app
```

After schema task completes, stop and return to normal runtime (`DB_AUTO_MIGRATE=0`).

---

## 8) Upgrade and Maintenance Runbook

### Before any upgrade
1. Pull/update code.
2. Snapshot backups:
   - database backup
   - app folder backup
3. Validate scripts before execution.

### Script validation/execution
```bash
bash -n setup_scripts/apply_round_three_update.sh
chmod +x setup_scripts/apply_round_three_update.sh
./setup_scripts/apply_round_three_update.sh
```

### Post-upgrade verification
- App boots with Gunicorn
- Login/register works
- Dashboard tabs load
- Account update/password flows pass
- Avatar picker displays curated avatars only
- Chat/presence endpoints respond
- No template rendering errors
- No startup migration warnings in prod mode

### Rollback
- Use generated `.backup_*` directories for templates/static restore
- Restore database from backup if schema/data change failed
- Redeploy known-good commit

---

## 9) UI Content Operations (`ui_content.json`)

Path:
- `static/data/ui_content.json`

Use it for:
- titles/headlines/button labels
- dashboard tab labels
- chat labels/placeholders
- curated avatar list

Validate JSON:
```bash
python -m json.tool static/data/ui_content.json >/dev/null && echo "JSON valid"
```

Notes:
- JSON must not contain comments.
- Ensure keys used by templates exist or have fallback defaults.

---

## 10) Avatar Governance

### Curated strategy
- Keep only approved names in `avatars.curated` in JSON.
- Backend should validate submitted avatar values against curated list.
- Optional: physically remove unapproved files from `static/avatars/`.

### Recommended checks
- Missing curated file → ignore automatically
- Empty curated list → fallback to default avatar (e.g., `user.png`)

---

## 11) Security and Operations Best Practices

- Never use Flask dev server in production.
- Keep Gunicorn bound to localhost when using Nginx.
- Restrict DB privileges for runtime account.
- Use admin/owner account only during migration windows.
- Rotate secrets and DB credentials regularly.
- Keep OS packages and Python dependencies updated.
- Monitor logs (`journalctl`, Nginx logs).
- Use HTTPS (Certbot/Nginx) for internet-exposed deployments.

---

## 12) Troubleshooting Quick Reference

### `flask db` command missing
Cause: Flask-Migrate is not configured.  
Action: use your app’s custom migration flow (`DB_AUTO_MIGRATE`) or implement Alembic/Flask-Migrate separately.

### Startup warning: insufficient privilege for migrations
Cause: app attempted schema operation with non-owner DB user.  
Action: run normal mode with `DB_AUTO_MIGRATE=0`; do maintenance run as DB owner/admin.

### Gunicorn starts but site unreachable
- Verify process:
  ```bash
  ss -ltnp | grep :8000
  ```
- Verify service logs:
  ```bash
  journalctl -u symoneural -n 200 --no-pager
  ```
- Verify Nginx:
  ```bash
  sudo nginx -t
  sudo systemctl status nginx
  ```

### Broken template or CSS after update
- restore from latest `.backup_*` folder
- re-run update script after validation

---

## 13) Recommended Admin Tasks (Recurring)

Daily:
- check service health/logs
- verify login and dashboard load

Weekly:
- validate backups
- dependency/security review
- verify disk usage/log growth

Monthly:
- patch OS + libraries
- perform controlled maintenance window
- review DB permissions and access

Per release:
- run upgrade script
- run smoke tests
- document changes
- tag/version release

---

## 14) License

See `LICENSE` in project root.

## 15) Operations Logging (File-First, Not Terminal)

All production/admin commands should log to files under `logs/ops/`.

### 15.1 Create log directory
```bash
cd /home/google/Desktop/SyMoNeuRaLSQLDB_APP
mkdir -p logs/ops
```

### 15.2 Standard log pattern (timestamped)
```bash
TS="$(date +%Y%m%d_%H%M%S)"
LOG="logs/ops/run_${TS}.log"
```

### 15.3 Health check to file
```bash
TS="$(date +%Y%m%d_%H%M%S)"; LOG="logs/ops/health_${TS}.log"
./setup_scripts/health_check_prod.sh >"$LOG" 2>&1
echo "saved: $LOG"
```

### 15.4 Service status checks to file
```bash
TS="$(date +%Y%m%d_%H%M%S)"; LOG="logs/ops/services_${TS}.log"
{
  echo "=== systemctl status symoneural ==="
  sudo systemctl status symoneural --no-pager
  echo
  echo "=== systemctl status nginx ==="
  sudo systemctl status nginx --no-pager
} >"$LOG" 2>&1
echo "saved: $LOG"
```

### 15.5 Nginx validation to file
```bash
TS="$(date +%Y%m%d_%H%M%S)"; LOG="logs/ops/nginx_test_${TS}.log"
sudo nginx -t >"$LOG" 2>&1
echo "saved: $LOG"
```

### 15.6 DNS + HTTP/TLS checks to file
```bash
TS="$(date +%Y%m%d_%H%M%S)"; LOG="logs/ops/network_${TS}.log"
{
  echo "=== DNS ==="
  dig +short symoneural.com
  dig +short www.symoneural.com
  echo
  echo "=== HTTP/TLS ==="
  curl -I http://symoneural.com
  curl -I https://symoneural.com
  curl -I https://www.symoneural.com
} >"$LOG" 2>&1
echo "saved: $LOG"
```

### 15.7 Migration maintenance run to file (admin window only)
```bash
TS="$(date +%Y%m%d_%H%M%S)"; LOG="logs/ops/migrate_${TS}.log"
DB_AUTO_MIGRATE=1 /home/google/Desktop/SyMoNeuRaLSQLDB_APP/.symondbvenv/bin/gunicorn -w 1 -b 127.0.0.1:8000 app:app >"$LOG" 2>&1
echo "saved: $LOG"
```

### 15.8 Normal production run to file (manual mode)
```bash
TS="$(date +%Y%m%d_%H%M%S)"; LOG="logs/ops/prod_${TS}.log"
DB_AUTO_MIGRATE=0 /home/google/Desktop/SyMoNeuRaLSQLDB_APP/.symondbvenv/bin/gunicorn -w 3 -b 127.0.0.1:8000 app:app >"$LOG" 2>&1
echo "saved: $LOG"
```

### 15.9 View log files safely
```bash
ls -1 logs/ops
tail -n 120 logs/ops/<logfile>.log
```

### 15.10 Optional: keep terminal quiet but preserve log + exit code
```bash
TS="$(date +%Y%m%d_%H%M%S)"; LOG="logs/ops/task_${TS}.log"
your_command >"$LOG" 2>&1; RC=$?
echo "saved: $LOG (exit=$RC)"
exit $RC
```
