"""
Bridge.V2Result.py
"""
import os
import numpy as np
from molass.Trimming.TrimmingInfo import TrimmingInfo as MoTrimmingInfo

def get_num_components_assumming_egh(length):
    """
    n * 4 + n + 2 + n + 7 + 2 + 2 + 6 = n * 6 + 19
    """
    n, r = divmod(length - 19, 6)
    assert r == 0, f"Invalid number of parameters: {length}"
    return n

def extract_params_assumming_egh(params):
    n = get_num_components_assumming_egh(len(params))
    return params[0:n*4].reshape((n,4))

class V2Result:
    """
    V2Result class
    """
    def __init__(self, folder):
        self.folder = folder
        self.trimming = self.import_trimming()
        self.init_params = self.import_init_params()
        self.best_params = None

    def import_trimming(self):
        """
        Import the parameters from the V2 result folder.
        """
        trimming_txt = os.path.join(self.folder, "trimming.txt")
        try:
            from molass_legacy.Trimming.TrimmingInfo import TrimmingInfo
            trimming_list = []
            with open(trimming_txt, 'r') as f:
                for line in f:
                    trimming_list.append(eval(line))
        except Exception as e:
            raise Exception(f"Error while importing trimming from {trimming_txt}: {e}")
    
        slice_pairs = []
        for jtrim, itrim in trimming_list:
            slice_pairs.append([slice(itrim.start, itrim.stop), slice(jtrim.start, jtrim.stop)])
        uv_slices, xr_slices= slice_pairs

        return MoTrimmingInfo(xr_slices=xr_slices, uv_slices=uv_slices)

    def import_init_params(self):
        """
        Import the parameters from the V2 result folder.
        """
        init_params_txt = os.path.join(self.folder, "init_params.txt")
        try:
            parameters = np.loadtxt(init_params_txt)
        except Exception as e:
            raise Exception(f"Error while importing parameters from {init_params_txt}: {e}")

        x0 = self.trimming.xr_slices[1].start        
        params = extract_params_assumming_egh(parameters)
        ret_params = []
        for h, m, s, t in params:
            ret_params.append([h, m + x0, s, t])
        return ret_params

    def get_init_params(self):
        """
        Get the parameters
        """
        return self.init_params

    def import_best_params(self):
        """
        Import the best parameters
        """


    def get_best_params(self):
        """
        Get the best parameters
        """
        if self.best_params is None:
            self.best_params = self.import_best_params()
        return self.best_params

    def get_trimming(self):
        """
        Get the trimming
        """
        return self.trimming

    def get_original_ssd(self):
        """
        Get the original ssd
        """
        from molass.DataObjects import SecSaxsData as SSD
        in_data_info_txt = os.path.join(self.folder, "in_data_info.txt")
        with open(in_data_info_txt, 'r') as fh:
            lines = fh.readlines()
            in_folder = lines[0].strip().split('=')[1]

        assert os.path.exists(in_folder), f"Input folder {in_folder} does not exist."
        return SSD(in_folder)

    def get_trimmed_ssd(self):
        """
        Get the trimmed ssd
        """
        ssd0 = self.get_original_ssd()
        return ssd0.trimmed_copy(self.trimming)