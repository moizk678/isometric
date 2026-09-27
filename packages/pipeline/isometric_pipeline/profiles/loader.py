"""Load versioned piping-isometric geometry profiles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

DEFAULT_PIPING_PROFILE_VERSION = "piping_isometric@1.0.0"

_REPO_ROOT = Path(__file__).resolve().parents[4]
_PROFILES_DIR = _REPO_ROOT / "profiles"


@dataclass(frozen=True)
class OcrProfile:
    model_id: str
    model_revision: str | None
    min_confidence: float
    conflict_margin: float
    crop_padding_px: int
    deskew_enabled: bool
    context_radius_px: float
    vocabulary_terms: tuple[str, ...]
    abbreviations: MappingProxyType[str, str]


@dataclass(frozen=True)
class AssemblyProfile:
    min_symbol_combined_score: float
    min_text_confidence: float
    default_layer_name: str


@dataclass(frozen=True)
class AssociationsProfile:
    max_witness_text_distance_px: float
    min_witness_length_px: float
    witness_max_gap_px: float
    max_witness_angle_from_axis_deg: float
    hough_threshold: int
    pipe_exclusion_buffer_px: float
    max_dimension_target_distance_px: float
    max_annotation_target_distance_px: float
    target_ambiguity_margin: float
    leader_max_steps: int
    leader_step_px: float
    arrow_alignment_tolerance_deg: float


@dataclass(frozen=True)
class SymbolsProfile:
    library_version: str
    classifier_backend: str
    allowed_symbol_ids: tuple[str, ...]
    min_shape_score: float
    min_context_score: float
    min_combined_margin: float
    port_attach_tolerance_px: float
    nearby_text_radius_px: float
    suppress_on_structural_junction: bool


@dataclass(frozen=True)
class TopologyProfile:
    endpoint_cluster_tolerance_px: float
    max_endpoint_angle_delta_deg: float
    intersection_proximity_px: float
    min_branch_angle_deg: float
    collinear_merge_max_gap_px: float
    collinear_angle_tolerance_deg: float
    ink_bridge_sample_step_px: float
    min_ink_bridge_coverage: float
    symbol_region_buffer_px: float
    min_hypothesis_margin: float
    elbow_angle_min_deg: float
    elbow_angle_max_deg: float


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
class TraceProfile:
    stroke_width_px: float
    simplify_epsilon_px: float
    min_polyline_length_px: float
    min_blob_area_px: int
    morph_open_kernel_px: int
    include_unclassified: bool
    max_paths_per_layer: int


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
    trace: TraceProfile
    snapping: SnappingProfile
    topology: TopologyProfile
    ocr: OcrProfile
    symbols: SymbolsProfile
    associations: AssociationsProfile
    assembly: AssemblyProfile


def _ocr_from_mapping(data: dict[str, object]) -> OcrProfile:
    terms_raw = data.get("vocabulary_terms", [])
    if not isinstance(terms_raw, list):
        raise ValueError("ocr.vocabulary_terms must be a list")
    abbrev_raw = data.get("abbreviations", {})
    if not isinstance(abbrev_raw, dict):
        raise ValueError("ocr.abbreviations must be a mapping")
    revision = data.get("model_revision")
    return OcrProfile(
        model_id=str(data["model_id"]),
        model_revision=str(revision) if revision is not None else None,
        min_confidence=float(data["min_confidence"]),
        conflict_margin=float(data["conflict_margin"]),
        crop_padding_px=int(data["crop_padding_px"]),
        deskew_enabled=bool(data["deskew_enabled"]),
        context_radius_px=float(data["context_radius_px"]),
        vocabulary_terms=tuple(str(t) for t in terms_raw),
        abbreviations=MappingProxyType({str(k): str(v) for k, v in abbrev_raw.items()}),
    )


def _assembly_from_mapping(data: dict[str, object]) -> AssemblyProfile:
    return AssemblyProfile(
        min_symbol_combined_score=float(data["min_symbol_combined_score"]),
        min_text_confidence=float(data["min_text_confidence"]),
        default_layer_name=str(data["default_layer_name"]),
    )


def _associations_from_mapping(data: dict[str, object]) -> AssociationsProfile:
    return AssociationsProfile(
        max_witness_text_distance_px=float(data["max_witness_text_distance_px"]),
        min_witness_length_px=float(data["min_witness_length_px"]),
        witness_max_gap_px=float(data["witness_max_gap_px"]),
        max_witness_angle_from_axis_deg=float(data["max_witness_angle_from_axis_deg"]),
        hough_threshold=int(data["hough_threshold"]),
        pipe_exclusion_buffer_px=float(data["pipe_exclusion_buffer_px"]),
        max_dimension_target_distance_px=float(
            data["max_dimension_target_distance_px"]
        ),
        max_annotation_target_distance_px=float(
            data["max_annotation_target_distance_px"]
        ),
        target_ambiguity_margin=float(data["target_ambiguity_margin"]),
        leader_max_steps=int(data["leader_max_steps"]),
        leader_step_px=float(data["leader_step_px"]),
        arrow_alignment_tolerance_deg=float(data["arrow_alignment_tolerance_deg"]),
    )


def _symbols_from_mapping(data: dict[str, object]) -> SymbolsProfile:
    allowed_raw = data.get("allowed_symbol_ids", [])
    if not isinstance(allowed_raw, list):
        raise ValueError("symbols.allowed_symbol_ids must be a list")
    return SymbolsProfile(
        library_version=str(data["library_version"]),
        classifier_backend=str(data["classifier_backend"]),
        allowed_symbol_ids=tuple(str(s) for s in allowed_raw),
        min_shape_score=float(data["min_shape_score"]),
        min_context_score=float(data["min_context_score"]),
        min_combined_margin=float(data["min_combined_margin"]),
        port_attach_tolerance_px=float(data["port_attach_tolerance_px"]),
        nearby_text_radius_px=float(data["nearby_text_radius_px"]),
        suppress_on_structural_junction=bool(data["suppress_on_structural_junction"]),
    )


def _topology_from_mapping(data: dict[str, object]) -> TopologyProfile:
    return TopologyProfile(
        endpoint_cluster_tolerance_px=float(data["endpoint_cluster_tolerance_px"]),
        max_endpoint_angle_delta_deg=float(data["max_endpoint_angle_delta_deg"]),
        intersection_proximity_px=float(data["intersection_proximity_px"]),
        min_branch_angle_deg=float(data["min_branch_angle_deg"]),
        collinear_merge_max_gap_px=float(data["collinear_merge_max_gap_px"]),
        collinear_angle_tolerance_deg=float(data["collinear_angle_tolerance_deg"]),
        ink_bridge_sample_step_px=float(data["ink_bridge_sample_step_px"]),
        min_ink_bridge_coverage=float(data["min_ink_bridge_coverage"]),
        symbol_region_buffer_px=float(data["symbol_region_buffer_px"]),
        min_hypothesis_margin=float(data["min_hypothesis_margin"]),
        elbow_angle_min_deg=float(data["elbow_angle_min_deg"]),
        elbow_angle_max_deg=float(data["elbow_angle_max_deg"]),
    )


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


def _trace_from_mapping(data: dict[str, object]) -> TraceProfile:
    return TraceProfile(
        stroke_width_px=float(data["stroke_width_px"]),
        simplify_epsilon_px=float(data["simplify_epsilon_px"]),
        min_polyline_length_px=float(data["min_polyline_length_px"]),
        min_blob_area_px=int(data["min_blob_area_px"]),
        morph_open_kernel_px=int(data["morph_open_kernel_px"]),
        include_unclassified=bool(data["include_unclassified"]),
        max_paths_per_layer=int(data.get("max_paths_per_layer", 50_000)),
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
    trace_raw = raw.get("trace")
    if not isinstance(trace_raw, dict):
        raise ValueError(f"profile trace section missing: {path}")
    snapping_raw = raw.get("snapping")
    if not isinstance(snapping_raw, dict):
        raise ValueError(f"profile snapping section missing: {path}")
    topology_raw = raw.get("topology")
    if not isinstance(topology_raw, dict):
        raise ValueError(f"profile topology section missing: {path}")
    ocr_raw = raw.get("ocr")
    if not isinstance(ocr_raw, dict):
        raise ValueError(f"profile ocr section missing: {path}")
    symbols_raw = raw.get("symbols")
    if not isinstance(symbols_raw, dict):
        raise ValueError(f"profile symbols section missing: {path}")
    associations_raw = raw.get("associations")
    if not isinstance(associations_raw, dict):
        raise ValueError(f"profile associations section missing: {path}")
    assembly_raw = raw.get("assembly")
    if not isinstance(assembly_raw, dict):
        raise ValueError(f"profile assembly section missing: {path}")
    return PipingIsometricProfile(
        version=version,
        geometry=_geometry_from_mapping(geometry_raw),
        trace=_trace_from_mapping(trace_raw),
        snapping=_snapping_from_mapping(snapping_raw),
        topology=_topology_from_mapping(topology_raw),
        ocr=_ocr_from_mapping(ocr_raw),
        symbols=_symbols_from_mapping(symbols_raw),
        associations=_associations_from_mapping(associations_raw),
        assembly=_assembly_from_mapping(assembly_raw),
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
    resolved = resolve_piping_profile_version(version)
    profile = _PROFILES.get(resolved)
    if profile is None:
        raise KeyError(f"unsupported piping profile version: {version}")
    return profile


def resolve_piping_profile_version(profile_id: str) -> str:
    """Map API ``profile_id`` (e.g. ``piping_isometric``) to a loaded profile version."""
    if profile_id in _PROFILES:
        return profile_id
    if "@" not in profile_id:
        versioned = f"{profile_id}@1.0.0"
        if versioned in _PROFILES:
            return versioned
    raise KeyError(f"unsupported piping profile version: {profile_id}")
