"""decomposition.rank2_report() (molass-library#420): one call for what the rank-2 correction did. Simulated data (molass.Testing.simulate_tiny); no local data."""
import warnings

import numpy as np
import pytest


def _decomp(ranks):
    import molass
    from molass.Testing import simulate_tiny
    molass.set_progress(False)
    d = simulate_tiny().trimmed_copy().corrected_copy().quick_decomposition(num_components=1, proportions=[1])
    d.update_xr_ranks(ranks)
    return d


def test_no_rank2_component_gives_an_empty_report():
    r = _decomp([1]).rank2_report()
    assert len(r) == 0 and "no rank-2 component" in repr(r)


def test_soft_bounded_report_gathers_the_diagnostics_and_the_rank1_comparison():
    d = _decomp([2])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rep = d.rank2_report()
    r = rep[0]
    info = d.soft_bounded_info[0]
    assert r['method'] == 'soft_bounded' and r['K'] == info['K'] and r['cutoff_q'] == info['cutoff_q'] and r['weight_mid'] == info['weight_mid']
    assert r['warnings'] == info.warnings_list()                         # kept even though the cached result no longer warns
    assert r['refinement'] is None or r['refinement']['max_curve_change'] >= 0
    assert len(r['rg_corrected']) == 2 and len(r['rg_uncorrected']) == 2
    text = repr(rep)
    assert "component 0: soft_bounded" in text and "Rg corrected" in text and "Rg uncorrected (rank 1)" in text and "mean weight" in text


def test_bounded_report_has_the_clipped_fractions():
    d = _decomp([2])
    d.set_rank2_method('bounded')
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rep = d.rank2_report()
    r = rep[0]
    assert r['method'] == 'bounded' and set(r['clipped_fraction']) >= {'band', 'above_b2'} and isinstance(r['L_penalized'], bool)
    assert "clipped: band" in repr(rep)
