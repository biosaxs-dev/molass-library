"""
DataUtils.ExportSsd.py
"""
import os
import numpy as np

def export_ssd_impl(self, folder, prefix=None, uv_device_id=None, fmt='%.18e', xr_only=False, uv_only=False):
    """Exports the SSD data to the specified folder.

    Parameters
    ----------
    folder : str
        The folder where the data will be exported.

    prefix : str, optional
        The prefix to be used for the exported files.

    xr_only : bool, optional
        If True, only export XR data.

    uv_only : bool, optional
        If True, only export UV data.

    Returns
    -------
    result : bool
        True if the export was successful, False otherwise.
    """
    if not os.path.exists(folder):
        os.makedirs(folder)

    if prefix is None:
        prefix = "PREFIX_"

    # Export XR data
    if self.xr is not None and not uv_only:
        qv = self.xr.qv
        n = 0
        for j in range(self.xr.M.shape[1]):
            xr_filename = os.path.join(folder, "%s%05d.dat" % (prefix, j))
            np.savetxt(xr_filename, np.array([qv, self.xr.M[:,j], self.xr.E[:,j]]).T, fmt=fmt)
            n += 1
        print(f"Exported {n} XR data files to {folder}.")

    # Export UV data
    if self.uv is not None and not xr_only:
        uv_filename = os.path.join(folder, "%sUV.txt" % prefix)
        fh = open(uv_filename, 'w')
        if uv_device_id is not None:    
            fh.write("Spectrometers:\t%s\n" % uv_device_id)
            fh.write(">>>> Data Start <<<<\n")
        uv_matrix_data = np.concatenate([self.uv.wv.reshape(-1, 1), self.uv.M], axis=1)
        np.savetxt(fh, uv_matrix_data, fmt=fmt)
        print(f"Exported UV data to {uv_filename}.")
