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

class CHighlighter(QSyntaxHighlighter):
    
    def highlightBlock(self, text: str) -> None:
        return super().highlightBlock(text)


class SourceEditor(QTextEdit):
    
    def __init__(self):
        super().__init__()
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.setStyleSheet("background-color: #272822;")
        self.setTextColor(QColor(255, 255, 255, 255))
        highlighter = CHighlighter(self.document())


class TransformWidget(QWidget):
    
    def __init__(self, class_: Type[ObfuscationUnit], parent: QWidget = None) -> None:
        super(TransformWidget, self).__init__(parent)
        self.layout = QHBoxLayout(self)
        self.setLayout(self.layout)


class AvailableForm(QWidget):
    
    def __init__(self, parent: QWidget = None) -> None:
        super(AvailableForm, self).__init__(parent)
        self.setStyleSheet("""background-color: #272822; 
                              border-style: outset;
                              border-width: 2px;
                              border-radius: 10px;
                              border-color: white;
                              padding: 6px;""")
        self.layout = QVBoxLayout(self)
        self.title_label = QLabel("Available Obfuscations", self)
        self.title_label.setFont(QFont(["JetBrains Mono", "Fira Code", "Consolas", "Courier New", "monospace"], 14))
        self.title_label.setStyleSheet("color: white;")
        self.layout.addWidget(self.title_label, alignment = Qt.AlignmentFlag.AlignTop)
        self.transforms = []
        for class_ in ObfuscationUnit.__subclasses__():
            transform_widget = TransformWidget(class_, self)
            self.layout.addWidget(transform_widget)
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
        

class SelectionForm(QWidget): # TODO move selection and misc just into obfuscatewidget?
    
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
        self.selection_form = SelectionForm()
        self.misc_form = MiscForm()
        self.layout.addWidget(self.source_editor)
        self.layout.addWidget(self.obfuscated_editor)
        self.layout.addWidget(self.selection_form)
        self.layout.addWidget(self.misc_form)
        self.setLayout(self.layout)

class MainWindow(QMainWindow):
    
    def __init__(self, parent: QWidget = None) -> None:
        super(MainWindow, self).__init__(parent)
        self.setWindowTitle("obfusCate")
        self.setWindowIcon(QIcon(".\\graphics\\logo.png"))
        self.setWindowIconText("obfusCate")
        self.setStyleSheet("background-color: #1D1E1A;")
        self.obfuscate_widget = ObfuscateWidget(self)
        self.setCentralWidget(self.obfuscate_widget)

def handle_gui():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec()