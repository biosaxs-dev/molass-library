"""
    Reports.Migrating.py

    extracted from molass_legacy.Reports.ReportUtils.py
"""
import numpy as np
from molass_legacy.AutorgKek.Quality import compute_atsas_fit_consistency

COLNAMES = [
    'folder',
    'file',
    'basic_quality',
    'positive_score',
    'fit_cover_ratio',
    'fit_consistency',
    'stdev_score',
    'q_rg_score',
    'fit_score',
    'basic_condition',
    'I0',
    'Rg',
    'min_qRg',
    'max_qRg',
    'gpfit_Rg',
    'gpfit_d',
    'gpfit_aic',
    'gpfit_bic',
    'unused',
    'gpfit_I0',
    'bico_mono_ratio',
    'IpI',
    'bicomponent',
    'head_trend',
    'result_type',
    'fit_consistency_pure',
    'stdev_ratio',
    'I0_stdev',
    'Rg_stdev',
    'atsas_I0',
    'atsas_Rg',
    'atsas_fit_consistency',
    'atsas_quality',
    ]

GPFIT_RG    = 14
GPFIT_I0    = 19
ATSAS_I0    = 29
ATSAS_RG    = 30
ATSAS_QUALITY   = 32

SELECT_COLUMS = [ 2, 3, 5, 6, 7, ATSAS_QUALITY, 10, GPFIT_I0, ATSAS_I0, 11, GPFIT_RG, ATSAS_RG ]
SELECT_COLUMS_ = np.array(SELECT_COLUMS) - 2

def make_gunier_row_values(result, result_atsas, return_selected=False):
    if result is not None and result.quality_object is not None:
        raw_factors = result.quality_object.get_raw_factors()
    else:
        raw_factors = None

    try:
        atsas_fit_consistency   = compute_atsas_fit_consistency( result.fit.Rg, result_atsas.Rg, raw_factors )
        atsas_quality           = result_atsas.Quality
    except:
        atsas_fit_consistency   = 0
        atsas_quality           = 0

    if result is None:
        results = []
    else:
        if result_atsas is None or result_atsas.Rg is None:
            atsas_results = []
        else:
            atsas_results = [ result_atsas.I0, result_atsas.Rg, atsas_fit_consistency, result_atsas.Quality ]
        if raw_factors is None:
            factors_with_fit_score  = [None] * 7
            basic_condition         = None
            fit_consistency_pure    = None
            stdev_ratio             = None
        else:
            factors_with_fit_score  = result.quality_object.get_factors_with_fit_score()    # 7 factors, TODO: remove
            basic_condition         = result.quality_object.basic_condition                 # TODO: remove
            fit_consistency_pure    =  result.quality_object.fit_consistency_pure
            stdev_ratio             = result.quality_object.stdev_ratio
        try:
            results =  ( factors_with_fit_score
                                + [ basic_condition ]
                                + [ result.I0, result.Rg, result.min_qRg, result.max_qRg ]
                                + [ result.fit.Rg, result.fit.degree ]
                                + [ result.fit.result.aic, result.fit.result.bic, 0, result.fit.I0, ]
                                + [ result.bico_mono_ratio ]
                                + [ result.IpI, result.bicomponent, result.head_trend ]
                                + [ result.result_type, fit_consistency_pure, stdev_ratio, result.I0_stdev, result.Rg_stdev ]
                                + atsas_results
                                )
        except Exception as exc:
            print( 'ERROR: ', str(exc) )
            results = [np.nan] * (len(COLNAMES) - 2)
    
    if return_selected:
        if len(results) < 31:
            results += [np.nan] * (31 - len(results))
        return [np.nan if results[i] is None else results[i] for i in SELECT_COLUMS_]
    else:
        return results