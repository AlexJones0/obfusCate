""" File: cli.py
Implements functions to implement the command-line interface of the program,
such that it can be used through text interaction in a terminal window."""
import sys
import unicodedata
from typing import Optional
from .debug import print_error, create_log_file, log
from .interaction import (
    CSource,
    menu_driven_option,
    handle_arguments,
    disable_logging,
    set_seed,
    suppress_errors,
    display_progress,
    save_composition,
    load_composition,
    save_composition_file,
    load_composition_file,
    disable_metrics,
    display_version,
)
from .obfuscation import *
from .complexity import *
from app import settings as config
from unidecode import unidecode


def skip_menus():
    config.SKIP_MENUS = True
    log("Set option to skip menus in the CLI and obfuscate instantly.")


# The list of command line arguments/options supported by the command line interface.
options = [
    (
        None,  # Function to call if argument supplied
        ["-h", "--help"],  # Arguments that can be provided for this function
        "Displays this help menu.",  # A help menu description for this argument
        [],  # Names of proceeding values used by the function
    ),
    (
        display_version,
        ["-v", "--version"],
        "Displays the program's name and current version.",
        [],
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
        display_progress,
        ["-p", "--progress"],
        "Outputs obfuscation pipleline progress (transformation completion) during obfuscation.",
        [],
    ),
    (
        save_composition,
        ["-c", "--save-comp"],
        "Saves the selected composition of obfuscation transformations as a JSON file to be reused.",
        [],
    ),
    (
        load_composition,
        ["-l", "--load-comp"],
        "Loads a given JSON file containing the composition of obfuscation transformations to use.",
        ["file"],
    ),
    (
        disable_metrics,
        ["-m", "--no-metrics"],
        "Disables calculation of code complexity metrics for the obfuscated programs.",
        [],
    ),
    (
        skip_menus,
        ["-s", "--skip"],
        "Skips the menus, immediately executing using any loaded composition file.",
        [],
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
            + option[2].split("\n")[0]
            + ("\n" if "\n" in option[2] else "")
            + "\n".join(
                [
                    (5 + max_len) * " " + "| " + line
                    for line in option[2].split("\n")[1:]
                ]
            )
            + "\n"
        )
    print(help_str)
    log("Displayed the help menu.")
    return False


options[0] = (help_menu, *options[0][1:])


def display_complexity_metrics(source: CSource, obfuscated: CSource) -> None:
    if source is None or obfuscated is None:
        return
    metrics = CodeMetricUnit.__subclasses__()
    print("\n===Obfuscation Metrics===")
    while len(metrics) != 0:
        processed = []
        vals_to_print = []
        max_global = 0
        for metric in metrics:
            missing_preds = [
                req
                for req in metric.predecessors
                if req in metrics and req not in processed
            ]
            if len(missing_preds) > 0:
                continue
            processed.append(metric)
            metric_unit = metric()
            metric_unit.calculate_metrics(source, obfuscated)
            metric_vals = metric_unit.get_metrics()
            max_local = max(
                [
                    len(unidecode(m[0]))
                    + (
                        len(m[1])
                        if not isinstance(m[1], tuple)
                        else len(m[1][0]) + len(m[1][1]) + 3
                    )
                    for m in metric_vals
                ]
            )
            max_global = max(max_local, max_global)
            vals_to_print.append((metric.name, metric_vals))
        for metric_name, metric_vals in vals_to_print:
            print(f"\n{metric_name}:")
            for name, m_val in metric_vals:
                if isinstance(m_val, tuple):
                    values = f"{m_val[0]} ({m_val[1]})"
                else:
                    values = m_val
                padding = " " * (max_global - len(unidecode(name)) - len(values))
                print(f"  {name}:        {padding}{values}")
        if len(processed) == 0:
            log(
                "Metrics {} have unsatisfiable predecessor dependencies!".format(
                    metrics
                )
            )
            return
        for metric in processed:
            metrics.remove(metric)
    print("")


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
    if config.COMPOSITION is None:
        selected = []
        cursor_index = 0  # Cursor to allow traversal of transforms in CLI.
    else:
        contents = load_composition_file(config.COMPOSITION)
        if contents is None:
            log(
                "Error loading saved transformations - please provide a valid compositions file",
                print_err=True,
            )
            return None
        saved_pipeline = Pipeline.from_json(contents, use_gui=False)
        if saved_pipeline is None:
            log(
                "Error loading saved transformations - please provide a valid compositions file",
                print_err=True,
            )
            return None
        if config.SEED is None:  # Only use saved seed if no seed was provided
            config.SEED = saved_pipeline.seed
        selected = saved_pipeline.transforms
        cursor_index = len(selected)

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
    done_selecting = config.SKIP_MENUS
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
        save_composition_file(pipeline.to_json())
    original = deepcopy(source)
    obfuscated = pipeline.process(source)

    # Calculate and display complexity metrics
    if config.CALCULATE_COMPLEXITY:
        display_complexity_metrics(original, obfuscated)

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
        supplied_args = supplied_args[1:]

    # Setup logging information
    create_log_file()
    log(f"Began execution of CLI script.")
    log(f"Supplied arguments: {str(supplied_args)}")

    # Handle supplied arguments/options
    args = handle_arguments(supplied_args, options)
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
            print("\n===Obfuscated Output===\n")
            print(obfuscated.contents)
        log("Execution finished normally.")
        return True
    elif len(args) == 2:  # 2 arguments - input and output files
        try:
            log("Writing obfuscation output")
            with open(args[1], "w+") as write_file:
                write_file.write(obfuscated.contents)
            print("Obfuscation written successfully.")
            log("Obfuscation written successfully.")
            log("Execution finished normally.")
            return True
        except Exception as e:
            print_error(f"Error creating output file '{args[1]}'")
            log(f"Error when writing output to file: {str(e)}")
    return False
