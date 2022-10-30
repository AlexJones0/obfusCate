from typing import Optional, TextIO
from .debug import print_error, log
from clang.cindex import TranslationUnit, TranslationUnitLoadError
import clang.cindex


index = clang.cindex.Index.create()


class CSource():

    def __init__(self, filepath: str, contents: Optional[str] = None, t_unit: Optional[TranslationUnit] = None):
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

    def __read_file(self) -> str:
        if not self.fpath.endswith(".c"):
            print_error(f"Supplied file {self.fpath} is not a .c file!")
            return None
        log("Started reading contents from source file.")
        try:
            with open(self.fpath, 'r') as source_file:
                contents = source_file.read()
            return contents
        except OSError as e:
            log(f"Error in opening source file: {str(e)}.")
        return None

    def parse(self) -> Optional[TranslationUnit]:
        log("Attempting to parse program.")
        try:
            t_unit = index.parse(self.fpath)
            return t_unit
        except TranslationUnitLoadError as e:
            log(f"Error parsing the program: {str(e)}")
            print_error(
                f"An error occurred whilst trying to parse {self.fpath} - check that this compiles without any errors or warnings and try again.")
            return None
        except Exception as e:
            log(f"Unexpected error whilst parsing the program: {str(e)}.")
            print_error(
                f"An unknown error occurred whilst trying to parse {self.fpath}.")
            return None

    def copy(self):
        log(f"Creating copy of source: {self.fpath}.")
        return CSource(self.fpath, self.contents)
