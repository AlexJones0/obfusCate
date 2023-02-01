""" File: config.py
Implements classes to store system configs/settings."""


class Config(object):
    """Stores settings used by the program during its execution."""

    LOG_PATH = ".\\logs\\"
    COMP_PATH = ".\\compositions\\auto\\"
    TEMP_FILE_PATH = ".\\obfuscate_temp.c"
    LOG_FILE = ""
    LOGS_ENABLED = True
    NAME = "obfusCate"
    VERSION = "v0.15.4"
    DISPLAY_ERRORS = False
    SUPPRESS_ERRORS = False
    DISPLAY_PROGRESS = False
    SAVE_COMPOSITION = False
    COMPOSITION = None
    SEED = None
