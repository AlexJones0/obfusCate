import os

def clean_dir():
    """A small utility to clean the testing directory, such that it can be reused."""
    test_path = os.getcwd() + "/tests/testing"
    if not os.path.isdir(test_path):
        return
    log_files = os.listdir(test_path)
    for file_ in log_files:
        if file_.endswith(".txt"):
            os.remove(os.path.join(test_path, file_))