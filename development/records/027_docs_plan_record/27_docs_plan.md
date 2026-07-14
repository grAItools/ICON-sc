# Task 27 — User documentation: design and implementation plan

**Branch:** `task/27-docs-plan` · **Deliverable:** this document (plan only — no tooling
config, no product code). The implementation is specified in §5 in the
`development/plans/` register, ready to lift into `development/plans/028_docs_implementation_plan.md`.

**Owner requirements (verbatim intent):**

1. Tooling configuration + scripts to generate BOTH API reference docs AND tutorials.
2. Output easy to deploy on static web servers — primarily GitHub Pages.
3. Tutorials explain the architecture for weather/climate scientists and students:
   strong domain knowledge, weak software-architecture knowledge. Explain
   composition/contracts/plans in terms of model coupling, process ordering,
   reproducibility — introduce software concepts only as needed, from the science in.
4. Evaluate and propose the documentation stack. Constraints: Markdown-flavored
   authoring; Google-style docstrings for the API reference.

**Known tension (explicit trunk decision, §3):** `docs/architecture/symcon_repo_layout.md`
§4 specifies `docs/api/` as "sphinx + autodoc from py.typed sources". The owner's
Markdown + Google-docstring requirements are *reconcilable* with that line
(Sphinx + MyST + Napoleon) or *conflict* with it (MkDocs + mkdocstrings). Both paths
are evaluated in §2; §3 states the recommendation and what the trunk must decide.

---

## 1. Audience and content strategy

### 1.1 Audience contract

The reader is a weather/climate scientist or student: they know what saturation
adjustment, a dycore, a parameterization, halo/ghost points (perhaps), splitting
methods, and 4D-Var are — they do **not** know what an API, a contract, a compiler
pass, a namespace package, or a design pattern is. Every tutorial therefore:

- opens with a *science question* ("in what order do processes act on the
  atmosphere during one Δt?"), never with a software concept;
- introduces at most 2–3 software terms per page, each defined science-in
  (e.g. *contract* = "the component's published list of what fields it reads and
  writes, with units and mesh location — the machine-checked version of the
  interface table in a model description paper"; *execution plan* = "the model,
  frozen after all checks have passed once, so the same physics runs without
  per-step bookkeeping — verified bit-for-bit against the checked version");
- builds on a **runnable, CI-smoked script** from `examples/` wherever possible, with
  code lifted via `literalinclude`/snippet inclusion from the tested file — tutorials
  must not carry hand-copied code that can drift from what CI runs;
- ends with "what you can now trust" — tying back to the validation ladder, because
  reproducibility claims are the currency this audience trades in.

A short **glossary page** (software terms defined science-in, one paragraph each)
backs all tutorials; terms link to it on first use.

### 1.2 Tutorial curriculum

Ordered; each entry names its source material. Pages T0–T2 are in the first
iteration (§5, item D); the rest are titled and abstracted now so the nav skeleton
is stable and later work is fill-in, not redesign.

**T0 — What symcon is: a weather model as a run script.**
Why re-express ICON-NWP in Python: the model is a set of fields (the state) evolved
by processes (components), and one legible script says which schemes run, in what
order, at what cadences, and where output goes — the same information a namelist
holds, but readable and checkable. Introduces: *state dictionary*, *component*,
*run script*. Sources: architecture §0, §5.1 (the canonical run script);
`README.md`; `examples/README.md`.

**T1 — The model state: fields, units, and where they live on the grid.**
Fields carry names (CF where CF has them, `icon:` names for solver internals),
canonical units, and a mesh location (cell/edge/vertex) — because on ICON's C-grid
the normal wind lives on edges and temperature at cell centers, and mixing them up
is a physics error the machinery catches for you. Halo validity is introduced as
"are my neighbor points up to date after the last exchange". Introduces: *property
contract*, *canonical units*, *staggering as API*. Sources: architecture §2.1–2.5,
§3.3; `symcon/icon/names.py`; §1 tensions T3/T5/T6.

**T2 — Your first run: a single-column model.**
Line-by-line walk of `examples/01_scm_column.py` (CI-smoked, <60 s CPU): the S09
validated preset — saturation adjustment → graupel microphysics → saturation
adjustment coupled by sequential-update splitting, plus a prescribed cooling
publishing a piecewise-constant slow tendency to the `icon:ddt_temperature_slow`
bus slot — run for an hour, written to NetCDF, plotted. The reader edits one config
value and reruns. Introduces: *preset*, *slow-tendency bus* (as "how slow physics
hands its heating rates to the core, ICON's operational arrangement"). Sources:
`examples/01_scm_column.py`; `symcon/icon/presets/scm.py`; architecture §4.2 (bus),
tutorial §3.7.2 lineage; `development/records/036_implementation_report_record.md` S09 row.

**T3 — Processes as components: calling saturation adjustment by hand.**
A parameterization is an object you can call interactively on a column state —
sympl's research affordance, retained. Shows the component's declared inputs/outputs
(dims, units, location), what happens when you hand it the wrong units in strict vs
interactive mode, and why "components never share data behind the state's back" is
the property that makes recomposition safe. Introduces: *strict mode*, *interactive
mode*. Sources: architecture §2.4, §4.1; `symcon/icon/components/fast/satad.py`;
example 05 placeholder (layout doc: `05_interactive_radiation.ipynb`).

**T4 — Process coupling and ordering: why the order matters.**
Sequential-update vs parallel splitting vs Strang, fast vs slow physics with calling
frequencies — the coupling algebra as the space of scientifically meaningful
experiments, with ICON's operational arrangement as one *validated preset* and the
machinery (`must_follow`/`must_precede`, the validated/experimental label) that keeps
"legal code" from being mistaken for "right science". Introduces: *federation/
coupling operator*, *validated preset*. Sources: architecture §1 T1, §4.2, §4.3
table, §11.7; the three-line SSUS swap in §5.1; S04 coupling formal-order results in
`development/records/036_implementation_report_record.md` §3; `validation/L7` (per layout doc).

**T5 — The dynamical core and a global test: the baroclinic wave.**
The dycore is not decomposed into per-tendency pieces — it *is* a time loop
(predictor–corrector, `ndyn_substeps`), hosted as one component with a slow-tendency
input port. Walk of `examples/02_jw_baroclinic.py`: the Jablonowski–Williamson wave
on the global R02B04 grid, 35 levels, and how to look at surface pressure at day 9.
Introduces: *substepping tier*, *component-private state*. Sources:
`examples/02_jw_baroclinic.py`; architecture §1 T2, §4.3, §4.4;
`validation/L4_idealized/README.md`; `symcon/icon/presets/jw.py`.

**T6 — Trusting the results: the validation ladder and reproducibility.**
What "scientific equivalence with ICON" means operationally: the L2→L8 ladder from
stencil parity to gradient verification; the ε-twin chaotic-growth envelope (why
bitwise comparison of 9-day forecasts is the wrong question and what the right one
is); restart reproducibility; provenance stamping (config + grid UUIDs + versions in
every output). Introduces: *tolerance as contract*. Sources: architecture §9;
`validation/README.md`, `validation/L4_idealized/README.md`;
`development/records/036_implementation_report_record.md` §3 (bitwise-zero L4 result, ε-twin envelope numbers).

**T7 — The same model, faster: plans and execution tiers.**
Why a Python loop over components is fine for a column and a ceiling for a global GPU
run; the negotiation/execution split told science-in: all checks run once at startup,
then a frozen plan executes the identical arithmetic — and the claim is not rhetoric,
it is a CI-enforced bitwise T0≡T1 gate (24 simulated hours through the dycore,
exactly equal at every step on every prognostic). Introduces: *bind time*,
*execution plan*, *tier*. Sources: architecture §8.1–8.3; S14 rows of
`development/records/036_implementation_report_record.md` (§3 headline + dispatch benchmark);
`benchmarks/dispatch_overhead/`.

**T8 — Asking the model "what if": gradients, sensitivities, parameter estimation.**
Walk of `examples/07_gradient_scm.py`: the derivative of accumulated surface rain
with respect to the autoconversion coefficient, over a multi-step window, checked
against a finite difference — the atomic operation of parameter estimation and
variational DA, framed via adjoint/tangent-linear language the audience already has.
Introduces: *differentiability contract*, *ParamTree*. Sources:
`examples/07_gradient_scm.py`; architecture §8.5–8.6, §9 item 8;
`validation/L8_gradients/README.md`.

**Non-tutorial pages in the same site:** landing page (what/why/install), the
architecture documents included read-only (`docs/architecture/*.md` — never edited,
per AGENTS.md), the API reference (§2), the glossary, and a "for developers" pointer
page linking AGENTS.md/plan (not reworked as user docs).

---

## 2. Stack evaluation

### 2.1 The existing docstring corpus (measured, this repo at `task/27-docs-plan` fork point)

The evaluation hinges on what the corpus actually is, so it was measured first
(`grep`/`ast` over `packages/*/src`, 78 source files):

| Metric | Count |
|---|---|
| Modules with docstrings | **78 of 78** |
| Public functions/classes **with** docstrings | **346** |
| Public functions/classes **without** docstrings | 122 |
| Lines using Sphinx roles `:func:`/`:mod:`/`:class:`/`:meth:` | **217** |
| Lines using further roles (`:ref:`/`:data:`/`:attr:`/`:exc:`/`:obj:`) | 12 |
| Lines with reST ``` ``inline literals`` ``` | 1441 |
| reST directives (`.. note::`) | 1 |
| Google-style `Args:/Returns:/Raises:` sections | **0** |
| reST/numpydoc field lists (`:param:`, `Parameters\n----`) | **0** |
| `::` literal-block introducers (examples/validation/tools) | 5 |

So the corpus is **not** field-list reST and **not** Google: it is *narrative prose
in reST/Sphinx flavor* — heavy cross-referencing via roles, heavy double-backtick
literals, no structured parameter sections at all. Two consequences:

- Any stack renders the prose; the differentiator is whether the **229 role-based
  cross-references and 1441 literals render correctly** (as links / code spans) or
  degrade to visible junk.
- Adopting Google style going forward costs nothing in *conversion*, because there
  are no legacy field lists to convert — the policy question is only how new
  `Args:/Returns:` sections coexist with old narrative prose (§4).

These docstrings are also **review-audited scientific provenance** (the S06 review
round explicitly fixed docstring provenance; S07 caught a false docstring claim).
A bulk mechanical rewrite of 346 docstrings is a scientific-review event, not a
formatting chore — that weighs heavily against any stack that requires it.

### 2.2 Candidates

- **(a) MkDocs + Material + mkdocstrings[python]** (griffe collects docstrings
  statically; `docstring_style: google`).
- **(b) Sphinx + MyST-Parser + Napoleon + furo** (Markdown authoring via MyST;
  autodoc imports the packages; Napoleon parses Google sections).
- **(c) Quarto + quartodoc** (Pandoc-based scientific publishing system; quartodoc
  renders Python API references from Google docstrings via griffe; used by the
  Posit Python ecosystem — plotnine, shiny, pins).

Also considered and set aside early: `sphinx-autodoc2` (MyST-native autodoc;
single-maintainer, slow cadence, and it abandons the role-resolution behavior that
is Sphinx's main advantage here); `mystmd`/Jupyter Book 2 (excellent tutorial
engine, Node-based, but no mature Python API-reference story); `pdoc` (Google
docstrings, zero config, but no tutorial framework, no math-first authoring, no
site nav to grow into).

### 2.3 Smoke tests (evidence)

Both (a) and (b) were smoke-tested on 2026-07-13 in throwaway `uv` venvs under
`/tmp/docsmoke` (python 3.10.18 — the workspace floor), against **copies** of real
sources arranged as *two* source roots to reproduce the PEP 420 namespace split:
`src/symcon/core/{registry.py,time.py,gsample.py}` and `src2/symcon/icon/{thermo.py,_constants.py}`
(`gsample.py` = a synthetic Google-style docstring, since the corpus has none;
`registry.py` = a real corpus module dense with `:class:` roles). Full transcripts
in Appendix A. Nothing was installed into the project environment. Results:

| Probe | (a) MkDocs/mkdocstrings | (b) Sphinx/MyST/Napoleon |
|---|---|---|
| Google `Args:/Returns:/Raises:` rendering | **Pass** — full parameter tables with types/defaults from annotations | **Pass** — Parameters/Returns/Raises blocks via Napoleon |
| Existing corpus: `` :class:`Factory` `` in prose | **Fail** — renders as literal text "`:class:` Factory" (217+ such lines site-wide) | **Pass** — resolves to a hyperlink (`#symcon.core.registry.Factory` verified in HTML) |
| Existing corpus: ``` ``literals`` ``` | Pass (rendered as code) | Pass |
| PEP 420 namespace across two src roots | **Pass** — griffe collected `symcon.core` *and* `symcon.icon` statically, no imports executed | **Pass** — autodoc imported both via `sys.path`; in the repo the packages are installed editable, so no path hacks needed (`uv run python -c "import symcon.core, symcon.icon"` → OK) |
| Typed-source introspection | Signatures + types from annotations (static) | Signatures + types from annotations (import-based; `autodoc_typehints = "description"` available) |
| Math | `pymdownx.arithmatex` configured (not probed) | **Pass** — `$…$` dollarmath rendered via MathJax (probed in output) |
| Toy build time | 1.71 s | 0.52 s (fresh, `-E`) |

**Maintenance-risk finding (verbatim from the (a) build output):** Material for
MkDocs 9.7.6 prints a hard warning that **MkDocs 2.0 "will introduce
backward-incompatible changes"**: *"All plugins will stop working – the plugin
system has been removed · All theme overrides will break · No migration path exists
– existing projects cannot be upgraded · Closed contribution model · Currently
unlicensed – unsuitable for production use"* (their analysis:
squidfunk.github.io/mkdocs-material/blog/2026/02/18/mkdocs-2.0/). Independently,
the mkdocstrings side has just crossed churn-heavy majors (mkdocstrings 1.0.6,
mkdocstrings-python 2.0.5, and griffe renamed to the `griffelib` distribution,
v2.1.0). Whatever one thinks of the eventual outcome, the MkDocs ecosystem is in
the middle of a governance/compatibility upheaval **right now**, and this repo's
pin discipline would strand us on a frozen island of it.

### 2.4 Evaluation table

| Criterion | (a) MkDocs + Material + mkdocstrings | (b) Sphinx + MyST + Napoleon + furo | (c) Quarto + quartodoc |
|---|---|---|---|
| Markdown flavor | Python-Markdown + pymdown-extensions (superfences, admonitions, tabs) | **MyST** (CommonMark + roles/directives/`{eval-rst}` escape hatch; dollarmath, colon fences) | Pandoc Markdown (+ Quarto div/shortcode syntax) |
| Google-docstring rendering | Excellent (verified: typed parameter tables) | Good (verified: Napoleon definition-list blocks; less tabular but complete) | Good (griffe-based; not smoke-tested) |
| **Existing corpus (217+ Sphinx-role lines, narrative reST)** | **Degrades** — roles render as literal junk (verified); fixing requires bulk-editing 346 audited docstrings | **Renders natively** — roles become links, zero migration (verified) | Degrades same as (a) (griffe, no role resolution) |
| PEP 420 namespace + typed sources | Verified OK (static, no import needed) | Verified OK (import-based; repo env already imports cleanly) | griffe-based → expected OK; not verified |
| Math in tutorials | arithmatex + MathJax (standard, config'd) | Verified (dollarmath + MathJax) | Native (Pandoc math, best-in-class) |
| Executable/tested snippets | No doctest integration; `mkdocs-jupyter` for notebooks; snippet inclusion via pymdown `snippets` | `sphinx.ext.doctest` (gate-able in CI); `myst-nb` executes notebooks (covers the planned `examples/05_*.ipynb`); `literalinclude` from CI-smoked `examples/` | First-class executed code cells (its headline feature) — but execution requires the full compute env inside the docs build |
| GitHub Pages deploy | `mkdocs gh-deploy` (gh-pages branch) or artifact flow | Artifact flow (workflow in §5 item E); plain static HTML | `quarto publish gh-pages` or artifact flow |
| Build speed | 1.71 s toy; fast at scale; no import of heavy deps (static analysis) — a real advantage | 0.52 s toy; at scale slower than MkDocs and autodoc must import `symcon.*` (pulls gt4py/xarray, seconds; acceptable in a CI job that `uv sync`s anyway); incremental builds mitigate locally | Slow-ish; requires the ~150 MB Quarto binary (not pip-installable) in CI and on every contributor machine |
| Maintenance risk | **High right now**: MkDocs 2.0 upheaval warning (verified, §2.3); mkdocstrings/griffe major-version churn + rename; bus factor of mkdocstrings ≈ 1 | Low: Sphinx is 15+ yr infrastructure with institutional users (Python docs, RTD); MyST-parser is Executable-Books-governed; furo single-maintainer but trivially swappable (pydata-sphinx-theme as drop-in fallback) | Medium: Posit-backed (company), healthy cadence, but quartodoc is young and the toolchain is outside the Python packaging world (violates the repo's uv/constraints pin discipline — can't be pinned in `constraints/*.txt`) |
| Fit with repo pins/discipline | pip-installable, pinnable | pip-installable, pinnable | **Not pip-pinnable** (system binary) |
| Layout-doc §4 ("sphinx + autodoc") | **Contradicts** — requires a trunk edit of the layout doc | **Complies** | Contradicts |

---

## 3. Recommendation and trunk decisions

### 3.1 Recommendation: (b) Sphinx + MyST-Parser + Napoleon + furo

The decision is dominated by two measured facts and one governance fact:

1. **The corpus is Sphinx-flavored narrative.** 78/78 module docstrings and 346
   public-API docstrings render natively under Sphinx (roles → links, verified) and
   visibly degrade under griffe-based stacks (verified). The alternative — bulk
   rewriting audited, provenance-bearing docstrings — is exactly the kind of
   mass-touch scientific-review event AGENTS.md discipline exists to prevent.
2. **Markdown + Google docstrings are fully satisfied inside Sphinx.** MyST gives
   Markdown authoring for every *hand-written* page (tutorials, index, glossary —
   the things humans write from now on); Napoleon parses Google `Args:/Returns:`
   sections in docstrings *while leaving the existing narrative prose and its roles
   untouched in the same docstring*. Coexistence is a config line, not a migration
   (verified: both styles rendered in one build).
3. **MkDocs is the wrong week to buy in.** Material's own MkDocs 2.0
   no-migration-path warning (§2.3) plus mkdocstrings/griffe churn make (a) a
   maintenance bet against the repo's pin-and-freeze discipline.

Quarto (c) is the best pure-tutorial engine but cannot be pinned via
`constraints/*.txt`, adds a system binary to every environment, and shares (a)'s
corpus-degradation problem. Rejected for the same governance reasons, with the note
that individual *notebooks* remain portable to it later if ever wanted.

### 3.2 Trunk decision TD-1 — the layout-doc line

`docs/architecture/symcon_repo_layout.md` §4: `docs/api/ # sphinx + autodoc from
py.typed sources`.

- **Recommended resolution: comply via MyST.** Stack (b) satisfies the line as
  written — `docs/api/` is generated by Sphinx autodoc from the py.typed sources;
  MyST only changes the *authoring format of hand-written pages*, which the layout
  doc does not constrain. **No layout-doc edit is required to proceed.**
- **Proposed (non-blocking) clarification** for the next trunk-owned layout-doc
  revision (we do not edit `docs/architecture/*`; recorded here per AGENTS.md):
  extend the `docs/` tree entry with `conf.py`, `index.md`, `tutorials/`, and a note
  "hand-written pages in MyST Markdown; docstrings Google-style going forward
  (Napoleon)". This is additive, not a contradiction.
- **The alternative** (change the line to name MkDocs) is *rejected*, not merely
  deferred — §2's evidence is one-sided once corpus cost and ecosystem churn are
  priced in. If the trunk overrules toward MkDocs anyway, the mandatory rider is a
  funded bulk conversion of all 346 docstrings' role syntax to mkdocstrings
  cross-reference syntax, re-reviewed for provenance — estimate that before deciding.

### 3.3 Trunk decision TD-2 — dependency additions (pins)

New dev-group entries (lower bounds, per repo discipline) and `constraints/cpu-ci.txt`
exact pins (versions **verified working in the §2.3 smoke test**, py3.10.18):

```toml
# pyproject.toml [dependency-groups] dev — additions
"sphinx>=8.1",
"myst-parser>=4.0",
"furo>=2025.12.19",
```

```text
# constraints/cpu-ci.txt — additions (verified pair, 2026-07-13)
sphinx==8.1.3
myst-parser==4.0.1
furo==2025.12.19
docutils==0.21.2
```

Notes for the trunk: (i) Sphinx ≥ 8.2 requires Python ≥ 3.11; the workspace floor is
3.10, hence the 8.1.x pin — revisit when the floor moves. (ii) These are *new*
dependencies, not bumps of existing pins, but adding them changes `uv.lock`, which is
trunk-gated by the prompts-README rules — task 28 grants it explicitly and the PR
flags it. (iii) `sphinx-copybutton`, `sphinx-design`, `myst-nb` are *deliberately
not* in the first iteration (unverified pins; myst-nb waits for a real
`examples/05_*.ipynb`).

### 3.4 Trunk decision TD-3 — docstring convention (see §4)

Adopting Google-style sections repo-wide going forward + ruff `D` enforcement
touches the definition-of-done in `development/records/000_overview_record.md` §1.4 ("new public API has
docstrings") only additively, but it is a repo-wide convention change → trunk
sign-off alongside TD-1/TD-2, then it binds all future steps.

---

## 4. Docstring policy going forward

**Convention.** Google style for *structure* (Args/Returns/Raises/Yields/Attributes
sections on public functions, methods, classes) — Napoleon-parsed. Sphinx roles
(`:func:`/`:class:`/`:mod:`) and double-backtick literals **remain first-class in
prose** (they are what makes the corpus cross-referenced, and Napoleon passes them
through untouched). Architecture-§ references in docstrings stay as plain text
(`(§8.2)`), as today.

**Existing corpus (346 public docstrings, 78 module docstrings): keep, do not bulk-convert.**

- There is nothing to convert *from* — zero legacy field lists (measured, §2.1); the
  corpus is narrative prose that renders correctly under the chosen stack as-is.
- Bulk edits to audited docstrings are a review liability with zero rendering gain.
- **Convert-on-touch:** when a change substantively edits a public docstring, add
  Google sections for its parameters/returns at that time. Never as a drive-by in an
  unrelated PR (diff discipline).

**Enforcement (staged, ruff-native — no new tool):**

1. Task 28 adds to `pyproject.toml`:
   ```toml
   [tool.ruff.lint.pydocstyle]
   convention = "google"
   ```
   and extends `select` with `"D"` **plus an explicit `ignore` list** for the rules
   the corpus legitimately fails today — at minimum the missing-docstring family
   `D1xx` (122 public defs lack docstrings; making them a lint error now would force
   a 122-docstring mass-write, which is exactly the low-quality bulk event to avoid)
   and any style rule that fires >20× on the existing corpus (measure, list counts
   in the task report, decide per rule).
2. `ruff check` stays green at every commit (the gate already runs it); the ignore
   list only ever *shrinks*, and shrinking it is a normal follow-up task.
3. New public API in future steps: docstring with Google sections required —
   enforced socially via the review protocol now, mechanically once `D1xx` comes out
   of the ignore list.

**Corpus size for planning:** 78 modules / 346 documented public defs / 122
undocumented public defs / 217 role lines. A full-coverage push is **not** scoped
(§6); the API reference ships with curated module pages over the existing corpus.

---

## 5. Implementation plan (→ `development/plans/028_docs_implementation_plan.md`)

The following is written in the `development/plans/` register (cf. `021_ci_hardening_plan.md`,
`022_plan_hash_config_digest_plan.md`) and can be lifted nearly verbatim.

---

# Task 28 — Documentation build: Sphinx + MyST site, API reference, first tutorials, Pages deploy

**Branch:** `task/28-docs-implementation` (from `main`; verify
`git branch --show-current` before every commit). One commit per item A–F below
(6 commits + report). **Prerequisite:** trunk sign-off on TD-1/TD-2/TD-3 of
`development/records/027_docs_plan_record/27_docs_plan.md` (this task implements that
plan; do not re-litigate the stack choice).

## Hard rules (restated; full list in development/plans/README.md)

- No tolerance changes. No data in git. Do not edit `docs/architecture/*` (the
  tutorials and toctrees may *include* those files read-only, never modify them),
  any SPEC/PLAN, or completed steps' STATUS files.
- Dependency additions are exactly the TD-2 list (three dev-group lower bounds +
  four constraints pins) — this task is the explicit grant the prompts-README
  requires. NOTHING else may change in `constraints/*.txt`; gt4py/icon4py/jax pins
  are untouchable. If `uv lock` reports a conflict between the docs pins and the
  existing locked set, STOP and report — resolving it is a trunk decision.
- **Never edit a docstring to silence a Sphinx warning or a ruff `D` finding** in
  this task. Warnings are triaged by config (`suppress_warnings`, per-rule ruff
  ignores), and counts are recorded in the report. Docstring content changes are
  out of scope here (convert-on-touch policy, §4 of the plan).
- Each item has an exact scope. If an item needs more than described, STOP on it,
  mark it "blocked — needs trunk decision" in your report, continue with the others.

## Item A — tooling config + dependencies

**Change:** add the TD-2 dev-group entries to the root `pyproject.toml` and the four
pins to `constraints/cpu-ci.txt` (comment: "task 28: docs build — plan
27_docs_plan §3.3"); run `uv lock` (lockfile grows, existing pins unchanged —
verify with `git diff uv.lock | grep -E '^[-]' | grep -v "^---"` showing no removed
version lines for gt4py/icon4py/jax). Create `docs/conf.py`:

```python
project = "symcon"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.doctest",
    "myst_parser",
]
napoleon_google_docstring = True
napoleon_numpy_docstring = False
myst_enable_extensions = ["dollarmath", "colon_fence"]
autodoc_typehints = "description"
autodoc_member_order = "bysource"
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
html_theme = "furo"
```

No `sys.path` manipulation — autodoc imports the *installed* workspace packages
(verified: `uv run python -c "import symcon.core, symcon.icon"` succeeds).

**Verify:**
```
uv run python -c "import sphinx, myst_parser, furo; print(sphinx.__version__)"   # 8.1.3
uv run sphinx-build -b html docs docs/_build/html                                 # succeeds (item B provides index)
```
**Stop rule:** items B–F depend on A; if A blocks, the task blocks.

## Item B — site skeleton + nav

**Change:** create `docs/index.md` (landing: what symcon is, install, links),
`docs/tutorials/index.md` (curriculum T0–T8 as titles; T0–T2 linked, T3–T8 marked
"planned" with their §1.2 abstracts), `docs/glossary.md` (seed with the terms
introduced by T0–T2), and a toctree that includes `docs/architecture/*.md`
**read-only** (if MyST chokes on a construct in those files, do NOT edit them —
exclude the file from the toctree, link it on GitHub instead, and record which
construct failed). Add `docs/_build/` to `.gitignore`.

**Verify:** `uv run sphinx-build -b html docs docs/_build/html` — zero *errors*
(warnings recorded); `docs/_build/html/index.html` exists; architecture pages
render or are recorded as excluded.

## Item C — API reference wiring

**Change:** `docs/api/index.md` plus one page per curated module group, each a MyST
file wrapping `{eval-rst}` `automodule` blocks with `:members:`. Curated set for
this task (not full coverage): `symcon.core` top-level (`context`, `registry`,
`time`, `config`), `symcon.core.state`, `symcon.core.contracts`,
`symcon.core.components`, `symcon.core.coupling`, `symcon.core.plan`,
`symcon.core.functional`, `symcon.core.io`; `symcon.icon.presets`,
`symcon.icon.names`, `symcon.icon.thermo`, `symcon.icon.grid`,
`symcon.icon.components` (public modules only). `symcon.bridges` is out (optional
toolchain).

**Verify:**
```
uv run sphinx-build -b html docs docs/_build/html 2>&1 | tee /tmp/t28-build.log
grep -c "WARNING" /tmp/t28-build.log     # record the count in the report; do not chase to zero
python -c "import pathlib; t=pathlib.Path('docs/_build/html/api/core.html').read_text(); assert 'ExecutionPlan' in t or 'registry' in t"
```
Spot-check in the built HTML (record in report): one page where a `` :class:` ` ``
role from the existing corpus renders as a hyperlink, and (after item D exists or
via `symcon.core.testing` if it has one) any Google-section docstring rendering as
Parameters/Returns. **Stop rule:** if a module *import* fails under autodoc (e.g.,
an optional dep missing in your env), add it to `autodoc_mock_imports` and record —
never restructure the module.

## Item D — tutorials T0–T2

**Change:** `docs/tutorials/00_what_is_symcon.md`, `01_state_fields_grids.md`,
`02_first_run_scm.md` per the abstracts and audience contract of plan §1. All code
shown for T2 comes from `examples/01_scm_column.py` via `{literalinclude}` with
`:lines:`/`:pyobject:` selectors — no hand-copied code blocks. Each page: the 2–3
new-term budget, glossary links, an "everything here runs" note with the exact
`uv run` command. Math via dollarmath where equations help (T1: unit/staggering
examples).

**Verify:** build clean as in B; every `literalinclude` resolves (a broken include
is a Sphinx error, not a warning); the T2 command `uv run python
examples/01_scm_column.py --hours 1 --output /tmp/t28-scm.nc` still runs (<60 s —
it is CI-smoked, this is a sanity re-run, not a new gate).

## Item E — GitHub Pages workflow

**Change:** `.github/workflows/docs.yml`, artifact flow (NOT a gh-pages branch —
built HTML in a git branch collides with the repo's no-generated-artifacts/no-data
discipline, and the artifact flow needs no branch protection carve-outs):

```yaml
name: docs
on:
  push: { branches: [main] }
  pull_request:
  workflow_dispatch:
concurrency: { group: pages-${{ github.ref }}, cancel-in-progress: true }
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync --frozen
      - run: uv run sphinx-build -b html docs docs/_build/html
      - uses: actions/upload-pages-artifact@v3
        with: { path: docs/_build/html }
  deploy:
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    needs: build
    permissions: { pages: write, id-token: write }
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

Repo setting "Pages → Source: GitHub Actions" is a human/one-time action — note it
in the report and the PR body; you cannot verify deployment locally.

**Verify:** `uv run python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/docs.yml'))"`;
`grep -n "uv sync --frozen" .github/workflows/docs.yml`. Confirm the build job's
sphinx invocation is *identical* to the local one from item B.

## Item F — ruff docstring convention (TD-3) + docs-build CI gate

**Change (two parts, one commit):**
1. `pyproject.toml`: add `"D"` to `[tool.ruff.lint] select`, add
   `[tool.ruff.lint.pydocstyle] convention = "google"`, and an `ignore` list built
   empirically: run `uv run ruff check . --select D --statistics`, put `D1xx`
   and every rule with >20 findings into `ignore` with a one-line comment each
   ("corpus baseline, plan 27 §4; shrink-only"). The final `uv run ruff check .`
   must be green **without any docstring edits**.
2. CI: extend `.github/workflows/lint.yml` with a docs-build step (same
   `sphinx-build` line, no artifact upload) so a PR that breaks the docs build
   fails lint, not just the decorative docs workflow.

**Verify:**
```
uv run ruff check .                       # All checks passed!
uv run ruff format --check .              # unchanged count
uv run ruff check . --select D --statistics   # paste into report (the baseline)
```

## Acceptance criteria

1. Items A–F done exactly as scoped (or explicitly reported blocked), one commit
   each, per-item verifications recorded.
2. `uv run sphinx-build -b html docs docs/_build/html` exits 0 from a clean
   checkout of the branch; warning count recorded and justified.
3. Full README gate green with **unchanged** test baselines (this task adds no
   tests and must not change any counts); ruff gates green with the new `D` config.
4. `git diff main..HEAD --stat` touches ONLY: `pyproject.toml`, `uv.lock`,
   `constraints/cpu-ci.txt`, `.gitignore`, `docs/**` (new files; `docs/architecture/`
   byte-identical), `.github/workflows/docs.yml`, `.github/workflows/lint.yml`, and
   the report `development/records/028_docs_implementation_record.md`.
5. Report includes: built-site page inventory, warning triage table, ruff `D`
   baseline statistics, the "Pages → GitHub Actions" human action item.

## Review checklist (appended to 10_REVIEW_PROTOCOL.md for this task)

- Re-run the docs build yourself from a clean venv (`uv sync --frozen` first);
  confirm exit 0 and that the warning count matches the report.
- Open the built HTML: verify (i) a corpus `` :class:` ` `` role rendering as a
  link, (ii) a Google-section docstring rendering structured, (iii) T2's included
  code matching `examples/01_scm_column.py` byte-for-byte at the cited lines,
  (iv) math rendering on T1.
- `git diff main..HEAD -- docs/architecture/` MUST be empty. Any docstring diff in
  `packages/` is a MAJOR finding (this task edits no docstrings).
- `git diff main..HEAD -- constraints/` shows exactly the four TD-2 additions;
  `uv.lock` diff removes no existing pin (check gt4py/icon4py/jax lines survive).
- Confirm no test-baseline drift: run the fast gate; counts must equal the
  prompts-README baselines current at branch time.
- Workflow hygiene: deploy job gated on `main` push; `permissions` scoped to the
  deploy job only; build job runs on PRs.

---
*(end of liftable task text)*

---

## 6. Out of scope / drift fences (first iteration)

Per `development/ideas/042_p7_presets_docs_anemoi_idea.md`, P7 owns "docs build (architecture doc
canonicalized, API autodoc, porting guide from the S07/S08/P3 pattern); versioning +
release automation". This plan **pulls forward** the docs *tooling* and the
user-tutorial track (which P7 does not mention and this plan adds); it must not
duplicate or contradict the rest. Fences:

- **`porting_guide.md`** (layout doc §4): P7's, explicitly — it needs the S07/S08/P3
  porting pattern to exist at scale. Not started here; the nav gets no placeholder
  that would imply a promise.
- **`coupling.md`** (operator semantics, preset catalogue, validated/experimental
  labels): P7's, tied to the preset-registry step. T4 links the architecture §4.2
  instead.
- **Architecture-doc canonicalization** (P7): the site *includes* the architecture
  documents verbatim; any reshaping into web-native chapters is P7's call. We never
  edit `docs/architecture/*`.
- **Versioned docs** (mike/sphinx-multiversion) + **release automation**: P7, with
  its versioning step. First iteration deploys `main` only.
- **Full API coverage**: curated module set only (§5 item C); driving the 122
  undocumented public defs to zero and unignoring ruff `D1xx` is follow-up work,
  shrink-only.
- **Tutorials T3–T8**: titled + abstracted in nav ("planned"), authored in later
  tasks; T8 should land near P6 (differentiable-distributed) for coherence.
- **Notebook execution in docs CI** (`myst-nb`): waits for a real
  `examples/05_interactive_radiation.ipynb` (currently a layout-doc placeholder).
- **Search tuning, analytics, custom theming/branding, i18n**: out.
- **anemoi docs**: P7's.
- **GPU/MPI-dependent doc examples**: tutorials only show CPU-runnable, CI-smoked
  paths (the audience's laptop is the target).

## 7. References (web documentation consulted; no sources cloned → no REFERENCES.lock entries)

Tool versions below were **empirically installed and exercised** in the /tmp smoke
test on 2026-07-13 (that is the verification, in place of doc-page citation):

- Sphinx 8.1.3 — sphinx-doc.org (autodoc, napoleon, doctest extensions)
- MyST-Parser 4.0.1 — myst-parser.readthedocs.io (dollarmath, colon_fence, eval-rst)
- furo 2025.12.19 — pradyunsg.me/furo
- docutils 0.21.2
- MkDocs 1.6.1 — mkdocs.org
- mkdocs-material 9.7.6 — squidfunk.github.io/mkdocs-material (incl. its MkDocs-2.0
  advisory: …/blog/2026/02/18/mkdocs-2.0/, surfaced verbatim at build time)
- mkdocstrings 1.0.6 / mkdocstrings-python 2.0.5 / griffelib 2.1.0 /
  mkdocs-autorefs 1.4.4 — mkdocstrings.github.io
- Quarto/quartodoc — quarto.org, machow.github.io/quartodoc (assessed from
  documentation only; **not** smoke-tested — flagged as such in §2.4)
- GitHub Pages Actions deploy — docs.github.com (actions/upload-pages-artifact@v3,
  actions/deploy-pages@v4 flow)

## Appendix A — smoke-test transcripts (2026-07-13, /tmp/docsmoke, python 3.10.18)

**Fixture:** two source roots emulating the PEP 420 namespace split —
`src/symcon/core/` holding copies of `registry.py` (real corpus module, dense with
`:class:` roles), `time.py` (real), `gsample.py` (synthetic Google-style docstring:
`Args:/Returns:/Raises:` on `saturation_vapor_pressure`), and `src2/symcon/icon/`
holding copies of `thermo.py` + `_constants.py`. No `symcon/__init__.py` anywhere.

**(a) MkDocs leg**

```
$ uv venv /tmp/docsmoke/venv-mkdocs
$ VIRTUAL_ENV=... uv pip install mkdocs mkdocs-material "mkdocstrings[python]"
# → mkdocs 1.6.1, mkdocs-material 9.7.6, mkdocstrings 1.0.6,
#   mkdocstrings-python 2.0.5, griffelib 2.1.0, mkdocs-autorefs 1.4.4
# mkdocs.yml: theme material; plugin mkdocstrings, handler python,
#   paths: [../src, ../src2], docstring_style: google
# docs/index.md: "::: symcon.core.gsample", "::: symcon.core.registry",
#   "::: symcon.icon.thermo"
$ mkdocs build
│  ⚠  Warning from the Material for MkDocs team
│   MkDocs 2.0, the underlying framework of Material for MkDocs,
│   will introduce backward-incompatible changes, including:
│  × All plugins will stop working – the plugin system has been removed
│  × All theme overrides will break – the theming system has been rewritten
│  × No migration path exists – existing projects cannot be upgraded
│  × Closed contribution model – community members can't report bugs
│  × Currently unlicensed – unsuitable for production use
│   https://squidfunk.github.io/mkdocs-material/blog/2026/02/18/mkdocs-2.0/
INFO - Documentation built in 1.71 seconds
```

Rendered-HTML probes (tags stripped):

- Google sample: `"Parameters: Name Type Description Default temperature float Air
  temperature in kelvin. required over_ice bool … Returns: … Raises: …"` →
  **full typed tables; PASS**.
- Namespace collection: `symcon.icon.thermo` members (`exner_from_pressure`, …)
  present alongside `symcon.core.*` → **two-root PEP 420 collection PASS, with no
  imports executed** (static analysis; heavy deps never installed in this venv).
- Existing corpus: `"Usage: a registry root subclasses :class: Factory directly"` →
  **role rendered as literal text; FAIL** for the 217-line role corpus.

**(b) Sphinx leg**

```
$ uv venv /tmp/docsmoke/venv-sphinx
$ VIRTUAL_ENV=... uv pip install sphinx myst-parser furo cftime array_api_compat numpy
# → sphinx 8.1.3 (8.2+ needs py≥3.11), myst-parser 4.0.1, furo 2025.12.19,
#   docutils 0.21.2; cftime/array_api_compat needed because autodoc IMPORTS
# conf.py: sys.path ← both roots; extensions autodoc+napoleon+mathjax+myst_parser;
#   napoleon_google_docstring=True; myst dollarmath; html_theme furo
# index.md (MyST): $\partial_t \rho = -\nabla\cdot(\rho\mathbf{v})$ +
#   {eval-rst} automodule blocks for gsample / registry / thermo
$ sphinx-build -b html . _build     # build succeeded
$ sphinx-build -q -b html -E . _build2   # fresh: 0.52 s
```

Rendered-HTML probes:

- Google sample: `"Parameters: temperature – Air temperature in kelvin. …
  Returns: … Raises: ValueError – …"` → **Napoleon PASS**.
- Existing corpus: literal `":class:"` **absent**; regex probe found
  `<a href="#symcon.core.registry.Factory">` → **role resolved to hyperlink; PASS**.
- Cross-root namespace import: `symcon.icon.thermo` members rendered → **PASS**
  (import-based; in-repo equivalent verified separately:
  `uv run python -c "import symcon.core, symcon.icon"` → `import OK` in the
  workspace env, so no mocks needed for the real build).
- Math: MathJax assets + rendered expression present → **PASS**.

**Corpus survey commands** (repo, `packages/*/src`, 78 files): role/section counts
via `grep -rn ":func:\|:mod:\|:class:\|:meth:"` (217), `grep` for
`Args:/Returns:/Raises:` (0) and reST field lists (0), double-backtick lines (1441),
`ast` walk for docstring coverage (78/78 modules; 346 public defs with, 122
without).
