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

Differentiability: ``differentiable: "native"`` (architecture §8.6) — since S10
the granule is paired with a JAX **functional core** co-located in this module
(:func:`_graupel_functional`, invoked through ``Graupel.functional_call``): a
line-by-line port of the granule's scan/flux programs (REFERENCES.lock
``icon4py-graupel-stencils``) sharing this scheme's constants module
(``graupel_constants.py``) so the two implementations cannot drift (§11.8).
Tunable scheme constants are exposed as the §8.6 ``params`` declaration
(``functional_params``): the Seifert-Beheng autoconversion/accretion kernel
coefficients and the ICON tuning-namelist knobs of :class:`GraupelConfig`;
coefficients the granule precomputes from them (``math.gamma`` expressions) are
re-derived *in-trace* via ``gammaln`` so ParamTree gradients flow through them.
jax imports stay inside the functional entry points — the component itself never
requires jax (the [jax] extra is optional).
"""

from __future__ import annotations

import dataclasses
import math
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
from symcon.icon.components.fast import graupel_constants as gconst
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
        "specific_rain_content": {
            "dims": _COLUMN_DIMS,
            "units": "1",
            "differentiable": "native",
            # §8.6 params declaration: the Seifert-Beheng autoconversion/accretion
            # kernel coefficients steer the cloud→rain path (values via
            # functional_params(); the S10 gradient example differentiates kcau).
            "params": ("kcau", "kcac"),
        },
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

    # -- the §8.6 functional core (S10) ---------------------------------------------

    def functional_params(self) -> dict[str, float]:
        """Tunable scheme constants exposed to the ParamTree (§8.6 ``params``).

        The Seifert-Beheng kernel coefficients (scheme constants, single source
        ``graupel_constants.py``) plus the ICON tuning-namelist knobs carried by
        :class:`GraupelConfig`; every granule coefficient derived from these is
        re-derived in-trace by the functional core, so their gradients are real.
        """
        return {
            "kcau": gconst.KCAU,
            "kcac": gconst.KCAC,
            "ice_stickeff_min": self.config.ice_stickeff_min,
            "snow2graupel_riming_coeff": self.config.snow2graupel_riming_coeff,
            "power_law_coeff_for_ice_mean_fall_speed": (
                self.config.power_law_coeff_for_ice_mean_fall_speed
            ),
            "exponent_for_density_factor_in_ice_sedimentation": (
                self.config.exponent_for_density_factor_in_ice_sedimentation
            ),
            "power_law_coeff_for_snow_fall_speed": (
                self.config.power_law_coeff_for_snow_fall_speed
            ),
            "rain_mu": self.config.rain_mu,
            "rain_n0": self.config.rain_n0,
        }

    def functional_call(
        self, inputs: Mapping[str, Any], params: Mapping[str, Any], *, dt: float
    ) -> dict[str, Any]:
        """Pure JAX evaluation of one graupel step (§8.6 ``native``; SPEC S10).

        Same boundary as :meth:`array_call`: contract-named inputs in, the flat
        union of outputs + diagnostics out (``x_new = x + dx/dt·Δt`` on the
        moist domain, surface precipitation rates from the ground-level fluxes).
        """
        return _graupel_functional(
            dt=dt,
            temperature=inputs["air_temperature"],
            pressure=inputs["air_pressure"],
            rho=inputs["air_density"],
            qv=inputs["specific_humidity"],
            qc=inputs["specific_cloud_content"],
            qi=inputs["specific_ice_content"],
            qr=inputs["specific_rain_content"],
            qs=inputs["specific_snow_content"],
            qg=inputs["specific_graupel_content"],
            qnc=inputs["icon:qnc"],
            dz=inputs["icon:ddqz_z_full"],
            params=params,
            config=self.config,
            kstart_moist=int(self._i4_vertical.kstart_moist),
        )


# --------------------------------------------------------------------------------------
# The JAX functional core (S10) — a line-by-line port of icon4py's graupel scan and
# flux programs (REFERENCES.lock ``icon4py-graupel-stencils``), drawing every number
# from graupel_constants.py / symcon.icon._constants (§11.8: shared scheme constants).
#
# Port discipline:
# - gt4py's per-element ``if``s become ``jnp.where``; every ``log``/division whose
#   argument can be non-positive in the *untaken* branch is double-where-guarded so
#   neither the primal nor the gradient sees a NaN (where-gradient rule, §8.6 notes).
# - Scalar-condition-and-value structure and floating-point operation *order* follow
#   the granule verbatim (acceptance 1: rtol ≤ 1e-10 against the gtfn kernel).
# - The granule's k_lev is RELATIVE to vertical_start = kstart_moist while
#   ``ground_level = num_levels - 1`` is ABSOLUTE; ``is_surface`` therefore only
#   fires when kstart_moist == 0 — replicated verbatim (quirk noted in STATUS S10).
# --------------------------------------------------------------------------------------

#: (0.5)^exponent model-top factors for the fixed ice/graupel fall-speed exponents
#: (the rain analogue depends on the tunable rain_mu and is derived in-trace).
_ICE_V_LN1O2: Final[float] = math.exp(
    gconst.POWER_LAW_EXPONENT_FOR_ICE_MEAN_FALL_SPEED * math.log(0.5)
)
_GRAUPEL_V_LN1O2: Final[float] = math.exp(
    gconst.POWER_LAW_EXPONENT_FOR_GRAUPEL_MEAN_FALL_SPEED * math.log(0.5)
)


def _graupel_functional(
    *,
    dt: float,
    temperature: Any,
    pressure: Any,
    rho: Any,
    qv: Any,
    qc: Any,
    qi: Any,
    qr: Any,
    qs: Any,
    qg: Any,
    qnc: Any,
    dz: Any,
    params: Mapping[str, Any],
    config: GraupelConfig,
    kstart_moist: int,
) -> dict[str, Any]:
    """One graupel step on (cell, height) arrays — pure, traced, fp64."""
    import jax
    import jax.numpy as jnp
    from jax.scipy.special import gammaln

    from symcon.icon._constants import ALS, ALV, CLW, RV, TMELT

    C = gconst
    qmin = C.GRAUPEL_QMIN

    def gamma(x: Any) -> Any:
        return jnp.exp(gammaln(x))

    def wlog(x: Any, mask: Any) -> Any:
        """log(x) where mask holds; a NaN-free constant elsewhere (double-where)."""
        return jnp.log(jnp.where(mask, x, 1.0))

    def wdiv(a: Any, b: Any, mask: Any) -> Any:
        """a/b where mask holds; NaN-free elsewhere (double-where)."""
        return a / jnp.where(mask, b, 1.0)

    # -- in-trace re-derivation of the granule's precomputed coefficients -------------
    mu = params["rain_mu"]
    rain_n0_factor = params["rain_n0"]
    v0s = params["power_law_coeff_for_snow_fall_speed"]
    vz0i = params["power_law_coeff_for_ice_mean_fall_speed"]
    icesedi_exp = params["exponent_for_density_factor_in_ice_sedimentation"]
    stickeff_min = params["ice_stickeff_min"]
    csg_coeff = params["snow2graupel_riming_coeff"]
    kcau = params["kcau"]
    kcac = params["kcac"]

    v1s = C.POWER_LAW_EXPONENT_FOR_SNOW_FALL_SPEED
    bms = C.POWER_LAW_EXPONENT_FOR_SNOW_MD_RELATION
    ams = C.POWER_LAW_COEFF_FOR_SNOW_MD_RELATION

    riming_coef = 0.25 * math.pi * C.SNOW_CLOUD_COLLECTION_EFF * v0s * gamma(v1s + 3.0)
    agg_coef = 0.25 * math.pi * v0s * gamma(v1s + 3.0)
    ccsvxp_m = -(v1s / (bms + 1.0) + 1.0)
    snow_sed_coef = ams * v0s * gamma(bms + v1s + 1.0) * (ams * gamma(bms + 1.0)) ** ccsvxp_m
    n0r = 8.0e6 * jnp.exp(3.2 * mu) * jnp.power(0.01, -mu)
    n0r = n0r * rain_n0_factor
    ar = math.pi * C.WATER_DENSITY / 6.0 * n0r * gamma(mu + 4.0)
    rain_v_exp = 0.5 / (mu + 4.0)
    rain_v_coeff = 130.0 * gamma(mu + 4.5) / gamma(mu + 4.0) * ar ** (-rain_v_exp)
    evap_alpha_exp = (mu + 2.0) / (mu + 4.0)
    evap_alpha_coeff = (
        2.0
        * math.pi
        * C.DIFFUSION_COEFF_FOR_WATER_VAPOR
        / C.HOWELL_FACTOR
        * n0r
        * ar ** (-evap_alpha_exp)
        * gamma(mu + 2.0)
    )
    evap_beta_exp = (2.0 * mu + 5.5) / (2.0 * mu + 8.0) - evap_alpha_exp
    evap_beta_coeff = (
        0.26
        * jnp.sqrt(C.REF_AIR_DENSITY * 130.0 / C.AIR_KINEMATIC_VISCOSITY)
        * ar ** (-evap_beta_exp)
        * gamma((2.0 * mu + 5.5) / 2.0)
        / gamma(mu + 2.0)
    )
    rain_v_ln1o2 = jnp.exp(rain_v_exp * jnp.log(0.5))

    nlev = int(temperature.shape[-1])
    ground_level = nlev - 1  # ABSOLUTE, vs the RELATIVE scan k (quirk, see header)
    use_const_lh = bool(config.use_constant_latent_heat)
    autoconv = int(config.liquid_autoconversion_option)
    intercept = int(config.snow_intercept_option)

    def sat_pres_water(t: Any) -> Any:
        return C.TETENS_P0 * jnp.exp(C.TETENS_AW * (t - TMELT) / (t - C.TETENS_BW))

    def sat_pres_ice(t: Any) -> Any:
        return C.TETENS_P0 * jnp.exp(C.TETENS_AI * (t - TMELT) / (t - C.TETENS_BI))

    def snow_intercept(t: Any, rho_k: Any, qs_k: Any, snow0: Any) -> tuple[Any, ...]:
        """compute_snow_interception_and_collision_parameters, ported."""
        if intercept == 1:  # FIELD_BEST_FIT_ESTIMATION
            tc = jnp.maximum(jnp.minimum(t - TMELT, 0.0), -40.0)
            n0s = C.SNOW_INTERCEPT_PARAMETER_N0S1 * jnp.exp(C.SNOW_INTERCEPT_PARAMETER_N0S2 * tc)
            n0s = jnp.maximum(jnp.minimum(n0s, 1.0e9), 1.0e6)
        elif intercept == 2:  # FIELD_GENERAL_MOMENT_ESTIMATION
            tc = jnp.maximum(jnp.minimum(t - TMELT, 0.0), -40.0)
            nnr = 3.0
            mma = C.SNOW_INTERCEPT_PARAMETER_MMA
            mmb = C.SNOW_INTERCEPT_PARAMETER_MMB
            hlp = (
                mma[0]
                + mma[1] * tc
                + mma[2] * nnr
                + mma[3] * tc * nnr
                + mma[4] * tc**2.0
                + mma[5] * nnr**2.0
                + mma[6] * tc**2.0 * nnr
                + mma[7] * tc * nnr**2.0
                + mma[8] * tc**3.0
                + mma[9] * nnr**3.0
            )
            alf = jnp.exp(hlp * math.log(10.0))
            bet = (
                mmb[0]
                + mmb[1] * tc
                + mmb[2] * nnr
                + mmb[3] * tc * nnr
                + mmb[4] * tc**2.0
                + mmb[5] * nnr**2.0
                + mmb[6] * tc**2.0 * nnr
                + mmb[7] * tc * nnr**2.0
                + mmb[8] * tc**3.0
                + mmb[9] * nnr**3.0
            )
            m2s = qs_k * rho_k / ams  # (UB: rho added as bugfix)
            m3s = alf * jnp.exp(bet * wlog(m2s, snow0))
            hlp = C.SNOW_INTERCEPT_PARAMETER_N0S1 * jnp.exp(C.SNOW_INTERCEPT_PARAMETER_N0S2 * tc)
            n0s = 13.50 * m2s * wdiv(m2s, m3s, snow0) ** 3.0
            n0s = jnp.maximum(n0s, 0.5 * hlp)
            n0s = jnp.minimum(n0s, 1.0e2 * hlp)
            n0s = jnp.minimum(n0s, 1.0e9)
            n0s = jnp.maximum(n0s, 1.0e6)
        else:
            n0s = jnp.full_like(t, C.SNOW_DEFAULT_INTERCEPT_PARAM)
        snow_sed0 = snow_sed_coef * jnp.exp(C.CCSVXP * jnp.log(n0s))
        crim = riming_coef * n0s
        cagg = agg_coef * n0s
        cbsdep = C.CCSDEP * jnp.sqrt(v0s)
        n0s = jnp.where(snow0, n0s, C.SNOW_DEFAULT_INTERCEPT_PARAM)
        snow_sed0 = jnp.where(snow0, snow_sed0, 0.0)
        crim = jnp.where(snow0, crim, 0.0)
        cagg = jnp.where(snow0, cagg, 0.0)
        cbsdep = jnp.where(snow0, cbsdep, 0.0)
        return n0s, snow_sed0, crim, cagg, cbsdep

    def body(carry: tuple[Any, ...], level: tuple[Any, ...]) -> tuple[tuple[Any, ...], Any]:
        (
            qv_t_kup,
            qc_t_kup,
            qi_t_kup,
            qr_t_kup,
            qs_t_kup,
            qg_t_kup,
            qv_old_kup,
            qc_old_kup,
            qi_old_kup,
            qr_old_kup,
            qs_old_kup,
            qg_old_kup,
            rhoqrv_old_kup,
            rhoqsv_old_kup,
            rhoqgv_old_kup,
            rhoqiv_old_kup,
            vnew_r,
            vnew_s,
            vnew_g,
            vnew_i,
            dist_cldtop_kup,
            rho_kup,
            crho1o2_kup,
            crhofac_qi_kup,
            snow_sed0_kup,
            qvsw_kup,
        ) = carry
        k, dz_k, t_k, p_k, rho_k, qv_k, qc_k, qi_k, qr_k, qs_k, qg_k = level

        # ---- Section 1: precomputed coefficients -------------------------------------
        qv_kup = qv_old_kup + qv_t_kup * dt
        qc_kup = qc_old_kup + qc_t_kup * dt
        qi_kup = qi_old_kup + qi_t_kup * dt
        qr_kup = qr_old_kup + qr_t_kup * dt
        qs_kup = qs_old_kup + qs_t_kup * dt
        qg_kup = qg_old_kup + qg_t_kup * dt

        is_surface = k == ground_level
        not_top = k > 0

        if use_const_lh:
            lhv: Any = ALV
            lhs: Any = ALS
        else:
            lhv = ALV + (C.CP_V - CLW) * (t_k - TMELT) - RV * t_k
            lhs = ALS + (C.CP_V - C.CPI) * (t_k - TMELT) - RV * t_k

        chlp = jnp.log(C.REF_AIR_DENSITY / rho_k)
        crho1o2 = jnp.exp(chlp / 2.0)
        crhofac_qi = jnp.exp(chlp * icesedi_exp)

        cdtdh = 0.5 * dt / dz_k
        cscmax = qc_k / dt
        cnin = jnp.minimum(5.0 * jnp.exp(0.304 * (TMELT - t_k)), C.NIMAX_THOM)
        cmi = jnp.minimum(rho_k * qi_k / cnin, C.ICE_MAX_MASS)
        cmi = jnp.maximum(C.ICE_INITIAL_MASS, cmi)

        qvsw = sat_pres_water(t_k) / (rho_k * RV * t_k)
        qvsi = sat_pres_ice(t_k) / (rho_k * RV * t_k)

        rhoqr = qr_k * rho_k
        rhoqs = qs_k * rho_k
        rhoqg = qg_k * rho_k
        rhoqi = qi_k * rho_k

        rhoqrv_new_kup = qr_kup * rho_kup * vnew_r
        rhoqsv_new_kup = qs_kup * rho_kup * vnew_s
        rhoqgv_new_kup = qg_kup * rho_kup * vnew_g
        rhoqiv_new_kup = qi_kup * rho_kup * vnew_i
        rhoqrv_new_kup = jnp.where(rhoqrv_new_kup <= qmin, 0.0, rhoqrv_new_kup)
        rhoqsv_new_kup = jnp.where(rhoqsv_new_kup <= qmin, 0.0, rhoqsv_new_kup)
        rhoqgv_new_kup = jnp.where(rhoqgv_new_kup <= qmin, 0.0, rhoqgv_new_kup)
        rhoqiv_new_kup = jnp.where(rhoqiv_new_kup <= qmin, 0.0, rhoqiv_new_kup)

        rhoqr_inter = rhoqr / cdtdh + rhoqrv_new_kup + rhoqrv_old_kup
        rhoqs_inter = rhoqs / cdtdh + rhoqsv_new_kup + rhoqsv_old_kup
        rhoqg_inter = rhoqg / cdtdh + rhoqgv_new_kup + rhoqgv_old_kup
        rhoqi_inter = rhoqi / cdtdh + rhoqiv_new_kup + rhoqiv_old_kup

        rain0 = rhoqr > qmin
        snow0 = rhoqs > qmin
        graupel0 = rhoqg > qmin
        ice0 = rhoqi > qmin

        n0s, snow_sed0, crim, cagg, cbsdep = snow_intercept(t_k, rho_k, qs_k, snow0)

        # ---- Section 2: sedimentation fluxes -----------------------------------------
        sum_s = qs_kup + qs_k
        sum_r = qr_kup + qr_k
        sum_g = qg_kup + qg_k
        sum_i = qi_kup + qi_k
        guard_s = not_top & (sum_s > qmin)
        guard_r = not_top & (sum_r > qmin)
        guard_g = not_top & (sum_g > qmin)
        guard_i = not_top & (sum_i > qmin)
        vnew_s = jnp.where(
            not_top,
            jnp.where(
                guard_s,
                snow_sed0_kup
                * jnp.exp(C.CCSWXP * wlog(sum_s * 0.5 * rho_kup, guard_s))
                * crho1o2_kup,
                0.0,
            ),
            vnew_s,
        )
        vnew_r = jnp.where(
            not_top,
            jnp.where(
                guard_r,
                rain_v_coeff
                * jnp.exp(rain_v_exp * wlog(sum_r * 0.5 * rho_kup, guard_r))
                * crho1o2_kup,
                0.0,
            ),
            vnew_r,
        )
        vnew_g = jnp.where(
            not_top,
            jnp.where(
                guard_g,
                C.POWER_LAW_COEFF_FOR_GRAUPEL_MEAN_FALL_SPEED
                * jnp.exp(
                    C.POWER_LAW_EXPONENT_FOR_GRAUPEL_MEAN_FALL_SPEED
                    * wlog(sum_g * 0.5 * rho_kup, guard_g)
                )
                * crho1o2_kup,
                0.0,
            ),
            vnew_g,
        )
        vnew_i = jnp.where(
            not_top,
            jnp.where(
                guard_i,
                vz0i
                * jnp.exp(
                    C.POWER_LAW_EXPONENT_FOR_ICE_MEAN_FALL_SPEED
                    * wlog(sum_i * 0.5 * rho_kup, guard_i)
                )
                * crhofac_qi_kup,
                0.0,
            ),
            vnew_i,
        )

        terminal_s = snow_sed0 * jnp.exp(C.CCSWXP * wlog(rhoqs, snow0)) * crho1o2
        terminal_s = jnp.where(
            is_surface, jnp.maximum(terminal_s, C.MINIMUM_SNOW_FALL_SPEED), terminal_s
        )
        rhoqsv = jnp.where(snow0, rhoqs * terminal_s, 0.0)
        vnew_s = jnp.where(snow0 & (vnew_s == 0.0), terminal_s * C.CCSWXP_LN1O2, vnew_s)

        terminal_r = rain_v_coeff * jnp.exp(rain_v_exp * wlog(rhoqr, rain0)) * crho1o2
        terminal_r = jnp.where(
            is_surface, jnp.maximum(terminal_r, C.MINIMUM_RAIN_FALL_SPEED), terminal_r
        )
        rhoqrv = jnp.where(rain0, rhoqr * terminal_r, 0.0)
        vnew_r = jnp.where(rain0 & (vnew_r == 0.0), terminal_r * rain_v_ln1o2, vnew_r)

        terminal_g = (
            C.POWER_LAW_COEFF_FOR_GRAUPEL_MEAN_FALL_SPEED
            * jnp.exp(C.POWER_LAW_EXPONENT_FOR_GRAUPEL_MEAN_FALL_SPEED * wlog(rhoqg, graupel0))
            * crho1o2
        )
        terminal_g = jnp.where(
            is_surface, jnp.maximum(terminal_g, C.MINIMUM_GRAUPEL_FALL_SPEED), terminal_g
        )
        rhoqgv = jnp.where(graupel0, rhoqg * terminal_g, 0.0)
        vnew_g = jnp.where(graupel0 & (vnew_g == 0.0), terminal_g * _GRAUPEL_V_LN1O2, vnew_g)

        terminal_i = (
            vz0i
            * jnp.exp(C.POWER_LAW_EXPONENT_FOR_ICE_MEAN_FALL_SPEED * wlog(rhoqi, ice0))
            * crhofac_qi
        )
        rhoqiv = jnp.where(ice0, rhoqi * terminal_i, 0.0)
        vnew_i = jnp.where(ice0 & (vnew_i == 0.0), terminal_i * _ICE_V_LN1O2, vnew_i)

        vnew_s = jnp.where(is_surface, jnp.maximum(vnew_s, C.MINIMUM_SNOW_FALL_SPEED), vnew_s)
        vnew_r = jnp.where(is_surface, jnp.maximum(vnew_r, C.MINIMUM_RAIN_FALL_SPEED), vnew_r)
        vnew_g = jnp.where(is_surface, jnp.maximum(vnew_g, C.MINIMUM_GRAUPEL_FALL_SPEED), vnew_g)

        rhoqrv = jnp.minimum(rhoqrv, rhoqr_inter)
        rhoqsv = jnp.minimum(rhoqsv, rhoqs_inter)
        rhoqgv = jnp.minimum(rhoqgv, jnp.maximum(0.0, rhoqg_inter))
        rhoqiv = jnp.minimum(rhoqiv, rhoqi_inter)

        rhoqr_inter = cdtdh * (rhoqr_inter - rhoqrv)
        rhoqs_inter = cdtdh * (rhoqs_inter - rhoqsv)
        rhoqg_inter = cdtdh * (rhoqg_inter - rhoqgv)
        rhoqi_inter = cdtdh * (rhoqi_inter - rhoqiv)

        cimr = 1.0 / (1.0 + vnew_r * cdtdh)
        cims = 1.0 / (1.0 + vnew_s * cdtdh)
        cimg = 1.0 / (1.0 + vnew_g * cdtdh)
        cimi = 1.0 / (1.0 + vnew_i * cdtdh)

        rhoqr = rhoqr_inter * cimr
        rhoqs = rhoqs_inter * cims
        rhoqg = rhoqg_inter * cimg

        # ---- Section 3: post-sedimentation coefficients -------------------------------
        rain = rhoqr > qmin
        snow = rhoqs > qmin
        graupel = rhoqg > qmin
        ice = qi_k > qmin
        cloud = qc_k > qmin

        clnrhoqr = wlog(rhoqr, rain)
        csrmax = jnp.where(rain, rhoqr_inter / rho_k / dt, 0.0)
        celn7o8qrk = jnp.where(rain & (qi_k + qc_k > qmin), jnp.exp(7.0 / 8.0 * clnrhoqr), 0.0)
        celn7o4qrk = jnp.where(
            rain & (t_k < C.THRESHOLD_FREEZE_TEMPERATURE), jnp.exp(7.0 / 4.0 * clnrhoqr), 0.0
        )
        celn13o8qrk = jnp.where(rain & ice, jnp.exp(13.0 / 8.0 * clnrhoqr), 0.0)

        clnrhoqs = wlog(rhoqs, snow)
        cssmax = jnp.where(snow, rhoqs_inter / rho_k / dt, 0.0)
        celn3o4qsk = jnp.where(snow & (qi_k + qc_k > qmin), jnp.exp(3.0 / 4.0 * clnrhoqs), 0.0)
        celn8qsk = jnp.where(snow, jnp.exp(0.8 * clnrhoqs), 0.0)

        clnrhoqg = wlog(rhoqg, graupel)
        csgmax = jnp.where(graupel, rhoqg_inter / rho_k / dt, 0.0)
        celnrimexp_g = jnp.where(
            graupel & (qi_k + qc_k > qmin), jnp.exp(C.GRAUPEL_RIMEXP * clnrhoqg), 0.0
        )
        celn6qgk = jnp.where(graupel, jnp.exp(0.6 * clnrhoqg), 0.0)

        isdep = ice | snow
        cdvtp = C.CCDVTP * jnp.exp(1.94 * jnp.log(t_k)) / p_k
        chi = C.CCSHI1 * cdvtp * rho_k * qvsi / (t_k * t_k)
        chlp2 = cdvtp / (1.0 + chi)
        cidep = jnp.where(isdep, C.CCIDEP * chlp2, 1.3e-5)
        cslam_arg = wdiv(C.CCSLAM * n0s, rhoqs, snow)
        cslam = jnp.where(
            isdep & snow,
            jnp.minimum(jnp.exp(C.CCSLXP * wlog(cslam_arg, isdep & snow)), 1.0e15),
            1.0e10,
        )
        csdep = jnp.where(isdep & snow, 4.0 * n0s * chlp2, 3.367e-2)

        # ---- Section 4: transfer rates -------------------------------------------------
        # deposition nucleation at low T or in clouds
        snuc = jnp.where(
            (cloud & (t_k <= 267.15) & (qi_k <= qmin))
            | (
                (t_k < C.HETEROGENEOUS_FREEZE_TEMPERATURE)
                & (qv_k > 8.0e-6)
                & (qi_k <= 0.0)
                & (qv_k > qvsi)
            ),
            C.ICE_INITIAL_MASS / rho_k * cnin / dt,
            0.0,
        )

        # autoconversion + rain accretion
        warm_cloud = cloud & (t_k > C.HOMOGENEOUS_FREEZE_TEMPERATURE)
        if autoconv == 0:  # Kessler (1969)
            scau = jnp.where(
                warm_cloud,
                C.KESSLER_CLOUD2RAIN_AUTOCONVERSION_COEFF_FOR_CLOUD
                * jnp.maximum(qc_k - C.QC0, 0.0),
                0.0,
            )
            scac = jnp.where(
                warm_cloud,
                C.KESSLER_CLOUD2RAIN_AUTOCONVERSION_COEFF_FOR_RAIN * qc_k * celn7o8qrk,
                0.0,
            )
        elif autoconv == 1:  # Seifert & Beheng (2001)
            sb_const = (
                kcau / (20.0 * C.XSTAR) * (C.CNUE + 2.0) * (C.CNUE + 4.0) / (C.CNUE + 1.0) ** 2.0
            )
            active = warm_cloud & (qc_k > 1.0e-6)
            tau = jnp.minimum(1.0 - wdiv(qc_k, qc_k + qr_k, active), 0.9)
            tau = jnp.maximum(tau, 1.0e-30)
            hlp = jnp.exp(C.KPHI2 * wlog(tau, active))
            phi = C.KPHI1 * hlp * (1.0 - hlp) ** 3.0
            scau = jnp.where(
                active,
                sb_const
                * qc_k
                * qc_k
                * qc_k
                * qc_k
                / (qnc * qnc)
                * (1.0 + phi / (1.0 - tau) ** 2.0),
                0.0,
            )
            phi2 = (tau / (tau + C.KPHI3)) ** 4.0
            scac = jnp.where(active, kcac * qc_k * qr_k * phi2, 0.0)
        else:
            scau = jnp.zeros_like(qc_k)
            scac = jnp.zeros_like(qc_k)

        # freezing in clouds
        cold_cloud = cloud & (t_k <= C.HOMOGENEOUS_FREEZE_TEMPERATURE)
        scfrz = jnp.where(cold_cloud, cscmax, 0.0)
        srfrz_clouds = jnp.where(
            warm_cloud & rain & (t_k < C.THRESHOLD_FREEZE_TEMPERATURE) & (qr_k > 0.1 * qc_k),
            C.COEFF_RAIN_FREEZE1
            * (jnp.exp(C.COEFF_RAIN_FREEZE2 * (C.THRESHOLD_FREEZE_TEMPERATURE - t_k)) - 1.0)
            * celn7o4qrk,
            jnp.where(cold_cloud, csrmax, 0.0),
        )

        # riming in clouds
        srim0 = jnp.where(warm_cloud & snow, crim * qc_k * jnp.exp(C.CCSAXP * jnp.log(cslam)), 0.0)
        grim0 = jnp.where(warm_cloud, C.CRIM_G * qc_k * celnrimexp_g, 0.0)
        melting_c = t_k >= TMELT
        shed = jnp.where(warm_cloud & melting_c, srim0 + grim0, 0.0)
        srim = jnp.where(warm_cloud & ~melting_c, srim0, 0.0)
        grim = jnp.where(warm_cloud & ~melting_c, grim0, 0.0)
        sconv = jnp.where(
            warm_cloud & ~melting_c & (qc_k >= C.QC0), csg_coeff * qc_k * celn3o4qsk, 0.0
        )

        # reduced deposition in clouds
        interior = not_top & ~is_surface
        cqcgk_1 = qi_kup + qs_kup + qg_kup
        dist_cldtop = jnp.where(
            cloud & interior,
            jnp.where((qv_kup + qc_kup < qvsw_kup) & (cqcgk_1 < qmin), 0.0, dist_cldtop_kup + dz_k),
            dist_cldtop_kup,
        )
        cnin2 = jnp.minimum(5.0 * jnp.exp(0.304 * (TMELT - t_k)), C.NIMAX_THOM)
        cfnuc = jnp.minimum(cnin2 / C.NIMIX, 1.0)
        reduce_dep = jnp.where(
            cloud & interior,
            jnp.minimum(
                cfnuc + (1.0 - cfnuc) * (C.REDUCE_DEP_REF + dist_cldtop / C.DIST_CLDTOP_REF),
                1.0,
            ),
            1.0,
        )

        # collision + ice deposition in cold ice clouds
        cold_ice = (t_k <= TMELT) & ice
        eff = jnp.maximum(jnp.minimum(jnp.exp(0.09 * (t_k - TMELT)), 1.0), stickeff_min)
        eff = jnp.maximum(eff, C.ICE_STICKING_EFF_FACTOR * (t_k - C.TMIN_ICEAUTOCONV))
        nid = rho_k * qi_k / cmi
        lnlogmi = jnp.log(cmi)
        qvsidiff = qv_k - qvsi
        svmax = qvsidiff / dt
        saggs = jnp.where(cold_ice, eff * qi_k * cagg * jnp.exp(C.CCSAXP * jnp.log(cslam)), 0.0)
        saggg = jnp.where(cold_ice, eff * qi_k * C.CAGG_G * celnrimexp_g, 0.0)
        siau = jnp.where(cold_ice, eff * C.CIAU * jnp.maximum(qi_k - C.QI0, 0.0), 0.0)
        sicri = jnp.where(cold_ice, C.CICRI * qi_k * celn7o8qrk, 0.0)
        srcri = jnp.where(cold_ice & (qs_k > 1.0e-7), C.CRCRI * (qi_k / cmi) * celn13o8qrk, 0.0)
        icetotaldep = cidep * nid * jnp.exp(0.33 * lnlogmi) * qvsidiff
        sidep = jnp.where(cold_ice, icetotaldep, 0.0)
        simax = rhoqi_inter / rho_k / dt
        reduced_dep_rate = icetotaldep * reduce_dep
        snet_dep = jnp.where(
            cold_ice & (icetotaldep > 0.0), jnp.minimum(reduced_dep_rate, svmax), 0.0
        )
        snet_sub0 = jnp.maximum(icetotaldep, svmax)
        snet_sub = jnp.where(cold_ice & (icetotaldep < 0.0), -jnp.maximum(snet_sub0, -simax), 0.0)
        lnlogmi2 = jnp.log(C.MSMIN / cmi)
        ztau = 1.5 * (jnp.exp(0.66 * lnlogmi2) - 1.0)
        sdau = jnp.where(cold_ice, snet_dep / ztau, 0.0)

        # snow/graupel depositional growth in cold ice clouds
        any_frozen = ice | snow | graupel
        cold_frozen = any_frozen & (t_k <= TMELT)
        xfac = 1.0 + cbsdep * jnp.exp(C.CCSDXP * jnp.log(cslam))
        ssdep_c = csdep * xfac * qvsidiff / (cslam + C_EPS) ** 2.0
        ssdep_c = jnp.where(ssdep_c > 0.0, ssdep_c * reduce_dep, ssdep_c)
        ssdep_c = jnp.where(ssdep_c > 0.0, jnp.minimum(ssdep_c, svmax - snet_dep), ssdep_c)
        ssdep_c = jnp.where(qs_k <= 1.0e-7, jnp.minimum(ssdep_c, 0.0), ssdep_c)
        ssdep_c = jnp.where(cold_frozen, ssdep_c, 0.0)
        sgdep_c = jnp.where(
            cold_frozen,
            (0.398561 - 0.00152398 * t_k + 2554.99 / p_k + 2.6531e-7 * p_k) * qvsidiff * celn6qgk,
            0.0,
        )

        # melting
        warm_frozen = any_frozen & (t_k > TMELT)
        simelt = jnp.where(warm_frozen, rhoqi_inter / rho_k / dt, 0.0)
        qvsw0 = C.PVSW0 / (rho_k * RV * TMELT)
        qvsw0diff = qv_k - qvsw0
        melt_active = warm_frozen & (t_k > TMELT - C.TCRIT * qvsw0diff)
        x1 = t_k - TMELT + C.ASMEL * qvsw0diff
        ssmelt0 = jnp.minimum((79.6863 / p_k + 0.612654e-3) * x1 * celn8qsk, cssmax)
        sgmelt0 = jnp.minimum((12.31698 / p_k + 7.39441e-05) * x1 * celn6qgk, csgmax)
        ssdep_m0 = (31282.3 / p_k + 0.241897) * qvsw0diff * celn8qsk
        sgdep_m0 = (0.153907 - p_k * 7.86703e-07) * qvsw0diff * celn6qgk
        subsat0 = qvsw0diff < 0.0
        ssdep_m_neg = jnp.maximum(-cssmax, ssdep_m0)
        sgdep_m_neg = jnp.maximum(-csgmax, sgdep_m0)
        ssmelt_neg = jnp.maximum(ssmelt0 + ssdep_m_neg, 0.0)
        sgmelt_neg = jnp.maximum(sgmelt0 + sgdep_m_neg, 0.0)
        # T below the melting-critical temperature: evaporation only
        qvswdiff = qv_k - qvsw
        ssdep_m_cold = jnp.maximum(-cssmax, (0.28003 - p_k * 0.146293e-6) * qvswdiff * celn8qsk)
        sgdep_m_cold = jnp.maximum(-csgmax, (0.0418521 - p_k * 4.7524e-8) * qvswdiff * celn6qgk)
        ssmelt = jnp.where(melt_active, jnp.where(subsat0, ssmelt_neg, ssmelt0), 0.0)
        sgmelt = jnp.where(melt_active, jnp.where(subsat0, sgmelt_neg, sgmelt0), 0.0)
        sconr = jnp.where(melt_active & ~subsat0, ssdep_m0 + sgdep_m0, 0.0)
        ssdep_m = jnp.where(
            warm_frozen,
            jnp.where(melt_active, jnp.where(subsat0, ssdep_m_neg, 0.0), ssdep_m_cold),
            0.0,
        )
        sgdep_m = jnp.where(
            warm_frozen,
            jnp.where(melt_active, jnp.where(subsat0, sgdep_m_neg, 0.0), sgdep_m_cold),
            0.0,
        )

        # rain evaporation + freezing in subsaturated air
        evap = rain & (qv_k + qc_k <= qvsw)
        lnqr = wlog(rhoqr, rain)
        x1e = 1.0 + evap_beta_coeff * jnp.exp(evap_beta_exp * lnqr)
        temp_c = t_k - TMELT
        maxevap = (0.61 - 0.0163 * temp_c + 1.111e-4 * temp_c**2.0) * (qvsw - qv_k) / dt
        sev = jnp.where(
            evap,
            jnp.minimum(
                evap_alpha_coeff * x1e * (qvsw - qv_k) * jnp.exp(evap_alpha_exp * lnqr),
                maxevap,
            ),
            0.0,
        )
        srfrz = jnp.where(
            evap
            & (t_k > C.HOMOGENEOUS_FREEZE_TEMPERATURE)
            & (t_k < C.THRESHOLD_FREEZE_TEMPERATURE),
            C.COEFF_RAIN_FREEZE1
            * (jnp.exp(C.COEFF_RAIN_FREEZE2 * (C.THRESHOLD_FREEZE_TEMPERATURE - t_k)) - 1.0)
            * celn7o4qrk,
            jnp.where(evap & (t_k <= C.HOMOGENEOUS_FREEZE_TEMPERATURE), csrmax, srfrz_clouds),
        )

        # ---- Section 5: negative-mass checks -------------------------------------------
        ssdep = ssdep_c + ssdep_m
        sgdep = sgdep_c + sgdep_m

        csum = scau + scac + srim + grim + shed
        denom = jnp.maximum(cscmax, csum)
        ccorr = wdiv(cscmax, denom, denom > 0.0)
        scau = jnp.where(warm_cloud, ccorr * scau, scau)
        scac = jnp.where(warm_cloud, ccorr * scac, scac)
        srim = jnp.where(warm_cloud, ccorr * srim, srim)
        grim = jnp.where(warm_cloud, ccorr * grim, grim)
        shed = jnp.where(warm_cloud, ccorr * shed, shed)
        sconv = jnp.where(warm_cloud, jnp.minimum(sconv, srim + cssmax), sconv)

        csimax = rhoqi_inter / rho_k / dt
        csum = siau + saggs + saggg + sicri + snet_sub
        denom = jnp.maximum(csimax, csum)
        ccorr = jnp.where(csimax > 0.0, wdiv(csimax, denom, denom > 0.0), 0.0)
        sidep = jnp.where(cold_frozen, snet_dep - ccorr * snet_sub, sidep)
        siau = jnp.where(cold_frozen, ccorr * siau, siau)
        saggs = jnp.where(cold_frozen, ccorr * saggs, saggs)
        saggg = jnp.where(cold_frozen, ccorr * saggg, saggg)
        sicri = jnp.where(cold_frozen, ccorr * sicri, sicri)
        ssdep = jnp.where(cold_frozen & (qvsidiff < 0.0), jnp.maximum(ssdep, -cssmax), ssdep)
        sgdep = jnp.where(cold_frozen & (qvsidiff < 0.0), jnp.maximum(sgdep, -csgmax), sgdep)

        csum = sev + srfrz + srcri
        denom = jnp.maximum(csrmax, csum)
        ccorr = jnp.where(csum > 0.0, wdiv(csrmax, denom, denom > 0.0), 1.0)
        sev = ccorr * sev
        srfrz = ccorr * srfrz
        srcri = ccorr * srcri

        neg_dep = ssdep <= 0.0
        csum = jnp.where(neg_dep, ssmelt + sconv - ssdep, ssmelt + sconv)
        denom = jnp.maximum(cssmax, csum)
        ccorr = jnp.where(csum > 0.0, wdiv(cssmax, denom, denom > 0.0), 1.0)
        ssmelt = ccorr * ssmelt
        sconv = ccorr * sconv
        ssdep = jnp.where(neg_dep, ccorr * ssdep, ssdep)

        # ---- Section 6: tendencies -------------------------------------------------------
        cqvt = sev - sidep - ssdep - sgdep - snuc - sconr
        cqct = simelt - scau - scfrz - scac - shed - srim - grim
        cqit = snuc + scfrz - simelt - sicri + sidep - sdau - saggs - saggg - siau
        cqrt = scau + shed + scac + ssmelt + sgmelt - sev - srcri - srfrz + sconr
        cqst = siau + sdau - ssmelt + srim + ssdep + saggs - sconv
        cqgt = saggg - sgmelt + sicri + srcri + sgdep + srfrz + grim + sconv

        t_tend = C.RCVD * (lhv * (cqct + cqrt) + lhs * (cqit + cqst + cqgt))
        qi_tend = jnp.maximum((rhoqi_inter / rho_k * cimi - qi_k) / dt + cqit * cimi, -qi_k / dt)
        qr_tend = jnp.maximum((rhoqr_inter / rho_k * cimr - qr_k) / dt + cqrt * cimr, -qr_k / dt)
        qs_tend = jnp.maximum((rhoqs_inter / rho_k * cims - qs_k) / dt + cqst * cims, -qs_k / dt)
        qg_tend = jnp.maximum((rhoqg_inter / rho_k * cimg - qg_k) / dt + cqgt * cimg, -qg_k / dt)
        qc_tend = jnp.maximum(cqct, -qc_k / dt)
        qv_tend = jnp.maximum(cqvt, -qv_k / dt)

        new_carry = (
            qv_tend,
            qc_tend,
            qi_tend,
            qr_tend,
            qs_tend,
            qg_tend,
            qv_k,
            qc_k,
            qi_k,
            qr_k,
            qs_k,
            qg_k,
            rhoqrv,
            rhoqsv,
            rhoqgv,
            rhoqiv,
            vnew_r,
            vnew_s,
            vnew_g,
            vnew_i,
            dist_cldtop,
            rho_k,
            crho1o2,
            crhofac_qi,
            snow_sed0,
            qvsw,
        )
        outputs = (
            t_tend,
            qv_tend,
            qc_tend,
            qi_tend,
            qr_tend,
            qs_tend,
            qg_tend,
            rhoqrv,
            rhoqsv,
            rhoqgv,
            rhoqiv,
            vnew_r,
            vnew_s,
            vnew_g,
            vnew_i,
        )
        return new_carry, outputs

    C_EPS = float(np.finfo(np.float64).eps)  # icon4py PhysicsConstants.eps (DBL_EPS)

    n_cell = temperature.shape[0]
    k0 = kstart_moist
    n_scan = nlev - k0

    def sliced(field: Any) -> Any:
        return jnp.moveaxis(field[:, k0:], -1, 0)  # (n_scan, cell) for lax.scan

    xs = (
        jnp.arange(n_scan),
        sliced(dz),
        sliced(temperature),
        sliced(pressure),
        sliced(rho),
        sliced(qv),
        sliced(qc),
        sliced(qi),
        sliced(qr),
        sliced(qs),
        sliced(qg),
    )
    zeros = jnp.zeros((n_cell,), dtype=jnp.result_type(temperature))
    carry0 = tuple(zeros for _ in range(26))
    _, ys = jax.lax.scan(body, carry0, xs)

    def full_levels(scan_field: Any) -> Any:
        column = jnp.moveaxis(scan_field, 0, -1)  # (cell, n_scan)
        if k0 == 0:
            return column
        pad = jnp.zeros((n_cell, k0), dtype=column.dtype)
        return jnp.concatenate([pad, column], axis=-1)

    (
        t_tend,
        qv_tend,
        qc_tend,
        qi_tend,
        qr_tend,
        qs_tend,
        qg_tend,
        rhoqrv_lev,
        rhoqsv_lev,
        rhoqgv_lev,
        rhoqiv_lev,
        vnew_r_lev,
        vnew_s_lev,
        vnew_g_lev,
        vnew_i_lev,
    ) = (full_levels(field) for field in ys)

    # icon_graupel_flux_at_ground (K domain [ground_level, nlev)): the surface
    # precipitation rate is the ground-level value of the flux field.
    def ground_rate(q: Any, q_tend: Any, rhoqv_old: Any, vnew: Any) -> Any:
        return 0.5 * ((q[:, -1] + q_tend[:, -1] * dt) * rho[:, -1] * vnew[:, -1] + rhoqv_old[:, -1])

    return {
        "air_temperature": temperature + t_tend * dt,
        "specific_humidity": qv + qv_tend * dt,
        "specific_cloud_content": qc + qc_tend * dt,
        "specific_ice_content": qi + qi_tend * dt,
        "specific_rain_content": qr + qr_tend * dt,
        "specific_snow_content": qs + qs_tend * dt,
        "specific_graupel_content": qg + qg_tend * dt,
        "icon:rain_gsp_rate": ground_rate(qr, qr_tend, rhoqrv_lev, vnew_r_lev),
        "icon:snow_gsp_rate": ground_rate(qs, qs_tend, rhoqsv_lev, vnew_s_lev),
        "icon:ice_gsp_rate": ground_rate(qi, qi_tend, rhoqiv_lev, vnew_i_lev),
        "icon:graupel_gsp_rate": ground_rate(qg, qg_tend, rhoqgv_lev, vnew_g_lev),
    }
