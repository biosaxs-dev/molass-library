"""
tests/specific/200_Rigorous/test_200_lumping_constraint.py

Unit tests for LumpingConstraint — do not require molass_data.
Tests the constraint logic and API integration with _dry_run=True.
"""
import numpy as np
import pytest
from molass.Rigorous.LumpingConstraint import (
    LumpingConstraint, _penetration, _compute_boundaries,
)


# --- Pure unit tests (no data loading) ---

class TestPenetration:
    """Tests for the _penetration distance function."""

    def setup_method(self):
        # boundaries: [60.5, 128.5, 185.5]
        # groups: 0=escape-left, 1=[60.5,128.5], 2=[128.5,185.5], 3=escape-right
        self.b = np.array([60.5, 128.5, 185.5])

    def test_inside_group_no_penalty(self):
        assert _penetration(89.0, 1, self.b) == 0.0
        assert _penetration(150.0, 2, self.b) == 0.0

    def test_right_boundary_violation(self):
        # pos=160, label=1 (should be < b[1]=128.5) → right viol = 160 - 128.5 = 31.5
        assert _penetration(160.0, 1, self.b) == pytest.approx(31.5)

    def test_left_boundary_violation(self):
        # pos=30, label=1 (should be > b[0]=60.5) → left viol = 60.5 - 30 = 30.5
        assert _penetration(30.0, 1, self.b) == pytest.approx(30.5)

    def test_left_escape_zone_ok(self):
        # label=0 means left escape; pos < b[0] → no penalty
        assert _penetration(10.0, 0, self.b) == 0.0

    def test_left_escape_zone_violation(self):
        # label=0, pos=70 > b[0]=60.5 → penalty = 70 - 60.5 = 9.5
        assert _penetration(70.0, 0, self.b) == pytest.approx(9.5)

    def test_right_escape_zone_ok(self):
        # label=len(b)=3, pos > b[-1]=185.5 → no penalty
        assert _penetration(200.0, 3, self.b) == 0.0

    def test_right_escape_zone_violation(self):
        # label=3, pos=170 < b[-1]=185.5 → penalty = 185.5 - 170 = 15.5
        assert _penetration(170.0, 3, self.b) == pytest.approx(15.5)

    def test_worst_of_left_right_taken(self):
        # Both boundaries violated (component completely outside its zone):
        # label=1 means zone [60.5, 128.5]; pos=200 → right_viol = 200 - 128.5 = 71.5
        # left_viol = max(0, 60.5 - 200) = 0 → max = 71.5
        assert _penetration(200.0, 1, self.b) == pytest.approx(71.5)


class TestLumpingConstraintImport:
    """API-level smoke test (no decomp data required)."""

    def test_import(self):
        from molass.Rigorous import LumpingConstraint as LC
        assert LC is LumpingConstraint

    def test_repr(self):
        # Construct manually without decomp (bypass __init__)
        c = object.__new__(LumpingConstraint)
        c.weight = 0.2
        c.ref_labels = [1, 1, 2]
        c.boundaries = np.array([60.5, 128.5, 185.5])
        c._n_comp = 3
        r = repr(c)
        assert 'LumpingConstraint' in r
        assert 'n_comp=3' in r
        assert 'weight=0.2' in r

    def test_call_no_penalty(self):
        """__call__ returns 0 when all peaks are inside their zones."""
        c = object.__new__(LumpingConstraint)
        c.weight = 0.2
        c.ref_labels = [1, 1, 2]
        c.boundaries = np.array([60.5, 128.5, 185.5])
        c._n_comp = 3

        # Mock lrf_info: peaks at 89, 109, 157 (all inside zones)
        x = np.arange(300, dtype=float)
        cy0 = np.zeros(300); cy0[89] = 1.0
        cy1 = np.zeros(300); cy1[109] = 1.0
        cy2 = np.zeros(300); cy2[157] = 1.0

        class FakeLrfInfo:
            def get_xr_cy_list(self):
                return [cy0, cy1, cy2]

        FakeLrfInfo.x = x
        penalty = c(FakeLrfInfo())
        assert penalty == pytest.approx(0.0)

    def test_call_with_penalty(self):
        """__call__ returns positive penalty when C1 drifts +49 frames."""
        c = object.__new__(LumpingConstraint)
        c.weight = 0.2
        c.ref_labels = [1, 1, 2]
        c.boundaries = np.array([60.5, 128.5, 185.5])
        c._n_comp = 3

        x = np.arange(300, dtype=float)
        cy0 = np.zeros(300); cy0[90] = 1.0
        # C1 drifted to frame 158 (was 109, ref_label=1 means should be < 128.5)
        cy1 = np.zeros(300); cy1[158] = 1.0
        cy2 = np.zeros(300); cy2[240] = 1.0  # also drifted

        class FakeLrfInfo:
            def get_xr_cy_list(self):
                return [cy0, cy1, cy2]

        FakeLrfInfo.x = x
        penalty = c(FakeLrfInfo())
        # C1: 158 - 128.5 = 29.5; C2: ref=2 zone [128.5, 185.5]; 240 > 185.5 → 54.5
        # C0: 90 inside [60.5, 128.5] → 0
        expected = 0.2 * (0.0 + 29.5 + 54.5)
        assert penalty == pytest.approx(expected)
