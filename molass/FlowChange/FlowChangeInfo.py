"""
    FlowChange.FlowChangeInfo.py
"""

class FlowChangeJudgeInfo:
    def __init__(self, caseid, **kwargs):
        self.caseid = caseid
        self.kwargs = kwargs

class FlowChangeInfo:
    def __init__(self, i, j, curves, judge_info):
        self.i = i
        self.j = j
        self.curves = curves
        self.judge_info = judge_info