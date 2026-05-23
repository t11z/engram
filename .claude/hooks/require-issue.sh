#!/usr/bin/env bash
# Issue-first guard. Blocks file-modifying tools unless a tracking issue is
# recorded for the current change. See /CLAUDE.md ("Working loop").
#
# A change is "authorized" when either:
#   - .claude/state/active-issue exists and is non-empty, or
#   - the BARTLEBY_ACTIVE_ISSUE environment variable is set.
#
# Edits under .claude/ are always allowed so this guard can never deadlock
# (you must be able to write the marker and the hook itself).
set -euo pipefail

input="$(cat)"

# Extract the target path from the tool input (best-effort; absent -> "").
path="$(printf '%s' "$input" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    print("")
    sys.exit(0)
ti = data.get("tool_input", {}) or {}
print(ti.get("file_path") or ti.get("notebook_path") or "")
' 2>/dev/null || printf '')"

case "$path" in
  */.claude/*|.claude/*) exit 0 ;;
esac

if [ -n "${BARTLEBY_ACTIVE_ISSUE:-}" ]; then
  exit 0
fi
if [ -s ".claude/state/active-issue" ]; then
  exit 0
fi

cat >&2 <<'MSG'
Issue-first workflow: no file changes without a tracking issue.

  1. Create a GitHub issue describing this change.
  2. Record it so this guard passes, e.g.:
       echo "<issue-url-or-number>" > .claude/state/active-issue
     (or export BARTLEBY_ACTIVE_ISSUE=<issue>)
  3. Open the PR with "Closes #<issue>".

See /CLAUDE.md for the full loop.
MSG
exit 2
