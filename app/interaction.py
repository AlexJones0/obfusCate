""" File: io.py
Implements classes and functions for handling input and output. """
from typing import Iterable, Optional, Tuple, Union
from .debug import print_error, log, delete_log_file
from pycparser import parse_file
from pycparser.c_ast import FileAST
from app import settings as cfg
import os
from time import localtime



class CSource:
    """A class representing a C source code program, storing its contents in both
    string form and as a Clang-parsed translation unit."""

    def __init__(
        self,
        filepath: str,
        contents: Optional[str] = None,
        t_unit: Optional[FileAST] = None,
    ):
        """A constructor for a CSource object.

        Args:
            filepath (str): The path to the C file.
            contents (Optional[str], optional): The contents of the file. Defaults to
            None, in which case the file path is opened and read to retrieve contents.
            t_unit (Optional[TranslationUnit], optional): The translation unit of the file
            after it is parsed by clang. Defaults to None, in which case it is retrieved
            by parsing the file.
        """
        self.fpath = filepath
        if contents is None:
            log(f"Started loading source file with path {filepath}")
            self.contents = self.__read_file()
        else:
            self.contents = contents
        if self.contents is None:
            return
        if t_unit is None:
            self.t_unit = self.parse()
        else:
            self.t_unit = t_unit

    def __read_file(self) -> Optional[str]:
        """Reads the file contents from the stored file path, raising errors and logging
        as appropriate.

        Returns:
            Optional[str]: The string contents of the file, or None if some error occurs.
        """
        if not self.fpath.endswith(".c"):
            print_error(f"Supplied file {self.fpath} is not a .c file!")
            return None
        log("Started reading contents from source file.")
        try:
            with open(self.fpath, "r") as source_file:
                contents = source_file.read()
            return contents
        except OSError as e:
            log(f"Error in opening source file: {str(e)}.")
        return None

    def parse(self) -> Optional[FileAST]:
        """Parses the file using the clang parser to produce a translation unit, raising
        errors and logging as appropriate.

        Returns:
            Optional[TranslationUnit]: The clang translation unit of the parsed file, or
            None if some error occurs.
        """
        log("Attempting to parse program.")
        try:
            t_unit = parse_file(
                self.fpath,
                use_cpp=True,
                cpp_path="clang",
                cpp_args=["-E", r"-Iutils/fake_libc_include"],
            )  # TODO check cpp stuff here? + with github actions
            fname = self.fpath.split("\\")[-1]
            t_unit.ext = [x for x in t_unit.ext if fname in x.coord.file]
            # TODO could also modify contents to cut off directives?
            return t_unit
        except Exception as e:
            log(f"Unexpected error whilst parsing the program: {str(e)}.")
            print_error(
                f"An unknown error occurred whilst trying to parse {self.fpath}."
            )
            return None

    def copy(self) -> "CSource":
        """Creates a copy of the code record, producing a separate translation unit.

        Returns:
            CSource: A copy of the file with the same path, contents and parsed contents.
        """
        log(f"Creating copy of source: {self.fpath}.")
        return CSource(self.fpath, self.contents)

    @property
    def valid_parse(self) -> bool:
        """This boolean property describes whether a valid parse has been performed on
        the C source file or not."""
        return self.t_unit is not None

    """@property
    def parse_errors(self) -> Iterable[str]:
        #Retrieves a list of string error/warning messages generated during the parse of
        #the C source file by clang.
        #
        #Returns:
        #    Iterable[str]: A list of strings, where each string is an individual parse error.
        # 
        return [] # TODO FIX THIS
        if self.t_unit is None:
            return []
        return [str(d) for d in self.t_unit.diagnostics]"""


def menu_driven_option(
    options: Iterable[Union[str, Tuple[str, Iterable[str]]]], prompt: str = None
) -> int:
    """Performs command-line interface input handling for a generalized menu-driven
    system in which a restricted integer input must be made to select one of many
    options. Returns the chosen option.

    Args:
        options (Iterable[Union[str, Tuple[str, Iterable[str]]]]): The list of
        options to provide. Each option can either be a string, or a tuple like
        (string, [str1, str2, str3, ...]) where string is the option text and
        [str1, str2, str3, ...] are optional strings that the CLI should understand
        as a selction of that choice.
        prompt (str, optional): Additional prompt text to display to the user after
        the printing of options but before requesting input. Defaults to None.

    Returns:
        int: The integer index of the selected choice. -1 if it was selected to quit.
    """
    if len(options) == 0:
        return 0
    prompt = "" if prompt is None else prompt

    # Display options and prompt
    printable_options = [x[0] if isinstance(x, tuple) else x for x in options]
    for i, option in enumerate(printable_options):
        print(f" ({i+1}) {option}")
    print(prompt + "\n >", end="")

    # Loop until valid input received
    valid_input = False
    while not valid_input:
        try:
            choice = input().lower().strip()
            # Check for quit inputs
            if choice in ["q", "quit", "exit", "leave", "x"]:
                return -1
            # Check for keyword matches
            for i, option in enumerate(options):
                if isinstance(option, tuple) and choice in option[1]:
                    choice = i + 1
                    break
            # Check for valid integer choice ranges
            if not isinstance(choice, int):
                choice = int(choice)
            if choice > 0 and choice <= len(options):
                valid_input = True
            else:
                print(
                    "Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.\n >",
                    end="",
                )
        except:  # Handle non-integer (and non-keyword) inputs
            print(
                "Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.\n >",
                end="",
            )
    return choice - 1


def get_float(lower_bound: float = None, upper_bound: float = None) -> float:
    """Gets an input float from the user, applying appropriate boundary checks if either bound
    is specified. Returns NaN if the user quits the input selection, and a valid float otherwise."""
    while True:
        user_input = input("\n>").lower().strip()
        # Check for quit inputs
        if user_input in ["q", "quit", "exit", "leave", "x"]:
            return float("nan")
        try:
            user_input = float(user_input)
        except:
            print("Invalid input for a decimal number. Please try again...")
            continue
        if lower_bound is not None and user_input < lower_bound:
            print(
                f"Input {user_input} is too small. The value must be at least {lower_bound}."
            )
            continue
        if upper_bound is not None and user_input > upper_bound:
            print(
                f"Input {user_input} is too large. The value must be at most {upper_bound}."
            )
            continue
        return user_input


def get_int(lower_bound: int = None, upper_bound: int = None) -> Optional[int]:
    """Gets an input integer from the user, applying appropriate boundary checks if either bound
    is specified. Returns None if the user quits the input selecion, and a valid integer otherwise."""
    while True:
        user_input = input("\n>").lower().strip()
        # Check for quit inputs
        if user_input in ["q", "quit", "exit", "leave", "x"]:
            return None
        try:
            user_input = int(user_input)
        except:
            print("Invalid input for an integer. Please try again...")
            continue
        if lower_bound is not None and user_input < lower_bound:
            print(
                f"Input {user_input} is too small. The value must be at least {lower_bound}."
            )
            continue
        if upper_bound is not None and user_input > upper_bound:
            print(
                f"Input {user_input} is too large. The value must be at most {upper_bound}."
            )
            continue
        return user_input


def save_composition(json: str, filepath: str = None) -> bool:
    """Creates a composition file and saves the JSON string representing the
    composition to it.

    Args:
        json (str): The JSON string to save to the composition file.
        filepath (str, optional): The path to the directory that the composition file
        should be created in. Defaults to the COMP_PATH location stored in the config.

    Returns:
        bool: Whether execution was successful or not.
    """
    if filepath is None:
        filepath = cfg.COMP_PATH
    filepath = os.getcwd() + filepath
    t = localtime()
    fname = "{}-{:02d}-{:02d}--{:02d}.{:02d}.{:02d}.txt".format(
        t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec
    )
    full_path = filepath + fname
    try:
        if not os.path.isdir(filepath):
            os.makedirs(filepath)
        with open(full_path, "w+") as comp_file:
            comp_file.write(json)
        log(f"Saved composition in file {full_path}.")
        return True
    except OSError:
        print_error("Unable to open composition file to save the composition.")
        log(
            "Failed to save composition file due to errors in accessing and writing to the file."
        )
    return False

def disable_logging() -> None:
    """Sets the config to disable logging during program execution."""
    cfg.LOGS_ENABLED = False
    delete_log_file()


def set_seed(supplied_args: Iterable[str]) -> bool:
    """Sets the random seed to be used during program execution.

    Args:
        supplied_args (Iterable[str]): The list of arguments following this argument.

    Returns:
        (bool) Whether the supplied arguments were valid or not."""
    if len(supplied_args) <= 0:
        print_error(
            "Some integer seed must be supplied with the -s and --seed options. Use the -h or --help options to see usage information."
        )
        log("Failed to supply seed alongside seed option.")
        return False
    try:
        cfg.SEED = int(supplied_args[0])
        log(f"Set option to use random seed {cfg.SEED}")
    except:
        print_error(
            "Some integer seed must be supplied with the -s and --seed options. Use the -h or --help options to see usage information."
        )
        log("Failed to supply a valid integer seed alongside seed option.")
        return False


def suppress_errors() -> None:
    """Sets the config to suppress displaying of errors that may occur."""
    cfg.SUPPRESS_ERRORS = True
    log("Set option to suppress errors during execution.")


def display_progress() -> None:
    """Sets the config to display progress during obfuscation transformations."""
    cfg.DISPLAY_PROGRESS = True
    log("Set option to display obfuscation progress during transformation.")


def save_composition() -> None:
    """Sets the config to save the selected transformation composition to a JSON file when done."""
    cfg.SAVE_COMPOSITION = True
    log("Set option to save the final obfuscation transformation sequence.")


def load_composition(supplied_args: Iterable[str]) -> bool:
    """Sets the file to load initial obfuscation transformation information from.

    Args:
        supplied_args (Iterable[str]): The list of arguments following this argument.

    Returns:
        (bool) Whether the supplied arguments were valid or not."""
    if len(supplied_args) <= 0:
        print_error(
            "Some composition file must be supplied with the -l and --load options. Use the -h or --help options to see usage information."
        )
        log("Fail to supply composition file alongside composition load option.")
        return False
    cfg.COMPOSITION = supplied_args[0]
    log(
        f"Set option to load initial obfuscation transformation sequence from file {cfg.COMPOSITION}."
    )
    return True

def handle_arguments(supplied_args: Iterable[str], options) -> Iterable[str] | bool: 
    # TODO options input + documentation
    """This function iteratively handles a list of supplied arguments, filtering
    out actual arguments and handling the execution of different options supplied
    to the program, most of which are just changing some config setting to alter
    later program behaviour.

    Args:
        supplied_args (Iterable[str]): The list of args/options supplied to the program.

    Returns:
        Union[Iterable[str], bool]: The list of (just) arguments supplied to the program.
        If execution is to be stopped, instead just returns True or False to indicate
        a valid or failed execution respectively.
    """
    args = []
    skip_next = False
    for i, arg in enumerate(supplied_args):
        # Handle skipping for giving values with options
        if skip_next:
            skip_next = False
            continue
        matched = False
        for opt in options:
            if arg in opt[1]:
                res = opt[0]() if len(opt[3]) == 0 else opt[0](supplied_args[(i + 1) :])
                if res is not None and not res:
                    return False
                skip_next = len(opt[2]) != 0
                matched = True
                break
        if matched:
            continue
        if arg.startswith("-"):  # Handle unknown options
            print_error(
                f"Unknown option '{arg}' supplied. Use the -h or --help options to see usage information."
            )
            log(f"Unknown option {arg} supplied.")
            return False
        else:  # Store valid arguments
            args.append(arg)
    return args