# molass_data File Format Reference

This document describes the file formats used in the `molass_data` package.

## Directory Structure

Each sample (e.g., `SAMPLE1`, `SAMPLE3`) is a directory containing:

```
SAMPLEn/
├── PREFIXn_00000.dat
├── PREFIXn_00001.dat
├── ...
├── PREFIXn_NNNNN.dat
└── PREFIXn_UV.txt
```

- The `.dat` files are SAXS scattering profiles, one per elution frame.
- The `_UV.txt` file contains the UV absorbance data for all frames.

## SAXS Frame Files (`.dat`)

Each `.dat` file is a three-column whitespace-delimited text file with **no header**:

| Column | Meaning | Units |
|--------|---------|-------|
| 1 | q (scattering vector) | 1/Å |
| 2 | I(q) (scattering intensity) | a.u. |
| 3 | error (standard deviation of I) | a.u. |

- All frames in a sample share the same q-grid (same number of rows, same q values).
- File numbering is zero-padded and corresponds to the elution frame index.
- Example: `PREFIX3_00000.dat` has 775 rows (q-points).

## UV Absorbance File (`_UV.txt`)

The UV file has a **header section** followed by a data block.

### Header

```
Spectrometers:	QEPB0040
>>>> Data Start <<<<
```

- The first line identifies the spectrometer (tab-separated).
- The second line `>>>> Data Start <<<<` marks the end of the header.
- Data rows begin immediately after the header.

### Data Block

Each row is tab-separated:

| Column | Meaning |
|--------|---------|
| 0 | Wavelength (nm) |
| 1 … N | Absorbance at each frame |

- Wavelengths range from ~200 nm to ~850 nm.
- **Important**: The UV file typically contains **twice as many frame columns** as there are SAXS `.dat` files. For example, SAMPLE3 has 360 SAXS frames but 720 UV columns. This 2:1 ratio reflects the higher sampling rate of the UV detector. Users must downsample (e.g., take every other column, or use the library's built-in loading) to align UV and SAXS data.

### Loading in Code

The recommended way to load data is through the `SecSaxsData` constructor, which handles the header parsing, wavelength extraction, and UV–SAXS alignment automatically:

```python
from molass_data import SAMPLE3
from molass.DataObjects import SecSaxsData as SSD

ssd = SSD(SAMPLE3)
# ssd.xr_data.M  → SAXS matrix (n_q × n_frames)
# ssd.uv_data    → UV data (aligned to SAXS frames)
```

For manual loading, skip the two header lines and treat column 0 as wavelength.
