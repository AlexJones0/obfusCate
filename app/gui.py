""" File: gui.py
Implements functions to implement the graphical user interface of the program,
such that it can be more accessibly used without text interaction in a terminal
window. """
from .obfuscation import *
from .interaction import (
    handle_arguments,
    disable_logging,
    set_seed,
    suppress_errors,
    display_progress,
    save_composition,
    save_composition_file,
    load_composition,
    load_composition_file,
)
from app import settings as config
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import Qt, QSize, QMimeData, QDir, QCoreApplication
from typing import Type, Tuple, Mapping, Any
from copy import deepcopy
import sys
import ctypes


DEFAULT_FONT = ["Consolas", "Fira Code", "Jetbrains Mono", "Courier New", "monospace"]
CODE_FONT = ["Jetbrains Mono", "Fira Code", "Consolas", "Courier New", "monospace"]
SHORTCUT_DESELECT = "Esc"
SHORTCUT_OBFUSCATE = "Ctrl+R"
GENERAL_TOOLTIP_CSS = """ 
    QToolTip { 
        background-color: #AAAAAA; 
        color: black; 
        border: black solid 2px
    }
"""
MINIMAL_SCROLL_BAR_CSS = """
    QScrollBar:vertical{
        border: none;
        background: transparent;
        width:10px;
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::sub-page:vertical{
        background: transparent;
    }
    QScrollBar::add-page:vertical{
        background: transparent;
    }
    QScrollBar::handle:vertical{
        background: white;
        border-radius: 5px;
        border-style: solid;
    }
    QScrollBar::add-line:vertical{
        background: transparent;
    }
    QScrollBar::sub-line:vertical{
        background: transparent;
    }
"""

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


def set_no_options_widget(parent: QWidget) -> None:
    layout = QVBoxLayout(parent)
    no_options_label = QLabel("No options available.", parent)
    no_options_label.setFont(QFont(DEFAULT_FONT, 12))
    no_options_label.setStyleSheet("QLabel{color: #727463;}")
    layout.addWidget(no_options_label, alignment=Qt.AlignmentFlag.AlignCenter)
    parent.setLayout(layout)
    
    
def generate_integer_widget(label_msg: str, tooltip_msg: str, init_val: int, min_val: int, max_val: int, parent: QWidget) -> Tuple[QWidget, QLineEdit]:
    integer_widget = QWidget(parent)
    layout = QHBoxLayout(integer_widget)
    label = QLabel(label_msg, integer_widget)
    label.setFont(QFont(DEFAULT_FONT, 12))
    label.setToolTip(tooltip_msg)
    QToolTip.setFont(QFont(DEFAULT_FONT, 13))
    label.setStyleSheet("QLabel{color: #727463;}\n" + GENERAL_TOOLTIP_CSS)
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignLeft) 
    layout.addSpacing(5)
    entry = QLineEdit(str(init_val), integer_widget)
    entry.setFont(QFont(DEFAULT_FONT, 12))
    entry.setValidator(QIntValidator(min_val, max_val, entry))
    entry.setStyleSheet("""
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


def generate_float_widget(label_msg: str, tooltip_msg: str, init_val: float, min_val: float, max_val: float, parent: QWidget) -> Tuple[QWidget, QLineEdit]:
    float_widget = QWidget(parent)
    layout = QHBoxLayout(float_widget)
    label = QLabel(label_msg, float_widget)
    label.setFont(QFont(DEFAULT_FONT, 12))
    label.setToolTip(tooltip_msg)
    QToolTip.setFont(QFont(DEFAULT_FONT, 13))
    label.setStyleSheet("QLabel{color: #727463;}\n" + GENERAL_TOOLTIP_CSS)
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignLeft) 
    layout.addSpacing(5)
    entry = QLineEdit(str(init_val), float_widget)
    entry.setFont(QFont(DEFAULT_FONT, 12))
    entry.setValidator(QDoubleValidator(min_val, max_val, 1000, entry))
    entry.setStyleSheet("""
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


def generate_radio_button_widget(label_msg: str, tooltip_msg: str, options: Mapping[str, Any], init_val: str, parent: QWidget, option_tooltips: Optional[Mapping[str,str]] = None) -> Tuple[QWidget, Iterable[QRadioButton]]:
    radio_widget = QWidget(parent)
    layout = QVBoxLayout(radio_widget)
    layout.setSpacing(0)
    layout.setContentsMargins(0, 0, 0, 0)
    label = QLabel(label_msg, radio_widget)
    label.setFont(QFont(DEFAULT_FONT, 12))
    label.setToolTip(tooltip_msg)
    QToolTip.setFont(QFont(DEFAULT_FONT, 13))
    label.setStyleSheet("QLabel{color: #727463;}\n" + GENERAL_TOOLTIP_CSS)
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
        radio_button.setFont(QFont(DEFAULT_FONT, 11))
        radio_button.setStyleSheet(GENERAL_TOOLTIP_CSS + """
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


def generate_checkbox_widget(label_msg: str, tooltip_msg: str, init: bool, parent: QWidget) -> Tuple[QWidget, QCheckBox]:
    checkbox_widget = QWidget(parent)
    layout = QHBoxLayout(checkbox_widget)
    layout.setSpacing(20)
    layout.setContentsMargins(0, 0, 0, 0)
    label = QLabel(label_msg, checkbox_widget)
    label.setFont(QFont(DEFAULT_FONT, 12))
    label.setToolTip(tooltip_msg)
    QToolTip.setFont(QFont(DEFAULT_FONT, 13))
    label.setStyleSheet("QLabel{color: #727463;}\n" + GENERAL_TOOLTIP_CSS)
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignLeft)
    checkbox = QCheckBox(checkbox_widget)
    checkbox.setFont(QFont(DEFAULT_FONT, 12))
    checkbox.setStyleSheet("""
        QCheckBox{
            color: #727463
        }"""
    )
    checkbox.setChecked(init)
    layout.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignLeft)
    layout.addStretch()
    checkbox_widget.setLayout(layout)
    return (checkbox_widget, checkbox)


def generate_checkboxes_widget(label_msg: str, tooltip_msg: str, options: Mapping[str, Any], init_vals: Iterable[str], parent: QWidget, option_tooltips: Optional[Mapping[str,str]] = None) -> Tuple[QWidget, Iterable[QCheckBox]]:
    labelled_widget = QWidget(parent)
    layout = QVBoxLayout(labelled_widget)
    layout.setSpacing(0)
    layout.setContentsMargins(0, 0, 0, 0)
    label = QLabel(label_msg, labelled_widget)
    label.setFont(QFont(DEFAULT_FONT, 12))
    label.setToolTip(tooltip_msg)
    QToolTip.setFont(QFont(DEFAULT_FONT, 13))
    label.setStyleSheet("QLabel{color: #727463;}\n" + GENERAL_TOOLTIP_CSS)
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignLeft)
    checkbox_widget = QWidget(labelled_widget)
    checkbox_layout = QVBoxLayout(checkbox_widget)
    checkbox_layout.setContentsMargins(15, 5, 5, 5)
    checkbox_layout.setSpacing(0)
    checkboxes = {}
    for option in options.keys():
        checkbox = QCheckBox(option, checkbox_widget)
        checkbox.setFont(QFont(DEFAULT_FONT, 11))
        checkbox.setStyleSheet(GENERAL_TOOLTIP_CSS + """
            QCheckBox{
                color: #727463
            }"""
        )
        checkbox.setChecked(option in init_vals or options[option] in init_vals)
        if option_tooltips is not None and option in option_tooltips:
            checkbox.setToolTip(option_tooltips[option])
        checkbox_layout.addWidget(checkbox, 1, alignment=Qt.AlignmentFlag.AlignLeft) # TODO will this alignment work?
        checkboxes[checkbox] = options[option]
    checkbox_widget.setLayout(checkbox_layout)
    layout.addWidget(checkbox_widget)
    labelled_widget.setLayout(layout)
    return (labelled_widget, checkboxes)
        

class GuiIdentityUnit(IdentityUnit):

    def edit_gui(self, parent: QWidget) -> None:
        set_no_options_widget(parent)

    def load_gui_values(self) -> None:
        return

    def from_json(json_str: str) -> None:
        return GuiIdentityUnit()

    def get_gui() -> "GuiIdentityUnit":
        return GuiIdentityUnit()


class GuiFuncArgumentRandomiseUnit(FuncArgumentRandomiseUnit):
    
    def __init__(self, *args, **kwargs):
        super(GuiFuncArgumentRandomiseUnit, self).__init__(*args, **kwargs)
        self.extra_args_entry = None
    
    def edit_gui(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        extra_args, self.extra_args_entry = generate_integer_widget(
            "Extra Args:",
            "The number of additional spurious arguments to add to each function.\n"
            "This must be an integer >= 0. If 0 is selected, then the argument\n"
            "list will just be randomised but not otherwise modified.",
            self.extra_args,
            0,
            2147483647,
            parent
        )
        layout.addWidget(extra_args, 1, alignment=Qt.AlignmentFlag.AlignTop)
        parent.setLayout(layout)

    def load_gui_values(self) -> None:
        if self.extra_args_entry is not None:
            try:
                self.extra_args = int(self.extra_args_entry.text())
                if self.extra_args < 0:
                    self.extra_args = 0
                self.traverser.extra = self.extra_args
            except:
                self.extra_args = 3
                self.traverser.extra = 3

    def from_json(json_str: str) -> None:
        unit = FuncArgumentRandomiseUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiFuncArgumentRandomiseUnit(unit.extra_args)

    def get_gui() -> "GuiFuncArgumentRandomiseUnit":
        return GuiFuncArgumentRandomiseUnit(3)


class GuiStringEncodeUnit(StringEncodeUnit):

    def __init__(self, *args, **kwargs):
        super(GuiStringEncodeUnit, self).__init__(*args, **kwargs)
        self.style_buttons = None

    def edit_gui(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        style, self.style_buttons = generate_radio_button_widget(
            "Encoding Style:",
            "The encoding style to use when encoding strings in the program, which\n"
            "dictates how it is chosen what encodings characters are replaced with.",
            {style.value: style for style in StringEncodeTraverser.Style},
            self.style.value,
            parent,
            {
                StringEncodeTraverser.Style.OCTAL.value: \
                    "Encode each character as its octal (base-8) representation where possible.\n"
                    "  e.g. \"hello\" -> \"\\150\\145\\154\\154\\157\".",
                StringEncodeTraverser.Style.HEX.value: \
                    "Encode each character as its hexadecimal (base-16) representation where possbible.\n"
                    "  e.g. \"hello\" -> \"\\x68\\x65\\x6c\\x6c\\x6f\".",
                StringEncodeTraverser.Style.MIXED.value: \
                    "Encode each character as either its octal (base-8) or hexadecimal (base-16)\n"
                    "representation where possible, choosing randomly between the two.\n"
                    "  e.g. \"hello\" -> \"\\x68\\145\\154\\x6c\\157\".",
                StringEncodeTraverser.Style.ALL.value: \
                    "Encode each character as either itself (no change), its octal (base-8) representation\n"
                    "or its hexadecimal (base-16) representation, choosing randomly between all 3 options.\n"
                    "  e.g. \"hello\" -> \"\\150e\\x6cl\\x6f\".",
            }
        )
        layout.addWidget(style, 1, alignment=Qt.AlignmentFlag.AlignTop)
        parent.setLayout(layout)

    def load_gui_values(self) -> None:
        if self.style_buttons is not None and len(self.style_buttons) > 0:
            for button, style in self.style_buttons.items():
                if button.isChecked():
                    self.style = style
                    self.traverser.style = style
                    break

    def from_json(json_str: str) -> None:
        unit = StringEncodeUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiStringEncodeUnit(unit.style)

    def get_gui() -> "GuiStringEncodeUnit":
        return GuiStringEncodeUnit(StringEncodeTraverser.Style.MIXED)


class GuiIntegerEncodeUnit(IntegerEncodeUnit):
    
    def edit_gui(self, parent: QWidget) -> None:
        # TODO this should have options in the future! But doesn't right now
        set_no_options_widget(parent)

    def load_gui_values(self) -> None:
        # TODO see above edit_gui method comment
        return

    def from_json(json_str: str) -> None:
        unit = IntegerEncodeUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiIntegerEncodeUnit(unit.style)

    def get_gui() -> "GuiIntegerEncodeUnit":
        return GuiIntegerEncodeUnit(IntegerEncodeTraverser.Style.SIMPLE)
    

class GuiIdentifierRenameUnit(IdentifierRenameUnit):
    
    def __init__(self, *args, **kwargs):
        super(GuiIdentifierRenameUnit, self).__init__(*args, **kwargs)
        self.style_buttons = None
        self.minimise_idents_checkbox = None
    
    def edit_gui(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        style, self.style_buttons = generate_radio_button_widget(
            "Renaming Style:",
            "The renaming style to use when renaming identifiers throughout the\n"
            "program, which dictates how new identifiers are chosen to replace\n"
            "existing names.",
            {style.value: style for style in IdentifierTraverser.Style},
            self.style.value,
            parent,
            {
                IdentifierTraverser.Style.COMPLETE_RANDOM.value: \
                    "Generate new identifiers that are completely random strings of 4-19 characters.\n"
                    "  e.g. tcEM7, aA_LsaUdhnh, YPWnW0XE.",
                IdentifierTraverser.Style.ONLY_UNDERSCORES.value: \
                    "Generate new identifiers that consist of solely the underscore character '_'.\n"
                    "  e.g. _, _____, ________.",
                IdentifierTraverser.Style.MINIMAL_LENGTH.value: \
                    "Generate new identifiers that occupy the minimum space possible as a whole, by\n"
                    "iterating through available symbols sequentially.\n"
                    "  e.g. a, b, c, d, e, ..."
            }
        )
        layout.addWidget(style, 1, alignment=Qt.AlignmentFlag.AlignTop)
        minimise_idents, self.minimise_idents_checkbox = generate_checkbox_widget(
            "Minimise Identifiers?",
            "Attempts to greedily re-use identifier names whenever possible, such that the minimum\n"
            "number of unique names are used throughout the program, and the maximum number of\n"
            "different programming constructs are named the same thing. This option exploits variable\n"
            "shadowing within scopes, the different naming systems of labels/structures and other\n"
            "constructs, and analysis of identifier usage and liveness. [WARNING: VERY EXPERIMENTAL].",
            self.minimiseIdents,
            parent
        )
        layout.addWidget(minimise_idents, 1, alignment=Qt.AlignmentFlag.AlignTop)
        parent.setLayout(layout)

    def load_gui_values(self) -> None:
        if self.style_buttons is not None and len(self.style_buttons) > 0:
            for button, style in self.style_buttons.items():
                if button.isChecked():
                    self.style = style
                    break
        if self.minimise_idents_checkbox is not None:
            self.minimiseIdents = self.minimise_idents_checkbox.isChecked()

    def from_json(json_str: str) -> None:
        unit = IdentifierRenameUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiIdentifierRenameUnit(unit.style, unit.minimiseIdents)

    def get_gui() -> "GuiIdentifierRenameUnit":
        return GuiIdentifierRenameUnit(IdentifierTraverser.Style.COMPLETE_RANDOM, False)


class GuiArithmeticEncodeUnit(ArithmeticEncodeUnit):
    
    def __init__(self, *args, **kwargs):
        super(GuiArithmeticEncodeUnit, self).__init__(*args, **kwargs)
        self.depth_entry = None
    
    def edit_gui(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
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
            parent
        )        
        layout.addWidget(depth, 1, alignment=Qt.AlignmentFlag.AlignTop)
        parent.setLayout(layout)

    def load_gui_values(self) -> None:
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
        unit = ArithmeticEncodeUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiArithmeticEncodeUnit(unit.level)

    def get_gui() -> "GuiArithmeticEncodeUnit":
        return GuiArithmeticEncodeUnit(1)


class GuiAugmentOpaqueUnit(AugmentOpaqueUnit):
    
    def __init__(self, *args, **kwargs):
        super(GuiAugmentOpaqueUnit, self).__init__(*args, **kwargs)
        self.style_checkboxes = None
        self.probability_entry = None
    
    def edit_gui(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        tooltips = {
            OpaqueAugmenter.Style.INPUT.value: \
                "Opaque predicates can be generated using user inputs (function parameters).",
            OpaqueAugmenter.Style.ENTROPY.value: \
                "Opaque predicates can be generated using entropic (random) variables, which\n"
                "are created globally and initialised with random values at the start of the\n"
                "main() function. In the current implementation, for every random variable\n"
                "that is needed, it is decided at random whether to use an existing variable\n"
                "or to make a new one (25 percent chance), to create good diversity and increase\n"
                "complexity throughout the program."
        }
        styles, self.style_checkboxes = generate_checkboxes_widget(
            "Predicate Style:",
            "The opaque predicate generation styles that can be used by the program.\n"
            "This simply refers to the types of inputs that can be utilised to make\n"
            "opaque predicates, such as using user input (function parameters) or\n"
            "using random variables (entropy).",
            {" ".join(style.value.split(" ")[3:]).capitalize(): style for style in OpaqueAugmenter.Style},
            set(self.styles),
            parent, 
            dict((" ".join(key.split(" ")[3:]).capitalize(), val) for key, val in tooltips.items())
        )
        layout.addWidget(styles, alignment=Qt.AlignmentFlag.AlignTop)
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
            parent
        )
        layout.addWidget(probability, alignment=Qt.AlignmentFlag.AlignTop)
        parent.setLayout(layout)

    def load_gui_values(self) -> None:
        if self.style_checkboxes is not None and len(self.style_checkboxes) > 0:
            self.styles = [s for cbox, s in self.style_checkboxes.items() if cbox.isChecked()]
            self.traverser.styles = self.styles
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

    def from_json(json_str: str) -> None:
        unit = AugmentOpaqueUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiAugmentOpaqueUnit(unit.styles, unit.probability)

    def get_gui() -> "GuiAugmentOpaqueUnit":
        return GuiAugmentOpaqueUnit([s for s in OpaqueAugmenter.Style], 1.0)


class GuiInsertOpaqueUnit(InsertOpaqueUnit):
    
    def __init__(self, *args, **kwargs):
        super(GuiInsertOpaqueUnit, self).__init__(*args, **kwargs)
        self.style_checkboxes = None
        self.granularity_checkboxes = None
        self.kind_checkboxes = None
        self.number_entry = None
    
    def edit_gui(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 20)
        scroll_widget = QScrollArea(parent)
        scroll_widget.setStyleSheet(
            """
            QScrollArea{
                background-color: transparent;
                border: none;
            }"""
            + MINIMAL_SCROLL_BAR_CSS
        )
        scroll_widget.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
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
        scroll_content.setContentsMargins(0, 0, 0, 0)
        scroll_content.layout.setContentsMargins(0, 0, 0, 0)
        scroll_content.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        scroll_widget.setWidget(scroll_content)
        layout.addWidget(scroll_widget)
        tooltips = {
            OpaqueAugmenter.Style.INPUT.value: \
                "Opaque predicates can be generated using user inputs (function parameters).",
            OpaqueAugmenter.Style.ENTROPY.value: \
                "Opaque predicates can be generated using entropic (random) variables, which\n"
                "are created globally and initialised with random values at the start of the\n"
                "main() function. In the current implementation, for every random variable\n"
                "that is needed, it is decided at random whether to use an existing variable\n"
                "or to make a new one (25 percent chance), to create good diversity and increase\n"
                "complexity throughout the program."
        }
        styles, self.style_checkboxes = generate_checkboxes_widget(
            "Predicate Style:",
            "The opaque predicate generation styles that can be used by the program.\n"
            "This simply refers to the types of inputs that can be utilised to make\n"
            "opaque predicates, such as using user input (function parameters) or\n"
            "using random variables (entropy).",
            {" ".join(style.value.split(" ")[3:]).capitalize(): style for style in OpaqueInserter.Style},
            set(self.styles),
            parent, 
            dict((" ".join(key.split(" ")[3:]).capitalize(), val) for key, val in tooltips.items())
        )
        scroll_content.layout.addWidget(styles, alignment=Qt.AlignmentFlag.AlignTop)
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
                OpaqueInserter.Granularity.PROCEDURAL.value.split(":")[0].capitalize(): \
                    "Generate new opaque predicate conditionals that encapsulate the entire\n"
                    "function body.",
                OpaqueInserter.Granularity.BLOCK.value.split(":")[0].capitalize(): \
                    "Generate new opaque predicate conditionals that encapsulate contiguous\n"
                    "sequences of statements (i.e. 'blocks' of code) within the function. These\n"
                    "blocks are chosen entirely at random, and are of random length.",
                OpaqueInserter.Granularity.STMT.value.split(":")[0].capitalize(): \
                    "Generate new opaque predicate conditionals that encapsulate singular\n"
                    "program statements within the function. These statements are chosen entirely\n"
                    "at random from those within the function body."
            }
        )
        scroll_content.layout.addWidget(granularities, alignment=Qt.AlignmentFlag.AlignTop)
        kinds, self.kind_checkboxes = generate_checkboxes_widget(
            "Predicate Kinds:",
            "The kinds (formats) of opaque predicate conditionals that will be inserted. This\n"
            "increases obfuscation diversity by inserting opaque predicates using different\n"
            "programming constructs and logical structures. For example, one kind might evaluate\n"
            "the real code on an else branch of an if statement, whereas another might evaluate\n"
            "buggy code within a while loop.",
            {k.value.split(":")[0].replace("_", " ").capitalize(): k for k in OpaqueInserter.Kind},
            set(self.kinds),
            parent,
            dict(
                (k.value.split(":")[0].replace("_", " ").capitalize(),
                 "Enable construction of opaque predicate conditionals with the form\n"
                 "  " + k.value.split(":")[1].strip())
                for k in OpaqueInserter.Kind  
            )
        )
        scroll_content.layout.addWidget(kinds, alignment=Qt.AlignmentFlag.AlignTop)
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
            parent
        )
        # TODO slightly weird large spacing here?
        scroll_content.layout.addWidget(number, alignment=Qt.AlignmentFlag.AlignTop)
        parent.setLayout(layout)

    def load_gui_values(self) -> None:
        if self.style_checkboxes is not None and len(self.style_checkboxes) > 0:
            self.styles = [s for cbox, s in self.style_checkboxes.items() if cbox.isChecked()]
            self.traverser.styles = self.styles
        if self.granularity_checkboxes is not None and len(self.granularity_checkboxes) > 0:
            self.granularities = [g for cbox, g in self.granularity_checkboxes.items() if cbox.isChecked()]
            self.traverser.granularities = self.granularities
        if self.kind_checkboxes is not None and len(self.kind_checkboxes) > 0:
            self.kinds = [k for cbox, k in self.kind_checkboxes.items() if cbox.isChecked()]
            self.traverser.kinds = self.kinds
        if self.number_entry is not None:
            try:
                self.number = int(self.number_entry.text())
                if self.number < 0:
                    self.number = 0
                self.traverser.number = self.number
            except:
                self.number = 5
                self.traverser.number = 5

    def from_json(json_str: str) -> None:
        unit = InsertOpaqueUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiInsertOpaqueUnit(unit.styles, unit.granularities, unit.kinds, unit.number)

    def get_gui() -> "GuiInsertOpaqueUnit":
        return GuiInsertOpaqueUnit(
            [s for s in OpaqueInserter.Style],
            [g for g in OpaqueInserter.Granularity],
            [k for k in OpaqueInserter.Kind],
            5,
        )


class GuiControlFlowFlattenUnit(ControlFlowFlattenUnit):
    
    def edit_gui(self, parent: QWidget) -> None:
        set_no_options_widget(parent)
    
    def load_gui_values(self) -> None:
        return
    
    def from_json(json_str: str) -> None:
        return GuiControlFlowFlattenUnit()
    
    def get_gui() -> "GuiControlFlowFlattenUnit":
        return GuiControlFlowFlattenUnit()


class GuiClutterWhitespaceUnit(ClutterWhitespaceUnit):
    
    def edit_gui(self, parent: QWidget) -> None:
        set_no_options_widget(parent)
    
    def load_gui_values(self) -> None:
        return
    
    def from_json(json_str: str) -> None:
        return GuiClutterWhitespaceUnit()
    
    def get_gui() -> "GuiClutterWhitespaceUnit":
        return GuiClutterWhitespaceUnit()


class GuiDiTriGraphEncodeUnit(DiTriGraphEncodeUnit):
    
    def __init__(self, *args, **kwargs):
        super(GuiDiTriGraphEncodeUnit, self).__init__(*args, **kwargs)
        self.style_buttons = None
        self.probability_entry = None
    
    def edit_gui(self, parent: QWidget) -> None:
        layout = QVBoxLayout(parent)
        style, self.style_buttons = generate_radio_button_widget(
            "Encoding Style:",
            "The encoding stylt to use when replacing symbols throughout the program\n"
            "body, which dictates how new macros are chosen to replace existing symbols.",
            {style.value: style for style in DiTriGraphEncodeUnit.Style},
            self.style.value,
            parent,
            {
                DiTriGraphEncodeUnit.Style.DIGRAPH.value: \
                    "Replace symbols []\{\}# with corresponding two-letter digraphs.\n"
                    "  e.g. \"[\" ---> \"<:\".",
                DiTriGraphEncodeUnit.Style.TRIGRAPH.value: \
                    "Replace symbols []\{\}#\\^|~ with corresponding three-letter digraphs.\n"
                    "  e.g. \"[\" ---> \"??(\".",
                DiTriGraphEncodeUnit.Style.MIXED.value: \
                    "Replace symbols with corresponding two-letter digraphs or three-letter\n"
                    "digraphs, chosen between randomly with equal probability."
            }
        )
        layout.addWidget(style, 1, alignment=Qt.AlignmentFlag.AlignTop)
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
            parent
        )
        layout.addWidget(probability, 1, alignment=Qt.AlignmentFlag.AlignTop)
        parent.setLayout(layout)
    
    def load_gui_values(self) -> None:
        if self.style_buttons is not None and len(self.style_buttons) > 0:
            for button, style in self.style_buttons.items():
                if button.isChecked():
                    self.style = style
                    break
        if self.probability_entry is not None:
            try:
                self.chance = float(self.probability_entry.text())
                if self.chance > 1.0:
                    self.chance = 1.0
                elif self.chance < 0.0:
                    self.chance = 0.0
            except:
                self.chance = 0.75
    
    def from_json(json_str: str) -> None:
        unit = DiTriGraphEncodeUnit.from_json(json_str)
        if unit is None:
            return None
        return GuiDiTriGraphEncodeUnit(unit.style, unit.chance)
    
    def get_gui() -> "GuiDiTriGraphEncodeUnit":
        return GuiDiTriGraphEncodeUnit(DiTriGraphEncodeUnit.Style.MIXED, 0.75)


def get_transform_colour(transform_type: TransformType) -> str:
    match transform_type:
        case TransformType.LEXICAL:
            return "#FFFFFF"
        case TransformType.PROCEDURAL:
            return "#5CD9EF"
        case TransformType.STRUCTURAL:
            return "#F92672"
        case TransformType.ENCODING:
            return "#A6E22E"
        case _:
            return "#0D09F7"


class CHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text: str) -> None:
        return super().highlightBlock(text)


class SourceEditor(QPlainTextEdit):
    def __init__(self, parent: QWidget = None) -> None:
        super(SourceEditor, self).__init__(parent)
        self.modified_from_read = True
        self.textChanged.connect(self.set_modified)
        self.source = CSource("", "", FileAST([]))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setFont(QFont(CODE_FONT, 10))
        self.setStyleSheet(
            """SourceEditor{
                border-style: solid;
                border-width: 3px;
                border-radius: 10px;
                border-color: #848484;
                background-color: #1D1E1A;    
            }"""
        )
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor("#272822"))
        palette.setColor(QPalette.ColorRole.Text, QColor("white"))
        self.setPalette(palette)
        highlighter = CHighlighter(self.document())
        # TODO proper syntax highlighting
        # TODO line numbers
        # TODO icons above files
        # TODO file names above files

    def add_source(self, source: CSource) -> None:
        self.source = source
        self.setPlainText(source.contents)
        self.modified_from_read = False
    
    def set_modified(self):
        self.modified_from_read = True


class TransformWidget(QWidget):
    def __init__(
        self,
        class_: Type[ObfuscationUnit],
        select_func: Callable,
        parent: QWidget = None,
    ) -> None:
        super(TransformWidget, self).__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setContentsMargins(0, 0, 0, 0)
        self.class_ = class_
        self.select_func = select_func
        self.label = QLabel(class_.name, self)
        self.label.setObjectName("transformNameLabel")
        self.label.setFont(QFont(DEFAULT_FONT, 11))
        self.label.setStyleSheet(
            "QLabel#transformNameLabel { color: "
            + get_transform_colour(class_.type)
            + "; }"
        )
        self.layout.addWidget(self.label, 7, alignment=Qt.AlignmentFlag.AlignLeft)
        self.buttons_widget = QWidget(self)
        self.buttons_widget.layout = QHBoxLayout(self.buttons_widget)
        self.buttons_widget.setContentsMargins(0, 0, 0, 0)
        self.buttons_widget.layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_widget.layout.setSpacing(0)
        self.info_symbol = QLabel(self)
        self.info_symbol.setPixmap(QPixmap(".\\app\\graphics\\info.png").scaled(28, 28))
        self.info_symbol.setToolTip(class_.extended_description)
        QToolTip.setFont(QFont(DEFAULT_FONT, 13))
        self.info_symbol.setStyleSheet(GENERAL_TOOLTIP_CSS)
        self.buttons_widget.layout.addSpacing(10)
        self.buttons_widget.layout.addWidget(self.info_symbol, 1)
        self.buttons_widget.layout.addSpacing(20)
        self.add_symbol = QPushButton("", self)
        self.add_symbol.setStyleSheet(
            """
            QPushButton {
                border: none;
                background: none;
            }"""
        )
        self.add_symbol.setIcon(QIcon(".\\app\\graphics\\plus.png"))
        self.add_symbol.setIconSize(QSize(22, 22))
        self.add_symbol.clicked.connect(self.add_transformation)
        self.buttons_widget.layout.addWidget(self.add_symbol, 1)
        self.layout.addWidget(
            self.buttons_widget, alignment=Qt.AlignmentFlag.AlignRight
        )
        self.setLayout(self.layout)

    def add_transformation(self):
        self.select_func(self.class_)


class AvailableForm(QFrame):
    def __init__(self, select_func, parent: QWidget = None) -> None:
        super(AvailableForm, self).__init__(parent)
        # TODO why is this not working?
        self.setStyleSheet(
            """
            AvailableForm{
                background-color: #272822; 
                border-style: solid;
                border-width: 2px;
                border-radius: 10px;
                border-color: #848484;
                padding: 6px; 
            }"""
        )
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(8)
        self.title_label = QLabel("Available Obfuscations", self)
        self.title_label.setFont(QFont(DEFAULT_FONT, 14))
        self.title_label.setStyleSheet("QLabel{color: white;}")
        self.layout.addWidget(
            self.title_label, 1, alignment=Qt.AlignmentFlag.AlignHCenter
        )  # TODO Or AlignTop?
        self.transforms = []
        subsubclasses = [c.__subclasses__() for c in ObfuscationUnit.__subclasses__()]
        subsubclasses = [c[0] for c in subsubclasses if len(c) > 0]
        ts = sorted(subsubclasses, key=lambda c: c.type.value)
        for class_ in ts:
            transform_widget = TransformWidget(class_, select_func, self)
            self.layout.addWidget(transform_widget, 1)
            self.transforms.append(transform_widget)
        self.setLayout(self.layout)


class SelectedTransformWidget(QWidget):
    def __init__(
        self,
        class_: Type[ObfuscationUnit],
        number: int,
        select_func: Callable,
        parent: QWidget = None,
    ) -> None:
        super(SelectedTransformWidget, self).__init__(parent)
        self.select_func = select_func
        self.class_ = class_
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.__number = number
        self.number_label = QLabel("{}.".format(number), self)
        self.number_label.setFont(QFont(DEFAULT_FONT, 11))
        self.number_label.setStyleSheet("QLabel{color: #AAAAAA}")
        self.layout.addWidget(self.number_label, 1)
        self.box_widget = QWidget(self)
        self.box_widget.layout = QHBoxLayout(self.box_widget)
        # self.box_widget.setContentsMargins(0, 0, 0, 0)
        # self.box_widget.layout.setContentsMargins(0, 0, 0, 0)
        # self.box_widget.layout.setSpacing(0)
        self.box_widget.setObjectName("TransformBackground")
        self.box_widget.setStyleSheet(
            """
            QWidget#TransformBackground{
                background-color: #34352D;
            }"""
        )
        self.name_label = QLabel(class_.name, self)
        self.name_label.setFont(QFont(DEFAULT_FONT, 11))
        self.name_label.setStyleSheet(
            "QLabel{ color: " + get_transform_colour(class_.type) + "; }"
        )
        self.box_widget.layout.addWidget(self.name_label)
        self.layout.addWidget(self.box_widget, 9)
        self.layout.addSpacing(10)
        self.box_widget.resize(self.box_widget.maximumWidth(), self.box_widget.height())
        self.setLayout(self.layout)
        self.drag_start_pos = None
        # TODO I think because of the drag pixmap image, it keeps printing text on drags
        # - "QPixmap::scaled: Pixmap is a null pixmap". Need to fix.

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton:
            if self.drag_start_pos is None:
                return
            moved = event.pos() - self.drag_start_pos
            if abs(moved.x()) + abs(moved.y()) <= 4:
                return
            drag = QDrag(self)
            drag.setMimeData(QMimeData())
            drag.exec(Qt.DropAction.MoveAction)
            drag.setPixmap(
                self.box_widget.grab()
            )  # TODO why is this not working? Try and get working

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.drag_start_pos = None
        if 0 <= event.pos().x() - self.box_widget.x() <= self.box_widget.width():
            self.select_func(self)
            self.select()

    def select(self):
        self.box_widget.setStyleSheet(
            """
            QWidget#TransformBackground{
                background-color: #48493E;
            }"""
        )

    def deselect(self):
        self.box_widget.setStyleSheet(
            """
            QWidget#TransformBackground{
                background-color: #34352D;
            }"""
        )

    @property
    def number(self):
        return self.__number

    @number.setter
    def number(self, new_number):
        self.__number = new_number
        self.number_label.setText("{}.".format(new_number))


class TransformOptionsForm(QFrame):
    def __init__(self, remove_func: Callable, parent: QWidget = None) -> None:
        super(TransformOptionsForm, self).__init__(parent)
        self.setStyleSheet(
            """
            TransformOptionsForm{
                background-color: #272822; 
                border-style: solid;
                border-width: 2px;
                border-radius: 10px;
                border-color: #848484;
                padding: 6px; 
            }"""
        )
        self.setMinimumHeight(250)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(5, 0, 5, 5)
        self.title_label = QLabel("Transform Options", self)
        self.title_label.setFont(QFont(DEFAULT_FONT, 14))
        self.title_label.setStyleSheet("QLabel{color: white;}")
        self.layout.addWidget(
            self.title_label, 1, alignment=Qt.AlignmentFlag.AlignHCenter
        )
        self.options = QFrame(self)
        self.options.setMinimumHeight(200)
        self.layout.addWidget(self.options, 9)
        # TODO seems to be an issue - if you click on the label text the button doesn't work
        # but if you click on any other part of the back it does? Need to troubleshoot this
        self.remove_button = QPushButton("Remove Transform", self)
        self.remove_button.setFont(QFont(DEFAULT_FONT, 12))
        self.remove_button.setStyleSheet(
            """
            QPushButton{
                background-color: #DE4C44;
                border: solid;
                border-color: #580904;
                color: #DDDDDD;
            }"""
        )
        self.remove_button.clicked.connect(remove_func)
        self.remove_button.hide()
        self.layout.addWidget(
            self.remove_button, 1, alignment=Qt.AlignmentFlag.AlignBottom
        )
        self.setLayout(self.layout)

    def load_transform(self, transform: ObfuscationUnit) -> None:
        if transform is None:
            self.remove_button.hide()
            self.layout.removeWidget(self.options)
            self.options = QFrame()
            self.options.setMinimumHeight(200)
            self.layout.insertWidget(1, self.options)
            # TODO figure out how to handle resetting default behaviour
            return
        self.remove_button.show()
        if isinstance(transform, (GuiIdentityUnit, GuiClutterWhitespaceUnit, GuiControlFlowFlattenUnit, GuiFuncArgumentRandomiseUnit, GuiStringEncodeUnit, GuiIntegerEncodeUnit, GuiIdentifierRenameUnit, GuiArithmeticEncodeUnit, GuiDiTriGraphEncodeUnit, GuiAugmentOpaqueUnit, GuiInsertOpaqueUnit)): # TODO remove when done developing:
            self.layout.removeWidget(self.options)
            self.options = QFrame()
            self.options.setMinimumHeight(200)
            transform.edit_gui(self.options)
            self.layout.insertWidget(1, self.options)
        else:
            self.layout.removeWidget(self.options)
            self.options = QFrame()
            self.options.setMinimumHeight(200)
            self.layout.insertWidget(1, self.options)


class CurrentForm(QFrame):

    # TODO could getter/setter self.current_transform with self.current_widget and the option form changes
    # and that would make code much more readable and simpler (but also make following changes much harder
    # to see)

    class RemoveBehaviour(Enum):
        SELECT_NEXT = 1
        DESELECT = 2

    def __init__(self, parent: QWidget = None) -> None:
        super(CurrentForm, self).__init__(parent)
        self.remove_behaviour = self.RemoveBehaviour.SELECT_NEXT
        self.deselect_shortcut = QShortcut(QKeySequence(SHORTCUT_DESELECT), self)
        self.deselect_shortcut.activated.connect(self.deselect_transform)
        self.setStyleSheet(
            """
            CurrentForm{
                background-color: #272822; 
                border-style: solid;
                border-width: 2px;
                border-radius: 10px;
                border-color: #848484;
                padding: 6px; 
            }"""
        )
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(8)
        self.setMinimumHeight(250)
        self.title_label = QLabel("Current Obfuscations", self)
        self.title_label.setFont(QFont(DEFAULT_FONT, 14))
        self.title_label.setStyleSheet("QLabel{color: white;}")
        self.title_widget = QWidget(self)
        self.title_widget.layout = QVBoxLayout(self.title_widget)
        self.title_widget.setContentsMargins(0, 0, 0, 0)
        self.title_widget.layout.setContentsMargins(0, 0, 0, 0)
        self.title_widget.layout.setSpacing(0)
        self.title_widget.layout.addWidget(
            self.title_label, alignment=Qt.AlignmentFlag.AlignHCenter
        )
        self.layout.addWidget(self.title_widget, alignment=Qt.AlignmentFlag.AlignTop)
        self.scroll_widget = QScrollArea(self)
        self.scroll_widget.setContentsMargins(0, 0, 0, 0)
        self.scroll_widget.setStyleSheet(
            """
            QScrollArea{
                background-color: transparent;
                border: none;
            }"""
            + MINIMAL_SCROLL_BAR_CSS
        )
        self.scroll_widget.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll_widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_widget.setWidgetResizable(True)
        self.scroll_content = QWidget(self.scroll_widget)
        self.scroll_content.setObjectName("ScrollWidget")
        self.scroll_content.setStyleSheet(
            """
            QWidget#ScrollWidget{
                background-color: transparent;
                border: none;
            }"""
        )
        self.scroll_content.layout = QVBoxLayout(self.scroll_content)
        self.scroll_content.setContentsMargins(0, 0, 0, 0)
        self.scroll_content.layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_content.layout.setSpacing(10)
        self.scroll_content.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self.scroll_widget.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll_widget, 9)
        self.setLayout(self.layout)
        self.selected = []
        self.selected_widgets = []
        self.current_transform = None
        self.current_widget = None
        self.__options_form_reference = None
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        # TODO
        if event.source() in self.selected_widgets:
            event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        position = event.position()
        source = event.source()
        num_items = self.scroll_content.layout.count()
        mouse_pos = position.y() + self.scroll_widget.verticalScrollBar().value()
        for i in range(num_items):
            widget = self.scroll_content.layout.itemAt(i).widget()
            widget_pos = (
                widget.y() + widget.height() + self.scroll_content.layout.spacing()
            )
            if mouse_pos < widget_pos:
                index = max(i - 1, 0)
                self.scroll_content.layout.insertWidget(index, source)
                self.move_transform(index, source)
                event.accept()
                return
        index = num_items - 1
        self.scroll_content.layout.insertWidget(index, source)
        self.move_transform(index, source)
        event.accept()

    def move_transform(self, new_index: int, source: QWidget) -> None:
        prev_index = self.selected_widgets.index(source)
        prev_transform = self.selected[prev_index]
        if prev_index < new_index:
            self.selected = (
                self.selected[:prev_index] + self.selected[(prev_index + 1) :]
            )
            self.selected_widgets = (
                self.selected_widgets[:prev_index]
                + self.selected_widgets[(prev_index + 1) :]
            )
        self.selected = (
            self.selected[:new_index] + [prev_transform] + self.selected[new_index:]
        )
        self.selected_widgets = (
            self.selected_widgets[:new_index]
            + [source]
            + self.selected_widgets[new_index:]
        )
        if prev_index >= new_index:
            self.selected = (
                self.selected[: (prev_index + 1)] + self.selected[(prev_index + 2) :]
            )
            self.selected_widgets = (
                self.selected_widgets[: (prev_index + 1)]
                + self.selected_widgets[(prev_index + 2) :]
            )
        for i in range(self.scroll_content.layout.count()):
            # TODO use self.selected_widgets instead?
            widget = self.scroll_content.layout.itemAt(i).widget()
            widget.number = i + 1

    def add_transform(self, class_: Type[ObfuscationUnit]) -> None:
        number = len(self.selected) + 1
        transform_widget = SelectedTransformWidget(
            class_, number, self.select_transform, self
        )
        transform_widget.setMaximumHeight(transform_widget.height())
        self.scroll_content.layout.addWidget(
            transform_widget, alignment=Qt.AlignmentFlag.AlignTop
        )
        self.selected.append(class_.get_gui())
        self.selected_widgets.append(transform_widget)
    
    def set_transforms(self, transforms: Iterable[ObfuscationUnit]) -> None:
        self.deselect_transform()
        for transform in self.selected:
            self.remove_transform(transform)
        self.current_transform = None
        self.current_widget = None
        for i, transform in enumerate(transforms):
            transform_widget = SelectedTransformWidget(
                transform.__class__, i+1, self.select_transform, self
            )
            transform_widget.setMaximumHeight(transform_widget.height())
            self.scroll_content.layout.addWidget(
                transform_widget, alignment=Qt.AlignmentFlag.AlignTop
            )
            self.selected.append(transform)
            self.selected_widgets.append(transform_widget)
        

    def remove_transform(self, transform: ObfuscationUnit) -> None:
        index = self.selected.index(transform)
        widget = self.selected_widgets[index]
        self.selected = self.selected[:index] + self.selected[(index + 1) :]
        self.selected_widgets = (
            self.selected_widgets[:index] + self.selected_widgets[(index + 1) :]
        )
        self.scroll_content.layout.removeWidget(widget)
        for i in range(index, len(self.selected)):
            self.selected_widgets[i].number = i + 1

    def select_transform(self, widget: SelectedTransformWidget) -> None:
        if self.current_widget is not None:
            if isinstance(self.current_transform, (GuiIdentityUnit, GuiClutterWhitespaceUnit, GuiControlFlowFlattenUnit, GuiFuncArgumentRandomiseUnit, GuiStringEncodeUnit, GuiIntegerEncodeUnit, GuiIdentifierRenameUnit, GuiArithmeticEncodeUnit, GuiDiTriGraphEncodeUnit, GuiAugmentOpaqueUnit, GuiInsertOpaqueUnit)): # TODO remove when done developing:
                self.current_transform.load_gui_values()
            self.current_widget.deselect()
        self.current_transform = self.selected[self.selected_widgets.index(widget)]
        self.current_widget = widget
        if self.__options_form_reference is not None:
            self.__options_form_reference.load_transform(self.current_transform)

    def deselect_transform(self) -> None:
        if self.current_widget is not None:
            self.current_widget.deselect()
        self.current_transform = None
        self.current_widget = None
        if self.__options_form_reference is not None:
            self.__options_form_reference.load_transform(self.current_transform)

    def remove_selected(self) -> None:
        if self.remove_behaviour == self.RemoveBehaviour.DESELECT:
            if self.current_transform is not None and self.current_widget is not None:
                self.remove_transform(self.current_transform)
            self.current_transform = None
            self.current_widget = None
            if self.__options_form_reference is not None:
                self.__options_form_reference.load_transform(None)
        elif self.remove_behaviour == self.RemoveBehaviour.SELECT_NEXT:
            if self.current_transform is not None and self.current_widget is not None:
                index = self.selected.index(self.current_transform)
                self.remove_transform(self.current_transform)
                if len(self.selected) <= index:
                    self.current_transform = None
                    self.current_widget = None
                else:
                    self.current_transform = self.selected[index]
                    self.current_widget = self.selected_widgets[index]
                    self.current_widget.select()
            else:
                self.current_transform = None
                self.current_widget = None
            if self.__options_form_reference is not None:
                self.__options_form_reference.load_transform(self.current_transform)
    
    def get_transforms(self):
        return self.selected

    def load_selected_values(self):
        if isinstance(self.current_transform, (GuiIdentityUnit, GuiClutterWhitespaceUnit, GuiControlFlowFlattenUnit, GuiFuncArgumentRandomiseUnit, GuiStringEncodeUnit, GuiIntegerEncodeUnit, GuiIdentifierRenameUnit, GuiArithmeticEncodeUnit, GuiDiTriGraphEncodeUnit, GuiAugmentOpaqueUnit, GuiInsertOpaqueUnit)): # TODO remove when done developing:
            self.current_transform.load_gui_values()

    def add_options_form(self, options_form: TransformOptionsForm) -> None:
        self.__options_form_reference = options_form


class MetricsForm(QFrame):
    def __init__(self, parent: QWidget = None) -> None:
        super(MetricsForm, self).__init__(parent)
        self.setStyleSheet(
            """
            MetricsForm{
                background-color: #272822; 
                border-style: solid;
                border-width: 2px;
                border-radius: 10px;
                border-color: #848484;
                padding: 6px; 
            }"""
        )
        self.setMinimumHeight(200)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel("Obfuscation Metrics", self)
        self.title_label.setFont(QFont(DEFAULT_FONT, 14))
        self.title_label.setStyleSheet("QLabel{color: white;}")
        self.layout.addWidget(
            self.title_label, 1, alignment=Qt.AlignmentFlag.AlignHCenter
        )
        self.metrics = QFrame(self)
        self.metrics.layout = QVBoxLayout(self.metrics)
        self.metrics.layout.setSpacing(5)
        self.metrics.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.metrics, 9)
        self.setLayout(self.layout)


class GeneralOptionsForm(QFrame):

    # TODO add a settings form maybe?
    def __init__(
        self,
        transforms_func: Callable,
        set_transforms_func: Callable,
        load_gui_vals_func: Callable,
        source_form: SourceEditor,
        obfuscated_form: SourceEditor,
        parent: QWidget = None,
    ) -> None:
        super(GeneralOptionsForm, self).__init__(parent)
        self.obfuscate_shortcut = QShortcut(QKeySequence(SHORTCUT_OBFUSCATE), self)
        self.obfuscate_shortcut.activated.connect(self.obfuscate)
        self.__transforms_reference = transforms_func
        self.__set_transforms_func = set_transforms_func
        self.__load_selected_gui_reference = load_gui_vals_func
        self.__source_form_reference = source_form
        self.__obfuscated_form_reference = obfuscated_form
        self.setStyleSheet(
            """
            GeneralOptionsForm{
                background-color: #272822; 
                border-style: solid;
                border-width: 2px;
                border-radius: 10px;
                border-color: #848484;
                padding: 6px; 
            }
            QPushButton{
                background-color: #2F3029;
                border-style: solid;
                border-width: 2px;
                border-color: #48493E;
                color: #B7B7B7;
            }
            QPushButton#ObfuscateButton{
                font-weight: bold;
            }"""
        )
        self.setMinimumHeight(200)  # TODO remove if not correct?
        self.seed = config.SEED
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        self.title_label = QLabel(config.NAME + " " + config.VERSION, self)
        self.title_label.setFont(QFont(DEFAULT_FONT, 14, 1000))
        self.title_label.setStyleSheet("QLabel{color: white;}")
        self.layout.addWidget(
            self.title_label, 1, alignment=Qt.AlignmentFlag.AlignHCenter
        )
        self.obfuscate_button = self.get_button("Obfuscate")
        self.obfuscate_button.setObjectName("ObfuscateButton")
        self.obfuscate_button.clicked.connect(self.obfuscate)
        self.load_source_button = self.get_button("Load source file")
        self.load_source_button.clicked.connect(self.load_source)
        self.save_obfuscated_button = self.get_button("Save obfuscated file")
        self.save_obfuscated_button.clicked.connect(self.save_obfuscated)
        self.load_transformations_button = self.get_button("Load transformations")
        self.load_transformations_button.clicked.connect(self.load_composition)
        self.save_transformations_button = self.get_button("Save transformations")
        self.save_transformations_button.clicked.connect(self.save_composition)
        self.quit_button = self.get_button("Quit")
        self.quit_button.clicked.connect(QCoreApplication.quit)
        self.setLayout(self.layout)

    def get_button(self, msg):
        button = QPushButton(msg, self)
        button.setFont(QFont(DEFAULT_FONT, 12))
        self.layout.addWidget(button, 1)
        return button

    def obfuscate(self) -> None:
        self.__load_selected_gui_reference()
        pipeline = Pipeline(self.seed, *self.__transforms_reference())
        source = deepcopy(self.__source_form_reference.source)
        source.contents = self.__source_form_reference.toPlainText()
        if self.__source_form_reference.modified_from_read:
            source.update_t_unit()
        obfuscated = pipeline.process(source)
        self.__obfuscated_form_reference.add_source(obfuscated)

    def load_source(self) -> None:
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setFilter(QDir.Filter.Readable)
        dialog.setNameFilter("C source files (*.c)")
        if not dialog.exec():
            return
        files = dialog.selectedFiles()
        if len(files) == 0:
            return
        source = CSource(files[0])
        if source.contents is None or not source.valid_parse:
            return False
        self.__source_form_reference.add_source(source)
    
    def load_composition(self) -> None:
        compositions_path = os.path.join(os.getcwd(), "compositions\\")
        if not os.path.exists(compositions_path):
            os.mkdir(compositions_path)
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setFilter(QDir.Filter.Readable)
        dialog.setNameFilter("C Obfuscation Files (*.cobf)")
        dialog.setDirectory(compositions_path)
        if not dialog.exec():
            return
        files = dialog.selectedFiles()
        if len(files) == 0:
            return
        try:
            with open(files[0], "r") as f:
                transform_pipeline = Pipeline.from_json(f.read(), use_gui=True)
                if transform_pipeline is None:
                    return
                if config.SEED is None: # Only use the saved seed if no seed was given
                    self.seed = transform_pipeline.seed
                self.__set_transforms_func(transform_pipeline.transforms)
        except:
            return
    
    def save_obfuscated(self) -> None:
        file, _ = QFileDialog.getSaveFileName(self, "Save Obfuscated C", "", "C Source Files (*.c);;All Files (*)")
        if not file or len(file) == 0:
            return
        with open(file, "w+") as f:
            f.write(self.__obfuscated_form_reference.toPlainText())
        
    
    def save_composition(self) -> None:
        compositions_path = os.path.join(os.getcwd(), "compositions\\")
        if not os.path.exists(compositions_path):
            os.mkdir(compositions_path)
        file, _ = QFileDialog.getSaveFileName(self, "Save Composition", compositions_path, "C Obfuscation Files (*.cobf)")
        if not file or len(file) == 0:
            return
        with open(file, "w+") as f:
            self.__load_selected_gui_reference()
            pipeline = Pipeline(self.seed, *self.__transforms_reference())
            f.write(pipeline.to_json())


class SelectionForm(QWidget):  # TODO move selection and misc just into obfuscatewidget?
    def __init__(self, parent: QWidget = None) -> None:
        super(SelectionForm, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.available_form = AvailableForm(self.add_transform, self)
        self.layout.addWidget(self.available_form, 1)
        self.current_form = CurrentForm(self)
        self.layout.addWidget(self.current_form, 1)
        self.setLayout(self.layout)

    def add_transform(self, class_):
        self.current_form.add_transform(class_)


class MiscForm(QWidget):
    def __init__(
        self,
        transforms_func: Callable,
        set_transforms_func: Callable,
        load_gui_vals_func: Callable,
        source_form: SourceEditor,
        obfuscated_form: SourceEditor,
        remove_func: Callable,
        parent: QWidget = None,
    ) -> None:
        super(MiscForm, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.transform_options = TransformOptionsForm(remove_func, self)
        self.layout.addWidget(
            self.transform_options, 1, alignment=Qt.AlignmentFlag.AlignTop
        )  # TODO temp alignment
        self.metrics_form = MetricsForm(self)
        self.layout.addWidget(self.metrics_form, 1)
        self.general_options = GeneralOptionsForm(
            transforms_func, set_transforms_func, load_gui_vals_func, source_form, obfuscated_form, self
        )
        self.layout.addWidget(
            self.general_options, 1, alignment=Qt.AlignmentFlag.AlignBottom
        )  # TODO temp alignment
        self.setLayout(self.layout)


class ObfuscateWidget(QWidget):
    def __init__(self, parent: QWidget = None) -> None:
        super(ObfuscateWidget, self).__init__(parent)
        self.layout = QHBoxLayout(self)
        # Define a splitter and both source editors
        self.source_editor = SourceEditor(self)
        self.obfuscated_editor = SourceEditor(self)
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.addWidget(self.source_editor)
        self.splitter.addWidget(self.obfuscated_editor)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        # Define column widgets for transform selection and miscallaneous options
        self.selection_form = SelectionForm(self)
        self.misc_form = MiscForm(
            self.selection_form.current_form.get_transforms,
            self.selection_form.current_form.set_transforms,
            self.selection_form.current_form.load_selected_values,
            self.source_editor,
            self.obfuscated_editor,
            self.selection_form.current_form.remove_selected,
            self,
        )
        self.selection_form.current_form.add_options_form(
            self.misc_form.transform_options
        )
        # Provide 60% of the screen to the source editors, 20% to selection, and 20% to misc options
        self.layout.addWidget(self.splitter, 6)
        self.layout.addWidget(self.selection_form, 2)
        self.layout.addWidget(self.misc_form, 2)
        self.setLayout(self.layout)

    def add_source(self, source: CSource) -> None:
        self.textChanged = False
        self.source_editor.add_source(source)


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget = None) -> None:
        super(MainWindow, self).__init__(parent)
        # Set window title and icon information
        self.setWindowTitle(config.NAME + " " + config.VERSION)
        self.setWindowIcon(QIcon(".\\app\\graphics\\logo5.png"))
        self.setAutoFillBackground(True)
        # Set default palette colour information
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#1D1E1A"))
        self.setPalette(palette)
        # Initialise window widgets
        self.obfuscate_widget = ObfuscateWidget(self)
        self.setCentralWidget(self.obfuscate_widget)

    def add_source(self, source: CSource) -> None:
        self.obfuscate_widget.add_source(source)


def handle_gui() -> bool:
    # Patch: If on windows, change the python window application user model
    # ID so that the icon is displayed correctly in the taskbar.
    if ctypes.windll is not None and ctypes.windll.shell32 is not None:
        app_id = config.NAME + "." + config.VERSION[1:]
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

    supplied_args = sys.argv
    if len(supplied_args) != 0 and supplied_args[0].endswith(".py"):
        supplied_args = supplied_args[1:]

    # Setup logging information
    create_log_file()
    log(f"Began execution of GUI script.")
    log(f"Supplied arguments: {str(supplied_args)}")

    # Handle supplied arguments/options
    args = handle_arguments(supplied_args, options)
    if isinstance(args, bool):
        return args

    app = QApplication(sys.argv)
    window = MainWindow()

    # Read file and display parse errors
    if len(args) >= 1:
        source = CSource(args[0])
        if source.contents is None or not source.valid_parse:
            return False
        window.add_source(source)
    if config.COMPOSITION is not None:
        contents = load_composition_file(config.COMPOSITION)
        if contents is None:
            log("Error loading saved transformations - please provide a valid compositions file", print_err=True)
            return False
        saved_pipeline = Pipeline.from_json(contents, use_gui=True)
        if saved_pipeline is None:
            log("Error loading saved transformations - please provide a valid compositions file", print_err=True)
            return False
        if config.SEED is None: # Only use saved seed if no seed was provided
            window.obfuscate_widget.misc_form.general_options.seed = saved_pipeline.seed
        window.obfuscate_widget.selection_form.current_form.set_transforms(saved_pipeline.transforms)

    window.show()
    app.exec()

    if config.SAVE_COMPOSITION:
        window.obfuscate_widget.selection_form.current_form.load_selected_values()
        seed = window.obfuscate_widget.misc_form.general_options.seed
        transforms = window.obfuscate_widget.selection_form.current_form.selected
        pipeline = Pipeline(seed, *transforms)
        save_composition_file(pipeline.to_json())

    if len(args) == 2:
        try:
            log("Writing obfuscation output")
            with open(args[1], "w+") as write_file:
                write_file.write(window.obfuscate_widget.obfuscated_editor.toPlainText())
            print("Obfuscation finished successfully.")
            log("Obfuscation written successfully.")
            log("Execution finished normally.")
        except Exception as e:
            print_error(f"Error creating output file '{args[1]}'")
            log(f"Error when writing output to file: {str(e)}")
            return False
    return True