# symcon docs — Sphinx configuration (task 28; stack decided in
# development/work/reports/report-0027-docs-plan/27_docs_plan.md §3, TD-1/TD-2).
# Autodoc imports the *installed* workspace packages — no sys.path manipulation.

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
# Auto-generate anchors for h1/h2 so tutorials can link glossary entries as
# glossary.md#<term-slug> (MyST resolves file#fragment against heading anchors).
myst_heading_anchors = 2
autodoc_typehints = "description"
autodoc_member_order = "bysource"
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
html_theme = "furo"

# Build hygiene (config-level triage only; never edit content to silence warnings):
# - _build: never re-ingest our own output;
# - api/README.md: the pre-existing placeholder note for this directory (the rendered
#   entry point is api/index.md).
exclude_patterns = ["_build", "api/README.md"]
