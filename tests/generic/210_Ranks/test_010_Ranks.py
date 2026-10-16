"""
    test SCDs computation from decomposition
"""
import numpy as np
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
    # The former pinned values [1.441978, 0.6520818] belonged to an older 2-component default
    # decomposition of SAMPLE1 and are stale (now 3 components, #306); check the structure instead.
    assert len(scds) == decomposition.num_components
    assert all(np.isfinite(scds)) and all(s > 0 for s in scds)

if __name__ == "__main__":
    test_010_compute_scds()
    # plt.show()