# Printer Presets

A preset is a one-click bundle of color management settings for a known
printer + paper + ink combination. Pick one in the GUI's **Quick Preset**
group, or pass `--preset <id>` to the CLI.

Even when the preset's ICC profile filename isn't installed on your machine,
the preset still applies its recommended rendering intent, BPC default, and
mirror setting. Use **Browse...** in the Color Management group to point at
your actual ICC profile.

## Bundled presets (0.3.0)

| ID | Printer | Paper | Workflow | Mirror |
|---|---|---|---|---|
| `epson_artisan_1400_glossy` | Epson Artisan 1400/1430 | Premium Glossy | inkjet | - |
| `epson_artisan_1400_semigloss` | Epson Artisan 1400/1430 | Premium Semi-Gloss | inkjet | - |
| `epson_artisan_1400_velvet_fineart` | Epson Artisan 1400/1430 | Velvet Fine Art | inkjet | - |
| `canon_pro9500_pt` | Canon Pixma Pro9500 Mark II | Photo Paper Pro Platinum | inkjet | - |
| `canon_pro9500_premium_matte` | Canon Pixma Pro9500 Mark II | Premium Matte | inkjet | - |
| `canon_pro9500_luster` | Canon Pixma Pro9500 Mark II | Photo Paper Pro Luster | inkjet | - |
| `canon_pro100_pt` | Canon Pixma Pro-100 | Photo Paper Pro Platinum | inkjet | - |
| `epson_p900_luster` | Epson SureColor P900 | Premium Luster | inkjet | - |
| `epson_p800_hot_press_bright` | Epson SureColor P800/P900 | Hot Press Bright | inkjet | - |
| `generic_color_laser` | Any color laser | Plain/coated | laser | - |
| `commercial_cmyk_swop` | Offset / commercial press | Coated #5 (SWOP) | commercial | - |
| `sublimation_polyester` | Sublimation inkjet | Sublimation transfer paper | sublimation | YES |
| `sublimation_hard_substrate` | Sublimation inkjet | Sublimation transfer paper | sublimation | YES |
| `sublimation_photo_panel` | Sublimation inkjet | Sublimation transfer paper | sublimation | YES |
| `sublimation_sublijet_generic` | Sawgrass SG500/SG1000 | TruePix or equivalent | sublimation | YES |

Run `python -m nup_imposer --list-presets` to print the same list with full
labels and per-preset notes.

## How profile resolution works

Each preset lists a few possible filenames the actual ICC profile might use.
At app startup the registry scans the OS profile directories
(`C:\\Windows\\System32\\spool\\drivers\\color` on Windows,
`/Library/ColorSync/Profiles` on macOS, `/usr/share/color/icc` on Linux)
for `.icc` and `.icm` files. The first filename match wins. Match is
case-insensitive on Windows-style filesystems.

If no match is found, the preset still applies its intent, BPC, and mirror
settings - the destination profile field stays as you left it, and you can
**Browse...** to pick the right ICC file. Manufacturer profile filenames
vary by driver version, so don't be surprised if a fresh install doesn't
match the bundled hints.

## Adding your own presets

Drop one or more JSON files into:

- **Windows**: `%USERPROFILE%\\.nup-imposer\\presets\\`
  *(equivalent: `%APPDATA%\\nup-imposer\\presets\\`)*
- **macOS / Linux**: `~/.nup-imposer/presets/`

Each file may contain a single preset, a list of presets, or a `{"presets": [...]}`
wrapper.

### Schema

```json
{
  "id": "my_studio_canson_baryta",
  "label": "My Studio - Canson Platine Fibre Rag (Pro9500 II)",
  "printer": "Canon Pixma Pro9500 Mark II",
  "paper": "Canson Platine Fibre Rag 310gsm",
  "ink_set": "Lucia pigment (10-color)",
  "profile_filename_candidates": [
    "Canson_Platine_Pro9500II.icc",
    "PFR310_Pro9500_2.icc"
  ],
  "default_intent": "relative",
  "default_bpc": true,
  "workflow": "inkjet",
  "mirror_output": false,
  "notes": "Custom profile generated with i1Profiler. Use Photo Pro Platinum driver setting."
}
```

Field reference:

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Unique. User presets override bundled presets with the same id. |
| `label` | string | yes | Shown in dropdowns and CLI listings. |
| `printer` | string | yes | Printer model. |
| `paper` | string | yes | Paper / substrate name. |
| `ink_set` | string | yes | Ink set name, channel count, ink line. |
| `profile_filename_candidates` | string[] | yes | List of ICC filenames to look for. Can be empty - just means no profile auto-resolution. |
| `default_intent` | string | yes | One of `perceptual`, `relative`, `saturation`, `absolute`. |
| `default_bpc` | bool | yes | Black point compensation default. |
| `workflow` | string | yes | One of `inkjet`, `laser`, `commercial`, `sublimation`. |
| `mirror_output` | bool | yes | Flip the canvas horizontally on save. True for sublimation transfer. |
| `notes` | string | no | Workflow tips shown in the GUI notes panel. |

Invalid entries are skipped silently at load time (a real app would log them).

### Wrapping multiple presets in one file

```json
{
  "presets": [
    { "id": "studio_a_glossy", ... },
    { "id": "studio_a_matte", ... }
  ]
}
```

or just a bare list:

```json
[
  { "id": "studio_a_glossy", ... },
  { "id": "studio_a_matte", ... }
]
```

## A note on sublimation profiles

Sublimation profiles are highly specific to the **ink line + transfer paper +
substrate + heat-press time/temp** combination. The bundled sublimation
presets use generic candidates that almost never match a real installation -
they're there to give you the correct mirror + intent + BPC defaults so you
can plug in your own profile.

Where to get sublimation ICC profiles:

- **Sawgrass** ships profiles through their PowerDriver / CreativeStudio.
- **ChromaLuxe** publishes substrate-specific profiles on their site.
- **Cosmos / Hiipoo / generic** ink vendors usually publish a generic
  polyester ICC; that's a fine starting point but won't beat a custom profile
  made for your specific press + substrate combo.

## Sharing presets

The JSON format is portable. To share with a colleague: zip up the JSON files
in your `~/.nup-imposer/presets/` folder and email them. They drop the files
into the same folder on their machine and restart Nup Imposer.
