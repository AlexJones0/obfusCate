""" File: obf_gui.py
A simple script to run the graphical interface for ObfusCate.
"""

if __name__ == "__main__":
    import sys
    from app import gui
    sys.exit(gui.handle_GUI())