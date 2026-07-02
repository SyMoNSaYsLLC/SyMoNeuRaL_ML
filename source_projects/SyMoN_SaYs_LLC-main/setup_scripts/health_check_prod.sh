#!/usr/bin/env bash
set -u

DOMAIN="${1:-symoneural.com}"
WWW_DOMAIN="${2:-www.symoneural.com}"
APP_SERVICE="${3:-symoneural}"
WEB_SERVICE="${4:-nginx}"
APP_LOCAL_URL="${5:-http://127.0.0.1:8000}"

PASS=0
WARN=0
FAIL=0

green() { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }
red() { printf "\033[31m%s\033[0m\n" "$*"; }

ok()   { PASS=$((PASS+1)); green "PASS: $*"; }
warn() { WARN=$((WARN+1)); yellow "WARN: $*"; }
bad()  { FAIL=$((FAIL+1)); red "FAIL: $*"; }

have_cmd() { command -v "$1" >/dev/null 2>&1; }

check_service_active() {
  local svc="$1"
  if systemctl is-active --quiet "$svc"; then
    ok "service active: $svc"
  else
    bad "service inactive: $svc"
  fi
}

check_service_enabled() {
  local svc="$1"
  if systemctl is-enabled --quiet "$svc"; then
    ok "service enabled: $svc"
  else
    warn "service not enabled at boot: $svc"
  fi
}

check_port_listener() {
  local port="$1"
  if ss -ltn "( sport = :$port )" | grep -q ":$port"; then
    ok "port listening: $port"
  else
    bad "port not listening: $port"
  fi
}

http_code() {
  local url="$1"
  curl -sS -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000"
}

check_http() {
  local url="$1"
  local code
  code="$(http_code "$url")"
  case "$code" in
    200|301|302|307|308) ok "HTTP reachable ($code): $url" ;;
    *) bad "HTTP failed ($code): $url" ;;
  esac
}

check_dns() {
  local host="$1"
  if ! have_cmd dig; then
    warn "dig not found; skipping DNS check for $host"
    return
  fi
  local out
  out="$(dig +short "$host" | tr '\n' ' ' | sed 's/  */ /g' | sed 's/^ //; s/ $//')"
  if [[ -n "$out" ]]; then
    ok "DNS resolves: $host -> $out"
  else
    bad "DNS does not resolve: $host"
  fi
}

check_tls_cert_days() {
  local host="$1"
  if ! have_cmd openssl; then
    warn "openssl not found; skipping TLS cert check"
    return
  fi

  local enddate end_ts now_ts days
  enddate="$(
    echo | openssl s_client -servername "$host" -connect "${host}:443" 2>/dev/null \
      | openssl x509 -noout -enddate 2>/dev/null \
      | cut -d= -f2
  )"

  if [[ -z "${enddate:-}" ]]; then
    bad "TLS certificate not readable for $host:443"
    return
  fi

  end_ts="$(date -d "$enddate" +%s 2>/dev/null || true)"
  now_ts="$(date +%s)"
  if [[ -z "${end_ts:-}" ]]; then
    warn "could not parse cert expiry for $host ($enddate)"
    return
  fi

  days="$(( (end_ts - now_ts) / 86400 ))"
  if (( days >= 30 )); then
    ok "TLS cert healthy for $host (expires in ${days} days)"
  elif (( days >= 0 )); then
    warn "TLS cert expiring soon for $host (expires in ${days} days)"
  else
    bad "TLS cert expired for $host (${days} days)"
  fi
}

check_nginx_config() {
  # Prefer sudo non-interactive check for accurate result on restricted users.
  if have_cmd sudo && sudo -n nginx -t >/dev/null 2>&1; then
    ok "nginx config test passed (sudo)"
    return
  fi

  # Fallback for environments where user can run nginx -t directly.
  if nginx -t >/dev/null 2>&1; then
    ok "nginx config test passed"
  else
    warn "nginx config test skipped/failed (permission or config). Run: sudo nginx -t"
  fi
}

check_local_header() {
  local hdr
  hdr="$(curl -sSI --max-time 10 "$APP_LOCAL_URL" 2>/dev/null | awk -F': ' 'tolower($1)=="server"{print $2}' | tr -d '\r' | head -n1)"
  if [[ "$hdr" =~ [Gg]unicorn ]]; then
    ok "local app server header indicates gunicorn"
  else
    warn "local app server header unexpected: ${hdr:-<none>}"
  fi
}

echo "=== SyMoNeuRaL Production Health Check ==="
echo "Domain: $DOMAIN"
echo "WWW:    $WWW_DOMAIN"
echo

check_service_active "$APP_SERVICE"
check_service_enabled "$APP_SERVICE"
check_service_active "$WEB_SERVICE"
check_service_enabled "$WEB_SERVICE"

check_port_listener 8000
check_port_listener 80
check_port_listener 443

check_nginx_config
check_local_header

check_dns "$DOMAIN"
check_dns "$WWW_DOMAIN"

check_http "http://127.0.0.1:8000"
check_http "http://$DOMAIN"
check_http "https://$DOMAIN"
check_http "https://$WWW_DOMAIN"

check_tls_cert_days "$DOMAIN"

echo
echo "=== Summary ==="
echo "PASS: $PASS"
echo "WARN: $WARN"
echo "FAIL: $FAIL"

if (( FAIL > 0 )); then
  exit 1
fi
exit 0