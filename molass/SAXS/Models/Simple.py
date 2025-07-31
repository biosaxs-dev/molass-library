"""
SAXS/Models/Simple.py
"""
import numpy as np

def guinier_porod(q, G, Rg, d, return_also_q1=False):
    q1 = 1/Rg*np.power(3*d/2, 1/2)
    D = G * np.exp(-q1**2 * Rg**2/3) * q1**d
    lower = q <= q1
    qlow = q[lower]
    qhigh = q[np.logical_not(lower)]
    low_angle_values = G * np.exp(-qlow**2*Rg**2/3)
    high_angle_values = D/qhigh**d
    w = np.concatenate([low_angle_values, high_angle_values])
    if return_also_q1:
        return w, q1
    else:
        return w

