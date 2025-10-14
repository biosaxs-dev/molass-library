"""
Bounded structure factorization tests with controlled execution order.
Requires: pip install pytest-order
"""

import numpy as np
import matplotlib.pyplot as plt
import pytest
from molass.Testing import control_matplotlib_plot

@pytest.mark.order(1)
@control_matplotlib_plot
def test_001_demo4():
    from molass import get_version
    assert get_version() >= '0.5.0', "This tutorial requires molass version 0.5.0 or higher."
    from molass.SAXS.Theory.SolidSphere import demo4
    demo4()

@pytest.mark.order(2)
@control_matplotlib_plot
def test_002_demo():
    from molass.SAXS.Theory.SfBound import demo
    demo()