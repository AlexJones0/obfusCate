""" File: obfuscation.py
Implements classes for obfuscation transformations and the transform pipeline. """

import random
from typing import Iterable, Optional
from ctypes import Union
from .io import CSource
from abc import ABC, abstractmethod


class ObfuscationUnit(ABC):
    """An abstract base class representing some obfuscation transformation unit, such that
    any implemented transformations will be subclasses of this class. Implements methods
    for transformations, constructing the class (in a CLI), and string representation."""

    name = "ObfuscationUnit"
    description = (
        "An abstract base class representing some obfuscation transformation unit"
    )

    @abstractmethod
    def transform(self, source: CSource) -> Optional[CSource]:
        return NotImplemented

    @abstractmethod
    def get_cli() -> Optional["ObfuscationUnit"]:
        return NotImplemented

    @abstractmethod
    def __eq__(self, other: "ObfuscationUnit") -> bool:
        return True

    @abstractmethod
    def __str__(self):
        return "ObfuscationUnit()"


class Pipeline:
    """Represents the pipeline of transformations that will be applied to some C source code
    to produce an obfuscated program. Provides functionalities for altering this pipeline
    and processing source code."""

    def __init__(self, seed: int = None, *args):
        """Constructs a Pipeline object with the supplied random seed and transformations.

        Args:
            seed (int, optional): The seed to use for randomness in obfuscation. Defaults to None.
            *args: A variable number of obfuscation transformation units to use in the pipeline.
        """
        if seed is not None:
            random.seed(seed)
        self.transforms = list(args)

    def add(self, transform: ObfuscationUnit, index: int = None) -> None:
        """Add a new obfuscation transform to the pipeline at the specified position.

        Args:
            transform (ObfuscationUnit): The transform to be added to the pipeline.
            index (int, optional): The position the transform will be inserted into the list.
            Defaults to None.
        """
        if index is None:
            return self.transforms.append(transform)
        self.transforms = (
            self.transforms[:index] + [transform] + self.transforms[index:]
        )

    def process(self, source: CSource) -> Optional[CSource]:
        """Processes some C source code, applying all the pipeline's transformations in sequence
        to produce some output obfuscated C code.

        Args:
            source (CSource): The C source code to be obfuscated through the pipeline.

        Returns:
            Optional[CSource]: The resulting obfuscated C source code. Returns None on some error.
        """
        if source is None:
            return None
        for t in self.transforms:
            source = t.transform(source)
            if source is None:
                break
        return source


class IdentityUnit(ObfuscationUnit):
    """Implements an identity transformation, which takes the input source code and does
    nothing to it, returning it unmodified."""

    name = "Identity"
    description = "Does nothing - returns the same code entered."

    def transform(self, source: CSource) -> CSource:
        """Performs the identity transformation on the source.

        Args:
            source (CSource): The source code to transform.

        Returns:
            CSource: The transformed source code.
        """
        return source

    def get_cli() -> "IdentityUnit":
        """Implements a command-line interface for creating an identity transformation.

        Returns:
            IdentityUnit: The transform created from user CLI interaction.
        """
        return IdentityUnit()

    def __eq__(self, other: ObfuscationUnit) -> bool:
        return isinstance(other, IdentityUnit)

    def __str__(self):
        return "Identity()"
