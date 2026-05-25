"""
    SEC.PoreEntryAnimation.py

    Single-molecule pore-entry animation: Knox sector geometry -> K_SEC -> LKM k.

    Complements ColumnSimulation.py (multi-particle elution) with a focused view of
    what happens at the grain scale: one molecule diffusing through a 5-grain assembly,
    entering and exiting pore sectors, accumulating dwell statistics.

    The simulation closes the loop:
        geometry -> K_SEC -> LKM mass-transfer rate k -> SDM n_pi

    Copyright (c) 2024-2025, Molass Community
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
plt.rcParams['animation.embed_limit'] = 512

from .ColumnElements import NewGrain, Particle, solvant_color
from .StationaryMove import get_next_position_impl


# ---------------------------------------------------------------------------
# Default geometry (2+1+2 staggered, matches 3D random close-packing ~0.64)
# ---------------------------------------------------------------------------

_DEFAULT_GRAIN_CENTERS = [
    (0.22, 0.20), (0.78, 0.20),   # bottom row
    (0.50, 0.50),                  # middle
    (0.22, 0.80), (0.78, 0.80),   # top row
]


def run_simulation(
    r_mol=0.03,
    R_grain=0.20,
    num_pores=3,
    grain_centers=None,
    W=1.0, H=1.0,
    D=0.003, dt=0.002,
    n_steps=10_000,
    v_drift=0.10,
    seed=42,
    k_ads=0.0,
    k_des=1.0,
):
    """
    Run a single-molecule Brownian simulation through a grain assembly.

    Parameters
    ----------
    r_mol : float
        Molecule radius.
    R_grain : float
        Grain radius.
    num_pores : int
        Number of pore sectors per grain.  Determines sector half-angle
        alpha = pi / (2 * num_pores) and Knox pore radius R_p = R_grain * alpha.
    grain_centers : list of (float, float), optional
        Centre coordinates of each grain.  Defaults to 2+1+2 staggered layout.
    W, H : float
        Simulation box width and height.
    D : float
        Diffusion coefficient.
    dt : float
        Time step.
    n_steps : int
        Number of simulation steps.
    v_drift : float
        Downward mobile-phase drift speed (mobile-phase steps only).
    seed : int
        Random seed.
    k_ads : float
        Langmuir adsorption rate (per unit time).  0 = pure SEC (no wall binding).
    k_des : float
        Langmuir desorption rate (per unit time).  K_ads = k_ads / k_des.

    Returns
    -------
    dict with keys:
        positions       : ndarray (n_steps+1, 2)
        states          : ndarray (n_steps+1,)  — grain index or -1 (mobile)
        wall_bound      : ndarray (n_steps+1,) bool — True when wall-adsorbed
        entry_times     : ndarray  — simulation time of each pore entry
        dwell_times     : ndarray  — total pore dwell duration (free + adsorbed)
        entry_grain_arr : ndarray  — which grain for each entry
        grains          : list of NewGrain
        R_p             : float    — Knox pore radius
        rho             : float    — r_mol / R_p
        K_SEC_theory    : float    — Knox (1-rho)^2 approximation
        T_total         : float
        K_ads_theory    : float    — k_ads / k_des equilibrium constant
        K_eff_theory    : float    — K_SEC_theory * (1 + K_ads_theory)
    """
    if grain_centers is None:
        grain_centers = _DEFAULT_GRAIN_CENTERS

    grains = [NewGrain(gid, center, R_grain, num_pores)
              for gid, center in enumerate(grain_centers)]

    R_p          = np.pi * R_grain / (2 * num_pores)
    rho          = r_mol / R_p
    K_SEC_theory = (1 - rho) ** 2

    rng   = np.random.default_rng(seed)
    sigma = np.sqrt(2 * D * dt)
    gc    = np.array([g.center for g in grains])

    pos      = np.array([W / 2, H * 0.90])
    in_grain = -1

    positions = np.zeros((n_steps + 1, 2))
    states    = np.full(n_steps + 1, -1, dtype=int)
    positions[0] = pos

    entry_times, dwell_starts, dwell_times, entry_grain_list = [], [], [], []
    wall_bound      = np.zeros(n_steps + 1, dtype=bool)
    wall_bound_flag = False   # True when molecule is adsorbed to the pore wall

    for step in range(n_steps):
        dx      = rng.normal(0, sigma, 2)
        new_pos = pos + dx

        if in_grain < 0:
            # Mobile phase: drift + reflective x walls + periodic y wrap
            new_pos[1] -= v_drift * dt

            if   new_pos[0] < 0: new_pos[0] = -new_pos[0]
            elif new_pos[0] > W: new_pos[0] =  2 * W - new_pos[0]

            if   new_pos[1] < 0: new_pos[1] += H
            elif new_pos[1] > H: new_pos[1] -= H

            dists = np.hypot(new_pos[0] - gc[:, 0], new_pos[1] - gc[:, 1])
            hit   = np.where(dists < grains[0].radius)[0]

            if len(hit) > 0:
                gi    = hit[0]
                grain = grains[gi]
                last_p = Particle(tuple(pos),     r_mol)
                this_p = Particle(tuple(new_pos), r_mol)
                ret    = this_p.enters_stationary(grain, last_particle=last_p)

                if ret is not None:
                    in_grain = gi
                    t_now    = step * dt
                    entry_times.append(t_now)
                    dwell_starts.append(t_now)
                    entry_grain_list.append(gi)
                else:
                    # Knox exclusion: radial bounce
                    cx, cy  = grain.center
                    outward = pos - np.array([cx, cy])
                    norm    = np.linalg.norm(outward)
                    if norm > 1e-9:
                        new_pos = np.array([cx, cy]) + outward / norm * (grain.radius + r_mol * 0.1)
                    else:
                        new_pos = pos.copy()
        else:
            # In-pore phase — two sub-states: free or wall-adsorbed
            if wall_bound_flag:
                # Wall-adsorbed: frozen in place, wait for desorption
                new_pos = pos.copy()
                if k_des > 0 and rng.random() < k_des * dt:
                    wall_bound_flag = False       # desorb -> free in pore
            else:
                # Free in pore: try to adsorb, or normal Brownian step
                if k_ads > 0 and rng.random() < k_ads * dt:
                    wall_bound_flag = True         # adsorb -> frozen at pore wall
                    new_pos = pos.copy()
                else:
                    grain    = grains[in_grain]
                    particle = Particle(tuple(pos), r_mol)
                    nx, ny, inmobile = get_next_position_impl(
                        particle, grain,
                        pos[0], pos[1],
                        new_pos[0], new_pos[1])
                    new_pos = np.array([nx, ny])

                    if inmobile:
                        dwell_times.append(step * dt - dwell_starts[-1])
                        in_grain        = -1
                        wall_bound_flag = False

        pos                = new_pos
        positions[step+1]  = pos
        states[step+1]     = in_grain
        wall_bound[step+1] = wall_bound_flag

    K_ads_theory = k_ads / k_des if k_des > 0 else float('inf')
    K_eff_theory = K_SEC_theory * (1 + K_ads_theory)

    return dict(
        positions       = positions,
        states          = states,
        wall_bound      = wall_bound,
        entry_times     = np.array(entry_times),
        dwell_times     = np.array(dwell_times),
        entry_grain_arr = np.array(entry_grain_list, dtype=int),
        grains          = grains,
        R_p             = R_p,
        rho             = rho,
        K_SEC_theory    = K_SEC_theory,
        T_total         = n_steps * dt,
        K_ads_theory    = K_ads_theory,
        K_eff_theory    = K_eff_theory,
    )


def get_pore_entry_animation(
    r_mol=0.03,
    R_grain=0.20,
    num_pores=3,
    grain_centers=None,
    W=1.0, H=1.0,
    D=0.003, dt=0.002,
    n_steps=10_000,
    v_drift=0.10,
    seed=42,
    k_ads=0.0,
    k_des=1.0,
    n_frames=200,
    interval=40,
    close_plot=True,
):
    """
    Create a pore-entry animation: single-molecule trajectory + live statistics.

    Runs a Brownian simulation first, then wraps the pre-computed trajectory in a
    FuncAnimation with three panels:

    - Left  : 2D grain assembly with molecule trajectory tail and colour-coded state
              (royalblue = mobile, orchid = free in pore, tomato = wall-adsorbed)
    - Top-right  : Cumulative pore-entry count N(t) with linear-rate overlay
    - Bottom-right : Dwell-time histogram with exponential fit

    Parameters
    ----------
    r_mol, R_grain, num_pores, grain_centers, W, H, D, dt, n_steps, v_drift, seed, k_ads, k_des
        Passed directly to `run_simulation`.
    n_frames : int
        Number of animation frames (default 200).
    interval : int
        Delay between frames in milliseconds (default 40).
    close_plot : bool
        If True, close the static figure after building the animation (prevents
        a duplicate static image appearing below the animation in notebooks).

    Returns
    -------
    ani : matplotlib.animation.FuncAnimation
    sim : dict
        Simulation result from `run_simulation` (positions, states, dwell_times, …).
    """
    sim = run_simulation(
        r_mol=r_mol, R_grain=R_grain, num_pores=num_pores,
        grain_centers=grain_centers, W=W, H=H,
        D=D, dt=dt, n_steps=n_steps, v_drift=v_drift, seed=seed,
        k_ads=k_ads, k_des=k_des,
    )

    positions    = sim['positions']
    states       = sim['states']
    wall_bound   = sim['wall_bound']
    entry_times  = sim['entry_times']
    dwell_times  = sim['dwell_times']
    grains       = sim['grains']
    T_total      = sim['T_total']

    stride   = max(1, n_steps // n_frames)
    tail_len = 30

    fig = plt.figure(figsize=(11, 5))
    gs  = fig.add_gridspec(2, 2, width_ratios=[1.15, 1], hspace=0.45, wspace=0.35)
    ax_main  = fig.add_subplot(gs[:, 0])
    ax_count = fig.add_subplot(gs[0,  1])
    ax_hist  = fig.add_subplot(gs[1,  1])

    ax_main.set_xlim(0, W); ax_main.set_ylim(0, H)
    ax_main.set_aspect('equal')
    ax_main.set_facecolor(solvant_color)
    ax_main.set_title('Brownian molecule in grain assembly', fontsize=9.5)
    for grain in grains:
        grain.draw(ax_main)

    traj_line, = ax_main.plot([], [], '-', color='royalblue', lw=0.8, alpha=0.65)
    mol_dot,   = ax_main.plot([], [], 'o',
                              markersize=max(3, int(r_mol * 120)), zorder=6)

    ax_count.set_xlabel('time t', fontsize=8.5)
    ax_count.set_ylabel('cumulative entries', fontsize=8.5)
    ax_count.set_title('Pore entry count N(t)', fontsize=9)
    count_line, = ax_count.plot([], [], 'k-', lw=1.4)
    rate_line,  = ax_count.plot([], [], 'r--', lw=1.1, label='linear fit')
    ax_count.legend(fontsize=8, loc='upper left')

    ax_hist.set_xlabel('dwell time', fontsize=8.5)
    ax_hist.set_ylabel('count', fontsize=8.5)
    ax_hist.set_title('Dwell-time distribution', fontsize=9)

    step_t  = np.arange(n_steps + 1) * dt
    count_t = np.searchsorted(entry_times, step_t)

    def _dwells_up_to(fi):
        t_now = fi * stride * dt
        n     = min(len(entry_times), len(dwell_times))
        idx   = np.where((entry_times[:n] + dwell_times[:n]) <= t_now)[0]
        return dwell_times[idx]

    def init():
        traj_line.set_data([], [])
        mol_dot.set_data([], [])
        count_line.set_data([], [])
        rate_line.set_data([], [])
        return traj_line, mol_dot, count_line, rate_line

    def update(fi):
        si    = fi * stride
        t_now = si * dt

        lo       = max(0, si - tail_len * stride)
        step_pts = max(1, stride // 8)
        pts      = positions[lo:si+1:step_pts]
        # Clip tail at last y-wrap to avoid diagonal lines across the box
        if len(pts) > 1:
            dy    = np.diff(pts[:, 1])
            wraps = np.where(np.abs(dy) > H * 0.5)[0]
            if len(wraps) > 0:
                pts = pts[wraps[-1] + 1:]
        traj_line.set_data(pts[:, 0], pts[:, 1])

        if   states[si] < 0:  color = 'royalblue'
        elif wall_bound[si]:  color = 'tomato'
        else:                 color = 'orchid'
        mol_dot.set_data([positions[si, 0]], [positions[si, 1]])
        mol_dot.set_color(color)

        t_slice = step_t[:si+1]
        n_slice = count_t[:si+1]
        count_line.set_data(t_slice, n_slice)
        ax_count.set_xlim(0, max(T_total * 0.05, t_now + 1e-6))
        ax_count.set_ylim(0, max(5, n_slice[-1] + 2))
        if count_t[si] >= 3 and t_now > 0:
            slope = count_t[si] / t_now
            rate_line.set_data([0, t_now], [0, slope * t_now])

        dw = _dwells_up_to(fi)
        ax_hist.cla()
        ax_hist.set_xlabel('dwell time', fontsize=8.5)
        ax_hist.set_ylabel('count', fontsize=8.5)
        ax_hist.set_title(f'Dwell-time distribution  (n={len(dw)})', fontsize=9)
        if len(dw) >= 3:
            bins  = np.linspace(0, dw.max() * 1.1 + 1e-9, 20)
            ax_hist.hist(dw, bins=bins, color='orchid', edgecolor='white', alpha=0.8)
            mu    = dw.mean()
            x_fit = np.linspace(0, dw.max() * 1.1, 100)
            y_fit = len(dw) * (bins[1] - bins[0]) / mu * np.exp(-x_fit / mu)
            ax_hist.plot(x_fit, y_fit, 'r-', lw=1.2, label=f'Exp(1/{mu:.2f})')
            ax_hist.legend(fontsize=7.5)

        return traj_line, mol_dot, count_line, rate_line

    plt.tight_layout()
    plt.subplots_adjust(top=0.93)
    title = 'Pore entry animation -- grain-sector geometry'
    if k_ads > 0:
        title += f'  (Langmuir: k_ads={k_ads}, k_des={k_des})'
    plt.suptitle(title, fontsize=10)

    ani = FuncAnimation(fig, update, frames=n_frames,
                        init_func=init, blit=False, interval=interval)

    if close_plot:
        plt.close(fig)

    return ani, sim
