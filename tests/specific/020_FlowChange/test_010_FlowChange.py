"""
    test FlowChange
"""
import os
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass.Local import get_local_settings
local_settings = get_local_settings()
DATA_ROOT_FOLDER = local_settings['DATA_ROOT_FOLDER']

TEST_TARGETS = [
    (r"20160227\backsub",           (None, None)),  # 0
    (r"20160628",                   (680, None)),   # 1
    (r"20161104\BL-10C\Ald",        (140, None)),   # 2
    (r"20161104\BL-6A\AhRR",        (160, 430)),    # 3
    (r"20161104\BL-6A\pH6",         (170, None)),   # 4
    (r"20161119\Kosugi8_Backsub",   (155, None)),   # 5
    (r"20161124\Backsub1",          (155, None)),   # 6
    (r"20161216\Backsub",           (140, None)),   # 7
    (r"20161217",                   (250, None)),   # 8
    (r"20170209\OA_Ald_Fer",        (None, None)),  # 9
    (r"20170209\OAGIwyatt_02",      ( 75, None)),   # 10
    (r"20170226\Sugiyama",          (285, None)),   # 11
    (r"20170301\Backsub",           (275, None)),   # 12
    (r"20170304\Backsub_166_195",   (300, None)),   # 13
    (r"20170307\Backsub",           (250, None)),   # 14
    (r"20170309\Backsub",           (100, None)),   # 15
    (r"20171203",                   (275, None)),   # 16
    (r"20180206",                   ( 75, None)),   # 16
    (r"20180219",                   ( 95, None)),   # 18
    (r"20180225",                   (None, None)),  # 19
    (r"20180316\Backsub",           (335, None)),   # 20
    (r"20180602",                   (115, None)),   # 21
    (r"20180617",                   (100, None)),   # 22
    (r"20181127",                   (100, None)),   # --
    (r"20190221",                   (145, None)),   # 23
    (r"20190221_2",                 (165, None)),   # 24
    (r"20190305_2",                 (120, None)),   # 25
    (r"20190309_5",                 (None, None)),  # 26
    (r"20190309_6",                 (None, None)),  # 27
    (r"20190524_1",                 ( 50, None)),   # 28
    (r"20190524_2",                 (None, None)),  # 29
    (r"20190524_3",                 (None, None)),  # --
    (r"20190607_1",                 ( 90, None)),   # 30
    (r"20190630_2",                 ( None, None)), # 31
    (r"20191006_proteins5",         (None, None)),  # 32
    (r"20191109",                   (None, None)),  # 33
    (r"20191201_1",                 (None, None)),  # --
    (r"20191207",                   (None, None)),  # --
    (r"20200121_3",                 (None, None)),  # 34
    (r"20200123_3",                 (None, None)),  # 35
    (r"20200218",                   (None, None)),  # --
    (r"20200304_1",                 (None, None)),  # --
    (r"20200304_2",                 (None, None)),  # --
    (r"20200624_2",                 (None, None)),  # --
    (r"20200624_3",                 (None, None)),  # --
    (r"20200624_4",                 (None, None)),  # --
    (r"20200630_1",                 (None, None)),  # --
    (r"20200630_10",                (None, None)),  # --
    (r"20200630_2",                 (None, None)),  # --
    (r"20200630_3",                 (None, None)),  # --
    (r"20200630_4",                 (None, None)),  # --
    (r"sample_data",                (135, None)),   # 36
]

def test_010_flowchange_exclude_slice():
    from molass.DataUtils.UvLoader import get_uvcurves
    from molass.FlowChange.FlowChange import flowchange_exclude_slice
    for k, (folder, result) in enumerate(TEST_TARGETS):
        path = os.path.join(DATA_ROOT_FOLDER, folder)
        print([k], "path=", path)
        c1, c2= get_uvcurves(path)
        i, j = flowchange_exclude_slice(c1, c2)[0]
        assert (k, (i,j)) == (k, result)    # using k in order to identify the case when it fails