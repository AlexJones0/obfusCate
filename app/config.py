""" File: config.py
Implements classes to store system configs/settings, as well as 
GUI styling and key-binding defaults.
"""


class Config(object):
    """Stores settings used by the program during its execution."""

    NAME = "obfusCate"
    VERSION = "v0.17.4"
    LOG_PATH = "./logs/"
    COMP_PATH = "./compositions/auto/"
    TEMP_FILE_PATH = "./obfuscate_temp.c"
    LOG_FILE = ""
    LOGS_ENABLED = True
    CALCULATE_COMPLEXITY = True
    DISPLAY_ERRORS = False
    SUPPRESS_ERRORS = False
    DISPLAY_PROGRESS = False
    SKIP_MENUS = False
    SAVE_COMPOSITION = False
    COMPOSITION = None
    SEED = None
    USE_ALLOCA = True
    USE_PATCHED_PARSER = True

class GuiDefaults(object):
    """ Stores important default values used by GUI code throughout the program,
    including lists of font families to use for rendering different text (in what
    order), shortcut keypress sequences, and standardized CSS to give the
    program a cohesive style. """
    
    DEFAULT_FONT = ["Consolas", "Fira Code", "Jetbrains Mono", "Courier New", "monospace"]
    CODE_FONT = ["Jetbrains Mono", "Fira Code", "Consolas", "Courier New", "monospace"]
    SHORTCUT_DESELECT = "Esc"
    SHORTCUT_SELECT_NEXT = "Ctrl+Space"
    SHORTCUT_SELECT_PREV = "Ctrl+B"
    SHORTCUT_OBFUSCATE = "Ctrl+R"
    SHORTCUT_DELETE = "Ctrl+D"
    SHORTCUT_SAVE_OBFS = "Ctrl+S"
    SHORTCUT_SAVE_COMP = "Shift+S"
    SHORTCUT_FULLSCREEN = "F11"
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
            width: 10px;
            margin: 1.5px 3px 0px 0px;
        }
        QScrollBar::sub-page:vertical{
            background: transparent;
        }
        QScrollBar::add-page:vertical{
            background: transparent;
        }
        QScrollBar::handle:vertical{
            background: white;
            border-radius: 3px;
            border-style: solid;
        }
        QScrollBar::add-line:vertical{
            background: transparent;
        }
        QScrollBar::sub-line:vertical{
            background: transparent;
        }
        QScrollBar:horizontal{
            border: none;
            background: transparent;
            height: 10px;
            margin: 0px 0px 3px 2.5px;
        }
        QScrollBar::sub-page:horizontal{
            background: transparent;
        }
        QScrollBar::add-page:horizontal{
            background: transparent;
        }
        QScrollBar::handle:horizontal{
            background: white;
            border-radius: 3px;
            border-style: solid;
        }
        QScrollBar::add-line:horizontal{
            background: transparent;
        }
        QScrollBar::sub-line:horizontal{
            background: transparent;
        }
    """