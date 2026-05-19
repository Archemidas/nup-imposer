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
]
