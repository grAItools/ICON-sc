"""L4 (architecture §9): the composed dry model vs the icon4py-driver JW reference.

SPEC S13 acceptance 3 + 4. Requires the cached reference from
``make_reference.py`` (skips with instructions otherwise — CI never generates it,
AGENTS.md) and the JW datatest archive. Markers: ``data`` + ``slow`` — the 9-day
symcon trajectory runs inside the test (hours of CPU; not part of the package
gates, which cover ``packages/`` only).

Tolerance schedule (documented per PLAN item 4): icon4py's own driver tests verify
exactly ONE timestep at this grid (vn atol=6e-12 etc. — adopted verbatim in
``packages/symcon-icon/tests/test_jw_datatest.py``); no upstream multi-day schedule
exists, so the day-9 envelope is derived from the reference's ε-perturbed twin
(initial vn + 1e-13 m/s): at every checkpoint the symcon-vs-reference surface
pressure deviation must stay within ``max(10 x twin-envelope(t), 0.1 Pa)`` — the
0.1 Pa floor is the SPEC's own day-1 criterion (rtol 1e-6 of ~1e5 Pa) and the
factor 10 covers the different (rounding-level vs 1e-13) seeding of the two
divergence pairs. Day 1 additionally enforces the SPEC's rtol ≤ 1e-6 verbatim.
"""

from __future__ import annotations

import json
import os
import pathlib
from datetime import timedelta
from typing import Any

import numpy as np
import pytest

pytestmark = [pytest.mark.data, pytest.mark.slow]

CACHE_DIR = pathlib.Path(
    os.environ.get(
        "SYMCON_L4_CACHE", str(pathlib.Path.home() / ".cache" / "symcon" / "l4_reference")
    )
)
ARTIFACTS = pathlib.Path(__file__).parent / "artifacts"

#: SPEC acceptance 3: surface-pressure rtol at day 1.
DAY1_RTOL = 1.0e-6
#: Envelope safety factor + floor (see module docstring).
ENVELOPE_FACTOR = 10.0
ENVELOPE_FLOOR_PA = 0.1
#: SPEC acceptance 4: zonal-symmetry preservation over 12 h.
SYMMETRY_RTOL = 1.0e-10


def _load_manifest() -> dict[str, Any]:
    manifest_path = CACHE_DIR / "manifest.json"
    if not manifest_path.exists():
        pytest.skip(
            f"L4 reference not cached at {CACHE_DIR} — generate it once with "
            f"`uv run python validation/L4_idealized/make_reference.py` "
            f"(hours of CPU; never run in CI)."
        )
    return json.loads(manifest_path.read_text())


def _load_run(manifest: dict[str, Any], tag: str) -> dict[str, np.ndarray]:
    import hashlib

    entry = manifest["files"][tag]
    path = CACHE_DIR / entry["name"]
    if not path.exists():
        pytest.skip(f"L4 reference file missing: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert digest == entry["sha256"], (
        f"L4 reference {path} fails its manifest checksum — regenerate with "
        f"make_reference.py --force"
    )
    with np.load(path) as data:
        return {key: np.asarray(data[key]) for key in data.files}


@pytest.fixture(scope="module")
def manifest() -> dict[str, Any]:
    pytest.importorskip("icon4py.model.testing", reason="symcon-icon[datatest] required")
    return _load_manifest()


@pytest.fixture(scope="module")
def jw_trajectories(manifest: dict[str, Any]) -> dict[str, Any]:
    """Reference + twin from the cache; the symcon trajectory computed here (once)."""
    from symcon.icon.presets import JWConfig, build_jw

    reference = _load_run(manifest, "reference")
    twin = _load_run(manifest, "twin")

    model = build_jw(
        JWConfig(
            perturbation_amplitude=float(manifest["provenance"]["perturbation_amplitude"]),
            backend="gtfn_cpu",
        )
    )
    # -- config congruence before any trajectory comparison (PLAN pitfall) ----------
    ours = {k: v for k, v in model.provenance.items() if k != "backend"}
    theirs = {k: v for k, v in manifest["provenance"].items() if k != "backend"}
    assert ours == theirs, "preset provenance != reference provenance"
    assert model.level_850 == int(manifest["level_850"])

    checkpoint_hours = float(manifest["checkpoint_hours"])
    stride = round(checkpoint_hours * 3600.0 / model.dtime.total_seconds())
    n_checkpoints = len(reference["hours"]) - 1

    state = dict(model.state)
    hours = [0.0]
    checkpoints = [model.checkpoint(state)]
    for index in range(n_checkpoints):
        for _ in range(stride):
            state = model.step(state, model.dtime)
        hours.append((index + 1) * checkpoint_hours)
        checkpoints.append(model.checkpoint(state))

    symcon = {
        "hours": np.asarray(hours),
        "surface_pressure": np.stack([c["surface_pressure"] for c in checkpoints]),
        "vn_l2": np.asarray([c["vn_l2"] for c in checkpoints]),
        "vn_linf": np.asarray([c["vn_linf"] for c in checkpoints]),
        "vorticity_850": np.stack([c["vorticity_850"] for c in checkpoints]),
    }
    return {"reference": reference, "twin": twin, "symcon": symcon, "model": model}


def test_l4_day1_surface_pressure(jw_trajectories: dict[str, Any]) -> None:
    """SPEC acceptance 3, day-1 leg: ps rtol <= 1e-6 vs the driver reference."""
    reference, symcon = jw_trajectories["reference"], jw_trajectories["symcon"]
    np.testing.assert_array_equal(reference["hours"], symcon["hours"])
    day1 = int(np.argwhere(np.isclose(reference["hours"], 24.0))[0, 0])
    np.testing.assert_allclose(
        symcon["surface_pressure"][day1],
        reference["surface_pressure"][day1],
        rtol=DAY1_RTOL,
        atol=0.0,
        err_msg="day-1 surface pressure vs icon4py-driver reference",
    )


def test_l4_trajectory_within_twin_envelope(jw_trajectories: dict[str, Any]) -> None:
    """SPEC acceptance 3, day-9 leg: every checkpoint within the documented envelope
    derived from the reference's ε-perturbed twin (see module docstring)."""
    reference = jw_trajectories["reference"]
    twin = jw_trajectories["twin"]
    symcon = jw_trajectories["symcon"]

    envelope = np.max(np.abs(twin["surface_pressure"] - reference["surface_pressure"]), axis=1)
    deviation = np.max(np.abs(symcon["surface_pressure"] - reference["surface_pressure"]), axis=1)
    bound = np.maximum(ENVELOPE_FACTOR * envelope, ENVELOPE_FLOOR_PA)

    ARTIFACTS.mkdir(exist_ok=True)
    table = np.column_stack([reference["hours"], deviation, envelope, bound])
    np.savetxt(
        ARTIFACTS / "l4_ps_deviation.txt",
        table,
        header="hours  max|ps_symcon-ps_ref| [Pa]  twin_envelope [Pa]  bound [Pa]",
    )
    _plot(reference["hours"], deviation, envelope, bound)

    violations = deviation > bound
    assert not violations.any(), (
        f"surface-pressure deviation exceeds the twin envelope at hours "
        f"{reference['hours'][violations]}: deviation {deviation[violations]} Pa vs "
        f"bound {bound[violations]} Pa"
    )
    # secondary norms: same criterion shape on the vorticity proxy and vn norms.
    vort_envelope = np.max(np.abs(twin["vorticity_850"] - reference["vorticity_850"]), axis=1)
    vort_deviation = np.max(np.abs(symcon["vorticity_850"] - reference["vorticity_850"]), axis=1)
    vort_floor = 1e-6 * max(1.0, float(np.max(np.abs(reference["vorticity_850"]))))
    assert (vort_deviation <= np.maximum(ENVELOPE_FACTOR * vort_envelope, vort_floor)).all()
    for norm in ("vn_l2", "vn_linf"):
        norm_envelope = np.abs(twin[norm] - reference[norm])
        norm_deviation = np.abs(symcon[norm] - reference[norm])
        norm_floor = 1e-6 * max(1.0, float(np.max(np.abs(reference[norm]))))
        within = norm_deviation <= np.maximum(ENVELOPE_FACTOR * norm_envelope, norm_floor)
        assert within.all(), norm


def _plot(
    hours: np.ndarray, deviation: np.ndarray, envelope: np.ndarray, bound: np.ndarray
) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(7, 4.5))
    positive = np.maximum.reduce([deviation, np.full_like(deviation, 1e-16)])
    ax.semilogy(hours / 24.0, positive, label="max|ps symcon - ps reference|")
    ax.semilogy(hours / 24.0, np.maximum(envelope, 1e-16), "--", label="twin envelope (ε=1e-13)")
    ax.semilogy(hours / 24.0, bound, ":", label="bound (10x envelope, 0.1 Pa floor)")
    ax.set_xlabel("days")
    ax.set_ylabel("surface pressure deviation [Pa]")
    ax.set_title("L4: JW baroclinic wave, symcon vs icon4py driver (R02B04L35)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(ARTIFACTS / "l4_ps_deviation.png", dpi=150)
    plt.close(fig)


def test_l4_zonal_symmetry_12h() -> None:
    """SPEC acceptance 4: perturbation off → surface pressure stays constant within
    latitude rings (the discrete symmetry classes of the icosahedral grid) to 1e-10
    relative over 12 h — the classic dycore smoke."""
    pytest.importorskip("icon4py.model.testing", reason="symcon-icon[datatest] required")

    from symcon.icon.presets import JWConfig, build_jw

    model = build_jw(JWConfig(perturbation_amplitude=0.0, backend="gtfn_cpu"))

    state = dict(model.state)
    n_steps = int(timedelta(hours=12) / model.dtime)
    for _ in range(n_steps):
        state = model.step(state, model.dtime)
    ps = model.checkpoint(state)["surface_pressure"]

    # latitude rings: cells whose latitudes agree to 1e-12 rad (symmetry classes).
    lat = _cell_latitudes()
    order = np.argsort(lat, kind="stable")
    sorted_lat = lat[order]
    ring_break = np.concatenate([[True], np.diff(sorted_lat) > 1e-12])
    ring_id = np.cumsum(ring_break) - 1

    sorted_ps = ps[order]
    n_rings = ring_id[-1] + 1
    sums = np.bincount(ring_id, weights=sorted_ps, minlength=n_rings)
    counts = np.bincount(ring_id, minlength=n_rings)
    ring_mean = sums / counts
    spread = np.abs(sorted_ps - ring_mean[ring_id]) / np.abs(ring_mean[ring_id])

    ARTIFACTS.mkdir(exist_ok=True)
    with open(ARTIFACTS / "l4_symmetry_12h.txt", "w") as stream:
        stream.write(
            f"rings={n_rings} max_ring_spread_rel={spread.max():.3e} "
            f"ps_range=[{ps.min():.6f},{ps.max():.6f}]\n"
        )
    assert spread.max() <= SYMMETRY_RTOL, (
        f"zonal symmetry broken: max relative ring spread {spread.max():.3e} > "
        f"{SYMMETRY_RTOL} after 12 h"
    )


def _cell_latitudes() -> np.ndarray:
    from icon4py.model.common.decomposition import definitions as decomposition
    from icon4py.model.testing import datatest_utils as dtu
    from icon4py.model.testing import definitions as i4_definitions

    props = decomposition.get_process_properties(decomposition.get_runtype(with_mpi=False))
    provider = dtu.create_icon_serial_data_provider(
        dtu.get_datapath_for_experiment(i4_definitions.Experiments.JW, props), props.rank, None
    )
    grid_savepoint = provider.from_savepoint_grid(
        i4_definitions.Experiments.JW.name, i4_definitions.Experiments.JW.grid.params
    )
    cell_geometry = grid_savepoint.construct_cell_geometry()
    return np.asarray(cell_geometry.cell_center_lat.asnumpy(), dtype=np.float64)
