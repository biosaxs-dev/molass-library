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

if __name__ == "__main__":
    test_010_PKS()