"""
    update-custom-codes.py

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

git_bin = os.path.join(GIT_REPOSITORY, "bin")
git_lib = os.path.join(GIT_REPOSITORY, "saxstats")

this_dir = os.path.dirname(os.path.abspath( __file__ ))
sys.path.append( this_dir + '/../../lib' )

import molass_legacy.KekLib
from DiffUtils import file2string, string2file

dmp = dmp_module.diff_match_patch()
dmp.Patch_DeleteThreshold = 0.7
dmp.Match_Distance = 5000

# saxstats
old_bin = "bin"
old_src_path = os.path.join(old_bin, "denss.fit_data.py")
old_fit_data = file2string(old_src_path)
tmp_bin = "bin-temp"
tmp_src_path = os.path.join(tmp_bin, "denss.fit_data.py")
tmp_fit_data = file2string(tmp_src_path)

def extract_func(path):
    extracted = []
    in_the_func = False
    with open(path) as fh:
        for line in fh:
            if line.find("def estimate_dmax(") >= 0:
                in_the_func = True

            if in_the_func:
                extracted.append(line)
                if line.find("return") >= 0:
                    break
    return "".join(extracted)

old_lib = "saxstats"
old_src_path = os.path.join(old_lib, "saxstats.py")
old_saxstats = extract_func(old_src_path)

tmp_lib = "saxstats-temp"
tmp_src_path = os.path.join(tmp_lib, "saxstats.py")
tmp_saxstats = extract_func(tmp_src_path)

k = 0
for old_src, file, tmp_src in [
                        (old_fit_data, "DenssUtils.py", tmp_fit_data), 
                        (old_saxstats, "DmaxEstimation.py", tmp_saxstats)]:

    mod_src = file2string(file)
    patches = dmp.patch_make(old_src, mod_src)
    print(dmp.patch_toText(patches))

    results = dmp.patch_apply(patches, tmp_src)

    new_src = results[0]
    print("=====================", results[1])
    assert results[1] == [True] * len(results[1])

    temp_file = file.replace(".py", "-temp.py")
    # string2file(new_src, temp_file)
    with open(temp_file, "w", newline="\n") as fh:
        fh.write(new_src)
