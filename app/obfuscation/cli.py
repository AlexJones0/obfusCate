""" File: obfuscation/cli.py
Defines subclasses of the obfuscation transformation unit classes that
provide support for command-line interface operation through the
addition of `get_cli` and `edit_cli` functions. This allows these
transformations to be instantiated and edited through a CLI.
"""
from .. import interaction
from . import *
from typing import Optional


class CliIdentityUnit(IdentityUnit):
    """The identity transformation with added command-line interfaces."""

    def edit_cli(self) -> bool:
        """Implements a command-line interface for editing an identity transformation.

        Returns:
            bool: True if editing successful, false if the user chose to quit."""
        return True

    def get_cli() -> Optional["CliIdentityUnit"]:
        """Creates an identity transformation and performs the CLI interaction to allow
        the user to edit the new transform.

        Returns:
            Optional[CliIdentityUnit]: the transform created from user CLI interaction.
            Returns None if the user chose to quit within the CLI."""
        return CliIdentityUnit()

    def from_json(json_str: str) -> "CliIdentityUnit":
        """Loads the CLI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the CliIdentityUnit.

        Returns:
            CliIdentityUnit: The corresponding CliIdentityUnit object."""
        return CliIdentityUnit()


class CliAugmentOpaqueUnit(AugmentOpaqueUnit):
    """The opaque augmentation transformation with added command-line interfaces."""

    def edit_cli(self) -> bool:
        """Implements a command-line interface for editing an opaque augmentation
        transformation.

        Returns:
            bool: True if editing successful, false if the user chose to quit."""
        styles = interaction.cli_enum_select(
            OpaqueAugmenter.Style,
            self.styles,
            "styles",
            "opaque predicate augmenting",
        )
        if styles is None:
            return None
        print(f"The current probability of augmentation is {self.probability}.")
        print("What is the new probability (0.0 <= p <= 1.0) of the augmentation?")
        prob = interaction.get_float(0.0, 1.0)
        if prob == float("nan"):
            return None
        print(f"The current number of predicates per condition is {self.number}.")
        print("What is the new number (n >= 0) of predicates to augment with?")
        number = interaction.get_int(0, None)
        if number is None:
            return None
        self.styles = styles
        self.traverser.styles = styles
        self.probability = prob
        self.traverser.probability = prob
        self.number = number
        self.traverser.number = number
        return True

    def get_cli() -> Optional["CliAugmentOpaqueUnit"]:
        """Creates an opaque augmentation transformation and performs the CLI
        interaction to allow the user to edit the new transform.

        Returns:
            Optional[CliAugmentOpaqueUnit]: the transform created from user CLI
            interaction. Returns None if the user chose to quit within the CLI."""
        styles = interaction.cli_enum_select(
            OpaqueAugmenter.Style,
            [s for s in OpaqueAugmenter.Style],
            "styles",
            "opaque predicate augmenting",
        )
        if styles is None:
            return None
        print("What is the probability (0.0 <= p <= 1.0) of the augmentation?")
        prob = interaction.get_float(0.0, 1.0)
        if prob == float("nan"):
            return None
        print("How many (n >= 0) predicates should be used to augment each condition?")
        number = interaction.get_int(0, None)
        if number is None:
            return None
        return CliAugmentOpaqueUnit(styles, prob, number)

    def from_json(json_str: str) -> Optional["CliAugmentOpaqueUnit"]:
        """Loads the CLI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the CliAugmentOpaqueUnit.

        Returns:
            Optional[CliAugmentOpaqueUnit]: The corresponding CliAugmentOpaqueUnit
            object."""
        unit = AugmentOpaqueUnit.from_json(json_str)
        if unit is None:
            return None
        return CliAugmentOpaqueUnit(unit.styles, unit.probability, unit.number)


class CliInsertOpaqueUnit(InsertOpaqueUnit):
    """The opaque insertion transformation with added command-line interfaces."""

    def edit_cli(self) -> bool:
        """Implements a command-line interface for editing an opaque insertion
        transformation.

        Returns:
            bool: True if editing successful, false if the user chose to quit."""
        styles = interaction.cli_enum_select(
            OpaqueInserter.Style,
            self.styles,
            "styles",
            "opaque predicate insertion",
        )
        if styles is None:
            return None
        granularities = interaction.cli_enum_select(
            OpaqueInserter.Granularity,
            self.granularities,
            "granularities",
            "opaque predicate insertion",
        )
        if granularities is None:
            return None
        kinds = interaction.cli_enum_select(
            OpaqueInserter.Kind,
            self.kinds,
            "predicate kinds",
            "opaque predicate insertion",
        )
        if kinds is None:
            return None
        print(
            f"The current number of opaque predicate insertions per function is {self.number}."
        )
        print(
            "What is the new number (n >= 0) of the opaque predicate insertions? "
            "(recommended: 1 <= n <= 10)"
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
        """Creates an opaque insertion transformation and performs the CLI
        interaction to allow the user to edit the new transform.

        Returns:
            Optional[CliInsertOpaqueUnit]: the transform created from user CLI
            interaction. Returns None if the user chose to quit within the CLI."""
        styles = interaction.cli_enum_select(
            OpaqueInserter.Style,
            [s for s in OpaqueInserter.Style],
            "styles",
            "opaque predicate insertion",
        )
        if styles is None:
            return None
        granularities = interaction.cli_enum_select(
            OpaqueInserter.Granularity,
            [g for g in OpaqueInserter.Granularity],
            "granularities",
            "opaque predicate insertion",
        )
        if granularities is None:
            return None
        kinds = interaction.cli_enum_select(
            OpaqueInserter.Kind,
            [k for k in OpaqueInserter.Kind],
            "predicate kinds",
            "opaque predicate insertion",
        )
        if kinds is None:
            return None
        print(
            "What number (n >= 0) of new opaque predicates should be added per function? "
            "(recommended: 1 <= n <= 10)"
        )
        number = interaction.get_int(0, None)
        if number is None:
            return None
        return CliInsertOpaqueUnit(styles, granularities, kinds, number)

    def from_json(json_str: str) -> Optional["CliInsertOpaqueUnit"]:
        """Loads the CLI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the CliInsertOpaqueUnit.

        Returns:
            Optional[CliInsertOpaqueUnit]: The corresponding CliInsertOpaqueUnit object."""
        unit = InsertOpaqueUnit.from_json(json_str)
        if unit is None:
            return None
        return CliInsertOpaqueUnit(
            unit.styles, unit.granularities, unit.kinds, unit.number
        )


class CliControlFlowFlattenUnit(ControlFlowFlattenUnit):
    """The control flow flattening transformation with added command-line interfaces."""

    def edit_cli(self) -> bool:
        """Implements a command-line interface for editing a control flow flattening
        transformation.

        Returns:
            bool: True if editing successful, false if the user chose to quit."""
        options = ["Randomise case order", "Do not randomise case order"]
        prompt = (
            "You have currently selected to{} randomise the case order.\n"
            "Select whether you would like to randomise the generated case order or not.\n"
        ).format("" if self.randomise_cases else " not")
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return False
        randomise_cases = choice == 0
        options = [s.value for s in ControlFlowFlattener.Style]
        prompt = f"\nThe current case generation style is '{self.style.value}'.\n"
        prompt += "Choose a new style for control flow flattening case generation.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return False
        self.randomise_cases = randomise_cases
        self.traverser.randomise_cases = randomise_cases
        self.style = ControlFlowFlattener.Style(options[choice])
        self.traverser.style = self.style
        return True

    def get_cli() -> Optional["CliControlFlowFlattenUnit"]:
        """Creates a control flow flattening transformation and performs the CLI
        interaction to allow the user to edit the new transform.

        Returns:
            Optional[CliControlFlowFlattenUnit]: the transform created from user CLI
            interaction. Returns None if the user chose to quit within the CLI."""
        options = ["Randomise case order", "Do not randomise case order"]
        prompt = "\nSelect whether you would like to randomise the generated case order or not.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return None
        randomise_cases = choice == 0
        options = [s.value for s in ControlFlowFlattener.Style]
        prompt = (
            "\nChoose a style for the cases generated in control flow flattening.\n"
        )
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return None
        style = ControlFlowFlattener.Style(options[choice])
        return CliControlFlowFlattenUnit(randomise_cases, style)

    def from_json(json_str: str) -> Optional["CliControlFlowFlattenUnit"]:
        """Loads the CLI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the CliControlFlowFlattenUnit.

        Returns:
            Optional[CliControlFlowFlattenUnit]: The corresponding CliControlFlowFlattenUnit
            object."""
        unit = ControlFlowFlattenUnit.from_json(json_str)
        if unit is None:
            return None
        return CliControlFlowFlattenUnit(unit.randomise_cases, unit.style)


class CliFuncArgumentRandomiseUnit(FuncArgumentRandomiseUnit):
    """The function argument randomisation transformation with added command-line interfaces."""

    def edit_cli(self) -> bool:
        """Implements a command-line interface for editing a function argument
        randomisation transformation.

        Returns:
            bool: True if editing successful, false if the user chose to quit."""
        print(f"The current number of extra arguments is {self.extra_args}.")
        print("What is the new number of extra arguments per function?")
        extra = interaction.get_int(0, None)
        if extra is None:
            return False
        self.extra_args = extra
        self.traverser.extra = extra
        options = ["Randomise argument order", "Do not randomise argument order"]
        prompt = (
            "You have currently selected to{} randomise the function argument order.\n"
            "Select whether you would like to randomise the function argument order or not.\n"
        ).format("" if self.randomise else " not")
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return False
        self.randomise = choice == 0
        self.traverser.randomise = self.randomise
        return True

    def get_cli() -> Optional["CliFuncArgumentRandomiseUnit"]:
        """Creates a function argument (interface) randomisation  transformation
        and performs the CLI interaction to allow the user to edit the new transform.

        Returns:
            Optional[CliFuncArgumentRandomiseUnit]: the transform created from user
            CLI interaction. Returns None if the user chose to quit within the CLI."""
        print("How many extra arguments should be inserted?")
        extra = interaction.get_int(0, None)
        if extra is None:
            return False
        options = ["Randomise argument order", "Do not randomise argument order"]
        prompt = "\nSelect whether you would like to randomise the function argument order or not.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return None
        return CliFuncArgumentRandomiseUnit(extra, (choice == 0))

    def from_json(json_str: str) -> Optional["CliFuncArgumentRandomiseUnit"]:
        """Loads the CLI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the
            CliFuncArgumentRandomiseUnit.

        Returns:
            Optional[CliFuncArgumentRandomiseUnit]: The corresponding
            CliFuncArgumentRandomiseUnit object."""
        unit = FuncArgumentRandomiseUnit.from_json(json_str)
        if unit is None:
            return None
        return CliFuncArgumentRandomiseUnit(unit.extra_args, unit.randomise)


class CliIdentifierRenameUnit(IdentifierRenameUnit):
    """The identifier renaming transformation with added command-line interfaces."""

    def edit_cli(self) -> bool:
        """Implements a command-line interface for editing an identifier renaming
        transformation.

        Returns:
            bool: True if editing successful, false if the user chose to quit."""
        options = [s.value for s in IdentifierTraverser.Style]
        prompt = f"\nThe current identifier renaming style is '{self.style.value}'.\n"
        prompt += "Choose a new style for identifier renaming.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return False
        self.style = IdentifierTraverser.Style(options[choice])
        options = [
            "Minimise identifier usage [WARNING: EXPERIMENTAL]", # TODO WARNING
            "Do not minimise identifier usage",
        ]
        prompt = (
            "You have currently selected to{} minimise identifier usage.\n"
            "Select whether you would like to minimise identifer usage or not.\n"
        ).format("" if self.minimise_idents else " not")
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return False
        self.minimise_idents = (choice == 0)
        return True

    def get_cli() -> Optional["CliIdentifierRenameUnit"]:
        """Creates an identifier renaming transformation and performs the CLI
        interaction to allow the user to edit the new transform.

        Returns:
            Optional[CliIdentifierRenameUnit]: the transform created from user CLI
            interaction. Returns None if the user chose to quit within the CLI."""
        options = [s.value for s in IdentifierTraverser.Style]
        prompt = "\nChoose a style to use for identifier renaming.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return None
        style = IdentifierTraverser.Style(options[choice])
        options = [
            "Minimise identifier usage [WARNING: EXPERIMENTAL]", # TODO WARNING
            "Do not minimise identifier usage",
        ]
        prompt = "Select whether you would like to minimise identifer usage or not.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return None
        return CliIdentifierRenameUnit(style, (choice == 0))

    def from_json(json_str: str) -> Optional["CliIdentifierRenameUnit"]:
        """Loads the CLI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the CliIdentifierRenameUnit.

        Returns:
            Optional[CliIdentifierRenameUnit]: The corresponding CliIdentifierRenameUnit
            object."""
        unit = IdentifierRenameUnit.from_json(json_str)
        if unit is None:
            return None
        return CliIdentifierRenameUnit(unit.style, unit.minimise_idents)


class CliReverseIndexUnit(ReverseIndexUnit):
    """The index reversing transformation with added command-line interfaces."""

    def edit_cli(self) -> bool:
        """Implements a command-line interface for editing an index reversing
        transformation.

        Returns:
            bool: True if editing successful, false if the user chose to quit."""
        print(f"The current probability of index reversal is {self.probability}.")
        print("What is the new probability (0.0 <= p <= 1.0) of reversal?")
        prob = interaction.get_float(0.0, 1.0)
        if prob == float("nan"):
            return False
        self.probability = prob
        self.traverser.probability = prob
        return True

    def get_cli() -> Optional["CliReverseIndexUnit"]:
        """Creates an index reversing transformation and performs the CLI
        interaction to allow the user to edit the new transform.

        Returns:
            Optional[CliReverseIndexUnit]: the transform created from user CLI
            interaction. Returns None if the user chose to quit within the CLI."""
        print("What is the probability (0.0 <= p <= 1.0) of index reversal?")
        prob = interaction.get_float(0.0, 1.0)
        if prob == float("nan"):
            return None
        return CliReverseIndexUnit(prob)

    def from_json(json_str: str) -> Optional["CliReverseIndexUnit"]:
        """Loads the CLI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the CliReverseIndexUnit.

        Returns:
            Optional[CliReverseIndexUnit]: The corresponding CliReverseIndexUnit object."""
        unit = ReverseIndexUnit.from_json(json_str)
        if unit is None:
            return None
        return CliReverseIndexUnit(unit.probability)


class CliClutterWhitespaceUnit(ClutterWhitespaceUnit):
    """The whitespace cluttering transformation with added command-line interfaces."""

    def edit_cli(self) -> bool:
        """Implements a command-line interface for editing a whitespace cluttering
        transformation.

        Returns:
            bool: True if editing successful, false if the user chose to quit."""
        print(f"The current target maximum line length is {self.target_length}.")
        print(
            "What target maximum line length (l >= 0) should be used? "
            "(recommended: l = 100)"
        )
        target_length = interaction.get_int(0, None)
        if target_length is None:
            return False
        options = ["Pad lines to max length", "Do not pad lines to max length"]
        prompt = (
            "\nYou have currently selected to{} pad the generated lines.\n"
            "Select whether you would like to pad the generated lines to\n"
            "max length (where possible) or not.\n"
        ).format("" if self.pad_lines else " not")
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return False
        self.target_length = target_length
        self.pad_lines = (choice == 0)
        return True

    def get_cli() -> Optional["CliClutterWhitespaceUnit"]:
        """Creates a whitespace cluttering transformation and performs the CLI
        interaction to allow the user to edit the new transform.

        Returns:
            Optional[CliClutterWhitespaceUnit]: the transform created from user CLI
            interaction. Returns None if the user chose to quit within the CLI."""
        print(
            "What target maximum line length (l >= 0) should be used? "
            "(recommended: l = 100)"
        )
        target_length = interaction.get_int(0, None)
        if target_length is None:
            return False
        options = ["Pad lines to max length", "Do not pad lines to max length"]
        prompt = (
            "\nSelect whether you would like to pad the generated lines to\n"
            "max length (where possible) or not.\n"
        )
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return None
        return CliClutterWhitespaceUnit(target_length, (choice == 0))

    def from_json(json_str: str) -> Optional["CliClutterWhitespaceUnit"]:
        """Loads the CLI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the CliClutterWhitespaceUnit.

        Returns:
            Optional[CliClutterWhitespaceUnit]: The corresponding CliClutterWhitespaceUnit
            object."""
        unit = ClutterWhitespaceUnit.from_json(json_str)
        if unit is None:
            return None
        return CliClutterWhitespaceUnit(unit.target_length, unit.pad_lines)


class CliDiTriGraphEncodeUnit(DiTriGraphEncodeUnit):
    """The digraph/trigraph encoding transformation with added command-line interfaces."""

    def edit_cli(self) -> bool:
        """Implements a command-line interface for editing a digraph/trigraph
        encoding transformation.

        Returns:
            bool: True if editing successful, false if the user chose to quit."""
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
        """Creates a digraph/trigraph encoding transformation and performs the CLI
        interaction to allow the user to edit the new transform.

        Returns:
            Optional[CliDiTriGraphEncodeUnit]: the transform created from user CLI
            interaction. Returns None if the user chose to quit within the CLI."""
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

    def from_json(json_str: str) -> Optional["CliDiTriGraphEncodeUnit"]:
        """Loads the CLI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the CliDiTriGraphEncodeUnit.

        Returns:
            Optional[CliDiTriGraphEncodeUnit]: The corresponding CliDiTriGraphEncodeUnit
            object."""
        unit = DiTriGraphEncodeUnit.from_json(json_str)
        if unit is None:
            return None
        return CliDiTriGraphEncodeUnit(unit.style, unit.chance)


class CliStringEncodeUnit(StringEncodeUnit):
    """The string literal encoding transformation with added command-line interfaces."""

    def edit_cli(self) -> bool:
        """Implements a command-line interface for editing an string literal
        encoding transformation.

        Returns:
            bool: True if editing successful, false if the user chose to quit."""
        options = [s.value for s in StringEncodeTraverser.Style]
        prompt = f"\nThe current encoding style is {self.style.value}.\n"
        prompt += "Choose a new style for string encoding.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return False
        self.style = StringEncodeTraverser.Style(options[choice])
        self.traverser.style = self.style
        return True

    def get_cli() -> Optional["CliStringEncodeUnit"]:
        """Creates a string literal encoding transformation and performs the CLI
        interaction to allow the user to edit the new transform.

        Returns:
            Optional[CliStringEncodeUnit]: the transform created from user CLI
            interaction. Returns None if the user chose to quit within the CLI."""
        options = [s.value for s in StringEncodeTraverser.Style]
        prompt = "\nChoose a style for the string encoding.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return None
        style = StringEncodeTraverser.Style(options[choice])
        return CliStringEncodeUnit(style)

    def from_json(json_str: str) -> Optional["CliStringEncodeUnit"]:
        """Loads the CLI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the CliStringEncodeUnit.

        Returns:
            Optional[CliStringEncodeUnit]: The corresponding CliStringEncodeUnit object."""
        unit = StringEncodeUnit.from_json(json_str)
        if unit is None:
            return None
        return CliStringEncodeUnit(unit.style)


class CliIntegerEncodeUnit(IntegerEncodeUnit):
    """The integer literal encoding transformation with added command-line interfaces."""

    def edit_cli(self) -> bool:
        """Implements a command-line interface for editing an integer literal
        encoding transformation.

        Returns:
            bool: True if editing successful, false if the user chose to quit."""
        options = [s.value for s in IntegerEncodeTraverser.Style]
        prompt = f"\nThe current encoding style is {self.style.value}.\n"
        prompt += "Choose a new style for integer encoding.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return False
        self.style = IntegerEncodeTraverser.Style(options[choice])
        self.traverser.style = self.style
        return True

    def get_cli() -> Optional["CliIntegerEncodeUnit"]:
        """Creates an integer literal encoding transformation and performs the
        CLI interaction to allow the user to edit the new transform.

        Returns:
            Optional[CliIntegerEncodeUnit]: the transform created from user CLI
            interaction. Returns None if the user chose to quit within the CLI."""
        options = [s.value for s in IntegerEncodeTraverser.Style]
        prompt = "\nChoose a style for the integer encoding.\n"
        choice = interaction.menu_driven_option(options, prompt)
        if choice == -1:
            return None
        style = IntegerEncodeTraverser.Style(options[choice])
        return CliIntegerEncodeUnit(style)

    def from_json(json_str: str) -> Optional["CliIntegerEncodeUnit"]:
        """Loads the CLI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the CliIntegerEncodeUnit.

        Returns:
            Optional[CliIntegerEncodeUnit]: The corresponding CliIntegerEncodeUnit object."""
        unit = IntegerEncodeUnit.from_json(json_str)
        if unit is None:
            return None
        return CliIntegerEncodeUnit(unit.style)


class CliArithmeticEncodeUnit(ArithmeticEncodeUnit):
    """The integer arithmetic encoding transformation with added command-line interfaces."""

    def edit_cli(self) -> bool:
        """Implements a command-line interface for editing an integer arithmetic
        encoding transformation.

        Returns:
            bool: True if editing successful, false if the user chose to quit."""
        print(f"The current arithmetic encoding depth is {self.level}.")
        print("What is the new depth (recommended: 1 <= d <= 5) of the encoding?")
        depth = interaction.get_int(1, None)
        if depth is None:
            return False
        self.level = depth
        self.traverser.transform_depth = depth
        return True

    def get_cli() -> Optional["CliArithmeticEncodeUnit"]:
        """Creates an integer arithmetic encoding transformation and performs
        the CLI interaction to allow the user to edit the new transform.

        Returns:
            Optional[CliArithmeticEncodeUnit]: the transform created from user CLI
            interaction. Returns None if the user chose to quit within the CLI."""
        print(
            "What recursive arithmetic encoding depth should be used? (recommended: 1 <= d <= 5)"
        )
        depth = interaction.get_int(0, None)
        if depth is None:
            return False
        return CliArithmeticEncodeUnit(depth)

    def from_json(json_str: str) -> Optional["CliArithmeticEncodeUnit"]:
        """Loads the CLI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the CliArithmeticEncodeUnit.

        Returns:
            Optional[CliArithmeticEncodeUnit]: The corresponding CliArithmeticEncodeUnit
            object."""
        unit = ArithmeticEncodeUnit.from_json(json_str)
        if unit is None:
            return None
        return CliArithmeticEncodeUnit(unit.level)
