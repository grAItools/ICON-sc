# symcon — Claude Code project memory

@AGENTS.md

## Claude Code specifics

- Start any implementation session with `/implement-step <SXX_folder_name>`.
- Prefer `uv run pytest <path> -x -q` while iterating; full gate before PR.
- Specs/plans live in `development/specs/` and `development/plans/`; the architecture doc
  is large — read the §s the SPEC cites rather than the whole file into context.
- When mining icon4py/ICON sources, clone shallowly into `/tmp` (never into the repo) and
  record SHAs in `REFERENCES.lock` immediately, not at the end.
