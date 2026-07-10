"""``Microphysics(Stepper)`` — the icon4py graupel granule on symcon state (S08).

The scientific kernel is icon4py's single-moment six-class graupel granule
(``single_moment_six_class_gscp_graupel.py``, REFERENCES.lock id
``icon4py-graupel``), the gt4py port of ICON's ``gscp_graupel.f90`` (now at
``src/granules/microphysics_1mom_schemes/``, REFERENCES.lock id
``icon-fortran-graupel``). symcon does not re-plumb the granule's internals —
in particular the sedimentation/level-loop structure (one forward K-scan
carrying the ``rhoq{r,s,g,i}v_old_kup``/``vnew_*`` sedimentation state, plus
the two flux programs) stays exactly as the granule has it (SPEC S08 in-scope
clause): ``array_call`` builds zero-copy gt4py views of the boundary buffers
(:mod:`symcon.core.ingress.gt4py`) and invokes ``granule.run(...)`` exactly as
icon4py's own integration test does, then applies the returned tendencies over
the timestep — ``x_new = x + dx/dt·Δt`` is icon4py's own verification
arithmetic against the microphysics-exit savepoints.

Scheme selection (SPEC: "scheme selectable by registry name"): concrete schemes
subclass :class:`Microphysics` and register under their ``name`` class attribute
via the S02 :class:`~symcon.core.registry.Factory` machinery;
``Microphysics(grid, cfg, ctx, scheme="graupel")`` (the architecture-§4.3 usage)
and ``Microphysics.factory("graupel", ...)`` both resolve through that registry.
``"graupel"`` is the only registered scheme for now.

Coupling position (tutorial §3.7.2, REFERENCES.lock id ``icon-tutorial-2025``):
fast physics is time-split ("also known as sequential-update split");
microphysics sits between turbulent diffusion and the second saturation
adjustment in the NWP fast-physics sequence. Hence
``coupling_constraints.admissible_operators = {"sequential_update_splitting"}``.

Differentiability: ``differentiable: "native"`` is *declared* on the contract
now (architecture §8.6 — a shared-constants functional core is planned, not a
custom rule); the JAX core lands in S10.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from datetime import timedelta
from typing import Any, ClassVar, Final, cast

import numpy as np

from symcon.core.components.base import Stepper
from symcon.core.context import ComputeContext
from symcon.core.coupling.constraints import CouplingConstraints
from symcon.core.ingress.gt4py import Backend, resolve_backend
from symcon.core.registry import Factory
from symcon.core.typing import FieldBuffer
from symcon.icon import names as _names  # noqa: F401  (registry seed side effect)
from symcon.icon.components.fast._column_grid import column_icon4py_grid
from symcon.icon.grid.vertical import VerticalGrid

__all__ = ["Graupel", "GraupelConfig", "Microphysics"]

_COLUMN_DIMS: Final[tuple[str, str]] = ("cell", "height")
_SURFACE_DIMS: Final[tuple[str]] = ("cell",)

#: Default scheme name (the architecture-§4.3 preset: ``Microphysics(scheme="graupel")``).
_DEFAULT_SCHEME: Final[str] = "graupel"


@dataclasses.dataclass(frozen=True)
class GraupelConfig:
    """graupel configuration (mirrors icon4py ``SingleMomentSixClassIconGraupelConfig``).

    Field-for-field transcription of the icon4py v0.2.0 config (REFERENCES.lock
    ``icon4py-graupel``), whose defaults are the ICON namelist defaults; the two
    option enums are carried as their integer values so icon4py stays a lazy
    import (``LiquidAutoConversionType``/``SnowInterceptParameterization``).
    Options hardcoded to ``True`` in ICON (``lsedi_ice``/``lstickeff``/
    ``lred_depgrow``) are removed by icon4py and therefore absent here too.
    """

    #: Liquid autoconversion mode: 0 = Kessler (1969), 1 = Seifert & Beheng (2006).
    liquid_autoconversion_option: int = 1
    #: Snow intercept parameterization: 1/2 = Field et al. (2005) best-fit/general moment.
    snow_intercept_option: int = 2
    #: Do latent heat nudging (ICON ``dass_lhn``).
    do_latent_heat_nudging: bool = False
    #: Fixed latent heats for water (ICON ``ithermo_water == 0``).
    use_constant_latent_heat: bool = True
    #: Minimum sticking efficiency (ICON ``tune_zceff_min``).
    ice_stickeff_min: float = 0.075
    #: v-qi power-law coefficient for ice fall speed (ICON ``tune_zvz0i``).
    power_law_coeff_for_ice_mean_fall_speed: float = 1.25
    #: Density-factor exponent in ice sedimentation (ICON ``tune_icesedi_exp``).
    exponent_for_density_factor_in_ice_sedimentation: float = 0.33
    #: v-D power-law coefficient for snow fall speed (ICON ``tune_v0snow``).
    power_law_coeff_for_snow_fall_speed: float = 20.0
    #: mu exponent in the rain gamma size distribution (ICON ``mu_rain``).
    rain_mu: float = 0.0
    #: Rain intercept tuning factor (ICON ``rain_n0_factor``).
    rain_n0: float = 1.0
    #: Snow-to-graupel riming conversion coefficient (ICON ``tune_zcsg``).
    snow2graupel_riming_coeff: float = 0.5

    @classmethod
    def from_icon4py(cls, config: Any) -> GraupelConfig:
        """Transcribe an icon4py ``SingleMomentSixClassIconGraupelConfig``.

        Used by the L2 datatest to consume ``experiment.config.graupel`` (the
        namelist the serialized data was produced with) through the symcon
        component — the PLAN-pitfall path that pins the exact configuration.
        """
        # The option members are gtx.int32-based enums; a deep-copied config (the
        # icon4py ``Experiment.config`` accessor) degrades them to bare scalars.
        liquid = config.liquid_autoconversion_option
        intercept = config.snow_intercept_option
        return cls(
            liquid_autoconversion_option=int(getattr(liquid, "value", liquid)),
            snow_intercept_option=int(getattr(intercept, "value", intercept)),
            do_latent_heat_nudging=bool(config.do_latent_heat_nudging),
            use_constant_latent_heat=bool(config.use_constant_latent_heat),
            ice_stickeff_min=float(config.ice_stickeff_min),
            power_law_coeff_for_ice_mean_fall_speed=float(
                config.power_law_coeff_for_ice_mean_fall_speed
            ),
            exponent_for_density_factor_in_ice_sedimentation=float(
                config.exponent_for_density_factor_in_ice_sedimentation
            ),
            power_law_coeff_for_snow_fall_speed=float(config.power_law_coeff_for_snow_fall_speed),
            rain_mu=float(config.rain_mu),
            rain_n0=float(config.rain_n0),
            snow2graupel_riming_coeff=float(config.snow2graupel_riming_coeff),
        )

    def to_icon4py(self) -> Any:
        """The equivalent icon4py granule config (lazy icon4py import)."""
        from icon4py.model.atmosphere.subgrid_scale_physics.microphysics import (
            microphysics_options as mphys_options,
        )
        from icon4py.model.atmosphere.subgrid_scale_physics.microphysics import (
            single_moment_six_class_gscp_graupel as i4_graupel,
        )

        return i4_graupel.SingleMomentSixClassIconGraupelConfig(
            liquid_autoconversion_option=mphys_options.LiquidAutoConversionType(
                self.liquid_autoconversion_option
            ),
            snow_intercept_option=mphys_options.SnowInterceptParameterization(
                self.snow_intercept_option
            ),
            do_latent_heat_nudging=self.do_latent_heat_nudging,
            use_constant_latent_heat=self.use_constant_latent_heat,
            ice_stickeff_min=self.ice_stickeff_min,
            power_law_coeff_for_ice_mean_fall_speed=self.power_law_coeff_for_ice_mean_fall_speed,
            exponent_for_density_factor_in_ice_sedimentation=(
                self.exponent_for_density_factor_in_ice_sedimentation
            ),
            power_law_coeff_for_snow_fall_speed=self.power_law_coeff_for_snow_fall_speed,
            rain_mu=self.rain_mu,
            rain_n0=self.rain_n0,
            snow2graupel_riming_coeff=self.snow2graupel_riming_coeff,
        )


class Microphysics(Stepper, Factory):
    """Grid-scale microphysics on the column/grid state (SPEC S08).

    Registry root (S02 ``Factory``): concrete schemes subclass this and set the
    ``name`` class attribute; ``Microphysics(grid_or_column, cfg, ctx,
    scheme=<registry name>)`` dispatches construction to the registered scheme
    class (default ``"graupel"``), and ``Microphysics.factory(name, ...)`` is
    the explicit registry path. Constructing a concrete subclass directly
    (``Graupel(...)``) is equivalent.

    ``Microphysics(grid_or_column, cfg, ctx)`` — ``grid_or_column`` is either

    - a :class:`symcon.icon.grid.vertical.VerticalGrid` (**column path**): the
      horizontal extent is discovered from the state at the first call and a
      trivial pointwise icon4py grid is built around it; or
    - an ``(icon4py_grid, icon4py_vertical_grid)`` pair (**host-grid path**):
      the granule is hosted on an existing icon4py grid exactly as icon4py's
      own tests build it (the L2 datatest path).
    """

    def __new__(cls, *args: Any, scheme: str | None = None, **kwargs: Any) -> Microphysics:
        if cls is Microphysics:
            registry = cls.registry
            key = scheme if scheme is not None else _DEFAULT_SCHEME
            if key not in registry:
                raise KeyError(
                    f"no microphysics scheme registered under {key!r}; "
                    f"known names: {sorted(registry)}"
                )
            return super().__new__(cast("type[Microphysics]", registry[key]))
        if scheme is not None and scheme != getattr(cls, "name", None):
            raise ValueError(
                f"{cls.__name__} is the {getattr(cls, 'name', None)!r} scheme; "
                f"got scheme={scheme!r}. Construct via Microphysics(..., "
                f"scheme={scheme!r}) or the matching subclass."
            )
        return super().__new__(cls)


class Graupel(Microphysics):
    """The single-moment six-class graupel scheme (registry name ``"graupel"``).

    State names are the S06/S08 registry rows; the scheme steps T and the six
    moisture tracers, consumes p, rho, the layer thickness ``icon:ddqz_z_full``
    (the SPEC's "dz from VerticalGrid via static-state input" — the S06 column
    builders put it in the state; the datatest takes it from the metrics
    savepoint) and the cloud droplet number concentration ``icon:qnc``, and
    diagnoses the four grid-scale surface precipitation rates (ground-level
    values of the granule's precipitation-flux fields — icon4py's own
    verification arithmetic; ``icon:*_gsp_rate`` per ICON ``prm_nwp_diag``).

    Stepping happens on levels ``kstart_moist ≤ k < nlev`` (moist physics
    domain); above it the outputs equal the inputs and the tendencies are an
    exact zero.
    """

    name: ClassVar[str] = "graupel"

    input_properties: ClassVar[Mapping[str, Any]] = {
        "air_temperature": {"dims": _COLUMN_DIMS, "units": "K"},
        "air_pressure": {"dims": _COLUMN_DIMS, "units": "Pa"},
        "air_density": {"dims": _COLUMN_DIMS, "units": "kg m-3"},
        "specific_humidity": {"dims": _COLUMN_DIMS, "units": "1"},
        "specific_cloud_content": {"dims": _COLUMN_DIMS, "units": "1"},
        "specific_ice_content": {"dims": _COLUMN_DIMS, "units": "1"},
        "specific_rain_content": {"dims": _COLUMN_DIMS, "units": "1"},
        "specific_snow_content": {"dims": _COLUMN_DIMS, "units": "1"},
        "specific_graupel_content": {"dims": _COLUMN_DIMS, "units": "1"},
        "icon:qnc": {"dims": _SURFACE_DIMS, "units": "m-3"},
        "icon:ddqz_z_full": {"dims": _COLUMN_DIMS, "units": "m"},
    }
    output_properties: ClassVar[Mapping[str, Any]] = {
        "air_temperature": {"dims": _COLUMN_DIMS, "units": "K", "differentiable": "native"},
        "specific_humidity": {"dims": _COLUMN_DIMS, "units": "1", "differentiable": "native"},
        "specific_cloud_content": {
            "dims": _COLUMN_DIMS,
            "units": "1",
            "differentiable": "native",
        },
        "specific_ice_content": {"dims": _COLUMN_DIMS, "units": "1", "differentiable": "native"},
        "specific_rain_content": {"dims": _COLUMN_DIMS, "units": "1", "differentiable": "native"},
        "specific_snow_content": {"dims": _COLUMN_DIMS, "units": "1", "differentiable": "native"},
        "specific_graupel_content": {
            "dims": _COLUMN_DIMS,
            "units": "1",
            "differentiable": "native",
        },
    }
    diagnostic_properties: ClassVar[Mapping[str, Any]] = {
        "icon:rain_gsp_rate": {"dims": _SURFACE_DIMS, "units": "kg m-2 s-1"},
        "icon:snow_gsp_rate": {"dims": _SURFACE_DIMS, "units": "kg m-2 s-1"},
        "icon:ice_gsp_rate": {"dims": _SURFACE_DIMS, "units": "kg m-2 s-1"},
        "icon:graupel_gsp_rate": {"dims": _SURFACE_DIMS, "units": "kg m-2 s-1"},
    }

    #: tutorial §3.7.2: fast physics is sequential-update split; see module docstring.
    coupling_constraints: ClassVar[CouplingConstraints] = CouplingConstraints(
        admissible_operators=("sequential_update_splitting",)
    )

    def __init__(
        self,
        grid_or_column: VerticalGrid | tuple[Any, Any],
        cfg: GraupelConfig | None = None,
        ctx: ComputeContext | None = None,
        *,
        scheme: str | None = None,  # consumed/validated by Microphysics.__new__
        name: str | None = None,
    ) -> None:
        del scheme
        super().__init__(ctx=ctx, name=name)
        self.config = cfg if cfg is not None else GraupelConfig()
        self._backend: Backend = resolve_backend(self.ctx.backend)

        if isinstance(grid_or_column, VerticalGrid):
            self._vertical = grid_or_column
            # icon4py vertical-params adapter of the S06 grid (friend access within
            # symcon.icon; public exposure proposed in S07 STATUS.md).
            self._i4_vertical = grid_or_column._i4_grid
            self._i4_grid: Any | None = None  # built per horizontal extent, lazily
            self._nlev = grid_or_column.nlev
        else:
            i4_grid, i4_vertical = grid_or_column
            self._vertical = None
            self._i4_vertical = i4_vertical
            self._i4_grid = i4_grid
            self._nlev = int(i4_grid.num_levels)

        # granule + private metric/tendency fields, built once per horizontal extent.
        self._bound: dict[int, tuple[Any, Any, tuple[Any, ...]]] = {}

    # -- granule hosting ---------------------------------------------------------

    def _granule(self, n_cell: int) -> tuple[Any, Any, tuple[Any, ...]]:
        bound = self._bound.get(n_cell)
        if bound is None:
            from icon4py.model.atmosphere.subgrid_scale_physics.microphysics import (
                single_moment_six_class_gscp_graupel as i4_graupel,
            )
            from icon4py.model.common import dimension as i4_dims
            from icon4py.model.common.utils import data_allocation as data_alloc

            grid = self._i4_grid
            if grid is None:
                grid = column_icon4py_grid(n_cell, self._nlev)
            elif int(grid.num_cells) != n_cell:
                raise ValueError(
                    f"component {self.name!r}: state has {n_cell} cells but the "
                    f"hosting icon4py grid has {int(grid.num_cells)}."
                )
            gt4py_backend = self._backend.gt4py_backend

            def _cell_k_field(dtype: Any = np.float64) -> Any:
                return data_alloc.zero_field(
                    grid, i4_dims.CellDim, i4_dims.KDim, dtype=dtype, allocator=gt4py_backend
                )

            # dz is consumed by the scan; the state's icon:ddqz_z_full is copied
            # into this granule-owned field per call (T0 buffers are not
            # pointer-stable across calls, so aliasing it once would be unsound).
            metric_dz = _cell_k_field()
            granule = i4_graupel.SingleMomentSixClassIconGraupel(
                graupel_config=self.config.to_icon4py(),
                grid=grid,
                metric_state=i4_graupel.MetricStateIconGraupel(ddqz_z_full=metric_dz),
                vertical_params=self._i4_vertical,
                backend=gt4py_backend,
            )
            tendencies = tuple(_cell_k_field() for _ in range(7))
            bound = (granule, metric_dz, tendencies)
            self._bound[n_cell] = bound
        return bound

    # -- the ABI hook --------------------------------------------------------------

    def array_call(
        self,
        inputs: dict[str, FieldBuffer],
        outputs: dict[str, FieldBuffer],
        timestep: timedelta | None,
    ) -> None:
        assert timestep is not None  # Stepper: enforced by the base class
        temperature = inputs["air_temperature"]
        pressure = inputs["air_pressure"]
        rho = inputs["air_density"]
        tracers = {
            short: inputs[canonical]
            for short, canonical in (
                ("qv", "specific_humidity"),
                ("qc", "specific_cloud_content"),
                ("qi", "specific_ice_content"),
                ("qr", "specific_rain_content"),
                ("qs", "specific_snow_content"),
                ("qg", "specific_graupel_content"),
            )
        }
        qnc = inputs["icon:qnc"]
        dz = inputs["icon:ddqz_z_full"]

        n_cell, n_lev = temperature.shape
        if n_lev != self._nlev:
            raise ValueError(
                f"component {self.name!r}: state has {n_lev} levels but the "
                f"vertical grid has {self._nlev}."
            )
        granule, metric_dz, tendencies = self._granule(int(n_cell))
        t_tend, qv_tend, qc_tend, qi_tend, qr_tend, qs_tend, qg_tend = tendencies

        from icon4py.model.common import dimension as i4_dims

        dims = (i4_dims.CellDim, i4_dims.KDim)
        view = self._backend.as_field  # zero-copy §2.3 ingress (aliases the buffers)

        # dz into the granule-owned metric field (same device: both come off ctx).
        metric_dz.ndarray[...] = cast(Any, dz)

        # The granule writes tendencies only on the moist domain
        # [start_cell_nudging:end_cell_local, kstart_moist:nlev]; zero the private
        # fields per call so outside points carry an exact zero tendency, and zero
        # the precipitation-flux fields so repeat calls never read stale values.
        for tend in tendencies:
            tend.ndarray[...] = 0.0
        for flux in (
            granule.rain_precipitation_flux,
            granule.snow_precipitation_flux,
            granule.ice_precipitation_flux,
            granule.graupel_precipitation_flux,
            granule.total_precipitation_flux,
        ):
            flux.ndarray[...] = 0.0

        dtime = timestep.total_seconds()
        granule.run(
            dtime=dtime,
            rho=view(dims, rho),
            temperature=view(dims, temperature),
            pressure=view(dims, pressure),
            qv=view(dims, tracers["qv"]),
            qc=view(dims, tracers["qc"]),
            qr=view(dims, tracers["qr"]),
            qi=view(dims, tracers["qi"]),
            qs=view(dims, tracers["qs"]),
            qg=view(dims, tracers["qg"]),
            qnc=view((i4_dims.CellDim,), qnc),
            temperature_tendency=t_tend,
            qv_tendency=qv_tend,
            qc_tendency=qc_tend,
            qr_tendency=qr_tend,
            qi_tendency=qi_tend,
            qs_tendency=qs_tend,
            qg_tendency=qg_tend,
        )

        # icon4py's own verification arithmetic (their integration test):
        # x_exit = x_init + dx/dt * dtime, everywhere on the field.
        updates = (
            ("air_temperature", temperature, t_tend),
            ("specific_humidity", tracers["qv"], qv_tend),
            ("specific_cloud_content", tracers["qc"], qc_tend),
            ("specific_ice_content", tracers["qi"], qi_tend),
            ("specific_rain_content", tracers["qr"], qr_tend),
            ("specific_snow_content", tracers["qs"], qs_tend),
            ("specific_graupel_content", tracers["qg"], qg_tend),
        )
        for out_name, buffer, tend in updates:
            cast(Any, outputs[out_name])[...] = cast(Any, buffer) + tend.ndarray * dtime

        # Surface precipitation rates = ground-level values of the granule's
        # precipitation-flux fields (icon4py's test compares [:, -1] against the
        # exit savepoint's *_gsp_rate fields).
        rates = (
            ("icon:rain_gsp_rate", granule.rain_precipitation_flux),
            ("icon:snow_gsp_rate", granule.snow_precipitation_flux),
            ("icon:ice_gsp_rate", granule.ice_precipitation_flux),
            ("icon:graupel_gsp_rate", granule.graupel_precipitation_flux),
        )
        for out_name, flux in rates:
            cast(Any, outputs[out_name])[...] = flux.ndarray[:, -1]
