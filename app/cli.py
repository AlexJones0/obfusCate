""" File: cli.py
Implements functions to implement the command-line interface of the program,
such that it can be used through text interaction in a terminal window."""
from select import select
import sys
from typing import Optional, Union
from .debug import print_error, create_log_file, log
from .io import CSource, menu_driven_option
from .obfuscation import *
from app import settings as config


def help_menu() -> None:  # TODO change from 'python cli' to actual name
    """Prints the help menu detailing usage of the CLI command interface."""
    hstr = """################ CLI Help Manual ################
This program takes as an argument some input C source program file and allows the application of a sequence of obfuscation transformations, resulting in an obfuscated C source file being produced. For more information on usage and options, see below.

Usage: python cli input_c_file [output_file] [options]

Options:
    -h --help           | Displays this help menu.
    -l --noLogs         | Stops a log file being created for this execution.
    -s --seed x         | Initialises the program with the random seed x (some integer).
    -e --errors         | Displays parse errors/warnings generated by clang for invalid programs.
    -S --supress-errors | Attempts to obfuscate in spite of parsing errors (WARNING: MAY CAUSE UNEXPECTED BEHAVIOUR)
"""
    print(hstr)


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
    selected_transforms = []
    cursor_index = 0  # Cursor to allow traversal of transforms in CLI.

    # Generate available transforms from implemented classes
    available_transforms = ObfuscationUnit.__subclasses__()
    num_transforms = len(available_transforms)
    options = [f"{t.name}: {t.description}" for t in available_transforms]
    options.append("Move cursor left")
    options.append("Move cursor right")
    options.append("Remove transform after cursor")
    options.append("Edit transform after cursor")
    options.append("Finish selecting transforms and continue")

    # Iteratively get transform info until user selects to continue/quit.
    done_selecting = False
    while not done_selecting:
        # Format current transforms with cursor location for printing
        prompt = "\nCurrent transforms: {} >>> {}\n".format(
            " -> ".join(str(t) for t in selected_transforms[:cursor_index]),
            ""
            if cursor_index == len(selected_transforms)
            else (" -> ".join(str(t) for t in selected_transforms[cursor_index:])),
        )
        choice = menu_driven_option(options, prompt=prompt)
        if choice == -1:  # Quit
            return None
        elif choice < num_transforms:  # Add a transform
            new_transform = available_transforms[choice].get_cli()
            if new_transform is None:
                return None
            selected_transforms.append(new_transform)
            cursor_index += 1  # Move cursor 1 right with new transform
        elif choice == num_transforms:  # Move cursor left
            cursor_index = max(cursor_index - 1, 0)
        elif choice == num_transforms + 1:  # Move cursor right
            cursor_index = min(cursor_index + 1, len(selected_transforms))
        elif choice == num_transforms + 2:  # Delete transform after cursor
            selected_transforms = (
                selected_transforms[:cursor_index]
                + selected_transforms[(cursor_index + 1) :]
            )
        elif choice == num_transforms + 3:  # Edit transform after cursor
            if cursor_index < len(selected_transforms):
                selected_transforms[cursor_index].edit_cli()
        else:  # Finished selecting
            done_selecting = True

    # Apply selected transform pipeline to given source code
    obfuscated = Pipeline(seed, *selected_transforms).process(source)
    return obfuscated


def check_source_errors(source: CSource) -> bool:
    """ Handles parse errors found with the input source file, displaying these errors and 
    choosing to terminate execution (or suppressing the errors) depending on settings supplied
    to the program. """
    if source.contents is None or source.t_unit is None:
        return False
    if len(source.parse_errors) > 0:
        if config.DISPLAY_ERRORS:
            print("PARSE ERRORS:")
            print("\n".join("  " + e for e in source.parse_errors))
        if config.SUPPRESS_ERRORS:
            print(f"Encountered {len(source.parse_errors)} errors/warnings whilst parsing but trying to continue anyway...\n")
        else:
            print(f"Encountered {len(source.parse_errors)} errors/warnings whilst parsing, so stopping execution.")
            return False
    return True


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
    skipNext = False
    for i, arg in enumerate(supplied_args):
        # Handle skipping for giving values with options
        if skipNext:
            skipNext = False
            continue
        match arg:
            case "-h" | "--help" | "--man" | "--manual":  
                # View help
                help_menu()
                return True
            case "-l" | "--noLogs":  
                # Disable logging
                config.LOGS_ENABLED = False
            case "-s" | "--seed":  
                # Set seed for randomness
                skipNext = True
                if len(supplied_args) <= i:
                    print_error(
                        "Some integer seed must be supplied with the -s and --seed options. Use the -h or --help options to see usage information."
                    )
                    return False
                try:
                    config.SEED = int(supplied_args[i + 1])
                except:
                    print_error(
                        "Some integer seed must be supplied with the -s and --seed options. Use the -h or --help options to see usage information."
                    )
                    return False
            case "-e" | "--errors": 
                # Display errors on invalid parse
                config.DISPLAY_ERRORS = True
            case "-S" | "--supress-errors": 
                # Supress errors and try to obfuscate anyway
                config.SUPPRESS_ERRORS = True
            case _:
                if arg.startswith("-"):  # Handle unknown options
                    print_error(
                        f"Unknown option '{arg}' supplied. Use the -h or --help options to see usage information."
                    )
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
        # Handle execution as python script rather than binary # TODO CHANGE?
        supplied_args = supplied_args[1:]

    # Setup logging information
    create_log_file()
    log(f"Began execution of CLI script.")
    log(f"Supplied arguments: {str(supplied_args)}")
    
    args = handle_arguments(supplied_args)
    if (isinstance(args, bool)):
        return args

    # Determine subsequent execution based on number of supplied arguments.
    if len(args) == 0:  # No arguments - error
        print_error(
            "No source file was supplied. Use the -h or --help options to see usage information."
        )
        log("Aborting executions because no arguments were supplied.")
        return False

    # Read file and display parse errors
    source = CSource(args[0])
    if not check_source_errors(source):
        return False
    obfuscated = get_transformations(source, config.SEED)
    
    # Handle obfuscation interface
    if len(args) == 1:  # 1 argument - take as input source file, and print output
        if obfuscated is not None:
            print(obfuscated.contents)
        return True
    elif len(args) == 2:  # 2 arguments - input and output files
        try:
            with open(args[1], "w+") as write_file:
                write_file.write(obfuscated.contents)
            print("Obfuscation finished successfully.")
            return True
        except:
            print_error(f"Error creating output file '{args[1]}'")
    return False
