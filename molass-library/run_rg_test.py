import os
os.environ['TQDM_DISABLE'] = '1'

from molass_data import SAMPLE1
from molass.DataObjects import SecSaxsData as SSD
from molass.Guinier.RgCurve import RgCurve
import math, numpy as np

ssd = SSD(SAMPLE1)
decomp = ssd.quick_decomposition()
print('Running get_rg_curve()...', flush=True)
rgcurve = decomp.get_rg_curve()

assert isinstance(rgcurve, RgCurve), f'Expected RgCurve, got {type(rgcurve)}'
assert len(rgcurve.x) > 0
assert len(rgcurve.y) == len(rgcurve.x)
assert len(rgcurve.scores) == len(rgcurve.x)
valid_rgs = [v for v in rgcurve.y if v is not None]
assert len(valid_rgs) > 0

print(f'test_040 PASSED: RgCurve with {len(rgcurve.x)} frames, {len(valid_rgs)} non-None Rg values')
print(f'  non-None range: {min(valid_rgs):.2f} - {max(valid_rgs):.2f} A')
