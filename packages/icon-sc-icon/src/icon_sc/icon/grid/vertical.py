"""ICON vertical grid (architecture §3.2, S06).

Everything a physics column needs from the vertical coordinate: the ``vct_a``/``vct_b``
table (ingested, or computed from the SLEVE namelist parameters), nominal interface and
full-level heights, the special level indices (flat / Rayleigh-damping / moist-physics),
and the ICON reference-atmosphere helpers.

Implementation policy (PLAN S06 item 1): *reuse* the pinned icon4py vertical-grid
machinery internally — ``icon4py.model.common.grid.vertical`` carries the ICON
``init_vert_coord`` algorithm and the namelist defaults — and adapt it behind the
frozen ``VerticalGrid(vct_a, vct_b, nlev)`` interface, whose surface speaks numpy, not
gt4py fields. The reference atmosphere is the decaying-isothermal profile of
``mo_vertical_grid.f90`` (identical formulas in icon4py
``metrics/reference_atmosphere.py``); the helpers here are array-namespace generic like
:mod:`icon_sc.icon.thermo`.

Coordinate convention (ICON): index 0 is the model top; ``vct_a`` is decreasing and has
``nlev + 1`` entries (interfaces / half levels).
"""

from __future__ import annotations

import dataclasses
from typing import Any

import array_api_compat
import numpy as np
import numpy.typing as npt

from icon_sc.icon._constants import (
    DEL_T_BG,
    GRAV,
    H_SCAL_BG,
    P0REF,
    P0SL_BG,
    RD,
    RD_O_CPD,
    T0SL_BG,
)

__all__ = [
    "SLEVEConfig",
    "VerticalGrid",
    "compute_vct_a_and_vct_b",
    "reference_exner",
    "reference_potential_temperature",
    "reference_pressure",
    "reference_rho",
    "reference_temperature",
]

#: Array-namespace-generic value (any array-API array: numpy, cupy, later JAX).
Array = Any

_F64 = npt.NDArray[np.float64]


@dataclasses.dataclass(frozen=True)
class SLEVEConfig:
    """SLEVE vertical-coordinate namelist parameters (ICON ``mo_sleve_nml`` /
    ``nonhydrostatic_nml``; defaults = icon4py v0.2.0 ``VerticalGridConfig`` = the ICON
    namelist defaults).

    Only the parameters governing the 1-d ``vct_a``/``vct_b`` table and the special
    level indices live here; the 3-d terrain-following SLEVE surfaces need topography
    and arrive with the metrics factory (lane B, S11).
    """

    #: Number of full levels (``num_lev``).
    num_levels: int
    #: ``min_lay_thckn``: thickness of the lowest layer [m] (<= 0.01 → uniform grid).
    lowest_layer_thickness: float = 50.0
    #: ``max_lay_thckn``: maximum layer thickness below ``htop_thcknlimit`` [m].
    maximal_layer_thickness: float = 25000.0
    #: ``htop_thcknlimit``: height below which the thickness limit applies [m].
    top_height_limit_for_maximal_layer_thickness: float = 15000.0
    #: ``top_height``: model top height [m].
    model_top_height: float = 23500.0
    #: ``flat_height``: height above which coordinate surfaces are flat [m].
    flat_height: float = 16000.0
    #: ``stretch_fac``: stretching factor of the layer distribution.
    stretch_factor: float = 1.0
    #: ``damp_height``: Rayleigh-damping start height for w [m] (nonhydrostatic_nml).
    rayleigh_damping_height: float = 45000.0
    #: ``htop_moist_proc``: height above which moist physics is switched off [m].
    htop_moist_proc: float = 22500.0
    # SLEVE decay parameters of the 3-d terrain-following surfaces (``mo_sleve_nml``;
    # consumed by the S11 metrics factory when topography is present; irrelevant over
    # flat terrain). Additive keyword extension declared in STATUS S11; defaults =
    # icon4py v0.2.0 ``VerticalGridConfig`` = the ICON namelist defaults.
    #: ``decay_scale_1``: decay scale of the large-scale topography component [m].
    decay_scale_1: float = 4000.0
    #: ``decay_scale_2``: decay scale of the small-scale topography component [m].
    decay_scale_2: float = 2500.0
    #: ``decay_exp``: exponent of the SLEVE decay function.
    decay_exponent: float = 1.2


def _icon4py_config(config: SLEVEConfig) -> Any:
    from icon4py.model.common.grid import vertical as _i4

    # icon4py annotates the namelist floats as wpfloat (np.float64); Python floats
    # are identical at runtime — donor-API typing friction only, hence the Any dict.
    kwargs: dict[str, Any] = {
        "num_levels": config.num_levels,
        "lowest_layer_thickness": config.lowest_layer_thickness,
        "maximal_layer_thickness": config.maximal_layer_thickness,
        "top_height_limit_for_maximal_layer_thickness": (
            config.top_height_limit_for_maximal_layer_thickness
        ),
        "model_top_height": config.model_top_height,
        "flat_height": config.flat_height,
        "stretch_factor": config.stretch_factor,
        "rayleigh_damping_height": config.rayleigh_damping_height,
        "htop_moist_proc": config.htop_moist_proc,
        "SLEVE_decay_scale_1": config.decay_scale_1,
        "SLEVE_decay_scale_2": config.decay_scale_2,
        "SLEVE_decay_exponent": config.decay_exponent,
    }
    return _i4.VerticalGridConfig(**kwargs)


def compute_vct_a_and_vct_b(config: SLEVEConfig) -> tuple[_F64, _F64]:
    """The analytic ICON vertical-coordinate table (SLEVE computation).

    Delegates to pinned icon4py ``get_vct_a_and_vct_b`` (the ``init_vert_coord``
    algorithm: ``vct_a[k] = H*(2/π·arccos((k/N)^s))^d`` with the lowest-layer-thickness
    exponent, thickness limiting and stretching; uniform grid when
    ``lowest_layer_thickness <= 0.01``; ``vct_b = exp(-vct_a/5000)``).

    Returns:
        ``(vct_a, vct_b)`` as numpy fp64 arrays of length ``num_levels + 1``, model
        top first.
    """
    from icon4py.model.common.grid import vertical as _i4

    # allocator=None → numpy allocation (icon4py accepts it at runtime).
    vct_a, vct_b = _i4.get_vct_a_and_vct_b(_icon4py_config(config), None)  # type: ignore[arg-type]
    return np.asarray(vct_a.asnumpy(), dtype=np.float64), np.asarray(
        vct_b.asnumpy(), dtype=np.float64
    )


class VerticalGrid:
    """The ICON vertical grid over one column stack (frozen interface, SPEC S06).

    ``VerticalGrid(vct_a, vct_b, nlev)`` ingests an existing coordinate table (e.g.
    from an icon4py grid savepoint); :meth:`from_config` computes the table from SLEVE
    namelist parameters. Internally adapts icon4py's ``VerticalGrid`` (index semantics
    are therefore identical to ICON's ``nflatlev``/``nrdmax``/``kstart_moist``).
    """

    def __init__(
        self,
        vct_a: npt.ArrayLike,
        vct_b: npt.ArrayLike | None,
        nlev: int,
        *,
        flat_height: float = 16000.0,
        rayleigh_damping_height: float = 45000.0,
        htop_moist_proc: float = 22500.0,
        config: SLEVEConfig | None = None,
    ) -> None:
        vct_a_arr = np.array(vct_a, dtype=np.float64)  # copy: table is frozen below
        if vct_a_arr.ndim != 1 or vct_a_arr.shape[0] != nlev + 1:
            raise ValueError(
                f"vct_a must be 1-d with nlev+1 = {nlev + 1} interface entries, "
                f"got shape {vct_a_arr.shape}."
            )
        if np.any(np.diff(vct_a_arr) >= 0.0):
            raise ValueError("vct_a must strictly decrease from model top to surface.")
        if vct_b is not None:
            vct_b_arr = np.array(vct_b, dtype=np.float64)
            if vct_b_arr.shape != vct_a_arr.shape:
                raise ValueError(
                    f"vct_b shape {vct_b_arr.shape} does not match vct_a {vct_a_arr.shape}."
                )
        else:
            vct_b_arr = None
        self._vct_a = vct_a_arr
        self._vct_b = vct_b_arr
        self._nlev = int(nlev)
        # ``config`` (additive keyword, declared in STATUS S11) carries the full SLEVE
        # namelist when an ingested table belongs to a known experiment configuration;
        # the metrics factory reads model_top_height / lowest_layer_thickness / decay
        # parameters off it. When given it wins over the three shortcut kwargs.
        if config is not None:
            if config.num_levels != self._nlev:
                raise ValueError(
                    f"config.num_levels={config.num_levels} does not match nlev={self._nlev}."
                )
            self._config = config
        else:
            self._config = SLEVEConfig(
                num_levels=self._nlev,
                flat_height=flat_height,
                rayleigh_damping_height=rayleigh_damping_height,
                htop_moist_proc=htop_moist_proc,
            )
        self._vct_a.setflags(write=False)
        if self._vct_b is not None:
            self._vct_b.setflags(write=False)
        self._i4_grid = self._build_icon4py_grid()

    def _build_icon4py_grid(self) -> Any:
        import gt4py.next as gtx
        from icon4py.model.common import dimension as dims
        from icon4py.model.common.grid import vertical as _i4

        return _i4.VerticalGrid(
            config=_icon4py_config(self._config),
            vct_a=gtx.as_field((dims.KDim,), self._vct_a),  # type: ignore[arg-type]
            vct_b=(
                gtx.as_field((dims.KDim,), self._vct_b)  # type: ignore[arg-type]
                if self._vct_b is not None
                else None
            ),
        )

    @classmethod
    def from_config(cls, config: SLEVEConfig) -> VerticalGrid:
        """Compute ``vct_a``/``vct_b`` from SLEVE parameters and build the grid."""
        vct_a, vct_b = compute_vct_a_and_vct_b(config)
        return cls(
            vct_a,
            vct_b,
            config.num_levels,
            flat_height=config.flat_height,
            rayleigh_damping_height=config.rayleigh_damping_height,
            htop_moist_proc=config.htop_moist_proc,
        )

    # --- sizes and level tables ------------------------------------------------------

    @property
    def nlev(self) -> int:
        """Number of full levels."""
        return self._nlev

    @property
    def num_interface_levels(self) -> int:
        """Number of interface (half) levels: ``nlev + 1``."""
        return self._nlev + 1

    @property
    def vct_a(self) -> _F64:
        """Vertical coordinate table A: nominal interface heights [m], top first."""
        return self._vct_a

    @property
    def vct_b(self) -> _F64 | None:
        """Vertical coordinate table B (w-profile merging table, ``mo_nh_init_utils``)."""
        return self._vct_b

    @property
    def interface_heights(self) -> _F64:
        """Nominal (flat-terrain) interface heights [m] — ``vct_a``."""
        return self._vct_a

    @property
    def full_level_heights(self) -> _F64:
        """Nominal full-level (mass-point) heights [m]: interface midpoints."""
        return 0.5 * (self._vct_a[:-1] + self._vct_a[1:])

    @property
    def layer_thickness(self) -> _F64:
        """Nominal layer thickness [m] (``ddqz_z_full`` over flat terrain)."""
        return self._vct_a[:-1] - self._vct_a[1:]

    @property
    def config(self) -> SLEVEConfig:
        """The SLEVE namelist parameters this grid was built with."""
        return self._config

    @property
    def icon4py_grid(self) -> Any:
        """The wrapped icon4py ``VerticalGrid`` (public accessor, declared S11).

        S07 flagged the ``_i4_grid`` friend access; the S11 metrics factory is the
        first out-of-module consumer, so the accessor becomes part of the surface.
        Lane-B wrappers hand this object to pinned icon4py machinery; ICON-sc-side
        code should keep using the numpy-speaking properties above.
        """
        return self._i4_grid

    # --- special level indices (ICON semantics via icon4py) --------------------------

    @property
    def nflatlev(self) -> int:
        """Bottom-most level index at which coordinate surfaces are flat."""
        return int(self._i4_grid.nflatlev)

    @property
    def nrdmax(self) -> int:
        """End index of the Rayleigh-damping layer for w (ICON ``nrdmax``)."""
        return int(self._i4_grid.end_index_of_damping_layer)

    @property
    def kstart_moist(self) -> int:
        """Start level of moist physics (interface midpoint < ``htop_moist_proc``)."""
        return int(self._i4_grid.kstart_moist)

    # --- reference state --------------------------------------------------------------

    def reference_profiles(self) -> dict[str, _F64]:
        """ICON reference-atmosphere profiles on nominal full levels.

        Keys are the registry names ``icon:exner_ref_mc`` / ``icon:theta_ref_mc`` /
        ``icon:rho_ref_mc`` (plain numpy arrays, not DataArrays — the static-state
        packaging is the metrics factory's job, S11).
        """
        z_mc = self.full_level_heights
        return {
            "icon:exner_ref_mc": reference_exner(z_mc),
            "icon:theta_ref_mc": reference_potential_temperature(z_mc),
            "icon:rho_ref_mc": reference_rho(z_mc),
        }

    def __repr__(self) -> str:
        return (
            f"VerticalGrid(nlev={self._nlev}, top={self._vct_a[0]:.1f} m, "
            f"nflatlev={self.nflatlev}, nrdmax={self.nrdmax}, "
            f"kstart_moist={self.kstart_moist})"
        )


# --- reference atmosphere (mo_vertical_grid.f90 ≡ icon4py reference_atmosphere.py) ---
#
# Decaying-isothermal profile: T(z) = (t0sl_bg - del_t_bg) + del_t_bg * exp(-z/h_scal_bg)
# integrated hydrostatically in closed form. Formulas transcribed from the reference;
# operation order follows the Fortran/icon4py cell-field variant so the cross-check in
# tests/test_icon4py_crosscheck.py holds to fp64 round-off.


def reference_temperature(z: Array) -> Array:
    """Reference temperature [K] at height ``z`` [m] — Fortran ``z_temp``."""
    xp = array_api_compat.array_namespace(z)
    return (T0SL_BG - DEL_T_BG) + DEL_T_BG * xp.exp(-z / H_SCAL_BG)


def reference_pressure(z: Array) -> Array:
    """Reference pressure [Pa] at height ``z`` [m] — Fortran ``z_aux1``."""
    xp = array_api_compat.array_namespace(z)
    denom = T0SL_BG - DEL_T_BG
    logval = xp.log((xp.exp(z / H_SCAL_BG) * denom + DEL_T_BG) / T0SL_BG)
    return P0SL_BG * xp.exp(-GRAV / RD * H_SCAL_BG / denom * logval)


def reference_exner(z: Array) -> Array:
    """Reference Exner function [1] at height ``z`` [m] — ``exner_ref_mc``."""
    return (reference_pressure(z) / P0REF) ** RD_O_CPD


def reference_potential_temperature(z: Array) -> Array:
    """Reference (virtual) potential temperature [K] — ``theta_ref_mc``.

    The ICON reference state is dry, so this doubles as the θv reference.
    """
    return reference_temperature(z) / reference_exner(z)


def reference_rho(z: Array) -> Array:
    """Reference density [kg m-3] at height ``z`` [m] — ``rho_ref_mc``."""
    return reference_pressure(z) / (RD * reference_temperature(z))
