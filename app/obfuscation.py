""" File: obfuscation.py
Implements classes for obfuscation transformations and the transform pipeline. """
import random
from typing import Iterable, Optional
from ctypes import Union
from .io import CSource, menu_driven_option
from abc import ABC, abstractmethod
from pycparser.c_ast import NodeVisitor
from pycparser import c_generator
from random import choices as randchoice, randint
from string import ascii_letters, digits as ascii_digits
from enum import Enum


def generate_new_contents(source: CSource) -> str:
    new_contents = ""
    for line in source.contents.splitlines():
        if line.strip().startswith("#"):
            new_contents += line + "\n"
    generator = c_generator.CGenerator()
    new_contents += generator.visit(source.t_unit)
    return new_contents


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
    def edit_cli() -> Optional["ObfuscationUnit"]:
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
            Defaults to None, which indicates the end of the pipeline.
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

    def edit_cli(self) -> bool:
        """Implements a command-line interface for editing an identity transformation.

        Returns:
            bool: True if editing successful, false if the user chose to quit.
        """
        return True

    def get_cli() -> Optional["IdentityUnit"]:
        """Creates an identity transformation and performs the CLI interaction to allow
        the user to edit the new transform.

        Returns:
            Optional[IdentityUnit]: the transform created from user CLI interaction.
            Returns None if the user chose to quit within the CLI.
        """
        new_transform = IdentityUnit()
        return new_transform

    def __eq__(self, other: ObfuscationUnit) -> bool:
        return isinstance(other, IdentityUnit)

    def __str__(self):
        return "Identity()"

class IdentifierTraverser(NodeVisitor):
    """Traverses the program AST looking for non-external identifiers (except main),
    transforming them to some random scrambled identifier."""
    
    class Style(Enum):
        COMPLETE_RANDOM  = "Complete Randomness"
        ONLY_UNDERSCORES = "Only underscores" # TODO will this break anything?
        MINIMAL_LENGTH   = "Minimal length"

    def __init__(self, style: Style):
        self.idents = {"main": "main"}
        self.new_idents = set()
        self.style = style
        self.pragmas = []
        self._in_scope = {}

    def get_new_ident(self, ident):
        new_ident = ""
        while len(new_ident) == 0 or new_ident in self.new_idents:
            if self.style == self.Style.COMPLETE_RANDOM:
                size_ = randint(4, 19)
                new_ident = randchoice(ascii_letters)[0]
                new_ident += "".join(
                    randchoice(ascii_letters + ascii_digits + "_" * 6, k=size_)
                )
            elif self.style == self.Style.ONLY_UNDERSCORES:
                new_ident = "_" * (len(self.new_idents) + 1)
            elif self.style == self.Style.MINIMAL_LENGTH:
                cur_num = len(self.new_idents) + 1
                #choices = "_" + ascii_letters + ascii_digits
                choices = ascii_letters
                new_ident = ""
                #new_ident += choices[cur_num // len(ascii_digits)]
                while cur_num >= 0:
                    new_ident += choices[cur_num % len(choices)]
                    cur_num = cur_num // len(choices)
                    if cur_num == 0:
                        break
        self.new_idents.add(new_ident)
        self.idents[ident] = new_ident
        return new_ident

    def scramble_ident(self, node):
        if hasattr(node, "name") and node.name is not None:
            if node.name not in self.idents:
                self.get_new_ident(node.name)
            node.name = self.idents[node.name]

    def visit_Decl(self, node):
        self.scramble_ident(node)
        NodeVisitor.generic_visit(self, node)

    def visit_Union(self, node):
        self.scramble_ident(node)
        NodeVisitor.generic_visit(self, node)
    
    def visit_Enum(self, node):
        self.scramble_ident(node)
        NodeVisitor.generic_visit(self, node)
    
    def visit_Enumerator(self, node):
        self.scramble_ident(node)
        NodeVisitor.generic_visit(self, node)
    
    def visit_Label(self, node):
        self.scramble_ident(node)
        NodeVisitor.generic_visit(self, node)
    
    def visit_Goto(self, node):
        self.scramble_ident(node)
        NodeVisitor.generic_visit(self, node)

    def visit_TypeDecl(self, node):
        if node.declname is not None:
            if node.declname not in self.idents:
                self.get_new_ident(node.declname)
            node.declname = self.idents[node.declname]
        NodeVisitor.generic_visit(self, node)

    def visit_ID(self, node):
        if node.name in self.idents:
            node.name = self.idents[node.name]
        NodeVisitor.generic_visit(self, node)

    def visit_FuncCall(self, node):
        if node.name in self.idents:
            node.name = self.idents[node.name]
        NodeVisitor.generic_visit(self, node)
    
    def visit_IdentifierType(self, node):
        for i, name in enumerate(node.names):
            if name in self.idents:
                node.names[i] = self.idents[name]
        NodeVisitor.generic_visit(self, node)
        
    def visit_Pragma(self, node): # TODO maybe warn on pragma?
        # TODO something's not working with pragmas because of how pycparser handles them!
        import debug
        debug.print_error("Error: cannot currently handle pragmas!")
        debug.log("Could not continue obfuscation because the obfuscator cannot handle pragmas!")
        exit()
    
    def visit_StaticAssert(self, node): # TODO what's breaking here?
        import debug
        debug.print_error("Error: cannot currently handle static assertions!")
        debug.log("Could not continue obfuscation because the obfuscator cannot handle static asserts!")
        exit()

    # TODO: ArrayRef, Enum, Enumerator, FuncCall, Goto, Label, NamedInitializer, Struct, StructRef


class IdentitifierRenameUnit(ObfuscationUnit):
    """Implements an identifier rename (IRN) obfuscation transformation, which takes the input
    source code and renames all identifiers (function names, parameter names, variable names, etc.)
    such that the program still performs the same functionality, but now the identifier names reveal
    no meaningful information about the program and are difficult to humanly comprehend."""

    name = "Identifier Renaming"
    description = "Renames variable/function names to make them uncomprehensible."

    def __init__(self, style):
        self.style = style
        self.traverser = IdentifierTraverser(style)

    def transform(self, source: CSource) -> CSource:
        self.traverser.visit(source.t_unit)
        new_contents = generate_new_contents(source)
        return CSource(source.fpath, new_contents, source.t_unit)

    def edit_cli(self) -> bool:
        options = [s.value for s in IdentifierTraverser.Style]
        prompt = f'\nChoose a style for the identifier renaming. Your current style is "{options[self.style-1]}".\n'
        choice = menu_driven_option(options, prompt)
        if choice == -1:
            return False
        self.style = IdentifierTraverser.Style(options[choice])
        self.traverser.style = self.style
        return True

    def get_cli() -> Optional["IdentitifierRenameUnit"]:
        options = [s.value for s in IdentifierTraverser.Style]
        prompt = "\nChoose a style for the identifier renaming.\n"
        choice = menu_driven_option(options, prompt)
        if choice == -1:
            return None
        style = IdentifierTraverser.Style(options[choice])
        return IdentitifierRenameUnit(style)

    def __eq__(self, other: ObfuscationUnit) -> bool:
        if not isinstance(other, IdentitifierRenameUnit):
            return False
        return self.style == other.style
 
    def __str__(self):
        style_flag = f"style={self.style.name}"
        return f"RenameIdentifiers({style_flag})"
