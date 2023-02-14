from typing import Iterable
from .interaction import CSource


# TODO Salvage or Scrap
"""REALISTIC_VAR_NAMES = []
with open(".\\app\\var_names.txt", "r") as f:
    for line in f.read().splitlines():
        line = line.strip()
        if not line.startswith("#") and len(line) != 0:
            REALISTIC_VAR_NAMES.append(line)"""


def is_initialised(source: CSource, libraries: Iterable[str]) -> Iterable[bool]:
    """Checks if each of the given libraries are initialised in the provided
    source file's contents such that they can be used in code safely.

    Inputs:
        - source (CSource): The source file to check within
        - libraries (Iterable[str]): The names of the libraries to check for.

    Returns an Iterable[bool] of the same size as the input libraries describing
    whether that library was initialised (included or not)."""
    # TODO could do with transformation units; hidden imports may be an issue
    libs = [l if l.startswith("<") else ("<" + l + ">") for l in libraries]
    inits = [False for _ in libraries]
    for line in source.contents.split("\n"):
        line = [t.strip() for t in line.strip().split(" ")]
        line = [t for t in line if len(t) > 0]
        if len(line) >= 2 and line[0] in ["#include", "%:include", "??=include"]:
            for i, lib in enumerate(libs):
                if line[1] == lib:
                    inits[i] = True
    return inits

