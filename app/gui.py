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
    load_composition,
)
from app import settings as config
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import Qt, QSize, QMimeData
from typing import Type
from copy import deepcopy
import sys

DEFAULT_FONT = ["Consolas", "Fira Code", "Jetbrains Mono", "Courier New", "monospace"]
CODE_FONT = ["Jetbrains Mono", "Fira Code", "Consolas", "Courier New", "monospace"]
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
        None,  # Function to call if argument supplied # TODO
        ["-h", "--help"],  # Arguments that can be provided for this function
        "Displays this help menu.",  # A help menu description for this argument
        [],  # Names of proceeding values used by the function
    ),
    (
        disable_logging,  # TODO
        ["-l", "--noLogs"],
        "Stops a log file being created for this execution.",
        [],
    ),
    (
        set_seed,  # TODO
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
        QToolTip.setFont(QFont(DEFAULT_FONT, 13))
        self.info_symbol.setStyleSheet(
            """ 
            QToolTip { 
                background-color: #AAAAAA; 
                color: black; 
                border: black solid 2px
            }"""
        )
        self.info_symbol.setToolTip(class_.extended_description)
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
        ts = sorted(ObfuscationUnit.__subclasses__(), key=lambda c: c.type.value)
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
        self.options = QFrame(self)  # TODO this is where we use the class
        self.layout.addWidget(self.options, 9)
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
            self.options = QFrame(self)
            # TODO figure out how to handle resetting default behaviour
            return
        self.remove_button.show()
        return  # TODO comment out when done implmenting menus
        self.options = transform.edit_gui()


class CurrentForm(QFrame):
    class RemoveBehaviour(Enum):
        SELECT_NEXT = 1
        DESELECT = 2

    def __init__(self, parent: QWidget = None) -> None:
        super(CurrentForm, self).__init__(parent)
        # TODO why is this not working?
        self.remove_behaviour = self.RemoveBehaviour.SELECT_NEXT
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
            self.current_widget.deselect()
        self.current_transform = self.selected[self.selected_widgets.index(widget)]
        self.current_widget = widget
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
        transforms: Iterable[ObfuscationUnit],
        source_form: SourceEditor,
        obfuscated_form: SourceEditor,
        parent: QWidget = None,
    ) -> None:
        super(GeneralOptionsForm, self).__init__(parent)
        self.__transforms_reference = transforms
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
        self.save_obfuscated_button = self.get_button("Save obfuscated file")
        self.load_transformations_button = self.get_button("Load transformations")
        self.save_transformations_button = self.get_button("Save transformations")
        self.quit_button = self.get_button("Quit")
        self.quit_button.clicked.connect(self.quit)
        self.setLayout(self.layout)

    def get_button(self, msg):
        button = QPushButton(msg, self)
        button.setFont(QFont(DEFAULT_FONT, 12))
        self.layout.addWidget(button, 1)
        return button

    def obfuscate(self):
        pipeline = Pipeline(config.SEED, *self.__transforms_reference)
        if config.SAVE_COMPOSITION:
            save_composition(pipeline.to_json())
        source = deepcopy(self.__source_form_reference.source)
        source.contents = self.__source_form_reference.toPlainText()
        obfuscated = pipeline.process(source)
        self.__obfuscated_form_reference.add_source(obfuscated)

    def quit(self):
        sys.exit(0)


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
        transforms: Iterable[ObfuscationUnit],
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
            transforms, source_form, obfuscated_form, self
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
            self.selection_form.current_form.selected,
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
        self.source_editor.add_source(source)


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget = None) -> None:
        super(MainWindow, self).__init__(parent)
        # Set window title and icon information
        self.setWindowTitle(config.NAME + " " + config.VERSION)
        self.setWindowIcon(QIcon(".\\app\\graphics\\logo.ico"))
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


def handle_gui() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()

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

    # Read file and display parse errors
    if len(args) == 1:
        source = CSource(args[0])
        if source.contents is None or not source.valid_parse:
            return False
        window.add_source(source)

    window.show()
    app.exec()
