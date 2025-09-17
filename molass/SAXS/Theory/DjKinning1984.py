"""
    Theory.DjKinning1984.py

    Copyright (c) 2021, SAXS Team, KEK-PF
"""
import numpy as np
import matplotlib.pyplot as plt
from .SolidSphere import phi

def S0(q, R, K=1):
    return 1 - K*phi(q, 2*R)

def P0(q, R):
    return phi(q, R)**2

def S1(q, R, K=1):
    return 1/(1 + K*phi(q, 2*R))

def P1(q, R, K=1):
    return phi(q, R)**2 * S1(q, R, K=K)

def S(q, R, n):
    A = 2*q*R
    return 1/(1 + 24*n*(G(A, n)/A))

def G(A, n):
    n4 = (1 - n)**4
    alpha = (1 + 2*n)**2/n4
    beta = -6*n*(1 + n/2)**2/n4
    gamma = n*alpha/2

    return ( alpha*(np.sin(A) - A*np.cos(A))/A**2
            + beta*(2*A*np.sin(A) + (2 - A**2)*np.cos(A) - 2)/A**3
            + gamma*(-A**4*np.cos(A) + 4*((3*A**2 - 6)*np.cos(A) + (A**3 - 6*A)*np.sin(A) + 6))/A**5
            )

def P2(q, R, c=0):
    return phi(q, R)**2 * S(q, R, c)

def demo1():
    from .SolidSphere import get_boundary_params_simple

    qv = np.linspace(0.005, 0.3, 100)
    Rg = 35
    R = np.sqrt(5/3)*Rg

    p = P0(qv, R)
    s_ = np.ones(len(qv))
    s0 = S0(qv, R)
    s1 = S1(qv, R)

    b1, b2, k = get_boundary_params_simple(Rg)

    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(16,7))
    fig.suptitle("Comparison of Structure Models for Solid Spheres", fontsize=20)

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
    ax1.plot(qv, p*s1, label=label)
    ax2.plot(qv, s1, label=label)

    for c in [0, 0.1, 0.2]:
        s2 = S(qv, R, c)
        label = 'Kinning (c=%.g)'%c
        ax1.plot(qv, p*s2, ':', label=label)
        ax2.plot(qv, s2, ':', label=label)

    for ax in [ax1, ax2]:
        ymin, ymax = ax.get_ylim()
        ax.set_ylim(ymin, ymax)
        for j, b in enumerate([b1, b2]):
            ax.plot([b, b], [ymin, ymax], ':', color='gray', label='b%d' % (j+1))

    ax1.legend()
    ax2.legend()
    fig.tight_layout()
    fig.subplots_adjust(top=0.85)
    plt.show()
