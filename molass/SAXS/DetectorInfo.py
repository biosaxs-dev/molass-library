"""
DetectorInfo.py
"""
import numpy as np
from scipy import ndimage, interpolate

class DetectorInfo:
    def __init__(self, **entries): 
        self.__dict__.update(entries)

def get_detector_info(q, F, dmax=100):
    shape = F.shape
    voxel = 5
    oversampling = 3

    D = dmax
    dn = shape[0]

    ############### from denss begin ###################

    #Initialize variables

    side = oversampling*D
    halfside = side/2

    if dn is None:
        dn = int(side/voxel)
        #want dn to be even for speed/memory optimization with the FFT, ideally a power of 2, but wont enforce that
        if dn%2==1:
            dn += 1

    #store dn for later use if needed
    nbox = dn

    dx = side/dn
    dV = dx**3
    V = side**3
    # x_ = np.linspace(-halfside,halfside,dn)
    # x,y,z = np.meshgrid(x_,x_,x_,indexing='ij')
    # r = np.sqrt(x**2 + y**2 + z**2)

    df = 1/side
    qx_ = np.fft.fftfreq(dn)*dn*df*2*np.pi

    qx, qy, qz = np.meshgrid(qx_,qx_,qx_,indexing='ij')
    qr = np.sqrt(qx**2+qy**2+qz**2)
    qmax = np.max(qr)
    qstep = np.min(qr[qr>0])
    nbins = int(qmax/qstep)
    qbins = np.linspace(0,nbins*qstep,nbins+1)

    #create modified qbins and put qbins in center of bin rather than at left edge of bin.
    qbinsc = np.copy(qbins)
    qbinsc[1:] += qstep/2.

    #create an array labeling each voxel according to which qbin it belongs
    qbin_labels = np.searchsorted(qbins,qr,"right")
    qbin_labels -= 1

    I3D = np.abs(F)**2
    # print('I3D.shape=', I3D.shape, 'qbin_labels.shape=', qbin_labels.shape)
    index = np.arange(0,qbin_labels.max()+1)
    # print('index=', index)
    Imean = ndimage.mean(I3D, labels=qbin_labels, index=index)

    #scale Fs to match data
    interp = interpolate.interp1d(qbinsc, Imean, kind='cubic', fill_value="extrapolate")
    I4chi = interp(q)

    ############### from denss end ###################

    curve_y = I4chi

    return DetectorInfo(q=q, y=curve_y, spline=interp)