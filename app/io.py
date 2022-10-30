""" File: io.py
Implements classes and functions for handling input and output. """
from typing import Iterable, Optional, Tuple, Union
from .debug import print_error, log
from clang.cindex import TranslationUnit, TranslationUnitLoadError
import clang.cindex

# Create the clang Index for parsing C source files.
index = clang.cindex.Index.create()


class CSource:
    """A class representing a C source code program, storing its contents in both
    string form and as a Clang-parsed translation unit."""

    def __init__(
        self,
        filepath: str,
        contents: Optional[str] = None,
        t_unit: Optional[TranslationUnit] = None,
    ):
        """A constructor for a CSource object.

        Args:
            filepath (str): The path to the C file.
            contents (Optional[str], optional): The contents of the file. Defaults to
            None, in which case the file path is opened and read to retrieve contents.
            t_unit (Optional[TranslationUnit], optional): The translation unit of the file
            after it is parsed by clang. Defaults to None, in which case it is retrieved
            by parsing the file.
        """
        self.fpath = filepath
        if contents is None:
            log(f"Started loading source file with path {filepath}")
            self.contents = self.__read_file()
        else:
            self.contents = contents
        if self.contents is None:
            return
        if t_unit is None:
            self.t_unit = self.parse()
        else:
            self.t_unit = t_unit

    def __read_file(self) -> Optional[str]:
        """Reads the file contents from the stored file path, raising errors and logging
        as appropriate.

        Returns:
            Optional[str]: The string contents of the file, or None if some error occurs.
        """
        if not self.fpath.endswith(".c"):
            print_error(f"Supplied file {self.fpath} is not a .c file!")
            return None
        log("Started reading contents from source file.")
        try:
            with open(self.fpath, "r") as source_file:
                contents = source_file.read()
            return contents
        except OSError as e:
            log(f"Error in opening source file: {str(e)}.")
        return None

    def parse(self) -> Optional[TranslationUnit]:
        """Parses the file using the clang parser to produce a translation unit, raising
        errors and logging as appropriate.

        Returns:
            Optional[TranslationUnit]: The clang translation unit of the parsed file, or
            None if some error occurs.
        """
        log("Attempting to parse program.")
        try:
            t_unit = index.parse(self.fpath)
            return t_unit
        except TranslationUnitLoadError as e:
            log(f"Error parsing the program: {str(e)}")
            print_error(
                f"An error occurred whilst trying to parse {self.fpath} - check that this compiles without any errors or warnings and try again."
            )
            return None
        except Exception as e:
            log(f"Unexpected error whilst parsing the program: {str(e)}.")
            print_error(
                f"An unknown error occurred whilst trying to parse {self.fpath}."
            )
            return None

    def copy(self) -> 'CSource':
        """Creates a copy of the code record, producing a separate translation unit.

        Returns:
            CSource: A copy of the file with the same path, contents and parsed contents.
        """
        log(f"Creating copy of source: {self.fpath}.")
        return CSource(self.fpath, self.contents)
    
    @property
    def valid_parse(self) -> bool:
        """ This boolean property describes whether a valid parse has been performed on
        the C source file or not."""
        if self.t_unit is None:
            return False
        return len(self.t_unit.diagnostics) == 0

    def get_parse_errors(self) -> Iterable[str]:
        """ Retrieves a list of string error/warning messages generated during the parse of
        the C source file by clang.

        Returns:
            Iterable[str]: A list of strings, where each string is an individual parse error.
        """
        if self.t_unit is None:
            return []
        return [str(d) for d in self.t_unit.diagnostics]


def menu_driven_option(
    options: Iterable[Union[str, Tuple[str, Iterable[str]]]], prompt: str = None
) -> int:
    """Performs command-line interface input handling for a generalized menu-driven
    system in which a restricted integer input must be made to select one of many
    options. Returns the chosen option.

    Args:
        options (Iterable[Union[str, Tuple[str, Iterable[str]]]]): The list of
        options to provide. Each option can either be a string, or a tuple like
        (string, [str1, str2, str3, ...]) where string is the option text and
        [str1, str2, str3, ...] are optional strings that the CLI should understand
        as a selction of that choice.
        prompt (str, optional): Additional prompt text to display to the user after
        the printing of options but before requesting input. Defaults to None.

    Returns:
        int: The integer index of the selected choice. -1 if it was selected to quit.
    """
    # Display options and prompt
    for i, option in enumerate(options):
        print(f" ({i+1}) {option}")
    print(prompt + "\n >", end="")

    # Loop until valid input received
    valid_input = False
    while not valid_input:
        try:
            choice = input().lower().strip()
            # Check for quit inputs
            if choice in ["q", "quit", "exit", "leave", "x"]:
                return -1
            # Check for keyword matches
            for i, option in enumerate(options):
                if isinstance(option, tuple) and choice in option[1]:
                    choice = i
                    break
            # Check for valid integer choice ranges
            if not isinstance(choice, int):
                choice = int(choice)
            if choice > 0 and choice <= len(options):
                valid_input = True
            else:
                print(
                    "Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.\n >",
                    end="",
                )
        except: # Handle non-integer (and non-keyword) inputs
            print(
                "Invalid option choice. Please select a number corresponding to your choice, or type 'quit' to exit.\n >",
                end="",
            )
    return choice - 1
