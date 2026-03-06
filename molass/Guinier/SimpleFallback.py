"""
Guinier.SimpleFallback.py
"""
import numpy as np
import matplotlib.pyplot as plt
MIN_RG = 10.0   # Angstrom
MAX_RG = 100.0   # Angstrom

def compute_rg(qw2, lnI, weights):
    """
    Compute radius of gyration (Rg) using weighted linear regression.
    """
    W = np.diag(weights)
    A = np.vstack([qw2, np.ones(len(qw2))]).T
    Aw = W @ A
    lnIw = W @ lnI
    coeffs, residuals, rank, s = np.linalg.lstsq(Aw, lnIw, rcond=None)
    slope = coeffs[0]
    Rg = np.sqrt(-3 * slope)
    return Rg

def compute_r_squared(qw2, lnI, weights):
    """
    Compute R² (coefficient of determination) for weighted linear regression.
    
    Parameters
    ----------
    qw2 : ndarray
        q² values
    lnI : ndarray
        Natural log of intensity
    weights : ndarray
        Weights for each point
    
    Returns
    -------
    float
        R² value (closer to 1.0 means better linearity)
    """
    W = np.diag(weights)
    A = np.vstack([qw2, np.ones(len(qw2))]).T
    Aw = W @ A
    lnIw = W @ lnI
    
    coeffs, _, _, _ = np.linalg.lstsq(Aw, lnIw, rcond=None)
    
    # Compute fitted values
    lnI_fit = coeffs[0] * qw2 + coeffs[1]
    
    # Compute R² with weights
    residuals = lnI - lnI_fit
    ss_res = np.sum(weights * residuals**2)
    
    lnI_mean = np.sum(weights * lnI) / np.sum(weights)
    ss_tot = np.sum(weights * (lnI - lnI_mean)**2)
    
    if ss_tot == 0:
        return 0.0
    
    r_squared = 1 - (ss_res / ss_tot)
    return r_squared

def estimate_rg_simply(data, rg_range=None, min_num_points=5, q_rg_limit=1.3, initial_q_max=0.025):
    """
    A simple fallback function for Guinier analysis.
    
    This function uses a multi-step approach:
    1. Sliding window to find the most linear region and exclude problematic initial points
    2. Initial conservative fit with the best window to estimate Rg
    3. Range refinement based on q*Rg < q_rg_limit criterion
    4. Final fit with the refined range
    
    Parameters
    ----------
    data : ndarray
        SAXS data with columns [q, I, error]
    rg_range : tuple, optional
        Expected range of Rg values (min_rg, max_rg) in Angstroms.
        Default is (MIN_RG, MAX_RG) = (10.0, 80.0)
    min_num_points : int, optional
        Minimum number of points required in the Guinier region (default: 5)
    q_rg_limit : float, optional
        Guinier criterion limit for q*Rg (default: 1.3)
    initial_q_max : float, optional
        Initial conservative q maximum for searching the best starting window (default: 0.025 Å⁻¹)
    
    Returns
    -------
    dict
        Dictionary containing:
        - 'Rg': Radius of gyration in Angstroms
        - 'I0': Forward scattering intensity
        - 'q_start': Starting index of the fitted range
        - 'q_end': Ending index of the fitted range
        - 'q_min': Minimum q value used in fit (Å⁻¹)
        - 'q_max': Maximum q value used in fit (Å⁻¹)
        - 'n_points': Number of points used in fit
        - 'q_rg_max': Maximum q*Rg value in the fitted range
        - 'r_squared': R² value indicating quality of linear fit
    
    Raises
    ------
    ValueError
        If there are not enough valid data points for analysis
    """
    if rg_range is None:
        rg_range = (MIN_RG, MAX_RG)
    min_rg, max_rg = rg_range
    
    q = data[:,0]
    I = data[:,1]
    e = data[:,2]
    
    # Filter out invalid data
    valid = (I > 0) & (e > 0) & np.isfinite(I) & np.isfinite(e)
    q = q[valid]
    I = I[valid]
    e = e[valid]
    
    if len(q) < min_num_points:
        raise ValueError(f"Not enough valid data points for Guinier analysis (need at least {min_num_points})")

    # Step 1: Find best starting point using sliding window
    # This excludes problematic initial points (beamstop, aggregation, etc.)
    q_limit_idx = np.searchsorted(q, initial_q_max)
    if q_limit_idx < min_num_points:
        q_limit_idx = min(len(q), min_num_points * 2)
    
    best_r_squared = -np.inf
    best_q_start = 0
    
    # Slide a min_num_points window from q=0 to initial_q_max
    for q_start_candidate in range(q_limit_idx - min_num_points + 1):
        q_end_candidate = q_start_candidate + min_num_points
        
        q_window = q[q_start_candidate:q_end_candidate]
        I_window = I[q_start_candidate:q_end_candidate]
        e_window = e[q_start_candidate:q_end_candidate]
        
        qw2_window = q_window**2
        lnI_window = np.log(I_window)
        weights_window = I_window**2 / e_window**2
        
        r_squared = compute_r_squared(qw2_window, lnI_window, weights_window)
        
        if r_squared > best_r_squared:
            best_r_squared = r_squared
            best_q_start = q_start_candidate
    
    # Step 2: Initial conservative fit with best window
    q_end_initial = min(best_q_start + min_num_points, q_limit_idx)
    
    q_init = q[best_q_start:q_end_initial]
    I_init = I[best_q_start:q_end_initial]
    e_init = e[best_q_start:q_end_initial]
    
    qw2_init = q_init**2
    lnI_init = np.log(I_init)
    weights_init = I_init**2 / e_init**2
    
    Rg_initial = compute_rg(qw2_init, lnI_init, weights_init)
    
    # Step 3: Refine q-range based on estimated Rg
    # Ensure Rg is within expected bounds
    Rg_estimate = np.clip(Rg_initial, min_rg, max_rg)
    q_max_refined = q_rg_limit / Rg_estimate
    
    # Step 4: Final fit with refined range
    q_end_refined = np.searchsorted(q, q_max_refined, side='right')
    q_end_refined = max(q_end_refined, best_q_start + min_num_points)  # Ensure minimum points
    q_end_refined = min(q_end_refined, len(q))  # Don't exceed array bounds
    
    q_final = q[best_q_start:q_end_refined]
    I_final = I[best_q_start:q_end_refined]
    e_final = e[best_q_start:q_end_refined]
    
    qw2_final = q_final**2
    lnI_final = np.log(I_final)
    weights_final = I_final**2 / e_final**2
    
    Rg_final = compute_rg(qw2_final, lnI_final, weights_final)
    
    # Compute I0 from the intercept
    W = np.diag(weights_final)
    A = np.vstack([qw2_final, np.ones(len(qw2_final))]).T
    Aw = W @ A
    lnIw = W @ lnI_final
    coeffs, _, _, _ = np.linalg.lstsq(Aw, lnIw, rcond=None)
    I0 = np.exp(coeffs[1])
    
    # Ensure Rg is within bounds
    Rg_final = np.clip(Rg_final, min_rg, max_rg)
    
    # Compute final R² for quality assessment
    final_r_squared = compute_r_squared(qw2_final, lnI_final, weights_final)
    
    return {
        'Rg': Rg_final,
        'I0': I0,
        'q_start': best_q_start,
        'q_stop': q_end_refined,
        'q_min': q_final.min(),
        'q_max': q_final.max(),
        'n_points': len(q_final),
        'q_rg_max': (q_final * Rg_final).max(),
        'r_squared': final_r_squared
    }

class SimpleFallback:
    """
    A simple fallback class for Guinier analysis.
    
    Attributes
    ----------
    data : ndarray
        SAXS data with columns [q, I, error]
    rg_range : tuple
        Expected range of Rg values (min_rg, max_rg) in Angstroms
    result : dict
        Results from Guinier analysis
    """
    def __init__(self, data, rg_range=None, q_rg_limit=1.3):
        """
        Initialize SimpleFallback with SAXS data.
        
        Parameters
        ----------
        data : ndarray
            SAXS data with columns [q, I, error]
        rg_range : tuple, optional
            Expected range of Rg values (min_rg, max_rg) in Angstroms
        q_rg_limit : float, optional
            Guinier criterion limit (default: 1.3)
        """
        self.data = data
        self.rg_range = rg_range if rg_range is not None else (MIN_RG, MAX_RG)
        self.q_rg_limit = q_rg_limit
        self.result = None
        
    def estimate(self):
        """
        Perform Guinier analysis and return results.
        
        Returns
        -------
        dict
            Dictionary with keys: 'Rg', 'I0', 'q_min', 'q_max', 'n_points', 'r_squared'
        """
        self.result = estimate_rg_simply(self.data, self.rg_range, q_rg_limit=self.q_rg_limit)
        return self.result
    
    def plot(self, ax=None, show=True):
        """
        Plot Guinier plot with the fitted range.
        
        Parameters
        ----------
        ax : matplotlib.axes.Axes, optional
            Axes to plot on. If None, creates new figure.
        show : bool, optional
            Whether to display the plot (default: True)
        
        Returns
        -------
        matplotlib.axes.Axes
            The axes with the plot
        """
        if self.result is None:
            self.estimate()
        
        if ax is None:
            fig, ax = plt.subplots(figsize=(8, 6))
        
        q = self.data[:,0]
        I = self.data[:,1]
        e = self.data[:,2]
        
        # Filter valid data
        valid = (I > 0) & (e > 0) & np.isfinite(I) & np.isfinite(e)
        q = q[valid]
        I = I[valid]
        e = e[valid]
        
        q2 = q**2
        lnI = np.log(I)
        lnE = e / I
        
        # Plot all data
        ax.errorbar(q2, lnI, yerr=lnE, fmt='o', alpha=0.3, label='All data')
        
        # Highlight fitted range
        mask = (q >= self.result['q_min']) & (q <= self.result['q_max'])
        ax.errorbar(q2[mask], lnI[mask], yerr=lnE[mask], fmt='o', 
                   label=f"Fitted range (n={self.result['n_points']})")
        
        # Plot fit line
        q2_fit = np.linspace(0, q2[mask].max(), 100)
        lnI_fit = np.log(self.result['I0']) - (self.result['Rg']**2 / 3.0) * q2_fit
        ax.plot(q2_fit, lnI_fit, 'r-', linewidth=2, 
               label=f"Rg = {self.result['Rg']:.2f} Å")
        
        ax.set_xlabel(r'$q^2$ (Å$^{-2}$)', fontsize=12)
        ax.set_ylabel(r'ln($I$)', fontsize=12)
        ax.set_title('Guinier Plot', fontsize=14)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        if show:
            plt.tight_layout()
            plt.show()
        
        return ax