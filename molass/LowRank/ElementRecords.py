"""
LowRank.ElementRecords.py
"""
from molass_legacy.Models.ElutionCurveModels import EGH
from molass_legacy.Decomposer.ModelEvaluator import ModelEvaluator

class FitRecordProxy:
    """
    A proxy class for FitRecord.
    """
    def __init__(self, kno, component):
        self.kno = kno
        self.component = component
        model = EGH()
        self.evaluator = ModelEvaluator(model, component.ccurve.params)
        self.item_list = [self.kno, self.evaluator]

    def __getitem__(self, index):
        return self.item_list[index]

def make_element_records_impl(decomposition):
    """
    Returns the element records for the components.
    """

    # 
    
    ret_records = []
    for kno, component in enumerate(decomposition.get_xr_components()):
        proxy = FitRecordProxy(kno, component)
        ret_records.append(proxy)

    return ret_records
