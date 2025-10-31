"""
Logging.Utils.py

Logging utilities for the Molass library.
"""

import logging
import sys

def setup_notebook_logging():
    """
    Setup logging to display messages in Jupyter notebooks.

    Returns
    -------
    logger : logging.Logger
        Configured logger for notebook output.
    """
    logger = logging.getLogger()  # Or use the specific logger name if needed
    logger.setLevel(logging.INFO)  # Or your desired level

    # Remove existing handlers to avoid duplicate logs
    logger.handlers = []

    # Add a StreamHandler for notebook output
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(handler)
    return logger