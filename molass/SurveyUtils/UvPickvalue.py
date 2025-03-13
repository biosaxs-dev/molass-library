"""
    SurveyUtils.UvPickvalue.py

    Copyright (c) 2024, SAXS Team, KEK-PF
"""

def get_pickvalue(in_folder, wvector):
    if in_folder.find('OAGIwyatt_01') >= 0 or in_folder.find('OA_Ald_Fer'):
        pickvalue = 400
    elif in_folder.find('20190315_1') >= 0:
        pickvalue = 550
    else:
        pickvalue = wvector[-5]
    return pickvalue