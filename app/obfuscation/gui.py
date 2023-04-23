""" File: obfuscation/gui.py
Defines generic widget generation functions in addition to subclasses 
of the obfuscation transformation unit classes that provide support 
for graphical user interface operation, through the addition of `get_gui`, 
`edit_gui` and `load_gui_values` methods. This allows these
transformations to be instantiated, edited and used through the GUI. 
"""
from ..config import GuiDefaults as Df
from . import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import Qt
from typing import Tuple, Mapping, Any


def set_no_options_widget(parent: QWidget) -> None:
    """Creates the transformation options menu for any obfuscation transformation
    that does not have any options, simply displaying a small centred label with the
    text "No options available.".

    Args:
        parent (QWidget): The parent widget to put this widget into.
    """
    layout = QVBoxLayout(parent)
    no_options_label = QLabel("No options available.", parent)
    no_options_label.setFont(QFont(Df.DEFAULT_FONT, 12))
    no_options_label.setStyleSheet("QLabel{color: #727463;}")
    layout.addWidget(no_options_label, alignment=Qt.AlignmentFlag.AlignCenter)
    parent.setLayout(layout)


def generate_integer_widget(
    label_msg: str,
    tooltip_msg: str,
    init_val: int,
    min_val: int,
    max_val: int,
    parent: QWidget,
) -> Tuple[QWidget, QLineEdit]:
    """Creates a GUI form for transformation option integer entry, displaying a
    left-justified label next to a right-justified entry that only accepts valid
    integer value inputs.

    Args:
        label_msg (str): The text message to label the integer entry with.
        tooltip_msg (str): The text message to display as a tooltip on the label.
        init_val (int): The initial integer value used to occupy the entry.
        min_val (int): The minimum allowed integer value to enter into the entry.
        max_val (int): The maximum allowed integer value to enter into the entry.
        parent (QWidget): The parent widget that this widget will be placed in.

    Returns:
        Tuple[QWidget, QLineEdit]: Returns a tuple, where the first item is the
        created widget, and the second is the exact entry UI element to allow
        you to access a user-entered value.
    """
    integer_widget = QWidget(parent)
    layout = QHBoxLayout(integer_widget)
    layout.setContentsMargins(0, 0, 0, 0)
    label = QLabel(label_msg, integer_widget)
    label.setFont(QFont(Df.DEFAULT_FONT, 12))
    label.setToolTip(tooltip_msg)
    QToolTip.setFont(QFont(Df.DEFAULT_FONT, 13))
    label.setStyleSheet("QLabel{color: #727463;}\n" + Df.GENERAL_TOOLTIP_CSS)
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignLeft)
    layout.addStretch()
    entry = QLineEdit(str(init_val), integer_widget)
    entry.setFont(QFont(Df.DEFAULT_FONT, 12))
    entry.setValidator(QIntValidator(min_val, max_val, entry))
    entry.setStyleSheet(
        """
        QLineEdit{
            background-color: #161613;
            border: solid;
            border-width: 3px;
            border-color: #161613;
            color: #727463;
        }"""
    )
    layout.addWidget(entry, alignment=Qt.AlignmentFlag.AlignRight)
    integer_widget.setLayout(layout)
    return (integer_widget, entry)


def generate_float_widget(
    label_msg: str,
    tooltip_msg: str,
    init_val: float,
    min_val: float,
    max_val: float,
    parent: QWidget,
) -> Tuple[QWidget, QLineEdit]:
    """Creates a GUI form for transformation option float entry, displaying a
    left-justified label next to a right-justified entry that only accepts valid
    float value inputs.

    Args:
        label_msg (str): The text message to label the float entry with.
        tooltip_msg (str): The text message to display as a tooltip on the label.
        init_val (float): The initial float value used to occupy the entry.
        min_val (float): The minimum allowed float value to enter into the entry.
        max_val (float): The maximum allowed float value to enter into the entry.
        parent (QWidget): The parent widget that this widget will be placed in.

    Returns:
        Tuple[QWidget, QLineEdit]: Returns a tuple, where the first item is the
        created widget, and the second is the exact entry UI element to allow
        you to access a user-entered value.
    """
    float_widget = QWidget(parent)
    layout = QHBoxLayout(float_widget)
    layout.setContentsMargins(0, 0, 0, 0)
    label = QLabel(label_msg, float_widget)
    label.setFont(QFont(Df.DEFAULT_FONT, 12))
    label.setToolTip(tooltip_msg)
    QToolTip.setFont(QFont(Df.DEFAULT_FONT, 13))
    label.setStyleSheet("QLabel{color: #727463;}\n" + Df.GENERAL_TOOLTIP_CSS)
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignLeft)
    layout.addStretch()
    entry = QLineEdit(str(init_val), float_widget)
    entry.setFont(QFont(Df.DEFAULT_FONT, 12))
    entry.setValidator(QDoubleValidator(min_val, max_val, 1000, entry))
    entry.setStyleSheet(
        """
        QLineEdit{
            background-color: #161613;
            border: solid;
            border-width: 3px;
            border-color: #161613;
            color: #727463;
        }"""
    )
    layout.addWidget(entry, alignment=Qt.AlignmentFlag.AlignRight)
    float_widget.setLayout(layout)
    return (float_widget, entry)


def generate_radio_button_widget(
    label_msg: str,
    tooltip_msg: str,
    options: Mapping[str, Any],
    init_val: str,
    parent: QWidget,
    option_tooltips: Optional[Mapping[str, str]] = None,
) -> Tuple[QWidget, dict[QRadioButton, Any]]:
    """Creates a GUI form for radio button UI elements that allow the mutually
    exclusive selection of an option from some set of options. A name label is
    displayed above the set of optiosn, and each individual radio button has
    its own option label describing what the option is.

    Args:
        label_msg (str): The text message to label the entire selection with.
        tooltip_msg (str): The text message to display as a tooltip on the top label.
        options (Mapping[str, Any]): The set of possible radio button options, mapping
        their string label to some value that they should be used to represent.
        init_val (str): The initial string name of the option that should be selected.
        parent (QWidget): The parent widget that this widget will be placed in.

    Returns:
        Tuple[QWidget, dict[QRadioButton, Any]]: Returns a tuple, where the first item
        is the created widget, and the second is a dictionary of created radio buttons 
        which can be checked to determine the user input value.
    """
    if option_tooltips is None:
        option_tooltips = {}
    radio_widget = QWidget(parent)
    layout = QVBoxLayout(radio_widget)
    layout.setSpacing(0)
    layout.setContentsMargins(0, 0, 0, 0)
    label = QLabel(label_msg, radio_widget)
    label.setFont(QFont(Df.DEFAULT_FONT, 12))
    label.setToolTip(tooltip_msg)
    QToolTip.setFont(QFont(Df.DEFAULT_FONT, 13))
    label.setStyleSheet("QLabel{color: #727463;}\n" + Df.GENERAL_TOOLTIP_CSS)
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignLeft)
    button_widget = QWidget(radio_widget)
    button_layout = QVBoxLayout(button_widget)
    button_layout.setContentsMargins(15, 5, 5, 5)
    radio_buttons = {}
    for option in options.keys():
        radio_button = QRadioButton(option, radio_widget)
        if option == init_val:
            radio_button.setChecked(True)
        if option in option_tooltips:
            radio_button.setToolTip(option_tooltips[option])
        radio_button.setFont(QFont(Df.DEFAULT_FONT, 11))
        radio_button.setStyleSheet(
            Df.GENERAL_TOOLTIP_CSS
            + """
            QRadioButton{
                color: #727463;
            }
            QRadioButton::indicator{
                width: 10px;
                height: 10px;
                border-radius: 7px;
            }
            QRadioButton::indicator::checked{
                background-color: none;
                border: 2px solid white;
            }
            QRadioButton::indicator::unchecked{
                background-color: white;
                border: 2px solid white;
            }"""
        )
        button_layout.addWidget(radio_button, 1)
        radio_buttons[radio_button] = options[option]
    button_widget.setLayout(button_layout)
    layout.addWidget(button_widget)
    radio_widget.setLayout(layout)
    return (radio_widget, radio_buttons)


def generate_checkbox_widget(
    label_msg: str, tooltip_msg: str, init: bool, parent: QWidget
) -> Tuple[QWidget, QCheckBox]:
    """Creates a GUI form for transformation option checkbox entry, displaying
    a left-justified label next to some binary checkbox that can be freely checked
    or unchecked by users.

    Args:
        label_msg (str): The text message to label the checkbox with.
        tooltip_msg (str): The text message to display as a tooltip on the label
        and checkbox.
        init (bool): Whether the checkbox should initially be checked or not.
        parent (QWidget): The parent widget that this widget will be placed in.

    Returns:
        Tuple[QWidget, QCheckBox]: Returns a tuple, where the first item is the
        created widget, and the second is the exact checkbox UI element to allow
        you to access a user-entered value.
    """
    checkbox_widget = QWidget(parent)
    layout = QHBoxLayout(checkbox_widget)
    layout.setSpacing(20)
    layout.setContentsMargins(0, 0, 0, 0)
    label = QLabel(label_msg, checkbox_widget)
    label.setFont(QFont(Df.DEFAULT_FONT, 12))
    label.setToolTip(tooltip_msg)
    QToolTip.setFont(QFont(Df.DEFAULT_FONT, 13))
    label.setStyleSheet("QLabel{color: #727463;}\n" + Df.GENERAL_TOOLTIP_CSS)
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
    checkbox = QCheckBox(checkbox_widget)
    checkbox.setFont(QFont(Df.DEFAULT_FONT, 12))
    checkbox.setStyleSheet(
        """
        QCheckBox{
            color: #727463
        }"""
    )
    checkbox.setChecked(init)
    layout.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
    checkbox_widget.setLayout(layout)
    return (checkbox_widget, checkbox)


def generate_checkboxes_widget(
    label_msg: str,
    tooltip_msg: str,
    options: Mapping[str, Any],
    init_vals: Iterable[str],
    parent: QWidget,
    option_tooltips: Mapping[str, str] | None = None,
) -> Tuple[QWidget, dict[QCheckBox, Any]]:
    """Creates a GUI form for a grouped set of checkbox entries for a transformation
    option, to allow users to select any subset of options from a specific set, as
    each option can be freely checked or unchecked by users (unlike radio buttons).

    Args:
        label_msg (str): The text message to label the entire selection with.
        tooltip_msg (str): The text message to display as a tooltip on the top label.
        options (Mapping[str, Any]): The set of possible checkbox options, mapping
        their string label to some value that they should be used to represent.
        init_vals (Iterable[str]): The set of string labels that should be used as
        checkboxes in the selection.
        parent (QWidget): The parent widget that this widget will be placed in.
        option_tooltips (Mapping[str, str] | None): An optional argument allowing
        tooltips to be assigned to each individual checkbox label. Defaults to None.

    Returns:
        Tuple[QWidget, dict[QCheckbox, Any]]: Returns a tuple, where the first item
        is the created widget, and the second is a dictionary of created checkboxes 
        which can be checked to determine the user input option subset.
    """
    labelled_widget = QWidget(parent)
    layout = QVBoxLayout(labelled_widget)
    layout.setSpacing(0)
    layout.setContentsMargins(0, 0, 0, 0)
    label = QLabel(label_msg, labelled_widget)
    label.setFont(QFont(Df.DEFAULT_FONT, 12))
    label.setToolTip(tooltip_msg)
    QToolTip.setFont(QFont(Df.DEFAULT_FONT, 13))
    label.setStyleSheet("QLabel{color: #727463;}\n" + Df.GENERAL_TOOLTIP_CSS)
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignLeft)
    checkbox_widget = QWidget(labelled_widget)
    checkbox_layout = QVBoxLayout(checkbox_widget)
    checkbox_layout.setContentsMargins(15, 5, 5, 5)
    checkbox_layout.setSpacing(0)
    checkboxes = {}
    for option in options.keys():
        checkbox = QCheckBox(option, checkbox_widget)
        checkbox.setFont(QFont(Df.DEFAULT_FONT, 11))
        checkbox.setStyleSheet(
            Df.GENERAL_TOOLTIP_CSS
            + """
            QCheckBox{
                color: #727463
            }"""
        )
        checkbox.setChecked(option in init_vals or options[option] in init_vals)
        if option_tooltips is not None and option in option_tooltips:
            checkbox.setToolTip(option_tooltips[option])
        checkbox_layout.addWidget(checkbox, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        checkboxes[checkbox] = options[option]
    checkbox_widget.setLayout(checkbox_layout)
    layout.addWidget(checkbox_widget)
    labelled_widget.setLayout(layout)
    return (labelled_widget, checkboxes)


class GuiIdentityUnit(IdentityUnit):
    """The identity transformation with added graphical interfaces."""

    def edit_gui(self, parent: QWidget) -> None:
        """Implements a graphical interface for editing an identity transformation.

        Args:
            parent (QWidget): The parent widget to place this widget into.
        """
        set_no_options_widget(parent)

    def load_gui_values(self) -> None:
        """Loads the user options from relevant UI elements into the actual identity
        unit. In this case, no such options exist."""
        return

    def from_json(json_str: str) -> "GuiIdentityUnit":
        """Loads the GUI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the GuiIdentityUnit.

        Returns:
            GuiIdentityUnit: The corresponding GuiIdentityUnit object."""
        return GuiIdentityUnit()

    def get_gui() -> "GuiIdentityUnit":
        """Creates an identity transformation loaded with default values to allow GUI
        interaction with the transformation.

        Returns:
            GuiIdentityUnit: the identity unit transformation with default values."""
        return GuiIdentityUnit()


class GuiFuncArgumentRandomiseUnit(FuncArgumentRandomiseUnit):
    """The function argument randomisation transformation with added graphical interfaces."""

    def __init__(self, *args, **kwargs):
        """The constructor for the GuiFuncArgumentRandomiseUnit, extending the original
        transformation unit to also initialise entries and checkbox attributes.
        """
        super(GuiFuncArgumentRandomiseUnit, self).__init__(*args, **kwargs)
        self.extra_args_entry = None
        self.probability_entry = None
        self.randomise_checkbox = None

    def edit_gui(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)

        # Add an integer entry for the number of extra arguments
        extra_args, self.extra_args_entry = generate_integer_widget(
            "Extra Args:",
            "The number of additional spurious arguments to add to each function.\n"
            "This must be an integer >= 0. If 0 is selected, then the argument\n"
            "list will just be randomised but not otherwise modified.",
            self.extra_args,
            0,
            2147483647,
            parent,
        )
        layout.addWidget(extra_args, 1, alignment=Qt.AlignmentFlag.AlignTop)

        # Add a float entry for the probability of using existing variables
        probability, self.probability_entry = generate_float_widget(
            "Probability:",
            "The probability that a function argument, linked to an extra spurious parameter\n"
            "that has been added to a function's specification, will be filled using some\n"
            "matching variable value from the program instead of some new constant value,\n"
            "where this pr obability must be  anumber in the range 0 <= p <= 1. A probability\n"
            "of 0 means all spurious arguments will be constants (less secure), a probability of\n"
            "0.5 means a 50 percent chance of using a variable where a variable can be used, and\n"
            "a 1.0 means that all spurious arguments will use defined variables were possible.\n"
            " This allows you to achieve a mixture of constants and variables for security.",
            self.probability,
            0.0,
            1.0,
            parent,
        )
        layout.addWidget(probability, alignment=Qt.AlignmentFlag.AlignTop)

        # Add a checkbox for randomising the order of function arguments.
        randomise, self.randomise_checkbox = generate_checkbox_widget(
            "Randomise Arg Order?",
            "Where possible, randomises the order of arguments in function definitions and calls such\n"
            "that any abstract symbolic meaning implied by their order is lost. This is particularly\n"
            "effective when combined with several additional new arguments, as it can cause the real\n"
            "arguments to become lost. When combined with opaque predicate insertion/augmentation,\n"
            "these fake arguments cannot be automatically removed using their usage information,\n"
            "creating a very effective obfuscation tool.",
            self.randomise,
            parent,
        )
        layout.addWidget(randomise, 1, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addStretch(3)
        parent.setLayout(layout)

    def load_gui_values(self) -> None:
        """Loads the user options from relevant UI elements into the actual function
        argument randomisation unit. In this case, we load the number of extra
        arguments, the probability, and whether to randomise the order or not."""
        # Load the number of extra arguments (>= 0, default 3)
        if self.extra_args_entry is not None:
            try:
                self.extra_args = int(self.extra_args_entry.text())
                if self.extra_args < 0:
                    self.extra_args = 0
                self.traverser.extra = self.extra_args
            except:
                self.extra_args = 3
                self.traverser.extra = 3
        # Load the probability (0.0 <= p <= 1.0, default 0.75)
        if self.probability_entry is not None:
            try:
                self.probability = float(self.probability_entry.text())
                if self.probability > 1.0:
                    self.probability = 1.0
                elif self.probability < 0.0:
                    self.probability = 0.0
                self.traverser.variable_probability = self.probability
            except:
                self.probability = 0.75
                self.traverser.variable_probability = self.probability
        # Load whether to randomise or not.
        if self.randomise_checkbox is not None:
            self.randomise = self.randomise_checkbox.isChecked()
            self.traverser.randomise = self.randomise

    def from_json(json_str: str) -> "GuiFuncArgumentRandomiseUnit":
        """Loads the GUI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the GuiFuncArgumentRandomiseUnit.

        Returns:
            GuiFuncArgumentRandomiseUnit: The corresponding GuiFuncArgumentRandomiseUnit object."""
        unit = FuncArgumentRandomiseUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiFuncArgumentRandomiseUnit(
            unit.extra_args, unit.probability, unit.randomise
        )

    def get_gui() -> "GuiFuncArgumentRandomiseUnit":
        """Creates a function argument randomisation transformation loaded with default
        values to allow GUI interaction with the transformation.

        Returns:
            GuiFuncArgumentRandomiseUnit: the function argument randomisation transformation
            with default values."""
        return GuiFuncArgumentRandomiseUnit(3, 0.75, True)


class GuiStringEncodeUnit(StringEncodeUnit):
    """The string literal encoding transformation with added graphical interfaces."""

    def __init__(self, *args, **kwargs):
        """The constructor for the GuiStringEncodeUnit, extending the original
        transformation unit to also initialise attributes for the style buttons.
        """
        super(GuiStringEncodeUnit, self).__init__(*args, **kwargs)
        self.style_buttons = None

    def edit_gui(self, parent: QWidget) -> None:
        """Implements a graphical interface for editing a string encoding transformation.

        Args:
            parent (QWidget): The parent widget to place this widget into.
        """
        layout = QVBoxLayout(parent)
        # Add radio buttons for selecting the string encoding style
        style, self.style_buttons = generate_radio_button_widget(
            "Encoding Style:",
            "The encoding style to use when encoding strings in the program, which\n"
            "dictates how it is chosen what encodings characters are replaced with.",
            {style.value: style for style in StringEncodeTraverser.Style},
            self.style.value,
            parent,
            {
                StringEncodeTraverser.Style.OCTAL.value: "Encode each character as its octal (base-8) representation where possible.\n"
                '  e.g. "hello" -> "\\150\\145\\154\\154\\157".',
                StringEncodeTraverser.Style.HEX.value: "Encode each character as its hexadecimal (base-16) representation where possbible.\n"
                '  e.g. "hello" -> "\\x68\\x65\\x6c\\x6c\\x6f".',
                StringEncodeTraverser.Style.MIXED.value: "Encode each character as either its octal (base-8) or hexadecimal (base-16)\n"
                "representation where possible, choosing randomly between the two.\n"
                '  e.g. "hello" -> "\\x68\\145\\154\\x6c\\157".',
                StringEncodeTraverser.Style.ALL.value: "Encode each character as either itself (no change), its octal (base-8) representation\n"
                "or its hexadecimal (base-16) representation, choosing randomly between all 3 options.\n"
                '  e.g. "hello" -> "\\150e\\x6cl\\x6f".',
            },
        )
        layout.addWidget(style, 1, alignment=Qt.AlignmentFlag.AlignTop)
        parent.setLayout(layout)

    def load_gui_values(self) -> None:
        """Loads the user options from relevant UI elements into the actual string
        encoding unit. In this case, we load the encoding style only."""
        if self.style_buttons is not None and len(self.style_buttons) > 0:
            for button, style in self.style_buttons.items():
                if button.isChecked():
                    self.style = style
                    self.traverser.style = style
                    break

    def from_json(json_str: str) -> "GuiStringEncodeUnit":
        """Loads the GUI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the GuiStringEncodeUnit.

        Returns:
            GuiStringEncodeUnit: The corresponding GuiStringEncodeUnit object."""
        unit = StringEncodeUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiStringEncodeUnit(unit.style)

    def get_gui() -> "GuiStringEncodeUnit":
        """Creates a string encoding transformation loaded with default values to allow
        GUI interaction with the transformation.

        Returns:
            GuiStringEncodeUnit: the string encoding transformation with default values."""
        return GuiStringEncodeUnit(StringEncodeTraverser.Style.MIXED)


class GuiIntegerEncodeUnit(IntegerEncodeUnit):
    """The integer literal encoding transformation with added graphical interfaces."""

    def edit_gui(self, parent: QWidget) -> None:
        """Implements a graphical interface for editing an integer encoding transformation.

        Args:
            parent (QWidget): The parent widget to place this widget into.
        """
        set_no_options_widget(parent)

    def load_gui_values(self) -> None:
        """Loads the user options from relevant UI elements into the actual integer
        encoding transformation unit. In this case, no such options exist."""
        return

    def from_json(json_str: str) -> "GuiIntegerEncodeUnit":
        """Loads the GUI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the GuiIntegerEncodeUnit.

        Returns:
            GuiIntegerEncodeUnit: The corresponding GuiIntegerEncodeUnit object."""
        unit = IntegerEncodeUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiIntegerEncodeUnit()

    def get_gui() -> "GuiIntegerEncodeUnit":
        """Creates an integer encoding transformation loaded with default values to allow
        GUI interaction with the transformation.

        Returns:
            GuiIntegerEncodeUnit: the integer encoding transformation with default values."""
        return GuiIntegerEncodeUnit()


class GuiIdentifierRenameUnit(IdentifierRenameUnit):
    """The identifier renaming transformation with added graphical interfaces."""

    def __init__(self, *args, **kwargs):
        """The constructor for the GuiIdentifierRenameUnit, extending the original
        transformation unit to also initialise attributes for the style buttons and
        a checkbox for minimising identifier usage.
        """
        super(GuiIdentifierRenameUnit, self).__init__(*args, **kwargs)
        self.style_buttons = None
        self.minimise_idents_checkbox = None

    def edit_gui(self, parent: QWidget) -> None:
        """Implements a graphical interface for editing an identifier renaming transformation.

        Args:
            parent (QWidget): The parent widget to place this widget into.
        """
        layout = QVBoxLayout(parent)

        # Add radio buttons for selecting the name generation style
        style, self.style_buttons = generate_radio_button_widget(
            "Renaming Style:",
            "The renaming style to use when renaming identifiers throughout the\n"
            "program, which dictates how new identifiers are chosen to replace\n"
            "existing names.",
            {style.value: style for style in IdentifierRenameUnit.Style},
            self.style.value,
            parent,
            {
                IdentifierRenameUnit.Style.COMPLETE_RANDOM.value: "Generate new identifiers that are completely random strings of 4-19 characters.\n"
                "  e.g. tcEM7, aA_LsaUdhnh, YPWnW0XE.",
                IdentifierRenameUnit.Style.ONLY_UNDERSCORES.value: "Generate new identifiers that consist of solely the underscore character '_'.\n"
                "  e.g. _, _____, ________.",
                IdentifierRenameUnit.Style.MINIMAL_LENGTH.value: "Generate new identifiers that occupy the minimum space possible as a whole, by\n"
                "iterating through available symbols sequentially.\n"
                "  e.g. a, b, c, d, e, ...",
                IdentifierRenameUnit.Style.I_AND_L.value: "Generate new identifiers that each comprise of the exact same amount of characters,\n"
                "using random combinations of only the characters 'I' and 'l'. This makes it hard to\n"
                "determine separate identifiers via. differences in length, as in e.g. underscore\n"
                "renaming.\n"
                "  e.g. IllIIlIIlIlIIlll, llIIlIlIlllllIlI, lIIlllIllIIIIIII.",
            },
        )
        layout.addWidget(style, 1, alignment=Qt.AlignmentFlag.AlignTop)

        # Add a checkbox for minimising identifier usage or not.
        minimise_idents, self.minimise_idents_checkbox = generate_checkbox_widget(
            "Minimise Identifiers?",
            "Attempts to greedily re-use identifier names whenever possible, such that the minimum\n"
            "number of unique names are used throughout the program, and the maximum number of\n"
            "different programming constructs are named the same thing. This option exploits variable\n"
            "shadowing within scopes, the different naming systems of labels/structures and other\n"
            "constructs, and analysis of identifier usage and liveness. [WARNING: VERY EXPERIMENTAL].",
            self.minimise_idents,
            parent,
        )
        layout.addWidget(minimise_idents, 1, alignment=Qt.AlignmentFlag.AlignTop)
        parent.setLayout(layout)

    def load_gui_values(self) -> None:
        """Loads the user options from relevant UI elements into the actual identifier
        renaming unit. In this case, we load the name generation style and whether to
        use minimial identifiers or not."""
        # Load the name generation style
        if self.style_buttons is not None and len(self.style_buttons) > 0:
            for button, style in self.style_buttons.items():
                if button.isChecked():
                    self.style = style
                    break
        # Load whether to minimise identifier usage or not
        if self.minimise_idents_checkbox is not None:
            self.minimise_idents = self.minimise_idents_checkbox.isChecked()

    def from_json(json_str: str) -> "GuiIdentifierRenameUnit":
        """Loads the GUI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the GuiIdentifierRenameUnit.

        Returns:
            GuiIdentifierRenameUnit: The corresponding GuiIdentifierRenameUnit object."""
        unit = IdentifierRenameUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiIdentifierRenameUnit(unit.style, unit.minimise_idents)

    def get_gui() -> "GuiIdentifierRenameUnit":
        """Creates an identifier renaming transformation loaded with default values to allow
        GUI interaction with the transformation.

        Returns:
            GuiIdentifierRenameUnit: the identifier renaming transformation with default values."""
        return GuiIdentifierRenameUnit(
            IdentifierRenameUnit.Style.COMPLETE_RANDOM, False
        )


class GuiArithmeticEncodeUnit(ArithmeticEncodeUnit):
    """The integer arithmetic encoding transformation with added graphical interfaces."""

    def __init__(self, *args, **kwargs):
        """The constructor for the GuiArithmeticEncodeUnit, extending the original
        transformation unit to also initialise attributes for the encoding depth entry.
        """
        super(GuiArithmeticEncodeUnit, self).__init__(*args, **kwargs)
        self.depth_entry = None

    def edit_gui(self, parent: QWidget) -> None:
        """Implements a graphical interface for editing an arithmetic encoding transformation.

        Args:
            parent (QWidget): The parent widget to place this widget into.
        """
        layout = QVBoxLayout(parent)

        # Add an integer entry for inputting the recursive depth.
        depth, self.depth_entry = generate_integer_widget(
            "Recursive Depth:",
            "The maximum recursive depth of performed arithmetic encoding. Arithmetic\n"
            "operations within encoded arithmetic operations can be recursively encoded\n"
            "to increase code complexity. This must be at least 0 (which does nothing),\n"
            "but a value > 5 is not recommended due to the large potential slowdown, as\n"
            "code exponentially increases in size.",
            self.level,
            0,
            2147483647,
            parent,
        )
        layout.addWidget(depth, 1, alignment=Qt.AlignmentFlag.AlignTop)
        parent.setLayout(layout)

    def load_gui_values(self) -> None:
        """Loads the user options from relevant UI elements into the actual arithmetic
        encoding unit. In this case, we load the recursive encoding depth."""
        # Load the encoding depth (>= 0, default 1)
        if self.depth_entry is not None:
            try:
                self.level = int(self.depth_entry.text())
                if self.level < 0:
                    self.level = 0
                self.traverser.transform_depth = self.level
            except:
                self.level = 1
                self.traverser.transform_depth = 1

    def from_json(json_str: str) -> None:
        """Loads the GUI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the GuiArithmeticEncodeUnit.

        Returns:
            GuiArithmeticEncodeUnit: The corresponding GuiArithmeticEncodeUnit object."""
        unit = ArithmeticEncodeUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiArithmeticEncodeUnit(unit.level)

    def get_gui() -> "GuiArithmeticEncodeUnit":
        """Creates an integer arithmetic encoding transformation loaded with default values
        to allow GUI interaction with the transformation.

        Returns:
            GuiArithmeticEncodeUnit: the arithmetic encoding transformation with default values."""
        return GuiArithmeticEncodeUnit(1)


class GuiAugmentOpaqueUnit(AugmentOpaqueUnit):
    """The opaque augmentation transformation with added graphical interfaces."""

    def __init__(self, *args, **kwargs):
        """The constructor for the GuiAugmentOpaqueUnit, extending the original
        transformation unit to also initialise attributes for the style checkboxes,
        and the probability and number entries.
        """
        super(GuiAugmentOpaqueUnit, self).__init__(*args, **kwargs)
        self.style_checkboxes = None
        self.probability_entry = None
        self.number_entry = None

    def edit_gui(self, parent: QWidget) -> None:
        """Implements a graphical interface for editing an opaque predicate augmentation
        transformation.

        Args:
            parent (QWidget): The parent widget to place this widget into.
        """
        layout = QVBoxLayout(parent)

        # Add checkboxes for selecting opaque predicate argument generation styles
        tooltips = {
            OpaqueAugmenter.Style.INPUT.value: "Opaque predicates can be generated using user inputs (function parameters).",
            OpaqueAugmenter.Style.ENTROPY.value: "Opaque predicates can be generated using entropic (random) variables, which\n"
            "are created globally and initialised with random values at the start of the\n"
            "main() function. In the current implementation, for every random variable\n"
            "that is needed, it is decided at random whether to use an existing variable\n"
            "or to make a new one (25 percent chance), to create good diversity and increase\n"
            "complexity throughout the program.",
        }
        styles, self.style_checkboxes = generate_checkboxes_widget(
            "Predicate Style:",
            "The opaque predicate generation styles that can be used by the program.\n"
            "This simply refers to the types of inputs that can be utilised to make\n"
            "opaque predicates, such as using user input (function parameters) or\n"
            "using random variables (entropy).",
            {
                " ".join(style.value.split(" ")[3:]).capitalize(): style
                for style in OpaqueAugmenter.Style
            },
            set(self.styles),
            parent,
            dict(
                (" ".join(key.split(" ")[3:]).capitalize(), val)
                for key, val in tooltips.items()
            ),
        )
        layout.addWidget(styles, alignment=Qt.AlignmentFlag.AlignTop)

        # Add a float entry for selecting the probability of augmenting conditionals
        probability, self.probability_entry = generate_float_widget(
            "Probability:",
            "The probability that a conditional will be augmented with an opaque predicate,\n"
            "which must be a number in the range 0 <= p <= 1. A probability of 0 means that\n"
            "no augmentations will occur, a probability of 0.5 means approximately half of\n"
            "the program's conditionals will be augmented with opaque predicates, and 1.0\n"
            "means that where possible, all conditionals will be augmented. This allows you\n"
            "to achieve a mixture of augmented and non-augmented conditionals.",
            self.probability,
            0.0,
            1.0,
            parent,
        )
        layout.addWidget(probability, alignment=Qt.AlignmentFlag.AlignTop)

        # Add an integer entry for selecting the number of predicates to add
        number, self.number_entry = generate_integer_widget(
            "Number of predicates:",
            "The number of opaque predicates that will be used to augment any probabilistically\n"
            "selected conditional statement, which must be some integer >= 0. A number of 0\n"
            "means that no opaque predicates will be added. A number of 5 means that 5 opaque\n"
            "predicates will be used to augment each chosen conditional.\n"
            "Typically, n=1 is sufficient for most use cases.",
            self.number,
            0,
            2147483647,
            parent,
        )
        layout.addWidget(number, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addStretch()
        parent.setLayout(layout)

    def load_gui_values(self) -> None:
        """Loads the user options from relevant UI elements into the actual opaque
        predicate augmentation unit. In this case, we load the valid predicate argument
        generation styles, the probabiltiy of augmenting existing conditionals, and
        the number of opaque predicates to augment each conditional with."""
        # Load the set of selected valid predicate argument styles.
        if self.style_checkboxes is not None and len(self.style_checkboxes) > 0:
            self.styles = [
                s for cbox, s in self.style_checkboxes.items() if cbox.isChecked()
            ]
            self.traverser.styles = self.styles
        # Load the augmenting probability (0.0 <= p <= 1.0, default 0.75)
        if self.probability_entry is not None:
            try:
                self.probability = float(self.probability_entry.text())
                if self.probability > 1.0:
                    self.probability = 1.0
                elif self.probability < 0.0:
                    self.probability = 0.0
                self.traverser.probability = self.probability
            except:
                self.probability = 0.75
                self.traverser.probability = self.probability
        # Load the number of predicates to add per conditional (>= 0, default 1)
        if self.number_entry is not None:
            try:
                self.number = int(self.number_entry.text())
                if self.number < 0:
                    self.number = 0
                self.traverser.number = self.number
            except:
                self.number = 1
                self.traverser.number = 1

    def from_json(json_str: str) -> "GuiAugmentOpaqueUnit":
        """Loads the GUI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the GuiAugmentOpaqueUnit.

        Returns:
            GuiAugmentOpaqueUnit: The corresponding GuiAugmentOpaqueUnit object."""
        unit = AugmentOpaqueUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiAugmentOpaqueUnit(unit.styles, unit.probability, unit.number)

    def get_gui() -> "GuiAugmentOpaqueUnit":
        """Creates an opaque predicate augmentation transformation loaded with default
        values to allow GUI interaction with the transformation.

        Returns:
            GuiAugmentOpaqueUnit: the opaque predicate augmentation transformation with
            default values."""
        return GuiAugmentOpaqueUnit([s for s in OpaqueAugmenter.Style], 1.0, 1)


class GuiInsertOpaqueUnit(InsertOpaqueUnit):
    """The opaque insertion transformation with added graphical interfaces."""

    def __init__(self, *args, **kwargs):
        """The constructor for the GuiInsertOpaqueUnit, extending the original
        transformation unit to also initialise attributes for the style, granularity
        and kind checkboxes, as well as an entry for the number of insertions.
        """
        super(GuiInsertOpaqueUnit, self).__init__(*args, **kwargs)
        self.style_checkboxes = None
        self.granularity_checkboxes = None
        self.kind_checkboxes = None
        self.number_entry = None

    def edit_gui(self, parent: QWidget) -> None:
        """Implements a graphical interface for editing an opaque predicate
        insertion transformation.

        Args:
            parent (QWidget): The parent widget to place this widget into.
        """
        # Initialise the layout design to allow scrolling, as there are a lot of options.
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 10, 0, 10)
        scroll_widget = QScrollArea(parent)
        scroll_widget.setStyleSheet(
            """
            QScrollArea{
                background-color: transparent;
                border: none;
            }"""
            + Df.MINIMAL_SCROLL_BAR_CSS
        )
        scroll_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll_widget.setWidgetResizable(True)
        scroll_content = QWidget(scroll_widget)
        scroll_content.setObjectName("ScrollWidget")
        scroll_content.setStyleSheet(
            """
            QWidget#ScrollWidget{
                background-color: transparent;
                border: none;
            }"""
        )
        scroll_content.layout = QVBoxLayout(scroll_content)
        scroll_content.layout.setContentsMargins(0, 0, 7, 0)
        scroll_content.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum
        )
        scroll_widget.setWidget(scroll_content)
        layout.addWidget(scroll_widget)

        # Add a set of checkboxes for selecting opaque predicate argument generation styles
        tooltips = {
            OpaqueAugmenter.Style.INPUT.value: "Opaque predicates can be generated using user inputs (function parameters).",
            OpaqueAugmenter.Style.ENTROPY.value: "Opaque predicates can be generated using entropic (random) variables, which\n"
            "are created globally and initialised with random values at the start of the\n"
            "main() function. In the current implementation, for every random variable\n"
            "that is needed, it is decided at random whether to use an existing variable\n"
            "or to make a new one (25 percent chance), to create good diversity and increase\n"
            "complexity throughout the program.",
        }
        styles, self.style_checkboxes = generate_checkboxes_widget(
            "Predicate Style:",
            "The opaque predicate generation styles that can be used by the program.\n"
            "This simply refers to the types of inputs that can be utilised to make\n"
            "opaque predicates, such as using user input (function parameters) or\n"
            "using random variables (entropy).",
            {
                " ".join(style.value.split(" ")[3:]).capitalize(): style
                for style in OpaqueInserter.Style
            },
            set(self.styles),
            parent,
            dict(
                (" ".join(key.split(" ")[3:]).capitalize(), val)
                for key, val in tooltips.items()
            ),
        )
        scroll_content.layout.addWidget(styles, alignment=Qt.AlignmentFlag.AlignTop)

        # Add a set of checkboxes for selecing insertion granularities
        granularities, self.granularity_checkboxes = generate_checkboxes_widget(
            "Predicate Granularities:",
            "Opaque predicate granularities refer to the 'scope'/'size' of the program components\n"
            "that are modified by the new conditional. For example, we can have conditionals that\n"
            "apply to an entire function body (procedural granularity), conditionals that apply to\n"
            "a contiguous sequence of multiple statements (block granularity), or new conditionals\n"
            "that apply to singular program statements (statement granularity). Selecting a mixture\n"
            "of these allows you to greatly increase program diversity.",
            {g.value.split(":")[0].capitalize(): g for g in OpaqueInserter.Granularity},
            set(self.granularities),
            parent,
            {
                OpaqueInserter.Granularity.PROCEDURAL.value.split(":")[
                    0
                ].capitalize(): "Generate new opaque predicate conditionals that encapsulate the entire\n"
                "function body.",
                OpaqueInserter.Granularity.BLOCK.value.split(":")[
                    0
                ].capitalize(): "Generate new opaque predicate conditionals that encapsulate contiguous\n"
                "sequences of statements (i.e. 'blocks' of code) within the function. These\n"
                "blocks are chosen entirely at random, and are of random length.",
                OpaqueInserter.Granularity.STMT.value.split(":")[
                    0
                ].capitalize(): "Generate new opaque predicate conditionals that encapsulate singular\n"
                "program statements within the function. These statements are chosen entirely\n"
                "at random from those within the function body.",
            },
        )
        scroll_content.layout.addWidget(
            granularities, alignment=Qt.AlignmentFlag.AlignTop
        )

        # Add a set of checkboxes for selecting insertion kinds/formats/structures
        kinds, self.kind_checkboxes = generate_checkboxes_widget(
            "Predicate Kinds:",
            "The kinds (formats) of opaque predicate conditionals that will be inserted. This\n"
            "increases obfuscation diversity by inserting opaque predicates using different\n"
            "programming constructs and logical structures. For example, one kind might evaluate\n"
            "the real code on an else branch of an if statement, whereas another might evaluate\n"
            "buggy code within a while loop.",
            {
                k.value.split(":")[0].replace("_", " ").capitalize(): k
                for k in OpaqueInserter.Kind
            },
            set(self.kinds),
            parent,
            dict(
                (
                    k.value.split(":")[0].replace("_", " ").capitalize(),
                    "Enable construction of opaque predicate conditionals with the form\n"
                    "  " + k.value.split(":")[1].strip(),
                )
                for k in OpaqueInserter.Kind
            ),
        )
        scroll_content.layout.addWidget(kinds, alignment=Qt.AlignmentFlag.AlignTop)

        # Add an integer entry for selecting the number of conditionals to insert.
        number, self.number_entry = generate_integer_widget(
            "Number per function:",
            "The number of new opaque predicates to add to each individual function (where\n"
            "possible). Controlling this value allows you to control the degree to which the\n"
            "program is obfuscated. A value of 1 <= n <= 10 is recommended, though this\n"
            "depends on the kinds that you use, as some insertions can exponentially increase\n"
            "the program size (notably, the 'EITHER' predicate type applied with the\n"
            "'PROCEDURE' granularity will copy the function body each time it is applied\n"
            "(doubling the program size).",
            self.number,
            0,
            2147483647,
            parent,
        )
        scroll_content.layout.addWidget(number, alignment=Qt.AlignmentFlag.AlignTop)
        parent.setLayout(layout)

    def load_gui_values(self) -> None:
        """Loads the user options from relevant UI elements into the actual opaque
        predicate insertion unit. In this case, we load the valid predicate argument
        generation styles, the conditional insertion granularities, the conditional
        kinds/structures/formates, and the number of conditionals to attempt to add."""
        # Load the valid opaque predicate argument generation styles.
        if self.style_checkboxes is not None and len(self.style_checkboxes) > 0:
            self.styles = [
                s for cbox, s in self.style_checkboxes.items() if cbox.isChecked()
            ]
            self.traverser.styles = self.styles
        # Load the valid conditional insertion granularities
        if (
            self.granularity_checkboxes is not None
            and len(self.granularity_checkboxes) > 0
        ):
            self.granularities = [
                g for cbox, g in self.granularity_checkboxes.items() if cbox.isChecked()
            ]
            self.traverser.granularities = self.granularities
        # Load the vaid conditional kinds/formats/structures
        if self.kind_checkboxes is not None and len(self.kind_checkboxes) > 0:
            self.kinds = [
                k for cbox, k in self.kind_checkboxes.items() if cbox.isChecked()
            ]
            self.traverser.kinds = self.kinds
        # Load the number of insertions to attempt per function (>= 0, default 5)
        if self.number_entry is not None:
            try:
                self.number = int(self.number_entry.text())
                if self.number < 0:
                    self.number = 0
                self.traverser.number = self.number
            except:
                self.number = 5
                self.traverser.number = 5

    def from_json(json_str: str) -> "GuiInsertOpaqueUnit":
        """Loads the GUI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the GuiInsertOpaqueUnit.

        Returns:
            GuiInsertOpaqueUnit: The corresponding GuiInsertOpaqueUnit object."""
        unit = InsertOpaqueUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiInsertOpaqueUnit(
            unit.styles, unit.granularities, unit.kinds, unit.number
        )

    def get_gui() -> "GuiInsertOpaqueUnit":
        """Creates an opaque predicate insertion transformation loaded with default
        values to allow GUI interaction with the transformation.

        Returns:
            GuiInsertOpaqueUnit: the opaque predicate insertion transformation with
            default values."""
        return GuiInsertOpaqueUnit(
            [s for s in OpaqueInserter.Style],
            [g for g in OpaqueInserter.Granularity],
            [k for k in OpaqueInserter.Kind],
            5,
        )


class GuiControlFlowFlattenUnit(ControlFlowFlattenUnit):
    """The control flow flattening transformation with added graphical interfaces."""

    def __init__(self, *args, **kwargs):
        """The constructor for the GuiControlFlowFlattenUnit, extending the original
        transformation unit to also initialise attributes for the style buttons and
        a checkbox for case randomisation.
        """
        super(GuiControlFlowFlattenUnit, self).__init__(*args, **kwargs)
        self.style_buttons = None
        self.randomise_cases_checkbox = None

    def edit_gui(self, parent: QWidget) -> None:
        """Implements a graphical interface for editing a control flow flattening
        transformation.

        Args:
            parent (QWidget): The parent widget to place this widget into.
        """
        layout = QVBoxLayout(parent)

        # Add radio buttons for selecting the case generation style.
        style, self.style_buttons = generate_radio_button_widget(
            "Case Expression Style:",
            "The generation style to use when creating new cases for flattened\n"
            "blocks in the control flow flattening procedure, dictating how cases\n"
            "are labelled and transitioned between.",
            {style.value: style for style in ControlFlowFlattener.Style},
            self.style.value,
            parent,
            {
                ControlFlowFlattener.Style.SEQUENTIAL.value: "Generate new cases with sequentially generated integer expressions, e.g.\n"
                "  case 0: ...\n"
                "  case 1: ...\n"
                "  case 2: ...\n"
                "etc.",
                ControlFlowFlattener.Style.RANDOM_INT.value: "Generate new cases with random integer expressions, e.g.\n"
                "  case 12: ...\n"
                "  case 6: ...\n"
                "  case -37: ...\n"
                "etc.",
                ControlFlowFlattener.Style.ENUMERATOR.value: "Generate new cases as enumerator values, e.g.\n"
                "  enum x = {ABC, DEF, GHI}\n"
                "  switch (x) {\n"
                "    case ABC: ...\n"
                "    case DEF: ...\n"
                "    case GHI: ...\n"
                "  }\n"
                "etc.",
            },
        )
        layout.addWidget(style, 1, alignment=Qt.AlignmentFlag.AlignTop)

        # Add a checkbox for selecting whether to randomise the case order or not.
        randomise_cases, self.randomise_cases_checkbox = generate_checkbox_widget(
            "Randomise Case Order?",
            "Randomises the order within which cases are dispatched within switch statements during\n"
            "control flow flattening, such that it is more difficult to follow the code's original\n"
            "sequential structure by reading through cases sequentially.",
            self.randomise_cases,
            parent,
        )
        layout.addWidget(randomise_cases, 1, alignment=Qt.AlignmentFlag.AlignTop)
        parent.setLayout(layout)

    def load_gui_values(self) -> None:
        """Loads the user options from relevant UI elements into the actual control
        flow flattenign unit. In this case, we load the case generation style to
        be used, as well as whether to randomise the case order or not."""
        # Load the case generation style to use (selected via radio button)
        if self.style_buttons is not None and len(self.style_buttons) > 0:
            for button, style in self.style_buttons.items():
                if button.isChecked():
                    self.style = style
                    self.traverser.style = style
                    break
        # Load whether to randomise the order of cases or not.
        if self.randomise_cases_checkbox is not None:
            self.randomise_cases = self.randomise_cases_checkbox.isChecked()
            self.traverser.randomise_cases = self.randomise_cases

    def from_json(json_str: str) -> "GuiControlFlowFlattenUnit":
        """Loads the GUI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the GuiControlFlowFlattenUnit.

        Returns:
            GuiControlFlowFlattenUnit: The corresponding GuiControlFlowFlattenUnit object."""
        unit = ControlFlowFlattenUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiControlFlowFlattenUnit(unit.randomise_cases, unit.style)

    def get_gui() -> "GuiControlFlowFlattenUnit":
        """Creates a control flow flattening transformation loaded with default values
        to allow GUI interaction with the transformation.

        Returns:
            GuiControlFlowFlattenUnit: the control flow flattening transformation with
            default values."""
        return GuiControlFlowFlattenUnit(False, ControlFlowFlattener.Style.SEQUENTIAL)


class GuiReverseIndexUnit(ReverseIndexUnit):
    """The index reversing transformation with added graphical interfaces."""

    def __init__(self, *args, **kwargs):
        """The constructor for the GuiReverseIndexUnit, extending the original
        transformation unit to also initialise attributes for the probability entry.
        """
        super(GuiReverseIndexUnit, self).__init__(*args, **kwargs)
        self.probability_entry = None

    def edit_gui(self, parent: QWidget) -> None:
        """Implements a graphical interface for editing an array index reversal
        transformation.

        Args:
            parent (QWidget): The parent widget to place this widget into.
        """
        layout = QVBoxLayout(parent)

        # Add a float entry for entering the probability of reversing indexes.
        probability, self.probability_entry = generate_float_widget(
            "Probability:",
            "The probability that an index reversal will take place, which must be a number\n"
            "in the range 0 <= p <= 1. A probability of 0 means that no reversals will\n"
            "occur, a probability of 0.5 means approximately half of the indexing operations\n"
            "will be encoded, and 1.0 means all indexing operations are encoded. This allows\n"
            "you to achieve a mix of reversed and non-reversed indexes for maximal obfuscation.",
            self.probability,
            0.0,
            1.0,
            parent,
        )
        layout.addWidget(probability, 1, alignment=Qt.AlignmentFlag.AlignTop)
        parent.setLayout(layout)

    def load_gui_values(self) -> None:
        """Loads the user options from relevant UI elements into the actual array
        index reversal unit. In this case, we load the independent probability that
        an array index will be reversed."""
        # Load the reversal probability (0.0 <= p <= 1.0, default 0.8)
        if self.probability_entry is not None:
            try:
                self.probability = float(self.probability_entry.text())
                if self.probability > 1.0:
                    self.probability = 1.0
                elif self.probability < 0.0:
                    self.probability = 0.0
                self.traverser.probability = self.probability
            except:
                self.probability = 0.8
                self.traverser.probability = 0.8

    def from_json(json_str: str) -> "GuiReverseIndexUnit":
        """Loads the GUI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the GuiReverseIndexUnit.

        Returns:
            GuiReverseIndexUnit: The corresponding GuiReverseIndexUnit object."""
        unit = ReverseIndexUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiReverseIndexUnit(unit.probability)

    def get_gui() -> "GuiReverseIndexUnit":
        """Creates an array index reversal transformation loaded with default values to
        allow  GUI interaction with the transformation.

        Returns:
            GuiReverseIndexUnit: the index reversal transformation with default values."""
        return GuiReverseIndexUnit(0.8)


class GuiClutterWhitespaceUnit(ClutterWhitespaceUnit):
    """The whitespace cluttering transformation with added graphical interfaces."""

    def __init__(self, *args, **kwargs):
        """The constructor for the GuiClutterWhitespaceUnit, extending the original
        transformation unit to also initialise attributes for the target length
        entry, as well as a checkbox for padding lines.
        """
        super(GuiClutterWhitespaceUnit, self).__init__(*args, **kwargs)
        self.target_length_entry = None
        self.pad_lines_checkbox = None

    def edit_gui(self, parent: QWidget) -> None:
        """Implements a graphical interface for editing a whitespace cluttering
        transformation.

        Args:
            parent (QWidget): The parent widget to place this widget into.
        """
        layout = QVBoxLayout(parent)

        # Add an integer entry for the target positive line length to achieve.
        target_length, self.target_length_entry = generate_integer_widget(
            "Target Line Length:",
            "The target maximum line length to aim to achieve when altering whitespace.\n"
            "The line length will always be less than or equal to this, unless a single\n"
            "token is greater than this length (e.g. a very long variable name). If the\n"
            "padding option is set, this is the length that will be padded towards.",
            self.target_length,
            0,
            2147483647,
            parent,
        )
        layout.addWidget(target_length, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addSpacing(4)

        # Add a checkbox for whether to pad lines to achieve the target line length or not.
        pad_lines, self.pad_lines_checkbox = generate_checkbox_widget(
            "Add Line Padding?",
            "Where possible, this pads lines by inserting extra spaces between tokens, such that all\n"
            "lines (except those with pre-processor directives) are padded to the set target length.",
            self.pad_lines,
            parent,
        )
        layout.addWidget(pad_lines, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addStretch()
        parent.setLayout(layout)

    def load_gui_values(self) -> None:
        """Loads the user options from relevant UI elements into the actual whitespace
        cluttering unit. In this case, we load the target line length to be achieved,
        and whether to pad tokens to achieve that line length or not."""
        # Load the target line length (>= 0, default 3)
        if self.target_length_entry is not None:
            try:
                self.target_length = int(self.target_length_entry.text())
                if self.target_length < 0:
                    self.target_length = 0
            except:
                self.target_length = 3
        # Load whether to pad lines to achieve the target length or not
        if self.pad_lines_checkbox is not None:
            self.pad_lines = self.pad_lines_checkbox.isChecked()

    def from_json(json_str: str) -> "GuiClutterWhitespaceUnit":
        """Loads the GUI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the GuiClutterWhitespaceUnit.

        Returns:
            GuiClutterWhitespaceUnit: The corresponding GuiClutterWhitespaceUnit object."""
        unit = ClutterWhitespaceUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiClutterWhitespaceUnit(unit.target_length, unit.pad_lines)

    def get_gui() -> "GuiClutterWhitespaceUnit":
        """Creates a whitespace cluttering transformation loaded with default values to
        allow  GUI interaction with the transformation.

        Returns:
            GuiCluterWhitespaceUnit: the whitespace cluttering transformation with default
            values."""
        return GuiClutterWhitespaceUnit(100, True)


class GuiDiTriGraphEncodeUnit(DiTriGraphEncodeUnit):
    """The digraph/trigraph encoding transformation with added graphical interfaces."""

    def __init__(self, *args, **kwargs):
        """The constructor for the GuiDiTriGraphEncodeUnit, extending the original
        transformation unit to also initialise attributes for the style buttons and
        the probability entry.
        """
        super(GuiDiTriGraphEncodeUnit, self).__init__(*args, **kwargs)
        self.style_buttons = None
        self.probability_entry = None

    def edit_gui(self, parent: QWidget) -> None:
        """Implements a graphical interface for editing a digraph and trigraph
        encoding transformation.

        Args:
            parent (QWidget): The parent widget to place this widget into.
        """
        layout = QVBoxLayout(parent)

        # Add radio buttons for selecting the encoding style to use.
        style, self.style_buttons = generate_radio_button_widget(
            "Encoding Style:",
            "The encoding stylt to use when replacing symbols throughout the program\n"
            "body, which dictates how new macros are chosen to replace existing symbols.",
            {style.value: style for style in DiTriGraphEncodeUnit.Style},
            self.style.value,
            parent,
            {
                DiTriGraphEncodeUnit.Style.DIGRAPH.value: "Replace symbols []{}# with corresponding two-letter digraphs.\n"
                '  e.g. "[" ---> "<:".',
                DiTriGraphEncodeUnit.Style.TRIGRAPH.value: "Replace symbols []{}#\\^|~ with corresponding three-letter digraphs.\n"
                '  e.g. "[" ---> "??(".',
                DiTriGraphEncodeUnit.Style.MIXED.value: "Replace symbols with corresponding two-letter digraphs or three-letter\n"
                "digraphs, chosen between randomly with equal probability.",
            },
        )
        layout.addWidget(style, 1, alignment=Qt.AlignmentFlag.AlignTop)

        # Add a float entry for selecting the probability of performing encodings.
        probability, self.probability_entry = generate_float_widget(
            "Probability:",
            "The probability that an encoding will take place, which must be a number\n"
            "in the range 0 <= p <= 1. A probability of 0 means that no encodings will\n"
            "occur, a probability of 0.5 means approximately half of the symbols will\n"
            "be encoded, and 1.0 means all symbols are encoded. This allows you to achieve\n"
            "a mixture of digraphs, trigraphs and regular symbols for maximal obfuscation.",
            self.chance,
            0.0,
            1.0,
            parent,
        )
        layout.addWidget(probability, 1, alignment=Qt.AlignmentFlag.AlignTop)
        parent.setLayout(layout)

    def load_gui_values(self) -> None:
        """Loads the user options from relevant UI elements into the actual digraph and
        trigraph encoding unit. In this case, we load the encoding style to be used,
        alongside the probability that an encoding should be performed."""
        # Load the encoding style to used (selected via radio buttons)
        if self.style_buttons is not None and len(self.style_buttons) > 0:
            for button, style in self.style_buttons.items():
                if button.isChecked():
                    self.style = style
                    break
        # Load the encoding probability (0.0 <= p <= 1.0, default 0.75)
        if self.probability_entry is not None:
            try:
                self.chance = float(self.probability_entry.text())
                if self.chance > 1.0:
                    self.chance = 1.0
                elif self.chance < 0.0:
                    self.chance = 0.0
            except:
                self.chance = 0.75

    def from_json(json_str: str) -> "GuiDiTriGraphEncodeUnit":
        """Loads the GUI obfuscation unit from its JSON string representation by
        calling the relevant unit-specific conversion method and parsing its attributes.

        Args:
            json_str (str): The JSON string representation of the GuiDiTriGraphEncodeUnit.

        Returns:
            GuiDiTriGraphEncodeUnit: The corresponding GuiDiTriGraphEncodeUnit object."""
        unit = DiTriGraphEncodeUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiDiTriGraphEncodeUnit(unit.style, unit.chance)

    def get_gui() -> "GuiDiTriGraphEncodeUnit":
        """Creates a digraph/trigraph encoding transformation loaded with default values
        to allow GUI interaction with the transformation.

        Returns:
            GuiDiTriGraphEncodeUnit: the digraph/trigraph encoding transformation with
            default values."""
        return GuiDiTriGraphEncodeUnit(DiTriGraphEncodeUnit.Style.MIXED, 0.75)
