""" File: gui.py
Implements functions to implement the graphical user interface of the program,
such that it can be more accessibly used without text interaction in a terminal
window. """
from .obfuscation import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import Qt
from typing import Type
import sys

DEFAULT_FONT = ["JetBrains Mono", "Fira Code", "Consolas", "Courier New", "monospace"]

class CHighlighter(QSyntaxHighlighter):
    def highlightBlock(self, text: str) -> None:
        return super().highlightBlock(text)


class SourceEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setFont(QFont(DEFAULT_FONT, 10))
        self.setStyleSheet(
            "border-style: outset; border-width: 3px; border-radius: 10px; border-color: #848484; background-color: #1D1E1A"
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


class TransformWidget(QWidget):
    def __init__(self, class_: Type[ObfuscationUnit], parent: QWidget = None) -> None:
        super(TransformWidget, self).__init__(parent)
        self.layout = QHBoxLayout(self)
        self.class_ = class_
        self.label = QLabel(class_.name, self)
        self.label.setObjectName("transformNameLabel")
        self.label.setFont(
            QFont(
                ["JetBrains Mono", "Fira Code", "Consolas", "Courier New", "monospace"],
                12,
            )
        )
        self.label.setStyleSheet(
            "QLabel#transformNameLabel { color: "
            + TransformWidget.get_colour(class_.type)
            + "; }"
        )
        self.layout.addWidget(self.label, 7, alignment=Qt.AlignmentFlag.AlignLeft)
        self.buttons_widget = QWidget(self)
        self.buttons_widget.layout = QHBoxLayout(self.buttons_widget)
        self.info_symbol = QLabel("🛈", self)
        self.info_symbol.setFont(QFont(DEFAULT_FONT, 25, 250))
        QToolTip.setFont(QFont(DEFAULT_FONT, 13))
        self.info_symbol.setStyleSheet(
            """ QLabel {color: white}
                QToolTip { 
                    background-color: #AAAAAA; 
                    color: black; 
                    border: black solid 2px
                } """
        )
        self.info_symbol.setToolTip(class_.extended_description)
        self.buttons_widget.layout.addWidget(self.info_symbol, 1)
        self.buttons_widget.layout.addSpacing(20)
        self.add_symbol = QLabel("+", self)
        self.add_symbol.setFont(QFont(DEFAULT_FONT, 28, 800))
        self.add_symbol.setStyleSheet("QLabel{color: white;}")
        self.buttons_widget.layout.addWidget(self.add_symbol, 1)
        self.layout.addWidget(
            self.buttons_widget, alignment=Qt.AlignmentFlag.AlignRight
        )
        self.setLayout(self.layout)

    def get_colour(transform_type):
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


class AvailableForm(QWidget):
    def __init__(self, parent: QWidget = None) -> None:
        super(AvailableForm, self).__init__(parent)
        self.setStyleSheet(
            """QWidget#AvailableForm {
                              background-color: #272822; 
                              border-style: outset;
                              border-width: 2px;
                              border-radius: 10px;
                              border-color: white;
                              padding: 6px; }"""
        )
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(0)
        self.title_label = QLabel("Available Obfuscations", self)
        self.title_label.setFont(QFont(DEFAULT_FONT, 14))
        self.title_label.setStyleSheet("QLabel{color: white;}")
        self.layout.addWidget(self.title_label, alignment=Qt.AlignmentFlag.AlignHCenter) # Or AlignTop?
        self.transforms = []
        ts = sorted(ObfuscationUnit.__subclasses__(), key=lambda c: c.type.value)
        for class_ in ts:
            transform_widget = TransformWidget(class_, self)
            self.layout.addWidget(transform_widget, 1)
            self.transforms.append(transform_widget)
        self.setLayout(self.layout)


class CurrentForm(QWidget):
    pass


class TransformOptionsForm(QWidget):
    pass


class MetricsForm(QWidget):
    pass


class GeneralOptionsForm(QWidget):
    pass


class SelectionForm(QWidget):  # TODO move selection and misc just into obfuscatewidget?
    def __init__(self, parent: QWidget = None) -> None:
        super(SelectionForm, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.available_form = AvailableForm(self)
        self.layout.addWidget(self.available_form)
        self.setLayout(self.layout)


class MiscForm(QWidget):
    def __init__(self, parent: QWidget = None) -> None:
        super(MiscForm, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)


class ObfuscateWidget(QWidget):
    def __init__(self, parent: QWidget = None) -> None:
        super(ObfuscateWidget, self).__init__(parent)
        self.layout = QHBoxLayout(self)
        self.source_editor = SourceEditor()
        self.obfuscated_editor = SourceEditor()
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.addWidget(self.source_editor)
        self.splitter.addWidget(self.obfuscated_editor)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.selection_form = SelectionForm()
        self.misc_form = MiscForm()
        self.layout.addWidget(self.splitter, 6)
        self.layout.addWidget(self.selection_form, 2)
        self.layout.addWidget(self.misc_form, 2)
        self.setLayout(self.layout)


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget = None) -> None:
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle("obfusCate")
        self.setWindowIcon(QIcon(".\\graphics\\logo.png"))
        self.setWindowIconText("obfusCate")
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#1D1E1A"))
        self.setPalette(palette)
        self.obfuscate_widget = ObfuscateWidget(self)
        self.setCentralWidget(self.obfuscate_widget)


def handle_gui():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()
