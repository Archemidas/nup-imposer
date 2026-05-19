"""Ink channel registry for multi-ink / RIP-ready output.

Defines InkChannel, InkSet, and the built-in printer/paper/ink registry used
for DeviceN TIFF export and TAC (Total Area Coverage) estimation.

Each InkSet describes:
  - The printer's ink channels (name, abbreviation, CMYK derivation).
  - The recommended TAC limit for the paper class (percentage, 0-400).
  - Workflow metadata matching the preset system (inkjet/laser/commercial/sublimation).

Light ink channels carry a `parent` abbreviation ('C', 'M', or 'K') and a
`split_at` threshold.  When channel_split() builds channel images from a CMYK
composite, values at or below split_at go to the light channel; values above
are scaled into the main channel.  This is a simplified model—real RIP ink
optimisation uses full ICC + GCR curves—but it gives accurate TAC estimates
and useful DeviceN TIFF previews for RIP ingestion.
"""
from __future__ import annotations

import dataclasses
from typing import Dict, List, Optional, Tuple


@dataclasses.dataclass(frozen=True)
class InkChannel:
    """One ink channel in a printer's ink set."""

    name: str           # Human-readable name, e.g. "Light Cyan"
    abbreviation: str   # Short code, e.g. "LC" – used in filenames and TIFF tags
    index: int          # Position in the channel array (0-based)
    is_light: bool = False          # True for Light Cyan, Light Magenta, etc.
    parent: Optional[str] = None    # Abbreviation of the main channel this splits from
    split_at: int = 128             # CMYK value (0-255) below which the light ink takes over


@dataclasses.dataclass(frozen=True)
class InkSet:
    """Printer ink set with channel definitions and paper limits."""

    id: str
    label: str
    printer: str
    channels: Tuple[InkChannel, ...]
    tac_limit: float     # max combined ink percentage (100% per channel, max 400%)
    workflow: str        # 'inkjet' | 'laser' | 'commercial' | 'sublimation'
    notes: str = ""

    @property
    def n_channels(self) -> int:
        return len(self.channels)

    @property
    def channel_names(self) -> List[str]:
        return [ch.name for ch in self.channels]

    @property
    def channel_abbreviations(self) -> List[str]:
        return [ch.abbreviation for ch in self.channels]

    @property
    def is_extended(self) -> bool:
        """True when the ink set has more than 4 channels (beyond plain CMYK)."""
        return self.n_channels > 4

    def find_channel(self, abbreviation: str) -> Optional[InkChannel]:
        for ch in self.channels:
            if ch.abbreviation == abbreviation:
                return ch
        return None


# ---------------------------------------------------------------------------
# Built-in ink sets
# ---------------------------------------------------------------------------

BUILTIN_INK_SETS: List[InkSet] = [

    # ------------------------------------------------------------------
    # 4-color CMYK / Laser
    # ------------------------------------------------------------------
    InkSet(
        id="cmyk_standard",
        label="Standard CMYK (4-color)",
        printer="Generic CMYK printer / any",
        channels=(
            InkChannel("Cyan", "C", 0),
            InkChannel("Magenta", "M", 1),
            InkChannel("Yellow", "Y", 2),
            InkChannel("Black", "K", 3),
        ),
        tac_limit=300.0,
        workflow="commercial",
        notes="Standard 4-color CMYK. TAC limit 300% is appropriate for coated offset stock.",
    ),

    InkSet(
        id="generic_laser",
        label="Generic color laser — CMYK toner",
        printer="Generic color laser / LED printer",
        channels=(
            InkChannel("Cyan", "C", 0),
            InkChannel("Magenta", "M", 1),
            InkChannel("Yellow", "Y", 2),
            InkChannel("Black", "K", 3),
        ),
        tac_limit=200.0,
        workflow="laser",
        notes="Conservative 200% TAC limit prevents toner cracking on plain paper.",
    ),

    # ------------------------------------------------------------------
    # 6-color inkjet: CMYK + Light Cyan + Light Magenta
    # ------------------------------------------------------------------
    InkSet(
        id="epson_artisan_1400_6color",
        label="Epson Artisan 1400/1430 — 6-color Claria",
        printer="Epson Artisan 1400 / Artisan 1430",
        channels=(
            InkChannel("Cyan",         "C",  0),
            InkChannel("Magenta",      "M",  1),
            InkChannel("Yellow",       "Y",  2),
            InkChannel("Black",        "K",  3),
            InkChannel("Light Cyan",   "LC", 4, is_light=True, parent="C", split_at=128),
            InkChannel("Light Magenta","LM", 5, is_light=True, parent="M", split_at=128),
        ),
        tac_limit=260.0,
        workflow="inkjet",
        notes=(
            "Epson Claria Hi-Definition 6-color dye ink. LC and LM handle mid-tone "
            "smooth gradients. TAC 260% for Premium Glossy / Semi-Gloss. Light ink split "
            "at 50% density threshold."
        ),
    ),

    # ------------------------------------------------------------------
    # 8-color Canon Pro-100: CMYK + Photo Black + Photo C/M + Gray
    # ------------------------------------------------------------------
    InkSet(
        id="canon_pro100_8color",
        label="Canon Pixma Pro-100 — 8-color ChromaLife100+",
        printer="Canon Pixma Pro-100",
        channels=(
            InkChannel("Cyan",         "C",   0),
            InkChannel("Magenta",      "M",   1),
            InkChannel("Yellow",       "Y",   2),
            InkChannel("Black",        "BK",  3),
            InkChannel("Photo Black",  "PBK", 4, is_light=True, parent="K", split_at=160),
            InkChannel("Photo Cyan",   "PC",  5, is_light=True, parent="C", split_at=128),
            InkChannel("Photo Magenta","PM",  6, is_light=True, parent="M", split_at=128),
            InkChannel("Gray",         "GY",  7, is_light=True, parent="K", split_at=64),
        ),
        tac_limit=280.0,
        workflow="inkjet",
        notes=(
            "Canon ChromaLife100+ 8-color dye ink. Photo Black replaces BK on glossy; "
            "Gray adds neutral shadow detail for smooth B&W. TAC 280% for Photo Paper "
            "Pro Platinum."
        ),
    ),

    # ------------------------------------------------------------------
    # 10-color Canon Pro9500 Mark II: CMYK + R/G/Gray + Photo C/M/PGY
    # ------------------------------------------------------------------
    InkSet(
        id="canon_pro9500ii_10color",
        label="Canon Pixma Pro9500 Mark II — 10-color Lucia",
        printer="Canon Pixma Pro9500 Mark II",
        channels=(
            InkChannel("Cyan",         "C",   0),
            InkChannel("Magenta",      "M",   1),
            InkChannel("Yellow",       "Y",   2),
            InkChannel("Photo Black",  "PBK", 3),
            InkChannel("Red",          "R",   4),
            InkChannel("Green",        "G",   5),
            InkChannel("Gray",         "GY",  6, is_light=True, parent="K", split_at=128),
            InkChannel("Photo Gray",   "PGY", 7, is_light=True, parent="K", split_at=64),
            InkChannel("Photo Cyan",   "PC",  8, is_light=True, parent="C", split_at=128),
            InkChannel("Photo Magenta","PM",  9, is_light=True, parent="M", split_at=128),
        ),
        tac_limit=260.0,
        workflow="inkjet",
        notes=(
            "Canon LUCIA 10-color pigment ink. Red and Green extend the wide-gamut. "
            "R and G are derived from saturated CMY combinations in this model. "
            "TAC 260% for Photo Paper Pro Platinum."
        ),
    ),

    # ------------------------------------------------------------------
    # 8-color Epson P800: CMYK + Light + dual Black
    # ------------------------------------------------------------------
    InkSet(
        id="epson_p800_8color",
        label="Epson SureColor P800 — 8-color UltraChrome HD",
        printer="Epson SureColor P800",
        channels=(
            InkChannel("Cyan",               "C",   0),
            InkChannel("Vivid Magenta",      "VM",  1),
            InkChannel("Yellow",             "Y",   2),
            InkChannel("Photo Black",        "PBK", 3),
            InkChannel("Matte Black",        "MBK", 4),
            InkChannel("Light Cyan",         "LC",  5, is_light=True, parent="C",  split_at=128),
            InkChannel("Vivid Light Magenta","VLM", 6, is_light=True, parent="VM", split_at=128),
            InkChannel("Light Black",        "LK",  7, is_light=True, parent="K",  split_at=128),
        ),
        tac_limit=240.0,
        workflow="inkjet",
        notes=(
            "Epson UltraChrome HD 8-color pigment. Photo Black for glossy/luster, "
            "Matte Black for fine-art matte. Light Black adds smooth neutral gradients. "
            "TAC 240% for Premium Luster."
        ),
    ),

    # ------------------------------------------------------------------
    # 10-color Epson P900: P800 + LLK + Violet
    # ------------------------------------------------------------------
    InkSet(
        id="epson_p900_10color",
        label="Epson SureColor P900 — 10-color UltraChrome PRO10",
        printer="Epson SureColor P900",
        channels=(
            InkChannel("Cyan",               "C",   0),
            InkChannel("Vivid Magenta",      "VM",  1),
            InkChannel("Yellow",             "Y",   2),
            InkChannel("Photo Black",        "PBK", 3),
            InkChannel("Matte Black",        "MBK", 4),
            InkChannel("Light Cyan",         "LC",  5, is_light=True, parent="C",  split_at=128),
            InkChannel("Vivid Light Magenta","VLM", 6, is_light=True, parent="VM", split_at=128),
            InkChannel("Light Black",        "LK",  7, is_light=True, parent="K",  split_at=128),
            InkChannel("Light Light Black",  "LLK", 8, is_light=True, parent="K",  split_at=64),
            InkChannel("Violet",             "V",   9),
        ),
        tac_limit=250.0,
        workflow="inkjet",
        notes=(
            "Epson UltraChrome PRO10 10-color pigment. Violet extends blues and purples. "
            "LLK gives ultra-smooth highlight neutrals. TAC 250% for Premium Luster."
        ),
    ),

    # ------------------------------------------------------------------
    # Commercial offset (CMYK SWOP v2)
    # ------------------------------------------------------------------
    InkSet(
        id="commercial_cmyk_swop",
        label="Commercial offset — CMYK SWOP v2",
        printer="Commercial sheetfed / web offset press",
        channels=(
            InkChannel("Cyan",    "C", 0),
            InkChannel("Magenta", "M", 1),
            InkChannel("Yellow",  "Y", 2),
            InkChannel("Black",   "K", 3),
        ),
        tac_limit=300.0,
        workflow="commercial",
        notes="SWOP v2 coated #5. TAC 300% for sheetfed coated; reduce to 260% for web offset on uncoated.",
    ),

    # ------------------------------------------------------------------
    # Sublimation inkjet (CMYK)
    # ------------------------------------------------------------------
    InkSet(
        id="sublimation_cmyk",
        label="Sublimation inkjet — CMYK transfer",
        printer="Sawgrass SG500/SG1000 / generic sublimation inkjet",
        channels=(
            InkChannel("Cyan",    "C", 0),
            InkChannel("Magenta", "M", 1),
            InkChannel("Yellow",  "Y", 2),
            InkChannel("Black",   "K", 3),
        ),
        tac_limit=220.0,
        workflow="sublimation",
        notes=(
            "Sublimation dye inks transfer to polyester via heat press. TAC limit 220% "
            "prevents ink bleeding and substrate saturation. Always enable mirror output "
            "so the image reads correctly after transfer."
        ),
    ),
]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class InkSetRegistry:
    """Lookup and filter ink sets by ID, workflow, or channel count."""

    def __init__(self, ink_sets: Optional[List[InkSet]] = None) -> None:
        sets = ink_sets if ink_sets is not None else BUILTIN_INK_SETS
        self._sets: Dict[str, InkSet] = {s.id: s for s in sets}

    def find(self, id: str) -> Optional[InkSet]:
        """Return the InkSet with the given id, or None."""
        return self._sets.get(id)

    def all(self) -> List[InkSet]:
        """Return all ink sets in insertion order."""
        return list(self._sets.values())

    def by_workflow(self, workflow: str) -> List[InkSet]:
        """Return ink sets matching the given workflow tag."""
        return [s for s in self._sets.values() if s.workflow == workflow]

    def extended_only(self) -> List[InkSet]:
        """Return ink sets with more than 4 channels."""
        return [s for s in self._sets.values() if s.is_extended]

    def __len__(self) -> int:
        return len(self._sets)

    def __iter__(self):
        return iter(self._sets.values())


def get_default_ink_registry() -> InkSetRegistry:
    """Return the default registry populated with all built-in ink sets."""
    return InkSetRegistry()
