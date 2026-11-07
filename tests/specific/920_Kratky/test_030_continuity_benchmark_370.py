"""
Acceptance test of the continuity report (molass-library#370): benchmark data with a known truth
(molass-researcher experiments/51_paper_m_results/51r_make_benchmark.py), decomposed as the real
Q3 analyses are (`quick_decomposition(num_components=k, proportions=[1]*k)`). No confident wrong
verdict: discrete benchmarks are reported "discrete", continuum benchmarks never are.
"""
import numpy as np
import pytest

from molass.Testing import Species, simulate_ssd
from molass.Continuity import VERDICT_DISCRETE


def _resolved_discrete():
    return [Species(amp=1.0, center=70, sigma=8, mass=2.0, rg=60.0), Species(amp=1.0, center=120, sigma=8, mass=2.0, rg=40.0),
            Species(amp=1.0, center=170, sigma=8, mass=1.5, rg=25.0)]


def _narrow_continuum():
    # 40 species, Rg 30 -> 25 A over the elution (the regime of SAMPLE4)
    centres = np.linspace(60, 140, 40)
    env = np.exp(-0.5*((centres - 95.0)/22.0)**2)
    amp = 2.0/(6.0*np.sqrt(2*np.pi)/np.diff(centres)[0])*env
    rg = 30.0 + (25.0 - 30.0)*(centres - centres[0])/(centres[-1] - centres[0])
    return [Species(amp=float(a), center=float(c), sigma=6.0, mass=1.0, rg=float(r)) for a, c, r in zip(amp, centres, rg)]


def _report(species, k):
    ssd = simulate_ssd(species, noise=1.0, seed=1)
    rgcurve = ssd.get_rg_curve()
    decomp = ssd.quick_decomposition(num_components=k, rgcurve=rgcurve, proportions=[1]*k)
    return decomp.get_continuity_report(rgcurve=rgcurve)


def test_resolved_discrete_species_are_reported_discrete():
    report = _report(_resolved_discrete(), 3)
    assert report.verdict == VERDICT_DISCRETE
    assert len(report.plateaus) >= 2
    assert report.power > 20


def test_narrow_continuum_is_never_reported_discrete():
    report = _report(_narrow_continuum(), 3)
    assert report.verdict != VERDICT_DISCRETE
    assert report.excess < 2
