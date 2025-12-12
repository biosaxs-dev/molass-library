"""
Stochastic-Dispersive Theory of Chromatography (Felinger et al. 1999)
INTERPRETED THROUGH THE LÉVY PROCESS FRAMEWORK (Pasti et al. 2005)

Implementation of the unified stochastic-dispersive model from:
"Stochastic-Dispersive Theory of Chromatography"
Felinger, A.; Cavazzini, A.; Remelli, M.; Dondi, F.
Anal. Chem. 1999, 71, 20, 4472-4479

════════════════════════════════════════════════════════════════════════════════
LÉVY PROCESS INTERPRETATION (Canonical Form)
════════════════════════════════════════════════════════════════════════════════

Felinger's characteristic function (eq 13):

    Φ(ω) = exp[iωt₀ - Dt₀ω²/(2u) + n·(Φ_s(ω) - 1)]

is EXACTLY a Lévy process with three independent components:

1. DRIFT TERM (convection in mobile phase):
   ────────────────────────────────────────
   γ·iω  where γ = t₀ = L/u
   
   Physical meaning: Deterministic flow carries molecules down column
   Lévy component: Linear drift with velocity u

2. BROWNIAN TERM (axial dispersion):
   ──────────────────────────────────
   -σ²ω²/2  where σ² = 2Dt₀/u = 2DL/u²
   
   Physical meaning: Diffusion spreads molecules symmetrically
   Lévy component: Gaussian with variance σ²

3. COMPOUND POISSON TERM (adsorption-desorption):
   ──────────────────────────────────────────────
   λ·∫[e^(iωτ) - 1]ν(dτ)  where λ = n, ν(dτ) = f_s(τ)dτ
   
   Physical meaning: Random jumps in time due to surface binding
   Lévy component: Jump process with rate λ and jump distribution f_s(τ)

════════════════════════════════════════════════════════════════════════════════
CANONICAL LÉVY-KHINTCHINE REPRESENTATION
════════════════════════════════════════════════════════════════════════════════

The Lévy-Khintchine formula states that ANY infinitely divisible distribution 
has a characteristic function of the form:

    log Φ(ω) = iγω - σ²ω²/2 + ∫[e^(iωx) - 1 - iωx·𝟙_{|x|<1}]ν(dx)

Felinger 1999 simplification (all jumps are POSITIVE delays, so no cutoff needed):

    log Φ(ω) = iγω - σ²ω²/2 + n·∫[e^(iωτ) - 1]f_s(τ)dτ
                ────   ─────────   ─────────────────────
                drift  Brownian    Poisson jumps (τ ≥ 0)

Parameters:
- γ = t₀ (hold-up time)
- σ² = 2DL/u² (dispersion variance)
- λ = n (rate parameter)
- ν(dτ) = f_s(τ)dτ (Lévy measure = sorption time PDF)

════════════════════════════════════════════════════════════════════════════════
KEY INSIGHTS FROM LÉVY FRAMEWORK
════════════════════════════════════════════════════════════════════════════════

1. INDEPENDENCE: The three components (drift, Brownian, Poisson) evolve
   independently. This is why Felinger can calculate variance by ADDITION:
   
   Var[total] = Var[Brownian] + Var[Poisson]
              = 2Dt₀(1+k')²/u  +  n·(m₂ - m₁²)

2. INFINITE DIVISIBILITY: Retention time distribution is infinitely divisible
   (can be written as sum of arbitrary number of i.i.d. random variables).
   This property is FUNDAMENTAL to Lévy processes.

3. LÉVY MEASURE: The sorption time distribution f_s(τ) is actually the Lévy
   measure ν restricted to positive jumps. Different f_s give different Lévy
   processes:
   - Exponential f_s → Gamma process (homogeneous surface)
   - Mixture of exponentials → Mixed Gamma process (heterogeneous)
   - Log-normal f_s → Log-normal subordinator

4. SUBORDINATION: In Lévy theory, the adsorption process is a "subordinator"
   (monotone increasing Lévy process). Time spent on surface only INCREASES,
   never decreases (ν supported on [0,∞) only).

5. MOMENTS WITHOUT SIMULATION: Lévy processes have cumulant generating function
   K(ω) = log Φ(iω). Derivatives at ω=0 give cumulants directly:
   
   κ₁ = K'(0) = mean
   κ₂ = K''(0) = variance
   κ₃ = K'''(0) = skewness numerator
   
   This is why Felinger can compute MOMENTS analytically (eqs 32-42)!
   
   ⚠️ CRITICAL DISTINCTION (see Dondi 2002):
   ─────────────────────────────────────────
   ANALYTICAL: Moments (mean, variance, skewness, kurtosis, plate height)
               → Always possible via derivatives of log Φ(ω) at ω=0
   
   NUMERICAL:  Full peak shape f(t)
               → Requires FFT inversion for most cases!
               → Analytical f(t) exists ONLY for special cases:
                 * Giddings-Eyring-Carmichael (1952): no dispersion → Gamma PDF
                 * Pure Gaussian: no adsorption → Normal PDF
               → Heterogeneous surfaces have NO closed-form f(t)!

════════════════════════════════════════════════════════════════════════════════
WHAT FELINGER DIDN'T KNOW IN 1999
════════════════════════════════════════════════════════════════════════════════

Felinger derived eq 13 from physical reasoning (convolution of independent
processes). But they didn't recognize this was a Lévy process! The Lévy
framework provides:

1. Rigorous mathematical foundation (Lévy-Khintchine theorem)
2. Connection to single-molecule experiments (Pasti 2005)
3. General theory for arbitrary jump distributions
4. Path properties (cadlag trajectories, no negative jumps)
5. Extension to infinite activity (∫ν(dτ) = ∞ for broad distributions)

This implementation makes the Lévy structure EXPLICIT through:
- Separation of γ (drift), σ² (Brownian), ν (Lévy measure)
- Direct calculation from Lévy-Khintchine formula
- Extensible sorption models = different Lévy measures

════════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.special import i1  # Modified Bessel function of the first kind
from dataclasses import dataclass
from typing import Optional, Callable, Union
from math import factorial

@dataclass
class ColumnParameters:
    """Chromatographic column parameters."""
    L: float  # Column length (cm or μm)
    u: float  # Mobile phase velocity (cm/s or μm/μs)
    D: float  # Axial dispersion coefficient (cm²/s or μm²/μs)
    
    @property
    def t0(self) -> float:
        """Hold-up time (column dead time)."""
        return self.L / self.u
    
    @property
    def N_disp(self) -> float:
        """Number of theoretical plates from dispersion only."""
        return self.L * self.u / (2 * self.D)


@dataclass
class SorptionModel:
    """Base class for sorption time distribution models.
    
    LÉVY INTERPRETATION:
    ────────────────────
    The sorption time distribution f_s(τ) is the LÉVY MEASURE ν(dτ) of the
    compound Poisson process representing adsorption-desorption events.
    
    In Lévy theory, ν(dτ) characterizes the jump distribution:
    - Support on [0,∞): Only positive delays (time spent on surface)
    - ∫ ν(dτ) < ∞: Finite activity (finite expected number of jumps)
    - ∫ τ ν(dτ): Mean jump size (average sorption time)
    - ∫ τ² ν(dτ): Second moment (controls variance)
    
    Different sorption models = Different Lévy measures:
    - Exponential: γ(dτ) = (1/τ̄)e^(-τ/τ̄)dτ  (Gamma process)
    - Two-site mixture: ν = p·ν₁ + (1-p)·ν₂  (Mixed Gamma)
    - Discrete: ν = Σ pᵢδ(τ-τᵢ)  (Compound Poisson with finite support)
    """
    
    def moment(self, order: int) -> float:
        """Calculate moment of sorption time distribution.
        
        For order r: m_r = ∫ τ^r f(τ) dτ = E[τ^r]
        
        LÉVY INTERPRETATION: These are moments of the Lévy measure ν(dτ).
        """
        raise NotImplementedError
    
    def mean(self) -> float:
        """Mean sorption time: m_1 = E[τ]."""
        return self.moment(1)
    
    def variance(self) -> float:
        """Variance: m_2 - m_1²."""
        return self.moment(2) - self.moment(1)**2
    
    def pdf(self, tau: np.ndarray) -> np.ndarray:
        """Probability density function f(τ)."""
        raise NotImplementedError
    
    def characteristic_function(self, omega: np.ndarray) -> np.ndarray:
        """Characteristic function Φ_s(ω) = E[exp(iωτ)].
        
        LÉVY INTERPRETATION:
        ────────────────────
        This is the characteristic function of the LÉVY MEASURE, which appears
        in the compound Poisson term:
        
            exp[n·(Φ_s(ω) - 1)] = exp[λ·∫(e^(iωτ) - 1)ν(dτ)]
        
        where Φ_s(ω) = ∫ e^(iωτ) f_s(τ)dτ
        
        The "-1" in the exponent is crucial: it's the Lévy-Khintchine
        compensator that ensures the process starts at 0.
        """
        raise NotImplementedError


class HomogeneousSorption(SorptionModel):
    """Homogeneous surface: exponential distribution (Giddings-Eyring).
    
    f(τ) = (1/τ̄) exp(-τ/τ̄)
    
    LÉVY INTERPRETATION:
    ────────────────────
    This is a GAMMA PROCESS (also called Gamma subordinator).
    
    The compound Poisson process with exponential jumps is equivalent to
    a continuous-time random walk that, in the limit n→∞, converges to
    a Gamma process with:
    - Shape parameter: α = n
    - Scale parameter: β = τ̄
    
    The Gamma process is the prototypical Lévy subordinator used in
    time change (subordination) applications.
    """
    
    def __init__(self, tau_mean: float):
        """
        Parameters
        ----------
        tau_mean : float
            Mean sorption time τ̄ (same units as time)
        """
        self.tau_mean = tau_mean
    
    def moment(self, order: int) -> float:
        """For exponential: m_r = r! τ̄^r."""
        return factorial(order) * (self.tau_mean ** order)
    
    def pdf(self, tau: np.ndarray) -> np.ndarray:
        """Exponential PDF."""
        return (1/self.tau_mean) * np.exp(-tau/self.tau_mean)
    
    def characteristic_function(self, omega: np.ndarray) -> np.ndarray:
        """CF for exponential: Φ(ω) = 1/(1 - iωτ̄)."""
        return 1.0 / (1.0 - 1j * omega * self.tau_mean)


class TwoSiteSorption(SorptionModel):
    """Two-site heterogeneous surface (Felinger 1999, Figure 4-7).
    
    Mixture of two exponential distributions:
    f(τ) = p·f_1(τ) + (1-p)·f_2(τ)
    
    LÉVY INTERPRETATION:
    ────────────────────
    This is a MIXTURE OF GAMMA PROCESSES.
    
    The Lévy measure is:
        ν(dτ) = p·ν₁(dτ) + (1-p)·ν₂(dτ)
    
    where ν₁ and ν₂ are exponential measures with rates 1/τ₁ and 1/τ₂.
    
    Physically: Each adsorption event randomly selects either a fast site
    (probability p) or slow site (probability 1-p), then draws a sorption
    time from the corresponding exponential distribution.
    
    This creates a DISCRETE LÉVY MEASURE with two atoms (Dirac masses)
    in the limit of rare events, or a continuous mixture for frequent events.
    
    KEY INSIGHT: Heterogeneity = Multiple components in Lévy measure!
    """
    
    def __init__(self, tau1: float, tau2: float, p: float):
        """
        Parameters
        ----------
        tau1 : float
            Mean sorption time on fast sites
        tau2 : float
            Mean sorption time on slow sites
        p : float
            Proportion of fast sites (0 < p < 1)
        """
        self.tau1 = tau1
        self.tau2 = tau2
        self.p = p
        
    def moment(self, order: int) -> float:
        """Weighted sum of exponential moments."""
        m1 = factorial(order) * (self.tau1 ** order)
        m2 = factorial(order) * (self.tau2 ** order)
        return self.p * m1 + (1 - self.p) * m2
    
    def pdf(self, tau: np.ndarray) -> np.ndarray:
        """Mixture of two exponentials."""
        f1 = (1/self.tau1) * np.exp(-tau/self.tau1)
        f2 = (1/self.tau2) * np.exp(-tau/self.tau2)
        return self.p * f1 + (1 - self.p) * f2
    
    def characteristic_function(self, omega: np.ndarray) -> np.ndarray:
        """Weighted sum of exponential CFs."""
        cf1 = 1.0 / (1.0 - 1j * omega * self.tau1)
        cf2 = 1.0 / (1.0 - 1j * omega * self.tau2)
        return self.p * cf1 + (1 - self.p) * cf2
    
    def worst_composition(self) -> dict:
        """Calculate worst stationary phase composition (eq 43).
        
        Returns proportion of slow sites that gives maximum plate height.
        """
        k1 = self.tau1  # Proportional to k'
        k2 = self.tau2
        
        p_worst = (k1 * np.sqrt(k2)) / (np.sqrt(k1) * (k1 + k2))
        
        return {
            'p_slow_worst': 1 - p_worst,
            'p_fast_worst': p_worst,
            'tau_ratio': k2 / k1
        }


class LogNormalSorption(SorptionModel):
    """Log-normal distribution from Gaussian energy distribution.
    
    From Frenkel equation: τ = τ₀ exp(E/RT)
    If E ~ N(E*, σ_E²) then τ has log-normal distribution.
    
    LÉVY INTERPRETATION:
    ────────────────────
    This is a LOG-NORMAL SUBORDINATOR.
    
    The Lévy measure has the form:
        ν(dτ) = (1/(τσ√(2π))) exp(-(log τ - μ)²/(2σ²)) dτ
    
    Key property: INFINITE ACTIVITY near τ=0
        ∫₀¹ ν(dτ) = ∞
    
    This means the process has INFINITELY MANY small jumps near zero.
    However, the integral ∫₀^∞ τ ν(dτ) < ∞, so mean jump size is finite.
    
    Physical interpretation: Continuous distribution of adsorption energies
    creates continuous distribution of sorption times, with many brief
    visits to shallow sites and rare long visits to deep sites.
    
    Unlike exponential (Gamma process), this does NOT simplify to a
    standard named Lévy process, but it's still a valid Lévy subordinator.
    """
    
    def __init__(self, tau_star: float, sigma_E: float, RT: float = 1.0):
        """
        Parameters
        ----------
        tau_star : float
            Median sorption time (τ* = τ₀ exp(E*/RT))
        sigma_E : float
            Standard deviation of energy distribution
        RT : float
            Gas constant × Temperature (default: 1.0 for normalized)
        """
        self.tau_star = tau_star
        self.sigma_E = sigma_E
        self.RT = RT
        self.q = np.exp((sigma_E / RT)**2)  # Convenience parameter
    
    def moment(self, order: int) -> float:
        """For log-normal: m_r = τ*^r · q^(r²/2) (eq 46 in Felinger 1999)."""
        return (self.tau_star ** order) * (self.q ** (order**2 / 2))
    
    def pdf(self, tau: np.ndarray) -> np.ndarray:
        """Log-normal PDF."""
        sigma = self.sigma_E / self.RT
        numerator = np.exp(-0.5 * ((np.log(tau / self.tau_star) / sigma)**2))
        denominator = tau * sigma * np.sqrt(2 * np.pi)
        return numerator / denominator
    
    def characteristic_function(self, omega: np.ndarray) -> np.ndarray:
        """No closed form - must integrate numerically."""
        raise NotImplementedError("Log-normal CF requires numerical integration")


class DiscreteSorption(SorptionModel):
    """Discrete sorption time distribution (arbitrary histogram).
    
    Used for Monte Carlo comparison or experimental distributions.
    
    LÉVY INTERPRETATION:
    ────────────────────
    This is a COMPOUND POISSON PROCESS with FINITE SUPPORT.
    
    The Lévy measure is a sum of Dirac masses:
        ν(dτ) = Σᵢ pᵢ δ(τ - τᵢ)
    
    This is the most general finite-activity Lévy subordinator.
    
    Properties:
    - Finite activity: ∫ ν(dτ) = Σ pᵢ = 1 < ∞
    - Jump process: Sample paths are piecewise constant (step functions)
    - Poisson arrivals: Jumps occur at Poisson times with rate λ = n
    - Random jump sizes: Each jump is τᵢ with probability pᵢ
    
    This is EXACTLY what Pasti 2005 analyzed for single-molecule experiments!
    Each binding event is a random draw from {τ₁, τ₂, ..., τₖ} with
    probabilities {p₁, p₂, ..., pₖ}.
    """
    
    def __init__(self, tau_values: np.ndarray, probabilities: np.ndarray):
        """
        Parameters
        ----------
        tau_values : ndarray
            Discrete sorption time values
        probabilities : ndarray
            Probability of each value (must sum to 1)
        """
        self.tau_values = np.array(tau_values)
        self.probabilities = np.array(probabilities)
        
        # Normalize probabilities
        self.probabilities = self.probabilities / np.sum(self.probabilities)
    
    def moment(self, order: int) -> float:
        """Discrete moment: Σ p_i · τ_i^r."""
        return np.sum(self.probabilities * (self.tau_values ** order))
    
    def pdf(self, tau: np.ndarray) -> np.ndarray:
        """Discrete distribution (sum of Dirac deltas - return histogram)."""
        # For visualization, create histogram
        hist, _ = np.histogram(self.tau_values, bins=len(tau), 
                               weights=self.probabilities, density=True)
        return hist
    
    def characteristic_function(self, omega: np.ndarray) -> np.ndarray:
        """Discrete CF: Σ p_i · exp(iω·τ_i)."""
        cf = np.zeros_like(omega, dtype=complex)
        for tau, prob in zip(self.tau_values, self.probabilities):
            cf += prob * np.exp(1j * omega * tau)
        return cf


class StochasticDispersiveChromatography:
    """
    Unified stochastic-dispersive chromatography model (Felinger 1999).
    
    Combines:
    - Random adsorption-desorption (stochastic)
    - Axial dispersion (Gaussian spreading)
    
    ANALYTICAL vs NUMERICAL:
    ────────────────────────
    ANALYTICAL (always possible):
    - Moments: mean, variance, skewness, kurtosis (via cumulants)
    - Plate number N, plate height H, optimum velocity
    - Peak characterization without computing f(t)
    
    NUMERICAL (required for most cases):
    - Full peak shape f(t) via FFT inversion of Φ(ω)
    - Only special cases have analytical f(t):
      * Giddings-Eyring (no dispersion) → Gamma distribution
      * Pure dispersion (no adsorption) → Normal distribution
      * Homogeneous + dispersion → Generalized Gamma (still complex)
    
    For heterogeneous surfaces, moments are exact but f(t) needs FFT!
    """
    
    def __init__(self, column: ColumnParameters, sorption: SorptionModel, n_ads: float):
        """
        Parameters
        ----------
        column : ColumnParameters
            Column properties (L, u, D)
        sorption : SorptionModel
            Sorption time distribution model
        n_ads : float
            Mean number of adsorption-desorption events
        """
        self.column = column
        self.sorption = sorption
        self.n_ads = n_ads
    
    def retention_time(self) -> float:
        """Mean retention time (eq 32): t_R = t₀(1 + k')."""
        m1 = self.sorption.mean()
        k_prime = self.n_ads * m1 / self.column.t0
        return self.column.t0 * (1 + k_prime)
    
    def variance(self) -> dict:
        """Variance components (eq 33).
        
        Returns
        -------
        dict with keys:
            'total': Total variance
            'kinetics': Variance from slow kinetics
            'dispersion': Variance from axial dispersion
        
        LÉVY INTERPRETATION:
        ────────────────────
        The total variance is the SUM of variances from independent Lévy
        components (by independence):
        
        Var[X] = Var[X₁] + Var[X₂] + Var[X₃]
        
        X₁ (drift): Var = 0 (deterministic)
        X₂ (Brownian): Var = σ² = 2Dt₀/u × (1+k')²
        X₃ (compound Poisson): Var = λ∫τ²ν(dτ) - (λ∫τν(dτ))²
                                   = n·m₂ - n²m₁² ≈ n(m₂-m₁²) for large n
        
        The (1+k')² factor in dispersion comes from time change: molecules
        spend total time t₀(1+k') in column, so dispersion accumulates over
        longer effective time.
        """
        m1 = self.sorption.mean()
        m2 = self.sorption.moment(2)
        
        # LÉVY COMPONENT 3: Compound Poisson variance
        # Var[Σᵢ τᵢ] where N~Poisson(n), τᵢ~f_s
        var_kinetics = self.n_ads * (m2 - m1**2)
        
        # LÉVY COMPONENT 2: Brownian variance (time-changed)
        k_prime = self.n_ads * m1 / self.column.t0
        var_dispersion = 2 * self.column.D * self.column.t0 * (1 + k_prime)**2 / self.column.u
        
        return {
            'total': var_kinetics + var_dispersion,
            'kinetics': var_kinetics,  # Jump variance
            'dispersion': var_dispersion  # Brownian variance
        }
    
    def plate_number(self) -> dict:
        """Number of theoretical plates (eq 34).
        
        1/N = 1/N_kinetics + 1/N_dispersion
        
        Returns
        -------
        dict with plate numbers and contributions
        """
        m1 = self.sorption.mean()
        m2 = self.sorption.moment(2)
        k_prime = self.n_ads * m1 / self.column.t0
        
        # Dispersion contribution (B-term in van Deemter)
        inv_N_disp = 2 * self.column.D / (self.column.u * self.column.L)
        
        # Kinetic contribution (C-term in van Deemter)
        inv_N_kinetics = (m2 - m1**2) / (self.n_ads * m1**2)
        
        inv_N_total = inv_N_disp + inv_N_kinetics
        
        return {
            'N_total': 1.0 / inv_N_total,
            'N_dispersion': 1.0 / inv_N_disp,
            'N_kinetics': 1.0 / inv_N_kinetics,
            'inv_N_total': inv_N_total,
            'inv_N_dispersion': inv_N_disp,
            'inv_N_kinetics': inv_N_kinetics
        }
    
    def plate_height(self) -> dict:
        """Plate height (eq 35): H = L/N.
        
        H = B/u + C·u  (van Deemter equation)
        """
        N = self.plate_number()
        m1 = self.sorption.mean()
        m2 = self.sorption.moment(2)
        k_prime = self.n_ads * m1 / self.column.t0
        
        # B and C terms
        B = 2 * self.column.D
        C = (m2 - m1**2) * self.column.L / (self.n_ads * m1**2)
        
        H_total = self.column.L / N['N_total']
        H_disp = B / self.column.u
        H_kinetics = C * self.column.u
        
        return {
            'H_total': H_total,
            'H_dispersion': H_disp,
            'H_kinetics': H_kinetics,
            'B_term': B,
            'C_term': C
        }
    
    def optimum_velocity(self) -> dict:
        """Optimum mobile phase velocity (eq 37): u_opt = √(B/C)."""
        H = self.plate_height()
        u_opt = np.sqrt(H['B_term'] / H['C_term'])
        H_min = 2 * np.sqrt(H['B_term'] * H['C_term'])
        
        return {
            'u_opt': u_opt,
            'H_min': H_min,
            'N_max': self.column.L / H_min
        }
    
    def skewness(self) -> float:
        """Peak skewness (eq 41): S = μ₃/σ³."""
        m1 = self.sorption.mean()
        m2 = self.sorption.moment(2)
        m3 = self.sorption.moment(3)
        
        var = self.variance()
        
        # Third central moment (kinetics only, dispersion contributes 0)
        mu3 = self.n_ads * (m3 - 3*m1*m2 + 2*m1**3)
        
        S = mu3 / (var['total'] ** 1.5)
        return S
    
    def excess(self) -> float:
        """Peak excess kurtosis (eq 42): Ex = μ₄/σ⁴ - 3."""
        m1 = self.sorption.mean()
        m2 = self.sorption.moment(2)
        m3 = self.sorption.moment(3)
        m4 = self.sorption.moment(4)
        
        var = self.variance()
        
        # Fourth central moment (kinetics contribution)
        mu4_kin = self.n_ads * (m4 - 4*m1*m3 + 6*m1**2*m2 - 3*m1**4)
        
        # Dispersion contribution (Gaussian has excess = 0, so adds 3σ⁴)
        mu4 = mu4_kin + 3 * var['dispersion']**2
        
        Ex = mu4 / (var['total'] ** 2) - 3
        return Ex
    
    def characteristic_function(self, omega: np.ndarray) -> np.ndarray:
        """Full CF including dispersion (eq 13).
        
        Φ(ω) = exp[iωt₀ - Dt₀ω²/(2u) + n·(Φ_s(ω) - 1)]
        
        LÉVY INTERPRETATION - CANONICAL DECOMPOSITION:
        ───────────────────────────────────────────────
        
        log Φ(ω) = iγω - σ²ω²/2 + λ∫[e^(iωτ) - 1]ν(dτ)
                   ─────  ─────────  ────────────────────
                   DRIFT  BROWNIAN   COMPOUND POISSON
        
        Components (independent Lévy processes):
        
        1. γ = t₀: Drift at constant velocity u
           Process: X₁(t) = u·t (deterministic)
           
        2. σ² = 2Dt₀/u: Brownian motion
           Process: X₂(t) ~ N(0, 2Dt)
           
        3. λ = n, ν(dτ) = f_s(τ)dτ: Compound Poisson jumps
           Process: X₃(t) = Σᵢ₌₁^N(t) τᵢ where N(t)~Poisson(λt), τᵢ~f_s
        
        Total: X(t) = X₁(t) + X₂(t) + X₃(t)
        
        This is the LÉVY-ITÔ DECOMPOSITION in action!
        """
        # LÉVY COMPONENT 1: Drift (deterministic translation)
        gamma = self.column.t0
        shift = np.exp(1j * omega * gamma)
        
        # LÉVY COMPONENT 2: Brownian motion (Gaussian spreading)
        sigma_squared = 2 * self.column.D * self.column.t0 / self.column.u
        dispersion = np.exp(-sigma_squared * omega**2 / 2)
        
        # LÉVY COMPONENT 3: Compound Poisson (random time delays)
        lambda_rate = self.n_ads
        cf_s = self.sorption.characteristic_function(omega)
        # Lévy-Khintchine form: λ∫[e^(iωτ) - 1]ν(dτ) = λ[Φ_s(ω) - 1]
        poisson = np.exp(lambda_rate * (cf_s - 1))
        
        # Independence: Multiply the three components
        return shift * dispersion * poisson
    
    def calculate_peak(self, n_points: int = 4096) -> tuple:
        """Calculate chromatographic peak by FFT inversion.
        
        ⚠️ NUMERICAL METHOD - NOT ANALYTICAL! ⚠️
        
        This uses FFT to numerically invert the characteristic function.
        The peak shape f(t) has NO closed-form analytical expression for
        most sorption models (except Giddings-Eyring-Carmichael 1952).
        
        Even though we can compute moments analytically (via derivatives),
        the full distribution requires numerical inversion.
        
        This is exactly what Pasti 2005 did - use the CF framework to get
        f(t) numerically while getting moments analytically.
        
        Parameters
        ----------
        n_points : int
            Number of FFT points
        
        Returns
        -------
        time : ndarray
            Time values
        peak : ndarray
            Peak intensity (probability density) - NUMERICAL APPROXIMATION
        """
        # Estimate time range
        t_R = self.retention_time()
        var = self.variance()['total']
        sigma = np.sqrt(var)
        
        # Time grid
        dt = 6 * sigma / n_points  # Cover ±3σ well
        t_max = t_R + 6 * sigma
        
        # Frequency grid
        omega_max = np.pi / dt
        omega = np.linspace(0, omega_max, n_points)
        
        # Calculate CF
        cf = self.characteristic_function(omega)
        
        # FFT inversion (same as pasti2005_levy_inversion.py)
        cf_extended = np.concatenate([cf, [0], np.conj(cf[-1:0:-1])])
        peak_complex = np.fft.ifft(cf_extended) * len(cf_extended) / np.sqrt(len(cf_extended))
        peak = np.real(peak_complex[:n_points])
        
        # Normalize
        peak = peak / (np.sum(peak) * dt)
        
        # Time axis
        time = np.arange(n_points) * dt
        
        return time, peak
    
    def summary(self) -> dict:
        """Generate comprehensive summary of chromatographic properties."""
        return {
            'retention_time': self.retention_time(),
            'variance': self.variance(),
            'plate_number': self.plate_number(),
            'plate_height': self.plate_height(),
            'optimum': self.optimum_velocity(),
            'skewness': self.skewness(),
            'excess': self.excess(),
            'retention_factor': self.n_ads * self.sorption.mean() / self.column.t0
        }


def demo_homogeneous_surface(save_fig=False):
    """Reproduce Figures 1-3 from Felinger 1999."""
    print("=" * 70)
    print("Demo: Homogeneous Surface (Figures 1-3)")
    print("=" * 70)
    
    # Parameters from Figure 1
    L = 25  # cm
    u = 0.5  # cm/s
    k_prime = 2
    n = 1000  # Fast kinetics
    
    # Calculate tau_mean from k' and n
    t0 = L / u  # 50 s
    tau_mean = k_prime * t0 / n  # 0.1 s
    
    sorption = HomogeneousSorption(tau_mean=tau_mean)
    
    # Vary diffusion coefficient
    D_values = np.logspace(-4, -1, 5)  # 10^-4 to 10^-1 cm²/s
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    for D in D_values:
        column = ColumnParameters(L=L, u=u, D=D)
        model = StochasticDispersiveChromatography(column, sorption, n)
        
        time, peak = model.calculate_peak(n_points=2048)
        
        summary = model.summary()
        label = f"D = {D:.0e} cm²/s, S = {summary['skewness']:.3f}"
        ax.plot(time, peak, label=label, linewidth=2)
    
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Probability Density')
    ax.set_title(f'Homogeneous Surface: n = {n}, k\' = {k_prime}')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    if save_fig:
        plt.savefig('felinger1999_fig1_homogeneous.png', dpi=300)
        print("\nSaved: felinger1999_fig1_homogeneous.png")
    plt.show()


def demo_two_site_heterogeneity(save_fig=False):
    """Reproduce Figures 4-7 from Felinger 1999."""
    print("\n" + "=" * 70)
    print("Demo: Two-Site Heterogeneous Surface (Figures 4-7)")
    print("=" * 70)
    
    # Parameters
    L = 25  # cm
    u = 0.5  # cm/s
    D = 0.001  # cm²/s
    tau_m = 0.005  # s (mobile phase)
    tau1 = 0.01  # s (fast sites)
    
    column = ColumnParameters(L=L, u=u, D=D)
    
    # Vary tau2/tau1 ratio
    ratios = [10, 100, 1000]
    p_values = np.linspace(0.001, 0.999, 200)
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Left: Minimum plate height vs composition
    ax = axes[0]
    for ratio in ratios:
        tau2 = ratio * tau1
        H_min_values = []
        
        for p in p_values:
            sorption = TwoSiteSorption(tau1, tau2, p)
            # Use high n to approach minimum
            n = 1000
            model = StochasticDispersiveChromatography(column, sorption, n)
            opt = model.optimum_velocity()
            H_min_values.append(opt['H_min'])
        
        ax.plot(1 - p_values, H_min_values, linewidth=2, 
                label=f'τ₂/τ₁ = {ratio}')
    
    ax.set_xlabel('Proportion of slow sites (1-p)')
    ax.set_ylabel('Minimum plate height H_min (cm)')
    ax.set_title('Worst Stationary Phase Composition (Fig 4)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xlim([0, 0.3])
    
    # Right: Skewness vs proportion of slow sites
    ax = axes[1]
    for ratio in ratios:
        tau2 = ratio * tau1
        skew_values = []
        
        for p in p_values:
            sorption = TwoSiteSorption(tau1, tau2, p)
            n = 10000  # High n for clear effect
            model = StochasticDispersiveChromatography(column, sorption, n)
            skew_values.append(model.skewness())
        
        ax.semilogy(1 - p_values, np.abs(skew_values), linewidth=2,
                    label=f'τ₂/τ₁ = {ratio}')
    
    ax.set_xlabel('Proportion of slow sites (1-p)')
    ax.set_ylabel('|Skewness|')
    ax.set_title('Peak Asymmetry (Fig 6 style)')
    ax.legend()
    ax.grid(True, alpha=0.3, which='both')
    ax.set_xlim([0, 0.01])
    
    plt.tight_layout()
    if save_fig:
        plt.savefig('felinger1999_two_site_analysis.png', dpi=300)
        print("\nSaved: felinger1999_two_site_analysis.png")
    plt.show()


def demo_comparison_with_monte_carlo(save_fig=False):
    """Compare Felinger 1999 analytical model with Monte Carlo from repository."""
    print("\n" + "=" * 70)
    print("Demo: Felinger 1999 vs Monte Carlo (Repository Parameters)")
    print("=" * 70)
    
    # Parameters matching script_column_run.py
    L = 2000  # μm
    u = 0.2  # μm/μs
    D = 0.05  # μm²/μs (estimate)
    
    tau1 = 10  # μs (fast sites)
    tau2 = 500  # μs (slow sites, 50x slower)
    p = 0.98  # 98% fast, 2% slow
    
    n_ads = 100  # Approximate number of adsorptions
    
    # Create model
    column = ColumnParameters(L=L, u=u, D=D)
    sorption = TwoSiteSorption(tau1, tau2, p)
    model = StochasticDispersiveChromatography(column, sorption, n_ads)
    
    # Calculate peak
    time, peak = model.calculate_peak(n_points=2048)
    
    # Get summary
    summary = model.summary()
    
    print("\nChromatographic Properties:")
    print(f"  Retention time: {summary['retention_time']:.1f} μs")
    print(f"  Retention factor k': {summary['retention_factor']:.2f}")
    print(f"  Total variance: {summary['variance']['total']:.1f} μs²")
    print(f"  Plate number N: {summary['plate_number']['N_total']:.1f}")
    print(f"  Plate height H: {summary['plate_height']['H_total']:.3f} μm")
    print(f"  Skewness: {summary['skewness']:.3f}")
    print(f"  Excess kurtosis: {summary['excess']:.3f}")
    
    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(time, peak, 'b-', linewidth=2.5, label='Felinger 1999 (Analytical)')
    ax.axvline(summary['retention_time'], color='r', linestyle='--', alpha=0.7,
               label=f'Mean: {summary['retention_time']:.0f} μs')
    
    ax.set_xlabel('Time (μs)')
    ax.set_ylabel('Probability Density')
    ax.set_title('Felinger 1999: Two-Site Model (Repository Parameters)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Add text box
    textstr = '\n'.join([
        f"N = {summary['plate_number']['N_total']:.0f}",
        f"k' = {summary['retention_factor']:.2f}",
        f"S = {summary['skewness']:.3f}",
    ])
    ax.text(0.95, 0.95, textstr, transform=ax.transAxes,
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    if save_fig:
        plt.savefig('felinger1999_repository_comparison.png', dpi=300)
        print("\nSaved: felinger1999_repository_comparison.png")
    print("\nNote: Compare this with Monte Carlo results from your repository!")
    plt.show()


if __name__ == '__main__':
    print("Felinger 1999: Stochastic-Dispersive Theory of Chromatography")
    print("=" * 70)
    
    demo_homogeneous_surface()
    demo_two_site_heterogeneity()
    demo_comparison_with_monte_carlo()
    
    print("\n" + "=" * 70)
    print("All demonstrations complete!")
    print("=" * 70)
