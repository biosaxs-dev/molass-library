"""
    test SCDs computation from decomposition
"""
import pytest
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass_data import SAMPLE1

def test_010_compute_scds():
    from molass.DataObjects import SecSaxsData as SSD
    ssd = SSD(SAMPLE1)
    trimmed_ssd = ssd.trimmed_copy()
    corrected_copy = trimmed_ssd.corrected_copy()
    decomposition = corrected_copy.quick_decomposition()
    scds = decomposition.compute_scds()
    expected = [1.441978, 0.6520818]
    assert scds == pytest.approx(expected, abs=1e-2)

if __name__ == "__main__":
    test_010_compute_scds()
    # plt.show()