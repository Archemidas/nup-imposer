"""Printer preset registry.

Loads bundled presets (`presets_data.BUILTIN_PRESETS`) plus any user-added
JSON files in `~/.nup-imposer/presets/*.json`, resolves each preset's profile
filename hints against the user's installed ICC profiles, and exposes lookup
helpers for the GUI and CLI.

A preset always provides intent / BPC / mirror defaults even when no matching
ICC file is found on disk - users can still apply the workflow recommendations
and select a profile manually via Browse.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from .color import RenderingIntent, system_profile_dirs
from .presets_data import BUILTIN_PRESETS


VALID_WORKFLOWS = ("inkjet", "laser", "commercial", "sublimation")


@dataclass(frozen=True)
class PrinterPreset:
    """A printer + paper + ink combination with recommended settings."""

    id: str
    label: str
    printer: str
    paper: str
    ink_set: str
    profile_filename_candidates: tuple
    default_intent: RenderingIntent
    default_bpc: bool
    workflow: str
    mirror_output: bool
    notes: str = ""

    @property
    def is_sublimation(self) -> bool:
        return self.workflow == "sublimation"

    def __str__(self) -> str:
        return self.label


@dataclass
class ResolvedPreset:
    """A preset with its profile path resolved (if any) against installed profiles."""

    preset: PrinterPreset
    profile_path: Optional[Path] = None

    @property
    def has_profile(self) -> bool:
        return self.profile_path is not None and self.profile_path.exists()

    def __str__(self) -> str:
        suffix = "" if self.has_profile else "  [profile not found - use Browse]"
        return f"{self.preset.label}{suffix}"


def _preset_from_dict(d: dict) -> PrinterPreset:
    """Validate and construct a PrinterPreset from a JSON/dict entry."""
    required = {"id", "label", "printer", "paper", "ink_set",
                "profile_filename_candidates", "default_intent",
                "default_bpc", "workflow", "mirror_output"}
    missing = required - set(d.keys())
    if missing:
        raise ValueError(f"Preset {d.get('id', '?')} missing keys: {sorted(missing)}")
    workflow = d["workflow"]
    if workflow not in VALID_WORKFLOWS:
        raise ValueError(f"Preset {d['id']} has invalid workflow {workflow!r}; "
                         f"must be one of {VALID_WORKFLOWS}")
    intent_str = d["default_intent"]
    if isinstance(intent_str, RenderingIntent):
        intent = intent_str
    else:
        intent = RenderingIntent.from_label(str(intent_str))
    return PrinterPreset(
        id=d["id"],
        label=d["label"],
        printer=d["printer"],
        paper=d["paper"],
        ink_set=d["ink_set"],
        profile_filename_candidates=tuple(d["profile_filename_candidates"]),
        default_intent=intent,
        default_bpc=bool(d["default_bpc"]),
        workflow=workflow,
        mirror_output=bool(d["mirror_output"]),
        notes=str(d.get("notes", "")),
    )


def _user_preset_dir() -> Path:
    """Return the OS-appropriate user preset directory."""
    if sys.platform.startswith("win"):
        base = Path.home() / "AppData" / "Roaming" / "nup-imposer" / "presets"
    else:
        base = Path.home() / ".nup-imposer" / "presets"
    return base


def load_user_presets(directory: Optional[Path] = None) -> List[PrinterPreset]:
    """Load user-supplied presets from JSON files in the given directory.

    Each file may contain a single preset (dict) or a list of presets.
    Invalid entries are skipped silently (a real app would log them).
    """
    out: List[PrinterPreset] = []
    dir_ = directory or _user_preset_dir()
    if not dir_.is_dir():
        return out
    for json_file in sorted(dir_.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and "presets" in data:
            entries = data["presets"]
        elif isinstance(data, list):
            entries = data
        elif isinstance(data, dict):
            entries = [data]
        else:
            continue
        for entry in entries:
            try:
                out.append(_preset_from_dict(entry))
            except Exception:
                continue
    return out


class PresetRegistry:
    """Holds all known presets (bundled + user) with profile resolution."""

    def __init__(
        self,
        bundled: Optional[List[PrinterPreset]] = None,
        user: Optional[List[PrinterPreset]] = None,
    ):
        if bundled is None:
            bundled = [_preset_from_dict(p) for p in BUILTIN_PRESETS]
        self._presets: Dict[str, PrinterPreset] = {p.id: p for p in bundled}
        if user:
            for p in user:
                # User presets override bundled ones with the same id
                self._presets[p.id] = p

    def __len__(self) -> int:
        return len(self._presets)

    def __iter__(self):
        return iter(self._presets.values())

    def find(self, preset_id: str) -> Optional[PrinterPreset]:
        return self._presets.get(preset_id)

    def all(self) -> List[PrinterPreset]:
        return list(self._presets.values())

    def by_workflow(self, workflow: str) -> List[PrinterPreset]:
        return [p for p in self._presets.values() if p.workflow == workflow]

    def workflows(self) -> List[str]:
        seen = []
        for p in self._presets.values():
            if p.workflow not in seen:
                seen.append(p.workflow)
        return seen

    def resolve(self, preset: PrinterPreset) -> ResolvedPreset:
        """Try to find one of preset's profile filename candidates on disk."""
        path = resolve_profile_path(preset.profile_filename_candidates)
        return ResolvedPreset(preset=preset, profile_path=path)


@lru_cache(maxsize=1)
def _installed_profile_files() -> Dict[str, Path]:
    """Return a {filename: path} map of all .icc/.icm files in system dirs."""
    out: Dict[str, Path] = {}
    for d in system_profile_dirs():
        for path in d.rglob("*"):
            if path.suffix.lower() in (".icc", ".icm"):
                out.setdefault(path.name, path)
                # Also key by lowercase name for case-insensitive matching on Windows
                out.setdefault(path.name.lower(), path)
    return out


def resolve_profile_path(candidates) -> Optional[Path]:
    """Return the first candidate filename that exists on disk, or None."""
    installed = _installed_profile_files()
    for filename in candidates:
        if filename in installed:
            return installed[filename]
        # Case-insensitive fallback
        if filename.lower() in installed:
            return installed[filename.lower()]
    return None


def get_default_registry() -> PresetRegistry:
    """Build the standard registry: bundled + user presets."""
    return PresetRegistry(user=load_user_presets())
