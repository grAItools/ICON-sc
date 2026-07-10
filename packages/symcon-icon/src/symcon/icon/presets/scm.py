"""The single-column (SCM) preset: SUS fast physics + slow-tendency bus (SPEC S09).

The first scientifically meaningful symcon composition — the architecture-§5.1
loop shape at column scale, running under T0:

- **fast suite**: ``SequentialUpdateSplitting`` over ``SCM_FAST_ORDER =
  ("satad", "mphys", "satad")`` — the SCM subset of ICON's fast-physics calling
  sequence (tutorial §3.7.2 / ``mo_nh_interface_nwp.f90``, REFERENCES.lock
  ``icon-tutorial-2025`` + ``icon-fortran-nwp-interface``: saturation adjustment
  before, and again after, microphysics "to ensure that vapor and liquid phase
  are in equilibrium before entering the slow physics parameterizations");
- **slow suite**: a ``CallingFrequency``-wrapped
  :class:`~symcon.icon.components.idealized.PrescribedCooling` inside a
  ``ConcurrentCoupling``, publishing a piecewise-constant tendency to the
  ``icon:ddt_temperature_slow`` bus slot at cadence ``slow_timestep``
  (tutorial §3.7.2: slow tendencies are "kept constant between two successive
  calls");
- **consumer**: :class:`~symcon.icon.components.idealized.ApplySlowTendencies`
  standing in for the dycore's slow-tendency port; the
  :class:`~symcon.core.coupling.bus.SlowTendencyBus` single-consumer check runs
  at build time, so a preset without the consumer refuses to build.

The tutorial's ordering prose is carried as *machine-checkable constraints*
(:data:`SCM_COUPLING_CONSTRAINTS`, applied to the built instances): swapping
sections against them raises
:class:`~symcon.core.coupling.constraints.CouplingConstraintError` at
composition time (acceptance 4).

Initial column (PLAN item 3, provenance): the S06
:func:`~symcon.icon.testing.moist_test_column` ``"reference_moist"`` profile —
T/p from the ICON decaying-isothermal reference atmosphere
(``mo_vertical_grid.f90``) with an exponentially decaying water-vapor profile —
made convectively/condensationally unstable by scaling the humidity
(``qv_scale``, default 2: the lower troposphere starts supersaturated, so satad
condenses immediately and graupel precipitates), plus the cloud droplet number
concentration ``icon:qnc`` the graupel scheme consumes (ICON default
``cloud_num`` = 200e6 m⁻³, ``gscp_data.f90``, REFERENCES.lock
``icon-fortran-graupel``).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from datetime import timedelta
from typing import Any, Final

import numpy as np

from symcon.core import (
    CallingFrequency,
    ComputeContext,
    ConcurrentCoupling,
    CouplingConstraints,
    SequentialUpdateSplitting,
    SlowTendencyBus,
    TendencySlot,
    constraints_of,
)
from symcon.core.state import canonical_units, make_dataarray
from symcon.core.time import datetime
from symcon.icon.components.fast.graupel_constants import CLOUD_NUM
from symcon.icon.components.fast.microphysics import GraupelConfig, Microphysics
from symcon.icon.components.fast.satad import (
    SaturationAdjustment,
    SaturationAdjustmentConfig,
)
from symcon.icon.components.idealized import (
    SLOW_TEMPERATURE_SLOT,
    ApplySlowTendencies,
    PrescribedCooling,
    PrescribedCoolingConfig,
)
from symcon.icon.grid.vertical import SleveConfig, VerticalGrid
from symcon.icon.testing import moist_test_column

__all__ = [
    "SCM_COUPLING_CONSTRAINTS",
    "SCM_FAST_ORDER",
    "SCMComposition",
    "SCMConfig",
    "build_scm",
]

#: The SCM fast-physics calling sequence (frozen interface, SPEC S09): the
#: satad → microphysics → satad subset of ICON's NWP fast-physics order
#: (tutorial §3.7.2; the full ``NWP_FAST_ORDER`` arrives with the P3 schemes).
SCM_FAST_ORDER: Final[tuple[str, str, str]] = ("satad", "mphys", "satad")

#: Tutorial-§3.7.2 ordering semantics as machine-checkable constraints, keyed by
#: the ``SCM_FAST_ORDER`` section names and applied to the built instances (the
#: S07/S08 *classes* declare only ``admissible_operators`` — an ordering
#: constraint against satad cannot live on the Graupel class without outlawing
#: the bare ``satad → graupel`` compositions the S08 suite validates):
#: microphysics must come after a saturation adjustment and be followed by one.
SCM_COUPLING_CONSTRAINTS: Final[Mapping[str, CouplingConstraints]] = {
    "mphys": CouplingConstraints(
        must_follow=("satad",),
        must_precede=("satad",),
        admissible_operators=("sequential_update_splitting",),
    ),
}


@dataclasses.dataclass(frozen=True)
class SCMConfig:
    """Configuration of the SCM preset (architecture §5.3 style: typed, frozen).

    ``slow_timestep`` defaults to exactly ``10 · dtime`` (SPEC acceptance 3);
    any positive value is legal — a non-multiple is rounded to the nearest
    multiple of the loop timestep by the frozen S03 ``CallingFrequency`` rule
    (the tutorial §3.7.1 rounds *up*; see STATUS S09).
    """

    #: Vertical levels of the S06 default (flat-terrain) ICON grid.
    nlev: int = 65
    #: Horizontal extent (independent columns; the preset is single-column).
    n_cell: int = 1
    #: Fast-physics / loop timestep Δt.
    dtime: timedelta = timedelta(seconds=30)
    #: Slow-physics cadence (default 10·Δt).
    slow_timestep: timedelta = timedelta(seconds=300)
    #: Humidity scaling of the reference_moist profile (module docstring).
    qv_scale: float = 2.0
    #: Cloud droplet number concentration [m-3] (ICON default ``cloud_num``).
    qnc: float = CLOUD_NUM
    #: Initial model time.
    start_time: Any = dataclasses.field(default_factory=lambda: datetime(2000, 1, 1))
    #: Newtonian-cooling (slow forcing) parameters.
    cooling: PrescribedCoolingConfig = dataclasses.field(default_factory=PrescribedCoolingConfig)
    #: Saturation-adjustment configuration (both SUS occurrences share it).
    satad: SaturationAdjustmentConfig = dataclasses.field(
        default_factory=SaturationAdjustmentConfig
    )
    #: Microphysics (graupel scheme) configuration.
    microphysics: GraupelConfig = dataclasses.field(default_factory=GraupelConfig)


@dataclasses.dataclass(frozen=True)
class SCMComposition:
    """The built SCM composition: §5.1 loop pieces + one ``step`` to drive them.

    ``step`` is the loop body of the canonical run script at column scale
    (architecture §5.1): slow-tendency publication into the bus slots, the
    consumer (dycore stand-in), then the fast SUS suite. It matches the
    :func:`symcon.core.driver.timeloop` ``StepFn`` shape.
    """

    #: The slow suite: ConcurrentCoupling of CallingFrequency-wrapped processes.
    slow: ConcurrentCoupling
    #: The CallingFrequency wrapper around the cooling (cadence/phase accessors).
    cooling: CallingFrequency
    #: The bus consumer (dycore stand-in for the slow-tendency port).
    core: ApplySlowTendencies
    #: The fast-physics SequentialUpdateSplitting federation.
    fast: SequentialUpdateSplitting
    #: The composition-time bus bookkeeping (checked by the builder).
    bus: SlowTendencyBus
    #: The fast-suite section order the federation was built with.
    order: tuple[str, ...]

    def step(self, state: Mapping[str, Any], timestep: timedelta) -> dict[str, Any]:
        """One Δt of the SCM loop body; returns the advanced state (T0 semantics)."""
        working: dict[str, Any] = dict(state)
        # Slow suite: lazy, piecewise-constant → icon:ddt_* bus slots (§5.1).
        tendencies, diagnostics = self.slow(working, timestep)
        working.update(diagnostics)
        working.update(tendencies)
        # Consumer: the dycore stand-in integrates the bus slot over Δt.
        diags, new_state = self.core(working, timestep)
        working.update(diags)
        working.update(new_state)
        # Fast suite: sequential updates (each section corrects its predecessor).
        diags, new_state = self.fast(working, timestep)
        working.update(diags)
        working.update(new_state)
        return working


def _initial_column(cfg: SCMConfig) -> dict[str, Any]:
    """The preset's initial state (provenance in the module docstring)."""
    state = moist_test_column(
        "reference_moist", nlev=cfg.nlev, n_cell=cfg.n_cell, time=cfg.start_time
    )
    state["specific_humidity"].data[:] *= cfg.qv_scale
    state["icon:qnc"] = make_dataarray(
        np.full((cfg.n_cell,), cfg.qnc),
        name="icon:qnc",
        dims=("cell",),
        units=canonical_units("icon:qnc"),
        location="cell",
    )
    return state


def build_scm(
    cfg: SCMConfig | None = None,
    *,
    ctx: ComputeContext | None = None,
    fast_order: Sequence[str] | None = None,
    consume_slow: bool = True,
) -> tuple[SCMComposition, dict[str, Any], SCMConfig]:
    """Build the SCM preset: ``(composition, initial_state, cfg)`` (SPEC S09).

    ``ctx`` defaults to the embedded (debug) backend. ``fast_order`` and
    ``consume_slow`` are experiment/test knobs off the validated preset: a
    ``fast_order`` violating :data:`SCM_COUPLING_CONSTRAINTS` raises
    ``CouplingConstraintError`` at composition (acceptance 4), and
    ``consume_slow=False`` (the consumer removed) is rejected by the bus
    single-consumer check with ``BusError`` (acceptance 3) — experimental knobs
    never inherit the validated-preset label (architecture §4.2).
    """
    cfg = cfg if cfg is not None else SCMConfig()
    ctx = ctx if ctx is not None else ComputeContext(backend="embedded")
    order = tuple(fast_order) if fast_order is not None else SCM_FAST_ORDER

    grid = VerticalGrid.from_config(SleveConfig(num_levels=cfg.nlev))

    # -- fast suite: one instance per section name, constraints attached -----------
    sections_by_name: dict[str, Any] = {
        "satad": SaturationAdjustment(grid, cfg.satad, ctx, name="satad"),
        "mphys": Microphysics(grid, cfg.microphysics, ctx, scheme="graupel", name="mphys"),
    }
    for section_name, constraints in SCM_COUPLING_CONSTRAINTS.items():
        component = sections_by_name[section_name]
        # Preserve the class-declared admissible_operators (S07/S08 contracts).
        declared = constraints_of(component)
        assert constraints.admissible_operators == declared.admissible_operators
        component.coupling_constraints = constraints
    unknown = set(order) - set(sections_by_name)
    if unknown:
        raise ValueError(
            f"build_scm: fast_order names {sorted(unknown)} are not SCM sections "
            f"(known: {sorted(sections_by_name)})."
        )
    fast = SequentialUpdateSplitting(
        [sections_by_name[section_name] for section_name in order], name="scm_fast"
    )

    # -- slow suite + bus wiring ---------------------------------------------------
    cooling = CallingFrequency(PrescribedCooling(cfg.cooling, ctx), cfg.slow_timestep)
    slow = ConcurrentCoupling([cooling], name="scm_slow")
    core = ApplySlowTendencies(ctx=ctx, name="apply_slow")

    bus = SlowTendencyBus()
    bus.declare(TendencySlot(name=SLOW_TEMPERATURE_SLOT, units="K s-1", dims=("cell", "height")))
    # Published through the wrapper chain: constraint/bus matching must see the
    # CallingFrequency-wrapped publisher exactly as the composition holds it.
    bus.publish(cooling, SLOW_TEMPERATURE_SLOT)
    if consume_slow:
        bus.consume(core, SLOW_TEMPERATURE_SLOT)
    bus.check()

    composition = SCMComposition(
        slow=slow, cooling=cooling, core=core, fast=fast, bus=bus, order=order
    )
    return composition, _initial_column(cfg), cfg
