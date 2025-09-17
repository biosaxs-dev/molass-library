"""
    Theory.SolidSphere.py

    Copyright (c) 2020-2023, SAXS Team, KEK-PF
"""
import numpy as np
from scipy.integrate import quad
from scipy.special import spherical_jn
from scipy.interpolate import UnivariateSpline
from scipy.optimize import minimize
import matplotlib.pyplot as plt

def f_imp(s, R):

    def psi(r):
        return 0 if r > R else 1

    # note that np.sinc(x) is normalized. i.e., np.sin(np.pi*x)/(np.pi*x)
    return 4*np.pi*quad(lambda x: psi(x)*np.sinc(s*x/np.pi)*x**2, 0, R)[0]

def f(qv, R):
    scale = f_imp(0, R)
    y = np.zeros_like(qv)
    for k, q in enumerate(qv):
        y[k] = f_imp(q, R)
    return y/scale

def phi(s, R):
    sr = s*R
    return 3*np.power(sr, -3)*(np.sin(sr) - sr*np.cos(sr))

def phi_j1(s, R):
    sr = s*R
    # print(spherical_jn(1, 1e-6)/1e-6)
    # return 4*np.pi*R**2/s*spherical_jn(1, sr)
    # spherical_jn(1, x)/x → 1/3 as x → 0
    return 3*spherical_jn(1, sr)/sr

def a_func(q, R):
    return phi(q, R)**2

def b_to_a_func(q, R):
    return -8*phi(q, 2*R)

def find_boundary(y, ratio):
    w = np.where(np.abs(y) > ratio)[0]
    return w[-1] if len(w) > 0 else len(y)-1

QV = None
B2_LIMIT_RATIO = 0.99
def get_boundary_params(Rg, qv=None):
    if qv is None:
        global QV
        if QV is None:
            QV = np.linspace(0.005, 0.5, 100)
        qv = QV
    R = np.sqrt(5/3)*Rg
    rq = -phi(qv, 2*R)
    spline = UnivariateSpline(qv, rq, k=4, s=0)
    roots = spline.derivative().roots()
    b1, b2 = roots[0:2]
    k = -np.log(1/B2_LIMIT_RATIO - 1)/(b2 - b1)
    return b1, b2, k

def get_boundary_params_simple(Rg):
    R = np.sqrt(5/3)*Rg
    b1 = np.pi/R
    b2 = b1*1.5
    k = -np.log(1/B2_LIMIT_RATIO - 1)/(b2 - b1)
    return b1, b2, k

def demo1():
    qv = np.linspace(0.005, 0.5, 100)

    fig, axes = plt.subplots(nrows=2, ncols=3, figsize=(21, 11))

    ax1, ax2, ax3 = axes[0,:]
    ax4, ax5, ax6 = axes[1,:]

    y1 = f(qv, 30)
    y2 = phi(qv, 30)
    y3 = phi_j1(qv, 30)
    ax1.plot(qv, y1)
    ax2.plot(qv, y2)
    ax3.plot(qv, y3)

    ay1 = f(qv, 30)**2
    ay2 = phi(qv, 30)**2
    ay3 = phi_j1(qv, 30)**2

    for ax in [ax4, ax5, ax6]:
        ax.set_yscale('log')

    ax4.plot(qv, ay1)
    ax5.plot(qv, ay2)
    ax6.plot(qv, ay3)

    fig.tight_layout()
    plt.show()

def plot_boundary(ax, Rg, qv=None, boundary_ratio=0.05, fontsize=None):
    if qv is None:
        qv = np.linspace(0.005, 0.5, 100)
    RRg_ratio = np.sqrt(5/3)
    R = Rg*RRg_ratio
    ax.set_title("Rg=%g (R=%.3g)" % (Rg, R), fontsize=fontsize)
    ax.set_yscale('log')
    ax.plot(qv, a_func(qv, R), label='A(q)')
    axt = ax.twinx()
    axt.grid(False)
    axt.set_ylim(-2, 2)
    by = b_to_a_func(qv, R)
    axt.plot(qv, by, label='B(q)/A(q)', color='pink')
    k = find_boundary(by, boundary_ratio)
    ymin, ymax = axt.get_ylim()
    axt.set_ylim(ymin, ymax)
    b = qv[k]
    axt.plot([b, b], [ymin, ymax], color='red', label='boundary: q=%.2g' % b)

    ax.legend(fontsize=fontsize)
    axt.legend(bbox_to_anchor=(1, 0.8), loc='upper right', fontsize=fontsize)

def demo2():
    qv = np.linspace(0.005, 0.5, 100)
    nrows = 3
    ncols = 5
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(21, 11))

    fig.suptitle("Rank Boundary Estimation based on Solid Sphere Model", fontsize=20)

    for i in range(nrows):
        Rg_base = (i+1)*20
        for j in range(ncols):
            ax = axes[i,j]
            Rg = Rg_base + j*4
            plot_boundary(ax, Rg, qv)

    fig.tight_layout()
    fig.subplots_adjust(top=0.9)

    plt.show()

def demo3(Rg=32):
    qv = np.linspace(0.005, 0.5, 100)

    R = np.sqrt(5/3)*Rg
    aq = phi(qv, R)**2
    rq = -phi(qv, 2*R)
    bq = aq*rq

    b1, b2, k = get_boundary_params(Rg)

    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(14, 7))
    fig.suptitle("Adjusting the Logistic Function Parameter K to B(q)/A(q) Decline", fontsize=20)

    ax1.set_yscale('log')
    ax1.set_title("Rg=%.3g" % Rg, fontsize=16)
    ax1.plot(qv, aq)

    axt = ax1.twinx()
    axt.grid(False)

    for ax in [axt, ax2]:
        ax.plot(qv, rq, color='yellow', label='B(q)/A(q)')
        ax.plot(qv, bq, color='cyan', label='B(q)')
        ymin, ymax = ax.get_ylim()
        ax.set_ylim(ymin, ymax)
        ax.plot([b1, b1], [ymin, ymax], ':', color='red', label='q s.t. w(q)=0.5')
        ax.plot([b2, b2], [ymin, ymax], ':', color='blue', label='q s.t. 1 - w(q)=0.01')

    ax2.set_title("k=%.3g" % k, fontsize=16)
    ax2t = ax2.twinx()
    ax2t.grid(False)

    y = 1/(1 + np.exp(-k*(qv-b1)))
    ax2t.plot(qv, y, label='w(q)')
    ax2t.plot(qv, 1-y, label='1 - w(q)')
    ax2t.legend(bbox_to_anchor=(1, 0.7), loc='center right', fontsize=16)
    ax2.legend(bbox_to_anchor=(1, 0.4), loc='center right', fontsize=16)

    fig.tight_layout()
    fig.subplots_adjust(top=0.85)

    plt.show()

def demo4(Rg=35):
    R = np.sqrt(5/3)*Rg
    qv = np.linspace(0.005, 0.3, 100)
    b1, b2, _ = get_boundary_params_simple(Rg)

    fig, ax = plt.subplots(figsize=(10,7))
    ax.set_yscale('log')
    axt = ax.twinx()
    axt.grid(False)

    ax.set_title("Periodic appearances in $ \Phi(qR)^2 $ and $cos(qR)^2$", fontsize=20)

    ax.plot(qv, phi(qv, R)**2, label='$ \Phi(qR)^2 $')
    axt.plot(qv, np.cos(qv*R), ':', color='C1', label='$cos(qR)$')
    axt.plot(qv, np.cos(qv*R)**2, ':', color='C2', label='$cos(qR)^2$')

    ymin, _ = axt.get_ylim()
    ymax = 4
    axt.set_ylim(ymin, ymax)
    for b, label in [[b1, r"$b_1=\pi/R$"], [b2, r"$b_2=1.5\pi/R$"]]:
        axt.plot([b, b], [ymin, ymax], ':', color='red', label=label)

    ax.legend(fontsize=16)
    axt.legend(bbox_to_anchor=(1, 0.9), loc='upper right', fontsize=16)
    fig.tight_layout()
    plt.show()

class SolidSphere:
    def __init__(self):
        pass

    def fit(self, qv, Ic, initRg):
        scale = np.sqrt(5/3)
        initR = scale*initRg

        def obj_func(p):
            C, R = p
            return np.sum((Ic - C*phi(qv,R)**2)**2)

        res = minimize(obj_func, (1, initR))
        self.C, self.R = res.x
        self.Rg = self.R/scale
        return res.x

    def intensity(self, qv):
        return self.C * phi(qv,self.R)**2
