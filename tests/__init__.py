import os

def clean_dir():
    """A small utility to clean the testing directory, such that it can be reused."""
    test_path = os.getcwd() + "/tests/testing"
    if not os.path.isdir(test_path):
        return
    files = os.listdir(test_path)
    for file_ in files:
        os.remove(os.path.join(test_path, file_))