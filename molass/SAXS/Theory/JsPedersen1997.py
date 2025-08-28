"""
    Theory.JsPedersen1997.py

    Copyright (c) 2021, SAXS Team, KEK-PF
"""
import numpy as np
from scipy.integrate import quad, dblquad, nquad
from scipy.optimize import minimize
import matplotlib.pyplot as plt

def F1(q, R):
    qR = q*R
    return 3*(np.sin(qR) - qR*np.cos(qR))/qR**3

def r5(R, e, x):
    return R*np.sqrt(np.sin(x)**2 + e**2*np.cos(x)**2)

# @jit(nopython=True)
def P5(qv, R, e):
    I = np.zeros(len(qv))
    for i, q in enumerate(qv):
        def f(x):
            return F1(q, r5(R, e, x))**2 * np.sin(x)
        I[i] = quad(f, 0, np.pi/2)[0]
    return I

def r6(a, b, c, alpha, beta):
    return np.sqrt((a**2*np.sin(beta)**2 + b**2*np.cos(beta)**2)*np.sin(alpha)**2 + c**2*np.cos(alpha)**2)

# @jit(nopython=True)
def P6d(qv, a, b, c):
    I = np.zeros(len(qv))
    r6_ = lambda x, y: r6(a, b, c, x, y)
    for i, q in enumerate(qv):
        def f(x, y):
            return F1(q, r6_(x, y))**2 * np.sin(x)
        I[i] = dblquad(f, 0, np.pi/2, lambda x: 0, lambda x: np.pi/2)[0]
    return 2/np.pi*I

def P6(qv, a, b, c):
    I = np.zeros(len(qv))
    for i, q in enumerate(qv):
        def f(x, y):
            return F1(q, r6(a, b, c, x, y))**2 * np.sin(x)
        I[i] = nquad(f, [[0, np.pi/2], [0, np.pi/2]])[0]
    return 2/np.pi*I

def demo():
    qv = np.linspace(0.005, 0.5, 100)

    fig, (ax1, ax2, ax3) = plt.subplots(ncols=3, figsize=(22,7))

    ax1.set_title("Ellipsoid of Revolution", fontsize=16)
    ax2.set_title("Tri-axial Ellipsoid (dblquad)", fontsize=16)
    ax3.set_title("Tri-axial Ellipsoid (nquad)", fontsize=16)

    R = 40
    for ax in [ax1, ax2, ax3]:
        ax.set_yscale('log')
        ax.plot(qv, F1(qv, R)**2, label='Sphere')

    for e in [0.9, 1, 1.1]:
        ax1.plot(qv, P5(qv, R, e), ':', label='Ellipsoid e=%g' % e)

    Rg = np.sqrt(3/5)*R

    for a, b, c in [(R, R, R), (4, 5, 6), (10, 11, 12)]:
        r = np.sqrt((a**2 + b**2 + c**2)/5)
        scale = Rg/r
        a_, b_, c_ = a*scale, b*scale, c*scale
        ax2.plot(qv, P6d(qv, a_, b_, c_), ':', label='Ellipsoid a,b,c=(%.2g, %.2g, %.2g)' % (a_, b_, c_))
        ax3.plot(qv, P6(qv, a_, b_, c_), ':', label='Ellipsoid a,b,c=(%.2g, %.2g, %.2g)' % (a_, b_, c_))

    for ax in [ax1, ax2, ax3]:
        ax.legend()

    fig.tight_layout()
    plt.show()

class SolidEllipsoidRev:
    def __init__(self):
        pass

    def fit(self, qv, Ic, initRg):
        scale = np.sqrt(5/3)
        initR = scale*initRg

        def obj_func(p):
            C, R, e = p
            return np.sum((Ic - C*P5(qv, R, e))**2)

        res = minimize(obj_func, (1, initR, 1))
        self.C, self.R, self.e = res.x
        self.Rg = self.R*np.sqrt((1+self.e**2)/4)
        return res.x

    def intensity(self, qv):
        return self.C * P5(qv, self.R, self.e)

class TriAxialEllipsoid:
    def __init__(self):
        pass

    def fit(self, qv, Ic, initRg):
        scale = np.sqrt(5/3)
        initR = scale*initRg

        def obj_func(p):
            C, a, b, c = p
            return np.sum((Ic - C*P6(qv, a, b, c))**2)

        res = minimize(obj_func, (1, initR, initR, initR))
        self.C, self.a, self.b, self.c = res.x
        self.Rg = np.sqrt((self.a**2 + self.b**2 + self.c**2)/5)
        return res.x

    def intensity(self, qv):
        return self.C * P6(qv, self.a, self.b, self.c)


def demo2():

    Rg = 35
    qv = np.linspace(0.005, 0.4, 100)

    fig, ax = plt.subplots()

    ax.set_title("Various Shapes of Ellipsoids with the same Rg=35", fontsize=20)
    ax.set_yscale('log')

    R = np.sqrt(5/3)*Rg
    b1 = np.pi/R
    b2 = b1*1.5

    ax.plot(qv, F1(qv, R)**2, label='Sphere')

    for a, b, c in np.random.uniform(0, 1, (10, 3)):
        print((a, b, c))
        r = np.sqrt((a**2 + b**2 + c**2)/5)
        scale = Rg/r
        a_ = a*scale
        b_ = b*scale
        c_ = c*scale
        ax.plot(qv, P6(qv, a_, b_, c_), label='Ellipsoid(%.3g, %.3g, %.3g)' % (a_, b_, c_))

    ymin, ymax = ax.get_ylim()
    ax.set_ylim(ymin, ymax)
    for b, pc in zip([b1, b2], [50, 1]):
        ax.plot([b, b], [ymin, ymax], ':', color='red', label='rank2 ratio %d%%' % pc)

    ax.legend()
    fig.tight_layout()
    plt.show()
