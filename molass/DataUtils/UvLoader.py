"""
    DataUtils.UvLoader.py

    Copyright (c) 2024, SAXS Team, KEK-PF
"""
import os
from molass_legacy.SerialAnalyzer.SerialDataUtils import load_uv_array, load_uv_file
from molass.DataObjects.Curve import create_icurve

def load_uv(path):
    if os.path.isdir(path):
        uvM, wvector, conc_file = load_uv_array(path)
    else:
        data = load_uv_file(path)
        wvector = data[:,0] 
        uvM = data[:,1:]    
    return uvM, wvector

def get_uvcurves(in_folder):
    uvM, wvector = load_uv(in_folder)
    assert wvector is not None
    c1 = create_icurve(None, uvM, wvector, 280)
    # w = wvector[-5]
    c2 = create_icurve(None, uvM, wvector, 400)
    return c1, c2