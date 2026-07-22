# 0055 — push-guardrail relaxation (report)

**Status:** owner-directed change, applied 2026-07-22; not yet merged. Plan ad hoc
(not committed). One trunk decision pair: TD-55.1 / TD-55.2 (REGISTRY §3). Reasoning:
ADR-0008.

## What prompted this

Owner question: *why does the project forbid agents from `git push`, and would it be
better to relax it to forbid only pushes to `main`?*

## Investigation (why the ban existed)

The blanket denial has been present in **both** agent-permission configs since the
initial commit (`89849bc`):

- `.claude/settings.json` — `deny: "Bash(git push:*)"`
- `opencode.json` — `"git push*": "deny"`

It sits in the same coarse "human-only verb" bucket as `rm -rf` and `sudo`. Its real
purpose was **not** "protect `main`" but "keep publication to the shared remote out of
the implementer agent's hands entirely" — publication is a deliberate, review-gated act
owned by a human/orchestrator. Evidence in the frozen work documents:

- `development/work/0024-pr-publication/plan.md` — agents *draft* a push/PR command
  script; a human reviews and executes it ("You do NOT push, do NOT open PRs, do NOT
  create remotes").
- `development/work/0054-work-unit-folders/plan.md` — "no push (the orchestrator pushes)".
- `development/work/0053-project-rename-icon-sc/plan.md`,
  `development/work/0035-naming-migration/plan.md` — "never `git push`", "`git push` is
  denied — do not attempt".
- `development/policies/agent-workflow.md` — implementer↔reviewer loop, "Merge only after
  approve".

## Why blanket-deny is now the wrong shape

1. The **live AO harness model** expects a session to open its own PRs from
   session-namespaced branches (`ao/icon-sc-9/…`); `ao review` operates on PRs that
   already exist on GitHub. A hard `deny` on `git push` contradicts that workflow.
2. **`main` is not protected server-side.** On 2026-07-22,
   `gh api repos/grAItools/ICON-sc/branches/main/protection` → `404 Branch not
   protected`. The client-side blanket deny is presently the *only* guard on `main`.

## Why "forbid only `main`" was rejected

The permission matcher is a command-string **prefix** matcher; it cannot read a push's
destination branch. `git push origin HEAD:main`, `git push origin feature:main`,
`git push --all`, `git push --mirror`, and a bare `git push` while `HEAD` is `main` all
reach `main` without a matchable `main` token, while a naive `*main*` glob also
mis-fires on branches named e.g. `main-fix`. A "deny-main-only" glob gives false
safety. The reliable place for the `main` invariant is **server-side branch
protection**.

## Decision applied

- **`deny` → `ask`** for `git push` in both configs (TD-55.1), **applied this
  session**: `opencode.json` (`"git push*": "ask"`) and `.claude/settings.json`
  (`Bash(git push:*)` moved out of `deny` into a new `ask` array). The
  `.claude/settings.json` edit was first blocked by the harness auto-mode classifier
  (self-edit of the permission-governance file) and applied after explicit owner
  permission; the two configs are now consistent.
- **Enable GitHub branch protection on `main`** (TD-55.2) — **done and verified
  2026-07-22**: require a PR, `enforce_admins`, 1 approving review with stale-dismissal,
  no force-pushes, no deletions, conversation-resolution required. This is where the
  "no direct writes to `main`" invariant now lives; the client-side rule is the
  in-session prompt, not the guarantee.

## Follow-ups

- [x] Apply the `.claude/settings.json` `deny`→`ask` move (done 2026-07-22 with owner
      permission; classifier-gated on first attempt).
- [x] `opencode.json` `deny`→`ask` (done 2026-07-22).
- [x] Enable branch protection on `main` (TD-55.2; repo admin) — done + verified
      2026-07-22 (require PR, enforce_admins, 1 review, no force-push/deletion).
- [ ] Keep `.claude/settings.json` and `opencode.json` in sync on this rule.
