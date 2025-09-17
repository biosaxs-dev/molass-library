"""
    test Mapping
"""
import os
import matplotlib.pyplot as plt
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass.Local import get_local_settings
local_settings = get_local_settings()
DATA_ROOT_FOLDER = local_settings['DATA_ROOT_FOLDER']

def test_010_Kosugi3a():
    from molass.DataObjects import SecSaxsData as SSD
    path = os.path.join(DATA_ROOT_FOLDER, "20161119", "Kosugi3a_BackSub")
    ssd = SSD(path)
    uv_curve = ssd.uv.get_icurve()
    xr_curve = ssd.xr.get_icurve()

    fig, axes = plt.subplots(ncols=2, figsize=(10,4))
    fig.suptitle("Kosugi3a BackSub")
    for ax, curve, title in zip(axes, [uv_curve, xr_curve], ["UV Curve", "XR Curve"]):
        ax.plot(curve.x, curve.y)
        peaks = curve.get_peaks(num_peaks=2)
        ax.plot(curve.x[peaks], curve.y[peaks], 'o', label='Peaks')
        ax.set_title(title)

    fig.tight_layout()
    plt.show()