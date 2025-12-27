

# Sepsey 2014 Equation 21

$$
\phi(\omega) = \exp\left[\frac{1}{\sqrt{2\pi}\sigma}\int_{r_{G}}^{\infty}\frac{n_{p}(r_{p})}{r_{p}}\exp\left(-\frac{\left(\ln r_{p}-\ln r_{p,0}\right)^{2}}{2\sigma^{2}}\right)\left(\frac{1}{1-i\omega\tau_{p}(r_{p})}-1\right)dr_{p}\right]
$$

## Breakdown:

- **φ(ω)** - Characteristic function
- **Outer exp[...]** - Exponential of the integrated term
- **Lognormal PDF**: $\frac{1}{\sqrt{2\pi}\sigma r_p}\exp\left(-\frac{(\ln r_p - \ln r_{p,0})^2}{2\sigma^2}\right)$
- **n_p(r_p)** - Mean number of pore entries (function of pore size)
- **τ_p(r_p)** - Residence time per pore visit (function of pore size)
- **CF term**: $\frac{1}{1-i\omega\tau_p(r_p)} - 1$ - Exponential residence time
- **Integration**: From $r_G$ (molecule size) to $\infty$