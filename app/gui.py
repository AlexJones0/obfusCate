""" File: gui.py
Implements functions to implement the graphical user interface of the program,
such that it can be more accessibly used without text interaction in a terminal
window. """ 
from . import interaction, obfuscation as obfs
from .obfuscation import gui as obfs_gui
from .complexity import *
from .debug import print_error, create_log_file, log, logprint
from .config import GuiDefaults as Df
from app import settings as config
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import (
    Qt,
    QSize,
    QMimeData,
    QDir,
    QCoreApplication,
    QTimer,
)
from typing import Type, Tuple, Callable
from copy import deepcopy
import functools, sys, os, ctypes


def help_menu() -> bool:
    """Prints the command-line help menu detailing usage of the GUI command interface.

    Returns:
        bool: Always returns False, to signal that execution should stop."""
    print(__file__)
    help_str = (
        "################ GUI Help Manual ################\n"
        "This program takes as an argument some input C source program file and allows\n"
        "the application of a sequence of obfuscation transformations, resulting in an\n"
        "obfuscated C source file being produced. An input file can be optionally     \n"
        "provided or just loaded in the application (or you can type in the GUI       \n"
        "directly). If an output file is provided, the contents of the obfuscated code\n"
        "editor will be automatically saved to that file when you quit. For more      \n"
        "information on usage and options, see below.\n\n"
        "Usage: python {} [input_c_file] [output_file] [options]\n\n"
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


# Set the help menu function generated from the GUI options.
interaction.set_help_menu(help_menu)


def display_error(error_msg: str) -> None:
    """A general function for displaying an error in the GUI, creating a critical
    popup window without a parent and the name 'Error'.

    Args:
        error_msg (str): The error message to display in the popup window.
    """
    QMessageBox.critical(None, "Error", error_msg)


def get_transform_colour(transform_type: obfs.TransformType) -> str:
    """Maps each obfuscation transformation type to a unique colour, such that
    transformation effects can be easily distinguished by just looking at the colour
    of the transformation.

    Args:
        transform_type (obfs.TransformType): The transformation type to get
        the colour of.

    Returns:
        str: The hexadecimal "#FFFFFF" string representation of the colour.
    """
    match transform_type:
        case obfs.TransformType.LEXICAL:
            return "#FFFFFF"
        case obfs.TransformType.PROCEDURAL:
            return "#5CD9EF"
        case obfs.TransformType.STRUCTURAL:
            return "#F92672"
        case obfs.TransformType.ENCODING:
            return "#A6E22E"
        case _:
            return "#0D09F7"


class SourceEditor(QPlainTextEdit):
    """This class represents a program text editing environment within the GUI, corresponding
    to either the original or obfuscate source C programs."""

    def __init__(self, file_label: QLabel, parent: QWidget | None = None):
        """The constructor for the SourceEditor, initialising the Qt text editor and
        also noting the source file that is associated with the editor.

        Args:
            file_label (QLabel): The label to maintain above the top-left corner of the
            file, to indicate what the file contents are about.
            parent (QWidget | None): The parent widget to place this source editor within."""
        super(SourceEditor, self).__init__(parent)
        self.file_label = file_label
        self.modified_from_read = True
        self.textChanged.connect(self.set_modified)
        self.source = CSource("obfuscated.c", "", FileAST([]))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setFont(QFont(Df.CODE_FONT, 10))
        font_metrics = QFontMetricsF(self.font())
        space_width = font_metrics.size(0, " ").width()
        self.setTabStopDistance(space_width * 4)
        self.setStyleSheet(
            """SourceEditor{
                border-style: solid;
                border-width: 3px;
                border-radius: 10px;
                border-color: #848484;
                background-color: #1D1E1A;    
            }"""
            + Df.MINIMAL_SCROLL_BAR_CSS
        )
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor("#272822"))
        palette.setColor(QPalette.ColorRole.Text, QColor("white"))
        self.setPalette(palette)

    def add_source(self, source: CSource) -> None:
        """Loads a source file into the editor, replacing its text contents with
        the source files contents, and replacing the file label with the name of the
        file (the last part of the file path).

        Args:
            source (CSource): The source C program to load.
        """
        self.source = source
        self.setPlainText(source.contents)
        self.modified_from_read = False
        if self.file_label is not None:
            fname = source.fpath.split("\\")[-1].split("/")[-1]
            self.file_label.setText("/" + fname)

    def get_file_name(self) -> str:
        """Get the name of the file associated with the source editor.

        Returns:
            str: The file name (the last part of the file path).
        """
        return self.source.fpath.split("\\")[-1].split("/")[-1]

    def set_modified(self) -> None:
        """Sets the source editor as being modified from when contents where last read
        into the source editor."""
        self.modified_from_read = True

    def setPlainText(self, text: str) -> None:
        """Sets the new plain text contents of the source editor to the given text.

        Args:
            text (str): The file contents to load into the source editor.
        """
        vertical_scrollbar = self.verticalScrollBar()
        horizontal_scrollbar = self.horizontalScrollBar()
        vertical_scroll = vertical_scrollbar.value()
        horizontal_scroll = horizontal_scrollbar.value()
        super(SourceEditor, self).setPlainText(text)
        # Maintain scroll positions between content changes if possible so that minute
        # obfuscation changes can be easily observed
        vertical_scrollbar.setValue(vertical_scroll)
        horizontal_scrollbar.setValue(horizontal_scroll)


class TransformWidget(QWidget):
    """This class represents a widget for a single transformation type that is listed
    in the available transforms form, and can be added to the program."""

    def __init__(
        self,
        class_: Type[obfs.ObfuscationUnit],
        select_func: Callable,
        parent: QWidget | None = None,
    ) -> None:
        """The constructor for the TransformWidget, initialising each constitutent
        UI element based on the provided class.

        Args:
            class_ (Type[obfs.ObfuscationUnit]): The obfuscation unit class that is
            being represented by this TransformWidget.
            select_func (Callable): The function that should be called with the
            transform class when the add button is pressed.
            parent (QWidget | None): The parent widget that this widget should be
            placed within. Defaults to None."""
        super(TransformWidget, self).__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setContentsMargins(0, 0, 0, 0)
        self.class_ = class_
        self.select_func = select_func

        # Create the transform label
        self.label = QLabel(class_.name, self)
        self.label.setObjectName("transformNameLabel")
        self.label.setFont(QFont(Df.DEFAULT_FONT, 11))
        self.label.setStyleSheet(
            "QLabel#transformNameLabel { color: "
            + get_transform_colour(class_.type)
            + "; }"
        )
        self.layout.addWidget(self.label, 7, alignment=Qt.AlignmentFlag.AlignLeft)

        # Create the info and add buttons
        self.buttons_widget = QWidget(self)
        self.buttons_widget.layout = QHBoxLayout(self.buttons_widget)
        self.buttons_widget.setContentsMargins(0, 0, 0, 0)
        self.buttons_widget.layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_widget.layout.setSpacing(0)
        self.info_symbol = QLabel(self)
        self.info_symbol.setPixmap(
            QIcon("./app/graphics/icons/info.png").pixmap(QSize(21, 21))
        )
        self.info_symbol.setToolTip(class_.extended_description)
        QToolTip.setFont(QFont(Df.DEFAULT_FONT, 13))
        self.info_symbol.setStyleSheet(Df.GENERAL_TOOLTIP_CSS)
        self.buttons_widget.layout.addSpacing(10)
        self.buttons_widget.layout.addWidget(self.info_symbol, 1)
        self.buttons_widget.layout.addSpacing(10)
        self.add_symbol = QPushButton("", self)
        self.add_symbol.setStyleSheet(
            """
            QPushButton {
                border: none;
                background: none;
            }"""
        )
        self.add_symbol.setIcon(QIcon("./app/graphics/icons/plus.png"))
        self.add_symbol.setIconSize(QSize(22, 22))
        self.add_symbol.clicked.connect(self.add_transformation)
        self.buttons_widget.layout.addWidget(self.add_symbol, 1)
        self.layout.addWidget(
            self.buttons_widget, alignment=Qt.AlignmentFlag.AlignRight
        )
        self.setLayout(self.layout)

    def add_transformation(self) -> None:
        """The function called to add the transformation, by calling its saved
        selection function with its class."""
        self.select_func(self.class_)


class AvailableForm(QFrame):
    """This class represents the UI form storing the list of available transformations,
    which can each be added to the list of current transforms."""

    def __init__(self, select_func: Callable, parent: QWidget | None = None):
        """The constructor for the AvailableForm, which stores the list of available
        transformations. This constructs the UI elements for the form title label,
        as well as one transformation for each implemented obfuscation class.

        Args:
            select_func (Callable): A function that takes an obfuscation unit class,
            which should be called whenever an "add" button is pressed to add
            an obfuscation.
            parent (QWidget | None): The parent widget that this widget should be
            placed within. Defaults to None."""
        super(AvailableForm, self).__init__(parent)
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
        self.setContentsMargins(5, 0, 5, 0)
        self.title_label = QLabel("Available Obfuscations", self)
        self.title_label.setFont(QFont(Df.DEFAULT_FONT, 14))
        self.title_label.setStyleSheet("QLabel{color: white;}")
        self.layout.addWidget(
            self.title_label, 1, alignment=Qt.AlignmentFlag.AlignHCenter
        )
        self.transforms = []
        subsubclasses = [
            c.__subclasses__() for c in obfs.ObfuscationUnit.__subclasses__()
        ]
        subsubclasses = [
            c[0]
            for c in subsubclasses
            if len(c) > 0 and not c[0].__name__.startswith("Cli")
        ]
        ts = sorted(subsubclasses, key=lambda c: c.type.value)
        for class_ in ts:
            transform_widget = TransformWidget(class_, select_func, self)
            self.layout.addWidget(transform_widget, 1)
            self.transforms.append(transform_widget)
        self.setLayout(self.layout)
        self._generate_shortcuts()

    def _generate_shortcuts(self) -> None:
        """Automatically generate shortcuts for the first 20 available transformations,
        first using the Ctrl+1, Ctrl+2, ..., Ctrl+0 shortcuts and then using the Alt+1,
        Alt+2, ..., Alt+0 shortcuts. These are sequentially in the same order that each
        transformation is presented, allowing easy power use."""
        cur_index = 0
        for key in ["Ctrl", "Alt"]:
            if cur_index >= len(self.transforms):
                break
            for i in range(10):
                if cur_index >= len(self.transforms):
                    break
                shortcut_keypress = f"{key}+{(i+1)%10}"
                t_shortcut = QShortcut(QKeySequence(shortcut_keypress), self)
                t_widget = self.transforms[cur_index]
                t_shortcut.activated.connect(t_widget.add_transformation)
                cur_index += 1


class SelectedTransformWidget(QWidget):
    """This class represents a single obfuscation transformation that is currently selected by
    the program, storing a coloured label with the class name, and the current number of the
    transformation within the currently selected list. It also offers the ability to be selected
    or deselected, highlighting the background."""

    def __init__(
        self,
        class_: Type[obfs.ObfuscationUnit],
        number: int,
        select_func: Callable,
        parent: QWidget | None = None,
    ):
        """The constructor for the SelectedTransformWidget, initialising the required UI elements
        and state tracking variables.

        Args:
            class_ (Type[obfs.ObfuscationUnit]): The type of obfuscation transformation represented
            by this object, represented by the relevant implementing subclass.
            number (int): The current integer location of this transformation in the list of
            currently selected transformations.
            select_func (Callable): The function to call when this object is selected, providing
            this object itself as the only argument.
            parent (QWidget | None): The parent widget that this widget should be
            placed within. Defaults to None."""
        super(SelectedTransformWidget, self).__init__(parent)
        self.select_func = select_func
        self.class_ = class_
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.__number = number
        self.number_label = QLabel("{}.".format(number), self)
        self.number_label.setFont(QFont(Df.DEFAULT_FONT, 11))
        self.number_label.setStyleSheet("QLabel{color: #AAAAAA}")
        self.layout.addWidget(self.number_label, 1)
        self.box_widget = QWidget(self)
        self.box_widget.layout = QHBoxLayout(self.box_widget)
        self.box_widget.setContentsMargins(0, 0, 0, 0)
        self.box_widget.layout.setContentsMargins(10, 5, 10, 5)
        self.box_widget.setObjectName("TransformBackground")
        self.box_widget.setStyleSheet(
            """
            QWidget#TransformBackground{
                background-color: #34352D;
            }"""
        )
        self.name_label = QLabel(class_.name, self)
        self.name_label.setFont(QFont(Df.DEFAULT_FONT, 11))
        self.name_label.setStyleSheet(
            "QLabel{ color: " + get_transform_colour(class_.type) + "; }"
        )
        self.box_widget.layout.addWidget(self.name_label)
        sp = self.box_widget.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.box_widget.setSizePolicy(sp)
        self.layout.addWidget(self.box_widget, 9)
        self.layout.addSpacing(10)
        self.setLayout(self.layout)
        self.drag_start_pos = None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle a mouse press on the the selected transformation widget. If
        this mouse press is a left button click, then we record the starting
        item of the transform it began to be dragged.

        Args:
            event (QMouseEvent): The UI mouse press event.
        """
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle a mouse move whilst holding down a mouse buttoon. If this
        held button is a left button click, then we move the transformation,
        setting it to drag and follow the cursor. We only do this if the total
        movement is more than 4 pixels - otherwise we do not move it.

        Args:
            event (QMouseEvent): The UI mouse movement event.
        """
        if event.buttons() == Qt.MouseButton.LeftButton:
            if self.drag_start_pos is None:
                return
            moved = event.pos() - self.drag_start_pos
            if abs(moved.x()) + abs(moved.y()) <= 4:
                return
            drag = QDrag(self)
            drag.setMimeData(QMimeData())
            drag.setPixmap(self.box_widget.grab())
            self.box_widget.hide()
            drag.setHotSpot(event.pos() - self.box_widget.pos())
            drag.exec(Qt.DropAction.MoveAction)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle a mouse release event. If the final mouse position is outside of
        the initial widget position, then the selection function is called so that
        the transformation's position in the list of currently selected transforms
        can be updated.

        Args:
            event (QMouseEvent): The UI mouse release event.
        """
        self.drag_start_pos = None
        if 0 <= event.pos().x() - self.box_widget.x() <= self.box_widget.width():
            self.select_func(self)
            self.select()

    def select(self) -> None:
        """Selects this transformation widget, giving it a lighter background colour."""
        self.box_widget.setStyleSheet(
            """
            QWidget#TransformBackground{
                background-color: #48493E;
            }"""
        )

    def deselect(self) -> None:
        """Deselects this transformation widget, returning it to its original darker
        gray backgound colour."""
        self.box_widget.setStyleSheet(
            """
            QWidget#TransformBackground{
                background-color: #34352D;
            }"""
        )

    @property
    def number(self) -> int:
        """Return the current number index location of this transformation in the list of
        currently selected transformations.

        Returns:
            int: The index location of this transformation.
        """
        return self.__number

    @number.setter
    def number(self, new_number: int):
        """Set the number attribute of the selected transform widget, updating its label
        text to correctly reflect this change in number automatically.

        Args:
            new_number (int): The new index location of this transformation.
        """
        self.__number = new_number
        self.number_label.setText("{}.".format(new_number))


class TransformOptionsForm(QFrame):
    """This class represents the UI form storing the user-input options (parameters)
    for the currently selected transform. By default this form is empty, and only has
    content loaded when a relevant transformation is selected, filling it."""

    def __init__(self, remove_func: Callable, parent: QWidget | None = None):
        """The constructor for the TransformOptionsForm, creating the title UI
        label and a "remove transform" button that is hidden by default until some
        transformation is selected.

        Args:
            remove_func (Callable): The function to call (with no arguments) when
            the "Remove Transformation" button is pressed, removing the currently
            selected transformation.
            parent (QWidget | None): The parent widget that this widget should be
            placed within. Defaults to None."""
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
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(2)
        self.layout.setContentsMargins(5, 0, 5, 4)
        self.title_label = QLabel("Transform Options", self)
        self.title_label.setFont(QFont(Df.DEFAULT_FONT, 14))
        self.title_label.setStyleSheet("QLabel{color: white;}")
        self.layout.addWidget(
            self.title_label,
            1,
            alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        )
        self.options = QFrame(self)
        self.layout.addWidget(self.options, 1, alignment=Qt.AlignmentFlag.AlignTop)

        # Create the remove transformation button, and hide it by default.
        self.remove_button = QPushButton("Remove Transform", self)
        self.remove_button.setFont(QFont(Df.DEFAULT_FONT, 12))
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

    def load_transform(self, transform: obfs.ObfuscationUnit | None) -> None:
        """Loads a given transformation (represented by some instance of its ObfuscationUnit
        subclass), inserting the content widget for editing that transformation and showing
        the remove button. If the transform given is None thn this instead unloads the current
        transform, emptying the form content and hiding the remove button.

        Args:
            transform (obfs.ObfuscationUnit | None): The transform to load. Alternatively,
            None if the currently selected transform should be unloaded.
        """
        if transform is None:
            self.remove_button.hide()
            self.layout.removeWidget(self.options)
            self.options = QFrame()
            self.layout.insertWidget(
                1, self.options, alignment=Qt.AlignmentFlag.AlignTop
            )
            return
        self.remove_button.show()
        self.layout.removeWidget(self.options)
        self.options = QFrame()
        transform.edit_gui(self.options)
        self.layout.insertWidget(1, self.options, alignment=Qt.AlignmentFlag.AlignTop)


class CurrentForm(QFrame):
    """This class represents a form that stores the list of currently selected obfuscation
    transformations, which can be selected, moved and traversed by a user."""

    class RemoveBehaviour(Enum):
        """An enumerated type class representing the possible behaviours that can be followed
        when a transformation is removed."""

        SELECT_NEXT = (
            1  # When a transformation is removed, select the following transformation
        )
        DESELECT = (
            2  # When a transformation is removed, deselect and do not select another.
        )

    def __init__(self, parent: QWidget | None = None):
        """The constructor for the CurrentForm, which creates a variety of keyboard shortcuts
        for traversing he list of transformations, then creates a title label, and finally creates
        a scrollable area and some lists for storing the obfuscation transformations that will
        be addded.

        Args:
            parent (QWidget | None): The parent widget that this widget should be
            placed within. Defaults to None."""
        super(CurrentForm, self).__init__(parent)

        # Set the default transformation remove behaviour as selecting the next transformation
        self.remove_behaviour = self.RemoveBehaviour.SELECT_NEXT

        # Create various shortcuts for traversing the transform list
        self.deselect_shortcut = QShortcut(QKeySequence(Df.SHORTCUT_DESELECT), self)
        self.deselect_shortcut.activated.connect(self.deselect_transform)
        self.select_next_shortcut = QShortcut(
            QKeySequence(Df.SHORTCUT_SELECT_NEXT), self
        )
        self.select_next_shortcut.activated.connect(self.select_next_transform)
        self.alt_select_next_shortcut = QShortcut(
            QKeySequence(Df.SHORTCUT_ALT_SELECT_NEXT), self
        )
        self.alt_select_next_shortcut.activated.connect(self.select_next_transform)
        self.select_prev_shortcut = QShortcut(
            QKeySequence(Df.SHORTCUT_SELECT_PREV), self
        )
        get_prev_func = lambda: self.select_next_transform(
            base=lambda n: n - 1, key=lambda i, n: (i - 1 + n) % n
        )
        self.select_prev_shortcut.activated.connect(get_prev_func)
        self.alt_select_prev_shortcut = QShortcut(
            QKeySequence(Df.SHORTCUT_ALT_SELECT_PREV), self
        )
        self.alt_select_prev_shortcut.activated.connect(get_prev_func)
        self.delete_shortcut = QShortcut(QKeySequence(Df.SHORTCUT_DELETE), self)
        self.delete_shortcut.activated.connect(self.remove_selected)
        self.move_up_shortcut = QShortcut(QKeySequence(Df.SHORTCUT_MOVE_UP), self)
        self.move_up_shortcut.activated.connect(self.move_transform_up)
        self.move_down_shortcut = QShortcut(QKeySequence(Df.SHORTCUT_MOVE_DOWN), self)
        self.move_down_shortcut.activated.connect(self.move_transform_down)
        self.copy_shortcut = QShortcut(QKeySequence(Df.SHORTCUT_COPY), self)
        self.copy_shortcut.activated.connect(self.copy_transform)
        self.paste_shortcut = QShortcut(QKeySequence(Df.SHORTCUT_PASTE), self)
        self.paste_shortcut.activated.connect(self.paste_transform)
        self.transform_clipboard = None  # Clipboard for use in copy/pasting

        # Set the layout stylesheet and create the title layout.
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
        self.setContentsMargins(5, 0, 5, 0)
        self.title_label = QLabel("Current Obfuscations", self)
        self.title_label.setFont(QFont(Df.DEFAULT_FONT, 14))
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

        # Create the scroll area and empty contents to add transformation widgets to
        self.scroll_widget = QScrollArea(self)
        self.scroll_widget.setContentsMargins(0, 0, 0, 0)
        self.scroll_widget.setStyleSheet(
            """
            QScrollArea{
                background-color: transparent;
                border: none;
            }"""
            + Df.MINIMAL_SCROLL_BAR_CSS
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

        # Create data structures and variables for tracking the list of selected
        # transformations (and their widgets), as well as the currently selected transform.
        self.selected = []
        self.selected_widgets = []
        self.current_transform = None
        self.current_widget = None
        self.__options_form_reference = None
        self.setAcceptDrops(True)  # Accept drops from dragged selected transforms.

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handles a mouse drag enter event, accepting he mouse drag so long as the object
        being dragged is one of the currently selected transformation widgets.

        Args:
            event (QDragEnterEvent): The UI drag enter event.
        """
        if event.source() in self.selected_widgets:
            event.accept()

    def dropEvent(self, event: QDropEvent) -> None:
        """Handles a 'drop event', where an item being dragged by the mouse is dropped. The
        dropped transformation has its new ordinal location in the list of selected
        transformations caculated from its position and its original location, such that the
        item is moved to an appropriate and intuitive position in the list.

        Args:
            event (QDropEvent): The UI drop event.
        """
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

    def move_transform(self, new_index: int, source: SelectedTransformWidget) -> None:
        """Move a given transformation (a selected transform widget) to a new ordinal
        index position in the list of selected transforms.

        Args:
            new_index (int): The new position of the transform in the current list.
            source (SelectedTransformWidget): The selected transform widget corresponding
            to the selected transform that should be moved.
        """
        source.box_widget.show()
        prev_index = self.selected_widgets.index(source)
        prev_transform = self.selected[prev_index]
        if prev_index < new_index:
            # If being moved down in the list, we remove the transform its current
            # location in the selected list first.
            self.selected = (
                self.selected[:prev_index] + self.selected[(prev_index + 1) :]
            )
            self.selected_widgets = (
                self.selected_widgets[:prev_index]
                + self.selected_widgets[(prev_index + 1) :]
            )
        # We insert the transform at its new location in the list
        self.selected = (
            self.selected[:new_index] + [prev_transform] + self.selected[new_index:]
        )
        self.selected_widgets = (
            self.selected_widgets[:new_index]
            + [source]
            + self.selected_widgets[new_index:]
        )
        if prev_index >= new_index:
            # If being moved up in the list, we *now* remove hthe transform
            # from its original position after it has been placed at its new location.
            self.selected = (
                self.selected[: (prev_index + 1)] + self.selected[(prev_index + 2) :]
            )
            self.selected_widgets = (
                self.selected_widgets[: (prev_index + 1)]
                + self.selected_widgets[(prev_index + 2) :]
            )

        # For each transform in the new list, we update their number to reflect
        # their new positions
        for i in range(self.scroll_content.layout.count()):
            widget = self.scroll_content.layout.itemAt(i).widget()
            widget.number = i + 1

    def add_transform(self, class_: Type[obfs.ObfuscationUnit]) -> None:
        """Adds a new obfuscation transformation to the list of currently selected
        transformations, creating a new SelectedTransformWidget to represent the
        transformation, and appending it to the end of the existing list.

        Args:
            class_ (Type[obfs.ObfuscationUnit]): The class (type) of the obfuscation
            transformation to add.
        """
        number = len(self.selected) + 1
        transform_widget = SelectedTransformWidget(
            class_, number, self.select_transform, self
        )
        self.scroll_content.layout.addWidget(
            transform_widget, alignment=Qt.AlignmentFlag.AlignTop
        )
        self.selected.append(class_.get_gui())
        self.selected_widgets.append(transform_widget)

    def set_transforms(self, transforms: Iterable[obfs.ObfuscationUnit]) -> None:
        """Replace the currently selected list of transforms with an entirely
        new list of transforms, used for e.g. loading in a saved preset.

        Args:
            transforms (Iterable[obfs.ObfuscationUnit]): The sequence of
            obfuscation transformations to replace the currently selected list with.
        """
        self.deselect_transform()  # First deselect any existing transform
        for transform in self.selected:
            self.remove_transform(transform)
        self.current_transform = None
        self.current_widget = None
        for i, transform in enumerate(transforms):
            transform_widget = SelectedTransformWidget(
                transform.__class__, i + 1, self.select_transform, self
            )
            self.scroll_content.layout.addWidget(
                transform_widget, alignment=Qt.AlignmentFlag.AlignTop
            )
            self.selected.append(transform)
            self.selected_widgets.append(transform_widget)

    def remove_transform(self, transform: obfs.ObfuscationUnit) -> None:
        """Remove a given obfuscation transformation from the list of currently
        selected transforms, updating numberings as appropriate.

        Args:
            transform (obfs.ObfuscationUnit): The obfuscation unit corresponding
            to the unique obfuscation transformation that should be removed.
        """
        index = self.selected.index(transform)
        widget = self.selected_widgets[index]
        self.selected = self.selected[:index] + self.selected[(index + 1) :]
        self.selected_widgets = (
            self.selected_widgets[:index] + self.selected_widgets[(index + 1) :]
        )
        self.scroll_content.layout.removeWidget(widget)
        # Update the numbers of transformations in the selected list.
        for i in range(index, len(self.selected)):
            self.selected_widgets[i].number = i + 1

    def select_transform(self, widget: SelectedTransformWidget) -> None:
        """Select a given obfuscaction transform from the list of currently
        seelcted transforms, deselecting (and updating) any currently
        selected transform, before loading in the options of the newly selected
        obfuscation transformation.

        Args:
            widget (SelectedTransformWidget): The widget corresponding to the
            unique obfuscation transformation that should be selected.
        """
        if self.current_widget is not None:
            self.current_transform.load_gui_values()
            self.current_widget.deselect()
        self.current_transform = self.selected[self.selected_widgets.index(widget)]
        self.current_widget = widget
        if self.__options_form_reference is not None:
            self.__options_form_reference.load_transform(self.current_transform)

    def select_next_transform(
        self, base: Callable | None = None, key: Callable | None = None
    ) -> None:
        """Selects the next transform from the list of currently selected transform, optionally
        using given functions to determine the next transformation that should be selected, or
        otherwise just employing a circular increment.

        Args:
            base (Callable | None): The function to call to generate the first base value that
            should be selected when this function is called with no transform currently selected.
            Defaults to None, meaning an index of 0 is selected by default.
            key (Callable | None): The function to call to generate the next transform to select
            in the list, taking the current index and the number of existing transformations as
            an arguent. Defaults to None, which corresponds to a circular increment.
        """
        if len(self.selected) == 0:
            return
        if self.current_transform is None:
            # If no transform is currently selected, load the base.
            if base is None:
                new_index = 0
            else:
                new_index = base(len(self.selected))
        else:
            # If a transform is currently selected, load the next index using the key.
            self.current_transform.load_gui_values()
            self.current_widget.deselect()
            if key is None:
                key = lambda i, n: (i + 1) % n
            index = self.selected.index(self.current_transform)
            new_index = key(index, len(self.selected))
        # Select the new widget and ensure it remains visible, loading its options.
        self.current_transform = self.selected[new_index]
        self.current_widget = self.selected_widgets[new_index]
        self.current_widget.select()
        self.scroll_widget.ensureWidgetVisible(self.current_widget, yMargin=1)
        if self.__options_form_reference is not None:
            self.__options_form_reference.load_transform(self.current_transform)

    def deselect_transform(self) -> None:
        """Deselects any currently selected transform, doing nothing if nothing is
        already selected. Updates the transform options form accordingly."""
        if self.current_widget is not None:
            self.current_widget.deselect()
        self.current_transform = None
        self.current_widget = None
        if self.__options_form_reference is not None:
            self.__options_form_reference.load_transform(self.current_transform)

    def remove_selected(self) -> None:
        """Removes any currently selected transform according to the currently stored
        remove behaviour, eiher selecting the next available transform or completely
        deselecting, not selecting any following transform."""
        if self.remove_behaviour == self.RemoveBehaviour.DESELECT:
            # With DESELECT behaviour, simply remove the selected transform.
            if self.current_transform is not None and self.current_widget is not None:
                self.remove_transform(self.current_transform)
            self.current_transform = None
            self.current_widget = None
            if self.__options_form_reference is not None:
                self.__options_form_reference.load_transform(None)
        elif self.remove_behaviour == self.RemoveBehaviour.SELECT_NEXT:
            # With SELECT_NEXT behaviour, remove the selected transform, and select
            # the next transform circularly available in the current list of
            # selected transforms, where such a transform exists.
            if self.current_transform is not None and self.current_widget is not None:
                index = self.selected.index(self.current_transform)
                self.remove_transform(self.current_transform)
                if len(self.selected) == 0:
                    self.current_transform = None
                    self.current_widget = None
                elif len(self.selected) > index:
                    self.current_transform = self.selected[index]
                    self.current_widget = self.selected_widgets[index]
                    self.current_widget.select()
                else:
                    self.current_transform = self.selected[index - 1]
                    self.current_widget = self.selected_widgets[index - 1]
                    self.current_widget.select()
            else:
                self.current_transform = None
                self.current_widget = None
            if self.__options_form_reference is not None:
                self.__options_form_reference.load_transform(self.current_transform)

    def move_transform_up(self) -> None:
        """Moves the currently selected transform one position upwards in the list, circularly
        looping back round to the bottom of the list if already at the top."""
        if self.current_transform is None:
            return
        length = len(self.selected)
        index = (length + self.selected.index(self.current_transform) - 1) % length
        self.scroll_content.layout.removeWidget(self.current_widget)
        self.scroll_content.layout.insertWidget(index, self.current_widget)
        self.move_transform(index, self.current_widget)
        # We must use a single shot timer to ensure the moved transform remains visible,
        # so that the remaining UI elements have time to show and update their sizes.
        QTimer.singleShot(
            0,
            functools.partial(
                self.scroll_widget.ensureWidgetVisible,
                self.current_widget,
                50,
                self.current_widget.height(),
            ),
        )

    def move_transform_down(self) -> None:
        """Moves the currently selected transform one position downwards in the list, circularly
        looping back round to the top of the list if already at the bottom."""
        if self.current_transform is None:
            return
        index = (self.selected.index(self.current_transform) + 1) % len(self.selected)
        self.scroll_content.layout.removeWidget(self.current_widget)
        self.scroll_content.layout.insertWidget(index, self.current_widget)
        self.move_transform(index, self.current_widget)
        # We must use a single shot timer to ensure the moved transform remains visible,
        # so that the remaining UI elements have time to show and update their sizes.
        QTimer.singleShot(
            0,
            functools.partial(
                self.scroll_widget.ensureWidgetVisible,
                self.current_widget,
                50,
                self.current_widget.height(),
            ),
        )

    def copy_transform(self) -> None:
        """Copies the currently selected transformation to the transform class' clipboard."""
        self.transform_clipboard = (
            self.current_transform.__class__,
            self.current_transform.to_json(),
        )

    def paste_transform(self) -> None:
        """Pastes the currently copied transform (stored in the class' clipboard), inserting it at
        the position following the currently seected transform, or at the end of the list if no
        transformations are currently selected."""
        if self.transform_clipboard is None:
            return
        # Load the transform from the clipboard, and get the position
        transform_class, transform_json = self.transform_clipboard
        if self.current_transform is None:
            new_index = len(self.selected)
        else:
            new_index = self.selected.index(self.current_transform) + 1

        # Create a new instance of the clipboard transform, copying it.
        new_transform = transform_class.from_json(transform_json)
        transform_widget = SelectedTransformWidget(
            new_transform.__class__, new_index + 1, self.select_transform, self
        )
        self.scroll_content.layout.insertWidget(
            new_index, transform_widget, alignment=Qt.AlignmentFlag.AlignTop
        )

        # Insert the copied transformation, and update the numbers of all transformations.
        self.selected = (
            self.selected[:new_index] + [new_transform] + self.selected[new_index:]
        )
        self.selected_widgets = (
            self.selected_widgets[:new_index]
            + [transform_widget]
            + self.selected_widgets[new_index:]
        )
        for i in range(new_index + 1, len(self.selected)):
            self.selected_widgets[i].number = i + 1
        self.select_transform(transform_widget)
        transform_widget.select()
        # We must use a single shot timer to ensure the moved transform remains visible,
        # so that the remaining UI elements have time to show and update their sizes.
        QTimer.singleShot(
            0,
            functools.partial(
                self.scroll_widget.ensureWidgetVisible,
                transform_widget,
                50,
                transform_widget.height(),
            ),
        )

    def get_transforms(self) -> list[obfs.ObfuscationUnit]:
        """Returns:
        list[obfs.ObfuscationUnit]: The list of currently selected transforms."""
        return self.selected

    def load_selected_values(self) -> None:
        """For all transforms in the list of current selections, updates their internal
        representations to use the values currently input by users in the GUI option menus."""
        if self.current_transform is not None:
            self.current_transform.load_gui_values()

    def add_options_form(self, options_form: TransformOptionsForm) -> None:
        """Add a reference to the transformation options form, such that relevant GUI
        menus allowing the user input of these options can be loaded.

        Args:
            options_form (TransformOptionsForm): The transform options form to reference."""
        self.__options_form_reference = options_form


class MetricsForm(QFrame):
    """This class repersents the UI form that displays the list of currently calculated
    metric groups (i.e. metrics), allowing the selection and deselection of these metric
    groups to both hide them and forcefully prevent their computation if desired. This class
    also implements methods for calculating and updating the values of metrics after obfuscation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """The constructor for the MetricsForm, creating UI elements for the title labe,
        a scroll area for the metrics contents, and then initialising the list of computed
        metrics with empty N/A values, waiting for obfuscation to occur.

        Args:
            parent (QWidget | None): The parent widget that this widget should be
            placed within. Defaults to None."""
        super(MetricsForm, self).__init__(parent)

        # Set the style sheet layout, and create the title label
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
        self.setMinimumWidth(250)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(2)
        self.setContentsMargins(5, 8, 5, 15)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel("Obfuscation Metrics", self)
        self.title_label.setFont(QFont(Df.DEFAULT_FONT, 14))
        self.title_label.setStyleSheet("QLabel{color: white;}")
        self.layout.addWidget(
            self.title_label,
            alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
        )

        # Create the scrollable area to store the metric contents.
        self.scroll_widget = QScrollArea(self)
        self.scroll_widget.setStyleSheet(
            """
            QScrollArea{
                background-color: transparent;
                border: none;
            }"""
            + Df.MINIMAL_SCROLL_BAR_CSS
        )
        self.scroll_widget.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll_widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_widget.setWidgetResizable(True)

        # Create the scroll area content widget to store actual metric values.
        self.metric_widget = QWidget(self.scroll_widget)
        self.metric_widget.setObjectName("MetricWidget")
        self.metric_widget.setStyleSheet(
            """
            QWidget#MetricWidget{
                background-color: transparent;
                border: none;
            }"""
        )
        self.metric_widget.layout = QVBoxLayout(self.metric_widget)
        self.metric_widget.layout.setContentsMargins(5, 2, 8, 5)
        self.metric_widget.layout.setSpacing(12)
        self.scroll_widget.setWidget(self.metric_widget)
        self.layout.addWidget(self.scroll_widget)
        self.setLayout(self.layout)

        # If not disabled, initialise metric computations with default N/A values.
        if config.CALCULATE_COMPLEXITY:
            self.load_metrics(None, None)

    def toggle_checkbox(self, metric: Type[CodeMetricUnit]) -> None:
        """Toggles the metric calculation checkbox for a specific metric group,
        hiding each of the relevant metric widgets, and creating a crossthrough
        graphic on the metric group. Alternatively, if toggling to unhide, the
        reverse is performed, unstrikethrough-ing the metric group label and
        revealing all of the individual metric calculations, where they exist.

        Args:
            metric (Type[CodeMetricUnit]): The metric group to toggle.
        """
        # Retrieve relevant checkbox information
        if metric not in self.checkbox_map:
            return
        checkbox = self.checkbox_map[metric]
        if checkbox is None:
            return
        # Change the metric name label formatting depending on the checkbox status
        name_label = checkbox.parent().layout().itemAt(0).widget()
        if checkbox.isChecked():
            name_colour = "white"
            name_font = QFont(Df.DEFAULT_FONT, 12)
        else:
            name_colour = "#727463"
            name_font = QFont(Df.DEFAULT_FONT, 12)
            name_font.setStrikeOut(True)
            name_font.setItalic(True)
        name_label.setFont(name_font)
        name_label.setStyleSheet(
            "QLabel{color: " + name_colour + ";}" + Df.GENERAL_TOOLTIP_CSS
        )
        # Hide/show the metrics themselves depending on the checkbox status
        unit_widget = checkbox.parent().parent()
        for i in range(1, unit_widget.layout().count()):
            widget = unit_widget.layout().itemAt(i).widget()
            if widget is None:
                continue
            if checkbox.isChecked():
                widget.show()
            else:
                widget.hide()

    def process_metric_groups(
        self, source: CSource, obfuscated: CSource, metrics: list[Type[CodeMetricUnit]]
    ) -> list[Type[CodeMetricUnit]]:
        """Performs a linear pass through the set of available metrics to process, attempting
        to calculate each group depending on whether required dependencies have been satisfied.
        For each such satisfiable group, all metrics within that group are calcualted and formatted
        at the end othe metrics UI form as additional widgets. A list of metric groups that were
        processed in this pass are then returned.

        Args:
            source (CSource): The original source C program.
            obfuscated (CSource): The final obfuscated C program.
            metrics (list[Type[CodeMetricUnit]]): The list of metric groups that still need to
            be processed.

        Returns:
            list[Type[CodeMetricUnit]]: The list of metric groups that were processed in this pass.
        """
        processed = []
        for metric in metrics:
            # Retrieve the list of missing predecessors for the metric
            missing_preds = [
                req
                for req in metric.predecessors
                if req in metrics and req not in processed
            ]
            # Only process metrics with fulfilled predecessors
            if len(missing_preds) > 0:
                continue
            processed.append(metric)

            # Create a widget corresponding to the metric group, and label it.
            metric_unit = metric()
            unit_widget = QWidget(self.metric_widget)
            unit_layout = QVBoxLayout(unit_widget)
            unit_layout.setContentsMargins(0, 0, 0, 0)
            unit_layout.setSpacing(0)
            name_widget = QWidget(unit_widget)
            name_layout = QHBoxLayout(name_widget)
            name_layout.setContentsMargins(0, 0, 5, 0)
            name_layout.setSpacing(0)
            if hasattr(metric_unit, "gui_name"):
                name_label = QLabel(metric_unit.gui_name)
            else:
                name_label = QLabel(metric_unit.name)
            if metric not in self.checkbox_map or self.checkbox_map[metric]:
                name_colour = "white"
                name_font = QFont(Df.DEFAULT_FONT, 12)
            else:
                name_colour = "#727463"
                name_font = QFont(Df.DEFAULT_FONT, 12)
                name_font.setStrikeOut(True)
                name_font.setItalic(True)
            name_label.setFont(name_font)
            name_label.setStyleSheet(
                "QLabel{color: " + name_colour + ";}" + Df.GENERAL_TOOLTIP_CSS
            )
            if hasattr(metric_unit, "name_tooltip"):
                name_label.setToolTip(metric_unit.name_tooltip)
            name_layout.addWidget(name_label)
            name_layout.addStretch()

            # Create a checkbox for the metric group to allow the enabling/disabling of the group.
            metric_checkbox = QCheckBox(name_widget)
            metric_checkbox.setStyleSheet(
                "QCheckBox{color: #727463;}" + Df.GENERAL_TOOLTIP_CSS
            )
            metric_checkbox.setToolTip(
                "Enable/disable calculation. Disabling will improve performance."
            )
            if metric in self.checkbox_map:
                checked = self.checkbox_map[metric]
                metric_checkbox.setChecked(checked)
            else:
                metric_checkbox.setChecked(True)
            self.checkbox_map[metric] = metric_checkbox
            metric_checkbox.stateChanged.connect(
                functools.partial(self.toggle_checkbox, metric)
            )
            name_layout.addWidget(metric_checkbox)
            unit_layout.addWidget(name_widget)
            unit_layout.addSpacing(2)
            unit_widget.setLayout(unit_layout)
            self.metric_widget.layout.addWidget(
                unit_widget, alignment=Qt.AlignmentFlag.AlignTop
            )
            if not metric_checkbox.isChecked():
                continue  # Only calculate enabled metric groups

            # Calculate the list of metrics in the group, and add UI widgets
            # for each one. Left justify names and right justify values.
            if source is not None and obfuscated is not None:
                metric_unit.calculate_metrics(source, obfuscated)
            metric_vals = metric_unit.get_metrics()
            if metric_vals is not None:
                for i, value_pair in enumerate(metric_vals):
                    metric_widget = QWidget(unit_widget)
                    metric_widget.setStyleSheet(Df.GENERAL_TOOLTIP_CSS)
                    metric_layout = QHBoxLayout(metric_widget)
                    metric_layout.setContentsMargins(0, 0, 0, 0)
                    metric_layout.setSpacing(0)
                    name, m_val = value_pair
                    metric_label = QLabel(" " + name)
                    metric_label.setFont(QFont(Df.DEFAULT_FONT, 9))
                    metric_label.setStyleSheet("QLabel{color: white;}")
                    if isinstance(m_val, Tuple):
                        # Format delta values to be in brackets
                        value_label = QLabel(
                            m_val[0] + " ({})".format(",".join(m_val[1:]))
                        )
                    else:
                        value_label = QLabel(m_val)
                    value_label.setFont(QFont(Df.DEFAULT_FONT, 9, 200))
                    value_label.setStyleSheet("QLabel{color: #878787;}")
                    if name in metric_unit.tooltips:
                        # Add tooltips to the metric where available
                        metric_widget.setToolTip(metric_unit.tooltips[name])
                    metric_layout.addWidget(metric_label)
                    metric_layout.addStretch()
                    metric_layout.addWidget(value_label)
                    metric_widget.setLayout(metric_layout)
                    unit_layout.addWidget(metric_widget)
            else:
                # Handle non-avilable metrics with a default value of "N/A"
                na_label = QLabel("N/A")
                na_label.setFont(QFont(Df.DEFAULT_FONT, 10))
                na_label.setStyleSheet("QLabel{color: white;}")
                unit_layout.addWidget(na_label)

        # Return the list of metrics successfully processed in this pass
        return processed

    def load_metrics(self, source: CSource, obfuscated: CSource) -> None:
        """Calculates and loads all available metric values for all selected metric groups,
        populating the metrics UI form with these calculated values.

        Args:
            source (CSource): The original source C program.
            obfuscated (CSource): The final obfuscated C program.
        """
        # Update the list of checkbox selections for metric groups.
        if not hasattr(self, "checkbox_map"):
            self.checkbox_map = {}
        else:
            for key in self.checkbox_map.keys():
                self.checkbox_map[key] = self.checkbox_map[key].isChecked()
        # Remove UI elements corresponding to existing metrics.
        QToolTip.setFont(QFont(Df.DEFAULT_FONT, 13))
        for i in reversed(range(self.metric_widget.layout.count())):
            item = self.metric_widget.layout.itemAt(i)
            widget = item.widget()
            if widget is None:
                self.metric_widget.layout.removeItem(item)
                continue
            self.metric_widget.layout.removeWidget(widget)
            widget.setParent(None)
        metrics = CodeMetricUnit.__subclasses__()
        # Add and compute all metric groups where enabled to satisfy predecessor constraints
        while len(metrics) != 0:
            processed = self.process_metric_groups(source, obfuscated, metrics)
            if len(processed) == 0:
                log(
                    "Metrics {} have unsatisfiable predecessor dependencies!".format(
                        metrics
                    ),
                    print_err=True,
                )
                return
            for metric in processed:
                metrics.remove(metric)
        self.metric_widget.layout.addStretch()


class GeneralOptionsForm(QFrame):
    """This class represents the UI form storing general options, including a label stating
    the program name and version and general buttons for obfuscation, loading/saving obfuscated
    files and obfuscation schemes (compositions), and for quitting."""

    def __init__(
        self,
        transforms_func: Callable,
        set_transforms_func: Callable,
        load_gui_vals_func: Callable,
        source_form: SourceEditor,
        obfuscated_form: SourceEditor,
        parent: QWidget | None = None,
    ):
        """The constructor for the GeneralOptionsForm, creating shortcuts for obfuscation
        and for saving obfuscated files / obfuscation schemes, and then creating UI elements
        used in the form. These include the program name / version title label, and the set
        of buttons providing general program options.

        Args:
            transforms_func (Callable): A function taking no arguments that returns a tuple
            of the currently selected transforms in the GUI.
            set_transforms_func (Callable): A function that takes a list of transforms
            (ObfuscationUnit subclass instances) and loads them into the GUI as the newly
            currently selected transforms.
            load_gui_vals_func (Callable): A function to load all current transformation
            option values input by users in the GUI into their repective obfuscation
            transformation units.
            source_form (SourceEditor): The SourceEditor widget corresponding to the
            original source program.
            obfuscated_form (SourceEditor): The SourceEditor widget corresponding to
            the final obfuscated output program.
            parent (QWidget | None): The parent widget that this widget should be
            placed within. Defaults to None."""
        super(GeneralOptionsForm, self).__init__(parent)
        self.__transforms_reference = transforms_func
        self.__set_transforms_func = set_transforms_func
        self.__load_selected_gui_reference = load_gui_vals_func
        self.__source_form_reference = source_form
        self.__obfuscated_form_reference = obfuscated_form

        # Create shorcuts for obfuscation, and for saving files / compositions
        self.obfuscate_shortcut = QShortcut(QKeySequence(Df.SHORTCUT_OBFUSCATE), self)
        self.obfuscate_shortcut.activated.connect(self.obfuscate)
        self.save_obfs_shortcut = QShortcut(QKeySequence(Df.SHORTCUT_SAVE_OBFS), self)
        self.save_obfs_shortcut.activated.connect(self.save_obfuscated)
        self.save_comp_shortcut = QShortcut(QKeySequence(Df.SHORTCUT_SAVE_COMP), self)
        self.save_comp_shortcut.activated.connect(self.save_composition)

        # Set the UI form stylesheet, lyout and title label.
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
        self.seed = config.SEED
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        self.title_label = QLabel(config.NAME + " " + config.VERSION, self)
        self.title_label.setFont(QFont(Df.DEFAULT_FONT, 14, 1000))
        self.title_label.setStyleSheet("QLabel{color: white;}")
        self.layout.addWidget(
            self.title_label, 1, alignment=Qt.AlignmentFlag.AlignHCenter
        )

        # Create the option buttons available in this form.
        self.obfuscate_button = self.make_button("Obfuscate")
        self.obfuscate_button.setObjectName("ObfuscateButton")
        self.cfg_button = self.make_button("View control flow")
        self.cfg_button.clicked.connect(self.show_control_flow)
        self.obfuscate_button.clicked.connect(self.obfuscate)
        self.load_source_button = self.make_button("Load source file")
        self.load_source_button.clicked.connect(self.load_source)
        self.save_obfuscated_button = self.make_button("Save obfuscated file")
        self.save_obfuscated_button.clicked.connect(self.save_obfuscated)
        self.load_transformations_button = self.make_button("Load transformations")
        self.load_transformations_button.clicked.connect(self.load_composition)
        self.save_transformations_button = self.make_button("Save transformations")
        self.save_transformations_button.clicked.connect(self.save_composition)
        self.quit_button = self.make_button("Quit")
        self.quit_button.clicked.connect(QCoreApplication.quit)
        self.setLayout(self.layout)

    def make_button(self, msg: str) -> QPushButton:
        """Creates a button with a given label message, using the default font with size 12 and
        adding it to the layout widget. This is a function primarily for modularity of code, to
        avoid repetition.

        Args:
            msg (str): The label of the button that is created.

        Returns:
            QPushButton: The created button, with the given label.
        """
        button = QPushButton(msg, self)
        button.setFont(QFont(Df.DEFAULT_FONT, 12))
        self.layout.addWidget(button, 1)
        return button

    def obfuscate(self) -> None:
        """This function performs obfuscation using the currently loaded C source
        program information and the list of currently selected transforms. In the
        case that obfuscation fails for some reason then an error will be displayed,
        but otherwise the obfuscated source form contents will be filled and metrics
        will be updated if the relevant config settings are set. This also handles
        a progress bar, showing how long the obfuscation pipeline is in processing."""
        # Create an obfuscation pipeline from the set of currently selected transformations
        self.__load_selected_gui_reference()
        pipeline = obfs.Pipeline(self.seed, *self.__transforms_reference())

        # Copy the source contents, updating the parsed AST if the contents were updated
        source = deepcopy(self.__source_form_reference.source)
        source.contents = self.__source_form_reference.toPlainText()
        if self.__source_form_reference.modified_from_read:
            source.update_t_unit()
        source.fpath = self.__obfuscated_form_reference.source.fpath

        if not source.valid_parse:
            # If invalid code is given, display an error and reset
            # the obfuscated form (code editor) and complexity metrics
            self.__obfuscated_form_reference.add_source(
                CSource(self.__obfuscated_form_reference.source.fpath, "", FileAST([]))
            )
            if config.CALCULATE_COMPLEXITY:
                self.parent().metrics_form.load_metrics(None, None)
            error_msg = (
                "An error occurred whilst parsing your C source code, and so\n"
                "obfuscation cannot be applied."
            )
            if source.error_context is not None:
                error_msg = "<html>" + error_msg
                error_msg.replace("\n", "<br></br>")
                error_msg += " Here is some more context for your error:<br></br>"
                error_msg += " <b>/{}:{}</b></html>".format(
                    self.__source_form_reference.get_file_name(), source.error_context
                )
            display_error(error_msg)
            return

        # If the source was parsed successfully, perform the transformation, setting
        # the relevant progress bar to be used and calculating complexity metrics where
        # relevant (if enabled).
        if config.CALCULATE_COMPLEXITY:
            original_source = deepcopy(source)
        if len(pipeline.transforms) != 0:
            self.parent().progress_bar.setRange(0, len(pipeline.transforms))
            self.parent().update_progress(0)
        obfuscated = pipeline.process(source, self.parent().update_progress)
        self.parent().update_progress(-1)
        self.__obfuscated_form_reference.add_source(obfuscated)
        if config.CALCULATE_COMPLEXITY:
            self.parent().metrics_form.load_metrics(original_source, obfuscated)

    def show_control_flow(self) -> None:
        pass  # TODO comehere

    def load_source(self) -> None:
        """Loads a new source C program through a file dialog with the user, allowing
        use of the native GUI interface to load a program file.
        """
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile)
        dialog.setFilter(QDir.Filter.Readable)
        dialog.setNameFilter("C source files (*.c)")
        if not dialog.exec():
            return
        files = dialog.selectedFiles()
        if len(files) == 0:
            return  # Exit quietly if the user exits the file dialog.
        source = CSource(files[0])
        if source.contents is None or not source.valid_parse:
            # Display a relevant error if the provided source file is invalid
            error_msg = (
                "An error occurred whilst parsing your C file, and so it cannot\n"
                "be loaded."
            )
            if source.error_context is not None:
                error_msg = "<html>" + error_msg
                error_msg.replace("\n", "<br></br>")
                error_msg += " Here is some more context for your error:<br></br>"
                error_msg += " <b>/{}:{}</b></html>".format(
                    self.__source_form_reference.get_file_name(), source.error_context
                )
            display_error(error_msg)
            return
        # Load the selected source file into the original source form contents.
        self.__source_form_reference.add_source(source)

    def load_composition(self) -> None:
        """Loads a new composition (obfuscation scheme) through a file dialog with
        the user, allowing use of the native GUI interface to load a composition file.
        This file dialog begins in the local ./compositions path by default, and only
        allows the selection of .cobf files created by the program (actually just JSON).
        """
        compositions_path = os.path.join(os.getcwd(), "compositions/")
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
            return  # Exit quitely if the user exits the file dialog

        # Attempt to load a Pipeline from the supplied obfuscation file, displaying a relevant
        # error if the file is corrupted.
        try:
            with open(files[0], "r") as f:
                transform_pipeline = obfs.Pipeline.from_json(f.read(), use_gui=True)
                if transform_pipeline is None:
                    display_error(
                        "The given composition file is corrupted, and so it cannot be loaded.\n"
                        "Please check the most recent log file if you are attempting to make\n"
                        "manual changes. Otherwise, you should remake your obfuscation scheme."
                    )
                    return
                if config.SEED is None:  # Only use the saved seed if no seed was given
                    self.seed = transform_pipeline.seed
                # If valid, load the set of transforms into the current list.
                self.__set_transforms_func(transform_pipeline.transforms)
        except:
            return

    def save_obfuscated(self) -> None:
        """Save the current obfuscated program (the current contents of the obfuscated
        source form) through a file dialogue with the user, allowing them to save the
        file as a .c file or any other file they want, and writing out in plain text.
        """
        file, _ = QFileDialog.getSaveFileName(
            self, "Save Obfuscated C", "", "C Source Files (*.c);;All Files (*)"
        )
        if not file or len(file) == 0:
            return
        with open(file, "w+") as f:
            f.write(self.__obfuscated_form_reference.toPlainText())
        prev_source = self.__obfuscated_form_reference.source
        self.__obfuscated_form_reference.add_source(
            CSource(file, prev_source.contents, prev_source.t_unit)
        )

    def save_composition(self) -> None:
        """Save the current composition (the current obfuscation scheme) through a file
        dialog with the uer, only allowing the file to be saved as a .cobf file which
        itself stores the JSON representation of the current pipeline, including all of
        its obfuscation transformations in sequence, and its random seed."""
        compositions_path = os.path.join(os.getcwd(), "compositions/")
        if not os.path.exists(compositions_path):
            os.mkdir(compositions_path)
        file, _ = QFileDialog.getSaveFileName(
            self, "Save Composition", compositions_path, "C Obfuscation Files (*.cobf)"
        )
        if not file or len(file) == 0:
            return
        with open(file, "w+") as f:
            self.__load_selected_gui_reference()
            pipeline = obfs.Pipeline(self.seed, *self.__transforms_reference())
            f.write(pipeline.to_json())


class SelectionForm(QWidget):
    """The vertical widget in the middle of the GUI, stacking the list of available
    transformations above the list of currently selected obfuscation transformations."""

    def __init__(self, resize_func: Callable, parent: QWidget | None = None) -> None:
        """The constructor for the SelectionForm object, creating a layout into which
        the available and currently selected transformation forms are vertically placed.

        Args:
            resize_func (Callable): A function that takes no arguments, and which will
            update the positions name labels above each source editor file when called
            after a GUI resize has ocurred.
            parent (QWidget | None): The parent widget that this widget should be
            placed within. Defaults to None."""
        super(SelectionForm, self).__init__(parent)
        self.resize_func = resize_func
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.available_form = AvailableForm(self.add_transform, self)
        self.layout.addWidget(self.available_form, 1)
        self.current_form = CurrentForm(self)
        self.layout.addWidget(self.current_form, 1)
        self.setLayout(self.layout)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handles a GUI resize event, extending the existing resizing functionality by
        calling a function for updating the position of source editor file name labels,
        such that these positions are appropriately updates after resizing of the GUI.

        Args:
            event (QResizeEvent): The GUI resize event.
        """
        super(SelectionForm, self).resizeEvent(event)
        self.resize_func()

    def add_transform(self, class_: Type[obfs.ObfuscationUnit]) -> None:
        """Adds a new obfuscation transform to the list of currently selected
        obfuscation transforms stored within the CurrentForm widget.

        Args:
            class_ (Type[obfs.ObfuscationUnit]): The type of obfuscation
            transformation to add (i.e. the type of it as an ObfuscationUnit
            subclass)."""
        self.current_form.add_transform(class_)


class MiscForm(QWidget):
    """The vertical widget on the right of the GUI, stacking the list of options for
    the currently selected transform, above the list of last-calculated metrics, above
    the progress bar, above the list of general program option buttons."""

    def __init__(
        self,
        transforms_func: Callable,
        set_transforms_func: Callable,
        load_gui_vals_func: Callable,
        source_form: SourceEditor,
        obfuscated_form: SourceEditor,
        remove_func: Callable,
        resize_func: Callable,
        parent: QWidget | None = None,
    ):
        """The constructor for the MiscForm object, creating each of the individual
        GUI components and hen stacking them vertically on top of each other with
        correct alignments to permit the expansion of these elements as is required.

        Args:
            transforms_func (Callable): A function taking no arguments that returns a tuple
            of the currently selected transforms in the GUI.
            set_transforms_func (Callable): A function that takes a list of transforms
            (ObfuscationUnit subclass instances) and loads them into the GUI as the newly
            currently selected transforms.
            load_gui_vals_func (Callable): A function to load all current transformation
            option values input by users in the GUI into their repective obfuscation
            transformation units.
            source_form (SourceEditor): The SourceEditor widget corresponding to the
            original source program.
            obfuscated_form (SourceEditor): The SourceEditor widget corresponding to
            the final obfuscated output program.
            remove_func (Callable): The function to call (with no arguments) when
            the "Remove Transformation" button is pressed, removing the currently
            selected transformation.
            resize_func (Callable): A function that takes no arguments, and which will
            update the positions name labels above each source editor file when called
            after a GUI resize has ocurred.
            parent (QWidget | None): The parent widget that this widget should be
            placed within. Defaults to None."""
        super(MiscForm, self).__init__(parent)

        # Initialse the layout and add the transform options form and metrics form.
        # Top align the transform options to let let metrics expand centrally.
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.resize_func = resize_func
        self.transform_options = TransformOptionsForm(remove_func, self)
        self.layout.addWidget(
            self.transform_options, alignment=Qt.AlignmentFlag.AlignTop
        )
        self.metrics_form = MetricsForm(self)
        self.layout.addWidget(self.metrics_form)

        # Create the progress bar and add it below them metrics form, aligned
        # to the bottom to allow expansion of the transform options and metrics.
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 13)
        self.progress_bar.setValue(0)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_bar.setFont(QFont(Df.DEFAULT_FONT, 10, 1000))
        self.base_format = "%v/%m (%p%)"
        self.progress_palette = QPalette()
        self.progress_palette.setColor(QPalette.ColorRole.Text, QColor("#727463"))
        self.progress_bar.setPalette(self.progress_palette)
        self.progress_bar.setFormat("Not currently obfuscating...")
        self.setStyleSheet(
            """
            QProgressBar{
                border-style: solid;
                border-color: #848484;
                border-radius: 7px;
                border-width: 2px;
                background-color: #272822;
                margin: 0px 0px 0px 0px;
            }
            QProgressBar::chunk{
                background-color: #2ed573;
                border-style: solid;
                border-color: none;
                border-radius: 7px;
                border-width: 2px;
            }"""
        )
        self.layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignBottom)

        # Create the general options form and add it below the progress bar, aligned
        # to the bottom of the GUI.
        self.general_options = GeneralOptionsForm(
            transforms_func,
            set_transforms_func,
            load_gui_vals_func,
            source_form,
            obfuscated_form,
            self,
        )
        self.layout.addWidget(
            self.general_options, alignment=Qt.AlignmentFlag.AlignBottom
        )
        self.setLayout(self.layout)

    def update_progress(self, index: int) -> None:
        """Update the progress bar as to some obfuscation progress, replacing its current
        value with the new progress index, formatting the progess bar appropriately.

        Args:
            index (int): The new progress index value for the progress bar. Alternatively,
            a value of -1 (or the max value) indicates that progress has complete and hence
            the progress bar is emptied, and set to say "Not currently obfuscating...".
        """
        self.progress_bar.setValue(max(index, 0))
        if index == -1 or index == self.progress_bar.maximum():
            self.progress_bar.setFormat("Not currently obfuscating...")
            self.progress_palette.setColor(QPalette.ColorRole.Text, QColor("#727463"))
            self.progress_bar.setPalette(self.progress_palette)
        else:
            self.progress_bar.setFormat(self.base_format)
            self.progress_palette.setColor(
                QPalette.ColorRole.Text, QColorConstants.White
            )
            self.progress_bar.setPalette(self.progress_palette)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handles a GUI resize event, extending the existing resizing functionality by
        calling a function for updating the position of source editor file name labels,
        such that these positions are appropriately updates after resizing of the GUI.

        Args:
            event (QResizeEvent): The GUI resize event.
        """
        super(MiscForm, self).resizeEvent(event)
        self.resize_func()


class NameLabel(QWidget):
    """This class represents a name label widget, which stores the combination
    of some file name label and some file icon, such that these name labels can
    be displayed against source editors to distinguish their contents."""

    def __init__(
        self,
        icon: QIcon,
        icon_size: QSize,
        filename: str,
        parent: QWidget | None = None,
    ):
        """The constructor for the NameLabel object, initialising the widget
        and inserting the icon and filename label based on given values.

        Args:
            icon (QIcon): The icon to display left of the file name.
            icon_size (QSize): The size at which the icon should be rendered.
            filename (str): The name of the file, whih will be used as the label.
            parent (QWidget | None): The parent widget that this widget should be
            placed within. Defaults to None."""
        super(NameLabel, self).__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(8, 0, 0, 0)
        self.layout.setSpacing(5)
        self.setLayout(self.layout)
        self.icon = icon
        self.icon_label = QLabel()
        self.icon_label.setPixmap(icon.pixmap(icon_size))
        self.icon_label.setFixedSize(icon_size)
        self.layout.addWidget(self.icon_label)
        self.file_label = QLabel(filename, self)
        self.file_label.setFont(QFont(Df.CODE_FONT, 10))
        self.file_label.setStyleSheet("QLabel{color: #FFFFFF;}")
        self.layout.addWidget(self.file_label)
        self.layout.addStretch()

    def label_width(self) -> int:
        """Returns:
        int: The width of the entire NameLabel, with 3 pixels edge padding.
        """
        return self.icon_label.width() + self.file_label.width() + 8


class ObfuscateWidget(QWidget):
    """This class represents the main GUI obfuscation window, essentially representing
    the entire card-based interface contained within the GUI. This includes each source
    editor, the name labels above each source editor, and the vertical selection and
    miscallaneous option forms which are horizontally positioned to create the final UI."""

    def __init__(self, parent: QWidget | None = None):
        """The constructor for an ObfusacteWidget object, creating the card-based
        GUI interface within the given parent widget.

        Args:
            parent (QWidget | None): The parent widget that this widget should be
            placed within. Defaults to None."""
        super(ObfuscateWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Define the icons/filename elements for source editors
        self.top_widget = QWidget(self)
        self.top_layout = QHBoxLayout(self.top_widget)
        self.top_layout.setSpacing(0)
        margins = self.top_layout.contentsMargins()
        margins.setTop(3)
        margins.setBottom(0)
        self.top_layout.setContentsMargins(margins)
        self.top_layout.addStretch(0)
        self.top_widget.setLayout(self.top_layout)
        self.source_namelabel = NameLabel(
            QIcon("./app/graphics/icons/C.png"),
            QSize(14, 14),
            "/source.c",
            self.top_widget,
        )
        self.obfuscated_namelabel = NameLabel(
            QIcon("./app/graphics/icons/lock.png"),
            QSize(14, 14),
            "/obfuscated.c",
            self.top_widget,
        )
        self.top_layout.addWidget(self.source_namelabel, 3)
        self.top_layout.addWidget(self.obfuscated_namelabel, 3)
        self.top_layout.addStretch(4)
        self.layout.addWidget(self.top_widget)

        # Define the main body of the obfuscate widget
        self.main_widget = QWidget(self)
        self.main_layout = QHBoxLayout(self.main_widget)
        margins = self.main_layout.contentsMargins()
        margins.setTop(1)
        self.main_layout.setContentsMargins(margins)
        self.main_widget.setLayout(self.main_layout)
        self.layout.addWidget(self.main_widget)

        # Define a splitter that horizontally separtes both source editors
        self.source_editor = SourceEditor(self.source_namelabel.file_label, self)
        self.obfuscated_editor = SourceEditor(
            self.obfuscated_namelabel.file_label, self
        )
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.addWidget(self.source_editor)
        self.splitter.addWidget(self.obfuscated_editor)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.splitterMoved.connect(self.update_namelabels)

        # Define column widgets for transform selection and miscellaneous options
        self.selection_form = SelectionForm(self.update_namelabels, self)
        self.misc_form = MiscForm(
            self.selection_form.current_form.get_transforms,
            self.selection_form.current_form.set_transforms,
            self.selection_form.current_form.load_selected_values,
            self.source_editor,
            self.obfuscated_editor,
            self.selection_form.current_form.remove_selected,
            self.update_namelabels,
            self,
        )
        self.selection_form.current_form.add_options_form(
            self.misc_form.transform_options
        )

        # Provide 60% of the screen to the source editors, 20% to selection, and 20% to misc options
        self.main_layout.addWidget(self.splitter, 6)
        self.main_layout.addWidget(self.selection_form, 2)
        self.main_layout.addWidget(self.misc_form, 2)
        self.setLayout(self.layout)
        self.top_layout.setStretch(1, self.source_editor.width())
        self.top_layout.setStretch(2, self.obfuscated_editor.width())
        self.top_layout.setStretch(
            3, self.selection_form.width() + self.misc_form.width()
        )

    def update_namelabels(self) -> None:
        """Updates the positions of the source editor file NameLabels, based upon
        the current size and positioning information of the stored GUI widgets.
        This needs to be calculated after the UI has been resized, or when the
        splitter has moved the locations of the source editors around."""
        # Calculate the widths of each source editor, accounting for padding
        # Each label is padded by 16 to offset it slightly from the start
        # position of the source editor for a cleaner look.
        source_size = self.source_editor.width() + self.main_layout.spacing()
        obfuscated_size = self.obfuscated_editor.width()
        other_size = (
            self.selection_form.width()
            + self.misc_form.width()
            + self.main_layout.spacing() * 2
        )
        source_width = self.source_namelabel.label_width() + 16
        obfuscated_width = self.obfuscated_namelabel.label_width() + 16

        # Hide labels if the source editor is too thin to display the full name,
        # otherwise show them.
        if not self.source_namelabel.isHidden() and source_size < source_width:
            self.source_namelabel.hide()
        elif self.source_namelabel.isHidden() and source_size >= source_width:
            self.source_namelabel.show()
        if (
            not self.obfuscated_namelabel.isHidden()
            and obfuscated_size < obfuscated_width
        ):
            self.obfuscated_namelabel.hide()
        elif (
            self.obfuscated_namelabel.isHidden() and obfuscated_size >= obfuscated_width
        ):
            self.obfuscated_namelabel.show()

        # Stretch the layout to exactly position the name labels, padding appropriately
        # if the source (original) file label is hidden.
        self.top_layout.setStretch(
            0, source_size if self.source_namelabel.isHidden() else 0
        )
        self.top_layout.setStretch(1, source_size)
        self.top_layout.setStretch(2, obfuscated_size)
        self.top_layout.setStretch(3, other_size)

    def resizeEvent(self, event: QResizeEvent):
        """Handles a GUI resize event, extending the existing resizing functionality by
        calling a function for updating the position of source editor file name labels,
        such that these positions are appropriately updates after resizing of the GUI.

        Args:
            event (QResizeEvent): The GUI resize event.
        """
        super(ObfuscateWidget, self).resizeEvent(event)
        self.update_namelabels()

    def add_source(self, source: CSource) -> None:
        """Add a new original source C program to the GUI, loading its contents into
        the relevant source editor.

        Args:
            source (CSource): The original source C program to be loaded.
        """
        self.source_editor.add_source(source)


class PrimaryWindow(QMainWindow):
    """This class represents the entire main window of the GUI, setting up basic window,
    colour palette and shortcut information, and containing the main card-based obfuscation
    GUI widget."""

    def __init__(self, parent: QWidget | None = None):
        """The constructor for the MainWindow class, setting up the window with
        the program information, setting the background colour, initialising
        a fullscreen shortcut and then creating the card-based obfuscation GUI.

        Args:
            parent (QWidget | None): The parent widget that this widget should be
            placed within. Defaults to None."""
        super(PrimaryWindow, self).__init__(parent)
        # Initialise window widgets
        self.obfuscate_widget = ObfuscateWidget(self)
        self.setCentralWidget(self.obfuscate_widget)

    def add_source(self, source: CSource) -> None:
        """Add a new original source C program to the GUI, loading its contents into
        the relevant source editor.

        Args:
            source (CSource): The original source C program to be loaded.
        """
        self.obfuscate_widget.add_source(source)

    def show(self, *args, **kwargs) -> None:
        """Displays the main window of the GUI interface, extending the regular
        functionality by updating the position of name labels where necessary after
        each GUI update."""
        super(MainWindow, self).show(*args, **kwargs)
        self.obfuscate_widget.update_namelabels()


class CFGWindow(QMainWindow):
    
    def __init__(self, parent: QWidget | None = None):
        super(CFGWindow, self).__init__(parent)
        # do something


class MainWindow(QStackedWidget):
    
    def __init__(self, parent: QWidget | None = None):
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle(config.NAME + " " + config.VERSION)
        self.setWindowIcon(QIcon("./app/graphics/icons/logo.png"))
        self.setAutoFillBackground(True)
        # Set window title and icon information
        self.setWindowTitle(config.NAME + " " + config.VERSION)
        self.setWindowIcon(QIcon("./app/graphics/icons/logo.png"))
        self.setAutoFillBackground(True)
        # Set default palette colour information
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#1D1E1A"))
        self.setPalette(palette)
        # Initialise shortcut for fullscreen
        self.fullscreen_shortcut = QShortcut(QKeySequence(Df.SHORTCUT_FULLSCREEN), self)
        self.fullscreen_shortcut.activated.connect(self.toggle_fullscreen)
        self.windowed_size = self.size()
        self.window_pos = self.pos()
        # Initialise the window widgets used by the program
        self.primary_window = PrimaryWindow()
        self.addWidget(self.primary_window)
        self.cfg_window = CFGWindow()
        self.addWidget(self.cfg_window)
        self.setCurrentWidget(self.primary_window)

    def toggle_fullscreen(self) -> None:
        """Toggles the program between fullscreen and windowed mode, updating relevant
        size and position information for the window."""
        if self.isFullScreen():
            self.showNormal()
            self.resize(self.windowed_size)
            return self.move(self.window_pos)
        self.windowed_size = self.size()
        self.window_pos = self.pos()
        self.showFullScreen()


def patch_windows() -> None:
    """This patches the application icon on Windows, which currently will simply display
    the Python icon for the script. This is due to a bug in PyQt and windows bloat;
    this function detects if running on windows, and if so updates the windows application
    user model ID to make it explicitly different from python's (we name it after the program
    and version) such that the GUI recognises it separately and applies its icon instead.
    This will cause the icon displayed in the taskbar to be correct."""
    # Patch: If on windows, change the python window application user model
    # ID so that the icon is displayed correctly in the taskbar.
    if (
        hasattr(ctypes, "windll")
        and ctypes.windll is not None
        and ctypes.windll.shell32 is not None
    ):
        app_id = config.NAME + "." + config.VERSION[1:]
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)


def handle_GUI(testing: bool = False) -> bool:
    """Handles the graphical user interface for the program, parsing command arguments
    and options to determine which settings to apply and what other functionalities
    to call. Behaviour changes depending on the value of sys.argv, which depends
    on the arguments supplied to the program when calling it.

    Args:
        testing (bool). A boolean value to indicate whether the GUI is currently
        being tested or not. If it is, this function will not execute the PyQt
        application.

    Returns:
        bool: Whether execution ended as expected or not (i.e. an error occurred).
    """
    if not testing:
        patch_windows()

    supplied_args = sys.argv
    if len(supplied_args) != 0 and supplied_args[0].endswith(".py"):
        supplied_args = supplied_args[1:]

    # Setup logging information
    create_log_file()
    log(f"Began execution of GUI script.")
    log(f"Supplied arguments: {str(supplied_args)}")

    # Handle supplied arguments/options
    args = interaction.handle_arguments(supplied_args, interaction.shared_options)
    if isinstance(args, bool):
        return args

    # Create the PyQt application and the main window, and load the JetBrains Mono font
    # into the font database for use by the application.
    if not testing:
        app = QApplication(sys.argv)
    QFontDatabase.addApplicationFont(
        "./app/graphics/fonts/Jetbrains-Mono/JetBrainsMono-Regular.ttf"
    )
    window = MainWindow()
    obfuscated_editor = window.primary_window.obfuscate_widget.obfuscated_editor
    misc_form = window.primary_window.obfuscate_widget.misc_form
    selection_form = window.primary_window.obfuscate_widget.selection_form

    # Read file and display parse errors
    if len(args) >= 1:
        # One argument given, so load the source file
        source = CSource(args[0])
        if source.contents is None or not source.valid_parse:
            return False
        window.add_source(source)
    if len(args) >= 2:
        # 2 arguments given, so note the filepath that the obfuscated
        # file contents should be saved to, initialising with empty contents.
        source = CSource(args[1], "")
        obfuscated_editor.add_source(source)

    # If the appropriate option is supplied, load the given composition
    # (obfuscation scheme) file.
    if config.COMPOSITION is not None:
        contents = interaction.load_composition_file(config.COMPOSITION)
        if contents is None:
            logprint(
                "Error loading saved transformations - please provide a valid compositions file",
            )
            return False
        saved_pipeline = obfs.Pipeline.from_json(contents, use_gui=True)
        if saved_pipeline is None:
            logprint(
                "Error loading saved transformations - please provide a valid compositions file",
            )
            return False
        if config.SEED is None:  # Only use saved seed if no seed was provided
            misc_form.general_options.seed = saved_pipeline.seed
        selection_form.current_form.set_transforms(saved_pipeline.transforms)

    # Display the window and execute the application, running the GUI until quit.
    if not testing:
        window.show()
        app.exec()

    if config.SAVE_COMPOSITION:
        # Save the last obfuscation scheme (composition) if the option is set.
        selection_form.current_form.load_selected_values()
        seed = misc_form.general_options.seed
        transforms = selection_form.current_form.selected
        pipeline = obfs.Pipeline(seed, *transforms)
        interaction.save_composition_file(pipeline.to_json())

    if len(args) == 2:
        # If an output file was given, automatically write the final contents
        # of the obfuscafted source editor to that file location.
        try:
            log("Writing obfuscation output")
            with open(args[1], "w+") as write_file:
                write_file.write(obfuscated_editor.toPlainText())
            print("Obfuscation finished successfully.")
            log("Obfuscation written successfully.")
            log("Execution finished normally.")
        except Exception as e:
            print_error(f"Error creating output file '{args[1]}'")
            log(f"Error when writing output to file: {str(e)}")
            return False
    return True
