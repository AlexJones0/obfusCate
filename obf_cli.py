""" File: obf_cli.py
A simple script to run the command-line interface for ObfusCate.
"""

if __name__ == "__main__":
    import sys
    from app import cli
    sys.exit(cli.handle_CLI())