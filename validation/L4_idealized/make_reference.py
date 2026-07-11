"""L4 reference-trajectory generator: the pinned icon4py driver on the JW experiment.

Runs ``icon4py.model.driver.icon4py_driver.TimeLoop`` (v0.2.0 — REFERENCES.lock
``icon4py-driver-jw``) for 9 days on the JW baroclinic wave (perturbation 1 m/s)
and caches checkpoints (6-hourly surface-pressure field, vn L2/L∞, 850 hPa vertex
vorticity) plus an ε-perturbed twin (initial vn + 1e-13 m/s: the perturbed-IC pair
that defines the chaotic-growth envelope, PLAN S13 item 4 — the probtest idea at
minimum viable scale) under ``~/.cache/symcon/l4_reference/`` with sha256 checksums
and full config provenance. CI never runs this (AGENTS.md); ``test_jw.py`` skips
when the cache is missing.

Construction notes (documented deviation, STATUS S13): the granules handed to the
upstream ``TimeLoop`` are the instances hosted inside the symcon preset
(``model.dycore._solve`` / ``model.diffusion._diffusion``) — genuine icon4py
``SolveNonhydro``/``Diffusion`` objects built from the archive's savepoint fields
and namelist config, i.e. byte-identical inputs to an upstream-built granule; the
*orchestration* under test (substepping, swaps, diffusion placement) is entirely
upstream ``TimeLoop`` code. This guarantees "same grid/config" by construction and
is asserted again by the provenance check in ``test_jw.py``.

Usage::

    uv run python validation/L4_idealized/make_reference.py [--days 9] [--force]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import time
from typing import Any

import numpy as np

CACHE_DIR = pathlib.Path(
    os.environ.get(
        "SYMCON_L4_CACHE", str(pathlib.Path.home() / ".cache" / "symcon" / "l4_reference")
    )
)
CHECKPOINT_HOURS = 6.0
EPSILON_VN = 1.0e-13  # twin-run initial vn shift [m/s] (PLAN S13 item 4)
PERTURBATION = 1.0  # jw_up [m/s] — the classic baroclinic wave


def sha256_of(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _icon4py_states(model: Any, *, vn_shift: float) -> tuple[Any, Any, Any, Any]:
    """icon4py state objects for TimeLoop from the preset's initial symcon state.

    Mirrors what the driver's ``read_initial_state``/``model_initialization_jabw``
    returns: prognostic now == next, zeroed diffusion diagnostics, a nonhydro
    diagnostic state seeded with perturbed exner = exner - exner_ref, zeroed
    prep_adv. ``vn_shift`` implements the twin run's ε-perturbed initial vn.
    """
    import gt4py.next as gtx
    from icon4py.model.atmosphere.dycore import dycore_states
    from icon4py.model.common import dimension as dims
    from icon4py.model.common import utils as i4_utils
    from icon4py.model.common.states import prognostic_state as i4_prognostics

    grid = model.dycore._i4_grid
    allocator = model.dycore._backend.gt4py_backend
    state = model.state

    def cell_k(name: str) -> np.ndarray:
        return np.ascontiguousarray(np.asarray(state[name].data), dtype=np.float64)

    vn_host = (
        np.ascontiguousarray(np.asarray(state["icon:normal_wind"].data), dtype=np.float64)
        + vn_shift
    )

    def as_field(host: np.ndarray, *fdims: Any) -> Any:
        return gtx.as_field(fdims, host, allocator=allocator)

    def prognostic() -> Any:
        return i4_prognostics.PrognosticState(
            vn=as_field(vn_host.copy(), dims.EdgeDim, dims.KDim),
            w=as_field(cell_k("upward_air_velocity_on_interface_levels"), dims.CellDim, dims.KDim),
            rho=as_field(cell_k("air_density"), dims.CellDim, dims.KDim),
            exner=as_field(cell_k("icon:exner_function"), dims.CellDim, dims.KDim),
            theta_v=as_field(cell_k("icon:virtual_potential_temperature"), dims.CellDim, dims.KDim),
        )

    prognostic_states = i4_utils.TimeStepPair(prognostic(), prognostic())

    from icon4py.model.atmosphere.diffusion import diffusion_states

    diffusion_diagnostic = diffusion_states.initialize_diffusion_diagnostic_state(
        grid=grid, allocator=allocator
    )
    exner_ref = model.dycore._exner_ref_mc.ndarray
    perturbed_exner_host = cell_k("icon:exner_function") - np.asarray(exner_ref)
    nonhydro_diagnostic = dycore_states.initialize_solve_nonhydro_diagnostic_state(
        perturbed_exner_at_cells_on_model_levels=as_field(
            perturbed_exner_host, dims.CellDim, dims.KDim
        ),
        grid=grid,
        allocator=allocator,
    )
    prep_adv = dycore_states.initialize_prep_advection(grid=grid, allocator=allocator)
    return diffusion_diagnostic, nonhydro_diagnostic, prognostic_states, prep_adv


def generate(tag: str, *, days: float, vn_shift: float, model: Any) -> pathlib.Path:
    """One 9-day TimeLoop run with 6-hourly checkpoints -> NPZ in the cache."""
    from icon4py.model.driver import icon4py_configuration as driver_config
    from icon4py.model.driver import icon4py_driver

    dtime = model.dtime
    chunk = datetime.timedelta(hours=CHECKPOINT_HOURS)
    steps_per_chunk = chunk // dtime
    assert steps_per_chunk * dtime == chunk
    n_chunks = round(days * 24.0 / CHECKPOINT_HOURS)

    start = datetime.datetime(2000, 1, 1)
    run_config = driver_config.Icon4pyRunConfig(
        dtime=dtime,
        start_date=start,
        end_date=start + chunk,  # one checkpoint interval per time_integration call
        n_substeps=int(model.provenance["ndyn_substeps"]),
        apply_initial_stabilization=False,  # the JW driver config (ltestcase path)
        restart_mode=False,
        backend=model.dycore._backend.gt4py_backend,
    )
    timeloop = icon4py_driver.TimeLoop(run_config, model.diffusion._diffusion, model.dycore._solve)

    diffusion_diag, nonhydro_diag, prognostic_states, prep_adv = _icon4py_states(
        model, vn_shift=vn_shift
    )

    def snapshot() -> dict[str, np.ndarray]:
        current = prognostic_states.current
        wrapped = {
            "icon:exner_function": _wrap(current.exner),
            "icon:virtual_potential_temperature": _wrap(current.theta_v),
            "icon:normal_wind": _wrap(current.vn),
        }
        return model.checkpoint(wrapped)

    hours = [0.0]
    checkpoints = [snapshot()]
    for index in range(n_chunks):
        t0 = time.time()
        timeloop.time_integration(
            diffusion_diagnostic_state=diffusion_diag,
            solve_nonhydro_diagnostic_state=nonhydro_diag,
            prognostic_states=prognostic_states,
            prep_adv=prep_adv,
            second_order_divdamp_factor=float(model.provenance["second_order_divdamp_factor"]),
            do_prep_adv=False,
        )
        hours.append((index + 1) * CHECKPOINT_HOURS)
        checkpoints.append(snapshot())
        print(
            f"  [{tag}] +{hours[-1]:6.1f} h ({steps_per_chunk} steps in "
            f"{time.time() - t0:6.1f} s)  ps range "
            f"[{checkpoints[-1]['surface_pressure'].min():10.2f}, "
            f"{checkpoints[-1]['surface_pressure'].max():10.2f}] Pa",
            flush=True,
        )

    out = CACHE_DIR / f"jw_l4_{tag}.npz"
    np.savez_compressed(
        out,
        hours=np.asarray(hours),
        surface_pressure=np.stack([c["surface_pressure"] for c in checkpoints]),
        vn_l2=np.asarray([c["vn_l2"] for c in checkpoints]),
        vn_linf=np.asarray([c["vn_linf"] for c in checkpoints]),
        vorticity_850=np.stack([c["vorticity_850"] for c in checkpoints]),
        vn_shift=np.asarray(vn_shift),
    )
    return out


class _Wrapped:
    """Minimal .data view so model.checkpoint accepts granule fields."""

    def __init__(self, field: Any) -> None:
        self.data = np.asarray(field.asnumpy())


def _wrap(field: Any) -> _Wrapped:
    return _Wrapped(field)


def main(days: float = 9.0, force: bool = False) -> None:
    from symcon.icon.presets import JWConfig, build_jw

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = CACHE_DIR / "manifest.json"
    if manifest_path.exists() and not force:
        print(f"reference already cached at {CACHE_DIR} (use --force to regenerate)")
        return

    print("building the JW model (archive download on first use)...", flush=True)
    model = build_jw(JWConfig(perturbation_amplitude=PERTURBATION, backend="gtfn_cpu"))

    files = {}
    for tag, shift in (("reference", 0.0), ("twin", EPSILON_VN)):
        print(f"generating {tag} trajectory ({days} days)...", flush=True)
        files[tag] = generate(tag, days=days, vn_shift=shift, model=model)

    manifest = {
        "generator": "icon4py TimeLoop v0.2.0 (28d32c45afb4dbea1da6b6e5170202f08b4adb88)",
        "days": days,
        "checkpoint_hours": CHECKPOINT_HOURS,
        "epsilon_vn": EPSILON_VN,
        "provenance": dict(model.provenance),
        "level_850": model.level_850,
        "created": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "files": {
            tag: {"name": path.name, "sha256": sha256_of(path)} for tag, path in files.items()
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str))
    print(f"manifest written: {manifest_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=float, default=9.0)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    main(days=args.days, force=args.force)
