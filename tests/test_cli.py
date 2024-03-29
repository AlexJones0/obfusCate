""" File: tests/test_cli.py
Implements unit and integration tests for the command line interface of the program,
including tests for general command line interaction functions, the obfuscation
transformation selection menu (including transform addition / editing / cursor
traversal etc.) and system arguments that are supplied to the CLI.
"""
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from app import settings as cfg
from app.cli import *
from app.interaction import CSource
from app.obfuscation import cli as obfscli
from tests import *
import io


class AggregateUnit(obfs.ObfuscationUnit):
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
        return f"AggregateUnit(c={self.count_})"


class CliAggregateUnit(AggregateUnit):
    """A simple obfuscaion unit class made for testing purposes,
    extending the existing aggregate unit. This simply increments the
    aggregate unit's count every time a new unit is created, such that
    each aggreage unit has its own unique number that can be tested for."""

    def edit_cli(self) -> None:
        print(f"Edited {self.count_}")

    def get_cli() -> "AggregateUnit":
        AggregateUnit.count += 1
        return CliAggregateUnit(AggregateUnit.count)


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
        """Tests that a valid composition file can be loaded with the
        `load_composition` function."""
        from app import obfuscation

        clean_dir()
        config.SEED = None
        cfg.COMPOSITION = "./tests/testing/comp.cobf"
        with open(
            os.path.join(os.getcwd(), "./tests/data/compositions/seed.cobf"), "r"
        ) as f:
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
        """Tests that the `load_composition` function can handle
        an invalid composition file (either a file that does not
        exist or a bad JSON file, etc.)"""
        clean_dir()
        config.SEED = None
        cfg.COMPOSITION = "./tests/testing/comp.cobf"
        self.assertFalse(os.path.exists(os.path.join(os.getcwd(), cfg.COMPOSITION)))
        result = load_composition()
        self.assertIsNone(result)
        self.assertIsNone(config.SEED)
        with open(
            os.path.join(os.getcwd(), "./tests/data/compositions/bad_json.cobf"), "r"
        ) as f:
            composition = f.read()
        new_contents = composition.replace("v0.17.4", cfg.VERSION)
        with open(os.path.join(os.getcwd(), cfg.COMPOSITION), "w+") as f:
            f.write(new_contents)
        result = load_composition()
        self.assertIsNone(result)
        self.assertIsNone(config.SEED)
        cfg.COMPOSITION = None

    def test_cli_quit(self) -> None:
        """Tests that the CLI obfuscation selection menu correctly propagates
        quitting the program, so that it can be exit at any point."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        quit_inputs = ["Q", "qUIt", "eXit    ", "  LEAVE    ", " X  "]
        with patch("builtins.input", side_effect=quit_inputs):
            for _ in quit_inputs:
                self.assertIsNone(cli_obfuscation(source))

    def test_cli_transform_display(self) -> None:
        """Tests that the transform selection CLI displays the available transforms
        and the cursor correctly."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        AggregateUnit.count = 0
        inp = str(len(obfs.ObfuscationUnit.__subclasses__()))
        inputs = [inp, inp, inp, inp, inp, "quit"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(out):
            cli_obfuscation(source)
        out = out.getvalue()
        self.assertIn(
            "Current transforms: AggregateUnit(c=1) -> AggregateUnit(c=2) -> AggregateUnit(c=3) -> AggregateUnit(c=4) -> AggregateUnit(c=5) >>>",
            out,
        )

    def test_cli_create_transform(self) -> None:
        """Tests that the option to create a transform in the CLI correctly
        calls the `get_cli` function and adds the created transform to the list."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        AggregateUnit.count = 0
        inp = str(len(obfs.ObfuscationUnit.__subclasses__()))
        inputs = [inp, "quit"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(out):
            cli_obfuscation(source)
        out = out.getvalue()
        self.assertIn("Current transforms: AggregateUnit(c=1) >>>", out)

    def test_cli_move_cursor(self) -> None:
        """Tests that the cursor can be properly moved left and right within the
        current composition of selected transforms in the CLI."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        AggregateUnit.count = 0
        inp = len(obfs.ObfuscationUnit.__subclasses__())
        left = str(inp + 1)
        right = str(inp + 2)
        inp = str(inp)
        inputs = [
            inp,
            left,
            inp,
            left,
            inp,
            right,
            right,
            inp,
            inp,
            left,
            inp,
            left,
            left,
            inp,
            "quit",
        ]
        out = io.StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(out):
            cli_obfuscation(source)
        out = out.getvalue()
        self.assertIn(
            "Current transforms: AggregateUnit(c=3) -> AggregateUnit(c=2) -> AggregateUnit(c=1) -> AggregateUnit(c=7) >>> AggregateUnit(c=4) -> AggregateUnit(c=6) -> AggregateUnit(c=5)",
            out,
        )

    def test_cli_delete_transform(self) -> None:
        """Tests that transforms can be deleted from the selection menu
        within the CLI, deleting the transform after the cursor only if one exists."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        AggregateUnit.count = 0
        inp = len(obfs.ObfuscationUnit.__subclasses__())
        left = str(inp + 1)
        delete = str(inp + 3)
        inp = str(inp)
        inputs = [inp, inp, inp, left, delete, inp, inp, delete, "quit"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(out):
            cli_obfuscation(source)
        out = out.getvalue()
        self.assertIn(
            "Current transforms: AggregateUnit(c=1) -> AggregateUnit(c=2) -> AggregateUnit(c=4) -> AggregateUnit(c=5) >>>",
            out,
        )

    def test_cli_edit_transform(self) -> None:
        """Tests that the user can select to edit the transform after the cursor
        in the CLI, if such a transform exists."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        AggregateUnit.count = 0
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
        """Tests that the user can make a valid selection of transformations and
        obfuscate their code with the GUI selection menu."""
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        original_contents = source.contents
        AggregateUnit.count = 0
        inp = len(obfs.ObfuscationUnit.__subclasses__())
        finish = str(inp + 5)
        inp = str(inp)
        inputs = [inp, inp, inp, inp, inp, finish]
        with patch("builtins.input", side_effect=inputs):
            result = cli_obfuscation(source)
        self.assertEqual(result.contents, original_contents + "\n1\n2\n3\n4\n5")

    def test_cli_load_composition_option(self) -> None:
        """Tests that the CLI can successfully load a composition if supplied with
        the correct argument (i.e. the correct option is set)."""
        cfg.SEED = None
        cfg.COMPOSITION = "./tests/data/compositions/seed.cobf"
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        inputs = ["quit"]
        with patch("builtins.input", side_effect=inputs):
            cli_obfuscation(source)
        self.assertEqual(cfg.SEED, 123456)
        cfg.COMPOSITION = None

    def test_cli_save_composition_option(self) -> None:
        """Tests that the CLI will successfully save a composition if supplied with
        the correct argument (i.e. the correct option is set)."""
        clean_dir()
        cfg.COMPOSITION = None
        cfg.SEED = 123
        cfg.SAVE_COMPOSITION = True
        cfg.COMP_PATH = "./tests/testing/"
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        inp = len(obfs.ObfuscationUnit.__subclasses__())
        finish = str(inp + 5)
        inputs = [finish]
        with patch("builtins.input", side_effect=inputs):
            cli_obfuscation(source)
        cfg.SAVE_COMPOSITION = False
        self.assertEqual(len(os.listdir(os.path.join(os.getcwd(), cfg.COMP_PATH))), 1)

    def test_cli_skip_menus_option(self) -> None:
        """Tests that the CLI will successfully skip menus if the correct option is set."""
        cfg.SKIP_MENUS = True
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        self.assertIsNotNone(cli_obfuscation(source))
        cfg.SKIP_MENUS = False

    def test_cli_display_metrics_option(self) -> None:
        """Tests that the CLI will successfully display metrics if the correct
        option is set (i.e. if not supplied with the disabling argument), and that
        it can be disabled."""
        cfg.CALCULATE_COMPLEXITY = True
        source = CSource(os.path.join(os.getcwd(), "./tests/data/minimal.c"))
        inp = len(obfs.ObfuscationUnit.__subclasses__())
        finish = str(inp + 5)
        inputs = [finish]
        out = io.StringIO()
        with patch("builtins.input", side_effect=inputs), redirect_stdout(out):
            self.assertIsNotNone(cli_obfuscation(source))
        out = out.getvalue()
        self.assertIn("===Obfuscation Metrics===", out)


class TestCLISysArgs(unittest.TestCase):
    """Tests the available system argument options for the CLI program interface."""

    def test_cli_no_args(self) -> None:
        """Tests that the CLI correctly identifies the erroneous case in which
        no arguments are supplied when calling it from the command line."""
        sys.argv = []
        self.assertFalse(handle_CLI())
        sys.argv = ["script.py"]
        self.assertFalse(handle_CLI())

    def test_cli_one_arg(self) -> None:
        """Tests that the CLI correctly handles the case where one command line
        argument is supplied, where it should print the obfuscated output to the
        standard output stream upon completion."""
        sys.argv = [os.path.join(os.getcwd(), "./tests/data/minimal.c")]
        cfg.SKIP_MENUS = True
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertTrue(handle_CLI())
        out = out.getvalue()
        self.assertTrue(out.endswith("===Obfuscated Output===\nint main() {}\n"))
        sys.argv = ["script.py", os.path.join(os.getcwd(), "./tests/data/minimal.c")]
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertTrue(handle_CLI())
        out = out.getvalue()
        self.assertTrue(out.endswith("===Obfuscated Output===\nint main() {}\n"))
        cfg.SKIP_MENUS = False

    def test_cli_two_args(self) -> None:
        """Tests that the CLI correctly handles the case where two arguments are
        supplied, where it should write the obfuscated output to the output
        file specified by the second argument upon completion."""
        clean_dir()
        sys.argv = [
            os.path.join(os.getcwd(), "./tests/data/minimal.c"),
            os.path.join(os.getcwd(), "./tests/testing/out.c"),
        ]
        cfg.SKIP_MENUS = True
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertTrue(handle_CLI())
        out = out.getvalue()
        self.assertTrue(out.endswith("Obfuscation written successfully.\n"))
        self.assertEqual(
            len(os.listdir(os.path.join(os.getcwd(), "./tests/testing/"))), 1
        )
        sys.argv = [
            "script.py",
            os.path.join(os.getcwd(), "./tests/data/minimal.c"),
            os.path.join(os.getcwd(), "./tests/testing/out2.c"),
        ]
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertTrue(handle_CLI())
        out = out.getvalue()
        self.assertTrue(out.endswith("Obfuscation written successfully.\n"))
        self.assertEqual(
            len(os.listdir(os.path.join(os.getcwd(), "./tests/testing/"))), 2
        )
        cfg.SKIP_MENUS = False

    def test_cli_more_args(self) -> None:
        """Tests that the CLI correctly handles the case where more than two
        arguments are supplied, where it should error and direct the user to
        the help menu for more information ."""
        sys.argv = ["a", "b", "c"]
        self.assertFalse(handle_CLI())
        sys.argv = ["script.py", "a", "b", "c"]
        self.assertFalse(handle_CLI())


class TestCLISysArgs(unittest.TestCase):
    """Implements unit tests for the CLI program system arguments & options."""

    def test_cli_help_sysarg(self) -> None:
        """Tests that the CLI correctly displays the help menu when the
        help system arguments are given, and that this contains a title,
        as well as usage and option information. Also tests that the
        help menu causes the program to quit when read."""
        interaction.set_help_menu(help_menu)
        help_args = ["-h", "--help"]
        for arg in help_args:
            reset_config()
            sys.argv = [
                "script.py",
                "./tests/data/minimal.c",
                "-l",
                "-S",
                "123",
                arg,
                "-v",
            ]
            out = io.StringIO()
            with redirect_stdout(out):
                handle_CLI()
            out = out.getvalue()
            self.assertNotIn("Current transforms:", out)
            self.assertNotIn("{} {}".format(cfg.NAME, cfg.VERSION), out)
            self.assertIn("CLI Help Manual", out)
            self.assertIn("Usage:", out)
            self.assertIn("Options:", out)
        reset_config()
        sys.argv = ["script.py", "./tests/data/minimal.c"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
            handle_CLI()
        out = out.getvalue()
        self.assertIn("Current transforms:", out)
        self.assertNotIn("CLI Help Manual", out)
        self.assertNotIn("Usage:", out)
        self.assertNotIn("Options:", out)

    def test_cli_version_sysarg(self) -> None:
        """Tests that the CLI correctly displays the program name and
        version when the version system arguments are given."""
        ver_args = ["-v", "--version"]
        for arg in ver_args:
            reset_config()
            sys.argv = [
                "script.py",
                "./tests/data/minimal.c",
                "-l",
                "-S",
                "123",
                arg,
                "-h",
            ]
            out = io.StringIO()
            with redirect_stdout(out):
                handle_CLI()
            out = out.getvalue()
            self.assertNotIn("Current transforms:", out)
            self.assertNotIn("CLI Help Manual", out)
            self.assertIn("{} {}".format(cfg.NAME, cfg.VERSION), out)
        reset_config()
        sys.argv = ["script.py", "./tests/data/minimal.c"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
            handle_CLI()
        out = out.getvalue()
        self.assertIn("Current transforms:", out)
        self.assertNotIn("{} {}".format(cfg.NAME, cfg.VERSION), out)

    def test_cli_nologs_sysarg(self) -> None:
        """Tests that the CLI correctly detects when the noLogs system
        arguments are given, and does not create a log file."""
        nolog_args = ["-L", "--noLogs"]
        for arg in nolog_args:
            reset_config()
            sys.argv = ["script.py", "./tests/data/minimal.c", "-m", arg, "-S", "123"]
            out = io.StringIO()
            with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
                handle_CLI()
            out = out.getvalue()
        self.assertFalse(cfg.LOGS_ENABLED)
        reset_config()
        sys.argv = ["script.py", "./tests/data/minimal.c"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
            handle_CLI()
        out = out.getvalue()
        self.assertTrue(cfg.LOGS_ENABLED)

    def test_cli_seed_sysarg(self) -> None:
        """Tests that the CLI correctly updates the loaded seed when
        a seed system argument is provided (along with a seed value)."""
        from random import randint

        seed_args = ["-S", "--seed"]
        for arg in seed_args:
            reset_config()
            seed_val = randint(100, 100000)
            sys.argv = [
                "script.py",
                "./tests/data/minimal.c",
                "-m",
                arg,
                str(seed_val),
                "-l",
            ]
            out = io.StringIO()
            with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
                handle_CLI()
            out = out.getvalue()
            self.assertEqual(cfg.SEED, seed_val)
        reset_config()
        sys.argv = ["script.py", "./tests/data/minimal.c"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
            handle_CLI()
        out = out.getvalue()
        self.assertIsNone(cfg.SEED)

    def test_cli_progress_sysarg(self) -> None:
        """Tests that the CLI correctly updates the option to display
        progress information when the progress system arguments are
        provided."""
        progress_args = ["-p", "--progress"]
        for arg in progress_args:
            reset_config()
            sys.argv = ["script.py", "./tests/data/minimal.c", "-m", arg, "-S", "123"]
            out = io.StringIO()
            with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
                handle_CLI()
            out = out.getvalue()
            self.assertTrue(cfg.DISPLAY_PROGRESS)
        reset_config()
        sys.argv = ["script.py", "./tests/data/minimal.c"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
            handle_CLI()
        out = out.getvalue()
        self.assertFalse(cfg.DISPLAY_PROGRESS)

    def test_cli_save_comp_sysarg(self) -> None:
        """Tests that the CLI correctly sets the option to save the
        final composition at when the progress system arugments are
        provided."""
        save_comp_args = ["-c", "--save-comp"]
        for arg in save_comp_args:
            reset_config()
            sys.argv = ["script.py", "./tests/data/minimal.c", "-m", arg, "-S", "123"]
            out = io.StringIO()
            with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
                handle_CLI()
            out = out.getvalue()
            self.assertTrue(cfg.SAVE_COMPOSITION)
        reset_config()
        sys.argv = ["script.py", "./tests/data/minimal.c"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
            handle_CLI()
        out = out.getvalue()
        self.assertFalse(cfg.SAVE_COMPOSITION)

    def test_cli_load_comp_sysarg(self) -> None:
        """Tests that the CLI correctly sets the option to load the given
        composition file when the load composition system arguments are given."""
        load_comp_args = ["-l", "--load-comp"]
        for arg in load_comp_args:
            reset_config()
            sys.argv = [
                "script.py",
                "./tests/data/minimal.c",
                "-m",
                arg,
                "comp.cobf",
                "-S",
                "123",
            ]
            out = io.StringIO()
            with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
                handle_CLI()
            out = out.getvalue()
            self.assertEqual(cfg.COMPOSITION, "comp.cobf")
        reset_config()
        sys.argv = ["script.py", "./tests/data/minimal.c"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
            handle_CLI()
        out = out.getvalue()
        self.assertIsNone(cfg.COMPOSITION)

    def test_cli_no_metric_sysarg(self) -> None:
        """Tests that the CLI correctly sets the option to not calculate or
        display the obfuscation metrics when the no metrics system arguments
        are given."""
        no_metric_args = ["-m", "--no-metrics"]
        for arg in no_metric_args:
            reset_config()
            sys.argv = ["script.py", "./tests/data/minimal.c", "-p", arg, "-S", "123"]
            out = io.StringIO()
            with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
                handle_CLI()
            out = out.getvalue()
            self.assertFalse(cfg.CALCULATE_COMPLEXITY)
        reset_config()
        sys.argv = ["script.py", "./tests/data/minimal.c"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
            handle_CLI()
        out = out.getvalue()
        self.assertTrue(cfg.CALCULATE_COMPLEXITY)

    def test_cli_no_alloca_sysarg(self) -> None:
        """Tests that the CLI correctly sets the option to disable alloca usage
        when the no alloca system arguments are given."""
        no_alloca_args = ["-a", "--no-alloca"]
        for arg in no_alloca_args:
            reset_config()
            sys.argv = ["script.py", "./tests/data/minimal.c", "-p", arg, "-S", "123"]
            out = io.StringIO()
            with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
                handle_CLI()
            out = out.getvalue()
            self.assertFalse(cfg.USE_ALLOCA)
        reset_config()
        sys.argv = ["script.py", ".tests/data/minimal.c"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
            handle_CLI()
        out = out.getvalue()
        self.assertTrue(cfg.USE_ALLOCA)

    def test_cli_unpatch_parser_sysarg(self) -> None:
        """Tests that the CLI correctly sets the option to use the unpatched
        parser version when the unpatch parser system arguments are given."""
        unpatch_args = ["-u", "--unpatch-parser"]
        for arg in unpatch_args:
            reset_config()
            sys.argv = ["script.py", "./tests/data/minimal.c", "-p", arg, "-S", "123"]
            out = io.StringIO()
            with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
                handle_CLI()
            out = out.getvalue()
            self.assertFalse(cfg.USE_PATCHED_PARSER)
        reset_config()
        sys.argv = ["script.py", ".tests/data/minimal.c"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
            handle_CLI()
        out = out.getvalue()
        self.assertTrue(cfg.USE_PATCHED_PARSER)

    def test_cli_skip_sysarg(self) -> None:
        """Tests that the CLI correctly sets the option to skip the selection
        interface when the skip system arguments are given."""
        skip_args = ["-s", "--skip"]
        for arg in skip_args:
            reset_config()
            sys.argv = ["script.py", "./tests/data/minimal.c", "-p", arg, "-S", "123"]
            out = io.StringIO()
            with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
                handle_CLI()
            out = out.getvalue()
            self.assertTrue(cfg.SKIP_MENUS)
        reset_config()
        sys.argv = ["script.py", "./tests/data/minimal.c"]
        out = io.StringIO()
        with patch("builtins.input", side_effect=["quit"]), redirect_stdout(out):
            handle_CLI()
        out = out.getvalue()
        self.assertFalse(cfg.SKIP_MENUS)


class TestObfuscationMethodsCLI(unittest.TestCase):
    """Implements unit tests some obfuscation method's CLI interfaces
    (their .edit_cli() and .get_cli() methods.)"""

    def test_identity_get_cli(self) -> None:
        """Tests that the CLI correctly provides an interface for getting a new
        IdentityUnit object, with no available options."""
        obfs_unit = obfscli.CliIdentityUnit.get_cli()
        self.assertIsNotNone(obfs_unit)
        self.assertIsInstance(obfs_unit, obfscli.CliIdentityUnit)

    def test_identity_edit_cli(self) -> None:
        """Tests that the CLI correctly provides an interface for editing
        an IdentityUnit object, with no available options."""
        obfs_unit = obfscli.CliIdentityUnit()
        self.assertTrue(obfs_unit.edit_cli())

    def test_augment_opaque_get_cli_quit(self) -> None:
        """Tests that the CLI correctly provies an interface for editing
        an AugmentOpaqueUnit object, which can be quit at all stages."""
        output = io.StringIO()
        with patch("builtins.input", side_effect=["quit"]), redirect_stdout(output):
            obfscli.CliIdentityUnit.get_cli()
        print(output.getvalue())
        output = io.StringIO()
        with patch("builtins.input", side_effect=["3", "quit"]), redirect_stdout(
            output
        ):
            obfscli.CliIdentityUnit.get_cli()
        print(output.getvalue())
        output = io.StringIO()
        with patch("builtins.input", side_effect=["3", "0.5", "quit"]), redirect_stdout(
            output
        ):
            obfscli.CliIdentityUnit.get_cli()
        print(output.getvalue())


if __name__ == "__main__":
    unittest.main()
