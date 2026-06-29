# molass_data Sample Datasets

Reference for the test datasets included in the `molass_data` package.

## Overview

| Dataset | Protein(s) | Frames | q-points | q range (1/Å) | Expected Rank | Notes |
|---------|-----------|--------|----------|---------------|---------------|-------|
| SAMPLE1 | ALD + OA | 242 | 1028 | 0.006 – 0.437 | 2 | Two-component standard mixture |
| SAMPLE2 | (unknown) | 1000 | 783 | — | — | Very hard case |
| SAMPLE3 | GI | 360 | 775 | 0.0075 – 0.4192 | 2 | Interparticle effects (SCD ≈ 5.14) |
| SAMPLE4 | (unknown) | 220 | 773 | — | — | Very hard case |

## Detailed Descriptions

### SAMPLE1 — Aldolase + Ovalbumin

- **Species**: ALD (aldolase, ~158 kDa) + OA (ovalbumin, ~44 kDa)
- **M shape**: 1028 × 242
- **Known issue**: One row of all-zero errors in the error matrix (requires floor correction)
- **Use case**: Standard two-component benchmark; well-separated peaks

### SAMPLE2

- **M shape**: 783 × 1000
- **Use case**: Stress test (very hard case); details undocumented

### SAMPLE3 — Glucose Isomerase

- **Species**: GI (glucose isomerase, ~173 kDa tetramer)
- **M shape**: 775 × 360
- **q range**: 0.0075 – 0.4192 Å⁻¹
- **UV file**: 720 columns (2:1 ratio vs SAXS frames; see [FORMAT.md](FORMAT.md))
- **UV peak frame**: ~200
- **SCD**: ≈ 5.137 (above `RANK2_SCD_LIMIT = 5.0`)
- **Expected rank**: 2 (due to interparticle interference, not multiple species)
- **Rg (rank-1)**: ~27.6 Å (biased by c² term)
- **Rg (rank-2)**: ~33.4 Å (closer to true value)
- **Use case**: Demonstrates interparticle effect detection and rank-2 correction

### SAMPLE4

- **M shape**: 773 × 220
- **Use case**: Stress test (very hard case); details undocumented

## Usage

```python
from molass_data import SAMPLE1
from molass.DataObjects import SecSaxsData as SSD

ssd = SSD(SAMPLE1)
M = ssd.xr_data.M      # SAXS matrix (n_q × n_frames)
q = ssd.xr_data.qv     # q-vector
E = ssd.xr_data.E      # error matrix
```

See also [FORMAT.md](FORMAT.md) for the raw file format details.
