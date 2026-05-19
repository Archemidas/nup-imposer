"""Tests for the printer preset registry."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nup_imposer.core import apply_preset_to_settings
from nup_imposer.core.color import ColorSettings, RenderingIntent
from nup_imposer.core.presets import (
    PresetRegistry,
    PrinterPreset,
    ResolvedPreset,
    _preset_from_dict,
    get_default_registry,
    load_user_presets,
    resolve_profile_path,
)
from nup_imposer.core.presets_data import BUILTIN_PRESETS


def test_builtin_presets_load():
    registry = PresetRegistry()
    assert len(registry) == len(BUILTIN_PRESETS)
    assert all(isinstance(p, PrinterPreset) for p in registry.all())


def test_default_registry_uses_builtins():
    registry = get_default_registry()
    assert len(registry) >= len(BUILTIN_PRESETS)


def test_find_by_id():
    registry = PresetRegistry()
    p = registry.find("sublimation_polyester")
    assert p is not None
    assert p.is_sublimation is True
    assert p.mirror_output is True


def test_find_missing_returns_none():
    registry = PresetRegistry()
    assert registry.find("not_a_real_preset") is None


def test_workflows_present():
    registry = PresetRegistry()
    workflows = set(registry.workflows())
    # At least these four should be in the bundled list
    assert {"inkjet", "laser", "sublimation"} <= workflows


def test_by_workflow_filters():
    registry = PresetRegistry()
    sub = registry.by_workflow("sublimation")
    assert len(sub) >= 3
    assert all(p.workflow == "sublimation" for p in sub)
    assert all(p.mirror_output for p in sub)


def test_inkjet_presets_have_intent():
    registry = PresetRegistry()
    for p in registry.by_workflow("inkjet"):
        assert isinstance(p.default_intent, RenderingIntent)
        assert p.default_bpc is True


def test_sublimation_presets_mirror():
    registry = PresetRegistry()
    for p in registry.by_workflow("sublimation"):
        assert p.mirror_output is True
        # Sublimation typically uses relative colorimetric
        assert p.default_intent == RenderingIntent.RELATIVE_COLORIMETRIC


def test_preset_from_dict_validates_required_keys():
    with pytest.raises(ValueError, match="missing keys"):
        _preset_from_dict({"id": "broken", "label": "x"})


def test_preset_from_dict_validates_workflow():
    bad = {
        "id": "bad_wf", "label": "x", "printer": "x", "paper": "x",
        "ink_set": "x", "profile_filename_candidates": [],
        "default_intent": "perceptual", "default_bpc": True,
        "workflow": "magical", "mirror_output": False,
    }
    with pytest.raises(ValueError, match="invalid workflow"):
        _preset_from_dict(bad)


def test_preset_from_dict_accepts_intent_strings():
    base = {
        "id": "t", "label": "T", "printer": "P", "paper": "P", "ink_set": "I",
        "profile_filename_candidates": [],
        "default_bpc": True, "workflow": "inkjet", "mirror_output": False,
    }
    for label, expected in (
        ("perceptual", RenderingIntent.PERCEPTUAL),
        ("relative", RenderingIntent.RELATIVE_COLORIMETRIC),
        ("Saturation", RenderingIntent.SATURATION),
        ("absolute", RenderingIntent.ABSOLUTE_COLORIMETRIC),
    ):
        preset = _preset_from_dict({**base, "default_intent": label})
        assert preset.default_intent is expected


def test_resolve_profile_path_returns_none_when_missing():
    out = resolve_profile_path(["definitely-not-a-real-icc-file-xyz.icc"])
    assert out is None


def test_user_presets_loaded_from_dir(tmp_path: Path):
    custom = {
        "id": "test_custom",
        "label": "Test Custom Preset",
        "printer": "Test Printer",
        "paper": "Test Paper",
        "ink_set": "Test Ink",
        "profile_filename_candidates": ["TestProfile.icc"],
        "default_intent": "perceptual",
        "default_bpc": False,
        "workflow": "inkjet",
        "mirror_output": False,
        "notes": "User-added test preset.",
    }
    (tmp_path / "test.json").write_text(json.dumps(custom))
    presets = load_user_presets(tmp_path)
    assert len(presets) == 1
    assert presets[0].id == "test_custom"


def test_user_presets_can_override_builtin(tmp_path: Path):
    """A user preset with the same id as a builtin should win."""
    override = {
        "id": "epson_artisan_1400_glossy",
        "label": "MY CUSTOM Epson 1400 Profile",
        "printer": "X", "paper": "X", "ink_set": "X",
        "profile_filename_candidates": [],
        "default_intent": "saturation",
        "default_bpc": False,
        "workflow": "inkjet",
        "mirror_output": False,
    }
    (tmp_path / "override.json").write_text(json.dumps(override))
    user_presets = load_user_presets(tmp_path)
    registry = PresetRegistry(user=user_presets)
    p = registry.find("epson_artisan_1400_glossy")
    assert p is not None
    assert p.label == "MY CUSTOM Epson 1400 Profile"
    assert p.default_intent is RenderingIntent.SATURATION


def test_apply_preset_to_settings_changes_intent_and_bpc():
    registry = PresetRegistry()
    preset = registry.find("epson_p800_hot_press_bright")
    assert preset is not None  # Sanity
    settings = ColorSettings()
    apply_preset_to_settings(preset, settings)
    assert settings.intent is preset.default_intent
    assert settings.black_point_compensation == preset.default_bpc
    assert settings.preset_id == preset.id


def test_apply_preset_to_settings_sublimation_sets_mirror():
    registry = PresetRegistry()
    preset = registry.find("sublimation_polyester")
    settings = ColorSettings()
    apply_preset_to_settings(preset, settings)
    assert settings.mirror_output is True
    assert settings.intent is RenderingIntent.RELATIVE_COLORIMETRIC


def test_apply_preset_to_settings_preserves_dest_when_unresolved():
    registry = PresetRegistry()
    preset = registry.find("sublimation_polyester")
    settings = ColorSettings(dest_profile_path=Path("/tmp/existing.icc"))
    apply_preset_to_settings(preset, settings)
    # Profile likely not found on disk, so previous dest is kept
    assert settings.dest_profile_path == Path("/tmp/existing.icc")


def test_resolved_preset_has_profile_flag():
    rp = ResolvedPreset(
        preset=PrinterPreset(
            id="t", label="T", printer="x", paper="x", ink_set="x",
            profile_filename_candidates=(), default_intent=RenderingIntent.PERCEPTUAL,
            default_bpc=True, workflow="inkjet", mirror_output=False,
        ),
        profile_path=None,
    )
    assert rp.has_profile is False


def test_preset_ids_are_unique():
    seen = set()
    for entry in BUILTIN_PRESETS:
        assert entry["id"] not in seen, f"Duplicate preset id: {entry['id']}"
        seen.add(entry["id"])
