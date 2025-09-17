"""
    SEC.ColumnElements.py

    Copyright (c) 2024-2025, Molass Community
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Wedge

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
            import molass.SEC.StationaryMove as sm
            reload(sm)
            from molass.SEC.StationaryMove import get_next_position_impl
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
