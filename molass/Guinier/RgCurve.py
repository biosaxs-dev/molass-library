"""
    Guinier.RgCurve.py

    This module contains the class RgCurve, which is used to store Rg curve information.

    Copyright (c) 2025, SAXS Team, KEK-PF
"""
import numpy as np

class RgCurve:
    """
    A class to represent a Rg curve.
    """

    def __init__(self, indeces, rgvalues, scores, results=None):
        """
        """
        self.index_dict = {}
        for k, i in enumerate(indeces):
            self.index_dict[i] = k
        self.indeces = np.asarray(indeces, dtype=int)
        self.rgvalues = rgvalues
        self.scores = scores
        self.results = results  # either, molass results or atsas results


def construct_rgcurve_from_list(rginfo_list, result_type=None):
    from molass_legacy.GuinierAnalyzer.AutorgKekAdapter import AutorgKekAdapter
    """
    Constructs an RgCurve from a result list.
    
    """
    indeces = []
    values = []
    scores = []
    results = []
    for k, (i, result) in enumerate(rginfo_list):
        indeces.append(i)
        values.append(result.Rg)
        if result_type is None:
            # SimpleGuinier result
            scores.append(result.score)
            adapter = AutorgKekAdapter(None, guinier=result)
            result_ = adapter.run(robust=True, optimize=True)
        else:
            # ATSAS.AutorgRunner result
            scores.append(result.Quality)
            result_ = result
        results.append(result_)
    
    return RgCurve(np.array(indeces), np.array(values), np.array(scores), results=results)
