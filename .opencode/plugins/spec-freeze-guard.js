/**
 * OpenCode twin of the Claude Code `spec_freeze_guard` PreToolUse hook.
 *
 * Both agents delegate to the SAME decision script — `tools/spec_freeze_guard.py` — so the
 * frozen-spec rule has exactly one implementation. This file only adapts OpenCode's
 * `tool.execute.before` calling convention to that script's stdin/stdout contract.
 *
 * Rule: writing `development/work/<NNNN>-<slug>/spec.md` is blocked when NNNN is frozen
 * (below the frontier, or registered with a non-`pending` status). See the script's
 * docstring for the full rule.
 *
 * Tool coverage, verified against opencode v1.17.12's registered tools:
 *   - `edit` / `write` carry `args.filePath` and are checked directly.
 *   - `apply_patch` carries only `args.patchText` — no filePath — so its envelope is parsed
 *     for `*** Add|Update|Delete File: <path>` headers and every target is checked. Without
 *     this it is a silent bypass, since one patch can rewrite any file.
 *   - `bash` is left to opencode.json's `permission.bash` (`"*": "ask"` gates the mutating
 *     commands), unlike Claude Code where Bash needed explicit guarding.
 *
 * Fails open: any error resolving/parsing a decision leaves the call unblocked, so a bug
 * here can never wedge unrelated edits. Only an explicit deny throws.
 */

const PATCH_FILE_HEADER = /^\*\*\* (?:Add|Update|Delete) File:\s*(.+?)\s*$/gm;

export const SpecFreezeGuard = async ({ directory, $ }) => {
  // The script resolves relative paths against $CLAUDE_PROJECT_DIR/cwd, which OpenCode does
  // not set — hand it absolute paths so the decision never depends on cwd.
  const absolute = (p) => (p.startsWith("/") ? p : `${directory}/${p}`);

  const denialFor = async (filePath) => {
    const payload = JSON.stringify({
      tool_name: "Edit",
      tool_input: { file_path: absolute(filePath) },
    });
    const res = await $`echo ${payload} | python3 ${directory}/tools/spec_freeze_guard.py`
      .quiet()
      .nothrow()
      .text();
    if (!res.trim()) return null;
    const decision = JSON.parse(res)?.hookSpecificOutput;
    return decision?.permissionDecision === "deny" ? decision.permissionDecisionReason : null;
  };

  const targetsOf = (input, output) => {
    if (input.tool === "edit" || input.tool === "write") {
      return output?.args?.filePath ? [output.args.filePath] : [];
    }
    if (input.tool === "apply_patch") {
      const text = output?.args?.patchText;
      if (!text) return [];
      return [...text.matchAll(PATCH_FILE_HEADER)].map((m) => m[1]);
    }
    return [];
  };

  return {
    "tool.execute.before": async (input, output) => {
      let denyReason = null;
      try {
        for (const target of targetsOf(input, output)) {
          denyReason = await denialFor(target);
          if (denyReason) break;
        }
      } catch {
        return; // fail open
      }
      if (denyReason) throw new Error(denyReason);
    },
  };
};
