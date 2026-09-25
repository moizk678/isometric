"""Load versioned piping-isometric geometry profiles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

DEFAULT_PIPING_PROFILE_VERSION = "piping_isometric@1.0.0"

_REPO_ROOT = Path(__file__).resolve().parents[4]
_PROFILES_DIR = _REPO_ROOT / "profiles"


@dataclass(frozen=True)
class SnappingProfile:
    max_snap_angle_deg: float
    min_axis_model_confidence: float
    min_primitive_length_px: float
    max_endpoint_displacement_px: float
    max_residual_after_snap_px: float
    endpoint_align_tolerance_px: float
    grid_confidence_min: float
    skip_dimension_region_overlap: bool
    dimension_overlap_fraction: float


@dataclass(frozen=True)
class GeometryProfile:
    min_component_pixels: int
    max_spur_length_px: int
    morph_open_kernel_px: int
    morph_close_kernel_px: int
    skeleton_prune_iterations: int
    max_line_fit_residual_px: float
    min_line_length_px: float
    min_r_squared: float
    max_chord_deviation_px: float
    max_turning_angle_deg: float
    stroke_width_percentile: float


@dataclass(frozen=True)
class PipingIsometricProfile:
    version: str
    geometry: GeometryProfile
    snapping: SnappingProfile


def _snapping_from_mapping(data: dict[str, object]) -> SnappingProfile:
    return SnappingProfile(
        max_snap_angle_deg=float(data["max_snap_angle_deg"]),
        min_axis_model_confidence=float(data["min_axis_model_confidence"]),
        min_primitive_length_px=float(data["min_primitive_length_px"]),
        max_endpoint_displacement_px=float(data["max_endpoint_displacement_px"]),
        max_residual_after_snap_px=float(data["max_residual_after_snap_px"]),
        endpoint_align_tolerance_px=float(data["endpoint_align_tolerance_px"]),
        grid_confidence_min=float(data["grid_confidence_min"]),
        skip_dimension_region_overlap=bool(data["skip_dimension_region_overlap"]),
        dimension_overlap_fraction=float(data["dimension_overlap_fraction"]),
    )


def _geometry_from_mapping(data: dict[str, object]) -> GeometryProfile:
    return GeometryProfile(
        min_component_pixels=int(data["min_component_pixels"]),
        max_spur_length_px=int(data["max_spur_length_px"]),
        morph_open_kernel_px=int(data["morph_open_kernel_px"]),
        morph_close_kernel_px=int(data["morph_close_kernel_px"]),
        skeleton_prune_iterations=int(data["skeleton_prune_iterations"]),
        max_line_fit_residual_px=float(data["max_line_fit_residual_px"]),
        min_line_length_px=float(data["min_line_length_px"]),
        min_r_squared=float(data["min_r_squared"]),
        max_chord_deviation_px=float(data["max_chord_deviation_px"]),
        max_turning_angle_deg=float(data["max_turning_angle_deg"]),
        stroke_width_percentile=float(data["stroke_width_percentile"]),
    )


def _load_yaml_profile(path: Path) -> PipingIsometricProfile:
    import yaml

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"profile must be a mapping: {path}")
    version = str(raw.get("version", ""))
    geometry_raw = raw.get("geometry")
    if not isinstance(geometry_raw, dict):
        raise ValueError(f"profile geometry section missing: {path}")
    snapping_raw = raw.get("snapping")
    if not isinstance(snapping_raw, dict):
        raise ValueError(f"profile snapping section missing: {path}")
    return PipingIsometricProfile(
        version=version,
        geometry=_geometry_from_mapping(geometry_raw),
        snapping=_snapping_from_mapping(snapping_raw),
    )


def _register_profiles() -> dict[str, PipingIsometricProfile]:
    profiles: dict[str, PipingIsometricProfile] = {}
    for path in sorted(_PROFILES_DIR.glob("piping_isometric@*.yaml")):
        profile = _load_yaml_profile(path)
        profiles[profile.version] = profile
    return profiles


_PROFILES = MappingProxyType(_register_profiles())


def load_piping_profile(version: str) -> PipingIsometricProfile:
    if not _PROFILES:
        raise RuntimeError(
            f"no piping profiles found under {_PROFILES_DIR}; expected piping_isometric@*.yaml"
        )
    profile = _PROFILES.get(version)
    if profile is None:
        raise KeyError(f"unsupported piping profile version: {version}")
    return profile
