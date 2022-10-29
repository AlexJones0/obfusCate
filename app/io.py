from typing import TextIO
from .debug import print_error, log
import clang.cindex

index = clang.cindex.Index.create()

class CSource():

    def __init__(self, filepath: str):
        log(f"Started loading source file with path {filepath}")
        self.fpath = filepath
        self.contents = self.__read_file()

    def __read_file(self) -> str:
        if not self.fpath.endswith(".c"):
            print_error(f"Supplied file {self.fpath} is not a .c file!")
            return
        log("Started reading contents from source file.")
        try:
            with open(self.fpath, 'r') as source_file:
                contents = source_file.read()
            return contents
        except OSError as e:
            log("Error in opening source file: {str(e)}.")
        return None

    def parse_ast(self):
        pass