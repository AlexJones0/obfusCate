import unittest
from unittest.mock import patch
from contextlib import redirect_stdout, redirect_stderr
import os
import io
import random
import math
from app import settings as cfg
from app.debug import *
from app.interaction import *
from app.utils import *
from tests import *
from pycparser.c_ast import FuncDef, Decl
from time import sleep


class TestDebugFunctions(unittest.TestCase):
    """Implements unit tests for the debug.py functions"""

    def test_log_creation_disabled(self) -> None:
        """Test that log creation is actually disabled by the setting."""
        clean_dir()
        cfg.LOG_PATH = "./tests/testing/"
        cfg.LOG_FILE = ""
        cfg.LOGS_ENABLED = False
        self.assertTrue(create_log_file(cfg.LOG_PATH))
        if os.path.isdir(os.path.join(os.getcwd(), "./tests/testing")):
            log_files = os.listdir(os.path.join(os.getcwd(), "./tests/testing"))
            self.assertEqual(len(log_files), 0)
        self.assertEqual(len(cfg.LOG_FILE), 0)
        clean_dir()

    def test_log_creation_use_path_on_none(self) -> None:
        """Test that log creation will use the LOG_PATH setting if not supplied."""
        clean_dir()
        cfg.LOG_PATH = "./tests/testing/"
        cfg.LOGS_ENABLED = True
        self.assertTrue(create_log_file())
        log_files = os.listdir(os.path.join(os.getcwd(), "./tests/testing/"))
        self.assertGreater(len(cfg.LOG_FILE), 0)
        self.assertEqual(len(log_files), 1)
        clean_dir()

    def test_log_dir_creation(self) -> None:
        """Test that log creation will create the log directories if needed."""
        if os.path.isdir(os.path.join(os.getcwd(), "./tests/testing/dir/")):
            log_files = os.listdir(os.path.join(os.getcwd(), "./tests/testing/dir/"))
            for file_ in log_files:
                os.remove(os.path.join(os.path.join(os.getcwd(), "./tests/testing/dir/", file_)))
            os.rmdir(os.path.join(os.getcwd(), "./tests/testing/dir/"))
        cfg.LOG_PATH = "./tests/testing/dir/"
        cfg.LOGS_ENABLED = True
        self.assertTrue(create_log_file(cfg.LOG_PATH))
        self.assertTrue(os.path.isdir(os.path.join(os.getcwd(), "./tests/testing/dir/")))
        log_files = os.listdir(os.path.join(os.getcwd(), "./tests/testing/dir/"))
        for file_ in log_files:
            os.remove(os.path.join(os.path.join(os.getcwd(), "./tests/testing/dir/", file_)))
        os.rmdir(os.path.join(os.getcwd(), "./tests/testing/dir/"))

    def test_normal_log_creation(self) -> None:
        """Test that regular use of log creation does indeed create a log file."""
        clean_dir()
        cfg.LOG_PATH = "./tests/testing/"
        cfg.LOGS_ENABLED = True
        self.assertTrue(create_log_file(cfg.LOG_PATH))
        log_files = os.listdir(os.path.join(os.getcwd(), "./tests/testing/"))
        self.assertGreater(len(cfg.LOG_FILE), 0)
        self.assertEqual(len(log_files), 1)
        clean_dir()

    def test_logging_disabled(self) -> None:
        """Test that logging is actually disabled by the setting."""
        clean_dir()
        cfg.LOG_PATH = "./tests/testing/"
        cfg.LOG_FILE = ""
        cfg.LOGS_ENABLED = False
        self.assertTrue(log("Test message"))
        log_files = os.listdir(os.path.join(os.getcwd(), "./tests/testing"))
        self.assertEqual(len(cfg.LOG_FILE), 0)
        self.assertEqual(len(log_files), 0)
        clean_dir()

    def test_logging_before_creation(self) -> None:
        """Test that logging requires the log file to be created first."""
        clean_dir()
        cfg.LOG_PATH = "./tests/testing/"
        cfg.LOG_FILE = ""
        cfg.LOGS_ENABLED = True
        self.assertFalse(log("Test message"))
        clean_dir()

    def test_normal_logging(self) -> None:
        """Tests that regular logging behaviour functions as expected."""
        clean_dir()
        cfg.LOG_PATH = "./tests/testing/"
        cfg.LOGS_ENABLED = True
        self.assertTrue(create_log_file())
        self.assertTrue(log("Test message!"))
        log_files = os.listdir(os.path.join(os.getcwd(), "./tests/testing"))
        self.assertEqual(len(log_files), 1)
        with open(os.path.join(os.getcwd(), "./tests/testing/") + log_files[0], "r") as log_file:
            content = log_file.read().split("\n")[-2]
            self.assertNotEqual(content.find("Test message!"), -1)
        clean_dir()

    def test_error_printing(self) -> None:
        """Tests that errors are printed to the standard error stream, and not
        the standard output stream. """
        clean_dir()
        err = io.StringIO()
        out = io.StringIO()
        err_msg = "This is an error message."
        with redirect_stderr(err), redirect_stdout(out):
            print_error(err_msg)
        self.assertNotIn(err_msg, out.getvalue())

    def test_normal_log_deletion(self) -> None:
        """Tests that the `delete_log_file()` function works normally."""
        clean_dir()
        cfg.LOG_PATH = "./tests/testing/"
        with open("./tests/testing/logger.txt", "w+") as f:
            f.write("some stuff...\n")
        cfg.LOG_FILE = "./tests/testing/logger.txt"
        cfg.LOGS_ENABLED = True
        self.assertIn("logger.txt", os.listdir("./tests/testing/"))
        delete_log_file()
        self.assertNotIn("logger.txt", os.listdir("./tests/testing/"))
    
    def test_log_deletion_no_file(self) -> None:
        """Tests that the `delete_log_file()` function works with no log 
        file specified. """
        clean_dir()
        cfg.LOG_FILE = None
        self.assertFalse(delete_log_file())
        cfg.LOG_FILE = ""
        self.assertFalse(delete_log_file())
    
    def test_log_deletion_no_longer_exists(self) -> None:
        """Tests that the `delete_log_file()` function can handle the case 
        where the log file no longer exists. """
        clean_dir()
        cfg.LOG_PATH = "./tests/testing/"
        cfg.LOG_FILE = "./tests/testing/logger.txt"
        cfg.LOGS_ENABLED = True
        self.assertFalse(delete_log_file())

    def test_logprint(self) -> None:
        """Tests that the `logprint` function works as expected."""
        clean_dir()
        cfg.LOG_PATH = "./tests/testing/"
        cfg.LOGS_ENABLED = True
        self.assertTrue(create_log_file())
        err = io.StringIO()
        out = io.StringIO()
        with redirect_stderr(err), redirect_stdout(out):
            self.assertTrue(logprint("Test message!"))
        self.assertNotIn("Test message!", out)
        log_files = os.listdir(os.path.join(os.getcwd(), "./tests/testing"))
        self.assertEqual(len(log_files), 1)
        with open(os.path.join(os.getcwd(), "./tests/testing/") + log_files[0], "r") as log_file:
            content = log_file.read().split("\n")[-2]
            self.assertNotEqual(content.find("Test message!"), -1)
        clean_dir()

    def test_time_function(self) -> None:
        """Tests that the time function decorator logs information as expected."""
        clean_dir()
        cfg.LOG_PATH = "./tests/testing/"
        cfg.LOGS_ENABLED = True
        self.assertTrue(create_log_file())
        self.garbage_func()
        log_files = os.listdir(os.path.join(os.getcwd(), "./tests/testing"))
        self.assertEqual(len(log_files), 1)
        with open(os.path.join(os.getcwd(), "./tests/testing/") + log_files[0], "r") as log_file:
            content = log_file.read().split("\n")[-2]
            self.assertNotEqual(content.find("garbage_func"), -1)
        clean_dir()

    @time_function
    def garbage_func(self) -> None:
        """A garbage function used purely for testing the time_function decorator."""

        sleep(0.0675)


class TestInteractionFunctions(unittest.TestCase):
    """Implements unit tests for the interactions.py functions"""

    def test_csource_only_fname(self) -> None:
        """Tests that the CSource constructor works correctly when taking only a file name."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        self.assertEqual(source.contents, "int main() {}")
        self.assertIsNotNone(source.t_unit)
        del source

    def test_csource_fname_and_contents(self) -> None:
        """Tests that the CSource constructor works correctly when taking a file name and contents."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"), "int main() {}")
        self.assertIsNotNone(source.t_unit)
        del source

    def test_csource_all_args(self) -> None:
        """Tests that the CSource constructor works correctly when taking all its arguments."""
        import clang.cindex

        index = clang.cindex.Index.create()
        fpath = os.path.join(os.getcwd(), "./tests/data/minimal.c")
        t_unit = index.parse(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        source = CSource(fpath, "int main() {}", t_unit)
        self.assertIsNotNone(source.fpath)
        self.assertIsNotNone(source.contents)
        self.assertIsNotNone(source.t_unit)
        del source, t_unit, fpath, index

    def test_non_c_file(self) -> None:
        """Tests that the CSource constructor correctly fails on being given a non-C file."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.cpp"))
        self.assertIsNone(source.contents)
        del source

    def test_non_existent_file(self) -> None:
        """Tests that the CSource constructor correctly fails on being given a file that
        does not exist."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/does_not_exist.c"))
        self.assertIsNone(source.contents)
        del source

    def test_parse_invalid_c_file(self) -> None:
        """Tests that the CSource constructor correctly fails on being given an invalid
        C file (that cannot be parsed)."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/invalid.c"))
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

    def test_parse_valid_c_file(self) -> None:
        """Tests that the CSource constructor correctly parses a valid C file."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        self.assertEqual(source.contents, "int main() {}")
        self.assertTrue(source.valid_parse)
        self.assertTrue(isinstance(source.t_unit, FileAST))
        children = source.t_unit.children()
        self.assertEqual(len(children), 1)
        self.assertTrue(isinstance(children[0][1], FuncDef))
        self.assertTrue(isinstance(children[0][1].children()[0][1], Decl))
        self.assertEqual(children[0][1].children()[0][1].name, "main")
        del source

    def test_valid_parse_false(self) -> None:
        """Tests that the CSource.valid_parse property works correctly for a false case."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/invalid.c"))
        self.assertFalse(source.valid_parse)
        del source

    def test_valid_parse_true(self) -> None:
        """Tests that the CSource.valid_parse property works correctly for a true case."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        self.assertTrue(source.valid_parse)
        del source

    def test_parse_errors_single_case(self) -> None:
        """Tests that the CSource.valid_parse property correctly detects single errors
        for an invalid C program."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/invalid.c"))
        self.assertFalse(source.valid_parse)
        del source

    def test_parse_errors_multiple_case(self) -> None:
        """Tests that the CSource.valid_parse property correctly detects multiple errors
        found by clang for an invalid C program."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/five_invalid.c"))
        self.assertFalse(source.valid_parse)
        del source

    def test_source_file_copy(self) -> None:
        """Tests that the Csource.copy function correclty returns a copy with a separate
        clang translation unit instance but the same name and file contents."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        copied = source.copy()
        self.assertEqual(source.fpath, copied.fpath)
        self.assertEqual(source.contents, copied.contents)
        self.assertIsNotNone(source.t_unit)
        self.assertIsNotNone(copied.t_unit)
        self.assertIsNot(source.t_unit, copied.t_unit)
        del source
    
    def test_update_t_unit(self) -> None:
        """ Tests that the CSource can update its AST (t_unit) from its contents
        without changing the original file by writing to and reading from a temp file."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        prev_contents = source.contents
        prev_t_unit = source.t_unit
        source.contents = "int main() { int x = 4 + 2; return x; }"
        self.assertFalse(os.path.exists(cfg.TEMP_FILE_PATH))
        self.assertNotEqual(prev_contents, source.contents)
        self.assertIs(prev_t_unit, source.t_unit)
        source.update_t_unit()
        self.assertIsNot(prev_t_unit, source.t_unit)
        new_source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        self.assertEqual(prev_contents, new_source.contents)
        self.assertNotEqual(new_source.contents, source.contents)
        self.assertFalse(os.path.exists(cfg.TEMP_FILE_PATH))
    
    def test_update_t_unit_no_temp(self) -> None:
        """ Tests that the CSource's `update_t_unit()` method can handle
        the case where No (or an empty) temporary file path is given. """
        cfg.TEMP_FILE_PATH = None
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        prev_t_unit = source.t_unit
        source.contents = "int main() { int x = 4 + 2; return x; }"
        self.assertIsNone(source.update_t_unit())
        self.assertIs(prev_t_unit, source.t_unit)
        cfg.TEMP_FILE_PATH = ""
        self.assertIsNone(source.update_t_unit())
        self.assertIs(prev_t_unit, source.t_unit)
        
    def test_construct_systemopt(self) -> None:
        """ Test that a SystemOpt object can be constructed successfully. """
        opt_func = clean_dir
        names = ["One", "Two", "Three"]
        desc = "This is a description."
        param_names = ["x", "y", "z"]
        opt = SystemOpt(opt_func, names, desc, param_names)
        self.assertIs(opt.func, opt_func)
        self.assertIs(opt.names, names)
        self.assertIs(opt.desc, desc)
        self.assertIs(opt.param_names, param_names)
    
    def test_systemopt_str(self) -> None:
        """ Tests that valid string representations of SystemOpts can be created. """
        opt_func = clean_dir
        names = ["One", "Two", "Three"]
        param_names = ["x", "y", "z"]
        desc = "This is a description."
        opt = SystemOpt(opt_func, [], desc, [])
        self.assertEqual(str(opt), "")
        opt.names = names
        self.assertEqual(str(opt), "One Two Three")
        opt.param_names = param_names
        self.assertEqual(str(opt), "One Two Three x y z")
        
    def test_systemopt_desc_str(self) -> None:
        """ Tests that valid help menu description strings can be created for
        system options, both with one and multiple lines. """
        opt_func = clean_dir
        names = ["One", "Two", "Three"]
        desc = "This is a description."
        param_names = ["x", "y", "z"]
        opt = SystemOpt(opt_func, names, desc, param_names)
        self.assertEqual(desc, opt.get_desc_str(0))
        self.assertEqual(desc, opt.get_desc_str(10000))
        opt.desc += "\nThis is a second line.\nThis is a third line."
        self.assertEqual("This is a description.\n| This is a second line.\n| This is a third line.",
                         opt.get_desc_str(0))
        self.assertEqual("This is a description.\n      | This is a second line.\n      | This is a third line.",
                         opt.get_desc_str(6))
        
    def test_menu_driven_no_args(self) -> None:
        """Tests that the menu_driven_option function in the `io.py` file can correctly
        handle the case where no options to select from are given."""
        with patch("sys.stdout", new=io.StringIO()) as output:
            result = menu_driven_option(list())
            self.assertEqual(result, 0)
            self.assertEqual(len(output.getvalue()), 0)
            del result

    def test_menu_driven_one_arg(self) -> None:
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

    def test_menu_driven_multiple_args(self) -> None:
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

    def test_menu_driven_quits(self) -> None:
        """Tests that the menu_driven_option function in the `io.py` file can correctly handle
        user requests to quit the menu and exit the program."""
        quit_inputs = ["Q", "qUIt", "eXit    ", "  LEAVE    ", " X  "]
        with patch("builtins.input", side_effect=quit_inputs):
            for _ in quit_inputs:
                result = menu_driven_option(["option 1", "option 2", "option 3"])
                self.assertEqual(result, -1)

    def test_menu_driven_prompt(self) -> None:
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

    def test_menu_driven_no_prompt(self) -> None:
        """Tests that no prompt is displayed successfully if no prompt is given to the
        menu_driven_option function in the `io.py` file."""
        output = io.StringIO()
        with patch("builtins.input", returns="1"), redirect_stdout(output):
            result = menu_driven_option(["option 1", "option 2"], prompt=None)
        self.assertEqual(result, 0)
        output = output.getvalue().split("\n")
        self.assertEqual(output, [" (1) option 1", " (2) option 2", "", " >"])
        del output, result

    def test_menu_driven_only_keywords(self) -> None:
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

    def tests_menu_driven_keyword_mixed(self) -> None:
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

    def test_menu_driven_selection_too_small(self) -> None:
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

    def test_menu_driven_selection_too_large(self) -> None:
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

    def test_menu_driven_selection_not_int(self) -> None:
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
    
    def test_get_float_valid(self) -> None:
        """ Tests that the `get_float()` function works for valid inputs."""
        inputs = ["2.596", "4"]
        with patch("builtins.input", side_effect=inputs):
            result1 = get_float(2.5, 2.6)
            result2 = get_float(3, 5)
        self.assertEqual(result1, 2.596)
        self.assertEqual(result2, 4.0)
    
    def test_get_float_not_number(self) -> None:
        """ Tests that the `get_float()` function handles non-numeric inputs. """
        inputs = ["", "abcdefgh", "5.70000O", ".596"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(out):
            result = get_float()
        self.assertEqual(result, 0.596)
        out = out.getvalue().split("\n")
        expected_out = [
            "Invalid input for a decimal number. Please try again...",
            "Invalid input for a decimal number. Please try again...",
            "Invalid input for a decimal number. Please try again..."
        ]
        for i, line in enumerate(expected_out):
            self.assertEqual(out[i], line)
    
    def test_get_float_lower_bound(self) -> None:
        """ Tests that the `get_float()` function correctly implements lower bounds. """
        inputs = ["-4.505", "-4.5045", "-4.504", "-4.5035"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(out):
            result1 = get_float(lower_bound=-4.504)
            result2 = get_float(lower_bound=-4.504)
        self.assertEqual(result1, -4.504)
        self.assertEqual(result2, -4.5035)
        out = out.getvalue().split("\n")
        expected_out = [
            "Input -4.505 is too small. The value must be at least -4.504.",
            "Input -4.5045 is too small. The value must be at least -4.504.",
        ]
        for i, line in enumerate(expected_out):
            self.assertEqual(out[i], line)

    def test_get_float_upper_bound(self) -> None:
        """ Tests that the `get_float()` function correctly implements upper bounds. """
        inputs = ["4.505", "4.5045", "4.504", "4.5035"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(out):
            result1 = get_float(upper_bound=4.504)
            result2 = get_float(upper_bound=4.504)
        self.assertEqual(result1, 4.504)
        self.assertEqual(result2, 4.5035)
        out = out.getvalue().split("\n")
        expected_out = [
            "Input 4.505 is too large. The value must be at most 4.504.",
            "Input 4.5045 is too large. The value must be at most 4.504.",
        ]
        for i, line in enumerate(expected_out):
            self.assertEqual(out[i], line)
    
    def test_get_float_quit(self) -> None:
        """ Tests that the user can quit the `get_float()` input function. """
        inputs = ["q", "quit", "exit", "leave", "x"]
        with patch("builtins.input", side_effect=inputs):
            for _ in inputs:
                result = get_float(0, 10)
                self.assertTrue(math.isnan(result))
    

    def test_get_int_valid(self) -> None:
        """ Tests that the `get_int()` function works for valid inputs."""
        inputs = ["2", "-5"]
        with patch("builtins.input", side_effect=inputs):
            result1 = get_int(1, 19)
            result2 = get_int(-100, 100)
        self.assertEqual(result1, 2)
        self.assertEqual(result2, -5)
    
    def test_get_int_not_number(self) -> None:
        """ Tests that the `get_int()` function handles non-numeric inputs. """
        inputs = ["", "abcdefgh", "5.70000O", ".596", "3"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(out):
            result = get_int()
        self.assertEqual(result, 3)
        out = out.getvalue().split("\n")
        expected_out = [
            "Invalid input for an integer. Please try again...",
            "Invalid input for an integer. Please try again...",
            "Invalid input for an integer. Please try again...",
            "Invalid input for an integer. Please try again..."
        ]
        for i, line in enumerate(expected_out):
            self.assertEqual(out[i], line)
    
    def test_get_int_lower_bound(self) -> None:
        """ Tests that the `get_int()` function correctly implements lower bounds. """
        inputs = ["-4", "-3", "-2", "-1"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(out):
            result1 = get_int(lower_bound=-2)
            result2 = get_int(lower_bound=-2)
        self.assertEqual(result1, -2)
        self.assertEqual(result2, -1)
        out = out.getvalue().split("\n")
        expected_out = [
            "Input -4 is too small. The value must be at least -2.",
            "Input -3 is too small. The value must be at least -2.",
        ]
        for i, line in enumerate(expected_out):
            self.assertEqual(out[i], line)

    def test_get_int_upper_bound(self) -> None:
        """ Tests that the `get_int()` function correctly implements upper bounds. """
        inputs = ["7", "6", "5", "4"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(out):
            result1 = get_int(upper_bound=5)
            result2 = get_int(upper_bound=5)
        self.assertEqual(result1, 5)
        self.assertEqual(result2, 4)
        out = out.getvalue().split("\n")
        expected_out = [
            "Input 7 is too large. The value must be at most 5.",
            "Input 6 is too large. The value must be at most 5.",
        ]
        for i, line in enumerate(expected_out):
            self.assertEqual(out[i], line)
    
    def test_get_int_quit(self) -> None:
        """ Tests that the user can quit the `get_int()` input function. """
        inputs = ["q", "quit", "exit", "leave", "x"]
        with patch("builtins.input", side_effect=inputs):
            for _ in inputs:
                result = get_int(0, 10)
                self.assertIsNone(result)

    def test_save_valid_composition_file(self) -> None:
        """ Tests that the user can save a valid composition file."""
        clean_dir()
        result = save_composition_file("{}", "./tests/testing/")
        self.assertTrue(result)
        if os.path.isdir(os.path.join(os.getcwd(), "./tests/testing")):
            log_files = os.listdir(os.path.join(os.getcwd(), "./tests/testing"))
            self.assertEqual(len(log_files), 1)
            with open(os.path.join(os.getcwd(), "./tests/testing/") + log_files[0], "r") as f:
                self.assertEqual(f.read(), "{}")
    
    def test_save_composition_dir_creation(self) -> None:
        """ Tests that the user can save a valid composition file, even if
        directories have to be created to meet the required path. """
        clean_dir()
        if os.path.isdir(os.path.join(os.getcwd(), "./tests/testing/dir/")):
            log_files = os.listdir(os.path.join(os.getcwd(), "./tests/testing/dir/"))
            for file_ in log_files:
                os.remove(os.path.join(os.path.join(os.getcwd(), "./tests/testing/dir/"), file_))
            os.rmdir(os.path.join(os.getcwd(), "./tests/testing/dir/"))
        result = save_composition_file("{}", "./tests/testing/dir/")
        self.assertTrue(result)
        self.assertTrue(os.path.isdir(os.path.join(os.getcwd(), "./tests/testing/dir/")))
        comp_files = os.listdir(os.path.join(os.getcwd(), "./tests/testing/dir/"))
        for file_ in comp_files:
            os.remove(os.path.join(os.path.join(os.getcwd(), "./tests/testing/dir/"), file_))
        os.rmdir(os.path.join(os.getcwd(), "./tests/testing/dir/"))
    
    def test_save_composition_no_path(self) -> None:
        """ Tests that the `save_composition_file` defaults to using the config
        composition path if no filepath is supplied. """
        clean_dir()
        cfg.COMP_PATH = "./tests/testing/"
        result = save_composition_file("{}")
        self.assertTrue(result)
        if os.path.isdir(os.path.join(os.getcwd(), "./tests/testing")):
            log_files = os.listdir(os.path.join(os.getcwd(), "./tests/testing"))
            self.assertEqual(len(log_files), 1)
            with open(os.path.join(os.getcwd(), "./tests/testing/" + log_files[0]), "r") as f:
                self.assertEqual(f.read(), "{}")
    
    def test_load_valid_composition_file(self) -> None:
        """ Tests that the `load_composition_file` function works when given
        a valid file path to read from. """
        clean_dir()
        with open("./tests/testing/test.cobf", "w+") as f:
            f.write("{}")
        result = load_composition_file("./tests/testing/test.cobf")
        self.assertEqual(result, "{}")
        cfg.COMPOSITION = "./tests/testing/test.cobf"
        result = load_composition_file()
        self.assertEqual(result, "{}")
    
    def test_load_valid_composition_no_path(self) -> None:
        """ Tests that the `load_composition_file` function can handle the case
        where no file path is given nor specified as a system default. """
        cfg.COMPOSITION = None
        self.assertIsNone(load_composition_file())
    
    def test_load_invalid_composition(self) -> None:
        """ Tests that the `load_composition_file` function can handle the case
        where the file that is specified does not exist or cannot be read. """
        self.assertIsNone(load_composition_file("tests/testing/does_not_exist.abc"))
        self.assertFalse(os.path.exists("./tests/testing/does_not_exist.abc"))
    
    def test_disable_logging_func(self) -> None:
        """ Tests that the `disable_logging` func does indeed disable logging
        and delete any existing log file. """
        clean_dir()
        cfg.LOG_PATH = "./tests/testing/"
        cfg.LOGS_ENABLED = True
        create_log_file()
        self.assertIsNone(disable_logging())
        self.assertFalse(cfg.LOGS_ENABLED)
        self.assertFalse(os.path.exists(cfg.LOG_FILE))
    
    def test_set_seed_func(self) -> None:
        """ Tests that the `set_seed` func works as intended, setting the 
        seed if valid args are supplied and returning False otherwise. """
        cfg.SEED = None
        self.assertFalse(set_seed([]))
        self.assertIsNone(cfg.SEED)
        self.assertFalse(set_seed(['abc']))
        self.assertIsNone(cfg.SEED)
        self.assertTrue(set_seed(['123']))
        self.assertEqual(cfg.SEED, 123)
    
    def test_suppress_errors_func(self) -> None:
        """ Tests that the `supress_errors` func works as intended, setting
        the relevant option. """
        cfg.SUPPRESS_ERRORS = False
        self.assertIsNone(suppress_errors())
        self.assertTrue(cfg.SUPPRESS_ERRORS)
    
    def test_display_progress_func(self) -> None:
        """ Tests that the `display_progress` func works as intended, setting
        the relevant option. """
        cfg.DISPLAY_PROGRESS = False
        self.assertIsNone(display_progress())
        self.assertTrue(cfg.DISPLAY_PROGRESS)
    
    def test_save_composition_func(self) -> None:
        """ Tests that the `save_composition` func works as intended, setting
        the relevant option. """
        cfg.SAVE_COMPOSITION = False
        self.assertIsNone(save_composition())
        self.assertTrue(cfg.SAVE_COMPOSITION)
    
    def test_disable_metrics_func(self) -> None:
        """ Tests that the `disable_metrics` func works as intended, setting
        the relevant option. """
        cfg.CALCULATE_COMPLEXITY = True
        self.assertIsNone(disable_metrics())
        self.assertFalse(cfg.CALCULATE_COMPLEXITY)
    
    def test_display_version_func(self) -> None:
        """ Tests that the `display_version` system option func works as
        intended, printing out the name and version of the program, and then
        returning false to indicate stopped execution. """
        cfg.NAME = "Program Name"
        cfg.VERSION = "v1.2.3.4.5.6"
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertFalse(display_version())
        out = out.getvalue()
        self.assertEqual(out, "Program Name v1.2.3.4.5.6\n")
    
    def test_load_composition_func(self) -> None:
        """Tests that the `load_composition` system option func correctly
        parses provided system arguments for the composition file name, and 
        can handle the case where no such argument is supplied. """
        cfg.COMPOSITION = None
        self.assertFalse(load_composition([]))
        self.assertIsNone(cfg.COMPOSITION)
        self.assertTrue(load_composition(['abc.cobf']))
        self.assertEqual(cfg.COMPOSITION, 'abc.cobf')
    
    def test_extract_valid_argumens(self) -> None:
        """ Tests that the `handle_arguments` function can correctly handle
        extracting a set of valid arguments interspersed with options."""
        supplied_args = ["one", "-s", "123", "two", "three", "--noLogs", "four"]
        result = handle_arguments(supplied_args, shared_options)
        self.assertEqual(len(result), 4)
        for i, arg in enumerate(["one", "two", "three", "four"]):
            self.assertEqual(result[i], arg)
    
    def test_system_option_synonyms(self) -> None:
        """ Tests that the `handle_arguments` function can correctly handle 
        names/synonyms for system options."""
        supplied_args = ["-a", "--two", "-c", "--four"]
        options = [SystemOpt(lambda: print("test", end=""), supplied_args, "", [])]
        out = io.StringIO()
        with redirect_stdout(out):
            result = handle_arguments(supplied_args, options)
        self.assertEqual(len(result), 0)
        self.assertEqual(out.getvalue(), "testtesttesttest")
        
    def test_no_parameter_options(self) -> None:
        """ Tests that the `handle_arguments` function can correctly handle
        system options that take no parameters."""
        supplied_args = ["abc", "def", "-a", "egh", "jik"]
        options = [SystemOpt(lambda: print("test", end=""), ["-a"], "", [])]
        out = io.StringIO()
        with redirect_stdout(out):
            result = handle_arguments(supplied_args, options)
        self.assertEqual(len(result), 4)
        for i, arg in enumerate(["abc", "def", "egh", "jik"]):
            self.assertEqual(result[i], arg)
        self.assertEqual(out.getvalue(), "test")
    
    def test_one_parameter_options(self) -> None:
        """ Tests that the `handle_arguments` function can correctly handle
        system options that take one parameter."""
        supplied_args = ["one", "two", "-a", "three", "four", "-a", "five", "six"]
        options = [SystemOpt(lambda x: print("test", x[0], end=""), ["-a"], "", ["x"])]
        out = io.StringIO()
        with redirect_stdout(out):
            result = handle_arguments(supplied_args, options)
        self.assertEqual(len(result), 4)
        for i, arg in enumerate(["one", "two", "four", "six"]):
            self.assertEqual(result[i], arg)
        self.assertEqual(out.getvalue(), "test threetest five")
    
    def test_many_parameter_options(self) -> None:
        """ Tests that the `handle_arguments` function can correctly handle
        system options that take many parameters."""
        supplied_args = ["one", "two", "-a", "three", "four", "-b", "five", "six", "seven", "-c", "eight", "nine", "ten", "eleven", "twelve", "thirteen"]
        options = [SystemOpt(lambda x: print("test", x[0], end=""), ["-a"], "", ["x"]),
                   SystemOpt(lambda x: print("test2", x[0], x[1], end=""), ["-b"], "", ["x", "y"]),
                   SystemOpt(lambda x: print("test3", x[0], x[1], x[2], x[3], x[4], end=""), ["-c"], "", ["a", "b", "c", "d", "e"])]
        out = io.StringIO()
        with redirect_stdout(out):
            result = handle_arguments(supplied_args, options)
        self.assertEqual(len(result), 5)
        for i, arg in enumerate(["one", "two", "four", "seven", "thirteen"]):
            self.assertEqual(result[i], arg)
        self.assertEqual(out.getvalue(), "test threetest2 five sixtest3 eight nine ten eleven twelve")
    
    def test_quit_from_option(self) -> None:
        """ Tests that the `handle_arguments` function propagates errors from
        called functions and quits appropriately. """
        supplied_args = ["abc", "def", "ghi", "-x", "--print"]
        options = [SystemOpt(lambda: False, ["-x"], "", []),
                   SystemOpt(lambda: print("hi"), ["--print"], "", [])]
        out = io.StringIO()
        with redirect_stdout(out):
            result = handle_arguments(supplied_args, options)
        self.assertFalse(result)
        self.assertEqual(out.getvalue(), '')
    
    def test_unknown_option(self) -> None:
        """ Tests that the `handle_arguments` function can correctly handle
        the case in which an unknown option is used. """
        supplied_args = ["abc", "def", "ghi", "-x", "--print", "-y", "--print"]
        options = [SystemOpt(lambda: True, ["-x"], "", []),
                   SystemOpt(lambda: print("hi"), ["--print"], "", [])]
        out = io.StringIO()
        with redirect_stdout(out):
            result = handle_arguments(supplied_args, options)
        self.assertFalse(result)
        self.assertEqual(out.getvalue(), 'hi\n')
    
    def test_set_help_menu_func(self) -> None:
        """ Tests that the `set_help_menu` function does indeed set the help
        menu of the list `shared_options` of system options available."""
        shared_options[0].func = None
        set_help_menu(print)
        self.assertEqual(shared_options[0].func, print)
        shared_options[0].func = None
    
    def test_default_options(self) -> None:
        """ Tests that the `shared_options` list of default system options 
        contains the following system options at bare minimum: --help, 
        --version, --noLogs, --seed, --progress, --save-comp, --load-comp
        and --no-metrics."""
        names = sum([opt.names for opt in shared_options], [])
        targets = ["--help", "--version", "--noLogs", "--seed", "--progress",
                   "--save-comp", "--load-comp", "--no-metrics"]
        for target in targets:
            self.assertIn(target, names)
        

class TestGeneralUtilities(unittest.TestCase):
    """Implements unit tests for the utils.py functions"""

    def test_is_initialised(self) -> None:
        """ Tests that the general `is_initialised` utility function can correctly detect
        when a library is being initialised in the file or not."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        source.contents = source.contents + (
            "\n#include <stdio.h>\n\n\n\n"
            "           #include    <stdlib.h>\n\n\n"
            "#include <time.h>\n"
        )
        result = is_initialised(source, ['<time.h>', 'math.h', '<stdio.h>', 'stdlib.h', '<string.h>'])
        self.assertTrue(result[0] and result[2] and result[3])
        self.assertFalse(result[1] or result[4])
