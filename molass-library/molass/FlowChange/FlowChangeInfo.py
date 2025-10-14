"""
    FlowChange.FlowChangeInfo.py
"""

class FlowChangeJudgeInfo:
    """Class to hold information about the flow change judgment.

    Attributes
    ----------
    caseid : str
        The identifier for the judgment case.
    kwargs : dict
        Additional keyword arguments holding various judgment details.
    """
    def __init__(self, caseid, **kwargs):
        self.caseid = caseid
        self.kwargs = kwargs

class FlowChangeInfo:
    """Class to hold information about the flow change analysis.
    Attributes
    ----------
    i : int
        The index along the iv axis where the flow change is analyzed.
    j : int
        The index along the jv axis where the flow change is analyzed.
    curves : list of CurveProxy
        The list of curves involved in the flow change analysis.
    judge_info : FlowChangeJudgeInfo
        The judgment information for the flow change.
    """
    def __init__(self, i, j, curves, judge_info):
        self.i = i
        self.j = j
        self.curves = curves
        self.judge_info = judge_info