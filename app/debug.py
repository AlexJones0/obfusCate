""" File: debug.py
Implements classes for debugging the system, with a focus on logging functions."""
from typing import Callable
from app import settings as cfg
from time import localtime
from sys import stderr
import os


def print_error(*args, **kwargs):
    """Performs the `print()` command, but to the standard error stream."""
    print(*args, file=stderr, **kwargs)


def create_log_file(filepath: str = None) -> bool:
    """Creates a log file to be used throughout the program's execution and populates
    it with some initial log information.

    Args:
        filepath (str, optional): The path to the directory that the log file should
        be created in. Defaults to the LOG_PATH location stored in the config.

    Returns:
        bool: Whether execution was successful or not.
    """
    if not cfg.LOGS_ENABLED:
        return True
    if filepath is None:
        filepath = cfg.LOG_PATH
    filepath = os.getcwd() + filepath
    t = localtime()
    fname = "{}-{:02d}-{:02d}--{:02d}.{:02d}.{:02d}.txt".format(
        t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec
    )
    cfg.LOG_FILE = filepath + fname
    try:
        if not os.path.isdir(filepath):
            os.makedirs(filepath)
        with open(cfg.LOG_FILE, "w+") as log_file:
            log_file.write(
                f"=== LOG FILE FOR {cfg.NAME} {cfg.VERSION} AT {fname[:-4]} ===\n"
            )
        return True
    except OSError:
        print_error("Unable to open log file.")
    return False


def delete_log_file():
    try:
        os.remove(cfg.LOG_FILE)
        return True
    except OSError:
        print_error("Unable to remove log file.")
    return False


def log(log_str: str, print_err: bool = False) -> bool:
    """Writes a log message to the log file, attaching relevant time information.
    Requires a log file to have been created first during program runtime.

    Args:
        log_str (str): The message to log.
        print_err (bool): Whether to display the log message as an error to the user.

    Returns:
        bool: Whether execution was successful or not.
    """
    if print_err:
        print_error(log_str)
    if not cfg.LOGS_ENABLED:
        return True
    if len(cfg.LOG_FILE) == 0:
        print_error("Log file must first be created.")
        return False
    t = localtime()
    time_str = "[{:02d}:{:02d}:{:02d}] ".format(t.tm_hour, t.tm_min, t.tm_sec)
    try:
        with open(cfg.LOG_FILE, "a") as f:
            f.write(time_str + log_str + "\n")
        return True
    except OSError:
        print_error("Unable to write to log file.")
    return False


def time_function(func: Callable) -> Callable:
    """A decorator that the execution of a function and logs it. Uses locacl time."""
    from time import time as current_time

    def wrapper(*args, **kwargs):
        t = current_time()
        to_return = func(*args, **kwargs)
        log(f"{func.__name__}: {current_time() - t}")
        return to_return

    return wrapper
