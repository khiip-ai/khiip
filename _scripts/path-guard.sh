#!/usr/bin/env bash
# Block internal-only paths from being committed to github.com/khiip-ai/khiip.
# Mirrored in .github/workflows/path-guard.yml as a server-side check.
#
# To extend: add the path pattern to the regex below AND to the CI workflow.

set -euo pipefail

PATTERN='(^|/)(HANDOFF\.md|CHRONICLE\.md|AGENTS\.md|SESSION-SUMMARY-.*\.md|_internal/|khiip-internal/|docs/research/|docs/strategy/|docs/product/naming-brief\.md|docs/product/naming-research-synthesis\.md|docs/product/canonical-edge-template-mapping\.md|docs/product/v0-spec\.md|docs/methodology/jtbd-framework\.md|docs/adr/ADR-[0-9]+-decision-prep\.md)$'

MATCH=$(git diff --cached --name-only | grep -E "$PATTERN" || true)

if [ -n "$MATCH" ]; then
  echo "BLOCKED: internal-only paths staged in public repo:"
  echo "$MATCH" | sed 's/^/  - /'
  echo ""
  echo "These belong in github.com/khiip-ai/internal"
  echo "(sibling checkout at ~/projects/khiip-internal/)."
  exit 1
fi

exit 0
