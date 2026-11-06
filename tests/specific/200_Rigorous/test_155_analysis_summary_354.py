import json
from types import SimpleNamespace

import numpy as np
import pytest

from molass.DataObjects.Curve import Curve
from molass.Guinier.RgCurve import RgCurve
from molass.LowRank.ComponentCurve import ComponentCurve
from molass.Rigorous.AnalysisFolder import AnalysisInfo


class _FakeResult:
    def __init__(self):
        x = np.arange(20, dtype=float)
        self.xr_ccurves = [ComponentCurve(x, [1.0, 8.0, 2.0, 1.0])]
        y = self.xr_ccurves[0].get_y()
        self.xr_icurve = Curve(x, y, type="i")
        self.uv_icurve = None
        self.uv_ccurves = None
        self.xr = SimpleNamespace(qv=np.linspace(0.001, 0.3, 600))
        self.fv = -1.25
        self.sv = 88.0
        self.model = "egh"
        self._profile = np.exp(-(self.xr.qv * 30.0) ** 2 / 3)
        self._shape_match = SimpleNamespace(
            best_shape=lambda component: ("sphere", 0.8, 0.9),
            to_dict=lambda: {"type": "ShapeMatchResult"},
        )

    def get_guinier_objects(self):
        return [SimpleNamespace(Rg=30.0, Iz=1.0, score=0.8)]

    def get_skewnesses(self):
        return [self.xr_ccurves[0].skewness()]

    def get_xr_matrices(self):
        return None, None, self._profile[:, None], None

    def get_xr_components(self):
        guinier = self.get_guinier_objects()[0]
        return [SimpleNamespace(get_guinier_object=lambda: guinier)]

    def get_kratky_shape_match(self):
        return self._shape_match

    def get_lrf_residual(self):
        return 0.03

    def get_rg_curve(self):
        x = np.arange(20)
        return RgCurve(x, np.full(20, 30.0), np.full(20, 0.8))

    def compute_reconstructed_rgcurve(self):
        x = np.arange(20)
        return RgCurve(x, np.full(20, 29.0), np.ones(20))


def _info():
    job = SimpleNamespace(id="000", best_fv=-1.25, iterations=10, n_entries=11, n_nonfinite=0)
    return AnalysisInfo(
        "analysis-001", _FakeResult(), "000",
        SimpleNamespace(get_rg_curve=lambda: RgCurve(np.arange(20), np.full(20, 30.0), np.full(20, 0.8))),
        None, None,
        {"model": "egh", "method": "bh", "molass_version": "1.2.2"},
        [job], {"status": "completed", "phase": "done"},
    )


def test_summary_dict_contains_metadata_and_component_facts():
    summary = _info().to_summary_dict()

    assert summary["result"]["fv"] == -1.25
    assert summary["jobs"] == [
        {"id": "000", "best_fv": -1.25, "iterations": 10, "entries": 11, "nonfinite": 0}
    ]
    component = summary["result"]["components"][0]
    assert component["rg"] == 30.0
    assert component["i0"] == 1.0
    assert component["guinier_score"] == 0.8
    assert component["area_fraction"] == pytest.approx(1.0)


def test_freeze_round_trips_optional_result_groups(tmp_path):
    path = _info().freeze(tmp_path / "summary.json", include=("curves", "kratky", "rgcurve"))
    with open(path, encoding="utf-8") as source:
        summary = json.load(source)

    assert summary["curves"]["xr"]["total"]["moments"]["mean"] is not None
    assert summary["kratky"]["profiles"]
    assert summary["kratky"]["shape_match"]["type"] == "ShapeMatchResult"
    assert summary["rgcurve"]["data"]["rgs"][0] == 30.0
    assert summary["rgcurve"]["model"]["rgs"][0] == 29.0


def test_summary_rejects_unknown_sections():
    with pytest.raises(ValueError, match="unknown summary sections"):
        _info().to_summary_dict(include=("everything",))


def test_analysis_info_describes_post_analysis_accessors():
    description = _info().describe()
    for accessor in (
        "xr_icurve.get_moment()",
        "decomp.get_rg_curve()",
        "compute_reconstructed_rgcurve()",
        "get_xr_matrices()",
        "get_kratky_shape_match()",
        "get_lrf_residual()",
        "info.freeze(",
    ):
        assert accessor in description


def test_after_analysis_cookbook_examples_run(tmp_path):
    info = _info()
    result = info.result

    total_moment = result.xr_icurve.get_moment().get_meanstd()
    component_moments = [curve.get_moment().get_meanstd() for curve in result.xr_ccurves]
    data_rg = info.decomp.get_rg_curve()
    model_rg = result.compute_reconstructed_rgcurve()
    reliable_frames, reliable_rgs = data_rg.reliable()
    M, C, P, Pe = result.get_xr_matrices()
    q = result.xr.qv
    component_guinier = [component.get_guinier_object() for component in result.get_xr_components()]
    shape_match = result.get_kratky_shape_match()
    residual = result.get_lrf_residual()
    summary_path = info.freeze(tmp_path / "analysis-summary.json", include=("curves", "kratky", "rgcurve"))

    assert len(total_moment) == len(component_moments[0]) == 2
    assert len(data_rg.frames) == len(model_rg.frames)
    assert P.shape[0] == len(q)
    assert len(reliable_frames) == len(reliable_rgs)
    assert len(component_guinier) == 1
    assert shape_match.best_shape(0)[0] == "sphere"
    assert residual == 0.03
    assert summary_path.endswith("analysis-summary.json")
