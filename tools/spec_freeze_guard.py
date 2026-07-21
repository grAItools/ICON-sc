#!/usr/bin/env python3
"""Guard: freeze spec ids that the work-unit register has already consumed.

Wired as a Claude Code PreToolUse hook (``.claude/settings.json``) and as an OpenCode
``tool.execute.before`` plugin (``.opencode/plugins/spec-freeze-guard.js``); both delegate
here so the rule has exactly one implementation.

It enforces the REGISTRY invariant — "numbers are strictly monotonic, never reused; gaps
are never backfilled" — at the tool layer. A ``development/work/<NNNN>-<slug>/spec.md``
write is DENIED when NNNN is frozen, so a retired id can never be re-created or edited
(writing there reads as reviving history), while authoring the in-flight unit's spec and
brand-new ids at the frontier stays free.

**NNNN is frozen when** either holds:
  * ``NNNN < max_id`` — below the frontier (covers every consumed id and the never-
    allocated gaps, e.g. 0015-0019); or
  * the register has a row for NNNN whose status is not ``pending`` — i.e. the unit is
    ``executed``/``accepted-roadmap``. This is what keeps the newest *completed* id frozen
    in the quiet window before the next one is allocated; without it the last row would
    stay writable purely by virtue of being the maximum.
Anything else — the in-flight (``pending``) unit, or an unallocated id at/above the
frontier — is allowed.

Contract: reads the PreToolUse payload on stdin; prints a deny JSON, or stays silent
(neutral) so normal permissions apply. **Fails open** — any error or ambiguity is neutral —
so a bug here can never wedge unrelated file edits. Only an explicit deny blocks.

Bash is covered too, because Claude Code's ``Edit(...)`` deny rules (which this replaced)
also blocked file-writing Bash commands. Detection there is deliberately narrow: a frozen
spec path is blocked only when the command redirects onto it or hands it to a mutating
utility. Reading a frozen spec (``cat``/``grep``/``git diff``) stays allowed — reads were
never the concern. Neither this nor the rule it replaced can stop an arbitrary subprocess
that opens the file itself; that needs OS-level sandboxing.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys

_SPEC_PATH_RE = re.compile(r"/development/work/(\d{4})-[^/]*/spec\.md$")
#: A whole shell *token* that is a spec path. Matched with fullmatch, never search: a token
#: that merely quotes the path (a JSON payload, a heredoc body, a grep pattern) is not a
#: write to it, and treating it as one blocks ordinary work.
_SPEC_TOKEN_RE = re.compile(r"[\w./-]*development/work/(\d{4})-[^/\s]*/spec\.md")
_ID_RE = re.compile(r"^(\d{4})-")
_NEXTFREE_RE = re.compile(r"Next free number:\s*(\d+)")
#: `| 0051 | kebab-and-flat-reports | plan + report | executed |`
_ROW_RE = re.compile(r"^\|\s*(\d{4})\s*\|[^|]*\|[^|]*\|\s*([^|]*?)\s*\|\s*$", re.MULTILINE)
#: Utilities that write a path argument. Over-inclusive on purpose: wrongly refusing to `cp`
#: a frozen spec is a nuisance; wrongly letting one be rewritten is the bug. `sed` only
#: counts with -i — plain `sed file` reads.
_MUTATING = frozenset(
    {"tee", "truncate", "dd", "sponge", "install", "cp", "mv", "rm", "patch", "ex"}
)

_FILE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


class _Frontier:
    """The register's view of which ids are spent."""

    def __init__(self, work_dir: str, registry: str) -> None:
        ids: list[int] = []
        # The id lives once, in the unit *folder* name (`<NNNN>-<slug>/`), so scan only the
        # immediate children of work/ — never recurse. A recursive walk would fold any
        # four-digit-prefixed artifact filename (e.g. `2026-metrics.json` under a unit's
        # artifacts/) into the frontier and could freeze every real id below it.
        try:
            for entry in os.scandir(work_dir):
                if entry.is_dir():
                    m = _ID_RE.match(entry.name)
                    if m:
                        ids.append(int(m.group(1)))
        except OSError:
            pass

        self.status: dict[int, str] = {}
        self.next_free: int | None = None
        try:
            with open(registry, encoding="utf-8") as fh:
                text = fh.read()
            m = _NEXTFREE_RE.search(text)
            if m:
                self.next_free = int(m.group(1))
                ids.append(self.next_free - 1)
            for row_id, row_status in _ROW_RE.findall(text):
                self.status[int(row_id)] = row_status.strip().lower()
        except OSError:
            pass

        self.max_id: int | None = max(ids) if ids else None

    def is_frozen(self, spec_id: int) -> bool:
        if self.max_id is None:
            return False  # nothing to compare against — stay neutral
        if spec_id < self.max_id:
            return True
        status = self.status.get(spec_id)
        # An allocated-but-unfinished unit is the one spec you are meant to be writing.
        return status is not None and not status.startswith("pending")

    def advice(self) -> int:
        if self.next_free is not None:
            return self.next_free
        return (self.max_id + 1) if self.max_id is not None else 0


def _reason(spec_id: int, frontier: _Frontier) -> str:
    status = frontier.status.get(spec_id)
    why = (
        f"work unit {spec_id:04d} is registered as '{status}'"
        if status
        else f"id {spec_id:04d} is below the frontier (max id {frontier.max_id})"
    )
    return (
        f"spec-{spec_id:04d} is frozen: {why}. Per the REGISTRY invariant (ids are strictly "
        "monotonic, never reused; gaps are never backfilled), creating or editing it reads as "
        "reviving a retired id. New work takes the register's next free number "
        f"({frontier.advice():04d}); only the in-flight (pending) unit's spec is writable. "
        "For a sanctioned migration, disable this guard deliberately (/hooks) rather than "
        "routing around it."
    )


def _locate(abs_path: str) -> tuple[str, str] | None:
    """Return (work_dir, registry) for a path inside development/work, else None."""
    marker = "/development/work/"
    idx = abs_path.find(marker)
    if idx < 0:
        return None
    return abs_path[:idx] + "/development/work", abs_path[:idx] + "/development/REGISTRY.md"


def _abs(raw: str) -> str:
    proj = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    path = raw if os.path.isabs(raw) else os.path.join(proj, raw)
    # realpath, not normpath: a symlinked specs/ dir must not dodge the path match.
    return os.path.realpath(path)


def _frozen_spec(abs_path: str) -> tuple[int, _Frontier] | None:
    m = _SPEC_PATH_RE.search(abs_path)
    if not m:
        return None
    located = _locate(abs_path)
    if not located:
        return None
    frontier = _Frontier(*located)
    spec_id = int(m.group(1))
    return (spec_id, frontier) if frontier.is_frozen(spec_id) else None


def _check_file_write(raw: str) -> str | None:
    if not raw:
        return None
    hit = _frozen_spec(_abs(raw))
    return _reason(*hit) if hit else None


def _check_bash(command: str) -> str | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None  # unbalanced quotes — unparseable, so stay neutral

    mutating = bool(_MUTATING.intersection(tokens)) or (
        "sed" in tokens and any(t.startswith("-i") for t in tokens)
    )
    for idx, token in enumerate(tokens):
        if not _SPEC_TOKEN_RE.fullmatch(token):
            continue
        redirected = idx > 0 and tokens[idx - 1] in (">", ">>")
        if not (redirected or mutating):
            continue  # reading a frozen spec is fine
        hit = _frozen_spec(_abs(token))
        if hit:
            return _reason(*hit)
    return None


def _decide() -> dict | None:
    data = json.load(sys.stdin)
    tool = data.get("tool_name")
    args = data.get("tool_input") or {}

    if tool in _FILE_TOOLS:
        reason = _check_file_write(args.get("file_path") or "")
    elif tool == "Bash":
        reason = _check_bash(args.get("command") or "")
    else:
        return None
    if not reason:
        return None

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
        if out is not None:
            json.dump(out, sys.stdout)
    except Exception:  # fail open: never wedge edits on a guard bug
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
