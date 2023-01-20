""" File: cli.py
Implements functions to implement the command-line interface of the program,
such that it can be used through text interaction in a terminal window."""
import sys
from typing import Optional
from .debug import print_error, create_log_file, delete_log_file, log
from .interaction import CSource, menu_driven_option, save_composition as save_comp
from .obfuscation import *
from app import settings as config

def disable_logging() -> None:
    """Sets the config to disable logging during program execution."""
    config.LOGS_ENABLED = False
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
        config.SEED = int(supplied_args[0])
        log(f"Set option to use random seed {config.SEED}")
    except:
        print_error(
            "Some integer seed must be supplied with the -s and --seed options. Use the -h or --help options to see usage information."
        )
        log("Failed to supply a valid integer seed alongside seed option.")
        return False


def suppress_errors() -> None:
    """Sets the config to suppress displaying of errors that may occur."""
    config.SUPPRESS_ERRORS = True
    log("Set option to suppress errors during execution.")


def display_progress() -> None:
    """Sets the config to display progress during obfuscation transformations."""
    config.DISPLAY_PROGRESS = True
    log("Set option to display obfuscation progress during transformation.")


def save_composition() -> None:
    """Sets the config to save the selected transformation composition to a JSON file when done."""
    config.SAVE_COMPOSITION = True
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
    config.COMPOSITION = supplied_args[0]
    log(
        f"Set option to load initial obfuscation transformation sequence from file {config.COMPOSITION}."
    )
    return True


# The list of command line arguments/options supported by the command line interface.
options = [
    (
        None,  # Function to call if argument supplied
        ["-h", "--help"],  # Arguments that can be provided for this function
        "Displays this help menu.",  # A help menu description for this argument
        [],  # Names of proceeding values used by the function
    ),
    (
        disable_logging,
        ["-l", "--noLogs"],
        "Stops a log file being created for this execution.",
        [],
    ),
    (
        set_seed,
        ["-s", "--seed"],
        "Initialises the program with the random seed x (some integer).",
        ["x"],
    ),
    (
        suppress_errors,
        ["-S", "--supress-errors"],
        "Attempts to obfsucate in spite of errors (WARNING: MAY CAUSE UNEXPECTED BEHAVIOUR).",
        [],
    ),
    (
        display_progress,  # TODO implement progress display
        ["-p", "--progress"],
        "Outputs obfuscation pipleline progress (transformation completion) during obfuscation.",
        [],
    ),
    (
        save_composition,  # TODO add composition saving
        ["-c", "--save-comp"],
        "Saves the selected composition of obfuscation transformations as a JSON file to be reused.",
        [],
    ),
    (
        load_composition,  # TODO add composition loading
        ["-l", "--load-comp"],
        "Loads a given JSON file containing the composition of obfuscation transformations to use.",
        ["file"],
    ),
]


def help_menu() -> bool:
    """Prints the help menu detailing usage of the CLI command interface.

    Returns:
        (bool) Always returns False, to signal that program execution should stop."""
    help_str = """################ CLI Help Manual ################
This program takes as an argument some input C source program file and allows the application of a sequence of obfuscation transformations, resulting in an obfuscated C source file being produced. For more information on usage and options, see below.

Usage: python {} input_c_file [output_file] [options]

Options:\n""".format(
        __file__.split("\\")[-1]
    )
    opt_strings = [" ".join(opt[1] + opt[3]) for opt in options]
    max_len = max([len(opt_str) for opt_str in opt_strings])
    for i, option in enumerate(options):
        opt_str = opt_strings[i]
        help_str += (
            "    "
            + opt_str
            + (max_len - len(opt_str) + 1) * " "
            + "| "
            + option[2]
            + "\n"
        )
    print(help_str)
    log("Displayed the help menu.")
    return False


options[0] = (help_menu, *options[0][1:])


def get_transformations(
    source: CSource, seed: Optional[int] = None
) -> Optional[CSource]:
    """Given a source program to obfuscate, this program implements the CLI that allows
    users to select a sequence of obfuscation transformations to apply and obfuscates
    the program, returning the result.

    Args:
        source (CSource): The C source code program to obfuscate.
        seed (Optional[int], optional): The seed to use for randomness. Defaults to None.

    Returns:
        Optional[CSource]: If successful, returns the obfuscated C source code. If an
        error occurs or the user quits, returns None.
    """
    selected = []
    cursor_index = 0  # Cursor to allow traversal of transforms in CLI.

    # Generate available transforms from implemented classes
    available_transforms = ObfuscationUnit.__subclasses__()
    num_transforms = len(available_transforms)
    options = [f"{t.name}: {t.description}" for t in available_transforms]
    options += [
        "Move cursor left",
        "Move cursor right",
        "Remove transform after cursor",
        "Edit transform after cursor",
        "Finish selecting transforms and continue",
    ]

    # Iteratively get transform information until user selects to continue/quit.
    done_selecting = False
    while not done_selecting:
        # Format current transforms with cursor location for printing
        prompt = "\nCurrent transforms: {} >>> {}\n".format(
            " -> ".join(str(t) for t in selected[:cursor_index]),
            " -> ".join(str(t) for t in selected[cursor_index:]),
        )
        choice = menu_driven_option(options, prompt=prompt)
        if choice == -1:  # Quit
            log("Selected to exit the transformation selection menu.")
            return None
        elif choice < num_transforms:  # Selected transform
            new_t = available_transforms[choice].get_cli()
            if new_t is None:
                return None
            selected = selected[:cursor_index] + [new_t] + selected[cursor_index:]
            log(
                "Added transform {} at index {}. Current transforms: {}".format(
                    new_t.name, cursor_index, " -> ".join(str(t) for t in selected)
                )
            )
            cursor_index += 1
        elif choice == num_transforms:  # Move cursor left
            cursor_index = max(cursor_index - 1, 0)
        elif choice == num_transforms + 1:  # Move cursor right
            cursor_index = min(cursor_index + 1, len(selected))
        elif choice == num_transforms + 2:  # Delete transform after cursor
            selected = selected[:cursor_index] + selected[(cursor_index + 1) :]
        elif choice == num_transforms + 3:  # Edit transform after cursor
            if cursor_index < len(selected):
                selected[cursor_index].edit_cli()
        else:  # Finished selecting
            done_selecting = True

    # Apply selected transform pipeline to given source code
    pipeline = Pipeline(seed, *selected)
    if config.SAVE_COMPOSITION:
        save_comp(pipeline.to_json())
    obfuscated = pipeline.process(source)
    return obfuscated


def handle_arguments(supplied_args: Iterable[str]) -> Iterable[str] | bool:
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


def handle_CLI() -> bool:
    """Handles the command line interface for the program, parsing command arguments
    and options to determine which settings to apply and what other functionalities
    and to call. Behaviour changes depending on the value of sys.argv, which depends
    on the arguments supplied to the program when calling it.

    Returns:
        bool: Whether execution ended as expected or not (i.e. an error occurred).
    """
    supplied_args = sys.argv
    if len(supplied_args) != 0 and supplied_args[0].endswith(".py"):
        supplied_args = supplied_args[1:]

    # Setup logging information
    create_log_file()
    log(f"Began execution of CLI script.")
    log(f"Supplied arguments: {str(supplied_args)}")

    # Handle supplied arguments/options
    args = handle_arguments(supplied_args)
    if isinstance(args, bool):
        return args

    # Determine subsequent execution based on number of supplied arguments.
    if len(args) == 0:  # No arguments - error
        print_error(
            "No source file supplied. Use the -h or --help options to see usage information."
        )
        log("Aborting executions because no arguments were supplied.")
        return False

    # Read file and display parse errors
    source = CSource(args[0])
    if source.contents is None or not source.valid_parse:
        return False
    obfuscated = get_transformations(source, config.SEED)
    if obfuscated is None:
        return False

    # Handle obfuscation interface
    if len(args) == 1:  # 1 argument - take as input source file, and print output
        if obfuscated is not None:
            log("Displaying obfuscation output.")
            print(obfuscated.contents)
        log("Execution finished normally.")
        return True
    elif len(args) == 2:  # 2 arguments - input and output files
        try:
            log("Writing obfuscation output")
            with open(args[1], "w+") as write_file:
                write_file.write(obfuscated.contents)
            print("Obfuscation finished successfully.")
            log("Obfuscation written successfully.")
            log("Execution finished normally.")
            return True
        except Exception as e:
            print_error(f"Error creating output file '{args[1]}'")
            log(f"Error when writing output to file: {str(e)}")
    return False
