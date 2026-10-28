"""
AI-friendliness fixes (#343, #347): load_analysis_session loads the best job by default, and
Component.icurve / jcurve are the curve objects (not None until a getter is called).
"""
import inspect
import numpy as np


def test_010_load_analysis_session_defaults_to_the_best_job():
    from molass.Rigorous.CurrentStateUtils import load_analysis_session
    from molass.LowRank.Decomposition import Decomposition
    assert inspect.signature(load_analysis_session).parameters['jobid'].default == 'best'
    assert inspect.signature(Decomposition.load_analysis_session).parameters['jobid'].default == 'best'


def test_020_usable_qrange_does_not_reload_by_default():
    from molass.Trimming.UsableQrange import get_usable_qrange_impl
    assert inspect.signature(get_usable_qrange_impl).parameters['debug'].default is False


def test_030_component_curves_are_not_none():
    from molass.LowRank.Component import Component
    icurve_array = np.array([np.arange(10.0), np.arange(10.0) ** 2])
    jcurve_array = np.column_stack([np.linspace(0.01, 0.3, 20), np.ones(20), np.zeros(20)])
    comp = Component(icurve_array, jcurve_array, ccurve=None)
    assert comp.icurve is not None and comp.jcurve is not None
    assert comp.icurve is comp.get_icurve() and comp.jcurve is comp.get_jcurve()   # cached, same object
    assert len(comp.icurve.x) == 10 and len(comp.jcurve.x) == 20
