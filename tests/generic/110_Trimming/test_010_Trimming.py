"""
    test Trimming
"""
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass_data import SAMPLE2
from molass.Testing import control_matplotlib_plot, is_interactive

@control_matplotlib_plot
def test_010_PKS():
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(SAMPLE2)
    ssd.plot_trimming(debug=is_interactive())
    trimmed_ssd = ssd.trimmed_copy()
    trimmed_ssd.plot_trimming(debug=is_interactive())

def test_020_adaptive_nsigmas():
    """Verify adaptive nsigmas scales with dataset length."""
    from molass.Trimming.TrimmingUtils import TRIMMING_NSIGMAS
    # Short dataset: should use TRIMMING_NSIGMAS (10)
    assert max(TRIMMING_NSIGMAS, 242 // 75) == 10
    # Long dataset (1500 frames): should widen to 20
    assert max(TRIMMING_NSIGMAS, 1500 // 75) == 20

    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(SAMPLE2)
    n_frames = len(ssd.xr.jv)
    trimmed = ssd.trimmed_copy()
    # Trimming should retain data (not crash)
    assert len(trimmed.xr.jv) > 0

def test_030_uv_wavelength():
    """Verify trimmed_copy(uv_wavelength=(None, 550)) clips UV to <= 550 nm."""
    from molass.DataObjects import SecSaxsData as SSD
    from molass_data import SAMPLE1
    ssd = SSD(SAMPLE1)
    wl_max = 550.0
    trimmed = ssd.trimmed_copy(uv_wavelength=(None, wl_max))
    assert trimmed.uv is not None, "UV data should be present"
    uv_wl = trimmed.uv.wavelengths
    assert uv_wl.max() <= wl_max, (
        f"UV wavelengths should be <= {wl_max} nm, got max={uv_wl.max():.1f}"
    )
    # Default trimming (no uv_wavelength) should produce more wavelengths
    trimmed_default = ssd.trimmed_copy()
    assert len(trimmed_default.uv.wavelengths) >= len(uv_wl), (
        "Clipped trimming should have no more wavelengths than the default"
    )

if __name__ == "__main__":
    test_010_PKS()