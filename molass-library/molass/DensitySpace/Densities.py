"""
DensitySpace.Densities.py
"""
import numpy as np
from scipy.stats import multivariate_normal

def gaussian_density_for_demo(N):
    """Generate a 3D Gaussian density distribution for demonstration purposes.

    Parameters
    ----------
    N : int
        The size of the 3D grid (N x N x N).
        
    Returns
    -------
    ndarray
        A 3D NumPy array representing the Gaussian density distribution.
    """
    
    w = np.arange(N)
    xx, yy, zz = np.meshgrid(w, w, w, indexing='ij')
    x = np.stack([xx, yy, zz], axis=-1) 
    density = multivariate_normal.pdf(x, mean=(32,32,32), cov=np.eye(3)*30)
    return density*20