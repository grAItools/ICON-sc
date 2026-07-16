#!/usr/bin/env python3
"""PreToolUse guard: freeze spec ids below the work-unit frontier.

Wired as a ``Write|Edit`` PreToolUse hook (``.claude/settings.json``). It enforces the
REGISTRY invariant — "numbers are strictly monotonic, never reused; gaps are never
backfilled" — at the tool layer: a ``development/work/specs/spec-NNNN-*.md`` write is
DENIED when ``NNNN`` is below the current maximum work id, so an old (frozen, gapped, or
abandoned) number can never be re-created or edited, while authoring at the frontier
(``NNNN >= max``) stays free.

Contract: reads the PreToolUse payload on stdin. Emits a ``permissionDecision: "deny"``
JSON object only for the one confident case; otherwise stays neutral (exit 0, no output),
so normal permissions apply. **Fails open** — any error or ambiguity → neutral — so a bug
here can never wedge unrelated file edits.

The "max id" is the largest ``NNNN`` seen across ``development/work/`` file/dir names
(``spec|plan|proposal|report``) OR implied by ``development/REGISTRY.md``'s
"Next free number: N" (→ N-1), whichever is greater.
"""

from __future__ import annotations

import json
import os
import re
import sys

_SPEC_RE = re.compile(r"/development/work/specs/spec-(\d{4})-[^/]*\.md$")
_ID_RE = re.compile(r"^(?:spec|plan|proposal|report)-(\d{4})-")
_NEXTFREE_RE = re.compile(r"Next free number:\s*(\d+)")


def _decide() -> dict | None:
    """Return a deny payload, or None to stay neutral."""
    data = json.load(sys.stdin)
    if data.get("tool_name") not in ("Write", "Edit", "MultiEdit"):
        return None
    raw = (data.get("tool_input") or {}).get("file_path") or ""
    if not raw:
        return None

    proj = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    ap = raw if os.path.isabs(raw) else os.path.join(proj, raw)
    ap = os.path.normpath(ap)

    m = _SPEC_RE.search(ap)
    if not m:  # not a spec under development/work/specs — not our concern
        return None
    target_id = int(m.group(1))

    marker = "/development/work/"
    idx = ap.find(marker)
    if idx < 0:
        return None
    work_dir = ap[:idx] + "/development/work"
    registry = ap[:idx] + "/development/REGISTRY.md"

    ids: list[int] = []
    for root, dirs, files in os.walk(work_dir):
        for name in (*files, *dirs):
            mm = _ID_RE.match(name)
            if mm:
                ids.append(int(mm.group(1)))
    try:
        with open(registry, encoding="utf-8") as fh:
            r = _NEXTFREE_RE.search(fh.read())
        if r:
            ids.append(int(r.group(1)) - 1)
    except OSError:
        pass

    if not ids:
        return None  # nothing to compare against — stay neutral
    max_id = max(ids)

    if target_id >= max_id:
        return None  # at or beyond the frontier — authoring is allowed

    reason = (
        f"spec-{target_id:04d} is below the current work-unit frontier (max id {max_id}). "
        "Per the REGISTRY invariant (monotonic ids, never reused, gaps never backfilled), "
        "specs below the frontier are frozen — creating or editing one reads as reviving a "
        f"retired id. Author new specs at id >= {max_id}. To edit a frozen spec under a "
        "sanctioned migration, temporarily disable this hook (/hooks) or use a non-Edit path."
    )
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def main() -> int:
    try:
        out = _decide()
    except Exception:  # fail open: never wedge edits on a guard bug
        return 0
    if out is not None:
        json.dump(out, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
