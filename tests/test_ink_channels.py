"""Tests for core/ink_channels.py — ink set registry and channel definitions."""
from __future__ import annotations

import pytest

from nup_imposer.core.ink_channels import (
    BUILTIN_INK_SETS,
    InkChannel,
    InkSet,
    InkSetRegistry,
    get_default_ink_registry,
)


# ---------------------------------------------------------------------------
# Registry basics
# ---------------------------------------------------------------------------

def test_builtin_count():
    """At least 8 built-in ink sets are defined."""
    assert len(BUILTIN_INK_SETS) >= 8


def test_registry_len():
    registry = get_default_ink_registry()
    assert len(registry) == len(BUILTIN_INK_SETS)


def test_find_by_id():
    registry = get_default_ink_registry()
    s = registry.find("epson_artisan_1400_6color")
    assert s is not None
    assert s.id == "epson_artisan_1400_6color"


def test_find_missing_returns_none():
    registry = get_default_ink_registry()
    assert registry.find("does_not_exist") is None


def test_all_returns_all():
    registry = get_default_ink_registry()
    ids = {s.id for s in registry.all()}
    assert len(ids) == len(BUILTIN_INK_SETS)


def test_workflows_present():
    registry = get_default_ink_registry()
    workflows = {s.workflow for s in registry.all()}
    assert "inkjet" in workflows
    assert "laser" in workflows
    assert "commercial" in workflows
    assert "sublimation" in workflows


def test_by_workflow_inkjet():
    registry = get_default_ink_registry()
    inkjet = registry.by_workflow("inkjet")
    assert len(inkjet) >= 4
    for s in inkjet:
        assert s.workflow == "inkjet"


def test_extended_only():
    registry = get_default_ink_registry()
    ext = registry.extended_only()
    for s in ext:
        assert s.n_channels > 4


# ---------------------------------------------------------------------------
# InkSet properties
# ---------------------------------------------------------------------------

def test_epson_artisan_6color_channels():
    registry = get_default_ink_registry()
    s = registry.find("epson_artisan_1400_6color")
    assert s is not None
    assert s.n_channels == 6
    abbrevs = s.channel_abbreviations
    assert "C" in abbrevs
    assert "LC" in abbrevs
    assert "LM" in abbrevs


def test_canon_pro9500_10color():
    registry = get_default_ink_registry()
    s = registry.find("canon_pro9500ii_10color")
    assert s is not None
    assert s.n_channels == 10


def test_epson_p900_10color():
    registry = get_default_ink_registry()
    s = registry.find("epson_p900_10color")
    assert s is not None
    assert s.n_channels == 10
    abbrevs = s.channel_abbreviations
    assert "LLK" in abbrevs
    assert "V" in abbrevs


def test_tac_limits_positive():
    """All TAC limits must be positive and reasonable."""
    for s in BUILTIN_INK_SETS:
        assert 100.0 < s.tac_limit <= 400.0, (
            f"{s.id} tac_limit {s.tac_limit} out of expected range"
        )


def test_light_ink_has_parent():
    """Every is_light channel must have a parent."""
    for s in BUILTIN_INK_SETS:
        for ch in s.channels:
            if ch.is_light:
                assert ch.parent is not None, (
                    f"{s.id} channel {ch.abbreviation} is_light but parent is None"
                )


def test_channel_indices_unique_and_sequential():
    """Channel indices within each ink set must be unique and 0-based sequential."""
    for s in BUILTIN_INK_SETS:
        indices = [ch.index for ch in s.channels]
        assert indices == list(range(s.n_channels)), (
            f"{s.id} channel indices not sequential: {indices}"
        )


def test_sublimation_has_conservative_tac():
    registry = get_default_ink_registry()
    sub = registry.find("sublimation_cmyk")
    assert sub is not None
    assert sub.tac_limit <= 240.0


def test_find_channel_method():
    registry = get_default_ink_registry()
    s = registry.find("epson_artisan_1400_6color")
    assert s is not None
    lc = s.find_channel("LC")
    assert lc is not None
    assert lc.is_light
    assert lc.parent == "C"


def test_is_extended_flag():
    registry = get_default_ink_registry()
    assert registry.find("epson_artisan_1400_6color").is_extended
    assert not registry.find("generic_laser").is_extended
    assert not registry.find("sublimation_cmyk").is_extended


def test_unique_ids():
    ids = [s.id for s in BUILTIN_INK_SETS]
    assert len(ids) == len(set(ids)), "Duplicate InkSet ids found"


def test_custom_registry():
    """A registry built with custom ink sets works independently."""
    custom = InkSet(
        id="test_custom",
        label="Test Custom",
        printer="Test Printer",
        channels=(
            InkChannel("Cyan", "C", 0),
            InkChannel("Magenta", "M", 1),
            InkChannel("Yellow", "Y", 2),
            InkChannel("Black", "K", 3),
        ),
        tac_limit=200.0,
        workflow="laser",
    )
    reg = InkSetRegistry([custom])
    assert len(reg) == 1
    assert reg.find("test_custom") is not None
    assert reg.find("epson_artisan_1400_6color") is None
