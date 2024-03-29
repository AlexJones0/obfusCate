""" File: interaction.py
Implements classes and functions for handling input and output, including
processing and writing of C source files as well as utilities for handling
system options (command-line arguments).
"""
from .debug import print_error, log, delete_log_file, logprint
from app import settings as cfg
from pycparser import parse_file as pycparse_file, c_generator, c_ast, c_parser, c_lexer
from pycparser.c_ast import FileAST
from typing import Iterable, Tuple, Callable
import os, time, enum


class PatchedParser(c_parser.CParser):
    """ Patches the behaviour of pycparser's CParser class to correctly parse 
    labels and gotos. By default, pycparser makes the assumption that it can 
    split identifier tokens into regular identifiers ('ID') and type identifiers
    ('TYPEID') based on whether a token is a defined type in the current scope
    or not. Labels/Gotos are then defined to only be of the form:
    
        labeled_stmt   : ID COLON pragmacomp_or_statement | ...
        jump_statement : GOTO ID SEMI | ...       
        
    This ignores the C name space rules [1], which states that we have four key name
    spaces - one for labels, one for tags (enums, structs, unions), one for
    members of unions & structs, and finally one for all other identifiers, colloquially
    referred to as 'ordinary identifiers'. Hence the current grammar fails in the case 
    where a type with the same name as the label has already been defined (by a typedef). 
    This should compile, as the name spaces are separate, but pycparser does not recognise 
    this. 
    
    Rather than alter the entire grammar/lexer to incorporate namespaces properly,
    a quick partchwork fix is made in this class to allow type idenftifiers 
    ('TYPEID') to be used as label names, such that even if an identifier 
    corresponds to an existing type it can be used as a label. So we now have:
    
        labeled_stmt   : ID COLON pragmacomp_or_statement 
                       | TYPEID COLON pragmacomp_or_statement | ...
        jump_statement : GOTO ID SEMI 
                       | GOTO TYPEID SEMI | ...
        
    Yacc optimisation is enabled but the yacc table is specified as a module
    local to the project, and thus the first time a PatchedParser() is created
    on the system some small slowdown will occur (a few seconds at most) to 
    generate this yacc table for the first time. After this, the lexer/parser
    will operate at full speed, however. 
    
    [1] See the C99 standards section 6.2.3 on the name spaces of identifiers
    (pages 31) - which details these name spaces and how they are disambiguated.
    https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1256.pdf
    """
    
    def __init__(self) -> None:
        super(PatchedParser, self).__init__(
            lex_optimize=True,
            lexer=c_lexer.CLexer,
            lextab="pycparser.lextab",
            yacc_optimize=True,
            yacctab="yacctab",
            yacc_debug=False,
            taboutputdir="",
        )

    def p_labeled_statement_1(self, p):
        """labeled_statement : TYPEID COLON pragmacomp_or_statement
                             | ID COLON pragmacomp_or_statement """
        p[0] = c_ast.Label(p[1], p[3], self._token_coord(p, 1))
        
    def p_jump_statement_1(self, p):
        """ jump_statement  : GOTO ID SEMI 
                            | GOTO TYPEID SEMI """
        p[0] = c_ast.Goto(p[2], self._token_coord(p, 1))


class PatchedGenerator(c_generator.CGenerator):
    """ A subclass that patches the behaviour of pycparser's default
    CGenerator, fixing an issue where it occassionally forgets to
    follow a compound literal expression statement with a semi-colon
    (e.g. if the next statement is a label to a null statement at
    the end of the function body). This causes incorrect generation,
    and so this patch is required to generate valid C code. """

    def _generate_stmt(self, n, add_indent=False):
        """ The original CGenerator appears to forget that 
        CompoundLiterals can appear in an expression context and so do not
        have automatic semi-colons added, so we just detect this case and
        add the missing semi-colon here for correct generation. """
        val = super(PatchedGenerator, self)._generate_stmt(n, add_indent)
        if type(n) == c_ast.CompoundLiteral:
            return val[:-1] + ';\n'
        return val


class CSource:
    """A class representing a C source code program, storing its file path,
    contents in string form, and contents as a Clang-parsed translation
    unit (in Abstract Syntax Tree format)."""

    def __init__(
        self, filepath: str, contents: str | None = None, t_unit: FileAST | None = None
    ) -> None:
        """Constructor for a CSource object.

        Args:
            filepath (str): The path to the C file.
            contents (str | None, optional): The contents of the file. Defaults to
            None, in which case the file path is opened and read to retrieve contents.
            t_unit (FileAST | None, optional): The translation unit of the file
            after it is preprocessed by clang and parsed by pycparser. Defaults to None,
            in which case it is retrieved by parsing the loaded contents.
        """
        self.fpath = filepath
        if contents is None:
            self.contents = self.__read_file()
        else:
            self.contents = contents
        self.t_unit = None
        if self.contents is None:
            return
        if t_unit is None:
            log(f"Parsing AST for file {self.fpath}")
            self.__parse_file(self.fpath)
        else:
            self.t_unit = t_unit
        self.error_context = None

    def __read_file(self) -> str | None:
        """Reads the file contents from the stored C file path.

        Returns:
            str | None: The string contents of the file, or None if some error occurs.
        """
        if not self.fpath.endswith(".c"):
            print_error(f"Supplied file {self.fpath} is not a .c file!")
            return None
        log(f"Started reading contents from source file with path {self.fpath}")
        try:
            with open(self.fpath, "r") as source_file:
                contents = source_file.read()
            return contents
        except OSError as e:
            log(f"Error in opening source file: {str(e)}.")
        return None

    def __parse_file(self, filepath: str) -> None:
        """Preprocesses and parses the file at the provided filepath, updating
        the CSource's translation unit with the result.

        Args:
            filepath (str): The filepath of the file to be parsed.
        """
        try:
            parser = PatchedParser() if cfg.USE_PATCHED_PARSER else None
            t_unit = pycparse_file(
                filepath,
                use_cpp=True,
                cpp_path="clang",
                cpp_args=["-E", r"-Iutils/fake_libc_include"],
                parser=parser
            )
            fname = filepath.split("\\")[-1]
            t_unit.ext = [x for x in t_unit.ext if fname in x.coord.file]
            self.t_unit = t_unit
            self.error_context = None
        except Exception as e:
            self.error_context = str(e).replace(".\\\\obfuscate_temp.c:", "")
            log(f"Unexpected error whilst parsing the program: {str(e)}.")
            self.t_unit = None

    def update_t_unit(self) -> None:
        """Updates the translation unit (parsed AST) of the CSource without
        reading from a file path (used when the contents no longer match up
        with the file). Does this by writing to a temporary file for
        preprocessing via clang, and then removing this aftwards."""
        if cfg.TEMP_FILE_PATH is None or cfg.TEMP_FILE_PATH == "":
            return
        try:
            with open(cfg.TEMP_FILE_PATH, "w+") as f:
                f.write(self.contents)
            self.__parse_file(cfg.TEMP_FILE_PATH)
            os.remove(cfg.TEMP_FILE_PATH)
        except OSError as e:
            log(f"Unexpected OS error whilst interacting with temp file: {str(e)}.")
            print_error(f"An unknown error occurred whilst updating the AST.")
            return

    def copy(self) -> "CSource":
        """Creates a copy of the code CSource, producing a separate translation unit.

        Returns:
            CSource: A copy of the CSource with a distinct, identical translation unit.
        """
        log(f"Creating copy of source: {self.fpath}.")
        return CSource(self.fpath, self.contents)

    @property
    def valid_parse(self) -> bool:
        """This boolean property describes whether a valid parse has been performed on
        the C source file or not."""
        return self.t_unit is not None


class SystemOpt:
    """A class that encapsulates information about an available system option (provided
    as a command-line argument when calling the script)."""

    def __init__(
        self,
        func: Callable,
        names: Iterable[str],
        desc: str,
        param_names: Iterable[str],
    ) -> None:
        """Constructor for the SystemOpt object.

        Args:
            func (Callable): The function that will be called if the option is present.
            names (Iterable[str]): The names (synonyms) that can be provided as the option.
            desc (str): The help menu description for the option, describing its behaviour.
            param_names (Iterable[str]): The names of any parameters that must be supplied
            alongside the option, which will be passed to the called function.
        """
        self.func = func
        self.names = names
        self.desc = desc
        self.param_names = param_names

    def get_desc_str(self, padding: int) -> str:
        """Retrieve a formatted description for the object for display in the help menu,
        appropriately padded for clean formatting.

        Args:
            padding (int): The amount of space padding to add before the line separator
            on new lines.

        Returns:
            str: The formatted help menu description string for the option.
        """
        if "\n" not in self.desc:
            return self.desc
        lines = self.desc.split("\n")
        padded_lines = [padding * " " + "| " + l for l in lines[1:]]
        return "\n".join([lines[0]] + padded_lines)

    def __str__(self) -> str:
        """Gets the string representation of the option, combining its names and
        any parameter names.

        Returns:
            str: The string representing the option usage "name param1 param2" etc.
        """
        return " ".join(self.names + self.param_names)


def menu_driven_option(
    options: Iterable[str | Tuple[str, Iterable[str]]], prompt: str | None = None
) -> int:
    """Performs command-line interface input handling for a generic menu where a
    restricted integer input must be made to select one of many options.

    Args:
        options (Iterable[str | Tuple[str, Iterable[str]]]): The list of options to
        select from. Each option can either be a string, or a tuple like
        (string, [str1, str2, str3, ...]) where string is the option text and
        [str1, str2, str3, ...] are optional strings that the CLI should understand.
        prompt (str | None, optional): An additional prompt text to display to the
        user after the printing of options but before requesting input. Defaults to None.

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
    choice = ""
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
                log(f"Valid choice {choice} in menu with {options} and {prompt}.")
                valid_input = True
            else:
                log(f"Invalid choice {choice} in menu with {options} and {prompt}.")
                print(
                    "Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.\n >",
                    end="",
                )
        except:  # Handle non-integer (and non-keyword) inputs
            log(f"Invalid choice {choice} in menu with {options} and {prompt}.")
            print(
                "Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.\n >",
                end="",
            )
    return choice - 1


def get_float(
    lower_bound: float | None = None, upper_bound: float | None = None
) -> float:
    """Gets an input float from the user, applying appropriate boundary
    checks if either bound is specified. Returns NaN if the user quits the
    input selection, and a valid float otherwise.

    Args:
        lower_bound (float | None, optional): The lower bound. Defaults to None.
        upper_bound (float | None, optional): The upper bound. Defaults to None.

    Returns:
        float: The user input float. NaN if the user chose to quit.
    """
    while True:
        user_input = input("\n>").lower().strip()
        if user_input in ["q", "quit", "exit", "leave", "x"]:
            return float("nan")  # Check for quit inputs
        try:
            user_input = float(user_input)
        except:
            print("Invalid input for a decimal number. Please try again...")
            continue
        if lower_bound is not None and user_input < lower_bound:
            print(
                f"Input {user_input} is too small. The value must be at least {lower_bound}."
            )
            log(f"User input {user_input} smaller than lower bound {lower_bound}.")
            continue
        if upper_bound is not None and user_input > upper_bound:
            print(
                f"Input {user_input} is too large. The value must be at most {upper_bound}."
            )
            log(f"User input {user_input} larger than upper bound {lower_bound}.")
            continue
        return user_input


def get_int(
    lower_bound: int | None = None, upper_bound: int | None = None
) -> int | None:
    """Gets an input integer from the user, applying appropriate
    boundary checks if either bound is specified.

    Args:
        lower_bound (int | None, optional): The lower bound. Defaults to None.
        upper_bound (int | None, optional): The upper bound. Defaults to None.

    Returns:
        int | None: None if the user quits the selection, or a valid
        integer in the specified range otherwise.
    """
    while True:
        user_input = input("\n>").lower().strip()
        if user_input in ["q", "quit", "exit", "leave", "x"]:
            return None  # Check for quit inputs
        try:
            user_input = int(user_input)
        except:
            print("Invalid input for an integer. Please try again...")
            continue
        if lower_bound is not None and user_input < lower_bound:
            print(
                f"Input {user_input} is too small. The value must be at least {lower_bound}."
            )
            log(f"User input {user_input} smaller than lower bound {lower_bound}.")
            continue
        if upper_bound is not None and user_input > upper_bound:
            print(
                f"Input {user_input} is too large. The value must be at most {upper_bound}."
            )
            log(f"User input {user_input} larger than upper bound {lower_bound}.")
            continue
        return user_input


def cli_enum_select(
    enum_: enum.Enum,
    init: Iterable[enum.Enum] | None,
    type_name: str,
    action_name: str,
    custom_prompt: str | None = None,
) -> list[enum.Enum] | None:
    """This function creates an iterative selection context from a given enum,
    allowing any combination of that enum's values to be selected by the user
    in a command-line interface and returned.

    Args:
        enum_ (enum.Enum): The enumerator to retrieve the available choices from.
        The enumerator values (.value) are the presented option strings.
        init (Iterable[enum.Enum] | None): The initial set of enumerator values
        to start with selected. None here is equivalent to `[]`.
        type_name (str): The name of what is being selected, e.g. "styles".
        action_name (str): The name of what you are doing with the selection,
        e.g. "opaque predicate insertion".
        custom_prompt (str | None, optional): A custom prompt to use instead
        of the default generated from the given `type_name` and `action_name`.
        Defaults to None, in which case the generated prompt is used.

    Returns:
        list[enum.Enum] | None: The list of selected enumerator values, or
        None if the user chose to quit the selection.
    """
    available = [s for s in enum_]
    chosen = [] if init is None else list(init)
    choice = 0
    while choice < len(enum_) or len(chosen) == 0:
        options = [("[X] " if s in chosen else "[ ] ") + s.value for s in enum_]
        options.append(f"Finish selecting {type_name}.")
        if custom_prompt is None:
            prompt = (
                "\nChoose which {} to enable for {}, or choose to finish.\n".format(
                    type_name, action_name
                )
            )
        else:
            prompt = custom_prompt
        choice = menu_driven_option(options, prompt)
        if choice == -1:
            return None
        elif choice < len(enum_):
            enumerator_val = enum_(available[choice])
            if enumerator_val in chosen:
                chosen.remove(enumerator_val)
            else:
                chosen.append(enumerator_val)
        elif len(chosen) == 0:
            print(
                "No valid options are currently selected. Please select at least one option.\n"
            )
    return chosen


def save_composition_file(json: str, filepath: str | None = None) -> bool:
    """Creates a composition file and saves the JSON string representing the
    composition to it.

    Args:
        json (str): The JSON string to save to the composition file.
        filepath (str | None, optional): The path to the directory that the
        composition file should be created in. Defaults to the COMP_PATH
        location stored in the config.

    Returns:
        bool: Whether execution was successful or not.
    """
    if filepath is None:
        filepath = cfg.COMP_PATH
    filepath = os.path.join(os.getcwd(), filepath)
    t = time.localtime()
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
        logprint("Unable to open composition file to save the composition.")
    return False


def load_composition_file(filepath: str | None = None) -> str | None:
    """Attempts to load the composition file from the specified
    composition file path.

    Args:
        filepath (str | None, optional): The filepath to read the
        composition file from. Defaults to None, in which case the
        the filepath saved in config is used.

    Returns:
        str | None: The composition file path contents, or None if
        an error ocurred, or if both the input filepath and config's
        composition file path are None.
    """
    if filepath is None:
        filepath = cfg.COMPOSITION
        if filepath is None:
            return None
    try:
        with open(os.path.join(os.getcwd(), filepath), "r") as comp_file:
            contents = comp_file.read()
        return contents
    except OSError as e:
        print_error("Unable to open composition file to load the composition.")
        log(
            f"Failed to load composition file {filepath} due to errors in accessing and reading from the file."
        )
    return None


def disable_logging() -> None:
    """Sets the config to disable logging during program execution."""
    cfg.LOGS_ENABLED = False
    delete_log_file()


def set_seed(supplied_args: Iterable[str]) -> bool:
    """Sets the random seed to be used during program execution.

    Args:
        supplied_args (Iterable[str]): The list of arguments following this argument.

    Returns:
        bool: Whether the supplied arguments were valid or not.
    """
    if len(supplied_args) <= 0:
        print_error(
            "Some integer seed must be supplied with the -s and --seed options. Use the -h or --help options to see usage information."
        )
        log("Failed to supply seed alongside seed option.")
        return False
    try:
        cfg.SEED = int(supplied_args[0])
        log(f"Set option to use random seed {cfg.SEED}")
        return True
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
    """Sets the config to save the selected transformation composition
    to a JSON file when done."""
    cfg.SAVE_COMPOSITION = True
    log("Set option to save the final obfuscation transformation sequence.")


def disable_metrics() -> None:
    """Sets the config to disable calculation, processing and displaying
    of code complexity metrics for the obfuscation."""
    cfg.CALCULATE_COMPLEXITY = False
    log("Set option to disable complexity calculations during execution.")


def display_version() -> bool:
    """Prints the program name and version to standard output, halting execution.

    Returns:
        bool: Returns False, to signal that execution should stop.
    """
    print(cfg.NAME, cfg.VERSION)
    log("Retrieved and displayed name and version information for the software.")
    return False


def disable_alloca() -> None:
    """Sets the config to disable use of `alloca()` calls to replace
    variable length arrays in control flow flattening."""
    cfg.USE_ALLOCA = False
    log("Set option to disable alloca use by CFF in replacing VLAs.")


def disable_patched_parser() -> None:
    """Sets the config to disable the use of the custom PatchedParser() class
    and instead makes the program use pycparcer's default CParser instead. """
    cfg.USE_PATCHED_PARSER = False
    log("Set opion to disabled patched parser use (now using pycparser default).")


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


def handle_arguments(
    supplied_args: Iterable[str], options: Iterable[SystemOpt]
) -> Iterable[str] | bool:
    """This function iteratively handles a list of supplied arguments, filtering
    out actual arguments and handling the execution of different options supplied
    to the program.

    Args:
        supplied_args (Iterable[str]): The list of args supplied to the program.
        options (Iterable[SystemOpt]): The list of supported options.

    Returns:
        Iterable[str] | bool: The list of arguments supplied to the program. If
        execution is to be stopped, instead just returns False to indicate that
        execution should stop.
    """
    args = []
    skip_num = 0
    for i, arg in enumerate(supplied_args):
        if skip_num > 0:
            skip_num -= 1
            continue
        # Find matching option (if one exists)
        found_match = False
        for opt in options:
            if arg in opt.names:
                if len(opt.param_names) == 0:
                    res = opt.func()
                else:
                    res = opt.func(supplied_args[(i + 1) :])
                if res is not None and not res:
                    return False
                skip_num = len(opt.param_names)
                found_match = True
                break
        if found_match:
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


# Defines a list of common shared system options used by both the CLI and GUI
shared_options = [
    SystemOpt(None, ["-h", "--help"], "Displays this help menu.", []),
    SystemOpt(
        display_version,
        ["-v", "--version"],
        "Displays the program's name and current version.",
        [],
    ),
    SystemOpt(
        disable_logging,
        ["-L", "--noLogs"],
        "Stops a log file being created for this execution.",
        [],
    ),
    SystemOpt(
        set_seed,
        ["-S", "--seed"],
        "Initialises the program with the random seed x (some integer).",
        ["x"],
    ),
    SystemOpt(
        display_progress,
        ["-p", "--progress"],
        "Outputs obfuscation pipleline progress (transformation completion) during obfuscation.",
        [],
    ),
    SystemOpt(
        save_composition,
        ["-c", "--save-comp"],
        "Saves the selected composition of obfuscation transformations as a JSON file to be reused.",
        [],
    ),
    SystemOpt(
        load_composition,
        ["-l", "--load-comp"],
        "Loads a given JSON file containing the composition of obfuscation transformations to use.",
        ["file"],
    ),
    SystemOpt(
        disable_metrics,
        ["-m", "--no-metrics"],
        "Disables calculation of code complexity metrics for the obfuscated programs.",
        [],
    ),
    SystemOpt(
        disable_alloca,
        ["-a", "--no-alloca"],
        "Disables use of alloca() to replace Variable Length Arrays (VLA) in the program whilst\n"
        "  control flow flattening, as this is not defined in the C standard and may not be\n"
        "  available in all systems (though it is in most). ",
        [],
    ),
    SystemOpt(
        disable_patched_parser,
        ["-u", "--unpatch-parser"],
        "Unpatches the parser/lexer/grammar used by yacc, such that the default pycparser CParser\n"
        "  class yacctable.py is used. Disabling the patch will mean you cannot use labels with\n"
        "  the same name as defined types, but may fix any unknown issues that arise due to patching. ",
        []
    )
]


def set_help_menu(func: Callable) -> None:
    """Sets the help menu system option ('-h', '--help') function.

    Args:
        func (Callable): The no-argument function that prints the help menu.
    """
    shared_options[0].func = func
