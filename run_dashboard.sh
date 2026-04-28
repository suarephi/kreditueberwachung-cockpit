#!/usr/bin/env bash
# Launches the password-gated Streamlit cockpit + a Cloudflare quick tunnel.
# Survives this shell exiting via `setsid` (process group detach).
# Re-run this script any time to bring it back up.
set -euo pipefail

cd "$(dirname "$0")"

PORT=8765
SETSID="/opt/homebrew/opt/util-linux/bin/setsid"
[ -x "$SETSID" ] || SETSID="setsid"   # fall back to PATH if user installed it elsewhere

# 1) kill anything from previous runs
lsof -ti:"$PORT" 2>/dev/null | xargs kill -9 2>/dev/null || true
pkill -f "cloudflared tunnel" 2>/dev/null || true
sleep 1

# 2) launch streamlit detached, bound to all interfaces (IPv4 + IPv6)
"$SETSID" -f .venv/bin/python -m streamlit run dashboard/app.py \
  --server.port "$PORT" \
  --server.address 0.0.0.0 \
  --server.headless true \
  --browser.gatherUsageStats false \
  >> /tmp/ku_dashboard.log 2>&1 < /dev/null &
disown 2>/dev/null || true

# 3) wait for streamlit to be up
for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:$PORT/_stcore/health" >/dev/null 2>&1; then break; fi
  sleep 1
done

# 4) launch cloudflared pointing at IPv4 explicitly
: > /tmp/ku_tunnel.log
"$SETSID" -f cloudflared tunnel \
  --url "http://127.0.0.1:$PORT" \
  --no-autoupdate \
  >> /tmp/ku_tunnel.log 2>&1 < /dev/null &
disown 2>/dev/null || true

# 5) wait for the public URL to appear in the tunnel log
for i in $(seq 1 30); do
  URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" /tmp/ku_tunnel.log | head -1)
  [ -n "${URL:-}" ] && break
  sleep 1
done

echo
echo "============================================================"
echo "  Streamlit:  http://localhost:$PORT"
echo "  Public URL: ${URL:-(not yet available — tail /tmp/ku_tunnel.log)}"
echo "  Password:   ilovekpmg"
echo "  Logs:       /tmp/ku_dashboard.log  /tmp/ku_tunnel.log"
echo "============================================================"
