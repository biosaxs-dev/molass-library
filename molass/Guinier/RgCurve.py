"""
    Guinier.RgCurve.py

    This module contains the class RgCurve, which is used to store Rg curve information.
"""
import numpy as np
from molass.DataObjects.Curve import Curve

class RgCurve(Curve):
    """
    A class to represent an Rg curve.

    Attributes
    ----------
    indeces : np.ndarray
        The indices of the frames used to compute the Rg values.
    rgvalues : np.ndarray
        The Rg values corresponding to the indeces.
    scores : np.ndarray
        The scores corresponding to the indeces and rgvalues.
    results : list or None
        The results of the Rg computation. It can be None if not specified.
    intensities : list or None
        The intensities corresponding to the indeces. It can be None if not specified.

    """

    def __init__(self, indeces, rgvalues, scores, results=None, intensities=None):
        """
        """
        indeces = np.asarray(indeces, dtype=int)
        super().__init__(indeces, rgvalues, type='i')
        assert len(indeces) == len(rgvalues) == len(scores)
        self.index_dict = {}
        for k, i in enumerate(indeces):
            self.index_dict[i] = k
        self.indeces = indeces
        self.rgvalues = rgvalues
        self.scores = scores
        self.results = results  # either, molass results or atsas results
        self.intensities = intensities  # only for molass results, None for atsas results


def construct_rgcurve_from_list(rginfo_list, result_type=None):
    """
    Constructs an RgCurve from a result list.

    Parameters
    ----------
    rginfo_list : list of tuples
        A list of tuples where each tuple contains (index, result).
        The result can be either a SimpleGuinier result or an ATSAS Autorg result.
    result_type : str or None
        If None, the results are assumed to be SimpleGuinier results.
        If 'atsas', the results are assumed to be ATSAS Autorg results.
        Default is None.

    Returns
    -------
    RgCurve
        An RgCurve object constructed from the provided result list.
    """
    from molass_legacy.GuinierAnalyzer.AutorgKekAdapter import AutorgKekAdapter
    indeces = []
    values = []
    scores = []
    results = []
    intensities = [] if result_type is None else None
    for k, (i, result) in enumerate(rginfo_list):
        indeces.append(i)
        values.append(result.Rg)
        if result_type is None:
            # SimpleGuinier result
            scores.append(result.score)
            adapter = AutorgKekAdapter(None, guinier=result)
            intensities.append(adapter.intensity)
            result_ = adapter.run(robust=True, optimize=True)
        else:
            # ATSAS.AutorgRunner result
            scores.append(result.Quality)
            result_ = result
        results.append(result_)
    
    return RgCurve(np.array(indeces), np.array(values), np.array(scores), results=results, intensities=intensities)
