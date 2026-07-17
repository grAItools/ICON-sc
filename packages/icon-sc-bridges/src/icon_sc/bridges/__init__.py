"""symcon.bridges — CFFI-wrapped Fortran bridge components.

Bridge components (ecRad reference, Tiedtke-Bechtold, TERRA) arrive when validation
needs them. May import ``symcon.core`` only; selected via the component registry so
``symcon.icon`` never imports this package directly.
"""

__version__ = "0.1.0"
