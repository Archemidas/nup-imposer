# Multi-Ink / RIP-Ready Output

As of **0.4.0**, Nup Imposer can estimate Total Area Coverage (TAC) and export
DeviceN separated TIFFs for ingestion by a RIP (Raster Image Processor).

## What's implemented (0.4.0)

### Ink Set Registry

`core/ink_channels.py` defines an `InkSet` for each supported printer family:

| ID | Printer | Channels | TAC limit |
|---|---|---|---|
| `cmyk_standard` | Generic CMYK | C M Y K | 300% |
| `generic_laser` | Generic color laser | C M Y K | 200% |
| `epson_artisan_1400_6color` | Epson Artisan 1400/1430 (Claria) | C M Y K + LC LM | 260% |
| `canon_pro100_8color` | Canon Pixma Pro-100 (ChromaLife100+) | C M Y BK + PBK PC PM GY | 280% |
| `canon_pro9500ii_10color` | Canon Pixma Pro9500 Mark II (Lucia) | C M Y PBK R G GY PGY PC PM | 260% |
| `epson_p800_8color` | Epson SureColor P800 (UltraChrome HD) | C VM Y PBK MBK + LC VLM LK | 240% |
| `epson_p900_10color` | Epson SureColor P900 (UltraChrome PRO10) | C VM Y PBK MBK + LC VLM LK LLK V | 250% |
| `commercial_cmyk_swop` | Commercial offset (SWOP v2) | C M Y K | 300% |
| `sublimation_cmyk` | Sublimation inkjet | C M Y K | 220% |

Run `python -m nup_imposer --list-ink-sets` to print the same table.

### TAC Estimation

TAC (Total Area Coverage) is the sum of ink coverage percentages per pixel.
For a 4-colour CMYK pixel: `TAC = (C + M + Y + K) / 255 × 100`.

```python
from nup_imposer.core.tac import estimate_tac
from nup_imposer.core.ink_channels import get_default_ink_registry

registry = get_default_ink_registry()
ink_set = registry.find("epson_artisan_1400_6color")

# image = your PIL Image (RGB, CMYK, or L)
result = estimate_tac(image, tac_limit=ink_set.tac_limit)
print(result.summary())
# TAC limit : 260%
# Average   : 183.4%
# 95th pct  : 242.1%
# Maximum   : 287.5%
# ✓ All pixels within TAC limit.
```

`estimate_tac()` works on any PIL mode (converts to CMYK internally).  For
accuracy, apply your ICC transform first using `core/color.py` so the colour
values reflect printer space, not display space.

#### TAC result fields

| Field | Type | Meaning |
|---|---|---|
| `tac_limit` | float | ink set's paper-specific limit (%) |
| `average_pct` | float | mean TAC across sampled pixels |
| `p95_pct` | float | 95th-percentile TAC |
| `max_pct` | float | maximum per-pixel TAC |
| `pixels_over` | int | count of pixels exceeding the limit |
| `total_pixels` | int | total sampled pixel count |
| `exceeds_limit` | bool | True when `max_pct > tac_limit` |
| `fraction_over` | float | `pixels_over / total_pixels` |

### Channel Splitting

`channel_split(cmyk_image, ink_set)` converts a CMYK image into the N channel
images required for DeviceN TIFF export.

For printers with light inks (e.g., Light Cyan), the CMYK parent channel is
split at a `split_at` threshold (0–255):

- Pixels **at or below** `split_at` are mapped to the light channel.
- Pixels **above** `split_at` are scaled into the main channel.
- The two channels are **non-overlapping**—no double-ink is introduced.

```
split_at = 128 (50% density)

  value   →  main       light
    0     →    0          255
   64     →    0          127
  128     →    0            0  ← transition
  192     →   127           0
  255     →   255           0
```

This is a simplified model; real RIP ink optimisation uses the full ICC profile
plus GCR/UCR curves.  The split gives accurate TAC estimates and useful DeviceN
previews.

```python
from nup_imposer.core.tac import channel_split
from nup_imposer.core.ink_channels import get_default_ink_registry

registry = get_default_ink_registry()
ink_set = registry.find("epson_artisan_1400_6color")

# Composite your image first, then:
channels = channel_split(cmyk_image, ink_set)
# returns [c_img, m_img, y_img, k_img, lc_img, lm_img] — all PIL 'L' mode
```

### DeviceN TIFF Export

`export_multichannel_tiff()` composites, transforms, and saves a separated TIFF
that a RIP can ingest directly:

```python
from nup_imposer.core.exporters import export_multichannel_tiff
from nup_imposer.core.ink_channels import get_default_ink_registry

registry = get_default_ink_registry()
ink_set = registry.find("epson_artisan_1400_6color")

path, is_single = export_multichannel_tiff(
    image, layout, "output.tif",
    ink_set=ink_set,
    output_dpi=300,
    color_settings=settings,   # optional ICC transform
)
```

The function tries three export strategies in order:

1. **`tifffile`** (if installed, `pip install tifffile`): writes a proper
   Separated TIFF with LZW compression, InkNames tag, and embedded ICC.
2. **Built-in pure-Python DEFLATE writer**: writes a conformant planar
   Separated TIFF using only the standard library.
3. **Per-channel fallback**: writes N individual 8-bit grayscale TIFFs named
   `<stem>_<ABBREVIATION>.tif` — accepted by most professional RIPs.

`is_single` is `True` for strategies 1 and 2, `False` for strategy 3.

### CLI

```bash
# List available ink sets
python -m nup_imposer --list-ink-sets

# Export 4-up letter sheet as a 6-channel DeviceN TIFF for the Artisan 1400
python -m nup_imposer photo.jpg -n 4 -p Letter \
    --format multichannel \
    --ink-set epson_artisan_1400_6color \
    --dest-profile path/to/EpsonArtisan1400_Glossy.icc \
    --intent relative

# Check TAC and warn before exporting
python -m nup_imposer photo.jpg -n 4 -p Letter \
    --ink-set epson_artisan_1400_6color \
    --tac-warn

# Check TAC and abort if limit exceeded
python -m nup_imposer photo.jpg -n 4 -p Letter \
    --ink-set epson_artisan_1400_6color \
    --tac-error   # exits 6 if TAC exceeded
```

### GUI

The new **Ink Set / TAC** group appears between Color Management and Output:

1. **Ink set** — select the target printer's ink set.
2. **TAC limit** — shows the ink set's paper limit and channel count.
3. **Check TAC** — estimates TAC for the loaded image and shows a summary popup.
4. **Format → Multi-channel TIFF (DeviceN / RIP)** — exports the separated TIFF
   using the selected ink set.

---

## Light ink derivation — technical notes

The simplified threshold split assumes the RIP applies its own full ink
optimisation.  What this gives:

- **Accurate TAC estimate**: main + light channels don't overlap, so coverage
  sums are correct.
- **Correct channel count**: the DeviceN TIFF contains exactly the right number
  of planes, named correctly, so the RIP can map them automatically.
- **Useful starting point**: even without the RIP, the separated TIFF shows the
  expected channel occupancy.

For maximum accuracy, pair this with a manufacturer ICC profile (loaded via
`--dest-profile`) so the CMYK values already live in printer colour space before
the split.

---

## What's still on the roadmap

### 0.5.x — production niceties

- Crop marks, registration marks, colour bars.
- Ink coverage estimate with per-channel statistics in the GUI.
- Batch / hot-folder mode.

### Not on the roadmap

- **Replacing a RIP**: halftoning, screening, dot-gain curves, and direct ink
  channel driving remain the domain of Wasatch, ColorBurst, Mirage, ErgoSoft,
  and similar tools.
- **Profile creation**: spectrophotometer-based profiling (X-Rite i1Pro,
  ColorMunki) is out of scope.

---

## Where to get multi-ink ICC profiles

- **Epson** — Epson Premium ICC Profiles (downloadable from Epson support,
  named by printer + paper + media type).
- **Canon** — Canon Professional Print & Layout ships profiles; individual
  profiles available from Canon support pages.
- **Paper makers** — Hahnemühle, Canson, Red River, Moab, Ilford all publish
  profiles for specific printer + paper combinations.
- **Sublimation** — Sawgrass PowerDriver/CreativeStudio, ChromaLuxe, and
  generic ink vendors ship paper-specific ICC profiles.

Drop profiles into your OS ICC folder and they appear in the **Scan installed
profiles** dropdown.
