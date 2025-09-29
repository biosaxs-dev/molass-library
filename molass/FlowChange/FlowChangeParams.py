"""
    FlowChange.FlowChangeParams.py

    It seems that this module is broken. Will fix it later.
"""
import os
import numpy as np
import matplotlib.pyplot as plt
from molass.DataUtils.UvLoader import get_uvcurves
# from molass.Test.TestFlowChange import TEST_TARGETS
TEST_TARGETS = []
# from molass.Test.TestSettings import get_datafolder
def get_datafolder():
    """Get the data folder path.
    
    Returns
    -------
    str
        The data folder path.
    """
    # Adjust this function to return the correct data folder path
    return

def compute_like_values(for_all=False):
    """Compute likelihood values for flow change detection on test datasets.

    Parameters
    ----------
    for_all : bool, optional
        If True, process all folders in the data directory. If False, process only predefined test targets. Default is False.

    Returns
    -------
    list of tuples
        Each tuple contains (in_folder, c1, c2, mi, points, segments, abs_likes, rel_likes, peaklike, peakpos)
    """
    from molass.FlowChange.FlowChange import flowchange_exclude_slice
    from molass.FlowChange.FlowChangeLikely import flowchange_likelihood
    root_folder = get_datafolder()
    recs = []
    def append_rec(i, in_folder):
        try:
            c1, c2 = get_uvcurves(in_folder)
        except:
            print("ERROR: in", in_folder)
            return
        mi, points, segments, rel_likes, peaklike, peakpos, yscale = flowchange_exclude_slice(c1, c2, return_firstinfo=True)
        print([i], in_folder, points)
        abs_likes = []
        for k, p in enumerate(points):
            abs_like = flowchange_likelihood(c1.x, c2.y, p, segments[k], segments[k+1], yscale)
            abs_likes.append(abs_like)
        recs.append((in_folder, c1, c2, mi, points, segments, abs_likes, rel_likes, peaklike, peakpos))

    if for_all:
        from molass.DataUtils.FolderWalker import walk_folders
        for i, folder_path in enumerate(walk_folders(root_folder)):
            append_rec(i, folder_path)
    else:
        for i, target in enumerate(TEST_TARGETS):
            folder_path = os.path.join(root_folder, target[0])
            append_rec(i, folder_path)

    return recs

def plot_flowchange(in_folder, c1, c2, mi, points, segments, axes=None):
    """Plot the flow change analysis results.

    Parameters
    ----------
    in_folder : str
        The input folder path.
    c1 : UvCurve
        The first UV curve.
    c2 : UvCurve
        The second UV curve.
    mi : Moment
        The moment information object.
    points : list of int
        List of points where flow changes are detected.
    segments : list of int
        List of segment boundaries.
    axes : list of Axes, optional
        If provided, use these axes for plotting.

    Returns
    -------
    None
    """

    from molass.Geometric.Linesegment import plot_segments
    from molass.FlowChange.FlowChangeJudge import LIMIT_SIGMA
    if axes is None:
        fig, axes = plt.subplots(ncols=2, figsize=(10,4))
    else:
        fig = axes[0].get_figure()
    fig.suptitle(in_folder)
    ax1, ax2 = axes
    axt = ax1.twinx()
    axt.grid(False)
    ax1.plot(c1.x, c1.y)
    axt.plot(c2.x, c2.y, color='red', alpha=0.5)
    for p in points:
        if p is not None:
            ax1.axvline(c1.x[p], color='cyan')
    plot_segments(c2.x, c2.y, segments, ax=ax2)
    M, std = mi.get_meanstd()
    for px in [M-LIMIT_SIGMA*std, M+LIMIT_SIGMA*std]:
        for ax in axes:
            ax.axvline(px, color='yellow')

    fig.tight_layout()

def make_test_targets(recs):
    """Make test targets from the computed records.

    Parameters
    ----------
    recs : list of tuples
        The computed records from the flow change analysis.

    Returns
    -------
    list of tuples
        Each tuple contains (folder, (i, j)) where i and j are the test target indices.
    """
    # from molass.Test.TestSettings import get_datafolder
    from importlib import reload
    import molass.FlowChange.FlowChangeJudge
    reload(molass.FlowChange.FlowChangeJudge)
    from molass.FlowChange.FlowChangeJudge import FlowChangeJudge

    root_folder = get_datafolder() + '\\'
    judge = FlowChangeJudge()
    targets = []
    for k, rec in enumerate(recs):
        in_folder, c1, c2, mi, points, segments, abs_likes, rel_likes, peaklike, peakpos = rec
        i, j, judge_info = judge.judge(c1, c2, mi, points, segments, abs_likes, rel_likes, peaklike, peakpos)
        folder = in_folder.replace(root_folder, '')
        target = (folder, (i,j))
        print([k], target)
        targets.append(target)
    return targets

def test_params(recs, params_dict, targets=None):
    """Test the flow change parameters against expected targets.

    Parameters
    ----------
    recs : list of tuples
        The computed records from the flow change analysis.
    params_dict : dict
        The parameters for the FlowChangeJudge.
    targets : list of tuples, optional
        The expected targets for the flow change analysis.
        If None, use the predefined TEST_TARGETS. Default is None.

    Returns
    -------
    None
    """
    from importlib import reload
    import molass.FlowChange.FlowChangeJudge
    reload(molass.FlowChange.FlowChangeJudge)
    from molass.FlowChange.FlowChangeJudge import FlowChangeJudge

    if targets is None:
        targets = TEST_TARGETS

    judge = FlowChangeJudge()
    judge.update_params(params_dict)

    for k, rec in enumerate(recs):
        in_folder, c1, c2, mi, points, segments, abs_likes, rel_likes, peaklike, peakpos = rec
        i, j, judge_info = judge.judge(c1, c2, mi, points, segments, abs_likes, rel_likes, peaklike, peakpos)
        expected = targets[k][1]
        if (i,j) == expected:
            result = 'ok'
        else:
            result = '-------------- not ok %s => %s : %s' % (points, (i,j), expected)
            plot_flowchange(in_folder, c1, c2, mi, (i,j), segments)

        print([k], in_folder, result)