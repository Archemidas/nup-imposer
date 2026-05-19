"""Bundled printer preset catalog.

Each entry maps a printer + paper + ink combo to:
- A list of profile filename candidates (best-effort hints; users can Browse)
- Manufacturer-recommended rendering intent and BPC default
- Workflow tag (inkjet / laser / sublimation)
- mirror_output flag (set True for sublimation transfer workflows)
- Notes shown in the GUI

Custom presets can be added by dropping a JSON file matching the same schema
into ~/.nup-imposer/presets/ (Windows: %USERPROFILE%\\.nup-imposer\\presets\\).
"""
from __future__ import annotations

BUILTIN_PRESETS: list[dict] = [
    # -------- Epson Artisan 1400 / 1430 (Claria Hi-Definition, 6-color CMYKLcLm)
    {
        "id": "epson_artisan_1400_glossy",
        "label": "Epson Artisan 1400/1430 - Premium Glossy",
        "printer": "Epson Artisan 1400 / 1430",
        "paper": "Premium Glossy Photo Paper",
        "ink_set": "Claria Hi-Definition (6-color CMYKLcLm)",
        "profile_filename_candidates": [
            "EPSON Stylus Photo 1400 Premium Glossy Photo Paper.icc",
            "Artisan 1430 Premium Glossy Photo Paper.icc",
            "Artisan_1400_PGPP.icc",
            "EPSON_1400_PGPP.icc",
        ],
        "default_intent": "perceptual",
        "default_bpc": True,
        "workflow": "inkjet",
        "mirror_output": False,
        "notes": "Set driver paper type to Premium Glossy. 1440 DPI works well; 5760 DPI for finest detail.",
    },
    {
        "id": "epson_artisan_1400_semigloss",
        "label": "Epson Artisan 1400/1430 - Premium Semi-Gloss",
        "printer": "Epson Artisan 1400 / 1430",
        "paper": "Premium Semi-Gloss Photo Paper",
        "ink_set": "Claria Hi-Definition (6-color CMYKLcLm)",
        "profile_filename_candidates": [
            "EPSON Stylus Photo 1400 Premium Semigloss Photo Paper.icc",
            "Artisan 1430 Premium Semigloss Photo Paper.icc",
            "Artisan_1400_PSGPP.icc",
        ],
        "default_intent": "perceptual",
        "default_bpc": True,
        "workflow": "inkjet",
        "mirror_output": False,
        "notes": "Pearl-like surface, slightly less reflective than glossy. Good for portraits.",
    },
    {
        "id": "epson_artisan_1400_velvet_fineart",
        "label": "Epson Artisan 1400/1430 - Velvet Fine Art",
        "printer": "Epson Artisan 1400 / 1430",
        "paper": "Velvet Fine Art Paper",
        "ink_set": "Claria Hi-Definition (6-color CMYKLcLm)",
        "profile_filename_candidates": [
            "EPSON Stylus Photo 1400 Velvet Fine Art Paper.icc",
            "Artisan 1430 Velvet Fine Art Paper.icc",
            "Artisan_1400_Velvet.icc",
        ],
        "default_intent": "relative",
        "default_bpc": True,
        "workflow": "inkjet",
        "mirror_output": False,
        "notes": "Matte fine-art paper. Use Relative Colorimetric for accurate proofing.",
    },

    # -------- Canon Pixma Pro9500 Mark II (Lucia pigment, 10-color)
    {
        "id": "canon_pro9500_pt",
        "label": "Canon Pro9500 Mark II - Photo Paper Pro Platinum",
        "printer": "Canon Pixma Pro9500 Mark II",
        "paper": "Photo Paper Pro Platinum (PT-101)",
        "ink_set": "Lucia pigment (10-color: CMYK, PC, PM, R, G, GY, PGY)",
        "profile_filename_candidates": [
            "Canon Pro9500 II PR1.icc",
            "Canon PIXMA Pro9500 II PT.icc",
            "CNB PR9500II PT1 1.icc",
            "Canon Pro9500II_PT.icc",
        ],
        "default_intent": "perceptual",
        "default_bpc": True,
        "workflow": "inkjet",
        "mirror_output": False,
        "notes": "Wide-gamut pigment inks. Pro Platinum gives the deepest blacks on this printer.",
    },
    {
        "id": "canon_pro9500_premium_matte",
        "label": "Canon Pro9500 Mark II - Premium Matte",
        "printer": "Canon Pixma Pro9500 Mark II",
        "paper": "Premium Matte Paper (MP-101)",
        "ink_set": "Lucia pigment (10-color)",
        "profile_filename_candidates": [
            "Canon Pro9500 II MP1.icc",
            "Canon PIXMA Pro9500 II MP.icc",
            "Canon Pro9500II_PremMatte.icc",
        ],
        "default_intent": "relative",
        "default_bpc": True,
        "workflow": "inkjet",
        "mirror_output": False,
        "notes": "Switches automatically to matte black ink. Use Relative Colorimetric for fine-art accuracy.",
    },
    {
        "id": "canon_pro9500_luster",
        "label": "Canon Pro9500 Mark II - Photo Paper Pro Luster",
        "printer": "Canon Pixma Pro9500 Mark II",
        "paper": "Photo Paper Pro Luster (LU-101)",
        "ink_set": "Lucia pigment (10-color)",
        "profile_filename_candidates": [
            "Canon Pro9500 II LU1.icc",
            "Canon PIXMA Pro9500 II LU.icc",
        ],
        "default_intent": "perceptual",
        "default_bpc": True,
        "workflow": "inkjet",
        "mirror_output": False,
        "notes": "Slight texture, low glare. Popular for gallery prints.",
    },

    # -------- Canon Pixma Pro-100 (ChromaLife100+ dye, 8-color)
    {
        "id": "canon_pro100_pt",
        "label": "Canon Pixma Pro-100 - Photo Paper Pro Platinum",
        "printer": "Canon Pixma Pro-100",
        "paper": "Photo Paper Pro Platinum (PT-101)",
        "ink_set": "ChromaLife100+ dye (8-color: CMY, BK, GY, LGY, PC, PM)",
        "profile_filename_candidates": [
            "Canon Pro-100 PT.icc",
            "Canon PIXMA Pro-100 PT.icc",
            "Pro100_PT_PP.icc",
        ],
        "default_intent": "perceptual",
        "default_bpc": True,
        "workflow": "inkjet",
        "mirror_output": False,
        "notes": "Dye-based, very wide gamut. Excellent for vivid photos.",
    },

    # -------- Epson SureColor P800 / P900 (UltraChrome HD/HDX, 9-10 color pigment)
    {
        "id": "epson_p900_luster",
        "label": "Epson SureColor P900 - Premium Luster",
        "printer": "Epson SureColor P900",
        "paper": "Premium Luster Photo Paper (250)",
        "ink_set": "UltraChrome HD pigment (10-color)",
        "profile_filename_candidates": [
            "SCP900 Premium Luster Photo Paper 250.icc",
            "SC-P900 PLPP250.icc",
            "Epson P900 LusterPro.icc",
        ],
        "default_intent": "perceptual",
        "default_bpc": True,
        "workflow": "inkjet",
        "mirror_output": False,
        "notes": "Pro-grade pigment printer. Use 1440 DPI minimum for the full gamut.",
    },
    {
        "id": "epson_p800_hot_press_bright",
        "label": "Epson SureColor P800/P900 - Hot Press Bright",
        "printer": "Epson SureColor P800 / P900",
        "paper": "Hot Press Bright (Epson fine art)",
        "ink_set": "UltraChrome HD pigment (9/10-color)",
        "profile_filename_candidates": [
            "SCP800 Hot Press Bright.icc",
            "Epson P900 HotPressBright.icc",
            "SCP_HotPressBright.icc",
        ],
        "default_intent": "relative",
        "default_bpc": True,
        "workflow": "inkjet",
        "mirror_output": False,
        "notes": "Matte fine art. Auto-switches to matte black. Relative Colorimetric for proofing.",
    },

    # -------- Generic / commercial workflows
    {
        "id": "generic_color_laser",
        "label": "Generic Color Laser (sRGB)",
        "printer": "Any color laser",
        "paper": "Plain or coated paper",
        "ink_set": "CMYK toner (typically 4-color)",
        "profile_filename_candidates": [
            "sRGB Color Space Profile.icm",
            "sRGB IEC61966-2.1.icc",
        ],
        "default_intent": "perceptual",
        "default_bpc": True,
        "workflow": "laser",
        "mirror_output": False,
        "notes": "Most office color lasers accept sRGB and convert internally. Leave color management to the driver if unsure.",
    },
    {
        "id": "commercial_cmyk_swop",
        "label": "Commercial CMYK (SWOP v2)",
        "printer": "Offset / commercial press",
        "paper": "Coated #5 (SWOP standard)",
        "ink_set": "CMYK process",
        "profile_filename_candidates": [
            "USWebCoatedSWOP.icc",
            "U.S. Web Coated (SWOP) v2.icc",
            "SWOP2006_Coated5v2.icc",
        ],
        "default_intent": "relative",
        "default_bpc": True,
        "workflow": "commercial",
        "mirror_output": False,
        "notes": "Standard for U.S. commercial offset printing. Use Relative Colorimetric for contract proofs.",
    },

    # -------- Sublimation workflows
    {
        "id": "sublimation_polyester",
        "label": "Sublimation - Polyester fabric",
        "printer": "Sublimation-converted inkjet (Epson EcoTank, Sawgrass SG500/SG1000, etc.)",
        "paper": "Sublimation transfer paper",
        "ink_set": "Sublimation ink (SubliJet, Cosmos, generic)",
        "profile_filename_candidates": [
            "SubliJet_Polyester.icc",
            "Sublimation_Polyester_Generic.icc",
            "Sub_Polyester.icc",
            "Sawgrass_Power_Driver_Polyester.icc",
        ],
        "default_intent": "relative",
        "default_bpc": True,
        "workflow": "sublimation",
        "mirror_output": True,
        "notes": "Output is mirrored for heat-press transfer. Source the ICC from your ink/paper vendor (Sawgrass PowerDriver, Cosmos, etc.). Press temp/time per substrate spec.",
    },
    {
        "id": "sublimation_hard_substrate",
        "label": "Sublimation - Hard substrate (mug/tile/metal)",
        "printer": "Sublimation-converted inkjet",
        "paper": "Sublimation transfer paper",
        "ink_set": "Sublimation ink",
        "profile_filename_candidates": [
            "Sublimation_HardSubstrate.icc",
            "SubliJet_Mug.icc",
            "Sub_Tile.icc",
        ],
        "default_intent": "relative",
        "default_bpc": True,
        "workflow": "sublimation",
        "mirror_output": True,
        "notes": "Mirror enabled. Use vendor profile for the specific coating (ChromaLuxe metal, ceramic mug, etc.). 400 F for ~60-90s typical.",
    },
    {
        "id": "sublimation_photo_panel",
        "label": "Sublimation - Photo panel (ChromaLuxe / metal)",
        "printer": "Sublimation-converted inkjet",
        "paper": "Sublimation transfer paper",
        "ink_set": "Sublimation ink",
        "profile_filename_candidates": [
            "ChromaLuxe_Gloss.icc",
            "ChromaLuxe_Matte.icc",
            "Sublimation_PhotoPanel.icc",
        ],
        "default_intent": "relative",
        "default_bpc": True,
        "workflow": "sublimation",
        "mirror_output": True,
        "notes": "Mirror enabled. ChromaLuxe ships official ICC profiles - download from their website. 400 F for 60s gloss / 75s matte.",
    },
    {
        "id": "sublimation_sublijet_generic",
        "label": "Sublimation - SubliJet Generic",
        "printer": "Sawgrass SG500 / SG1000 / Virtuoso",
        "paper": "TruePix or equivalent sub paper",
        "ink_set": "SubliJet HD/UHD",
        "profile_filename_candidates": [
            "SubliJet_HD_Generic.icc",
            "Sawgrass_Generic.icc",
            "SG500_Generic.icc",
        ],
        "default_intent": "relative",
        "default_bpc": True,
        "workflow": "sublimation",
        "mirror_output": True,
        "notes": "Use Sawgrass PowerDriver / CreativeStudio for best results. PowerDriver profiles take priority over this generic fallback.",
    },
]
