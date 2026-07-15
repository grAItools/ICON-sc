# S01 — Plan

1. **Discover the pin.** Clone icon4py; inspect its lock/requirements for the gt4py version it is tested against; choose the latest icon4py tag/commit whose CI is green. Record `icon4py@<sha>`, `gt4py@<version>` in `constraints/*.txt` and `development/references/lock.toml`. If icon4py ships subpackages as separate distributions (`icon4py-model-common`, `-atmosphere-dycore`, …), pin each; note the discovered distribution names — later SPECs refer to them symbolically as `icon4py.common`, `icon4py.dycore`, etc.
2. Scaffold the workspace exactly per the layout document (§0–§1 trees). Use PEP 420 namespace packaging (`symcon/` without `__init__.py` at namespace level — verify with two-package import test).
3. Write `.importlinter` contracts + the negative unit test of acceptance 2.
4. `symcon.core.testing`: implement `assert_allclose` (wrap numpy.testing; on failure, report argmax |rel err| index, both values, and the field `names`); conftest with marker registration and a `backend` fixture parametrized `["embedded", "gtfn_cpu"]` + `pytest.param("gtfn_gpu", marks=gpu)` — values are strings until S02 gives them meaning.
5. CI workflows; cache uv; constraints matrix on test-cpu.
6. Placeholder READMEs; commit `development/references/lock.toml`.

**Pitfalls:** namespace packages + mypy need explicit `mypy_path`/packages config; get strict mypy green on the (nearly empty) core now, not later. Do not vendor icon4py; it is a dependency.
