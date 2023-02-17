""" File: cli.py
Implements functions and logic for providing the command-line interface of the program,
such that it can be used through text interaction in a terminal window as either a 
menu-driven CLI, or as a traditional single command GUI with use of appropriate options
providing a JSON file. Handles the overall general CLI interaction / control flow, as well
as CLI system arguments and options."""

from . import interaction, complexity, obfuscation as obfs
from .debug import print_error, create_log_file, log, logprint
from app import settings as config
from typing import Iterable, Type, Tuple, Optional
import sys, copy, unidecode


# Define Cli obfuscation subclasses with CLI methods for creating new transformations
# and editing existing transformations, such that they can be used within the GUI.
class CliIdentityUnit(obfs.IdentityUnit):

    def edit_cli(self) -> bool:
        """Implements a command-line interface for editing an identity transformation.

        Returns:
            bool: True if editing successful, false if the user chose to quit.
        """
        return True

    def get_cli() -> Optional["CliIdentityUnit"]:
        """Creates an identity transformation and performs the CLI interaction to allow
        the user to edit the new transform.

        Returns:
            Optional[IdentityUnit]: the transform created from user CLI interaction.
            Returns None if the user chose to quit within the CLI.
        """
        new_transform = CliIdentityUnit()
        return new_transform
    
    def from_json(json_str: str) -> None:
        return CliIdentityUnit()


class CliAugmentOpaqueUnit(obfs.AugmentOpaqueUnit):
    
    def edit_cli(self) -> bool:
        styles = obfs.AugmentOpaqueUnit.generic_styles(self.styles)
        if styles is None:
            return None
        print(f"The current probability of augmentation is {self.probability}.")
        print("What is the new probability (0.0 <= p <= 1.0) of the augmentation?")
        prob = interaction.get_float(0.0, 1.0)
        if prob == float("nan"):
            return None
        self.styles = styles
        self.traverser.styles = styles
        self.probability = prob
        self.traverser.probability = prob
        return True

    def get_cli() -> Optional["CliAugmentOpaqueUnit"]:  
        # TODO could also add a NUMBER field???
        styles = obfs.AugmentOpaqueUnit.generic_styles([s for s in obfs.OpaqueAugmenter.Style])
        if styles is None:
            return None
        print("What is the probability (0.0 <= p <= 1.0) of the augmentation?")
        prob = interaction.get_float(0.0, 1.0)
        if prob == float("nan"):
            return None
        return CliAugmentOpaqueUnit(styles, prob)

    def from_json(json_str: str) -> None:
        unit = obfs.AugmentOpaqueUnit.from_json(json_str)
        if unit is None:
            return None
        return CliAugmentOpaqueUnit(unit.styles, unit.probability)


class CliInsertOpaqueUnit(obfs.InsertOpaqueUnit):

    def edit_cli(self) -> bool:
        styles = CliInsertOpaqueUnit.generic_styles(self.styles)
        if styles is None:
            return None
        granularities = CliInsertOpaqueUnit.generic_granularities(self.granularities)
        if granularities is None:
            return None
        kinds = CliInsertOpaqueUnit.generic_kinds(self.kinds)
        if kinds is None:
            return None
        print(
            f"The current number of opaque predicate insertions per function is {self.number}."
        )
        print(
            "What is the new number (n >= 0) of the opaque predicate insertions? (recommended: 1 <= n <= 10)"
        )
        number = interaction.get_int(0, None)
        if number is None:
            return None
        self.styles = styles
        self.traverser.styles = styles
        self.granularities = granularities
        self.traverser.granularities = granularities
        self.kinds = kinds
        self.traverser.kinds = kinds
        self.number = number
        self.traverser.number = number
        return True

    def get_cli() -> Optional["CliInsertOpaqueUnit"]:
        styles = CliInsertOpaqueUnit.generic_styles([s for s in obfs.OpaqueInserter.Style])
        if styles is None:
            return None
        granularities = CliInsertOpaqueUnit.generic_granularities(
            [g for g in obfs.OpaqueInserter.Granularity]
        )
        if granularities is None:
            return None
        kinds = CliInsertOpaqueUnit.generic_kinds([k for k in obfs.OpaqueInserter.Kind])
        if kinds is None:
            return None
        print(
            "What number (n >= 0) of new opaque predicates should be added per function? (recommended: 1 <= n <= 10)"
        )
        number = interaction.get_int(0, None)
        if number is None:
            return None
        return CliInsertOpaqueUnit(styles, granularities, kinds, number)

    def generic_styles(
        styles: Iterable[obfs.OpaqueInserter.Style],
    ) -> Iterable[obfs.OpaqueInserter.Style] | None:
        available = [s for s in obfs.OpaqueInserter.Style]
        choice = 0
        while choice < len(obfs.OpaqueInserter.Style) or len(styles) == 0:
            options = [
                ("[X] " if s in styles else "[ ] ") + s.value
                for s in obfs.OpaqueInserter.Style
            ]
            options.append("Finish selecting styles.")
            prompt = "\nChoose which syles to enable for opaque predicate insertion, or choose to finish.\n"
            choice = interaction.menu_driven_option(options, prompt)
            if choice == -1:
                return None
            elif choice < len(obfs.OpaqueInserter.Style):
                style = obfs.OpaqueInserter.Style(available[choice])
                if style in styles:
                    styles.remove(style)
                else:
                    styles.append(style)
            elif len(styles) == 0:
                print(
                    "No valid options are currently selected. Please select at least one option.\n"
                )
        return styles

    def generic_granularities(
        granularities: Iterable[obfs.OpaqueInserter.Granularity],
    ) -> Iterable[obfs.OpaqueInserter.Granularity] | None:
        available = [g for g in obfs.OpaqueInserter.Granularity]
        choice = 0
        while choice < len(obfs.OpaqueInserter.Granularity) or len(granularities) == 0:
            options = [
                ("[X] " if g in granularities else "[ ] ") + g.value
                for g in obfs.OpaqueInserter.Granularity
            ]
            options.append("Finish selecting granularities.")
            prompt = "\nChoose which granularities to enable for opaque predicate insertion, or choose to finish.\n"
            choice = interaction.menu_driven_option(options, prompt)
            if choice == -1:
                return None
            elif choice < len(obfs.OpaqueInserter.Granularity):
                granularity = obfs.OpaqueInserter.Granularity(available[choice])
                if granularity in granularities:
                    granularities.remove(granularity)
                else:
                    granularities.append(granularity)
            elif len(granularities) == 0:
                print(
                    "No valid options are currently selected. Please select at least one option.\n"
                )
        return granularities

    def generic_kinds(
        kinds: Iterable[obfs.OpaqueInserter.Kind],
    ) -> Iterable[obfs.OpaqueInserter.Kind] | None:
        available = [k for k in obfs.OpaqueInserter.Kind]
        choice = 0
        while choice < len(obfs.OpaqueInserter.Kind) or len(kinds) == 0:
            options = [
                ("[X] " if k in kinds else "[ ] ") + k.value
                for k in obfs.OpaqueInserter.Kind
            ]
            options.append("Finish selecting kinds.")
            prompt = "\nChoose which kinds to enable for opaque predicate insertion, or choose to finish.\n"
            choice = interaction.menu_driven_option(options, prompt)
            if choice == -1:
                return None
            elif choice < len(obfs.OpaqueInserter.Kind):
                kind = obfs.OpaqueInserter.Kind(available[choice])
                if kind in kinds:
                    kinds.remove(kind)
                else:
                    kinds.append(kind)
            elif len(kinds) == 0:
                print(
                    "No valid options are currently selected. Please select at least one option.\n"
                )
        return kinds

    def from_json(json_str: str) -> None:
        unit = obfs.InsertOpaqueUnit.from_json(json_str)
        if unit is None:
            return None
        return CliInsertOpaqueUnit(
            unit.styles, unit.granularities, unit.kinds, unit.number
        )


class CliControlFlowFlattenUnit(obfs.ControlFlowFlattenUnit):

    def edit_cli(self) -> bool:
        options = ["Randomise case order", "Do not randomise case order"]
        prompt = (
            "\nYou have currently selected to{} randomise the case order.\n".format(
                "" if self.randomise_cases else " not"
            )
        )
        prompt += "Select whether you would like to randomise the generated case order or not.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return False
        randomise_cases = choice == 0
        options = [s.value for s in obfs.ControlFlowFlattener.Style]
        prompt = f"\nThe current case generation style is '{self.style.value}'.\n"
        prompt += "Choose a new style for control flow flattening case generation.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return False
        self.randomise_cases = randomise_cases
        self.traverser.randomise_cases = randomise_cases
        self.style = obfs.ControlFlowFlattener.Style(options[choice])
        self.traverser.style = self.style
        return True

    def get_cli() -> Optional["CliControlFlowFlattenUnit"]:
        options = ["Randomise case order", "Do not randomise case order"]
        prompt = "\nSelect whether you would like to randomise the generated case order or not.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return None
        randomise_cases = choice == 0
        options = [s.value for s in obfs.ControlFlowFlattener.Style]
        prompt = (
            "\nChoose a style for the cases generated in control flow flattening.\n"
        )
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return None
        style = obfs.ControlFlowFlattener.Style(options[choice])
        return CliControlFlowFlattenUnit(randomise_cases, style)

    def from_json(json_str: str) -> None:
        unit = obfs.ControlFlowFlattenUnit.from_json(json_str)
        if unit is None:
            return None
        return CliControlFlowFlattenUnit(unit.randomise_cases, unit.style)


class CliFuncArgumentRandomiseUnit(obfs.FuncArgumentRandomiseUnit):

    def edit_cli(self) -> bool:  # TODO - maybe allow users to give specific functions?
        print(f"The current number of extra arguments is {self.extra_args}.")
        print("What is the new number of extra arguments per function?")
        extra = interaction.get_int(0, None)
        if extra is None:
            return False
        self.extra_args = extra
        self.traverser.extra = extra
        return True

    def get_cli() -> Optional["CliFuncArgumentRandomiseUnit"]:
        # TODO should I add an option to make randomisation optional?
        print("How many extra arguments should be inserted?")
        extra = interaction.get_int(0, None)
        if extra is None:
            return False
        return CliFuncArgumentRandomiseUnit(extra)

    def from_json(json_str: str) -> None:
        unit = obfs.FuncArgumentRandomiseUnit.from_json(json_str)
        if unit is None:
            return None
        return CliFuncArgumentRandomiseUnit(unit.extra_args)


class CliIdentifierRenameUnit(obfs.IdentifierRenameUnit):

    def edit_cli(self) -> bool:
        options = [s.value for s in obfs.IdentifierTraverser.Style]
        options.append("placeholder")
        options.append("Finish editing")
        while True:
            prompt = f'\nChoose a style for the identifier renaming. Your current style is "{self.style.value}".\n'
            if self.minimiseIdents:
                options[
                    len(obfs.IdentifierTraverser.Style)
                ] = "Disable minimal identifier usage option [WARNING:EXPERIMENTAL] (currently: ENABLED)"
            else:
                options[
                    len(obfs.IdentifierTraverser.Style)
                ] = "Enable minimal identifer usage option [WARNING:EXPERIMENTAL] (currently: DISABLED)"
            choice = interaction.menu_driven_option(options, prompt)
            if choice == -1:
                return False
            elif choice == len(obfs.IdentifierTraverser.Style):
                self.minimiseIdents = not self.minimiseIdents
            elif choice == len(options) - 1:
                return True
            else:
                self.style = obfs.IdentifierTraverser.Style(options[choice])

    def get_cli() -> Optional["CliIdentifierRenameUnit"]:
        options = [s.value for s in obfs.IdentifierTraverser.Style]
        prompt = "\nChoose a style for the identifier renaming.\n"
        minimiseIdents = False
        validChoice = False
        while not validChoice:
            if minimiseIdents:
                options.append(
                    "Disable minimal identifier usage option [WARNING:EXPERIMENTAL] (currently: ENABLED)"
                )
            else:
                options.append(
                    "Enable minimal identifer usage option [WARNING:EXPERIMENTAL] (currently: DISABLED)"
                )
            choice = interaction.menu_driven_option(options, prompt)
            if choice == -1:
                return None
            elif choice == len(obfs.IdentifierTraverser.Style):
                minimiseIdents = not minimiseIdents
                options = options[:-1]
            else:
                style = obfs.IdentifierTraverser.Style(options[choice])
                return CliIdentifierRenameUnit(style, minimiseIdents)
        return None

    def from_json(json_str: str) -> None:
        unit = obfs.IdentifierRenameUnit.from_json(json_str)
        if unit is None:
            return None
        return CliIdentifierRenameUnit(unit.style, unit.minimiseIdents)


class CliReverseIndexUnit(obfs.ReverseIndexUnit):

    def edit_cli(self) -> bool:
        print(f"The current probability of index reversal is {self.probability}.")
        print("What is the new probability (0.0 <= p <= 1.0) of reversal?")
        prob = interaction.get_float(0.0, 1.0)
        if prob == float("nan"):
            return None
        self.probability = prob
        self.traverser.probability = prob
        return True

    def get_cli() -> Optional["CliReverseIndexUnit"]:
        print("What is the probability (0.0 <= p <= 1.0) of the augmentation?")
        prob = interaction.get_float(0.0, 1.0)
        if prob == float("nan"):
            return None
        return CliReverseIndexUnit(prob)
    
    def from_json(json_str: str) -> None:
        unit = obfs.ReverseIndexUnit.from_json(json_str)
        if unit is None:
            return None
        return CliReverseIndexUnit(unit.probability)


class CliClutterWhitespaceUnit(obfs.ClutterWhitespaceUnit):
    
    def edit_cli(self) -> bool:
        print(f"The current target maximum line length is {self.target_length}.")
        print(
            "What target maximum line length (l >= 0) should be used? (recommended: l = 100)"
        )
        target_length = interaction.get_int(0, None)
        if target_length is None:
            return False
        options = ["Pad lines to max length", "Do not pad lines to max length"]
        prompt = "\nYou have currently selected to{} pad the generated lines.\n".format(
            "" if self.pad_lines else " not"
        )
        prompt += "Select whether you would like to pad the generated lines to max length (where possible) or not.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return False
        self.target_length = target_length
        self.pad_lines = choice == 0
        return True

    def get_cli() -> Optional["CliClutterWhitespaceUnit"]:
        print(
            "What target maximum line length (l >= 0) should be used? (recommended: l = 100)"
        )
        target_length = interaction.get_int(0, None)
        if target_length is None:
            return False
        options = ["Pad lines to max length", "Do not pad lines to max length"]
        prompt = "\nSelect whether you would like to pad the generated lines to max length (where possible) or not.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return None
        return CliClutterWhitespaceUnit(target_length, choice == 0)

    def from_json(json_str: str) -> None:
        unit = obfs.ClutterWhitespaceUnit.from_json(json_str)
        if unit is None:
            return None
        return CliClutterWhitespaceUnit(unit.target_length, unit.pad_lines)


class CliDiTriGraphEncodeUnit(obfs.DiTriGraphEncodeUnit):

    def edit_cli(self) -> bool:
        options = [s.value for s in self.Style]
        prompt = f"\nThe current encoding style is {self.style.value}.\n"
        prompt += "Choose a new style for the digraph/trigraph encoding.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return False
        style = self.Style(options[choice])
        print(f"The current probability of encoding is {self.chance}.")
        print("What is the new probability (0.0 <= p <= 1.0) of the encoding?")
        prob = interaction.get_float(0.0, 1.0)
        if prob == float("nan"):
            return False
        self.style = style
        self.chance = prob
        return True

    def get_cli() -> "CliDiTriGraphEncodeUnit":
        options = [s.value for s in CliDiTriGraphEncodeUnit.Style]
        prompt = "\nChoose a style for the digraph/trigraph encoding.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return None
        style = CliDiTriGraphEncodeUnit.Style(options[choice])
        print("What is the probability (0.0 <= p <= 1.0) of the encoding?")
        prob = interaction.get_float(0.0, 1.0)
        if prob == float("nan"):
            return None
        return CliDiTriGraphEncodeUnit(style, prob)

    def from_json(json_str: str) -> None:
        unit = obfs.DiTriGraphEncodeUnit.from_json(json_str)
        if unit is None:
            return None
        return CliDiTriGraphEncodeUnit(unit.style, unit.chance)


class CliStringEncodeUnit(obfs.StringEncodeUnit):

    def edit_cli(self) -> bool:
        options = [s.value for s in obfs.StringEncodeTraverser.Style]
        prompt = f"\nThe current encoding style is {self.style.value}.\n"
        prompt += "Choose a new style for string encoding.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return False
        self.style = obfs.StringEncodeTraverser.Style(options[choice])
        self.traverser.style = self.style
        return True

    def get_cli() -> Optional["CliStringEncodeUnit"]:
        options = [s.value for s in obfs.StringEncodeTraverser.Style]
        prompt = "\nChoose a style for the string encoding.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return None
        style = obfs.StringEncodeTraverser.Style(options[choice])
        return CliStringEncodeUnit(style)
    
    def from_json(json_str: str) -> None:
        unit = obfs.StringEncodeUnit.from_json(json_str)
        if unit is None:
            return None
        return CliStringEncodeUnit(unit.style)
    

class CliIntegerEncodeUnit(obfs.IntegerEncodeUnit):

    def edit_cli(self) -> bool:
        options = [s.value for s in obfs.IntegerEncodeTraverser.Style]
        prompt = f"\nThe current encoding style is {self.style.value}.\n"
        prompt += "Choose a new style for integer encoding.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return False
        self.style = obfs.IntegerEncodeTraverser.Style(options[choice])
        self.traverser.style = self.style
        return True

    def get_cli() -> Optional["CliIntegerEncodeUnit"]:
        options = [s.value for s in obfs.IntegerEncodeTraverser.Style]
        prompt = "\nChoose a style for the integer encoding.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return None
        style = obfs.IntegerEncodeTraverser.Style(options[choice])
        return CliIntegerEncodeUnit(style)

    def from_json(json_str: str) -> None:
        unit = obfs.IntegerEncodeUnit.from_json(json_str)
        if unit is None:
            return None
        return CliIntegerEncodeUnit(unit.style)


class CliArithmeticEncodeUnit(obfs.ArithmeticEncodeUnit):

    def edit_cli(self) -> bool:
        print(f"The current arithmetic encoding depth is {self.level}.")
        print("What is the new depth (recommended: 1 <= d <= 5) of the encoding?")
        depth = interaction.get_int(1, None)
        if depth is None:
            return False
        self.level = depth
        self.traverser.transform_depth = depth
        return True

    def get_cli() -> Optional["CliArithmeticEncodeUnit"]:
        print(
            "What recursive arithmetic encoding depth should be used? (recommended: 1 <= d <= 5)"
        )
        depth = interaction.get_int(0, None)
        if depth is None:
            return False
        return CliArithmeticEncodeUnit(depth)

    def from_json(json_str: str) -> None:
        unit = obfs.ArithmeticEncodeUnit.from_json(json_str)
        if unit is None:
            return None
        return CliArithmeticEncodeUnit(unit.level)


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
    ).format(__file__.split("\\")[-1])
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
    available_transforms = [c.__subclasses__() for c in obfs.ObfuscationUnit.__subclasses__()]
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
    if config.SAVE_COMPOSITION: # TODO could let users give a file location or not?
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
