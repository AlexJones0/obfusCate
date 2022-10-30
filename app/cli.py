""" File: cli.py
Implements functions to implement the command-line interface of the program,
such that it can be used through text interaction in a terminal window."""
from select import select
import sys
from typing import Optional
from .debug import print_error, create_log_file, log
from .io import CSource, menu_driven_option
from .obfuscation import *
from app import settings as cfg


def help_menu() -> None:  # TODO change from 'python cli' to actual name
    """Prints the help menu detailing usage of the CLI command interface."""
    hstr = """################ CLI Help Manual ################
This program takes as an argument some input C source program file and allows the application of a sequence of obfuscation transformations, resulting in an obfuscated C source file being produced. For more information on usage and options, see below.

Usage: python cli input_c_file [output_file] [options]

Options:
    -h --help       | Displays this help menu.
    -l --noLogs     | Stops a log file being created for this execution.
    -s --seed x     | Initialises the program with the random seed x (some integer).
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
        else:  # Finished selecting
            done_selecting = True

    # Apply selected transform pipeline to given source code
    obfuscated = Pipeline(seed, *selected_transforms).process(source)
    return obfuscated


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

    # Iteratively handle arguments/options
    args = []
    seed = None
    skipNext = False
    for i, arg in enumerate(supplied_args):
        if skipNext:
            skipNext = False
            continue
        match arg:
            case "-h" | "--help" | "--man" | "--manual":  # View help option
                help_menu()
                return True
            case "-l" | "--noLogs":  # Disable logging option
                cfg.LOGS_ENABLED = False
            case "-s" | "--seed":  # Set random seed option
                skipNext = True
                if len(supplied_args) <= i:
                    print_error(
                        "Some integer seed must be supplied with the -s and --seed options. Use the -h or --help options to see usage information."
                    )
                    return False
                try:
                    seed = int(supplied_args[i + 1])
                except:
                    print_error(
                        "Some integer seed must be supplied with the -s and --seed options. Use the -h or --help options to see usage information."
                    )
                    return False
            case _:
                if arg.startswith("-"):  # Handle unknown options
                    print_error(
                        f"Unknown option '{arg}' supplied. Use the -h or --help options to see usage information."
                    )
                    return False
                else:  # Store valid arguments
                    args.append(arg)

    # Setup logging information
    create_log_file()
    log(f"Began execution of CLI script.")
    log(f"Supplied arguments: {str(supplied_args)}")

    # Determine subsequent execution based on number of supplied arguments.
    if len(args) == 0:  # No arguments - error
        print_error(
            "No source file was supplied. Use the -h or --help options to see usage information."
        )
        log("Aborting executions because no arguments were supplied.")
    elif len(args) == 1:  # 1 argument - take as input source file, and print output
        source = CSource(args[0])
        obfuscated = get_transformations(source, seed)
        if obfuscated is not None:
            print(obfuscated.contents)
        return True
    elif len(args) == 2:  # 2 arguments - input and output files
        source = CSource(args[0])
        obfuscated = get_transformations(source, seed)
        try:
            with open(args[1], "w+") as write_file:
                write_file.write(obfuscated.contents)
            print("Obfuscation finished successfully.")
            return True
        except:
            print_error(f"Error creating output file '{args[1]}'")
    return False
