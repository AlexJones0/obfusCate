import os
from app import settings as cfg


def clean_dir() -> None:
    """A small utility to clean the testing directory, such that it can be reused."""
    test_path = os.path.join(os.getcwd(), "./tests/testing")
    if not os.path.isdir(test_path):
        return
    files = os.listdir(test_path)
    for file_ in files:
        os.remove(os.path.join(test_path, file_))


def reset_config() -> None:
    """Resets the state of the config used during testing to a default state,
    such that the config can be re-used between tests without mutation of state."""
    cfg.LOG_PATH = "./logs/"
    cfg.COMP_PATH = "./compositions/auto/"
    cfg.TEMP_FILE_PATH = "./obfuscate_temp.c"
    cfg.LOG_FILE = ""
    cfg.LOGS_ENABLED = True
    cfg.CALCULATE_COMPLEXITY = True
    cfg.DISPLAY_ERRORS = False
    cfg.SUPPRESS_ERRORS = False
    cfg.DISPLAY_PROGRESS = False
    cfg.SKIP_MENUS = False
    cfg.SAVE_COMPOSITION = False
    cfg.COMPOSITION = None
    cfg.SEED = None
    cfg.USE_ALLOCA = True
    cfg.USE_PATCHED_PARSER = True
