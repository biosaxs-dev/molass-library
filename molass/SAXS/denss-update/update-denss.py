"""
    update-denss.py

    Copyright (c) 2022-2023, SAXS Team, KEK-PF
"""
import sys
import os
from shutil import copy
import diff_match_patch as dmp_module

try:
    GIT_REPOSITORY = r"D:\Github\denss"
    assert os.path.exists(GIT_REPOSITORY)
except:
    GIT_REPOSITORY = r"E:\Github\denss"
    assert os.path.exists(GIT_REPOSITORY)

denss_scripts = os.path.join(GIT_REPOSITORY, r"denss\scripts")
denss_lib = os.path.join(GIT_REPOSITORY, "denss")

temp_scripts = "scripts-temp"
temp_lib = "core-temp"

for path in [temp_scripts, temp_lib]:
    if not os.path.exists(path):
        os.makedirs(path)

this_dir = os.path.dirname(os.path.abspath( __file__ ))
root_dir = os.path.dirname(os.path.dirname(this_dir))
sys.path.insert(0, root_dir)

from molass_legacy.KekLib.DiffUtils import file2string, string2file

dmp = dmp_module.diff_match_patch()
dmp.Match_Distance = 5000

# bin
old_bin = "bin"

for file in ["denss_fit_data.py", "denss_pdb2mrc.py"]:
    orig_file = file.replace(".py", "-orig.py")

    old_src = file2string(os.path.join(old_bin, orig_file))
    mod_src = file2string(os.path.join(old_bin, file))

    patches = dmp.patch_make(old_src, mod_src)
    print(dmp.patch_toText(patches))

    git_src_path = os.path.join(denss_scripts, file)
    git_src = file2string(git_src_path)
    results = dmp.patch_apply(patches, git_src)

    new_src = results[0]
    print("=====================", results[1])
    assert results[1] == [True] * len(results[1])

    string2file(new_src, os.path.join(temp_scripts, file))
    copy(git_src_path, os.path.join(temp_scripts, orig_file))

exit()

# saxstats
old_lib = "saxstats"

for file in ["denssopts.py", "saxstats.py"]:
    orig_file = file.replace(".py", "-orig.py")

    old_src = file2string(os.path.join(old_lib, orig_file))
    mod_src = file2string(os.path.join(old_lib, file))

    patches = dmp.patch_make(old_src, mod_src)
    print(dmp.patch_toText(patches))

    git_src_path = os.path.join(git_lib, file)
    git_src = file2string(git_src_path)
    results = dmp.patch_apply(patches, git_src)

    new_src = results[0]
    print("=====================", results[1])
    assert results[1] == [True] * len(results[1])

    string2file(new_src, os.path.join(tmp_lib, file))
    copy(git_src_path, os.path.join(tmp_lib, orig_file))

for file in ["__init__.py", "_version.py"]:
    git_src_path = os.path.join(git_lib, file)
    copy(git_src_path, os.path.join(tmp_lib, file))
    print("copied", file)
