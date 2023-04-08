""" File: cli.py
Implements functions and logic for providing the command-line interface of the program,
such that it can be used through text interaction in a terminal window as either a 
menu-driven CLI, or as a traditional single command GUI with use of appropriate options
providing a JSON file. Handles the overall general CLI interaction / control flow, as well
as CLI system arguments and options.
"""
from . import interaction, complexity, obfuscation as obfs
from .debug import print_error, create_log_file, log, logprint
from .obfuscation import cli as obfs_cli
from app import settings as config
from typing import Iterable, Type, Tuple
import sys, copy, unidecode


def skip_menus() -> None:
    """Sets the config option to skip through all menus during execution."""
    config.SKIP_MENUS = True
    log("Set option to skip menus in the CLI and obfuscate instantly.")


# Add the command-line specific '--skip' option to the list of system options.
interaction.shared_options.append(
    interaction.SystemOpt(
        skip_menus,
        ["-s", "--skip"],
        "Skips the menus, immediately executing using any loaded composition file.",
        [],
    )
)


def help_menu() -> bool:
    """Prints the help menu detailing usage of the CLI command interface.

    Returns:
        bool: Always returns False, to signal that execution should stop."""
    help_str = (
        "################ CLI Help Manual ################\n"
        "This program takes as an argument some input C source program file and allows\n"
        "the application of a sequence of obfuscation transformations, resulting in an\n"
        "obfuscated C source file being produced. For more information on usage and   \n"
        "options, see below.\n\n"
        "Usage: python {} input_c_file [output_file] [options]\n\n"
        "Options:\n"
    ).format(__file__.split("\\")[-1].split("/")[-1])
    max_len = max([len(str(opt)) for opt in interaction.shared_options])
    for option in interaction.shared_options:
        option_str = str(option)
        padding = (max_len - len(option_str) + 1) * " "
        desc_str = option.get_desc_str(5 + max_len)
        help_str += f"    {option_str}{padding}| {desc_str}\n"
    print(help_str)
    log("Displayed the help menu.")
    return False


# Set the help menu function generated from the CLI options.
interaction.set_help_menu(help_menu)


def get_metric_length(metric_val: Tuple[str, str | Tuple[str, str]]) -> int:
    """Calculates the formatted string length of an output calculated
    metric value.

    Args:
        metric_val (Tuple[str | [str,Tuple[str,str]]): The given metric
        value - the first string is the metric name, the second is the
        value string, and the optional third string is the delta value.

    Returns:
        int: The length of the formatted metric string."""
    if not isinstance(metric_val[1], tuple):
        value_len = len(metric_val[1])
    else:
        value_len = len(metric_val[1][0]) + len(metric_val[1][1]) + 3
    return len(unidecode.unidecode(metric_val[0])) + value_len


def process_metrics(
    metrics: Iterable[Type[complexity.CodeMetricUnit]],
    source: interaction.CSource,
    obfuscated: interaction.CSource,
) -> dict[str, list[Tuple[str, str]]]:
    """Processes the list of given metrics if possible, performing multiple
    passes if necessary to ensure that metrics have their desired constraints
    (predecessor metrics) satisfied. O(n^2) worst case, but this can be run
    in O(n) time so long as the provided list of metrics is correctly ordered
    so that predecessors come before the metrics they are used in.

    Args:
        metrics (Iterable[Type[complexity.CodeMetricUnit]]): The list of metric
        classes to use. Should extend the complexity.CodeMetricUnit class.
        source (interaction.CSource): The original, unobfuscated C source file.
        obfuscated (interaction.CSource): The final obfuscated C source file.

    Returns:
        dict[str, list[Tuple[str, str]]]: A dictionary mapping the metric's name to
        a list of string tuples, where the first string in each tuple is the
        value's name/meaning and the second is the actual value."""
    metrics = [m for m in metrics]  # Create a copy to avoid mutation
    processed_values = {}
    while len(metrics) != 0:
        just_processed = []
        for metric in metrics:
            # Check all predecessors have already been calculated.
            missing_preds = [
                req
                for req in metric.predecessors
                if req in metrics and req not in just_processed
            ]
            if len(missing_preds) > 0:
                continue
            # Calculate metrics, recovering from unexpected error
            try:
                metric_unit = metric()
                metric_unit.calculate_metrics(source, obfuscated)
                metric_values = metric_unit.get_metrics()
                processed_values[metric.name] = metric_values
            except Exception as e:
                log(f"Unknown error when processing metrics: {e}")
            just_processed.append(metric)
        if len(just_processed) == 0:
            log(f"Unsatisfiable metric predecessor dependencies: {metrics}")
            return
        for metric in just_processed:
            metrics.remove(metric)  # Remove metrics at the end to avoid iteration bugs
    return processed_values


def display_complexity_metrics(
    source: interaction.CSource, obfuscated: interaction.CSource
) -> None:
    """Prints out all available complexity metrics (retrieved from valid subclasses
    of the complexity.CodeMetricUnit abstract base class), feeding them the original
    source code and the obfuscated code and printing out the results for each metric.

    Args:
        source (interaction.CSource): The original, unmodified source C program.
        obfuscated (interaction.CSource): The final C program after all obfuscation."""
    if source is None or obfuscated is None:
        return
    log("Began processing and displaying complexity metrics")
    print("\n===Obfuscation Metrics===")
    # Retrieve, process, and calculate the size of metrics
    metrics = complexity.CodeMetricUnit.__subclasses__()
    metric_value_dict = process_metrics(metrics, source, obfuscated)
    max_str_len = 0
    for metric_values in metric_value_dict.values():
        max_str_len = max(max_str_len, *[get_metric_length(m) for m in metric_values])
    # Print formatted metrics in a tabulated list
    for metric_name, metric_vals in metric_value_dict.items():
        print(f"\n{metric_name}:")
        for name, val in metric_vals:
            values = f"{val[0]} ({val[1]})" if isinstance(val, tuple) else val
            padding = " " * (max_str_len - len(unidecode.unidecode(name)) - len(values))
            print(f"  {name}:        {padding}{values}")
    print("")
    log("Finished displaying complexity metrics")


def load_composition() -> obfs.Pipeline | None:
    """Attempts to load the saved composition file into a valid pipeline object
    using relevant file reading and JSON parsing. Also sets the seed to be
    used if no seed was given during this execution.


    Returns:
        obfs.Pipeline | None: The loaded pipeline corresponding to the
        information in the composition file. None if an error ocurred.
    """
    file_contents = interaction.load_composition_file(config.COMPOSITION)
    if file_contents is None:
        logprint(
            "Error loading saved transformations - invalid composition file supplied."
        )
        return None
    saved_pipeline = obfs.Pipeline.from_json(file_contents, use_gui=False)
    if saved_pipeline is None:
        logprint(
            "Error loading saved transformations - please provide a valid compositions file"
        )
        return None
    if config.SEED is None:  # Only use the saved seed if no seed was provided
        config.SEED = saved_pipeline.seed
    log("Loaded saved composition into pipeline.")
    return saved_pipeline


def cli_obfuscation(
    source: interaction.CSource, seed: int | None = None
) -> interaction.CSource | None:
    """Given a source program to obfuscate, this program implements the CLI that allows
    users to select a sequence of obfuscation transformations to apply and obfuscates
    the program, returning the result.

    Args:
        source (interaction.CSource): The C source file to obfuscate.
        seed (int | None, optional): The seed to use for randomness. Defaults to None.

    Returns:
        interaction.CSource | None: The obfuscated C source file, or None if quit."""
    # Load starting selections from the composition file if provided
    if config.COMPOSITION is not None:
        composition_pipeline = load_composition()
        if composition_pipeline is None:
            return None
        selected = composition_pipeline.transforms
    else:
        selected = []
    cursor_index = len(selected)

    # Generate available transforms from implemented CLI subclasses
    available_transforms = [
        c.__subclasses__() for c in obfs.ObfuscationUnit.__subclasses__()
    ]
    available_transforms = [c[0] for c in available_transforms if len(c) > 0]
    available_transforms = sorted(available_transforms, key=lambda c: c.type.value)
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
        prompt = "\nCurrent transforms: {} >>> {}\n".format(
            " -> ".join(str(t) for t in selected[:cursor_index]),
            " -> ".join(str(t) for t in selected[cursor_index:]),
        )
        choice = interaction.menu_driven_option(options, prompt=prompt)
        if choice == -1:  # Choice to quit
            log("Selected to exit the transformation selection menu.")
            return None
        elif choice < num_transforms:  # Choice to load a specific transform
            new_t = available_transforms[choice].get_cli()
            if new_t is None:
                continue
            selected = selected[:cursor_index] + [new_t] + selected[cursor_index:]
            log(
                "Added transform {} at index {}. Current transforms: {}".format(
                    new_t.name, cursor_index, " -> ".join(str(t) for t in selected)
                )
            )
            cursor_index += 1
        elif choice == num_transforms:  # Choice to move cursor left
            cursor_index = max(cursor_index - 1, 0)
        elif choice == num_transforms + 1:  # Choice to move cursor right
            cursor_index = min(cursor_index + 1, len(selected))
        elif choice == num_transforms + 2:  # Choice to delete transform after cursor
            if cursor_index < len(selected):
                log(
                    f"Deleted selected transform {selected[cursor_index]} at index {cursor_index}"
                )
            selected = selected[:cursor_index] + selected[(cursor_index + 1) :]
        elif choice == num_transforms + 3:  # Choice to edit transform after cursor
            if cursor_index < len(selected):
                log(
                    f"Began editing transform {selected[cursor_index]} at index {cursor_index}"
                )
                selected[cursor_index].edit_cli()
        else:  # Choice to finish selecting
            done_selecting = True
            log("Finished selecting from command line.")

    # Apply selected transform pipeline to given source code
    pipeline = obfs.Pipeline(seed, *selected)
    if config.SAVE_COMPOSITION:
        # TODO if time: could let users give a file location or not?
        interaction.save_composition_file(pipeline.to_json())
    original = copy.deepcopy(source)
    obfuscated = pipeline.process(source)
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
    args = interaction.handle_arguments(supplied_args, interaction.shared_options)
    if isinstance(args, bool):
        return args

    # Read file and display parse errors
    if len(args) == 0:  # 0 arguments supplied, which is erroneous
        print_error(
            "No source file supplied. Use the -h or --help options to see usage information."
        )
        log("Aborting executions because no arguments were supplied.")
        return False
    elif len(args) > 2:
        print_error(
            "Unrecognised number of arguments. At most 2 arguments must be supplied.\n"
            "Use the -h or --help options to see usage information."
        )
        log(f"Aborting execution because too many arguments ({len(args)}) were given.")
        return False
    source = interaction.CSource(args[0])
    if source.contents is None or not source.valid_parse:
        return False
    obfuscated = cli_obfuscation(source, config.SEED)
    if obfuscated is None:
        return False

    # Choose how to record the output based on the number of arguments
    if len(args) == 1:  # 1 argument - take as input source file, and print output
        if obfuscated is not None:
            log("Displaying obfuscation output.")
            print("\n===Obfuscated Output===")
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
            log("Execution finished normally; file was written to successfuly.")
            return True
        except Exception as e:
            print_error(f"Error creating output file '{args[1]}'")
            log(f"Error when writing output to file: {str(e)}")
    return False
