"""Core imposition logic."""
from .color import (
    ColorSettings,
    ProfileInfo,
    RenderingIntent,
    apply_transform,
    ensure_source_profile,
    list_installed_profiles,
    read_profile_info,
    soft_proof,
    srgb_profile,
    srgb_profile_bytes,
    system_profile_dirs,
)
from .exporters import export_pdf, export_tiff
from .image_loader import LoadedImage, load_image
from .imposition import ImpositionLayout, compute_layout
from .paper_sizes import PAPER_SIZES, PaperSize, get_paper_size
from .presets import (
    PrinterPreset,
    PresetRegistry,
    ResolvedPreset,
    get_default_registry,
    load_user_presets,
    resolve_profile_path,
)

__all__ = [
    # Imposition
    "PAPER_SIZES",
    "PaperSize",
    "get_paper_size",
    "ImpositionLayout",
    "compute_layout",
    # Loading
    "LoadedImage",
    "load_image",
    # Export
    "export_tiff",
    "export_pdf",
    # Color management
    "ColorSettings",
    "ProfileInfo",
    "RenderingIntent",
    "apply_transform",
    "soft_proof",
    "ensure_source_profile",
    "list_installed_profiles",
    "read_profile_info",
    "srgb_profile",
    "srgb_profile_bytes",
    "system_profile_dirs",
    # Presets
    "PrinterPreset",
    "PresetRegistry",
    "ResolvedPreset",
    "get_default_registry",
    "load_user_presets",
    "resolve_profile_path",
]


def apply_preset_to_settings(preset: "PrinterPreset", settings: "ColorSettings",
                             resolved_profile_path=None) -> "ColorSettings":
    """Apply a preset's recommended values to a ColorSettings instance.

    Mutates and returns the settings object. If `resolved_profile_path` is
    given (or the preset's filename candidates resolve on disk), the
    destination profile path is set; otherwise the previous destination is
    preserved so the user can still Browse manually.
    """
    settings.intent = preset.default_intent
    settings.black_point_compensation = preset.default_bpc
    settings.mirror_output = preset.mirror_output
    settings.preset_id = preset.id
    if resolved_profile_path is not None:
        settings.dest_profile_path = resolved_profile_path
        settings.dest_profile_bytes = None
    else:
        path = resolve_profile_path(preset.profile_filename_candidates)
        if path is not None:
            settings.dest_profile_path = path
            settings.dest_profile_bytes = None
        # else: leave dest_profile_path as it was
    return settings


__all__.append("apply_preset_to_settings")
