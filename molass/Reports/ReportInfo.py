"""
    Reports.ReportInfo.py
"""

class ReportInfo:
    def __init__(self, **kwrgs):
        self.__dict__.update(kwrgs)

    def __str__(self):
        return str(self.__dict__)