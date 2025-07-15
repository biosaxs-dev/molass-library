"""
    LowRank.PairedRange.py

    This module contains the class PairedRange, which is used to store information
    about the valid elution ranges for the analysis report.
"""

class PairedRange:
    def __init__(self, range_, minor=False, peak_index=None, elm_recs=None):
        self.peak_index = peak_index
        if minor:
            ranges = [range_]
        else:
            if peak_index is None:
                peak_index = (range_[0] + range_[1])//2
            ranges = [(range_[0], peak_index), (peak_index, range_[1])]

        self.ranges = ranges
        self.elm_recs = elm_recs

    def get_fromto_list(self):
        """
        for backward compatibility to molass_legacy.AnalysisRangeInfo.PaoiredRange,
        returns a list of tuples
        """
        return self.ranges

    def as_list(self, k):
        from molass_legacy.DataStructure.PeakInfo import PeakInfo
        peakinfo = PeakInfo(k,
                         self.peak_index,
                         self.elm_recs
                         )  
        return [peakinfo] + self.ranges

    def is_minor(self):
        return len(self.ranges) == 1

    def __len__(self):
        return len(self.ranges)

    def __iter__(self):
        for range_ in self.ranges:
            yield range_

    def __str__(self):
        return str(self.ranges)

    def __repr__(self):
        return str(self.ranges)

def convert_to_list_pairedranges(pairedranges):
    ret_list = []
    for prange in pairedranges:
        for range_ in prange.ranges:
            ret_list += [range_]
    return ret_list