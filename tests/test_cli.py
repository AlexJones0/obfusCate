import unittest
from venv import create
from app import settings as cfg
from app.debug import *
from app.io import *
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


class TestDebugFunctions(unittest.TestCase):
    """Implements unit tests for the debug.py functions"""
    
    def test_log_creation_disabled(self):
        """Test that log creation is actually disabled by the setting."""
        clean_dir()
        cfg.LOG_PATH = "/tests/testing/"
        cfg.LOG_FILE = ""
        cfg.LOGS_ENABLED = False
        self.assertTrue(create_log_file(cfg.LOG_PATH))
        if os.path.isdir(os.getcwd() + "/tests/testing"):
            log_files = os.listdir(os.getcwd() + "/tests/testing")
            self.assertTrue(len(log_files) == 0)
        self.assertTrue(len(cfg.LOG_FILE) == 0)
        clean_dir()

    def test_log_creation_use_path_on_none(self):
        """Test that log creation will use the LOG_PATH setting if not supplied."""
        clean_dir()
        cfg.LOG_PATH = "/tests/testing/"
        cfg.LOGS_ENABLED = True
        self.assertTrue(create_log_file())
        log_files = os.listdir(os.getcwd() + "/tests/testing/")
        self.assertTrue(len(cfg.LOG_FILE) > 0)
        self.assertTrue(len(log_files) == 1)
        clean_dir()

    def test_log_dir_creation(self):
        """Test that log creation will create the log directories if needed."""
        if os.path.isdir(os.getcwd() + "/tests/testing/dir/"):
            log_files = os.listdir(os.getcwd() + "/tests/testing/dir/")
            for file_ in log_files:
                os.remove(os.path.join(os.getcwd() + "/tests/testing/dir/", file_))
            os.rmdir(os.getcwd() + "/tests/testing/dir/")
        cfg.LOG_PATH = "/tests/testing/dir/"
        cfg.LOGS_ENABLED = True
        self.assertTrue(create_log_file(cfg.LOG_PATH))
        self.assertTrue(os.path.isdir(os.getcwd() + "/tests/testing/dir/"))
        log_files = os.listdir(os.getcwd() + "/tests/testing/dir/")
        for file_ in log_files:
            os.remove(os.path.join(os.getcwd() + "/tests/testing/dir/", file_))
        os.rmdir(os.getcwd() + "/tests/testing/dir/")

    def test_normal_log_creation(self):
        """Test that regular use of log creation does indeed create a log file."""
        clean_dir()
        cfg.LOG_PATH = "/tests/testing/"
        cfg.LOGS_ENABLED = True
        self.assertTrue(create_log_file(cfg.LOG_PATH))
        log_files = os.listdir(os.getcwd() + "/tests/testing/")
        self.assertTrue(len(cfg.LOG_FILE) > 0)
        self.assertTrue(len(log_files) == 1)
        clean_dir()

    def test_logging_disabled(self):
        """Test that logging is actually disabled by the setting."""
        clean_dir()
        cfg.LOG_PATH = "/tests/testing/"
        cfg.LOG_FILE = ""
        cfg.LOGS_ENABLED = False
        self.assertTrue(log("Test message"))
        log_files = os.listdir(os.getcwd() + "/tests/testing")
        self.assertTrue(len(cfg.LOG_FILE) == 0)
        self.assertTrue(len(log_files) == 0)
        clean_dir()

    def test_logging_before_creation(self):
        """Test that logging requires the log file to be created first."""
        clean_dir()
        cfg.LOG_PATH = "/tests/testing/"
        cfg.LOG_FILE = ""
        cfg.LOGS_ENABLED = True
        self.assertFalse(log("Test message"))
        clean_dir()

    def test_normal_logging(self):
        """Tests that regular logging behaviour functions as expected."""
        clean_dir()
        cfg.LOG_PATH = "/tests/testing/"
        cfg.LOGS_ENABLED = True
        self.assertTrue(create_log_file())
        self.assertTrue(log("Test message!"))
        log_files = os.listdir(os.getcwd() + "/tests/testing")
        self.assertTrue(len(log_files) == 1)
        with open(os.getcwd() + "/tests/testing/" + log_files[0], "r") as log_file:
            content = log_file.read().split("\n")[-2]
            self.assertTrue(content.find("Test message!") != -1)
        clean_dir()

    def test_time_function(self):
        """Tests that the time function decorator logs information as expected."""
        clean_dir()
        cfg.LOG_PATH = "/tests/testing/"
        cfg.LOGS_ENABLED = True
        self.assertTrue(create_log_file())
        self.garbage_func()
        log_files = os.listdir(os.getcwd() + "/tests/testing")
        self.assertTrue(len(log_files) == 1)
        with open(os.getcwd() + "/tests/testing/" + log_files[0], "r") as log_file:
            content = log_file.read().split("\n")[-2]
            self.assertTrue(content.find("garbage_func") != -1)
        clean_dir()

    @time_function
    def garbage_func(self):
        """A garbage function used purely for testing the time_function decorator."""
        from time import sleep

        sleep(0.0675)


class TestIOFunctions(unittest.TestCase):
    """Implements unit tests for the io.py functions """
    
    def test_csource_only_fname(self):
        """ Tests that the CSource constructor works correctly when taking only a file name."""
        source = CSource(os.getcwd() + "/tests/data/minimal.c")
        self.assertTrue(source.contents == "int main() {}")
        self.assertTrue(source.t_unit is not None)
        del source

    def test_csource_fname_and_contents(self):
        """ Tests that the CSource constructor works correctly when taking a file name and contents."""
        source = CSource(os.getcwd() + "/tests/data/minimal.c", "int main() {}")
        self.assertTrue(source.t_unit is not None)
        del source

    def test_csource_all_args(self):
        """ Tests that the CSource constructor works correctly when taking all its arguments."""
        import clang.cindex

        index = clang.cindex.Index.create()
        fpath = os.getcwd() + "/tests/data/minimal.c"
        t_unit = index.parse(os.getcwd() + "/tests/data/minimal.c")
        source = CSource(fpath, "int main() {}", t_unit)
        del source, t_unit, fpath, index

    def test_non_c_file(self):
        """ Tests that the CSource constructor correctly fails on being given a non-C file."""
        source = CSource(os.getcwd() + "/tests/data/minimal.cpp")
        self.assertTrue(source.contents is None)
        del source

    def test_non_existent_file(self):
        """ Tests that the CSource constructor correctly fails on being given a file that
        does not exist. """
        source = CSource(os.getcwd() + "/tests/data/does_not_exist.c")
        self.assertTrue(source.contents is None)
        del source


if __name__ == "__main__":
    unittest.main()
