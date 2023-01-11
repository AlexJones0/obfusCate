""" File: config.py
Implements classes to store system configs/settings."""


class Config(object):
    """Stores settings used by the program during its execution."""

    LOG_PATH = "./logs/"
    COMP_PATH = "./saved/"
    LOG_FILE = ""
    LOGS_ENABLED = True
    NAME = "obfusCated"
    VERSION = "v0.0.1"
    DISPLAY_ERRORS = False
    SUPPRESS_ERRORS = False
    DISPLAY_PROGRESS = False
    SAVE_COMPOSITION = False
    COMPOSITION = None
    SEED = None
