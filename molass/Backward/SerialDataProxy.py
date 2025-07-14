"""
Backward.SerialData.py
"""

class SerialDataProxy:
    """
    SerialData class to hold data for serial processing.
    This class is used to store the data that will be processed in a serial manner.
    """
    def __init__(self, ssd, concentration):
        self.mc_vector = concentration.curve.y
