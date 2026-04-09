import io, contextlib, os, sys
import numpy as np
from molass.DataObjects import SecSaxsData as SSD
from molass.Peaks.EghPeeler import egh_peel

DATA_ROOT = r"C:\Users\takahashi\Dropbox\MOLASS\DATA\20260305"

datasets = {
    "ATP": (os.path.join(DATA_ROOT, "ATP"), {"uv_monitor": 290}),
    "Apo": (os.path.join(DATA_ROOT, "Apo"), {}),
}

for name, (path, kwargs) in datasets.items():
    # Load silently
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        ssd = SSD(path, **kwargs)
        trimmed = ssd.trimmed_copy()
        corrected = trimmed.corrected_copy()
    finally:
        sys.stdout = old_out
        sys.stderr = old_err

    icurve = corrected.xr.get_icurve()
    print(f"\n=== {name} ===")
    peaks = egh_peel(icurve.x, icurve.y, debug=True)
    print(f"Result: {len(peaks)} peaks")
    for i, p in enumerate(peaks):
        print(f"  peak {i+1}: H={p[0]:.5f}, mu={p[1]:.1f}, sigma={p[2]:.1f}, tau={p[3]:.1f}")

# SAMPLE1
old_out, old_err = sys.stdout, sys.stderr
sys.stdout = io.StringIO()
sys.stderr = io.StringIO()
try:
    from molass_data import SAMPLE1
    ssd = SSD(SAMPLE1)
    trimmed = ssd.trimmed_copy()
    corrected = trimmed.corrected_copy()
finally:
    sys.stdout = old_out
    sys.stderr = old_err

icurve = corrected.xr.get_icurve()
print(f"\n=== SAMPLE1 ===")
peaks = egh_peel(icurve.x, icurve.y, debug=True)
print(f"Result: {len(peaks)} peaks")
for i, p in enumerate(peaks):
    print(f"  peak {i+1}: H={p[0]:.5f}, mu={p[1]:.1f}, sigma={p[2]:.1f}, tau={p[3]:.1f}")
