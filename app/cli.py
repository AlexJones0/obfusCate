import sys
from .debug import print_error, create_log_file, log
from .io import CSource
from app import settings as cfg


def run_cli() -> bool:
    create_log_file()
    log(f"Began execution of CLI script.")
    supplied_args = sys.argv
    if len(supplied_args) != 0 and supplied_args[0].endswith(".py"):
        supplied_args = supplied_args[1:]
    log(f"Supplied arguments: {str(supplied_args)}")
    if len(supplied_args) == 0:
        print_error(
            "No source file was supplied. Use the -h or --help options for more information.")
        return log("Aborting executions because no arguments were supplied.")
    options, args = [], []
    for arg in supplied_args:
        target = args if arg.startswith("-") else options
        target.append(arg)
    if len(options) == 1:
        source = CSource(options[0])