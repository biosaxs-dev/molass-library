"""
    DataUtils.PfBeamline.py

    Copyright (c) 2025, SAXS Team, KEK-PF
"""
import os

BEAMLINE_NAME = {
    "QEPB0040" : "PF BL-10C",
    "QEP01069" : "PF BL-15A2",
    "QEP03487" : "SPring-8 BL38B1",
    "FLMS00687" : "SPring-8 BL38B1",
    }

class BeamlineInfo:
    def __init__(self, **entries): 
        self.__dict__.update(entries)

    def get_concfactor(self):
        return self.path_length * self.extinction

    def __str__(self):
        return str(self.__dict__)

def get_beamlineinfo(folder):
    from glob import glob
    from molass_legacy.SerialAnalyzer.SerialDataUtils import get_uv_filename

    meter_name = None
    beamline = None
    file = get_uv_filename(folder)
    if file is not None:
        uvfile_path = os.path.join(folder, file)
        with open(uvfile_path) as fh:
            for k, line in enumerate(fh):
                if line.find('Spectrometers') >= 0:
                    meter_name = line.strip().split()[-1]
                    beamline = BEAMLINE_NAME.get(meter_name)
                    break

    return BeamlineInfo(meter_name=meter_name, name=beamline)

def get_beamlineinfo_from_settings():
    from molass_legacy._MOLASS.SerialSettings import get_setting
    meter_name = get_setting("uv_device_no")
    beamline = BEAMLINE_NAME.get(meter_name)
    path_length = get_setting('path_length')
    extinction = get_setting('extinction')
    return BeamlineInfo(meter_name=meter_name,
                        name=beamline,
                        path_length=path_length,
                        extinction=extinction,
                        )