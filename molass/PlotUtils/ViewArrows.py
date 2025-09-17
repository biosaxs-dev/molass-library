"""
    PlotUtils.ViewArrows.py
"""

def plot_view_arrows(ax, use_quiver=False, debug=False):
    """
    Plot view arrows on a 3D axis.
    This function adds arrows to indicate the elutional and spectral views.
    """
    if debug:
        from importlib import reload
        import molass.PlotUtils.Arrow3D
        reload(molass.PlotUtils.Arrow3D)
    from molass.PlotUtils.Arrow3D import add_arrow3D

    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    zmin, zmax = ax.get_zlim()
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_zlim(zmin, zmax)
    if debug:
        print(f"X: {xmin}, {xmax}")
        print(f"Y: {ymin}, {ymax}")
        print(f"Z: {zmin}, {zmax}")

    def get_coordinates(x, y, z):
        return (x * (xmax - xmin) + xmin,
                y * (ymax - ymin) + ymin,
                z * (zmax - zmin) + zmin)

    def get_direction(x, y, z):
        return (x * (xmax - xmin),
                y * (ymax - ymin),
                z * (zmax - zmin))

    xz_view_point = get_coordinates(0.5, -0.6, 0)
    xz_head_vector = get_direction(0, 0.4, 0)
    yz_view_point = get_coordinates(1.6, 0.5, 0)
    yz_head_vector = get_direction(-0.3, 0, 0)
    
    if use_quiver:
        # Use quiver for 3D arrows
        # Note: currently not available possibly due to a bug.
        xz_arrow_length = 0.3*(xmax - xmin)
        yz_arrow_length = 0.3*(ymax - ymin)
        ax.quiver(*xz_view_point, *xz_head_vector, color='orange', length=xz_arrow_length, arrow_length_ratio=0.2, normalize=True)
        ax.quiver(*yz_view_point, *yz_head_vector, color='orange', length=yz_arrow_length, arrow_length_ratio=0.2, normalize=True)
    else:
        add_arrow3D()
        arrowstyle="-|>"
        arrow_spec = dict(color='orange', arrowstyle=arrowstyle, linewidth=3, linestyle='-', mutation_scale=20)
        ax.arrow3D(*xz_view_point, *xz_head_vector, **arrow_spec)
        ax.arrow3D(*yz_view_point, *yz_head_vector, **arrow_spec)

    ax.text(*xz_view_point, "Elutional View", color='orange', va='top', ha='center', fontsize=14)
    ax.text(*yz_view_point, "Spectral View", color='orange', va='top', ha='center', fontsize=14)