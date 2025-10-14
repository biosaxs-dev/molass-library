"""
    Theory.SfBound.py

    Copyright (c) 2021, SAXS Team, KEK-PF
"""
import numpy as np
from .JsPedersen1997 import F1
from .DjKinning1984 import P0, S0
import matplotlib.pyplot as plt

def S0_bound(q, R, K=1):
    return  1 - K * 3 / (q*R)**2

def demo():
    from .SolidSphere import get_boundary_params_simple

    qv = np.linspace(0.005, 0.3, 100)
    Rg = 35
    R = np.sqrt(5/3)*Rg

    p = P0(qv, R)
    s_ = np.ones(len(qv))
    s0 = S0(qv, R)

    b1, b2, k = get_boundary_params_simple(Rg)

    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(16,7))
    fig.suptitle("Structure Factor Bounds", fontsize=20)

    ax1.set_title("Intensities: I(q)=P(q)*S(q)", fontsize=16)
    ax2.set_title("Structure Factors: S(q)", fontsize=16)

    ax1.set_yscale('log')

    label = 'S=1'
    ax1.plot(qv, p, label=label)
    ax2.plot(qv, s_, label=label)
    label = 'Debye (K=1)'
    ax1.plot(qv, p*s0, label=label)
    ax2.plot(qv, s0, label=label)
    label = 'Fournet (K=1)'

    for i, ax in enumerate([ax1, ax2]):
        ymin, ymax = ax.get_ylim()
        if i == 1:
            ymax = 1.8
        ax.set_ylim(ymin, ymax)
        for j, b in enumerate([b1, b2]):
            ax.plot([b, b], [ymin, ymax], ':', color='gray', label='b%d' % (j+1))

    ax2.plot(qv, S0_bound(qv, 2*R), ':', color='red', label='SF Lower Bound')
    ax2.plot(qv, S0_bound(qv, 2*R, K=-1), ':', color='red', label='SF Upper Bound')

    ax1.legend()
    ax2.legend()
    fig.tight_layout()
    fig.subplots_adjust(top=0.85)
    plt.show()
