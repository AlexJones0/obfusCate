import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from app import settings as cfg
from app.cli import *
from app.interaction import CSource
from tests import *
import io


class CountUnit(obfs.ObfuscationUnit):
    "A simple obfuscation class made for testing purposes."
    count = 1
    type = obfs.TransformType.STRUCTURAL
    
    def __init__(self, count: int) -> None:
        self.count_ = count
        
    def transform(self, source: CSource):
        source.contents += f"\n{self.count_}"
        return source
    
    def from_json():
        return None
    
    def to_json(self):
        return None
    
    def __str__(self) -> str:
        return f"CountUnit(c={self.count_})"


class CliCountUnit(CountUnit):

    def edit_cli(self):
        print(f"Edited {self.count_}")
    
    def get_cli() -> "CountUnit":
        CountUnit.count += 1
        return CliCountUnit(CountUnit.count)


class TestMainCLIFunctions(unittest.TestCase):
    """Implements unit tests for the cli.py functions"""

    def test_skip_menus_option(self) -> None:
        """Tests that the `skip_menus` option func actually sets the
        corresponding option, and that the option is added to the list
        of system options."""
        cfg.SKIP_MENUS = False
        self.assertIsNone(skip_menus())
        self.assertTrue(cfg.SKIP_MENUS)

    def test_cli_help_menu(self) -> None:
        """Tests that the CLI help menu contains the necessary minimum
        information and that it is updated in the list of system options."""
        result = [opt for opt in interaction.shared_options if "--help" in opt.names]
        self.assertEqual(len(result), 1)
        self.assertIsNotNone(result[0].func)
        out = io.StringIO()
        with redirect_stdout(out):
            result[0].func()
        out = out.getvalue().lower()
        self.assertIn("usage", out)
        self.assertIn("options", out)
        for opt in interaction.shared_options:
            for name in opt.names:
                self.assertIn(name.lower(), out)

    def test_get_metric_length(self) -> None:
        """Tests that the `get_metric_length` function correctly calculates
        the length of the formatted metric entry."""
        self.assertEqual(get_metric_length(("123", "456")), 6)
        self.assertEqual(get_metric_length(("12", ("34", "56"))), 9)

    def test_get_metric_length_unicode(self) -> None:
        """Tests that the `get_metric_length` function correctly handles
        formatting string length with special multi-character unicode
        encodings."""
        self.assertEqual(get_metric_length(("123\u030545", "67")), 7)
        self.assertEqual(get_metric_length(("\u004E\u0302", ("0", "0"))), 6)

    def test_process_metrics_valid(self) -> None:
        """Tests that the process_metrics function can correctly process the
        list of available metrics, with empty source file inputs."""
        from app import complexity

        source = CSource("", "", None)
        source.update_t_unit()
        other = CSource("", "", None)
        other.update_t_unit()
        result = process_metrics(
            complexity.CodeMetricUnit.__subclasses__(), source, other
        )
        self.assertIsNotNone(result)

    def test_process_metrics_opposite_order(self) -> None:
        """Tests that the `process_metrics` function can correctly handle
        metric predecessor prerequisities, even if given in the exact opposite
        order as to what the predecessors state"""
        from app import complexity

        source = CSource("", "", None)
        source.update_t_unit()
        other = CSource("", "", None)
        other.update_t_unit()

        class A(complexity.CodeMetricUnit):
            name = "A"

            def calculate_metrics(
                self, old_source: CSource, new_source: CSource
            ) -> None:
                return

        class B(complexity.CodeMetricUnit):
            name = "B"

            def calculate_metrics(
                self, old_source: CSource, new_source: CSource
            ) -> None:
                return

        class C(complexity.CodeMetricUnit):
            name = "C"

            def calculate_metrics(
                self, old_source: CSource, new_source: CSource
            ) -> None:
                return

        class D(complexity.CodeMetricUnit):
            name = "D"

            def calculate_metrics(
                self, old_source: CSource, new_source: CSource
            ) -> None:
                return

        class E(complexity.CodeMetricUnit):
            name = "E"

            def calculate_metrics(
                self, old_source: CSource, new_source: CSource
            ) -> None:
                return

        A.predecessors = [B, C, D, E]
        B.predecessors = [C, D, E]
        C.predecessors = [D, E]
        D.predecessors = [E]
        E.predecessors = []

        result = process_metrics([A, B, C, D, E], source, other)
        self.assertEqual(result, {"A": [], "B": [], "C": [], "D": [], "E": []})

    def test_process_metrics_unsatisfiable(self) -> None:
        """Tests that the `process_metrics` function can correctly identify
        unsatisfiable metric predecessor dependencies and stop execution
        safely, without infinitely looping."""
        from app import complexity

        source = CSource("", "", None)
        source.update_t_unit()
        other = CSource("", "", None)
        other.update_t_unit()

        class A(complexity.CodeMetricUnit):
            name = "A"

            def calculate_metrics(
                self, old_source: CSource, new_source: CSource
            ) -> None:
                return

        class B(complexity.CodeMetricUnit):
            name = "B"

            def calculate_metrics(
                self, old_source: CSource, new_source: CSource
            ) -> None:
                return

        class C(complexity.CodeMetricUnit):
            name = "C"

            def calculate_metrics(
                self, old_source: CSource, new_source: CSource
            ) -> None:
                return

        class D(complexity.CodeMetricUnit):
            name = "D"

            def calculate_metrics(
                self, old_source: CSource, new_source: CSource
            ) -> None:
                return

        class E(complexity.CodeMetricUnit):
            name = "E"

            def calculate_metrics(
                self, old_source: CSource, new_source: CSource
            ) -> None:
                return

        A.predecessors = [B]
        B.predecessors = [C]
        C.predecessors = [D]
        D.predecessors = [E]
        E.predecessors = [A]

        result = process_metrics([A, B, C, D, E], source, other)
        self.assertIsNone(result)

    def test_process_metrics_erroneous_metric(self) -> None:
        """Tests that the `process_metric` function can attempt to handle and
        recover from an error in one of its subsequent complexity modules/units,
        ignoring the error and continuing execution."""
        from app import complexity

        source = CSource("", "", None)
        source.update_t_unit()
        other = CSource("", "", None)
        other.update_t_unit()

        class A(complexity.CodeMetricUnit):
            name = "A"

            def calculate_metrics(
                self, old_source: CSource, new_source: CSource
            ) -> None:
                return

        class B(complexity.CodeMetricUnit):
            name = "B"

            def calculate_metrics(
                self, old_source: CSource, new_source: CSource
            ) -> None:
                raise Exception()

        class C(complexity.CodeMetricUnit):
            name = "C"

            def calculate_metrics(
                self, old_source: CSource, new_source: CSource
            ) -> None:
                return

        result = process_metrics([A, B, C], source, other)
        self.assertEqual(result, {"A": [], "C": []})

    def test_display_metrics(self) -> None:
        """Tests that complexity metrics are correctly formatted and displayed
        within the CLI."""
        from app import complexity

        source = CSource("", "", None)
        source.update_t_unit()
        other = CSource("", "", None)
        other.update_t_unit()

        class A(complexity.CodeMetricUnit):
            name = "A"

            def calculate_metrics(
                self, old_source: CSource, new_source: CSource
            ) -> None:
                self.metrics = {
                    "abc": "32598345",
                    "ABCDEF": (
                        "19234",
                        "(+94500000000000000000000000000000000000000000000000000000000000000000000000000000000)",
                    ),
                }

        class B(complexity.CodeMetricUnit):
            name = "B"

            def calculate_metrics(
                self, old_source: CSource, new_source: CSource
            ) -> None:
                self.metrics = {
                    "figomdfg": ("123", "(N/A"),
                    "ABCDEF": ("Positive", "(no change)"),
                }

        class C(complexity.CodeMetricUnit):
            name = "C"

            def calculate_metrics(
                self, old_source: CSource, new_source: CSource
            ) -> None:
                self.metrics = {"N/A": "N/A"}

        out = io.StringIO()
        with redirect_stdout(out):
            self.assertIsNone(display_complexity_metrics(source, other))
        out = out.getvalue()
        self.assertTrue(out.startswith("\n===Obfuscation Metrics===\n\n"))
        self.assertTrue(
            out.endswith(
                "A:\n  abc:                                                                                                 32598345\n  ABCDEF:        19234 ((+94500000000000000000000000000000000000000000000000000000000000000000000000000000000))\n\nB:\n  figomdfg:                                                                                          123 ((N/A)\n  ABCDEF:                                                                                Positive ((no change))\n\nC:\n  N/A:                                                                                                      N/A\n\n"
            )
        )

    def test_load_composition_valid(self) -> None:
        """ Tests that a valid composition file can be loaded with the
        `load_composition` function. """
        from app import obfuscation
        clean_dir()
        config.SEED = None
        cfg.COMPOSITION = "./tests/testing/comp.cobf"
        with open(os.path.join(os.getcwd(), "./tests/data/compositions/seed.cobf"), "r") as f:
            composition = f.read()
        new_contents = composition.replace("v0.17.4", cfg.VERSION)
        with open(os.path.join(os.getcwd(), cfg.COMPOSITION), "w+") as f:
            f.write(new_contents)
        result = load_composition()
        self.assertIsInstance(result, obfuscation.Pipeline)
        self.assertEqual(result.transforms, [])
        self.assertEqual(result.seed, 123456)
        self.assertEqual(config.SEED, 123456)
        new_contents = composition.replace("123456", "123457")
        with open(os.path.join(os.getcwd(), cfg.COMPOSITION), "w+") as f:
            f.write(new_contents)
        result = load_composition()
        self.assertIsInstance(result, obfuscation.Pipeline)
        self.assertEqual(result.transforms, [])
        self.assertEqual(result.seed, 123457)
        self.assertEqual(config.SEED, 123456)
        cfg.COMPOSITION = None

    def test_load_composition_invalid(self) -> None:
        """ Tests that the `load_composition` function can handle
        an invalid composition file (either a file that does not
        exist or a bad JSON file, etc.) """
        clean_dir()
        config.SEED = None
        cfg.COMPOSITION = "./tests/testing/comp.cobf"
        self.assertFalse(os.path.exists(os.path.join(os.getcwd(),  cfg.COMPOSITION)))
        result = load_composition()
        self.assertIsNone(result)
        self.assertIsNone(config.SEED)
        with open(os.path.join(os.getcwd(),  "./tests/data/compositions/bad_json.cobf"), "r") as f:
            composition = f.read()
        new_contents = composition.replace("v0.17.4", cfg.VERSION)
        with open(os.path.join(os.getcwd(),  cfg.COMPOSITION), "w+") as f:
            f.write(new_contents)
        result = load_composition()
        self.assertIsNone(result)
        self.assertIsNone(config.SEED)
        cfg.COMPOSITION = None

    def test_cli_quit(self) -> None:
        """ Tests that the CLI obfuscation selection menu correctly propagates
        quitting the program, so that it can be exit at any point. """
        source = CSource(os.path.join(os.getcwd(),  "./tests/data/minimal.c"))
        quit_inputs = ["Q", "qUIt", "eXit    ", "  LEAVE    ", " X  "]
        with patch("builtins.input", side_effect=quit_inputs):
            for _ in quit_inputs:
                self.assertIsNone(cli_obfuscation(source))

    def test_cli_transform_display(self) -> None:
        """ Tests that the transform selection CLI displays the available transforms
        and the cursor correctly."""
        source = CSource(os.path.join(os.getcwd(),  "./tests/data/minimal.c"))
        CountUnit.count = 0
        inp = str(len(obfs.ObfuscationUnit.__subclasses__()))
        inputs = [inp, inp, inp, inp, inp, "quit"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(out):
            cli_obfuscation(source)
        out = out.getvalue()
        self.assertIn("Current transforms: CountUnit(c=1) -> CountUnit(c=2) -> CountUnit(c=3) -> CountUnit(c=4) -> CountUnit(c=5) >>>", out)

    def test_cli_create_transform(self) -> None:
        """ Tests that the option to create a transform in the CLI correctly
        calls the `get_cli` function and adds the created transform to the list. """
        source = CSource(os.path.join(os.getcwd(),  "./tests/data/minimal.c"))
        CountUnit.count = 0
        inp = str(len(obfs.ObfuscationUnit.__subclasses__()))
        inputs = [inp, "quit"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(out):
            cli_obfuscation(source)
        out = out.getvalue()
        self.assertIn("Current transforms: CountUnit(c=1) >>>", out)

    def test_cli_move_cursor(self) -> None:
        """ Tests that the cursor can be properly moved left and right within the
        current composition of selected transforms in the CLI. """
        source = CSource(os.path.join(os.getcwd(),  "./tests/data/minimal.c"))
        CountUnit.count = 0
        inp = len(obfs.ObfuscationUnit.__subclasses__())
        left = str(inp + 1)
        right = str(inp + 2)
        inp = str(inp)
        inputs = [inp, left, inp, left, inp, right, right, inp, 
                  inp, left, inp, left, left, inp, "quit"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(out):
            cli_obfuscation(source)
        out = out.getvalue()
        self.assertIn("Current transforms: CountUnit(c=3) -> CountUnit(c=2) -> CountUnit(c=1) -> CountUnit(c=7) >>> CountUnit(c=4) -> CountUnit(c=6) -> CountUnit(c=5)", out)

    def test_cli_delete_transform(self) -> None:
        """ Tests that transforms can be deleted from the selection menu
        within the CLI, deleting the transform after the cursor only if one exists. """
        source = CSource(os.path.join(os.getcwd(),  "./tests/data/minimal.c"))
        CountUnit.count = 0
        inp = len(obfs.ObfuscationUnit.__subclasses__())
        left = str(inp + 1)
        delete = str(inp + 3)
        inp = str(inp)
        inputs = [inp, inp, inp, left, delete, inp, inp, delete, "quit"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(out):
            cli_obfuscation(source)
        out = out.getvalue()
        self.assertIn("Current transforms: CountUnit(c=1) -> CountUnit(c=2) -> CountUnit(c=4) -> CountUnit(c=5) >>>", out)

    def test_cli_edit_transform(self) -> None:
        """ Tests that the user can select to edit the transform after the cursor
        in the CLI, if such a transform exists. """
        source = CSource(os.path.join(os.getcwd(),  "./tests/data/minimal.c"))
        CountUnit.count = 0
        inp = len(obfs.ObfuscationUnit.__subclasses__())
        left = str(inp + 1)
        edit = str(inp + 4)
        inp = str(inp)
        inputs = [inp, inp, inp, edit, left, edit, left, edit, left, edit, "quit"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(out):
            cli_obfuscation(source)
        out = out.getvalue()
        self.assertIn("Edited 3", out)
        out = "".join(out.split("Edited 3")[1:])
        self.assertIn("Edited 2", out)
        out = "".join(out.split("Edited 2")[1:])
        self.assertIn("Edited 1", out)

    def test_cli_valid_selection(self) -> None:
        """ Tests that the user can make a valid selection of transformations and
        obfuscate their code with the GUI selection menu. """
        source = CSource(os.path.join(os.getcwd(),  "./tests/data/minimal.c"))
        original_contents = source.contents
        CountUnit.count = 0
        inp = len(obfs.ObfuscationUnit.__subclasses__())
        finish = str(inp + 5)
        inp = str(inp)
        inputs = [inp, inp, inp, inp, inp, finish]
        with patch("builtins.input", side_effect=inputs):
            result = cli_obfuscation(source)
        self.assertEqual(result.contents, original_contents + "\n1\n2\n3\n4\n5")

    def test_cli_load_composition_option(self) -> None:
        """ Tests that the CLI can successfully load a composition if supplied with
        the correct argument (i.e. the correct option is set). """
        cfg.SEED = None
        cfg.COMPOSITION = "./tests/data/compositions/seed.cobf"
        # TODO make non-version dependent
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        inputs = ["quit"]
        with patch("builtins.input", side_effect=inputs):
            cli_obfuscation(source)
        self.assertEqual(cfg.SEED, 123456)
        cfg.COMPOSITION = None

    def test_cli_save_composition_option(self) -> None:
        """ Tests that the CLI will successfully save a composition if supplied with
        the correct argument (i.e. the correct option is set)."""
        clean_dir()
        cfg.COMPOSITION = None
        cfg.SEED = 123
        cfg.SAVE_COMPOSITION = True
        cfg.COMP_PATH = "./tests/testing/"
        source = CSource(os.path.join(os.getcwd(),  "./tests/data/minimal.c"))
        inp = len(obfs.ObfuscationUnit.__subclasses__())
        finish = str(inp + 5)
        inputs = [finish]
        with patch("builtins.input", side_effect=inputs):
            cli_obfuscation(source)
        cfg.SAVE_COMPOSITION = False
        self.assertEqual(len(os.listdir(os.path.join(os.getcwd(),  cfg.COMP_PATH))), 1)

    def test_cli_skip_menus_option(self) -> None:
        """ Tests that the CLI will successfully skip menus if the correct option is set. """
        cfg.SKIP_MENUS = True
        source = CSource(os.path.join(os.getcwd(),  "./tests/data/minimal.c"))
        self.assertIsNotNone(cli_obfuscation(source))
        cfg.SKIP_MENUS = False

    def test_cli_display_metrics_option(self) -> None:
        """ Tests that the CLI will successfully display metrics if the correct
        option is set (i.e. if not supplied with the disabling argument), and that
        it can be disabled."""
        cfg.CALCULATE_COMPLEXITY = True
        source = CSource(os.path.join(os.getcwd(),  "./tests/data/minimal.c"))
        inp = len(obfs.ObfuscationUnit.__subclasses__())
        finish = str(inp + 5)
        inputs = [finish]
        out = io.StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(out):
            self.assertIsNotNone(cli_obfuscation(source))
        out = out.getvalue()
        self.assertIn("===Obfuscation Metrics===", out)

    def test_cli_no_args(self) -> None:
        """ Tests that the CLI correctly identifies the erroneous case in which
        no arguments are supplied when calling it from the command line."""
        sys.argv = []
        self.assertFalse(handle_CLI())
        sys.argv = ["script.py"]
        self.assertFalse(handle_CLI())

    def test_cli_one_arg(self) -> None:
        """ Tests that the CLI correctly handles the case where one command line
        argument is supplied, where it should print the obfuscated output to the
        standard output stream upon completion. """
        sys.argv = [os.path.join(os.getcwd(),  "./tests/data/minimal.c")]
        cfg.SKIP_MENUS = True
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertTrue(handle_CLI())
        out = out.getvalue()
        self.assertTrue(out.endswith("===Obfuscated Output===\nint main() {}\n"))
        sys.argv = ["script.py", os.path.join(os.getcwd(),  "./tests/data/minimal.c")]
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertTrue(handle_CLI())
        out = out.getvalue()
        self.assertTrue(out.endswith("===Obfuscated Output===\nint main() {}\n"))
        cfg.SKIP_MENUS = False

    def test_cli_two_args(self) -> None:
        """ Tests that the CLI correctly handles the case where two arguments are
        supplied, where it should write the obfuscated output to the output
        file specified by the second argument upon completion."""
        clean_dir()
        sys.argv = [os.path.join(os.getcwd(),  "./tests/data/minimal.c"), 
                    os.path.join(os.getcwd(),  "./tests/testing/out.c")]
        cfg.SKIP_MENUS = True
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertTrue(handle_CLI())
        out = out.getvalue()
        self.assertTrue(out.endswith("Obfuscation written successfully.\n"))
        self.assertEqual(len(os.listdir(os.path.join(os.getcwd(),  "./tests/testing/"))), 1)
        sys.argv = ["script.py",
                    os.path.join(os.getcwd(),  "./tests/data/minimal.c"), 
                    os.path.join(os.getcwd(),  "./tests/testing/out2.c")]
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertTrue(handle_CLI())
        out = out.getvalue()
        self.assertTrue(out.endswith("Obfuscation written successfully.\n"))
        self.assertEqual(len(os.listdir(os.path.join(os.getcwd(),  "./tests/testing/"))), 2)
        cfg.SKIP_MENUS = False
    
    def test_cli_more_args(self) -> None:
        """ Tests that the CLI correctly handles the case where more than two 
        arguments are supplied, where it should error and direct the user to 
        the help menu for more information ."""
        sys.argv = ["a", "b", "c"]
        self.assertFalse(handle_CLI())
        sys.argv = ["script.py", "a", "b", "c"]
        self.assertFalse(handle_CLI())


class TestObfuscationCLIFunctions(unittest.TestCase):
    """Implements unit test for the obfuscation edit_cli and get_cli methods."""

    pass


if __name__ == "__main__":
    unittest.main()


# TODO
# TESTING TODO
###Done### Debug unit tests
###Done### Interaction unit tests
###Done### General CLI unit tests
###Done### Utils unit tests
# Obfuscation CLI unit tests
# Code Complexity CLI unit tests
# CLI integration tests
# General GUI unit tests
# Obfuscation GUI unit tests
# Code Complexity GUI unit tests
# GUI integration tests
# Obfuscation unit tests (per method, per construct)
# Obfucation construct integration tests (per method)
# Obfuscation transformation integration tests (combinations of methods)
# Code Complexity metric unit tests
# Whole system tests
