"""
SAXS.MrcViewer.py
"""
import numpy as np
import matplotlib.pylab as plt
from molass_legacy.Saxs.EdPlotter import ed_scatter

def show_mrc(mrc_file):
    """show_mrc(mrc_file)
    
    Displays a 3D scatter plot and a 2D projection of the data in an MRC file.

    Parameters
    ----------
    mrc_file : str
        Path to the MRC file to be displayed.

    Returns
    -------
    None
    """
    import mrcfile
    with mrcfile.open(mrc_file) as mrc:
        data = mrc.data
    plt.style.use('dark_background')        
    fig  = plt.figure(figsize=(16,7))
    ax1 = fig.add_subplot(121, projection='3d')
    ax2 = fig.add_subplot(122, aspect='equal')
    axes = [ax1, ax2]
    ed_scatter(fig, axes, data, mrc_file)
    plt.style.use('default')

def _surface(crop, level, voxel, up, step):
    from scipy.ndimage import zoom, gaussian_filter
    from skimage.measure import marching_cubes
    cs = gaussian_filter(zoom(crop, up, order=1), sigma=up * 0.6) if up != 1 else gaussian_filter(crop, 0.6)
    # zoom() maps corner to corner, so the real spacing is not exactly voxel/up
    spacing = tuple(voxel * (n - 1) / (m - 1) for n, m in zip(crop.shape, cs.shape))
    verts, faces, _, _ = marching_cubes(cs, level=level, spacing=spacing, step_size=step)
    return verts, faces

def _shaded_triangles(verts, faces, center):
    tri = (verts - center)[faces]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    fn /= np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12
    shade = np.abs(fn @ np.array([0.3, 0.3, 0.9]))
    # a neutral colour with lighting: the isosurface does not encode density,
    # so it must not share the density colormap used elsewhere in the figure
    colors = np.ones((len(tri), 4))
    colors[:, :3] = np.array([0.50, 0.64, 0.85]) * (0.45 + 0.55 * shade)[:, None]
    return tri, colors

def _scatter_points(crop, level, voxel, center):
    w = np.argwhere(crop > level)
    xyz = w * voxel - center
    d = ((xyz - xyz.mean(axis=0)) ** 2).sum(axis=1)
    keep = d < d.mean() + 3 * d.std()           # drop far-off voxels, as the legacy viewer does
    return xyz[keep], crop[tuple(w[keep].T)]

def _geometry(data, voxel, level):
    """Everything the viewer draws for one density level."""
    idx = np.argwhere(data > level)
    if len(idx) == 0:
        raise ValueError("No voxel exceeds the density level %.3g" % level)
    lo = np.maximum(idx.min(axis=0) - 3, 0)
    hi = np.minimum(idx.max(axis=0) + 4, data.shape)
    crop = data[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]

    fv, ff = _surface(crop, level, voxel, up=3, step=1)
    cv, cf = _surface(crop, level, voxel, up=1, step=2)
    center = fv.mean(axis=0)
    meshes = {"fine": _shaded_triangles(fv, ff, center),
              "coarse": _shaded_triangles(cv, cf, center)}
    pts, vals = _scatter_points(crop, level, voxel, center)

    c = [int(round(v)) - l for v, l in zip(idx.mean(axis=0), lo)]
    # (array, plane name, row axis, column axis, row centre, column centre); the centre
    # (centroid of the marked voxels) is the origin of the Angstrom ticks
    slices = [(crop[c[0], :, :], "yz plane", "y", "z", c[1], c[2]),
              (crop[:, c[1], :], "xz plane", "x", "z", c[0], c[2]),
              (crop[:, :, c[2]], "xy plane", "x", "y", c[0], c[1])]
    return dict(meshes=meshes, pts=pts, vals=vals, r=np.abs(fv - center).max(), slices=slices)

def _draw_slice(ax, s, level, voxel, vmax):
    """One central slice: density map with Angstrom axes and the threshold contour."""
    from matplotlib.lines import Line2D
    arr, name, row_name, col_name, row_c, col_c = s
    n_rows, n_cols = arr.shape
    extent = [(-col_c - 0.5) * voxel, (n_cols - col_c - 0.5) * voxel,
              (n_rows - row_c - 0.5) * voxel, (-row_c - 0.5) * voxel]
    ax.imshow(arr, cmap="plasma", vmin=0, vmax=vmax, extent=extent)
    if arr.min() < level < arr.max():
        ax.contour((np.arange(n_cols) - col_c) * voxel, (np.arange(n_rows) - row_c) * voxel,
                   arr, levels=[level], colors="white", linewidths=1.2)
    ax.set_title(name, fontsize=10)
    ax.set_xlabel(col_name + " (\u00c5)", fontsize=8)
    ax.set_ylabel(row_name + " (\u00c5)", fontsize=8)
    ax.tick_params(labelsize=7)
    return Line2D([], [], color="white", linewidth=1.2, label="density = %.3g (threshold)" % level)

def make_mrc_figure(mrc_file, level=None, fig=None):
    """make_mrc_figure(mrc_file, level=None, fig=None)

    Builds an interactive viewer figure for an MRC (electron density) file.

    The left panel is a 3D view that can be switched between an isosurface and
    a voxel scatter (drag to rotate, optional auto-rotation). The isosurface has
    a neutral colour (lighting only); the slices, the voxel scatter and the
    histogram share one density colour scale, shown by the colorbar at the right.
    The "Level" slider
    (logarithmic, relative to the maximum density) changes the density threshold;
    the display is rebuilt when the slider is released. The right panels
    show the three central slices (yz, xz and xy planes, in Angstrom, with the
    isosurface threshold drawn as a white contour line) and a histogram of the
    marked voxel densities (the threshold is the dashed line).
    While the mouse button is down or auto-rotation is running, a coarse
    isosurface mesh is used to keep the rotation smooth.

    The figure is created without touching pyplot state, so it can be embedded
    in a GUI canvas, or displayed in a notebook with ``show_mrc_views()``.

    Parameters
    ----------
    mrc_file : str
        Path to the MRC file to be displayed.
    level : float, optional
        Density threshold of the isosurface and the voxel scatter.
        If None, it is guessed from the data.
    fig : matplotlib.figure.Figure, optional
        Figure to draw into. If None, a new ``Figure`` is created.

    Returns
    -------
    fig : matplotlib.figure.Figure
    """
    import mrcfile
    from matplotlib import colormaps
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize
    from matplotlib.ticker import FormatStrFormatter
    from matplotlib.figure import Figure
    from matplotlib.widgets import CheckButtons, RadioButtons, Slider
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from molass_legacy.Saxs.EdBoundary import guess_boundary_value

    with mrcfile.open(mrc_file) as mrc:
        data = np.array(mrc.data, dtype=float)
        voxel = float(mrc.voxel_size.x)     # A per voxel
    if level is None:
        level = guess_boundary_value(data, debug=False)
    try:
        geo = _geometry(data, voxel, level)
    except ValueError as exc:
        raise ValueError("%s in %s" % (exc, mrc_file)) from None
    dmax = float(data.max())

    if fig is None:
        fig = Figure(figsize=(16, 7))
    gs = fig.add_gridspec(6, 2, height_ratios=[1, 1, 1, 0.45, 1, 1])    # row 3: gap between slices and histogram
    ax = fig.add_subplot(gs[:, 0], projection="3d")
    slice_gs = gs[0:3, 1].subgridspec(1, 3, wspace=0.45)
    slice_axes = [fig.add_subplot(slice_gs[0, k]) for k in range(3)]
    ax3 = fig.add_subplot(gs[4:6, 1])

    state = {"mode": "fine", "dragging": False, "auto": False, "view": "Isosurface", "timer": None,
             "level": level, "poly": None, "sc": None, "meshes": None,
             "slider_drag": False, "legend": []}

    # one density scale for the slices, the voxel scatter, the histogram and the colorbar
    density_norm = Normalize(vmin=0, vmax=dmax)

    def apply_view():
        iso = state["view"] == "Isosurface"
        state["poly"].set_visible(iso)
        state["sc"].set_visible(not iso)
        if iso:
            ax.set_title(f"Isosurface (level={state['level']:.3g}, {voxel:.2f} \u00c5/voxel) -- drag to rotate")
        else:
            ax.set_title("Density Distribution in Voxels -- drag to rotate")

    def use(mode):
        if state["mode"] != mode:
            tri, colors = state["meshes"][mode]
            state["poly"].set_verts(tri)
            state["poly"].set_facecolor(colors)
            state["mode"] = mode

    def draw_geometry(geo, level):
        """(Re)draw all level-dependent artists."""
        for key in ("poly", "sc"):
            if state[key] is not None:
                state[key].remove()
        state["level"] = level
        state["meshes"] = geo["meshes"]
        poly = Poly3DCollection(geo["meshes"]["fine"][0], linewidths=0)
        poly.set_facecolor(geo["meshes"]["fine"][1])
        ax.add_collection3d(poly)
        pts, vals = geo["pts"], geo["vals"]
        sc = ax.scatter3D(pts[:, 0], pts[:, 1], pts[:, 2], c=vals, cmap="plasma", norm=density_norm,
                          s=30, alpha=1)
        state["poly"], state["sc"], state["mode"] = poly, sc, "fine"
        if state["auto"]:
            use("coarse")
        r = geo["r"]
        ax.set_xlim(-r, r); ax.set_ylim(-r, r); ax.set_zlim(-r, r)
        ax.set_box_aspect((1, 1, 1))
        ax.set_axis_off()

        handles = []
        for sax, s in zip(slice_axes, geo["slices"]):
            sax.clear()
            handles.append(_draw_slice(sax, s, level, voxel, dmax))
        for artist in state["legend"]:
            artist.remove()
        handles[0].set_label("Central slices, white line: threshold = %.3g" % level)
        state["legend"] = [fig.legend(handles=handles[:1], loc="upper center", bbox_to_anchor=(0.75, 0.995),
                                      fontsize=9, frameon=False)]
        ax3.clear()
        counts, edges = np.histogram(vals, bins=10)
        centers = (edges[:-1] + edges[1:]) / 2
        ax3.bar(centers, counts / counts.sum() * 100, width=np.diff(edges) * 0.9,
                color=colormaps["plasma"](density_norm(centers)))
        ax3.axvline(level, color="gray", linestyle="--", linewidth=1,
                    label="threshold = %.3g (Level slider)" % level)
        ax3.legend(fontsize=8, loc="upper right")
        ax3.set_xlabel("Density")
        ax3.set_ylabel("Voxels (%)")
        ax3.set_title("Density of the %d marked voxels (%.2g%% of the %dx%dx%d cube)"
                      % (len(vals), len(vals) / data.size * 100, *data.shape))

        apply_view()

    draw_geometry(geo, level)
    fig.tight_layout()
    fig.subplots_adjust(top=0.9, right=0.88)    # room for the 3D title and, at the right, the colorbar with its labels

    cbax = fig.add_axes([0.905, 0.15, 0.012, 0.7])
    cbar = fig.colorbar(ScalarMappable(norm=density_norm, cmap="plasma"), cax=cbax, label="Density")
    cbar.ax.yaxis.set_major_formatter(FormatStrFormatter("%.3g"))
    cbar.ax.tick_params(labelsize=8)
    apply_view()

    def set_view(label):
        state["view"] = label
        apply_view()
        fig.canvas.draw_idle()

    # the level slider is logarithmic, relative to the maximum density
    s_min, s_max = -5.0, -0.05
    s0 = float(np.clip(np.log10(max(level, 1e-30) / dmax), s_min, s_max)) if dmax > 0 else s_min
    slider_ax = fig.add_axes([0.20, 0.03, 0.22, 0.03])
    slider = Slider(slider_ax, "Level", s_min, s_max, valinit=s0)

    def show_level(s):
        slider.valtext.set_text("%.3g" % (dmax * 10 ** s))

    slider.on_changed(show_level)
    show_level(s0)
    state["slider_value"] = s0

    def apply_level():
        s = slider.val
        try:
            geo = _geometry(data, voxel, dmax * 10 ** s)
        except ValueError:      # no voxel above the level, or no surface to extract
            slider.eventson = False
            slider.set_val(state["slider_value"])
            slider.eventson = True
            show_level(state["slider_value"])
            slider_ax.set_title("no surface at that level", fontsize=8, color="red")
            fig.canvas.draw_idle()
            return
        slider_ax.set_title("")
        state["slider_value"] = s
        draw_geometry(geo, dmax * 10 ** s)
        fig.canvas.draw_idle()

    def on_press(event):
        if event.inaxes is slider_ax:
            state["slider_drag"] = True
        elif event.inaxes is ax:
            state["dragging"] = True
            use("coarse")

    def on_release(event):
        # the geometry is rebuilt when the slider is released, not on every move
        if state["slider_drag"]:
            state["slider_drag"] = False
            apply_level()
        if state["dragging"]:
            state["dragging"] = False
            if not state["auto"]:
                use("fine")
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect("button_press_event", on_press)
    fig.canvas.mpl_connect("button_release_event", on_release)

    def spin():
        ax.view_init(elev=ax.elev, azim=ax.azim + 4)
        fig.canvas.draw_idle()

    radio = RadioButtons(fig.add_axes([0.02, 0.09, 0.12, 0.09]), ["Isosurface", "Voxel scatter"])
    radio.on_clicked(set_view)

    check = CheckButtons(fig.add_axes([0.02, 0.02, 0.12, 0.06]), ["Auto-rotate"], [False])

    def on_check(_label):
        state["auto"] = check.get_status()[0]
        if state["timer"] is None:
            # created here, not earlier: the canvas may be replaced after this function returns
            state["timer"] = fig.canvas.new_timer(interval=100)
            state["timer"].add_callback(spin)
        if state["auto"]:
            use("coarse")
            state["timer"].start()
        else:
            state["timer"].stop()
            use("fine")
            fig.canvas.draw_idle()

    check.on_clicked(on_check)
    state["apply_level"] = apply_level
    fig._mrc_viewer_state = (state, radio, check, slider, ax)    # keep widgets alive
    return fig

def show_mrc_views(mrc_file, level=None):
    """show_mrc_views(mrc_file, level=None)

    Shows the interactive viewer of ``make_mrc_figure()`` in a pyplot window.
    In a notebook, an interactive backend is required to rotate the 3D view,
    e.g. ``%matplotlib tk``, ``%matplotlib qt`` or ``%matplotlib widget``.

    Parameters
    ----------
    mrc_file : str
        Path to the MRC file to be displayed.
    level : float, optional
        Density threshold. If None, it is guessed from the data.

    Returns
    -------
    fig : matplotlib.figure.Figure
    """
    fig = make_mrc_figure(mrc_file, level=level, fig=plt.figure(figsize=(16, 7)))
    plt.show()
    return fig