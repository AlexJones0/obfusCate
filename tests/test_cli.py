import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
import os
import io
import random
from app import settings as cfg
from app.debug import *
from app.interaction import *
from tests import *
from pycparser.c_ast import FuncDef, Decl


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
            self.assertEqual(len(log_files), 0)
        self.assertEqual(len(cfg.LOG_FILE), 0)
        clean_dir()

    def test_log_creation_use_path_on_none(self):
        """Test that log creation will use the LOG_PATH setting if not supplied."""
        clean_dir()
        cfg.LOG_PATH = "/tests/testing/"
        cfg.LOGS_ENABLED = True
        self.assertTrue(create_log_file())
        log_files = os.listdir(os.getcwd() + "/tests/testing/")
        self.assertGreater(len(cfg.LOG_FILE), 0)
        self.assertEqual(len(log_files), 1)
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
        self.assertGreater(len(cfg.LOG_FILE), 0)
        self.assertEqual(len(log_files), 1)
        clean_dir()

    def test_logging_disabled(self):
        """Test that logging is actually disabled by the setting."""
        clean_dir()
        cfg.LOG_PATH = "/tests/testing/"
        cfg.LOG_FILE = ""
        cfg.LOGS_ENABLED = False
        self.assertTrue(log("Test message"))
        log_files = os.listdir(os.getcwd() + "/tests/testing")
        self.assertEqual(len(cfg.LOG_FILE), 0)
        self.assertEqual(len(log_files), 0)
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
        self.assertEqual(len(log_files), 1)
        with open(os.getcwd() + "/tests/testing/" + log_files[0], "r") as log_file:
            content = log_file.read().split("\n")[-2]
            self.assertNotEqual(content.find("Test message!"), -1)
        clean_dir()

    def test_time_function(self):
        """Tests that the time function decorator logs information as expected."""
        clean_dir()
        cfg.LOG_PATH = "/tests/testing/"
        cfg.LOGS_ENABLED = True
        self.assertTrue(create_log_file())
        self.garbage_func()
        log_files = os.listdir(os.getcwd() + "/tests/testing")
        self.assertEqual(len(log_files), 1)
        with open(os.getcwd() + "/tests/testing/" + log_files[0], "r") as log_file:
            content = log_file.read().split("\n")[-2]
            self.assertNotEqual(content.find("garbage_func"), -1)
        clean_dir()

    @time_function
    def garbage_func(self):
        """A garbage function used purely for testing the time_function decorator."""
        from time import sleep

        sleep(0.0675)


class TestIOFunctions(unittest.TestCase):
    """Implements unit tests for the io.py functions"""

    def test_csource_only_fname(self):
        """Tests that the CSource constructor works correctly when taking only a file name."""
        source = CSource(os.getcwd() + "/tests/data/minimal.c")
        self.assertEqual(source.contents, "int main() {}")
        self.assertIsNotNone(source.t_unit)
        del source

    def test_csource_fname_and_contents(self):
        """Tests that the CSource constructor works correctly when taking a file name and contents."""
        source = CSource(os.getcwd() + "/tests/data/minimal.c", "int main() {}")
        self.assertIsNotNone(source.t_unit)
        del source

    def test_csource_all_args(self):
        """Tests that the CSource constructor works correctly when taking all its arguments."""
        import clang.cindex

        index = clang.cindex.Index.create()
        fpath = os.getcwd() + "/tests/data/minimal.c"
        t_unit = index.parse(os.getcwd() + "/tests/data/minimal.c")
        source = CSource(fpath, "int main() {}", t_unit)
        self.assertIsNotNone(source.fpath)
        self.assertIsNotNone(source.contents)
        self.assertIsNotNone(source.t_unit)
        del source, t_unit, fpath, index

    def test_non_c_file(self):
        """Tests that the CSource constructor correctly fails on being given a non-C file."""
        source = CSource(os.getcwd() + "/tests/data/minimal.cpp")
        self.assertIsNone(source.contents)
        del source

    def test_non_existent_file(self):
        """Tests that the CSource constructor correctly fails on being given a file that
        does not exist."""
        source = CSource(os.getcwd() + "/tests/data/does_not_exist.c")
        self.assertIsNone(source.contents)
        del source

    def test_parse_invalid_c_file(self):
        """Tests that the CSource constructor correctly fails on being given an invalid
        C file (that cannot be parsed)."""
        source = CSource(os.getcwd() + "/tests/data/invalid.c")
        self.assertEqual(
            source.contents,
            """int main() {
    if 1 == 1 {
        return 1;
    }
}""",
        )
        self.assertFalse(source.valid_parse)
        del source

    def test_parse_valid_c_file(self):
        """Tests that the CSource constructor correctly parses a valid C file."""
        source = CSource(os.getcwd() + "/tests/data/minimal.c")
        self.assertEqual(source.contents, "int main() {}")
        self.assertTrue(source.valid_parse)
        self.assertTrue(isinstance(source.t_unit, FileAST))
        children = source.t_unit.children()
        self.assertEqual(len(children), 1)
        self.assertTrue(isinstance(children[0][1], FuncDef))
        self.assertTrue(isinstance(children[0][1].children()[0][1], Decl))
        self.assertEqual(children[0][1].children()[0][1].name, "main")
        del source

    def test_valid_parse_false(self):
        """Tests that the CSource.valid_parse property works correctly for a false case."""
        source = CSource(os.getcwd() + "/tests/data/invalid.c")
        self.assertFalse(source.valid_parse)
        del source

    def test_valid_parse_true(self):
        """Tests that the CSource.valid_parse property works correctly for a true case."""
        source = CSource(os.getcwd() + "/tests/data/minimal.c")
        self.assertTrue(source.valid_parse)
        del source

    def test_parse_errors_single_case(self):
        """Tests that the CSource.valid_parse property correctly detects single errors
        for an invalid C program."""
        source = CSource(os.getcwd() + "/tests/data/invalid.c")
        self.assertFalse(source.valid_parse)
        del source

    def test_parse_errors_multiple_case(self):
        """Tests that the CSource.valid_parse property correctly detects multiple errors
        found by clang for an invalid C program."""
        source = CSource(os.getcwd() + "/tests/data/five_invalid.c")
        self.assertFalse(source.valid_parse)
        del source

    def test_source_file_copy(self):
        """Tests that the Csource.copy function correclty returns a copy with a separate
        clang translation unit instance but the same name and file contents."""
        source = CSource(os.getcwd() + "/tests/data/minimal.c")
        copied = source.copy()
        self.assertEqual(source.fpath, copied.fpath)
        self.assertEqual(source.contents, copied.contents)
        self.assertIsNotNone(source.t_unit)
        self.assertIsNotNone(copied.t_unit)
        self.assertIsNot(source.t_unit, copied.t_unit)
        del source

    def test_menu_driven_no_args(self):
        """Tests that the menu_driven_option function in the `io.py` file can correctly
        handle the case where no options to select from are given."""
        # TODO add more when figured out capturing standard output and feeding to standard input
        with patch("sys.stdout", new=io.StringIO()) as output:
            result = menu_driven_option(list())
            self.assertEqual(result, 0)
            self.assertEqual(len(output.getvalue()), 0)
            del result

    def test_menu_driven_one_arg(self):
        """Tests that the menu_driven_option function in the `io.py` file can correctly handle
        the case where one option to select from is given."""
        output = io.StringIO()
        inputs = ["2", "0", "1"]
        with patch("builtins.input", side_effect=inputs), redirect_stdout(output):
            result = menu_driven_option(["test one"])
        self.assertEqual(result, 0)
        output = output.getvalue().split("\n")
        expected_out = [
            " (1) test one",
            "",
            " >Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.",
            " >Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.",
            " >",
        ]
        for i, line in enumerate(expected_out):
            self.assertEqual(output[i], line)
        del output, inputs, expected_out

    def test_menu_driven_multiple_args(self):
        """Tests that the menu_driven_option function in the `io.py` file can correctly handle
        the case where multiple options are given. Does this by simulating with 100 random tests,
        each using from 2 to 500 options, with an expected amount of around 9 invalid inputs per
        1 correct input to the menu."""
        potential_options = ["test {}".format(x) for x in range(500)]
        num_tests = 100
        for i in range(num_tests):
            chosen_options = random.randint(2, len(potential_options))
            available_options = [o for o in potential_options]
            chosen = []
            for _ in range(chosen_options):
                option = random.choice(available_options)
                chosen.append(option)
                available_options.remove(option)
            inputs = [0]
            upper_bound = 5 * chosen_options
            lower_bound = -upper_bound
            while inputs[-1] <= 0 or inputs[-1] > chosen_options:
                inputs.append(random.randint(lower_bound, upper_bound))
            inputs = [str(x) for x in inputs]
            expected_out = []
            for j, option in enumerate(chosen):
                expected_out.append(f" ({j+1}) {option}")
            expected_out.append("")
            for _ in range(len(inputs) - 1):
                expected_out.append(
                    " >Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit."
                )
            expected_out.append(" >")

            output = io.StringIO()
            with patch("builtins.input", side_effect=inputs), redirect_stdout(output):
                result = menu_driven_option(chosen)
            self.assertEqual(result, int(inputs[-1]) - 1)
            output = output.getvalue().split("\n")
            for i, line in enumerate(expected_out):
                self.assertEqual(output[i], line)

    def test_menu_driven_quits(self):
        """Tests that the menu_driven_option function in the `io.py` file can correctly handle
        user requests to quit the menu and exit the program."""
        quit_inputs = ["Q", "qUIt", "eXit    ", "  LEAVE    ", " X  "]
        with patch("builtins.input", side_effect=quit_inputs):
            for _ in quit_inputs:
                result = menu_driven_option(["option 1", "option 2", "option 3"])
                self.assertEqual(result, -1)

    def test_menu_driven_prompt(self):
        """Tests that prompts given to the menu_driven_option function in the `io.py` file actually
        displays the correct prompts to users."""
        output = io.StringIO()
        with patch("builtins.input", returns="1"), redirect_stdout(output):
            result = menu_driven_option(
                ["option 1", "option 2"], prompt="This is a test prompt."
            )
        self.assertEqual(result, 0)
        output = output.getvalue().split("\n")
        self.assertEqual(
            output, [" (1) option 1", " (2) option 2", "This is a test prompt.", " >"]
        )
        del output, result

    def test_menu_driven_no_prompt(self):
        """Tests that no prompt is displayed successfully if no prompt is given to the
        menu_driven_option function in the `io.py` file."""
        output = io.StringIO()
        with patch("builtins.input", returns="1"), redirect_stdout(output):
            result = menu_driven_option(["option 1", "option 2"], prompt=None)
        self.assertEqual(result, 0)
        output = output.getvalue().split("\n")
        self.assertEqual(output, [" (1) option 1", " (2) option 2", "", " >"])
        del output, result

    def test_menu_driven_only_keywords(self):
        """Tests that the menu_driven_option function in the `io.py` file can correctly handle
        the case where keywords are given to be used alongside options."""
        options = [
            ("test one", ["first", "hello"]),
            ("test two", ["second", "goodbye", "two"]),
        ]
        inputs = [
            "1",
            "2",
            "first",
            "second",
            "hello",
            "goodbye",
            "two",
            "other",
            "quit",
        ]
        results = [0, 1, 0, 1, 0, 1, 1, -1]
        with patch("builtins.input", side_effect=inputs):
            for i, _ in enumerate(results):
                result = menu_driven_option(options)
                self.assertEqual(result, results[i])
        del options, inputs, results, result

    def tests_menu_driven_keyword_mixed(self):
        """Tests that the menu_druven_option function in the `io.py` file can correctly handle
        the case where some options have keywords given to be used alongside options, and
        some do not."""
        output = io.StringIO()
        options = [
            ("test one", ["first", "test"]),
            "test two",
            ("test three", ["three"]),
            "test four",
        ]
        inputs = [
            "1",
            "2",
            "3",
            "4",
            "first",
            "test",
            "three",
            "two",
            "four",
            "other",
            "quit",
        ]
        results = [0, 1, 2, 3, 0, 0, 2, -1]
        with patch("builtins.input", side_effect=inputs), redirect_stdout(output):
            for i, _ in enumerate(results):
                result = menu_driven_option(options)
                self.assertEqual(result, results[i])
        output = output.getvalue().split("\n")
        self.assertEqual(
            output[-9:],
            [
                " > (1) test one",
                " (2) test two",
                " (3) test three",
                " (4) test four",
                "",
                " >Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.",
                " >Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.",
                " >Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.",
                " >",
            ],
        )
        del options, inputs, results, result, output

    def test_menu_driven_selection_too_small(self):
        """Tests that the menu_driven_option function in the `io.py` file can correctly handle
        the case where an integer of zero or below is given as the selected option."""
        output = io.StringIO()
        inputs = ["0", "-10000", "-1", "1"]
        with patch("builtins.input", side_effect=inputs), redirect_stdout(output):
            result = menu_driven_option(["option 1", "option 2"], prompt=None)
        self.assertEqual(result, 0)
        output = output.getvalue().split("\n")
        expected_out = [
            " (1) option 1",
            " (2) option 2",
            "",
            " >Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.",
            " >Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.",
            " >Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.",
            " >",
        ]
        self.assertEqual(output, expected_out)
        del inputs, output, result

    def test_menu_driven_selection_too_large(self):
        """Tests that the menu_driven_option function in the `io.py` file can correctly handle
        the case where an integer greater than then number of supplied options is given as
        the selected option."""
        output = io.StringIO()
        inputs = ["4", "5000345345", "5", "3"]
        with patch("builtins.input", side_effect=inputs), redirect_stdout(output):
            result = menu_driven_option(
                ["option 1", "option 2", "option 3"], prompt=None
            )
        self.assertEqual(result, 2)
        output = output.getvalue().split("\n")
        expected_out = [
            " (1) option 1",
            " (2) option 2",
            " (3) option 3",
            "",
            " >Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.",
            " >Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.",
            " >Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.",
            " >",
        ]
        self.assertEqual(output, expected_out)
        del inputs, output, result

    def test_menu_driven_selection_not_int(self):
        """Tests that the menu_driven_option function in the `io.py` file can correctly handle
        the case where a non-integer is given as the selected option."""
        output = io.StringIO()
        inputs = ["4.3592", "abcdef", "42O", "2"]
        with patch("builtins.input", side_effect=inputs), redirect_stdout(output):
            result = menu_driven_option(["option 1", "option 2"], prompt=None)
        self.assertEqual(result, 1)
        output = output.getvalue().split("\n")
        expected_out = [
            " (1) option 1",
            " (2) option 2",
            "",
            " >Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.",
            " >Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.",
            " >Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.",
            " >",
        ]
        self.assertEqual(output, expected_out)
        del inputs, output, result


class TestMainCLIFunctions(unittest.TestCase):
    """Implements unit tests for the cli.py functions"""
    pass


class TestObfuscationCLIFunctions(unittest.TestCase):
    """Implements unit test for the obfuscation edit_cli and get_cli methods in obfuscation.py"""
    pass
        


if __name__ == "__main__":
    unittest.main()
