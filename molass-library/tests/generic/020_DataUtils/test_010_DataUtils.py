"""
    test DataUtils
"""
import os
from molass import get_version
get_version(toml_only=True)     # to ensure that the current repository is used
from molass.Local import get_local_settings
local_settings = get_local_settings()
TUTORIAL_DATA = local_settings['TUTORIAL_DATA']
DATA_ROOT_FOLDER = local_settings['DATA_ROOT_FOLDER']

def test_010_load_uv():
    from molass.DataUtils.UvLoader import load_uv
    uvM, wvector = load_uv(TUTORIAL_DATA)
    assert uvM.shape == (318,574), "uvM.shape should be (318,574)"
    assert len(wvector) == 318, "wvector should have length 318"    

    uvfile = os.path.join(TUTORIAL_DATA, 'SAMPLE_UV280_01.txt')
    uvM, wvector = load_uv(uvfile)
    assert uvM.shape == (318,574), "uvM.shape should be (318,574)"
    assert len(wvector) == 318, "wvector should have length 318"

def test_020_walk_folders():
    from molass.DataUtils.FolderWalker import walk_folders
    folders = []
    for folder in walk_folders(DATA_ROOT_FOLDER):
        folders.append(folder)
        if len(folders) >= 10:
            break
    assert len(folders) == 10, "Should find 10 folders"
    assert all(os.path.isdir(folder) for folder in folders), "All items should be directories"