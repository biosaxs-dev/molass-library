"""
ScipyUtils.BoundsChecker.py
"""

def check_egh_bounds(x, y, x0, bounds, modify=False, debug=False):
    """
    Check if the parameters for EGH function are within specified bounds.
    Optionally modify the parameters to fit within bounds and visualize the results.

    Parameters
    ----------
    x : array-like
        The x-values of the data.
    y : array-like
        The y-values of the data.
    x0 : array-like
        The initial guess parameters for the EGH function, expected to be in groups of four (H, tR, sigma, tau).
    bounds : list of tuples
        The bounds for each parameter, specified as (min, max) pairs.
    modify : bool, optional
        If True, modify x0 to fit within bounds. Default is False.
    debug : bool, optional
        If True, print debug information and plot the results. Default is False.

    Returns
    -------
    x0 : array-like
        The modified parameters, if modify is True. Otherwise, returns None.
    """
    import numpy as np

    x0 = np.asarray(x0).copy()
    for i, (val, (lower, upper)) in enumerate(zip(x0, bounds)):
        if (lower is not None and val < lower) or (upper is not None and val > upper):
            if debug:
                j, k = divmod(i, 4)
                print(f"Parameter {(j, k)} (value={val}) is out of bounds: ({lower}, {upper})")
            if modify:
                if lower is not None and val < lower:
                    x0[i] = lower
                if upper is not None and val > upper:
                    x0[i] = upper
    
    if debug:
        import matplotlib.pyplot as plt
        from molass.SEC.Models.Simple import egh

        shape = len(x0)//4, 4
        params = x0.reshape(shape)
        
        fig, ax = plt.subplots()
        ax.plot(x, y, label='Function')
        for i, (H, tR, sigma, tau) in enumerate(params):
            y_fit = egh(x, H, tR, sigma, tau)
            ax.plot(x, y_fit, ":", label=f'Component {i+1}: H={H}, tR={tR}, σ={sigma}, τ={tau}')

        ax.legend()
        plt.show()

    if modify:
        return x0
