"""
    Stochastic.StationaryMove.py

    Copyright (c) 2024, SAXS Team, KEK-PF
"""
import numpy as np
from shapely import LineString, Point, Polygon, intersection
from molass_legacy.KekLib.PolygonGeometry import makeOffsetPoly
from molass_legacy.KekLib.CircleGeometry import circle_line_segment_intersection

REFLECT_LIMIT_DIST = 1e-5
REFLECT_NUM_TRIALS = 5

def find_nearest_wall(grain, px, py):
    cx, cy = grain.center
    dx = px - cx
    dy = py - cy
    angle = np.arctan2(dy, dx)
    entries = grain.entries.flatten()
    k = np.argmin((entries - angle)**2)
    i, j = divmod(k, 2)
    return i, j

def compute_boundary_walls(cx, cy, R, r, entry_points):
    outerx = [cx]
    outery = [cy]
    for ex, ey in entry_points:
        outerx.append(ex)
        outery.append(ey)
    innerx, innery = makeOffsetPoly(outerx, outery, -r, outer_ccw=1)
    ipoints = np.array([(ex, ey) for ex, ey in zip(innerx, innery)])
    cpoint = ipoints[0,:]
    bpoints = [cpoint]
    for ipoint in ipoints[1:,:]:
        dvec = ipoint - cpoint
        dvec /= np.linalg.norm(dvec)
        opoint = cpoint + dvec * R
        intersections = circle_line_segment_intersection((cx, cy), R, cpoint, opoint, full_line=False)
        if len(intersections) > 0:
            bpoints.append(intersections[0])
        else:
            # investigate this case
            pass
    return bpoints

def mirrorImage(a, b, c, x1, y1):
    """
    borrowed from
    https://www.geeksforgeeks.org/find-mirror-image-point-2-d-plane/
    """
    temp = -2 * (a * x1 + b * y1 + c) /(a * a + b * b)
    x = temp * a + x1
    y = temp * b + y1 
    return (x, y)

def compute_reflected_point(bpoints, wx, wy, nx, ny, debug=False):
    ls = LineString([(wx, wy), (nx, ny)])
    cpoint = bpoints[0]
    ret = None
    for point in bpoints[1:]:
        tp = intersection(ls, LineString([cpoint, point]))
        if debug:
            print(tp, type(tp) is Point)
        if type(tp) is Point:
            # task: choose the closer wall if both walls have an intersection point
            cx, cy = cpoint
            px, py = tp.x, tp.y
            """
            m = (py - cy)/(px - cx)
            y - cy = m * (x - cx)
            m*x - y + cy - m*cx = 0
            """
            m = (py - cy)/(px - cx)
            a = m
            b = -1
            c = cy - m*cx
            mx, my = mirrorImage(a, b, c, nx, ny)
            dist = np.sqrt((mx - nx)**2 + (my - ny)**2)
            if dist > REFLECT_LIMIT_DIST:
                if debug:
                    print("dist=", dist)
                    print("(nx, ny) ==> (mx, my)", (nx, ny), (mx, my))
                ret = mx, my
    return ret

def get_next_position_impl(particle, grain, last_px, last_py, px, py, debug_info=None):
    inmobile = False
    cx, cy = grain.center
    nx, ny = px, py
    i, j = find_nearest_wall(grain, px, py)
    entry_points = [grain.get_point_from_angle(angle) for angle in grain.entries[i,:]]
    bpoints = compute_boundary_walls(cx, cy, grain.radius, particle.radius, entry_points)
    wx, wy = last_px, last_py
    debug = debug_info is not None
    reflected = False
    for k in range(REFLECT_NUM_TRIALS):
        ret = compute_reflected_point(bpoints, wx, wy, nx, ny, debug=debug)
        if ret is None:
            break
        wx, wy = nx, ny
        nx, ny = ret
        reflected = True

    if not reflected:
        poly = Polygon(bpoints)
        if not poly.contains(Point(nx, ny)):
            intersections = circle_line_segment_intersection((cx, cy), grain.radius, (wx, wy), (nx, ny), full_line=False)
            if len(intersections) == 0:
                dist = np.sqrt((nx - cx)**2 + (ny - cy)**2)
                if dist < grain.radius + particle.radius:
                    inmobile = True
            else:
                if debug:
                    print("not reflected", intersections[0])
                tx, ty = intersections[0]
                """
                get the tangent line equation
                and find the mirror image of (nx, ny) against the tangent line
                ((x, y) - (tx, ty)) ・ ((cx, cy) - (tx, ty)) = 0
                (x - tx, y - ty)・(cx - tx, cy - ty) = 0
                (x - tx, y - ty)・(a, b) = 0
                a*x + b*y - a*tx - b*ty = 0
                """
                a = cx - tx
                b = cy - ty
                c = - a*tx - b*ty
                nx, ny = mirrorImage(a, b, c, nx, ny)
                reflected = True
                inmobile = True

    if debug_info is not None:
        from matplotlib.patches import Polygon as MplPolygon
        print("get_next_position_impl", px, py)
        print("get_next_position_impl", nx, ny, inmobile)
        fig, ax = debug_info
        ax.cla()
        ax.set_title("get_next_position_impl debug")  
        grain.draw(ax)
        dx = px - last_px
        dy = py - last_py
        vlen = np.sqrt(dx**2 + dy**2)
        ax.arrow(x=last_px, y=last_py, dx=dx, dy=dy, width=0.0005, head_width=0.002, length_includes_head=True,
                    head_length=0.2*vlen, color='black', alpha=0.5)
        for entry in entry_points:
            ax.plot([cx, entry[0]], [cy, entry[1]], color='red')

        if reflected:
            dx = nx - wx
            dy = ny - wy
            vlen = np.sqrt(dx**2 + dy**2)
            ax.arrow(x=wx, y=wy, dx=dx, dy=dy, width=0.0005, head_width=0.002, length_includes_head=True,
                    head_length=0.2*vlen, color='green', alpha=0.5)
            
        poly = MplPolygon(bpoints, color="red", alpha=0.5)
        ax.add_patch(poly)
        particle.draw(ax, alpha=0.5)

        r = grain.radius * 1.2
        ax.set_xlim(cx - r, cx + r)
        ax.set_ylim(cy - r, cy + r)
        fig.canvas.draw_idle()

    return nx, ny, inmobile