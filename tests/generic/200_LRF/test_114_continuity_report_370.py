import json
import numpy as np
import pytest

from molass.Continuity import (compute_continuity_report, plateau_excess, find_plateaus, kratky_separation,
                               VERDICT_DISCRETE, VERDICT_NO_EVIDENCE, VERDICT_UNDETERMINED)


def _curve(levels, n_each=40, noise=0.4, seed=0):
    rng = np.random.default_rng(seed)
    frames = np.arange(n_each*len(levels), dtype=float)
    return frames, np.repeat(levels, n_each) + noise*rng.standard_normal(len(frames))


def test_staircase_is_discrete_and_plateaus_are_found():
    frames, rgs = _curve([60.0, 40.0, 25.0])
    report = compute_continuity_report(frames, rgs, component_rgs=[60.0, 40.0, 25.0])
    assert report.verdict == VERDICT_DISCRETE
    assert [round(p["level"]) for p in report.plateaus] == [60, 40, 25]
    assert report.plateau_backed == [True, True, True]
    assert report.excess >= report.thresholds["excess_min"]


def test_ramp_gives_no_evidence_and_never_continuum():
    rng = np.random.default_rng(1)
    frames = np.arange(120, dtype=float)
    rgs = np.linspace(60, 25, 120) + 0.4*rng.standard_normal(120)
    report = compute_continuity_report(frames, rgs)
    assert report.verdict == VERDICT_NO_EVIDENCE
    assert "continuum" not in report.verdict
    assert not report.plateaus
    assert any("not evidence of a continuum" in note for note in report.notes)


def test_small_drop_is_low_power_and_tiny_drop_is_undetermined():
    rng = np.random.default_rng(2)
    frames = np.arange(100, dtype=float)
    small = compute_continuity_report(frames, np.linspace(30, 25, 100) + 0.3*rng.standard_normal(100))
    assert small.verdict == VERDICT_NO_EVIDENCE
    assert any("Low power" in note for note in small.notes)
    tiny = compute_continuity_report(frames, np.linspace(30, 30.8, 100) + 0.3*rng.standard_normal(100))
    assert tiny.verdict == VERDICT_UNDETERMINED
    assert tiny.power < tiny.thresholds["power_min"]


def test_too_few_frames_is_undetermined():
    report = compute_continuity_report(np.arange(8.0), np.linspace(40, 30, 8))
    assert report.verdict == VERDICT_UNDETERMINED
    assert report.n_frames == 8


def test_thresholds_are_overridable_and_checked():
    frames, rgs = _curve([60.0, 40.0, 25.0])
    strict = compute_continuity_report(frames, rgs, excess_min=1e6)
    assert strict.verdict == VERDICT_NO_EVIDENCE and strict.thresholds["excess_min"] == 1e6
    with pytest.raises(TypeError, match="unknown threshold"):
        compute_continuity_report(frames, rgs, excess=2.0)


def test_report_is_strict_json_and_printable():
    frames, rgs = _curve([60.0, 40.0, 25.0])
    report = compute_continuity_report(frames, rgs, component_rgs=[60, 40, 25])
    json.dumps(report.to_dict(), allow_nan=False)
    text = repr(report)
    assert "DISCRETE" in text and "plateau excess" in text


def test_indicators_on_arrays():
    frames, rgs = _curve([60.0, 25.0])
    assert plateau_excess(frames, rgs) > 2
    assert len(find_plateaus(frames, rgs)) == 2


def test_kratky_separation_distinguishes_shapes_and_ordering():
    qrg = np.linspace(0.3, 6, 300)
    rng = np.random.default_rng(3)

    def curve(peak):
        return qrg, 2.0*(qrg/peak)**2*np.exp(-(qrg/peak)**2) + 0.01*rng.standard_normal(len(qrg))

    same = kratky_separation([curve(1.73) for _ in range(4)])
    assert same["max_sep"] < 3
    ordered = kratky_separation([curve(p) for p in (1.5, 1.8, 2.2, 2.7)])
    assert ordered["max_sep"] > 6 and ordered["end_fraction"] == pytest.approx(1.0)
    assert np.isnan(kratky_separation([curve(1.7), None])["max_sep"])
