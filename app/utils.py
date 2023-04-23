""" File: utils.py
Defines utility functions for use in all parts of the system.
Currently continas a utility to check if a list of libraries are
initialised within a given source file. 
"""
from .interaction import CSource
from typing import Iterable


def is_initialised(source: CSource, libraries: Iterable[str]) -> Iterable[bool]:
    """Checks if each of the given libraries are initialised in the provided
    source file's contents such that they can be used in code safely.

    Args:
        source (CSource): The source file to check within
        libraries (Iterable[str]): The names of the libraries to check for.

    Returns:
        Iterable[bool]: a bool list of the same size as the input libraries,
        describing whether that library was initialised (included or not).
    """
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
