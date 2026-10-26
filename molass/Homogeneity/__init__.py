"""
    molass.Homogeneity

    Building blocks for a homogeneity analysis of elution peaks: concentration
    proxies (I(0), I(q), A(wavelength)) and their ratio curves.
"""
from molass.Homogeneity.Proxies import (ConcentrationProxy, band_average,
                                        xr_i0_proxy, xr_q_proxy, uv_proxy)
from molass.Homogeneity.Ratios import ProxyRatio, independent_axes
