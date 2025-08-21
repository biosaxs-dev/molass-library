"""
    Stochastic.ColumnSimulation.py

    Copyright (c) 2024-2025, Molass Community
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.widgets import Button
from matplotlib.animation import FuncAnimation
plt.rcParams['animation.embed_limit'] = 512     # https://stackoverflow.com/questions/52778505/matplotlib-set-the-animation-rc-parameter
from .ColumnElements import Particle
from .ColumnStructure import plot_column_structure

def get_animation(num_frames=None, interval=100, seed=None, close_plot=True, return_init=False, fig_check=False, blit=False, use_tqdm=True, large_only=False, debug=False):
    """
    """
    ymin, ymax = 0, 1
    xmin, xmax = 0.35, 0.65

    num_pores = 16
    rs = 0.04

    if seed is not None:
        np.random.seed(seed)

    psizes = np.array([5, 2.5, 2])
    markersizes = np.array([5, 3, 2])
    pcolors = ["green", "blue", "red"]
    uv_absorbance_ratios = np.array([1.0, 1.5, 2.0])
    num_species_particles = 500
    ptype_indeces = np.array(list(np.arange(len(psizes)))*num_species_particles)
    np.random.shuffle(ptype_indeces)
    large_indeces = np.where(ptype_indeces == 0)[0]
    middle_indeces = np.where(ptype_indeces == 1)[0]
    small_indeces = np.where(ptype_indeces == 2)[0]
    num_particles = len(ptype_indeces)
    # print("ptype_indeces=", ptype_indeces)
    print("num_particles=", num_particles)
    grain_references = -np.ones(num_particles, dtype=int)

    init_pxv = np.linspace(xmin+0.02, xmax-0.02, num_particles)
    init_pyv = np.ones(num_particles)*ymax

    if num_frames is None:
        num_frames = 400
    delta = ymax/num_frames
    du = delta*5    # Increased to enhance particle movement
    particle_scale = 1/1000  # [10, 5, 1] => [0.01, 0.005, 0.001]
    radius_map = psizes*particle_scale
    print("radius_map=", radius_map)    
    radiusv = np.array([radius_map[i] for i in ptype_indeces])
    if debug:
        print("radiusv=", radiusv)
    rv = radiusv + rs

    figsize = (12,10)
    fig = plt.figure(figsize=figsize)
    gs = GridSpec(2, 12)
    ax1 = fig.add_subplot(gs[:,0:3])

    ax2 = fig.add_subplot(gs[:,3:6])
    ax2.yaxis.set_visible(False)
    ax2.set_xlim(0, 80)
    ax2.set_ylim(0, 1)

    ax3 = fig.add_subplot(gs[0,6:12])
    ax4 = fig.add_subplot(gs[1,6:12])
    for ax in (ax3, ax4):
        ax.set_ylim(0, 40)
        ax.set_xlim(100, num_frames)

    suptitle_fmt = "SEC-SAXS Illustrative 2D Animation: %3d"
    suptitle_text = fig.suptitle(suptitle_fmt % 0, fontsize=16, y=0.99)
    print(suptitle_text)
    ax1.set_title("Column Image")
    ax2.set_title("Histogram by Y-Axis") 
    ax3.set_title("UV Histogram by Retension Time (Frames)")
    ax4.set_title("X-Ray Histogram by Retension Time (Frames)")

    # Add CC BY 4.0 license notice as an icon or text
    fig.text(
        0.99, 0.01,  # Position: bottom-right corner
        "© 2025, Molass Community, CC BY 4.0  ",  # License text
        fontsize=8, color="gray", ha="right", va="bottom", alpha=0.7
    )

    if fig_check:
        fig.tight_layout()
        return

    pause = False
    def on_click(event):
        nonlocal pause
        print('on_click')
        if event.inaxes != ax1:
            return
        pause ^= True
        
    fig.canvas.mpl_connect('button_press_event', on_click)

    if False:
        button_ax = fig.add_axes([0.85, 0.05, 0.1, 0.03])
        def draw_slice_states(event):
            from Stochastic.ColumnSliceStates import draw_slice_states_impl
            print("draw_slice_states")
            if event.inaxes != button_ax:
                return
            draw_slice_states_impl(fig, ax2, grains, pxv, pyv, inmobile_states)

        debug_btn = Button(button_ax, 'Draw Slice States', hovercolor='0.975')
        debug_btn.on_clicked(draw_slice_states)

    grains = plot_column_structure(ax1, xmin, xmax, ymin, ymax, num_pores, rs)
    xxv = []
    yyv = []
    for grain in grains:
        x, y = grain.center
        xxv.append(x)
        yyv.append(y)
    xxv = np.array(xxv)
    yyv = np.array(yyv)

    particles = []
    for k, x in enumerate(init_pxv):
        m = ptype_indeces[k]
        particle, = ax1.plot(x, ymax, "o", markersize=markersizes[m], color=pcolors[m])
        particles.append(particle)

    fig.tight_layout()
    fig.subplots_adjust(left=0.02, bottom=0.06)    # to allow for the license text
    # ax2.set_position([0.29, 0.06, 0.17, 0.87])    # [left, bottom, width, height]
    ax2.set_position([0.25, 0.06, 0.223, 0.87])    # [left, bottom, width, height]

    inmobile_states = np.ones(num_particles, dtype=bool)
    pxv = init_pxv.copy()
    pyv = init_pyv.copy()

    def touchable_indeces(inmobile_states, last_pxv, last_pyv, debug=False):
        indeces = []
        bounce_scales = []
        for k, (mobile, x, y) in enumerate(zip(inmobile_states, pxv, pyv)):
            distv = rv[k] - np.sqrt((xxv - x)**2 + (yyv - y)**2)
            w = np.where(distv > 0)[0]
            if len(w) == 0:
                inmobile_states[k] = True
                grain_references[k] = -1
            else:
                j = w[0]
                # print("w=", w, "j=", j, "distv=", distv[j], "x,y=", x, y)
                grain = grains[j]
                last_particle = Particle((last_pxv[k], last_pyv[k]), radiusv[k])
                this_particle = Particle((x, y), radiusv[k])
                ret = this_particle.enters_stationary(grain, last_particle=last_particle, debug=debug)
                if mobile:
                    if ret is None:
                        indeces.append((k, j))
                        bounce_scales.append(distv[j])
                        inmobile_states[k] = True
                        grain_references[k] = -1
                    else:
                        inmobile_states[k] = False
                        grain_references[k] = j
                else:
                    # ret = this_particle.exits_stationary(grain, last_particle=last_particle, debug=debug)
                    # task: restrict stationary move
                    pass
                
        if len(indeces) == 0:
            return None
        
        touchables, porous_indeces = np.array(indeces, dtype=int).T
        if debug:
            print("(1) touchables=", touchables)
            print("(1) inmobile_states=", ''.join(map(lambda b: '%d' % b, inmobile_states)))
            print("(1) staying_grains =", ''.join(map(lambda j: '.' if j < 0 else chr(97+j), grain_references)))
        bounce_scales = np.array(bounce_scales)
        dxv = pxv[touchables] - xxv[porous_indeces]
        dyv = pyv[touchables] - yyv[porous_indeces]
        dlenv = np.sqrt(dxv**2 + dyv**2)
        scale = bounce_scales/dlenv*2
        bxv = dxv*scale
        byv = dyv*scale
        return touchables, np.array([bxv, byv]).T

    cancel_debug = False

    def compute_next_positions(debug=False):
        nonlocal pxv, pyv, cancel_debug
        if debug:
            print("(2) inmobile_states=", ''.join(map(lambda b: '%d' % b, inmobile_states)))
        last_pxv = pxv.copy()
        last_pyv = pyv.copy()
        dxv, dyv = np.random.normal(0, delta, (2,num_particles))
        pxv += dxv
        exceed_left = pxv < xmin
        pxv[exceed_left] = 2*xmin - pxv[exceed_left]
        exceed_right = pxv > xmax
        pxv[exceed_right] = 2*xmax - pxv[exceed_right]
        pyv += dyv
        pyv[inmobile_states] -= du
        ret = touchable_indeces(inmobile_states, last_pxv, last_pyv)
        if ret is not None:
            # modify mobile move
            touchables, bounce_vects = ret
            pxv[touchables] += bounce_vects[:,0]
            pyv[touchables] += bounce_vects[:,1]

        # modify statinary move
        stationary_indeces = np.where(np.logical_not(inmobile_states))[0]
        # if not old_grain:
        for i in stationary_indeces:
            particle = Particle((pxv[i], pyv[i]), radiusv[i])
            grain = grains[grain_references[i]]
            nx, ny, state = particle.stationary_move(grain, last_pxv[i], last_pyv[i], pxv[i], pyv[i], debug=False)
            pxv[i] = nx
            pyv[i] = ny
            inmobile_states[i] = state

        exceed_left = pxv < xmin
        pxv[exceed_left] += -2*dxv[exceed_left]
        exceed_right = pxv > xmax
        pxv[exceed_right] += -2*dxv[exceed_right]

        exceed_top = pxv > ymax
        pyv[exceed_top] += -2*dyv[exceed_top]
        if debug and not cancel_debug:
            print("ret=", ret)
            with plt.Dp():
                fig, ax = plt.subplots(figsize=(9,9))
                plot_column_structure(ax)
                U = pxv - last_pxv
                V = pyv - last_pyv
                ax.quiver(last_pxv, last_pyv, U, V, width=0.002,
                            angles='xy', scale_units='xy', scale=1, color="blue")

                if ret is not None:
                    X = pxv[touchables] - bounce_vects[:,0]
                    Y = pyv[touchables] - bounce_vects[:,1]
                    U = 2*bounce_vects[:,0]
                    V = 2*bounce_vects[:,1]
                    ax.quiver(X, Y, U, V, width=0.002,
                            angles='xy', scale_units='xy', scale=1, color="red")

                fig.tight_layout()
                reply = plt.show()
                if not reply:
                    cancel_debug = True
        if debug:
            print("(3) inmobile_states=", ''.join(map(lambda b: '%d' % b, inmobile_states)))
        return pxv, pyv


    y_margen = 1e-6
    y_axis_bins = np.linspace(ymin, ymax+y_margen, 100)
    x_axis_bins = np.arange(num_frames)
    # horizontal_bins = 50
    horizontal_bar_containers = []
    vertical_bar_containers_uv = []
    vertical_bar_containers_xr = []

    x_hist_large = np.zeros(len(x_axis_bins))
    x_hist_middle = np.zeros(len(x_axis_bins))
    x_hist_small = np.zeros(len(x_axis_bins))
    x_hist_list = [x_hist_large, x_hist_middle, x_hist_small]
    y_hist_list = [None]*3
    delta_y = y_axis_bins[1] - y_axis_bins[0]

    def compute_histogram_data(i, add_containers=False):
        pyv_large = pyv[large_indeces]
        pyv_middle = pyv[middle_indeces]
        pyv_small = pyv[small_indeces]

        y_hist_large = np.histogram(pyv_large, bins=y_axis_bins)[0]
        y_hist_middle = np.histogram(pyv_middle, bins=y_axis_bins)[0]
        y_hist_small = np.histogram(pyv_small, bins=y_axis_bins)[0]
        y_hist_list[0] = y_hist_large
        y_hist_list[1] = y_hist_middle
        y_hist_list[2] = y_hist_small
        x_hist_large[i] = np.where(np.logical_and(pyv_large > -delta_y, pyv_large < +delta_y))[0].shape[0]
        x_hist_middle[i] = np.where(np.logical_and(pyv_middle > -delta_y, pyv_middle < +delta_y))[0].shape[0]
        x_hist_small[i] = np.where(np.logical_and(pyv_small > -delta_y, pyv_small < +delta_y))[0].shape[0]
        
        if add_containers:
            for hist, color in zip(y_hist_list, pcolors):
                print("color=", color)
                _, _, bar_container = ax2.hist(hist, y_axis_bins, lw=1,
                                        ec="yellow", color=color, alpha=0.5, orientation='horizontal')     #  
                horizontal_bar_containers.append(bar_container)
            for hist, color in zip(x_hist_list, pcolors):
                _, _, bar_container = ax3.hist(hist, x_axis_bins, lw=1,
                                        ec="yellow", color=color, alpha=0.5)
                vertical_bar_containers_uv.append(bar_container)
            for hist, color in zip(x_hist_list, pcolors):
                _, _, bar_container = ax4.hist(hist, x_axis_bins, lw=1,
                                        ec="yellow", color=color, alpha=0.5)
                vertical_bar_containers_xr.append(bar_container)

        for hist, container in zip(y_hist_list, horizontal_bar_containers):
            for count, rect in zip(hist, container.patches):
                rect.set_width(count)
        for k, (hist, container) in enumerate(zip(x_hist_list, vertical_bar_containers_uv)):
            ratio = uv_absorbance_ratios[k]
            for count, rect in zip(hist, container.patches):
                rect.set_height(count * ratio)
        for hist, container in zip(x_hist_list, vertical_bar_containers_xr):
            for count, rect in zip(hist, container.patches):
                rect.set_height(count)

    compute_histogram_data(0, add_containers=True)
    """
    bar_patches[0:3] : horizontal_bar_containers
    bar_patches[3:6] : vertical_bar_containers_uv
    bar_patches[6:9] : vertical_bar_containers_xr
    """
    bar_patches = []
    bar_patch_lengths = []
    bar_patch_cum_indices = [0]
    for container in (horizontal_bar_containers
                      + vertical_bar_containers_uv
                      + vertical_bar_containers_xr):
        bar_patches += container.patches
        bar_patch_lengths.append(len(container.patches))
        bar_patch_cum_indices.append(len(bar_patches))
    print("len(bar_patches)=", len(bar_patches))
    print("bar_patch_lengths=", bar_patch_lengths)
    print("bar_patch_cum_indices=", bar_patch_cum_indices)

    if return_init:
        return

    if large_only:
        animate_patches = []
        for k in [0]:
            for i in np.arange(bar_patch_cum_indices[k], bar_patch_cum_indices[k+1]):
                animate_patches.append(bar_patches[i])
    else:
        animate_patches = bar_patches

    def animate(i):
        if i > 50:
            nonlocal pause
            # pause = True
            pass
        if not pause:
            compute_next_positions()
            compute_histogram_data(i)
            suptitle_text.set_text(suptitle_fmt % i)
            for k, p in enumerate(particles):
                p.set_data(pxv[k:k+1], pyv[k:k+1])
        return particles + animate_patches

    def init():
        nonlocal pxv, pyv, rv
        pxv = init_pxv.copy()
        pyv = init_pyv.copy()
        # np.random.shuffle(ptype_indeces)
        radiusv = np.array([radius_map[i] for i in  ptype_indeces])
        if debug:
            print("init: radiusv=", radiusv)
        rv = radiusv + rs
        return animate(0)

    if use_tqdm:
        # https://stackoverflow.com/questions/60998231/python-how-to-make-tqdm-print-one-line-of-progress-bar-in-shell
        import sys
        from tqdm import tqdm
        frames = tqdm(range(num_frames))
    else:
        frames = num_frames
    anim = FuncAnimation(fig, animate, init_func=init,
                            frames=frames, interval=interval, blit=blit)

    if close_plot:
        plt.close() # Close the figure to prevent it from displaying in a static form

    return anim