import sys
from typing import Optional
from .debug import print_error, create_log_file, log
from .io import CSource
from .obfuscation import *
from app import settings as cfg


def help_menu() -> None:  # TODO change from 'python cli' to actual name
    print("""################ CLI Help Manual ################
This program takes as an argument some input C source program file and allows the application of a sequence of obfuscation transformations, resulting in an obfuscated C source file being produced. For more information on usage and options, see below.

Usage: python cli input_c_file [output_file] [options]

Options:
    -h --help       | Displays this help menu.
    -l --noLogs     | Stops a log file being created for this execution.
    -s --seed x     | Initialises the program with the random seed x (some integer).
""")


def get_transformations(source: CSource, seed: Optional[int] = None) -> Optional[CSource]:
    new_source = source.copy()
    transforms = []
    available_transforms = ObfuscationUnit.__subclasses__()
    finished_choosing = False
    while not finished_choosing:
        # TODO maybe just keep a list somewhere instead?
        print("\n")
        for i, class_ in enumerate(available_transforms):
            print(f" ({i+1}) {class_.name}: {class_.description}")
        print(f" ({i+2}) Undo previous transform selection")
        print(f" ({i+3}) Finish selecting transforms and continue\n")
        print("Current transforms: {}\n\n >".format(", ".join(str(t) for t in transforms)), end="")
        valid_input = False
        while not valid_input:
            try:
                choice = input()
                match choice:
                    case 'q' | 'quit' | 'exit' | 'leave' | 'x':
                        return None
                    case 'back' | 'undo' | 'u':
                        choice = len(available_transforms) + 1
                    case 'done' | 'finish' | 'next' | 'continue':
                        choice = len(available_transforms) + 2
                    case _:
                        choice = int(choice)
                if choice > 0 and choice <= len(available_transforms):
                    valid_input = True
                elif choice == len(available_transforms) + 1:
                    transforms = transforms[:-1]
                    valid_input = True
                    print(" >", end="")
                elif choice == len(available_transforms) + 2:
                    valid_input = True
                    finished_choosing = True
                else:
                    print(
                        "Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.\n >", end="")
            except:
                print("Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.\n >", end="")
        if not finished_choosing and choice != len(available_transforms) + 1:
            new_transform = available_transforms[choice-1].get_cli()
            if new_transform is None:
                return None
            transforms.append(new_transform)
    pipeline = Pipeline(seed, *transforms)
    obfuscated = pipeline.process(source)
    return obfuscated


def run_cli() -> bool:
    supplied_args = sys.argv
    if len(supplied_args) != 0 and supplied_args[0].endswith(".py"):
        supplied_args = supplied_args[1:]
    if len(supplied_args) == 0:
        print_error(
            "No source file was supplied. Use the -h or --help options for more information.")
        return log("Aborting executions because no arguments were supplied.")
    args = []
    seed = None
    skipNext = False
    for i, arg in enumerate(supplied_args):
        if skipNext:
            skipNext = False
            continue
        match arg:
            case '-h' | '--help' | '--man' | '--manual':
                help_menu()
                return True
            case '-l' | '--noLogs':
                cfg.LOGS_ENABLED = False
            case '-s' | '--seed':
                skipNext = True
                if len(supplied_args) < (i+1):
                    print_error(
                        "Some integer seed must be supplied with the -s and --seed options. Use the -h or --help options to see usage information.")
                    return False
                try:
                    seed = int(supplied_args[i+1])
                except:
                    print_error(
                        "Some integer seed must be supplied with the -s and --seed options. Use the -h or --help options to see usage information.")
                    return False
            case _:
                if arg.startswith("-"):
                    print_error(
                        f"Unknown option '{arg}' supplied. Use the -h or --help options to see usage information.")
                    return False
                else:
                    args.append(arg)
    create_log_file()
    log(f"Began execution of CLI script.")
    log(f"Supplied arguments: {str(supplied_args)}")
    if len(args) == 1:
        source = CSource(args[0])
        obfuscated = get_transformations(source, seed)
        if obfuscated is not None:
            print(obfuscated.contents)
        return True
    elif len(args) == 2:
        source = CSource(args[0])
        obfuscated = get_transformations(source, seed)
        try:
            with open(args[1], "w+") as write_file:
                write_file.write(obfuscated.contents)
            print("Obfuscation finished successfully.")
            return True
        except:
            print_error(f"Error creating output file '{args[1]}'")
    return False
