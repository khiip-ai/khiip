#!/usr/bin/env bash
# Live recall round-trip smoke for khiipd.
#
# Spins up khiipd with KHIIP_HOME=$(mktemp -d), POSTs a real X tweet,
# verifies /api/v1/recall returns it, and tears down the sandbox.
#
# Hits real upstreams: fxtwitter (X capture) + Hugging Face Hub (first-run
# fastembed MiniLM-L6 download, ~80MB). Does NOT touch the developer's real
# ~/.config/khiip, ~/.local/share/khiip, or ~/khiip-vault — all writes happen
# under the temporary KHIIP_HOME root.
#
# Human-run before tagging a release. NOT wired into CI (upstream flakiness
# would train the team to ignore red builds).
#
# Usage:   make smoke   (or)   bash _scripts/smoke/recall_roundtrip.sh

set -euo pipefail

# Pre-flight: port collision check. If another khiipd (or any HTTP server)
# is already on 127.0.0.1:8478, the smoke's sandbox auth.toml won't match
# the running daemon's and the test would fail confusingly with 401s.
if curl -fsS -m 1 http://127.0.0.1:8478/health >/dev/null 2>&1; then
    echo "✗ port 8478 already in use — is another daemon running?"
    echo "  stop it first (or kill the conflicting process), then re-run smoke."
    exit 1
fi

KHIIP_HOME="$(mktemp -d -t khiip-smoke.XXXXXX)"
export KHIIP_HOME
echo "→ KHIIP_HOME=$KHIIP_HOME"

DAEMON_PID=""
cleanup() {
    if [[ -n "$DAEMON_PID" ]]; then
        kill "$DAEMON_PID" 2>/dev/null || true
        wait "$DAEMON_PID" 2>/dev/null || true
    fi
    rm -rf "$KHIIP_HOME"
    echo "→ teardown complete"
}
trap cleanup EXIT

# Start daemon (first run downloads MiniLM-L6 ~80MB; allow up to 120s)
khiipd serve >"$KHIIP_HOME/daemon.log" 2>&1 &
DAEMON_PID=$!

echo "→ waiting for daemon (up to 120s for first-run model download)..."
READY=0
for _ in $(seq 1 120); do
    if curl -fsS -m 1 http://127.0.0.1:8478/health >/dev/null 2>&1; then
        READY=1
        break
    fi
    sleep 1
done
if [[ "$READY" -eq 0 ]]; then
    echo "✗ daemon failed to start within 120s"
    tail -50 "$KHIIP_HOME/daemon.log"
    exit 1
fi
echo "→ daemon ready"

# Exercise the public CLI surface (khiipd capture / khiipd recall) — the
# same commands documented in the README quickstart. Auth is auto-discovered
# from $KHIIP_HOME/config/auth.toml via ensure_auth().

echo "→ khiipd capture https://x.com/jack/status/20"
khiipd capture https://x.com/jack/status/20 >/dev/null

echo "→ khiipd recall 'first tweet on twitter' --limit 3"
RECALL_OUTPUT=$(khiipd recall "first tweet on twitter" --limit 3)
echo "$RECALL_OUTPUT"

# Each hit is two lines (score+title, then url); count score-prefixed lines.
COUNT=$(echo "$RECALL_OUTPUT" | grep -cE "^  [0-9]+\.[0-9]+  " || true)
if [[ "$COUNT" -lt 1 ]]; then
    echo "✗ recall returned 0 results"
    exit 1
fi
echo "✓ recall returned $COUNT result(s) — smoke passed"
