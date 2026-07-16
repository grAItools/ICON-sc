/**
 * OpenCode twin of the Claude Code `spec_freeze_guard` PreToolUse hook.
 *
 * Both agents delegate to the SAME decision script — `tools/spec_freeze_guard.py` — so the
 * frozen-spec rule has exactly one implementation. This file only adapts OpenCode's
 * `tool.execute.before` calling convention to that script's stdin/stdout contract.
 *
 * Rule: a `development/work/specs/spec-NNNN-*.md` write is blocked when NNNN is below the
 * current maximum work id (REGISTRY invariant: monotonic ids, never reused, gaps never
 * backfilled). Authoring at the frontier (NNNN >= max) is untouched.
 *
 * Fails open: any error resolving/parsing the decision leaves the call unblocked, so a bug
 * here can never wedge unrelated edits. Only an explicit deny throws.
 */

const WRITE_TOOLS = new Set(["edit", "write", "patch"]);

export const SpecFreezeGuard = async ({ directory, $ }) => {
  return {
    "tool.execute.before": async (input, output) => {
      if (!WRITE_TOOLS.has(input.tool)) return;

      const filePath = output?.args?.filePath;
      if (!filePath) return;

      // The script resolves relative paths against $CLAUDE_PROJECT_DIR/cwd, which OpenCode
      // does not set — hand it an absolute path so the decision never depends on cwd.
      const abs = filePath.startsWith("/") ? filePath : `${directory}/${filePath}`;
      const payload = JSON.stringify({
        tool_name: input.tool === "write" ? "Write" : "Edit",
        tool_input: { file_path: abs },
      });

      let denyReason = null;
      try {
        const res = await $`echo ${payload} | python3 ${directory}/tools/spec_freeze_guard.py`
          .quiet()
          .nothrow()
          .text();
        if (res.trim()) {
          const decision = JSON.parse(res)?.hookSpecificOutput;
          if (decision?.permissionDecision === "deny") {
            denyReason = decision.permissionDecisionReason;
          }
        }
      } catch {
        return; // fail open
      }

      if (denyReason) throw new Error(denyReason);
    },
  };
};
