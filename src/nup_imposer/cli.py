"""Command-line interface for headless imposition."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import apply_preset_to_settings
from .core.color import ColorSettings, RenderingIntent
from .core.exporters import export_pdf, export_tiff
from .core.image_loader import load_image
from .core.imposition import compute_layout
from .core.paper_sizes import PAPER_SIZES, custom_paper_size, get_paper_size
from .core.presets import get_default_registry
from .version import __version__


def _list_presets() -> int:
    registry = get_default_registry()
    by_workflow: dict = {}
    for p in registry.all():
        by_workflow.setdefault(p.workflow, []).append(p)

    print(f"Available presets ({len(registry)} total):\n")
    for workflow in ("inkjet", "laser", "commercial", "sublimation"):
        if workflow not in by_workflow:
            continue
        print(f"  [{workflow}]")
        for preset in by_workflow[workflow]:
            mirror_tag = "  (mirror)" if preset.mirror_output else ""
            print(f"    {preset.id:<40} {preset.label}{mirror_tag}")
        print()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="nup-imposer",
        description="N-up image imposition for print production.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--list-presets", action="store_true",
                        help="List all available printer presets and exit")
    parser.add_argument("input", nargs="?", help="Input image (JPG/PNG/TIFF/PSD/PDF)")
    parser.add_argument(
        "-n", "--copies", type=int,
        help="Number of copies to fit (2, 3, 4, 6, 8, 9, 10, 12, 16...)",
    )
    parser.add_argument(
        "-p", "--paper", default="Letter",
        help=f"Paper size. One of: {', '.join(PAPER_SIZES.keys())}, or use --paper-custom",
    )
    parser.add_argument(
        "--paper-custom", nargs=2, type=float, metavar=("WIDTH_IN", "HEIGHT_IN"),
        help="Custom paper size in inches (overrides --paper)",
    )
    parser.add_argument(
        "--orientation", choices=("auto", "portrait", "landscape"), default="auto",
        help="Paper orientation (default: auto-pick best fit)",
    )
    parser.add_argument(
        "-m", "--margin", type=float, default=0.25,
        help="Margin in inches (default: 0.25)",
    )
    parser.add_argument(
        "-g", "--gutter", type=float, default=0.125,
        help="Gutter between cells in inches (default: 0.125)",
    )
    parser.add_argument(
        "-d", "--dpi", type=int, default=300,
        help="Output DPI (default: 300)",
    )
    parser.add_argument(
        "-f", "--format", choices=("tiff", "pdf", "both"), default="tiff",
        help="Output format (default: tiff)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output path (without extension; defaults next to input)",
    )
    parser.add_argument(
        "--pdf-render-dpi", type=int, default=300,
        help="When input is PDF, render first page at this DPI (default: 300)",
    )

    # Color management
    color = parser.add_argument_group("color management")
    color.add_argument(
        "--dest-profile",
        help="Convert to this destination ICC profile (.icc/.icm) before saving",
    )
    color.add_argument(
        "--intent",
        choices=("perceptual", "relative", "saturation", "absolute"),
        default="perceptual",
        help="Rendering intent for the color transform (default: perceptual)",
    )
    color.add_argument(
        "--no-bpc", action="store_true",
        help="Disable black point compensation (BPC is on by default)",
    )

    # Presets / sublimation (phase 3)
    pres = parser.add_argument_group("presets")
    pres.add_argument(
        "--preset",
        help="Apply a printer preset by id (e.g. sublimation_polyester). "
             "Sets intent, BPC, destination profile, and mirror_output to the "
             "preset's defaults. Use --list-presets to see all options.",
    )
    pres.add_argument(
        "--mirror", action="store_true",
        help="Mirror the imposed sheet horizontally (sublimation transfer).",
    )
    pres.add_argument(
        "--no-mirror", action="store_true",
        help="Force mirror off even if --preset would enable it.",
    )

    args = parser.parse_args()

    if args.list_presets:
        return _list_presets()

    if not args.input or args.copies is None:
        parser.error("input and -n/--copies are required (use --list-presets to browse presets)")

    # Resolve paper
    if args.paper_custom:
        paper = custom_paper_size(args.paper_custom[0], args.paper_custom[1])
    else:
        paper = get_paper_size(args.paper)
        if paper is None:
            print(f"Unknown paper: {args.paper}", file=sys.stderr)
            print(f"Available: {', '.join(PAPER_SIZES.keys())}", file=sys.stderr)
            return 2

    # Resolve color settings
    settings = ColorSettings()
    settings.intent = RenderingIntent.from_label(args.intent)
    settings.black_point_compensation = not args.no_bpc

    # Apply preset first so explicit flags can override it
    if args.preset:
        registry = get_default_registry()
        preset = registry.find(args.preset)
        if preset is None:
            print(f"Unknown preset: {args.preset}", file=sys.stderr)
            print(f"Run with --list-presets to see all options.", file=sys.stderr)
            return 5
        apply_preset_to_settings(preset, settings)
        print(f"Applied preset: {preset.label}")
        if settings.dest_profile_path is None:
            print(f"  (profile not found on this system - use --dest-profile to override)")

    # Explicit --intent always wins over preset
    if "--intent" in sys.argv:
        settings.intent = RenderingIntent.from_label(args.intent)
    # Explicit --no-bpc wins
    if args.no_bpc:
        settings.black_point_compensation = False
    # Explicit --dest-profile wins
    if args.dest_profile:
        dest_path = Path(args.dest_profile)
        if not dest_path.exists():
            print(f"Destination ICC profile not found: {dest_path}", file=sys.stderr)
            return 4
        settings.dest_profile_path = dest_path
        settings.dest_profile_bytes = None
    # Mirror flags
    if args.mirror:
        settings.mirror_output = True
    if args.no_mirror:
        settings.mirror_output = False

    # Load image
    try:
        image = load_image(args.input, pdf_render_dpi=args.pdf_render_dpi)
    except Exception as e:
        print(f"Failed to load {args.input}: {e}", file=sys.stderr)
        return 3

    print(f"Loaded {image.source_format}: {image.width_px}x{image.height_px}px "
          f"@ {image.dpi_x:.0f} DPI ({image.width_in:.2f}x{image.height_in:.2f} in)")
    print(f"Color mode: {image.mode}, ICC embedded: {'yes' if image.icc_profile else 'no'}")
    if settings.has_destination():
        dest_name = (settings.dest_profile_path.name
                     if settings.dest_profile_path else "<embedded bytes>")
        print(f"Color transform: -> {dest_name} "
              f"({settings.intent.label}, BPC {'on' if settings.black_point_compensation else 'off'})")
    if settings.mirror_output:
        print("Mirror output: ON (horizontal flip for sublimation transfer)")

    # Compute layout
    orientation = None if args.orientation == "auto" else args.orientation
    layout = compute_layout(
        paper=paper,
        n=args.copies,
        source_aspect=image.aspect,
        margin_in=args.margin,
        gutter_in=args.gutter,
        paper_orientation=orientation,
    )
    print(f"Layout: {layout.rows}x{layout.cols} grid on {layout.paper.name} "
          f"({layout.paper.width_in:.2f}x{layout.paper.height_in:.2f} in), "
          f"cell {layout.cell_width_in:.2f}x{layout.cell_height_in:.2f} in"
          f"{', rotated' if layout.source_rotated else ''}")

    # Resolve output path
    in_path = Path(args.input)
    if args.output:
        out_base = Path(args.output)
    else:
        out_base = in_path.with_name(
            f"{in_path.stem}_{args.copies}up_{paper.name.split()[0].lower()}"
        )

    fmt = args.format
    if fmt in ("tiff", "both"):
        out_tiff = out_base.with_suffix(".tif")
        export_tiff(image, layout, out_tiff, output_dpi=args.dpi, color_settings=settings)
        print(f"Wrote TIFF: {out_tiff}")
    if fmt in ("pdf", "both"):
        out_pdf = out_base.with_suffix(".pdf")
        export_pdf(image, layout, out_pdf, output_dpi=args.dpi, color_settings=settings)
        print(f"Wrote PDF: {out_pdf}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
