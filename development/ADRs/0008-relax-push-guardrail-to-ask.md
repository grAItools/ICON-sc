# 0008 — Relax the agent `git push` guardrail from deny to ask; protect `main` server-side

**Status:** accepted · **Date:** 2026-07-22 (owner-directed 2026-07-22)

## Context

Since the initial commit (`89849bc`), both agent-permission configs have denied
**all** `git push` unconditionally — `.claude/settings.json`
(`deny: "Bash(git push:*)"`) and `opencode.json` (`"git push*": "deny"`) — grouped
in the same coarse "human-only verb" bucket as `rm -rf` and `sudo`.

The rule encodes the **pre-AO, human-orchestrated publication model**: an implementer
agent commits locally only, and a human (or the orchestrator) performs the push and
opens the PR as a deliberate, review-gated act. That model is explicit in the frozen
work documents — `development/work/0024-pr-publication/plan.md` ("You do NOT push, do
NOT open PRs, do NOT create remotes — you produce … a … command script for the human to
review and execute"), `development/work/0054-work-unit-folders/plan.md` ("no push — the
orchestrator pushes"), and `development/policies/agent-workflow.md` ("Merge only after
approve"). The denial's
real purpose was never "protect `main`" specifically; it was "keep publication to the
shared remote out of the implementer's hands entirely."

Two facts make the blanket denial the wrong shape now:

1. **The live AO harness model expects sessions to open their own PRs** from
   session-namespaced branches (`ao/icon-sc-9/…`); `ao review` operates on PRs that
   already exist on GitHub. A hard `deny` on `git push` contradicts that workflow.
2. **`main` is not protected server-side.** Investigation on 2026-07-22 found
   `gh api repos/grAItools/ICON-sc/branches/main/protection` returns
   `404 Branch not protected`. The client-side blanket `deny` is therefore currently
   the *only* thing guarding `main` — a client-side guard on a shared-remote concern.

## Decision

- **Relax the client-side rule `deny` → `ask`** for `git push` in both configs:
  `.claude/settings.json` moves `Bash(git push:*)` into a new `ask` array;
  `opencode.json` sets `"git push*": "ask"`. A push now prompts for human
  confirmation per invocation instead of being hard-blocked — matching the AO
  PR-opening model while keeping a human in the loop on every publish.
- **Reject branch-scoped denial ("forbid only `main`").** The permission matcher is a
  command-string **prefix** matcher; it cannot determine a push's *destination*
  branch. `git push origin HEAD:main`, `git push origin feature:main`,
  `git push --all`, `git push --mirror`, and a bare `git push` while `HEAD` is `main`
  all reach `main` without the literal token `main` in a matchable position, while a
  naive `*main*` glob also mis-fires on branches merely named `main-fix`. A
  "deny-main-only" glob would give **false safety**.
- **Protect `main` server-side** via GitHub branch protection (require a PR, disallow
  direct pushes) — the reliable guarantee, independent of and stronger than any client
  glob. This is where the "no direct writes to `main`" invariant actually belongs.
  Tracked as a follow-up (REGISTRY TD-55.2) because it needs repo-admin action and
  `main` is presently unprotected.

## Consequences

- Agents can open PRs from their own branches under the AO model without hitting a
  hard denial; each push still requires an explicit human `ask` approval.
- The `main` invariant moves to the layer that can enforce it (server-side), rather
  than resting on a client-side command glob.
- `.claude/settings.json` and `opencode.json` stay in sync (both `ask`).
- **Open risk until TD-55.2 lands:** with `main` unprotected server-side, `ask` plus
  human vigilance is the only guard on direct pushes to `main`. Enabling branch
  protection is the closing action.

## Alternatives considered

- **Status quo (blanket `deny`)** — rejected: contradicts the AO session-opens-its-own-PR
  model and forces every push, even routine feature-branch PRs, onto a human or the
  orchestrator.
- **Deny only `main` via a command glob** — rejected as unsound (see Decision): the
  matcher cannot read a push's destination from the command string, so the rule both
  over- and under-blocks and gives false confidence.
- **Namespace-scoped allow** (`Bash(git push origin ao/icon-sc-9/*)` allowed, else
  `ask`) — considered and deferred (the owner explicitly skipped this option). The
  glob still cannot cover `HEAD:`/`refs/heads/` refspec forms, and plain `ask` already
  meets the goal with a human check on every push.
