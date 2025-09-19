"""
    DmaxEstimation.py

    Copyright (c) 2020-2025, SAXS Team, KEK-PF
"""
import numpy as np
from .denss.core import Sasrec, clean_up_data, calc_rg_I0_by_guinier, calc_rg_by_guinier_peak, filter_P
from molass.SAXS.DenssUtils import fit_data_impl

### DENSS.denss.core.py copy & modify BEGIN ###
def estimate_dmax(Iq,dmax=None,clean_up=True):
    """Attempt to roughly estimate Dmax directly from data."""
    # first, clean up the data
    if clean_up:
        Iq = clean_up_data(Iq)
    q = Iq[:, 0]
    I = Iq[:, 1]
    nq = len(q)
    if dmax is None:
        # first, estimate a very rough rg from the first 20 data points
        nmax = 20
        try:
            rg, I0 = calc_rg_I0_by_guinier(Iq, ne=nmax)
        except:
            rg = calc_rg_by_guinier_peak(Iq, exp=1, ne=100)
        # next, dmax is roughly 3.5*rg for most particles
        # so calculate P(r) using a larger dmax, say twice as large, so 7*rg
        D = 7 * rg
    else:
        # allow user to give an initial estimate of Dmax
        # multiply by 2 to allow for enough large r values
        D = 2 * dmax
    # create a calculated q range for Sasrec for low q out to q=0
    qmin = np.min(q)
    dq = (q.max() - q.min()) / (q.size - 1)
    nqc = int(qmin / dq)
    qc = np.concatenate(([0.0], np.arange(nqc) * dq + (qmin - nqc * dq), q))
    # run Sasrec to perform IFT
    sasrec = Sasrec(Iq[:nq // 2], D, qc=None, alpha=0.0, extrapolate=False)
    # if the rg estimate was way off, it would screw up Dmax estimate
    # but the sasrec rg should be more accurate, even with a screwed up guinier estimate
    # so run it again, but this time with the Dmax = 7*sasrec.rg
    # only do this if rg is significantly different
    if np.abs(sasrec.rg - rg) > 0.2 * sasrec.rg:
        sasrec = Sasrec(Iq[:nq // 2], D=7 * sasrec.rg, qc=None, alpha=0.0, extrapolate=False)
    # lets test a bunch of different dmax's on a logarithmic spacing
    # then see where chi2 is minimal. that at least gives us a good ball park of Dmax
    # the main problem is that we don't know the scale even remotely, or the units,
    # so we need to check many orders of magnitude
    Ds = np.logspace(.1, np.log10(2 * 7 * rg), 10)
    chi2 = np.zeros(len(Ds))
    for i in range(len(Ds)):
        sasrec = Sasrec(Iq[:nq // 2], D=Ds[i], qc=None, alpha=0.0, extrapolate=False)
        chi2[i] = sasrec.calc_chi2()
    order = np.argsort(chi2)
    D = 2 * np.interp(2 * chi2.min(), chi2[order], Ds[order])
    # one final time with new D and full q range
    sasrec = Sasrec(Iq, D=D, qc=None, alpha=0.0, extrapolate=False)
    # now filter the P(r) curve for estimating Dmax better
    qmax = 2 * np.pi / D
    # qmax_fraction = 0.5
    r, Pfilt, sigrfilt = filter_P(sasrec.r, sasrec.P, sasrec.Perr, qmax=qmax)  # qmax_fraction*Iq[:,0].max())
    # import matplotlib.pyplot as plt
    # plt.plot(sasrec.r,sasrec.r*0,'k--')
    # plt.plot(sasrec.r, sasrec.P,'b-')
    # plt.plot(r,Pfilt,'r-')
    # estimate D as the first position where P becomes less than 0.01*P.max(), after P.max()
    Pargmax = Pfilt.argmax()
    # catch cases where the P(r) plot goes largely negative at large r values,
    # as this indicates repulsion. Set the new Pargmax, which is really just an
    # identifier for where to begin searching for Dmax, to be any P value whose
    # absolute value is greater than at least 10% of Pfilt.max. The large 10% is to
    # avoid issues with oscillations in P(r).
    argmax_threshold = 0.05
    above_idx = np.where((np.abs(Pfilt) > argmax_threshold * Pfilt.max()) & (r > r[Pargmax]))
    Pargmax = np.max(above_idx)
    dmax_threshold = (0.01 * Pfilt.max())
    near_zero_idx = np.where((np.abs(Pfilt[Pargmax:]) < dmax_threshold))[0]
    near_zero_idx += Pargmax
    D_idx = near_zero_idx[0]
    D = r[D_idx]
    sasrec.D = np.copy(D)
    # plt.plot(sasrec.r,sasrec.r*0+argmax_threshold*Pfilt.max(),'g--')
    # plt.plot(sasrec.r,sasrec.r*0-argmax_threshold*Pfilt.max(),'g--')
    # plt.plot(sasrec.r,sasrec.r*0+dmax_threshold,'r--')
    # plt.axvline(D,c='r')
    # plt.plot()
    # plt.show()
    # exit()
    sasrec.update()
    # return D, sasrec
    return D, sasrec, [r, Pfilt, Pargmax, D_idx]
### DENSS.denss.core.py copy & modify END ###

def plot_input(ax, data, in_file):
    q = data[:,0]
    a = data[:,1]
    e = data[:,2]

    sasrec, work_info = fit_data_impl(q, a, e, in_file)
    qc = sasrec.qc
    ac = sasrec.Ic
    ec = work_info.Icerr

    ax.set_yscale('log')
    ax.set_xlabel('q', fontsize=16)
    ax.set_ylabel('log(I)', fontsize=16)

    ax.plot(q, a, color='C1', label="input data")
    # ax1.plot(qc, ac, color='C2', label="fitted data")

    ax.legend(fontsize=16)

def illustrate_dmax(ax, data):
    D_, sasrec_, info = estimate_dmax(data)
    r = sasrec_.r
    P = sasrec_.P
    r_, Pfilt, Pargmax, D_idx = info

    ax.set_xlabel('r', fontsize=16)
    ax.set_ylabel('P', fontsize=16)

    ax.plot(r, P, color='C1', label="P(r) from input data")
    ax.plot(r_, Pfilt, color='C2', label="filtered P(r)")
    ax.plot(r_[D_idx], Pfilt[D_idx], 'o', color='red', label='estimated Dmax')

    ax.legend(fontsize=16)
    ymin, ymax = ax.get_ylim()
    hymax = ymax*0.5
    if ymin < 0 and abs(ymin) > hymax:
        # cut off the negative part of P(r) if it is too large
        ymin = -abs(hymax)
        ax.set_ylim(ymin, ymax)

def demo(in_file):
    import molass_legacy.KekLib.DebugPlot as plt    
    print(in_file)
    data = np.loadtxt(in_file)

    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(16,7))
    fig.suptitle("Denss Dmax Estimation Illustrated", fontsize=30)

    plot_input(ax1, data, in_file)
    illustrate_dmax(ax2, data)

    fig.tight_layout()
    fig.subplots_adjust(top=0.9)
    plt.show()
