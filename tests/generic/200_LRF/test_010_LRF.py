"""
    test LRF
"""
import pytest
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass_data import SAMPLE1
from molass.DataObjects import SecSaxsData as SSD
from molass.Testing import control_matplotlib_plot, is_interactive

def corrected_ssd_instance_():
    ssd = SSD(SAMPLE1)
    trimmed_ssd = ssd.trimmed_copy()
    corrected_copy = trimmed_ssd.corrected_copy()
    return corrected_copy

corrected_ssd_instance = corrected_ssd_instance_()

@control_matplotlib_plot
def test_010_default():
    ssd = corrected_ssd_instance
    ssd.estimate_mapping()
    decomposition = ssd.quick_decomposition()
    decomposition.plot_components(debug=is_interactive())

@control_matplotlib_plot
def test_020_num_components():
    ssd = corrected_ssd_instance
    ssd.estimate_mapping()
    decomposition = ssd.quick_decomposition(num_components=3)
    decomposition.plot_components(debug=is_interactive())

def test_030_upgrade_preserves_rgcurve():
    """Test that upgrade() preserves the _rgcurve cache (issue #220).
    
    The Rg curve is expensive to compute. When upgrading from EGH to a physical
    model (SDM/EDM/LKM/GRM), the cache should be preserved automatically so
    subsequent score_initial() calls don't recompute it.
    """
    ssd = corrected_ssd_instance
    
    # Get Rg curve and create initial decomposition
    rgcurve = ssd.get_rg_curve()
    decomp_egh = ssd.quick_decomposition(num_components=3, rgcurve=rgcurve)
    
    # Verify EGH has cached rgcurve
    assert hasattr(decomp_egh, '_rgcurve')
    assert decomp_egh._rgcurve is not None
    egh_rgcurve_id = id(decomp_egh._rgcurve)
    
    # Upgrade to SDM
    decomp_sdm = decomp_egh.upgrade(model='SDM')
    
    # Verify SDM preserved the cache
    assert hasattr(decomp_sdm, '_rgcurve'), "upgrade() should preserve _rgcurve cache"
    assert decomp_sdm._rgcurve is not None, "_rgcurve should not be None after upgrade"
    assert id(decomp_sdm._rgcurve) == egh_rgcurve_id, "_rgcurve should be the same object"
    
    # Verify it works for other models too
    decomp_edm = decomp_egh.upgrade(model='EDM')
    assert hasattr(decomp_edm, '_rgcurve')
    assert id(decomp_edm._rgcurve) == egh_rgcurve_id

if __name__ == "__main__":
    test_010_default()
    # plt.show()