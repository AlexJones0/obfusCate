""" File: gui.py
Implements functions to implement the graphical user interface of the program,
such that it can be more accessibly used without text interaction in a terminal
window. """
from . import interaction, obfuscation as obfs
from .obfuscation import gui as obfs_gui
from .complexity import *
from .debug import print_error, create_log_file, log, logprint
from .config import GuiDefaults as Df
from app import settings as cfg
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import Qt, QSize, QMimeData, QDir, QCoreApplication
from typing import Type, Tuple, Callable, Any
from copy import deepcopy
import functools, sys, os, ctypes


def help_menu() -> bool:
    """Prints the help menu detailing usage of the GUI command interface.

    Returns:
        bool: Always returns False, to signal that execution should stop."""
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


interaction.set_help_menu(help_menu)


def display_error(error_msg: str) -> None:
    QMessageBox.critical(None, "Error", error_msg)


def get_transform_colour(transform_type: obfs.TransformType) -> str:
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


class CHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text: str) -> None:
        return super().highlightBlock(text)


# TODO can I make the editors _not_ reset scroll unless necessary
# when text is changed?
class SourceEditor(QPlainTextEdit):
    def __init__(self, file_label: QLabel, parent: QWidget = None) -> None:
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
        highlighter = CHighlighter(self.document())
        # TODO proper syntax highlighting
        # TODO line numbers

    def add_source(self, source: CSource) -> None:
        self.source = source
        self.setPlainText(source.contents)
        self.modified_from_read = False
        if self.file_label is not None:
            fname = source.fpath.split("\\")[-1].split("/")[-1]
            self.file_label.setText("/" + fname)
    
    def get_fname(self) -> str:
        return self.source.fpath.split("\\")[-1].split("/")[-1]

    def set_modified(self):
        self.modified_from_read = True

    def setPlainText(self, text: str):
        # TODO double check everything works here but I think it's good?
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
    def __init__(
        self,
        class_: Type[obfs.ObfuscationUnit],
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
        self.label.setFont(QFont(Df.DEFAULT_FONT, 11))
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
        self.info_symbol.setPixmap(
            QIcon(".\\app\\graphics\\info.png").pixmap(QSize(21, 21))
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
        self.title_label.setFont(QFont(Df.DEFAULT_FONT, 14))
        self.title_label.setStyleSheet("QLabel{color: white;}")
        self.layout.addWidget(
            self.title_label, 1, alignment=Qt.AlignmentFlag.AlignHCenter
        )  # TODO Or AlignTop?
        self.transforms = []
        subsubclasses = [c.__subclasses__() for c in obfs.ObfuscationUnit.__subclasses__()]
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
        class_: Type[obfs.ObfuscationUnit],
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
            drag.setPixmap(self.box_widget.grab())
            self.box_widget.hide()
            drag.setHotSpot(event.pos() - self.box_widget.pos())
            drag.exec(Qt.DropAction.MoveAction)

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
        self.title_label.setFont(QFont(Df.DEFAULT_FONT, 14))
        self.title_label.setStyleSheet("QLabel{color: white;}")
        self.layout.addWidget(
            self.title_label, 1, alignment=Qt.AlignmentFlag.AlignHCenter
        )
        self.options = QFrame(self)
        self.options.setMinimumHeight(200)
        self.layout.addWidget(self.options, 9)
        # TODO seems to be an issue - if you click on the label text the button doesn't work
        # but if you click on any other part of the back it does? Need to troubleshoot this
        # TODO above *may* (or may not) have something to do with having source editor text highlighted?
        # TODO also maybe it is getting _covered_ by some other widget which is taking the click?
        # TODO ^^ seems to be relatively consistent on removing ControlFlow?
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

    def load_transform(self, transform: obfs.ObfuscationUnit) -> None:
        if transform is None:
            self.remove_button.hide()
            self.layout.removeWidget(self.options)
            self.options = QFrame()
            self.options.setMinimumHeight(200)
            self.layout.insertWidget(1, self.options)
            # TODO figure out how to handle resetting default behaviour
            return
        self.remove_button.show()
        self.layout.removeWidget(self.options)
        self.options = QFrame()
        self.options.setMinimumHeight(200)
        transform.edit_gui(self.options)
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
        self.deselect_shortcut = QShortcut(QKeySequence(Df.SHORTCUT_DESELECT), self)
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

    def move_transform(self, new_index: int, source: SelectedTransformWidget) -> None:
        source.box_widget.show()
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

    def add_transform(self, class_: Type[obfs.ObfuscationUnit]) -> None:
        number = len(self.selected) + 1
        transform_widget = SelectedTransformWidget(
            class_, number, self.select_transform, self
        )
        transform_widget.height()
        self.scroll_content.layout.addWidget(
            transform_widget, alignment=Qt.AlignmentFlag.AlignTop
        )
        self.selected.append(class_.get_gui())
        self.selected_widgets.append(transform_widget)

    def set_transforms(self, transforms: Iterable[obfs.ObfuscationUnit]) -> None:
        self.deselect_transform()
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
        if self.current_transform is not None:
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
        self.setMinimumSize(250, 250)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.title_label = QLabel("Obfuscation Metrics", self)
        self.title_label.setFont(QFont(Df.DEFAULT_FONT, 14))
        self.title_label.setStyleSheet("QLabel{color: white;}")
        self.layout.addWidget(
            self.title_label, 1, alignment=Qt.AlignmentFlag.AlignHCenter
        )
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
        self.metric_widget.layout.setContentsMargins(5, 5, 8, 5)
        self.metric_widget.layout.setSpacing(12)
        # self.metric_widget.setSizePolicy(
        #    QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum
        # ) # TODO keep or remove this?
        self.scroll_widget.setWidget(self.metric_widget)
        self.layout.addWidget(self.scroll_widget, 9)
        self.setLayout(self.layout)
        if cfg.CALCULATE_COMPLEXITY:
            self.load_metrics(None, None)

    def toggle_checkbox(self, metric):
        # Retrieve relevant checbox information
        if metric not in self.checkbox_map:
            return
        checkbox = self.checkbox_map[metric]
        if checkbox is None:
            return
        # Change the metric name label formatting depending on the checkbox status
        name_label = checkbox.parent().layout().itemAt(0).widget()
        if checkbox.isChecked():  # TODO unmodularised code with the stuff below
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

    def load_metrics(self, source: CSource, obfuscated: CSource) -> None:
        if not hasattr(self, "checkbox_map"):
            self.checkbox_map = {}
        else:
            for key in self.checkbox_map.keys():
                self.checkbox_map[key] = self.checkbox_map[key].isChecked()
        QToolTip.setFont(QFont(Df.DEFAULT_FONT, 13))
        for i in reversed(range(self.metric_widget.layout.count())):
            widget = self.metric_widget.layout.itemAt(i).widget()
            self.metric_widget.layout.removeWidget(widget)
            widget.setParent(None)
        metrics = CodeMetricUnit.__subclasses__()
        while len(metrics) != 0:
            processed = []
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
                    continue
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
                            value_label = QLabel(
                                m_val[0] + " ({})".format(",".join(m_val[1:]))
                            )
                        else:
                            value_label = QLabel(m_val)
                        value_label.setFont(QFont(Df.DEFAULT_FONT, 9, 200))
                        value_label.setStyleSheet("QLabel{color: #878787;}")
                        if name in metric_unit.tooltips:
                            metric_widget.setToolTip(metric_unit.tooltips[name])
                        metric_layout.addWidget(metric_label)
                        metric_layout.addStretch()
                        metric_layout.addWidget(value_label)
                        metric_widget.setLayout(metric_layout)
                        unit_layout.addWidget(metric_widget)
                else:
                    na_label = QLabel("N/A")
                    na_label.setFont(QFont(Df.DEFAULT_FONT, 10))
                    na_label.setStyleSheet("QLabel{color: white;}")
                    unit_layout.addWidget(na_label)
            if len(processed) == 0:
                log(
                    "Metrics {} have unsatisfiable predecessor dependencies!".format(
                        metrics
                    )
                )
                return
            for metric in processed:
                metrics.remove(metric)


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
        self.obfuscate_shortcut = QShortcut(QKeySequence(Df.SHORTCUT_OBFUSCATE), self)
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
        self.title_label.setFont(QFont(Df.DEFAULT_FONT, 14, 1000))
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
        button.setFont(QFont(Df.DEFAULT_FONT, 12))
        self.layout.addWidget(button, 1)
        return button

    def obfuscate(self) -> None:
        self.__load_selected_gui_reference()
        pipeline = obfs.Pipeline(self.seed, *self.__transforms_reference())
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
            if cfg.CALCULATE_COMPLEXITY:
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
                    self.__source_form_reference.get_fname(),
                    source.error_context
                )
            display_error(error_msg)
            return
        if cfg.CALCULATE_COMPLEXITY:
            original_source = deepcopy(source)
        if len(pipeline.transforms) != 0:
            # TODO add complexity metric calculations to progress bar? Seems hard
            self.parent().progress_bar.setRange(0, len(pipeline.transforms))
            self.parent().update_progress(0)
        obfuscated = pipeline.process(source, self.parent().update_progress)
        self.parent().update_progress(-1)
        self.__obfuscated_form_reference.add_source(obfuscated)
        if cfg.CALCULATE_COMPLEXITY:
            self.parent().metrics_form.load_metrics(original_source, obfuscated)

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
                transform_pipeline = obfs.Pipeline.from_json(f.read(), use_gui=True)
                if transform_pipeline is None:
                    return
                if config.SEED is None:  # Only use the saved seed if no seed was given
                    self.seed = transform_pipeline.seed
                self.__set_transforms_func(transform_pipeline.transforms)
        except:
            return

    def save_obfuscated(self) -> None:
        file, _ = QFileDialog.getSaveFileName(
            self, "Save Obfuscated C", "", "C Source Files (*.c);;All Files (*)"
        )
        if not file or len(file) == 0:
            return
        with open(file, "w+") as f:
            f.write(self.__obfuscated_form_reference.toPlainText())

    def save_composition(self) -> None:
        compositions_path = os.path.join(os.getcwd(), "compositions\\")
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


class SelectionForm(QWidget):  # TODO move selection and misc just into obfuscatewidget?
    def __init__(self, resize_func: Callable, parent: QWidget = None) -> None:
        super(SelectionForm, self).__init__(parent)
        self.resize_func = resize_func
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.available_form = AvailableForm(self.add_transform, self)
        self.layout.addWidget(self.available_form, 1)
        self.current_form = CurrentForm(self)
        self.layout.addWidget(self.current_form, 1)
        self.setLayout(self.layout)

    def resizeEvent(self, event) -> None:
        super(SelectionForm, self).resizeEvent(event)
        self.resize_func()

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
        resize_func: Callable,
        parent: QWidget = None,
    ) -> None:
        super(MiscForm, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.resize_func = resize_func
        self.transform_options = TransformOptionsForm(remove_func, self)
        self.layout.addWidget(
            self.transform_options, alignment=Qt.AlignmentFlag.AlignTop
        )  # TODO temp alignment
        self.metrics_form = MetricsForm(self)
        self.layout.addWidget(self.metrics_form)
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
        )  # TODO temp alignment
        self.setLayout(self.layout)

    def update_progress(self, i: int):
        self.progress_bar.setValue(max(i, 0))
        if i == -1 or i == self.progress_bar.maximum():
            self.progress_bar.setFormat("Not currently obfuscating...")
            self.progress_palette.setColor(QPalette.ColorRole.Text, QColor("#727463"))
            self.progress_bar.setPalette(self.progress_palette)
        else:
            self.progress_bar.setFormat(self.base_format)
            self.progress_palette.setColor(
                QPalette.ColorRole.Text, QColorConstants.White
            )
            self.progress_bar.setPalette(self.progress_palette)

    def resizeEvent(self, event) -> None:
        super(MiscForm, self).resizeEvent(event)
        self.resize_func()


class NameLabel(QWidget):
    def __init__(
        self, icon: QIcon, icon_size: QSize, filename: str, parent: QWidget = None
    ) -> None:
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

    def label_width(self):
        return self.icon_label.width() + self.file_label.width() + 8


class ObfuscateWidget(QWidget):
    def __init__(self, parent: QWidget = None) -> None:
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
        # TODO every since I added namelabel code am getting print msg!? Why?
        self.top_layout.setContentsMargins(margins)
        self.top_layout.addStretch(0)
        self.top_widget.setLayout(self.top_layout)
        self.source_namelabel = NameLabel(
            QIcon(".\\app\\graphics\\C.png"),
            QSize(14, 14),
            "/source.c",
            self.top_widget,
        )
        self.obfuscated_namelabel = NameLabel(
            QIcon(".\\app\\graphics\\lock.png"),
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
        # Define a splitter and both source editors
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
        # Define column widgets for transform selection and miscallaneous options
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
        source_size = self.source_editor.width() + self.main_layout.spacing()
        obfuscated_size = self.obfuscated_editor.width()
        other_size = (
            self.selection_form.width()
            + self.misc_form.width()
            + self.main_layout.spacing() * 2
        )
        source_width = self.source_namelabel.label_width() + 16
        if not self.source_namelabel.isHidden() and source_size < source_width:
            self.source_namelabel.hide()
        elif self.source_namelabel.isHidden() and source_size >= source_width:
            self.source_namelabel.show()
        obfuscated_width = self.obfuscated_namelabel.label_width() + 16
        if (
            not self.obfuscated_namelabel.isHidden()
            and obfuscated_size < obfuscated_width
        ):
            self.obfuscated_namelabel.hide()
        elif (
            self.obfuscated_namelabel.isHidden() and obfuscated_size >= obfuscated_width
        ):
            self.obfuscated_namelabel.show()
        self.top_layout.setStretch(
            0, source_size if self.source_namelabel.isHidden() else 0
        )
        self.top_layout.setStretch(1, source_size)
        self.top_layout.setStretch(2, obfuscated_size)
        self.top_layout.setStretch(3, other_size)

    def resizeEvent(self, event: QResizeEvent) -> None:
        val = super(ObfuscateWidget, self).resizeEvent(event)
        self.update_namelabels()
        return val

    def add_source(self, source: CSource) -> None:
        self.source_editor.add_source(source)


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget = None) -> None:
        super(MainWindow, self).__init__(parent)
        # Set window title and icon information
        self.setWindowTitle(config.NAME + " " + config.VERSION)
        self.setWindowIcon(QIcon(".\\app\\graphics\\logo.png"))
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

    def show(self, *args, **kwargs) -> None:
        super(MainWindow, self).show(*args, **kwargs)
        self.obfuscate_widget.update_namelabels()


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
    args = interaction.handle_arguments(supplied_args, interaction.shared_options)
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
    if len(args) >= 2:
        source = CSource(args[1], "")  # TODO check this works
        window.obfuscate_widget.obfuscated_editor.add_source(source)
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
            window.obfuscate_widget.misc_form.general_options.seed = saved_pipeline.seed
        window.obfuscate_widget.selection_form.current_form.set_transforms(
            saved_pipeline.transforms
        )

    window.show()
    app.exec()

    if config.SAVE_COMPOSITION:
        window.obfuscate_widget.selection_form.current_form.load_selected_values()
        seed = window.obfuscate_widget.misc_form.general_options.seed
        transforms = window.obfuscate_widget.selection_form.current_form.selected
        pipeline = obfs.Pipeline(seed, *transforms)
        interaction.save_composition_file(pipeline.to_json())

    if len(args) == 2:
        try:
            log("Writing obfuscation output")
            with open(args[1], "w+") as write_file:
                write_file.write(
                    window.obfuscate_widget.obfuscated_editor.toPlainText()
                )
            print("Obfuscation finished successfully.")
            log("Obfuscation written successfully.")
            log("Execution finished normally.")
        except Exception as e:
            print_error(f"Error creating output file '{args[1]}'")
            log(f"Error when writing output to file: {str(e)}")
            return False
    return True
