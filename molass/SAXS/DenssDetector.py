"""
DenssDetector.py
"""
import numpy as np
import matplotlib.pyplot as plt
from molass_legacy.DENSS.denss.core import *

class DenssDetector:
    def __init__(self, **entries): 
        self.__dict__.update(entries)

def get_denss_detector(q, rho, DENSS_GPU=False, debug=True):
    # return DenssDetector(q=q, y=curve_y, spline=interp)
    # Initialize variables

    dmax = 41
    voxel = 5           # voxel size in Angstroms
    oversampling=3.     # oversampling factor

    D = dmax

    # Initialize variables

    side = oversampling * D
    halfside = side / 2

    # n = int(side / voxel)
    n = rho.shape[0]
    voxel = int(side / n)
    print("side=", side, "n=", n, "voxel=", voxel)
    # want n to be even for speed/memory optimization with the FFT, ideally a power of 2, but wont enforce that
    if n % 2 == 1:
        n += 1
    # store n for later use if needed
    nbox = n

    dx = side / n
    dV = dx ** 3
    V = side ** 3
    x_ = np.linspace(-(n // 2) * dx, (n // 2 - 1) * dx, n)
    # x, y, z = np.meshgrid(x_, x_, x_, indexing='ij')
    # r = np.sqrt(x ** 2 + y ** 2 + z ** 2)

    df = 1 / side
    qx_ = np.fft.fftfreq(x_.size) * n * df * 2 * np.pi
    qz_ = np.fft.rfftfreq(x_.size) * n * df * 2 * np.pi
    # qx, qy, qz = np.meshgrid(qx_,qx_,qx_,indexing='ij')
    qx, qy, qz = np.meshgrid(qx_, qx_, qz_, indexing='ij')
    qr = np.sqrt(qx ** 2 + qy ** 2 + qz ** 2)
    qmax = np.max(qr)
    qstep = np.min(qr[qr > 0]) - 1e-8  # subtract a tiny bit to deal with floating point error
    nbins = int(qmax / qstep)
    qbins = np.linspace(0, nbins * qstep, nbins + 1)

    # create an array labeling each voxel according to which qbin it belongs
    qbin_labels = np.searchsorted(qbins, qr, "right")
    qbin_labels -= 1
    qbl = qbin_labels
    qblravel = qbin_labels.ravel()
    xcount = np.bincount(qblravel)

    # calculate qbinsc as average of q values in shell
    qbinsc = mybinmean(qr.ravel(), qblravel, xcount)

    # allow for any range of q data
    qdata = qbinsc[np.where((qbinsc >= q.min()) & (qbinsc <= q.max()))]

    # F = myfftn(rho, DENSS_GPU=DENSS_GPU)
    F = myrfftn(rho, DENSS_GPU=DENSS_GPU)

    # sometimes, when using denss_refine.py with non-random starting rho,
    # the resulting Fs result in zeros in some locations and the algorithm to break
    # here just make those values to be 1e-16 to be non-zero
    F[np.abs(F) == 0] = 1e-16

    # APPLY RECIPROCAL SPACE RESTRAINTS
    # calculate spherical average of intensities from 3D Fs
    # I3D = myabs(F, DENSS_GPU=DENSS_GPU)**2
    I3D = abs2(F)
    print("I3D.shape=", I3D.shape, "qbin_labels.shape=", qbin_labels.shape)
    Imean = mybinmean(I3D.ravel(), qblravel, xcount=xcount, DENSS_GPU=DENSS_GPU)
    Imean /= Imean.max()

    #scale Fs to match data
    interp = interpolate.interp1d(qbinsc, Imean, kind='cubic', fill_value="extrapolate")
    I4chi = interp(q)

    from molass.SAXS.Models.Formfactors import homogeneous_sphere
    from learnsaxs import draw_voxles_as_dots

    R = 30
    I = homogeneous_sphere(q, R)

    fig = plt.figure(figsize=(12, 5))
    ax1 = fig.add_subplot(121, projection='3d')
    ax1.set_title('Electron density')
    draw_voxles_as_dots(ax1, rho)

    ax2 = fig.add_subplot(122)
    ax2.set_title('SAXS intensity')
    ax2.set_yscale('log')
    ax2.plot(q, I, label='homogeneous sphere')
    ax2.plot(q, I4chi, label='DENSS-like simulation')
    ax2.legend()
    ax2.set_xlabel('q (1/Å)')
    fig.tight_layout()
    plt.show()
