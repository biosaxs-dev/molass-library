"""
    Stochastic.ColumnSimulation.py

    Copyright (c) 2024-2025, SAXS Team, KEK-PF
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import Rectangle, Circle, Wedge
from matplotlib.animation import FuncAnimation
plt.rcParams['animation.embed_limit'] = 512     # https://stackoverflow.com/questions/52778505/matplotlib-set-the-animation-rc-parameter

solvant_color = "lightcyan"

class SolidGrain:
    def __init__(self, id_, center, radius, poreradius, poredist):
        self.id_ = id_
        self.center = np.asarray(center)
        self.radius = radius
        self.poreradius = poreradius
        self.poredist = poredist
        self.compute_poreentries()

    def compute_poreentries(self):
        entry_edges = []
        for dy in [-self.poredist, 0, self.poredist]:
            for y in [dy - self.poreradius, dy + self.poreradius]:
                dx = np.sqrt(self.radius**2 - y**2)
                for x in [-dx, dx]:
                    entry_edges.append(np.arctan2(y, x))
        entry_edges = sorted(entry_edges)
        entries = []
        entries.append((entry_edges[-1], entry_edges[0]))
        for k in range(len(entry_edges)//2-1):
            entries.append((entry_edges[2*k+1], entry_edges[2*k+2]))
        self.entries = np.array(entries)

    def draw_entries(self, ax):
        for entry in self.entries:
            points = np.array([self.center + self.radius*np.array([np.cos(r), np.sin(r)]) for r in entry])
            ax.plot(*points.T)

    def draw(self, ax, color=None, alpha=1):
        p = Circle(self.center, self.radius, color=color, alpha=alpha)
        ax.add_patch(p)
        cx, cy = self.center
        for dy in [-self.poredist, 0, self.poredist]:
            p = Rectangle((cx-self.radius, cy-self.poreradius+dy), self.radius*2, self.poreradius*2, color=solvant_color)
            ax.add_patch(p)
        p = Rectangle((cx-self.poreradius, cy-self.radius*0.9), self.poreradius*2, self.radius*1.8, color=color)
        ax.add_patch(p)

    def get_point_from_angle(self, angle):
        return self.center + np.array([np.cos(angle), np.sin(angle)])*self.radius

    def get_entry_including(self, angles, debug=False):
        if angles[0] > angles[1]:
            angles = np.flip(angles)
        w = np.where(np.logical_and(self.entries[:,0] < angles[0], angles[1] < self.entries[:,1]))[0]
        if debug:
            print('get_entry_including: ', self.id_, angles, w)
        if len(w) == 0:
            return None
        else:
            return w[0]

    def compute_bounce_vector(self, particle):
        pass

    def compute_inpore_nextpos(self, particle):
        pass

class Particle:
    def __init__(self, center, radius):
        self.center = np.asarray(center)
        self.radius = radius

    def draw(self, ax, color=None, alpha=1):
        p = Circle(self.center, self.radius, color=color, alpha=alpha)
        ax.add_patch(p)

    def enters_stationary(self, grain, last_particle=None, return_point_info=False, ax=None, debug=False):
        from molass_legacy.KekLib.CircleGeometry import get_intersections, circle_line_segment_intersection
        if self.radius >= grain.poreradius:
            if debug:
                # print("self.radius(%g) >= grain.poreradius(%g)" % (self.radius, grain.poreradius))
                pass
            return None

        ret = get_intersections(*self.center, self.radius, *grain.center, grain.radius)
        if debug:
            print("enters_stationary (1): ", grain.id_, ret, self.center, grain.center)
        if False:
            import molass_legacy.KekLib.DebugPlot as plt
            print("self.center=", self.center, "self.radius=", self.radius)
            with plt.Dp():
                fig, ax = plt.subplots()
                ax.set_title("enters_stationary debug")
                ax.set_aspect("equal")
                grain.draw(ax, alpha=0.5)
                self.draw(ax)
                ax.plot(*self.center, "o", color="black", markersize=1)
                fig.tight_layout()
                reply = plt.show()
                assert reply

        if ret is None:
            if last_particle is None:
                return None
            intersections = circle_line_segment_intersection(grain.center, grain.radius, self.center, last_particle.center, full_line=False)
            for point in intersections:
                tp = Particle(point, self.radius)
                tp_ret = tp.enters_stationary(grain)
                if debug:
                    print("tp_ret=", tp_ret)
                if tp_ret is not None:
                    if ax is not None:
                        ax.plot(point[0], point[1], "o", color="yellow")
                    return tp_ret
            return None
        
        if debug:
            print("enters_stationary (2): ", grain.id_)

        v1 = np.asarray(ret[0]) - grain.center
        v2 = np.asarray(ret[1]) - grain.center
        angles = []
        for v in [v1,v2]:
            r = np.arctan2(v[1], v[0])      # np.atan2(y, x)
            angles.append(r)

        if return_point_info:
            return angles, ret

        i = grain.get_entry_including(angles)
        if i is None:
            return None

        return angles, ret, i

    def stationary_move(self, grain, last_px, last_py, px, py, debug=False):

        def get_next_position():
            from importlib import reload
            import molass.Stochastic.StationaryMove as sm
            reload(sm)
            from molass.Stochastic.StationaryMove import get_next_position_impl
            debug_info = (fig, ax) if debug else None
            nx, ny, state = get_next_position_impl(self, grain, last_px, last_py, px, py, debug_info=debug_info)
            if debug:
                fig.canvas.draw_idle()
            return nx, ny, state

        if debug:
            # import molass_legacy.KekLib.DebugPlot as plt
            # task: new verion of DebugPlot
            extra_button_specs = [
                ("Next", get_next_position),
            ]
            fig, ax = plt.subplots()
            ax.set_title("stationary_move debug")
            ax.set_aspect("equal")
            grain.draw(ax)
            dx = px - last_px
            dy = py - last_py
            vlen = np.sqrt(dx**2 + dy**2)
            ax.arrow(x=last_px, y=last_py, dx=dx, dy=dy, width=0.0005, head_width=0.002, length_includes_head=True,
                        head_length=0.2*vlen, color='black', alpha=0.5)
            self.draw(ax, alpha=0.5)
            cx, cy = grain.center
            r = grain.radius * 1.2
            ax.set_xlim(cx - r, cx + r)
            ax.set_ylim(cy - r, cy + r)
            fig.tight_layout()
            plt.show()

        return get_next_position()

class NewGrain(SolidGrain):
    def __init__(self, id_, center, radius, num_pores):
        self.id_ = id_
        self.center = center
        self.radius = radius
        self.num_pores = num_pores
        self.poreradius = np.pi*radius/(2*num_pores)
        # print("poreradius=", self.poreradius)
        self.x = np.ones(num_pores*2)
        self.colors = ['lavender', 'gray'] * num_pores
        self.compute_poreentries()

    def compute_poreentries(self):
        unit_angle = 2*np.pi/self.num_pores
        half_angle = unit_angle/2
        entries = []
        wedge_rad_pairs = []
        for i in range(self.num_pores):
            angle = i*unit_angle
            entries.append((angle, angle+half_angle))
            wedge_rad_pairs.append((angle, angle+half_angle))
            wedge_rad_pairs.append((angle+half_angle, angle+half_angle*2))
        self.entries = np.array(entries)
        self.wedge_rad_pairs = wedge_rad_pairs

    def draw(self, ax):
        # task: use patches.Wedge instead
        # ax.pie(self.x, colors=self.colors, radius=self.radius, center=self.center)
        draw_wedges(ax, self.center, self.radius, self.wedge_rad_pairs, self.colors)

def new_grain_unit_test():
    # import molass_legacy.KekLib.DebugPlot as plt

    radius = 0.2
    num_pores = 10
    colors = ['gray', 'pink'] * num_pores
    print("entry lenght=", radius*np.pi/num_pores)
    grain = NewGrain((0, 0), (0.5, 0.5), radius, num_pores)
    p0 = Particle((0.33, 0.7), 0.05)
    p1 = Particle((0.35, 0.65), 0.05)
    p2 = Particle((0.7, 0.7), 0.025)
    p3 = Particle((0.64, 0.64), 0.025)
    p4 = Particle((0.75, 0.55), 0.025)
    p5 = Particle((0.65, 0.52), 0.025)
    p6 = Particle((0.65, 0.33), 0.025)
    p7 = Particle((0.57, 0.36), 0.025)

    fig, ax = plt.subplots(figsize=(5,5))
    ax.set_aspect('equal')
    back = Rectangle((0.1, 0), 0.8, 1, color=solvant_color)
    ax.add_patch(back)
    grain.draw(ax)

    last_particle = None
    for k, particle in enumerate([p0, p1, p2, p3, p4, p5, p6, p7]):
        i, j = divmod(k,2)
        if j == 0:
            last_particle = None
        particle.draw(ax, alpha=0.3, color='C%d' % i)
        ret = particle.enters_stationary(grain, last_particle=last_particle, ax=ax)
        print([k], ret)
        if ret is not None:
            angles, points, i = ret
            for angle, point in zip(angles, points):
                ax.plot(*point, "o", color="yellow")
                ax.plot(*grain.get_point_from_angle(angle), "o", color="red", markersize=3)
        last_particle = particle

    grain.draw_entries(ax)

    ax.set_xlim(0,1)
    ax.set_ylim(0,1)
    fig.tight_layout()
    plt.show()

def grain_particle_test():
    # import molass_legacy.KekLib.DebugPlot as plt

    grain  = SolidGrain((0,0), (0.5,0.5), 0.2, 0.03, 0.12)
    p0 = Particle((0.33, 0.7), 0.05)
    p1 = Particle((0.35, 0.65), 0.05)
    p2 = Particle((0.7, 0.7), 0.025)
    p3 = Particle((0.67, 0.63), 0.025)
    p4 = Particle((0.75, 0.5), 0.025)
    p5 = Particle((0.65, 0.5), 0.025)
    p6 = Particle((0.62, 0.3), 0.025)
    p7 = Particle((0.6, 0.38), 0.025)

    fig, ax = plt.subplots(figsize=(5,5))
    ax.set_aspect('equal')

    back = Rectangle((0.1, 0), 0.8, 1, color=solvant_color)
    ax.add_patch(back)

    grain.draw(ax, color="gray")

    last_particle = None
    for k, particle in enumerate([p0, p1, p2, p3, p4, p5, p6, p7]):
        i, j = divmod(k,2)
        if j == 0:
            last_particle = None
        particle.draw(ax, alpha=0.3, color='C%d' % i)
        ret = particle.enters_stationary(grain, last_particle=last_particle, ax=ax)
        print([k], ret)
        if ret is not None:
            angles, points, i = ret
            for angle, point in zip(angles, points):
                ax.plot(*point, "o", color="yellow")
                ax.plot(*grain.get_point_from_angle(angle), "o", color="red", markersize=3)
        last_particle = particle

    grain.draw_entries(ax)

    fig.tight_layout()
    plt.show()

def draw_wedges(ax, center, radius, rad_pairs, colors):
    scale = 180/np.pi
    for (r1, r2), c in zip(rad_pairs, colors):
        wedge = Wedge(center, radius, scale*r1, scale*r2, color=c)
        ax.add_patch(wedge)

def get_animation(figsize=None, use_tqdm=True, num_frames=None, close_plot=True, fig_check=False, debug=False):
    # import molass_legacy.KekLib.DebugPlot as plt
    from matplotlib.widgets import Button

    save_gif = False
    smart_phone = False
    old_grain = False
    enbale_slice_drawing = True

    ymin, ymax = 0, 1
    xmin, xmax = 0.3, 0.7

    xm = 0.01
    ym = 0.03
    rs = 0.06
    if old_grain:
        pyshift = 0.03
        rp = 0.009
    else:
        num_pores = 32

    circle_cxv = np.linspace(xmin, xmax, 7)
    circle_cyv = np.flip(np.linspace(ymin+ym+rs, ymax-ym-rs, 8))
    cxx, cyy = np.meshgrid(circle_cxv, circle_cyv)
    if debug:
        print("cxx=", cxx)
        print("cyy=", cyy)

    psizes = np.array([8, 3, 1])
    markersizes = np.array([8, 4, 2])
    pcolors = ["green", "blue", "red"]
    ptype_indeces = np.array(list(np.arange(len(psizes)))*200)
    np.random.shuffle(ptype_indeces)
    num_particles = len(ptype_indeces)
    grain_references = -np.ones(num_particles, dtype=int)

    init_pxv = np.linspace(xmin+0.01, xmax-0.01, num_particles)
    init_pyv = np.ones(num_particles)*ymax

    if num_frames is None:
        num_frames = 400
    sigma = ymax/num_frames*2
    du = sigma
    particle_scale = 1/1000  # [10, 5, 1] => [0.01, 0.005, 0.001]
    radius_map = psizes*particle_scale
    print("radius_map=", radius_map)    
    radiusv = np.array([radius_map[i] for i in ptype_indeces])
    if debug:
        print("radiusv=", radiusv)
    rv = radiusv + rs

    if smart_phone:
        fig, ax1 = plt.subplots(figsize=(8,20))
        fig.suptitle("Size Exclusion Chromatography", fontsize=24, y=0.99)
    else:
        # fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=figsize)
        if figsize is None:
            figsize = (7*2,7*1.25)
        fig = plt.figure(figsize=figsize)
        gs = GridSpec(1, 4)
        ax1 = fig.add_subplot(gs[0,0])
        ax2 = fig.add_subplot(gs[0,1])
        ax3 = fig.add_subplot(gs[0,2:4])
        fig.suptitle("Size Exclusion Chromatography Illustrative 2D Animation", fontsize=16, y=0.99)
    main_fig = fig

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

    button_ax = fig.add_axes([0.85, 0.05, 0.1, 0.03])
    def draw_slice_states(event):
        from Stochastic.ColumnSliceStates import draw_slice_states_impl
        print("draw_slice_states")
        if event.inaxes != button_ax:
            return
        draw_slice_states_impl(fig, ax2, grains, pxv, pyv, inmobile_states)

    debug_btn = Button(button_ax, 'Draw Slice States', hovercolor='0.975')
    debug_btn.on_clicked(draw_slice_states)

    def plot_column_structure(ax):
        ax.set_axis_off()

        p = Rectangle(
                    (xmin, ymin),      # (x,y)
                    xmax - xmin,          # width
                    ymax - ymin,    # height
                    facecolor   = solvant_color,
                    # alpha       = 0.2,
                )
        ax.add_patch(p)

        def plot_circles(radius, color="gray", alpha=1, create_grains=False, draw_rectangle=False, debug=False):
            if create_grains:
                grains = []
            
            for i, y in enumerate(circle_cyv):
                for j, x in enumerate(circle_cxv):
                    if i%2 == 0:
                        if j%2 == 0:
                            continue
                    else:
                        if j%2 == 1:
                            continue

                    if create_grains:
                        if old_grain:
                            grain = SolidGrain((i, j), (x, y), radius, rp, pyshift)
                        else:
                            grain = NewGrain((i, j), (x, y), radius, num_pores)

                    if draw_rectangle:
                        p = Rectangle((x-radius, y-radius*4.5), radius*2, radius*9, color=color, alpha=alpha)
                    else:
                        p = Circle((x, y), radius, color=color, alpha=alpha)
                        if create_grains:
                            if old_grain:
                                grain = SolidGrain((i, j), (x, y), radius, rp, pyshift)
                            else:
                                grain = NewGrain((i, j), (x, y), radius, num_pores)
                            if debug:
                                print("create_grains: ", (i, j), (x, y))
                                grain.draw_entries(ax)
                            grains.append(grain)
                    ax.add_patch(p)

            if create_grains:
                return grains

        grains = plot_circles(rs, create_grains=True)

        if old_grain:
            for y in np.linspace(ymin+ym+rs, ymax-ym-rs, 8):
                for dy in [-pyshift, 0, pyshift]:
                    y_ = y + dy
                    p = Rectangle(
                            (xmin, y_-rp),   # (x,y)
                            xmax - xmin,    # width
                            rp*2,           # height
                            facecolor   = solvant_color,
                            # alpha       = 0.2,
                        )
                    ax.add_patch(p)
            plot_circles(rs*0.2, draw_rectangle=True)
            plot_circles(rs, color="pink", alpha=0.5)
        else:
            for grain in grains:
                grain.draw(ax)

        """
        set_xlim or set_ylim must be called after plot_circles maybe due to NewGrain.graw which calles ax.pie
        """
        if not smart_phone:
            ax.set_aspect('equal')
        ax.set_xlim(xmin, xmax)    

        ax.set_ylim(0,1)

        return grains

    grains = plot_column_structure(ax1)
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
        dxv, dyv = np.random.normal(0, sigma, (2,num_particles))
        pxv += dxv
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

    def animate(i):
        if not pause:
            compute_next_positions()
        for k, p in enumerate(particles):
            p.set_data(pxv[k:k+1], pyv[k:k+1])
        return particles

    def init():
        nonlocal pxv, pyv, rv
        pxv = init_pxv.copy()
        pyv = init_pyv.copy()
        np.random.shuffle(ptype_indeces)
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
                            frames=frames, interval=100, blit=True)

    if close_plot:
        plt.close() # Close the figure to prevent it from displaying in a static form

    return anim