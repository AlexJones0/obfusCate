""" File: tests/test_obfuscation.py
Implements procedural property-based tests for the functionality and correctness
of obfuscation within the program, randomly generating tens of thousands to 
millions of tests and performing obfuscations to ensure that the implementation
is correct. Tests are implemented for both single transformations, pairs of 
transformations, and sequences of all 12 implemented obfusation transformations.
"""
from app import debug
from app.obfuscation import *
from app.interaction import CSource
from tests import *
from copy import deepcopy
from typing import Callable, Any, Type
from random import uniform as randf, randint as randi
import itertools, subprocess, shutil, enum, unittest


class UsedDepth(enum.Enum):
    """An enumerated type used to control the scale of property-based testing performed
    when checking correctness."""

    NONE = 0
    LIGHTEST = 1
    LIGHT = 2
    MEDIUM = 3
    HEAVY = 4
    EXTREME = 5


# Set the scale of property-based testing to be performed here.
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


# List of all available transformations to test
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

# Dictionary mapping all transforms to their list of possible option combinations
options = {
    IdentityUnit: [tuple()],  # 1 Option
    IdentifierRenameUnit: list(  # 8 Options
        itertools.product(
            [
                IdentifierRenameUnit.Style.COMPLETE_RANDOM,
                IdentifierRenameUnit.Style.ONLY_UNDERSCORES,
                IdentifierRenameUnit.Style.MINIMAL_LENGTH,
                IdentifierRenameUnit.Style.I_AND_L,
            ],
            [True, False],
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
                99999,
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
    IntegerEncodeUnit: [tuple()],  # 1 Option
    ArithmeticEncodeUnit: [  # 4 Options
        (0,),
        (1,),
        (2,),
        (3,),
    ],
    FuncArgumentRandomiseUnit: list(  # 48 Options
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
            [0.0, 0.5, 1.0],
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
        itertools.product(  # 1953 options
            list(
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
                            OpaqueInserter.Kind.ELSE_TRUE,
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


def parse_input(contents: str) -> list[str] | None:
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


def get_program_output(filepath: str, inputs: list[str]) -> str | None:
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
        output = subprocess.run(
            [
                "clang",
                "-O",
                "-o",
                "./tests/testing/obfs.exe",
                filepath,
                "-trigraphs",
            ],
            capture_output=True,
            text=True,
        )
        output = output.stdout + "\n" + output.stderr
        if "error" in output:
            return None
        os.chmod("./tests/testing/obfs.exe", 0o777)
        output = subprocess.run(
            ["./tests/testing/obfs.exe"] + inputs, capture_output=True, text=True
        )
        return output.stdout + "\n" + output.stderr
    except Exception as e:
        return None


def get_example_programs() -> dict[str, Tuple[CSource, list[str], str]]:
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
            inputs = parse_input(contents)
            if inputs is None:
                continue
            output = get_program_output(filepath, inputs)
            if output is None:
                continue
            source = CSource(filepath, contents)
            if not source.valid_parse:
                continue
            programs[filepath] = (source, inputs, output)
    return programs


def run_test(
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
    """Run a property based test, attempting to obfuscate, then compile, and then run
    a program, and comparing its output to the pre-computed unobfuscated output. If
    any of these steps fail, a corresponding debugging log will be created discussing
    the reason for failure and providing as much helpful context as possible, including
    the exact program/transforms/seed such that the error can be reproduced, any relevant
    error messages, and any relevant program outputs in the case of incorrect results.

    Args:
        test (int): The chronological number of this test. Used to format debug messages.
        num_tests (int): The total number of tests run in this scheme. Used to format debug messages.
        passed (int): The total number of tests passed so far in this testing scheme. Used
        to format debug messages.
        pipeline (Pipeline): The obfuscation pipeline to apply to transform the program, with
        all relevant obfuscation transformations and a random seed already set.
        filepath (str): The file path of the source program the test is generated on. Used to
        format debug messages.
        source (CSource): The original source C program loaded from the filepath that is to
        be obfuscated. This will not be modified in this function.
        inputs (str): The list of command-line inputs that should be fed to the program when
        running it during the test.
        expected_output (str): The expected output of the program as a string, representing
        the concatenated standard output and standard error strings (separated by a newline).
        This should be the value for the original program's execution.
        seed (int): The random seed applied in the obfuscation pipeline. Used to format debug
        messages.

    Returns:
        bool: True if the test passed, False if the test failed.
    """

    # Try to obfuscate the program. If an exception occurs, log this and return.
    exception_handled = None
    try:
        result = pipeline.process(deepcopy(source))
    except Exception as e:
        exception_handled = e
    if exception_handled is not None or not result.valid_parse:
        debug.logprint(
            (
                "FAIL Test {} - Failed [obfuscation error] ({}/{})\n"
                "   Transform={},\n"
                "   Example={},\n"
                "   Seed={}{}"
            ).format(
                test,
                passed,
                num_tests,
                str(pipeline),
                filepath.split("\\./")[-1],
                seed,
                "\n   Exception={}".format(exception_handled)
                if exception_handled is not None
                else "",
            ),
            err=False,
        )
        return False

    # Save and try to compile and run the program. If this fails, log this and return.
    obfs_filepath = os.path.join(os.getcwd(), "./tests/testing/obfs.c")
    with open(obfs_filepath, "w+") as f:
        f.write(result.contents)
    output = get_program_output(obfs_filepath, inputs)
    if output is None:
        debug.logprint(
            (
                "FAIL Test {} - Failed [compile/run error] ({}/{})\n"
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
            ),
            err=False,
        )
        return False

    # Compare the actual obfusacted program output to the expected original program output.
    # If this is wrong, log this error and then return.
    if output != expected_output:
        debug.logprint(
            (
                "FAIL Test {} - Failed [correctness error] ({}/{})\n"
                "   Transform={},\n"
                "   Example={},\n"
                "   Seed={},\n"
                "   Program={}\n"
                "       Expected={}\n"
                "       Received={}"
            ).format(
                test,
                passed,
                num_tests,
                str(pipeline),
                filepath.split("\\./")[-1],
                seed,
                result.contents,
                expected_output,
                output,
            ),
            err=False,
        )
        return False

    # All checks pass and so the test is passed, which should aso be logged before returning.
    passed += 1
    debug.logprint(
        "INFO Test {} - Passed ({}/{})".format(test, passed, num_tests), err=False
    )
    return True


def get_bounded(
    options: Iterable[Any], max_: int, first_last: bool = False
) -> Iterable[Any]:
    """Given a large set of options, this function returns a bounded number of these
    options, which are randomly sampled. Optionally the first and last option can
    be guaranteed to be included to account for bondary options.

    Args:
        options (Iterable[Any]): The list of options to select from.
        max_ (int): The maximum number of options that can be selected (upper bound).
        first_last (bool, optional): Whether to guaranteed include the last and first
        option or not. Defaults to False.

    Returns:
        Iterable[Any]: The selected bounded list of options
    """
    if len(options) <= max_:
        return options
    if first_last:
        # Always include the first or last - as boundary edge cases
        return [options[0], options[-1]] + random.sample(options[1:-1], max_ - 2)
    else:
        return random.sample(options, max_)


class TestObfuscationIntegrationParams(unittest.TestCase):
    """Implements integration tests for the obfuscation transformations,
    checking that these methods, for different combinations of options/parameters
    (and different combinations of methods) and different random seeds, can
    correctly obfuscate a set of example programs and compile them, running them
    to achieve the same result."""

    def test_valid_parameters(self) -> None:
        """Tests that the defined enumerated parameters / boundary and random parameters
        are actually valid and accepted by the relevant obfuscation unit classes."""
        clean_dir()
        reset_config()
        for transform in transforms:
            for parameters in options[transform]:
                transform(*parameters)


class TestObfuscationIntegrationSingle(unittest.TestCase):
    """Implements integration tests for the obfuscation transformations,
    checking that these methods, for different combinations of options/parameters
    (and different combinations of methods) and different random seeds, can
    correctly obfuscate a set of example programs and compile them, running them
    to achieve the same result."""

    def test_single_transforms(self) -> None:
        """Tests that for every single obfuscation transform, for every single defined set of
        predefined options/parameters, for some example programs, for some random seeds,
        the obfuscation runs correctly, and the resulting program compiles correctly and
        provides the same result as the original program. This tests that each transformation
        definitely works independently of each other."""
        if INTEGRATION_TEST_STYLE == UsedDepth.NONE:
            return

        # Initialise testing environment and retrieve example programs
        reset_config()
        test_path = os.path.join(os.getcwd(), "./tests/testing")
        if os.path.isdir(test_path):
            shutil.rmtree(test_path)
        os.mkdir(test_path, 0o777)
        examples = get_example_programs()
        debug.create_log_file()
        programs = list(examples.keys())

        # Calculate number of required tests from setting
        bounds = {
            UsedDepth.LIGHTEST: (1, 10, 3),
            UsedDepth.LIGHT: (1, 20, 10),
            UsedDepth.MEDIUM: (3, 50, 100),
            UsedDepth.HEAVY: (5, 100, 100000),
            UsedDepth.EXTREME: (10, 100000, 100000),
        }
        num_seeds, max_options, max_programs = bounds[INTEGRATION_TEST_STYLE]
        runs = (
            sum(min(len(options[t]), max_options) for t in transforms)
            * min(len(examples), max_programs)
            * num_seeds
        )
        passed = 0
        test_num = 1

        # Perform the tests according to the setings
        for t in transforms:
            for parameters in get_bounded(options[t], max_options, True):
                for program in get_bounded(programs, max_programs):
                    for seed in random.sample(range(0, 100000), num_seeds):
                        test_passed = run_test(
                            test_num,
                            runs,
                            passed,
                            Pipeline(seed, t(*parameters)),
                            program,
                            *examples[program],
                            seed
                        )
                        test_num += 1
                        if test_passed:
                            passed += 1

        # Assert that all tests passed
        self.assertEqual(passed, runs)


class TestObfuscationIntegrationDouble(unittest.TestCase):
    """Implements integration tests for the obfuscation transformations,
    checking that these methods, for different combinations of options/parameters
    (and different combinations of methods) and different random seeds, can
    correctly obfuscate a set of example programs and compile them, running them
    to achieve the same result."""

    def test_double_transforms(self) -> None:
        """Tests that for every possible pair of obfuscation transforms, for some combinations
        of predefined options/parameters, for some example programs, for some random seeds,
        that the obfusaction runs correctly, and that the resulting program compiles correctly
        and provides the same result as the original program. This tests that a transformations
        work when combined with each other."""
        if INTEGRATION_TEST_STYLE == UsedDepth.NONE:
            return

        # Initialise testing environment and retrieve example programs
        reset_config()
        test_path = os.path.join(os.getcwd(), "./tests/testing")
        if os.path.isdir(test_path):
            shutil.rmtree(test_path)
        os.mkdir(test_path, 0o777)
        try:
            examples = get_example_programs()
        except:
            self.fail("Example programs could not be retrieved.")
        debug.create_log_file()
        programs = list(examples.keys())

        # Calculate number of required tests from setting
        bounds = {
            UsedDepth.LIGHTEST: (1, 2, 2),
            UsedDepth.LIGHT: (1, 5, 5),
            UsedDepth.MEDIUM: (3, 5, 100),
            UsedDepth.HEAVY: (5, 25, 100000),
            UsedDepth.EXTREME: (10, 1000, 100000),
        }
        num_seeds, max_options, max_programs = bounds[INTEGRATION_TEST_STYLE]
        runs = 0
        for t1 in transforms:
            for t2 in transforms:
                runs += min(len(options[t1]) * len(options[t2]), max_options)
        runs *= min(len(examples), max_programs) * num_seeds
        passed = 0
        test_num = 1

        # Perform the tests according to the setings
        combination_options = lambda t1, t2: get_bounded(
            list(itertools.product(options[t1], options[t2])), max_options
        )
        for t1 in transforms:
            for t2 in transforms:
                for t1params, t2params in combination_options(t1, t2):
                    for program in get_bounded(programs, max_programs):
                        for seed in random.sample(range(0, 100000), num_seeds):
                            debug.log(f"{test_num} {passed} {runs}\n")
                            test_passed = run_test(
                                test_num,
                                runs,
                                passed,
                                Pipeline(seed, t1(*t1params), t2(*t2params)),
                                program,
                                *examples[program],
                                seed
                            )
                            test_num += 1
                            if test_passed:
                                passed += 1

        # Assert that all tests passed
        self.assertEqual(passed, runs)


class TestObfuscationIntegrationMax(unittest.TestCase):
    """Implements integration tests for the obfuscation transformations,
    checking that these methods, for different combinations of options/parameters
    (and different combinations of methods) and different random seeds, can
    correctly obfuscate a set of example programs and compile them, running them
    to achieve the same result."""

    def __get_composition_options(
        self, composition: list[Type[ObfuscationUnit]], n: int
    ) -> list[Tuple[Tuple[Any]]]:
        """Retrieves a set of n random options for a specific sequence of
        obfuscation units, such that the given sequence of obfuscation units can
        be run with these options in procedural testing. These options are chosen
        entirely at random and combined with each other.

        Args:
            composition (list[Type[ObfuscationUnit]]): The sequence of obfuscation
            methods to be applied in the test.
            n (int): The number of unique combinations of options to generate.

        Returns:
            list[Tuple[Tuple[Any]]]: A list of n tuples, where each tuple is a list
            of selected options for the sequence of transforms (corresponding to one
            test environment), where each element of that option tuple is itself
            a tuple containing options that can be given to each obfuscation
            transformation during initialisation.
        """
        all_options = []
        for _ in range(n):
            selected_options = []
            for transform in composition:
                t_opts = options[transform]
                selected = t_opts[random.randint(0, len(t_opts) - 1)]
                selected_options.append(selected)
            all_options.append(tuple(selected_options))
        return all_options

    def test_max_transforms(self) -> None:
        """Tests that for some random sequences combining all 12 obfuscation transformations,
        in some random orders with some random options, for some example programs, for some
        random seeds, that the obfuscation runs correctly, and that the resulting program
        compiles correctly and provides the same result as the original program. This tests that
        the system works at scale, combining all transformations together with each other."""
        if INTEGRATION_TEST_STYLE == UsedDepth.NONE:
            return

        # Initialise testing environment and retrieve example programs
        reset_config()
        test_path = os.path.join(os.getcwd(), "./tests/testing")
        if os.path.isdir(test_path):
            shutil.rmtree(test_path)
        os.mkdir(test_path, 0o777)
        try:
            examples = get_example_programs()
        except:
            self.fail("Example programs could not be retrieved.")
        debug.create_log_file()
        programs = list(examples.keys())

        # Calculate number of required tests from setting
        bounds = {
            UsedDepth.LIGHTEST: (1, 10, 10, 2),
            UsedDepth.LIGHT: (1, 20, 10, 5),
            UsedDepth.MEDIUM: (3, 20, 10, 100),
            UsedDepth.HEAVY: (5, 30, 30, 100000),
            UsedDepth.EXTREME: (10, 250, 250, 100000),
        }
        num_seeds, max_comps, max_options, max_programs = bounds[INTEGRATION_TEST_STYLE]
        runs = max_comps * max_options * min(len(programs), max_programs) * num_seeds
        passed = 0
        test_num = 1

        # Perform the tests according to the setings
        compositions = []
        for _ in range(max_comps):
            copied_transforms = [t for t in transforms]
            random.shuffle(copied_transforms)
            compositions.append(copied_transforms)
        for composition in compositions:
            for params in self.__get_composition_options(composition, max_options):
                for program in get_bounded(programs, max_programs):
                    for seed in random.sample(range(0, 100000), num_seeds):
                        test_passed = run_test(
                            test_num,
                            runs,
                            passed,
                            Pipeline(
                                seed, *[t(*p) for t, p in zip(composition, params)]
                            ),
                            program,
                            *examples[program],
                            seed
                        )
                        test_num += 1
                        if test_passed:
                            passed += 1

        # Assert that all tests passed
        self.assertEqual(passed, runs)


if __name__ == "__main__":
    unittest.main()
