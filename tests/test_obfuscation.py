import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from app import settings as cfg
from app.obfuscation import *
from app.interaction import CSource
from app import debug
from tests import *
import io
import itertools
import pytest
import subprocess
import shutil
import sys
import enum
from copy import deepcopy
from typing import Callable, Any, Type
from random import uniform as randf, randint as randi


class UsedDepth(enum.Enum):
    LIGHTEST = 0
    VERY_LIGHT = 1
    LIGHT = 2
    MEDIUM = 3
    HEAVY = 4


INTEGRATION_TEST_STYLE = UsedDepth.LIGHTEST


def callfunc_neq(func: Callable, neq: Iterable[Any]) -> Any:
    """Repeatedly (iteratively) calls the provided function until
    the returned value is not a member of the given `neq` list.
    Then, adds that value to the neq list and returns it.
    Be careful, as depending on the arguments, this can infinitely loop.

    Args:
        func (Callable): The function to iteratively call.
        neq (Iterable[Any]): The list of disallowed return values

    Returns:
        Any: The returned value that is not in neq.
    """
    x = func()
    while x in neq:
        x = func()
    return x


class TestObfuscationIntegration(unittest.TestCase):
    """Implements integration tests for the obfuscation transformations,
    checking that these methods, for different combinations of options/parameters
    (and different combinations of methods) and different random seeds, can
    correctly obfuscate a set of example programs and compile them, running them
    to achieve the same result."""

    transforms = [
        IdentityUnit,
        IdentifierRenameUnit,
        ReverseIndexUnit,
        ClutterWhitespaceUnit,
        DiTriGraphEncodeUnit,
        StringEncodeUnit,
        IntegerEncodeUnit,
        ArithmeticEncodeUnit,
        FuncArgumentRandomiseUnit,
        AugmentOpaqueUnit,
        InsertOpaqueUnit,
        ControlFlowFlattenUnit,
    ]
    options = {
        IdentityUnit: [tuple()],  # 1 Option
        IdentifierRenameUnit: list(  # 8 Options
            itertools.product(
                [
                    IdentifierTraverser.Style.COMPLETE_RANDOM,
                    IdentifierTraverser.Style.ONLY_UNDERSCORES,
                    IdentifierTraverser.Style.MINIMAL_LENGTH,
                    IdentifierTraverser.Style.I_AND_L,
                ],
                # [True, False],
                [False],  # TODO add back True when fixed
            )
        ),
        ReverseIndexUnit: [  # 8 Options
            (0.0,),
            (1.0,),
            (0.5,),
            tuple([callfunc_neq(lambda: randf(0, 1), set([0.0, 1.0, 0.5]))]),
            tuple([callfunc_neq(lambda: randf(0, 1), set([0.0, 1.0, 0.5]))]),
            tuple([callfunc_neq(lambda: randf(0, 1), set([0.0, 1.0, 0.5]))]),
            tuple([callfunc_neq(lambda: randf(0, 1), set([0.0, 1.0, 0.5]))]),
            tuple([callfunc_neq(lambda: randf(0, 1), set([0.0, 1.0, 0.5]))]),
        ],
        ClutterWhitespaceUnit: list(  # 16 Options
            itertools.product(
                [
                    0,
                    999999999999999999999999999999,
                    50,
                    100,
                    callfunc_neq(lambda: randi(5, 100), set([0, 50, 100])),
                    callfunc_neq(lambda: randi(5, 100), set([0, 50, 100])),
                    callfunc_neq(lambda: randi(5, 100), set([0, 50, 100])),
                    callfunc_neq(lambda: randi(5, 100), set([0, 50, 100])),
                ],
                [True, False],
            )
        ),
        DiTriGraphEncodeUnit: list(  # 15 Options
            itertools.product(
                [
                    DiTriGraphEncodeUnit.Style.DIGRAPH,
                    DiTriGraphEncodeUnit.Style.TRIGRAPH,
                    DiTriGraphEncodeUnit.Style.MIXED,
                ],
                [
                    0,
                    1.0,
                    0.5,
                    callfunc_neq(lambda: randf(0, 1), set([0.0, 1.0, 0.5])),
                    callfunc_neq(lambda: randf(0, 1), set([0.0, 1.0, 0.5])),
                ],
            )
        ),
        StringEncodeUnit: [  # 4 Options
            (StringEncodeTraverser.Style.OCTAL,),
            (StringEncodeTraverser.Style.HEX,),
            (StringEncodeTraverser.Style.MIXED,),
            (StringEncodeTraverser.Style.ALL,),
        ],
        IntegerEncodeUnit: [(IntegerEncodeTraverser.Style.SIMPLE,)],  # 1 Option
        ArithmeticEncodeUnit: [  # 6 Options
            (0,),
            (1,),
            (2,),
            (3,),
            (4,),
            (5,),
        ],
        FuncArgumentRandomiseUnit: list(  # 16 Options
            itertools.product(
                [
                    0,
                    3,
                    5,
                    10,
                    100,
                    callfunc_neq(lambda: randi(0, 250), set([0, 3, 5, 10, 100])),
                    callfunc_neq(lambda: randi(0, 250), set([0, 3, 5, 10, 100])),
                    callfunc_neq(lambda: randi(0, 250), set([0, 3, 5, 10, 100])),
                ],
                [True, False],
            )
        ),
        AugmentOpaqueUnit: list(  # 75 Options
            itertools.product(
                list(
                    itertools.chain.from_iterable(
                        itertools.combinations(
                            [
                                OpaqueAugmenter.Style.INPUT,
                                OpaqueAugmenter.Style.ENTROPY,
                            ],
                            r,
                        )
                        for r in range(1, 3)
                    )
                ),
                [
                    0.0,
                    0.5,
                    1.0,
                    callfunc_neq(lambda: randf(0, 1), set([0.0, 1.0, 0.5])),
                    callfunc_neq(lambda: randf(0, 1), set([0.0, 1.0, 0.5])),
                ],
                [0, 1, 2, 3, 4],
            )
        ),
        InsertOpaqueUnit: list(
            itertools.product(  # 1953 options # TODO is this OK?
                list(  # 3
                    itertools.chain.from_iterable(
                        itertools.combinations(
                            [
                                OpaqueInserter.Style.INPUT,
                                OpaqueInserter.Style.ENTROPY,
                            ],
                            r,
                        )
                        for r in range(1, 3)
                    )
                ),
                list(  # 7
                    itertools.chain.from_iterable(
                        itertools.combinations(
                            [
                                OpaqueInserter.Granularity.PROCEDURAL,
                                OpaqueInserter.Granularity.BLOCK,
                                OpaqueInserter.Granularity.STMT,
                            ],
                            r,
                        )
                        for r in range(1, 4)
                    )
                ),
                list(  # 31
                    itertools.chain.from_iterable(
                        itertools.combinations(
                            [
                                OpaqueInserter.Kind.CHECK,
                                OpaqueInserter.Kind.FALSE,
                                OpaqueInserter.Kind.ELSE,
                                OpaqueInserter.Kind.EITHER,
                                OpaqueInserter.Kind.WHILE_FALSE,
                            ],
                            r,
                        )
                        for r in range(1, 6)
                    )
                ),
                [1, 2, 3],
            )
        ),
        ControlFlowFlattenUnit: list(  # 6 Options
            itertools.product(
                [True, False],
                [
                    ControlFlowFlattener.Style.SEQUENTIAL,
                    ControlFlowFlattener.Style.RANDOM_INT,
                    ControlFlowFlattener.Style.ENUMERATOR,
                ],
            )
        ),
    }

    def __parse_input(self, contents: str) -> list[str] | None:
        """Parses the given program file for input, searching for a line
        that starts with '//////' to delimit the input contents. Then reads
        the intended input contents from the rest of that line, and returns
        them as a list of string arguments to give when running the example
        program.

        Args:
            contents (str): The contents of the example program file

        Returns:
            list[str] | None: The arguments to give to the program. Returns
            None if no input arguments are found.
        """
        for line in contents.splitlines():
            line = line.strip()
            if line.startswith("//////"):
                line = line.replace("//////", "")
                return line.split(" ")
        return None

    def __get_program_output(self, filepath: str, inputs: list[str]) -> str | None:
        """Given the filepath of an example C program, and a list of
        strings corresponding to command line arguments to run the program
        with, this method compiles the program using clang with the commands:
          clang -O -o obfs.exe [filepath] -trigraphs
          ./obfs.exe [inputs]
        And returns the standard output returned when running the program.

        Args:
            filepath (str): The absolute path to the C source file to run.
            inputs (list[str]): The command-line arguments to provide to the
            program when running.

        Returns:
            str | None: The output (on the stdout stream) of the program
            when compiled and run with the specified command line arguments.
            Returns None if compilation fails or some other error occurs
            during execution.
        """
        try:
            output = subprocess.check_output(
                [
                    "clang",
                    "-O",
                    "-o",
                    "./tests/testing/obfs.exe",
                    filepath,
                    "-trigraphs",
                ]
            ).decode("utf-8")
            if "error" in output:
                return None
            os.chmod("./tests/testing/obfs.exe", 0o777)
            return subprocess.check_output(
                ["./tests/testing/obfs.exe"] + inputs
            ).decode("utf-8")
        except Exception as e:
            return None

    def __get_example_programs(self) -> dict[str, Tuple[CSource, list[str], str]]:
        """Gets the path and resulting output of all example programs to be tested by
        the integration tests. Searches for programs in specified directories containing
        meaningful content and that compile and run correctly.

        Returns:
            dict[str, Tuple[CSource,list[str],str]]: A dictionary of example programs.
            Each key is the absolute file path to the program, and each value is a tuple,
            where the first tuple element is a the C source file object used in
            transformations, the second tuple element is the list of command-line arguments
            to run the program with, and the third tuple element is the stdout output of the
            program with those command-line arguments supplied.
        """
        programs = {}
        explore_dirs = ["./tests/data/examples/", "./tests/data/constructs"]
        explore_dirs = [os.path.join(os.getcwd(), dir_) for dir_ in explore_dirs]
        for dir_ in explore_dirs:
            for file in os.listdir(dir_):
                filepath = os.path.join(dir_, file)
                if not os.path.isfile(filepath) or not filepath.endswith(".c"):
                    continue
                with open(filepath, "r") as f:
                    contents = f.read().strip()
                if len(contents) == 0:
                    continue
                inputs = self.__parse_input(contents)
                if inputs is None:
                    continue
                output = self.__get_program_output(filepath, inputs)
                if output is None:
                    continue
                source = CSource(filepath, contents)
                if not source.valid_parse:
                    continue
                programs[filepath] = (source, inputs, output)
        return programs

    def test_valid_parameters(self) -> None:
        """Tests that the defined enumerated parameters / boundary and random parameters
        are actually valid and accepted by the relevant obfuscation unit classes."""
        clean_dir()
        reset_config()
        for transform in self.transforms:
            for parameters in self.options[transform]:
                transform(*parameters)

    def __run_test(
        self,
        test: int,
        num_tests: int,
        passed: int,
        pipeline: Pipeline,
        filepath: str,
        source: CSource,
        inputs: str,
        expected_output: str,
        seed: int,
    ) -> bool:
        # TODO Docstring
        exception_handled = False
        try:
            result = pipeline.process(deepcopy(source))
        except:
            exception_handled = True
        if not result.valid_parse or exception_handled:
            debug.log(
                (
                    "Test {} - Failed [obfuscation error] ({}/{})\n"
                    "   Transform={},\n"
                    "   Example={},\n"
                    "   Seed={}"
                ).format(
                    test,
                    passed,
                    num_tests,
                    str(pipeline),
                    filepath.split("\\./")[-1],
                    seed,
                )
            )
            return False
        obfs_filepath = os.path.join(os.getcwd(), "./tests/testing/obfs.c")
        with open(obfs_filepath, "w+") as f:
            f.write(result.contents)
        output = self.__get_program_output(obfs_filepath, inputs)
        if output is None:
            debug.log(
                (
                    "Test {} - Failed [compile/run error] ({}/{})\n"
                    "   Transform={},\n"
                    "   Example={},\n"
                    "   Seed={}"
                ).format(
                    test,
                    passed,
                    num_tests,
                    str(pipeline),
                    filepath.split("\\./")[-1],
                    seed,
                )
            )
            return False
        if output != expected_output:
            debug.log(
                (
                    "Test {} - Failed [correctness error] ({}/{})\n"
                    "   Transform={},\n"
                    "   Example={},\n"
                    "   Seed={}\n,"
                    "       Expected={}\n"
                    "       Received={}"
                ).format(
                    test,
                    passed,
                    num_tests,
                    str(pipeline),
                    filepath.split("\\./")[-1],
                    seed,
                    expected_output,
                    output,
                )
            )
            return False
        passed += 1
        debug.log("Test {} - Passed ({}/{})".format(test, passed, num_tests))
        return True

    def __get_bounded(self, options: Iterable[Any], max_: int) -> Iterable[Any]:
        # TODO Docstring
        if len(options) <= max_:
            return options
        # Always include the first or last - as edge cases
        return [options[0], options[-1]] + random.sample(options[1:-1], max_ - 2)

    def test_single_transforms(self) -> None:
        """Tests that for every single obfuscation transform, for every single defined set of
        predefined options/parameters, for every example program, for 10 random seeds,
        the obfuscation runs correctly, and the resulting program compiles correctly and
        provides the same result as the original program.
        Runs approximately 10N * M * P + P programs to determine this correctness, where:
            - N is the number of obfuscation transformation methods.
            - M is the average number of sets of transform options.
            - P is the number of example programs."""
        # TODO the above is out of date now
        # Reset state, initialise testing directory and retrieve examples
        reset_config()
        test_path = os.path.join(os.getcwd(), "./tests/testing")
        if os.path.isdir(test_path):
            shutil.rmtree(test_path)
        os.mkdir(test_path, 0o777)
        try:
            examples = self.__get_example_programs()
        except:
            self.fail("Example programs could not be retrieved.")
        debug.create_log_file()

        # Calculate number of required tests from setting
        bounds = {
            UsedDepth.LIGHTEST: (1, 10, 2),
            UsedDepth.VERY_LIGHT: (1, 20, 10),
            UsedDepth.LIGHT: (3, 50, 100),
            UsedDepth.MEDIUM: (5, 100, 100000),
            UsedDepth.HEAVY: (10, 100000, 100000),
        }
        num_seeds, max_options, max_programs = bounds[INTEGRATION_TEST_STYLE]
        runs = (
            sum(min(len(self.options[t]), max_options) for t in self.transforms)
            * min(len(examples), max_programs)
            * num_seeds
        )
        passed = 0
        test_num = 1

        # Perform the tests according to the setings
        for transform in self.transforms:
            for parameters in self.__get_bounded(self.options[transform], max_options):
                for program in self.__get_bounded(list(examples.keys()), max_programs):
                    for seed in random.sample(range(0, 100000), num_seeds):
                        test_passed = self.__run_test(
                            test_num,
                            runs,
                            passed,
                            Pipeline(seed, transform(*parameters)),
                            program,
                            *examples[program],
                            seed
                        )
                        test_num += 1
                        if test_passed:
                            passed += 1

        # Assert that all tests passed
        self.assertEqual(passed, runs)

    """def test_double_transforms(self) -> None:
        # TODO docstring
        # Reset state, initialise testing directory and retrieve examples
        reset_config()
        test_path = os.path.join(os.getcwd(), "./tests/testing")
        if os.path.isdir(test_path):
            shutil.rmtree(test_path)
        os.mkdir(test_path, 0o777)
        try:
            examples = self.__get_example_programs()
        except:
            self.fail("Example programs could not be retrieved.")
        debug.create_log_file()

        # Calculate number of required tests from setting
        bounds = {
            UsedDepth.LIGHTEST: (1, 10, 2),
            UsedDepth.VERY_LIGHT: (1, 20, 10),
            UsedDepth.LIGHT: (3, 50, 100),
            UsedDepth.MEDIUM: (5, 100, 100000),
            UsedDepth.HEAVY: (10, 100000, 100000),
        }
        num_seeds, max_options, max_programs = bounds[INTEGRATION_TEST_STYLE]
        runs = (
            sum(min(len(self.options[t]), max_options) for t in self.transforms)
            * min(len(examples), max_programs)
            * num_seeds
        )
        passed = 0
        test_num = 0

        # Perform the tests according to the setings
        for transform in self.transforms:
            for parameters in self.__get_bounded(self.options[transform], max_options):
                for program in self.__get_bounded(list(examples.keys()), max_programs):
                    for seed in random.sample(range(0, 100000), num_seeds):
                        test_passed = self.__run_test(
                            test_num,
                            runs,
                            passed,
                            Pipeline(seed, transform(*parameters)),
                            program,
                            *examples[program],
                            seed
                        )
                        test_num += 1
                        if test_passed:
                            passed += 1

        # Assert that all tests passed
        self.assertEqual(passed, runs)"""

# TODO could have a very scaled down testing plan and a very scaled up testing plan?
# General obfuscation testing idea (using N = number of transforms, M = avg number of preset options, P = number of programs)
#   - For every method
#       - For every combination of limited (predefined) options/parameters:
#           - For a program type for each AST node AND every example program
#               - For 10 random seeds
#                   - Run the method on the program, and check it runs without error.
#                   - Run the method on the program, and check it compiles.
#                   - Run the method on the program, and check it gives the same result.
#       ? Check the transform performs as we would expect for every AST node type.
#   = (30N * M * P) runs
#   - For every combination of two methods
#       - For 5 combinations of random options/parameters:
#           - For every example program
#               - For 10 random seeds:
#                   - Run the method on the program, and check it runs without error.
#                   - Run the method on the program, and check it compiles.
#                   - Run the method on the program, and check it gives the same result.
#   = (150N^2 * P) runs
#   - For every combination of three methods
#       - For 3 combinations of random options/parameters:
#           - For every example program
#               - Run the method on the example, and check it runs without error
#               - Run the method on the example, and check it compiles
#               - Run the method on the example, and check it gives the same result
#   = (9N^3 * P) runs
#   - For 500 random combinations of all 12 methods
#       - For 10 combinations of random options/parameters:
#           - For every example program
#               - Run the method on the example, and check it runs without error
#               - Run the method on the example, and check it compiles
#               - Run the method on the example, and check it gives the same result
#   = (15000P) runs
# Assuming 12 methods, 50 average option combinations, and 50 example programs, that gives
#   = 900,000 + 1,080,000 + 777,600 + 750,000 = 3,507,600 tests (2,338,400 C program executions)

if __name__ == "__main__":
    INTEGRATION_TEST_STYLE = UsedDepth.MEDIUM
    test_class = TestObfuscationIntegration("test_single_transforms")
    test_class.run()
