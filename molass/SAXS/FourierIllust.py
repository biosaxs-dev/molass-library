"""
SAXS.FourierIllust.py

This code illustrates the Fourier transform of a 3D ellipsoid and its corresponding scattering curve.
"""
import numpy as np
import matplotlib.pyplot as plt
from learnsaxs import draw_voxles_as_dots, get_detector_info, draw_detector_image

def plot_saxs_illust(center, a, b, c):
    N = 32
    x = y = z = np.arange(N)
    xx, yy, zz = np.meshgrid(x, y, z)    
    cx, cy, cz = center
    shape = (xx - cx)**2/a**2 + (yy - cy)**2/b**2 + (zz - cz)**2/c**2 < 1
    canvas = np.zeros((N,N,N))
    canvas[shape] = 1
    fig = plt.figure(figsize=(12,3))
    ax1 = fig.add_subplot(141, projection="3d")
    ax2 = fig.add_subplot(142, projection="3d")
    ax3 = fig.add_subplot(143)
    ax4 = fig.add_subplot(144)
    ax4.set_yscale("log")
    ax1.set_title("Real Space Image")
    ax2.set_title("Resiprocal Space Image $abs(F)^2$")
    ax3.set_title("Detector Image")
    ax4.set_title("Scattering Curve")
    draw_voxles_as_dots(ax1, canvas)
    F = np.fft.fftn(canvas)
    ft_image = np.abs(F)
    draw_voxles_as_dots(ax2, ft_image**2)
    q = np.linspace(0.005, 0.5, 100)
    info = get_detector_info(q, F)
    draw_detector_image(ax3, q, info.y)
    ax4.set_xlabel("q")
    ax4.set_ylabel("I(q)")
    ax4.plot(q, info.y)
    ax1.set_xlim(ax2.get_xlim())
    ax1.set_ylim(ax2.get_ylim())
    ax1.set_zlim(ax2.get_zlim())
    fig.tight_layout()
    return fig