#!/usr/bin/env bash
# Block "Co-Authored-By: Claude*" trailers from commit messages.
#
# Project norm 2026-05-19: AI co-authorship is not recorded in git history.
# Convention follows current OSS practice — Claude, Copilot, Cursor, Codex,
# and other coding assistants are heavily used across the ecosystem but rarely
# co-authored on commits.
#
# Installed via .pre-commit-config.yaml at the commit-msg stage. Run
# `pre-commit install --hook-type commit-msg` once after cloning to activate.

set -euo pipefail

MSG_FILE="$1"

if grep -qE "^Co-Authored-By:.*Claude" "$MSG_FILE"; then
    cat >&2 <<'ERR'
✗ commit blocked: "Co-Authored-By: Claude ..." trailer is disabled in this repo.

  Strip the trailing line(s) matching "Co-Authored-By: Claude*" from the commit
  message and retry. See ./_scripts/no-claude-coauthor.sh for the rule.
ERR
    exit 1
fi
