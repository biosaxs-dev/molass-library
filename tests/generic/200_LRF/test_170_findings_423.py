"""Findings of the rank-2 correction (molass-library#423): per code a plain-language text, the region and a check behind each warning, and the impact summary of rank2_report().
The infos are built from their fields, so every code is triggered exactly; one end-to-end check goes through a Decomposition (simulate_tiny)."""
import warnings

import numpy as np
import pytest

from molass.LowRank.BoundedLrf import BoundedLrfInfo
from molass.LowRank.Findings import Finding
from molass.LowRank.Rank2Report import profile_shape_change
from molass.LowRank.SoftBoundedLrf import SoftBoundedInfo


def _soft(**kw):
    base = dict(K=0.3, sigma=88.0, L=2.0, rg_seed=34.0, cutoff_q=0.0707, violation_fraction=0.0, q_min_used=0.01, refine=None)
    return SoftBoundedInfo({**base, **kw})


def _bounded(**kw):
    base = dict(K=0.5, L=2.5, R=44.0, Rg=34.0, cutoff_q=0.0707, band_upper_q=0.106, max_move_in_band=0.01, L_penalized=False, L_stage1=2.5, q_min_used=0.01,
                clipped_fraction=dict(below_b1=0.0, band=0.0, above_b2=0.0))
    return BoundedLrfInfo({**base, **kw})


def _complete(f):
    assert isinstance(f, Finding) and f.code and f.text and f.plain and f.region and f.check
    assert f.plain != f.text and "decomposition." not in f.plain          # words of its own, not the library's text


def test_a_clean_result_has_no_findings():
    assert _soft().findings() == [] and _soft().warnings_list() == []
    assert _bounded().findings() == [] and _bounded().warnings_list() == []


@pytest.mark.parametrize("code, kw", [
    ("refine_at_bound", dict(refine=dict(at_bound=True))),
    ("k_small", dict(K=0.01)),
    ("violation", dict(violation_fraction=0.65)),
    ("q_min_high", dict(q_min_used=0.03)),
])
def test_every_soft_bounded_code_has_a_complete_finding_and_the_unchanged_warning_text(code, kw):
    info = _soft(**kw)
    found = info.findings()
    assert [f.code for f in found] == [code]
    _complete(found[0])
    assert info.warnings_list() == [found[0].text]


@pytest.mark.parametrize("code, kw", [
    ("clipped_below_b1", dict(clipped_fraction=dict(below_b1=0.1, band=0.0, above_b2=0.0))),
    ("clipped_band", dict(clipped_fraction=dict(below_b1=0.0, band=0.83, above_b2=0.9))),
    ("l_penalized", dict(L_penalized=True)),
    ("kl_negative", dict(K=-0.1)),
    ("q_min_high", dict(q_min_used=0.03)),
])
def test_every_bounded_code_has_a_complete_finding_and_the_unchanged_warning_text(code, kw):
    info = _bounded(**kw)
    found = info.findings()
    assert [f.code for f in found] == [code]
    _complete(found[0])
    assert info.warnings_list() == [found[0].text]


def test_the_texts_of_the_warnings_did_not_change():
    assert _soft(violation_fraction=0.65).warnings_list() == [
        "B/A exceeds twice the hard-core envelope significantly at 65% of the points in the band 0.0707 <= q < 0.106: adhesive or soft particles? the soft bound then removes real B(q)"]
    assert _soft(K=0.01).warnings_list() == ["K = 0.01 is small: no detectable interparticle term below q = 0.035; rank 2 may not be needed"]


def test_the_findings_come_in_the_order_of_the_warnings_and_carry_their_numbers():
    found = _soft(refine=dict(at_bound=True), K=0.01, violation_fraction=0.7, q_min_used=0.05).findings()
    assert [f.code for f in found] == ["refine_at_bound", "k_small", "violation", "q_min_high"]
    assert found[2].values['violation_fraction'] == 0.7 and found[2].values['band'] == pytest.approx((0.0707, 1.5 * 0.0707))
    assert "70%" in found[2].plain and "0.0707" in found[2].region


def test_the_shape_change_ignores_the_scale_and_is_zero_where_the_correction_fades():
    rg = 34.0
    q = np.linspace(0.008, 0.25, 300)
    base = np.exp(-(q * rg) ** 2 / 3) + 0.002
    bump = 1.0 + 0.2 * np.exp(-(q * rg) ** 2)                            # a +20 % change at q = 0 that fades out
    out = profile_shape_change(q, 3.7 * base * bump, base, rg)           # 3.7: a different scale of A
    assert out['regions']['high']['median_pct'] == pytest.approx(0.0, abs=0.5)
    assert out['regions']['Guinier']['median_pct'] > 5 and out['regions']['Guinier']['max_abs_pct'] > out['regions']['mid']['max_abs_pct']
    assert profile_shape_change(q[q * rg < 3.0], base[q * rg < 3.0], base[q * rg < 3.0], rg) is None     # nothing to normalise at


def test_rank2_report_has_the_impact_and_the_findings_end_to_end():
    import molass
    from molass.Testing import simulate_tiny
    molass.set_progress(False)
    d = simulate_tiny().trimmed_copy().corrected_copy().quick_decomposition(num_components=1, proportions=[1])
    d.update_xr_ranks([2])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rep = d.rank2_report()
    r = rep[0]
    assert [f.text for f in r['findings']] == r['warnings']
    assert len(r['impact']['rg']) == 2 and all(set(g) == {'convention', 'uncorrected', 'corrected', 'change_pct'} for g in r['impact']['rg'])
    text = repr(rep)
    assert "impact: Rg" in text and "impact: A(q) shape against rank 1" in text and ("no findings" in text or "finding [" in text)
