""" File: obfuscation.py
Implements classes for obfuscation transformations and the transform pipeline. """
import random
from typing import Iterable, Optional
from ctypes import Union
from .io import CSource, menu_driven_option, get_float
from abc import ABC, abstractmethod
from pycparser.c_ast import NodeVisitor, PtrDecl, ArrayDecl, InitList, Constant, \
    CompoundLiteral, Typename, TypeDecl, IdentifierType
from pycparser import c_generator, c_lexer
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

    def __init__(self, style: Style, minimiseIdents : bool):
        self.idents = {"main": "main"}
        self._new_idents = set()
        self._scopes = list()
        self.style = style
        self.minimiseIdents = minimiseIdents

    def get_new_ident(self, ident):
        if self.minimiseIdents: # TODO THIS OPTION IS VERY BROKE BUT COMPLEX SO JUST LEAVE IT FOR NOW?
            for new_ident in self._new_idents:
                in_scope = False # TODO maintain a list of unused idents - will be cleaner and cheaper
                for scope in self._scopes[::-1]:
                    if new_ident in scope:
                        in_scope = True
                        break
                if not in_scope:
                    self.idents[ident] = new_ident
                    return new_ident
        new_ident = ""
        while len(new_ident) == 0 or new_ident in self._new_idents:
            if self.style == self.Style.COMPLETE_RANDOM:
                size_ = randint(4, 19)
                new_ident = randchoice(ascii_letters)[0]
                new_ident += "".join(
                    randchoice(ascii_letters + ascii_digits + "_" * 6, k=size_)
                )
            elif self.style == self.Style.ONLY_UNDERSCORES:
                new_ident = "_" * (len(self._new_idents) + 1)
            elif self.style == self.Style.MINIMAL_LENGTH:
                cur_num = len(self._new_idents) + 1
                #choices = "_" + ascii_letters + ascii_digits
                choices = ascii_letters
                new_ident = ""
                #new_ident += choices[cur_num // len(ascii_digits)]
                while cur_num >= 0:
                    new_ident += choices[cur_num % len(choices)]
                    cur_num = cur_num // len(choices)
                    if cur_num == 0:
                        break
        self._new_idents.add(new_ident)
        self.idents[ident] = new_ident
        return new_ident

    def scramble_ident(self, node):
        if hasattr(node, "name") and node.name is not None:
            if node.name not in self.idents:
                self.get_new_ident(node.name)
            node.name = self.idents[node.name]
            self._scopes[-1].add(node.name)

    def visit_FileAST(self, node):
        self._scopes.append(set())
        NodeVisitor.generic_visit(self, node)
        self._scopes = self._scopes[:-1]
    
    def visit_FuncDef(self, node):
        self._scopes.append(set())
        NodeVisitor.generic_visit(self, node)
        self._scopes = self._scopes[:-1]
    
    def visit_Compound(self, node):
        self._scopes.append(set())
        NodeVisitor.generic_visit(self, node)
        self._scopes = self._scopes[:-1]

    def visit_Decl(self, node):
        self.scramble_ident(node)
        NodeVisitor.generic_visit(self, node)

    def visit_Union(self, node):
        self.scramble_ident(node)
        NodeVisitor.generic_visit(self, node)
    
    def visit_Enum(self, node):
        self.scramble_ident(node)
        NodeVisitor.generic_visit(self, node)
        self._in_scope.remove(node.name)
    
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
            self._scopes[-1].add(node.declname)
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


class IdentitifierRenameUnit(ObfuscationUnit):
    """Implements an identifier rename (IRN) obfuscation transformation, which takes the input
    source code and renames all identifiers (function names, parameter names, variable names, etc.)
    such that the program still performs the same functionality, but now the identifier names reveal
    no meaningful information about the program and are difficult to humanly comprehend."""

    name = "Identifier Renaming"
    description = "Renames variable/function names to make them uncomprehensible."

    def __init__(self, style, minimiseIdents):
        self.style = style
        self.minimiseIdents = minimiseIdents
        self.traverser = IdentifierTraverser(style, minimiseIdents)

    def transform(self, source: CSource) -> CSource:
        self.traverser.visit(source.t_unit)
        new_contents = generate_new_contents(source)
        return CSource(source.fpath, new_contents, source.t_unit)

    def edit_cli(self) -> bool:
        options = [s.value for s in IdentifierTraverser.Style]
        options.append("placeholder")
        options.append("Finish editing")
        while True:
            prompt = f'\nChoose a style for the identifier renaming. Your current style is "{self.style.value}".\n'
            if self.minimiseIdents:
                options[len(IdentifierTraverser.Style)] = "Disable minimal identifier usage option (currently: ENABLED)"
            else:
                options[len(IdentifierTraverser.Style)] = "Enable minimal identifer usage option (currently: Disabled)"
            choice = menu_driven_option(options, prompt)
            if choice == -1:
                return False
            elif choice == len(IdentifierTraverser.Style):
                self.minimiseIdents = not self.minimiseIdents
                self.traverser.minimiseIdents = self.minimiseIdents
            elif choice == len(options) - 1:
                return True
            else:
                self.style = IdentifierTraverser.Style(options[choice])
                self.traverser.style = self.style
        return True

    def get_cli() -> Optional["IdentitifierRenameUnit"]:
        options = [s.value for s in IdentifierTraverser.Style]
        prompt = "\nChoose a style for the identifier renaming.\n"
        minimiseIdents = False
        validChoice = False
        while not validChoice:
            if minimiseIdents:
                options.append("Disable minimal identifier usage option (currently: ENABLED)")
            else:
                options.append("Enable minimal identifer usage option (currently: DISABLED)")
            choice = menu_driven_option(options, prompt)
            if choice == -1:
                return None
            elif choice == len(IdentifierTraverser.Style):
                minimiseIdents = not minimiseIdents
                options = options[:-1]
            else:
                style = IdentifierTraverser.Style(options[choice])
                return IdentitifierRenameUnit(style, minimiseIdents)
        return None

    def __eq__(self, other: ObfuscationUnit) -> bool:
        if not isinstance(other, IdentitifierRenameUnit):
            return False
        return self.style == other.style
 
    def __str__(self):
        style_flag = f"style={self.style.name}"
        minimise_ident_flag = f"minimal={'ENABLED' if self.minimiseIdents else 'DISABLED'}"
        return f"RenameIdentifiers({style_flag},{minimise_ident_flag})"


class IdentitifierRenameUnit(ObfuscationUnit):
    """Implements an identifier rename (IRN) obfuscation transformation, which takes the input
    source code and renames all identifiers (function names, parameter names, variable names, etc.)
    such that the program still performs the same functionality, but now the identifier names reveal
    no meaningful information about the program and are difficult to humanly comprehend."""

    name = "Identifier Renaming"
    description = "Renames variable/function names to make them incomprehensible."

    def __init__(self, style, minimiseIdents):
        self.style = style
        self.minimiseIdents = minimiseIdents
        self.traverser = IdentifierTraverser(style, minimiseIdents)

    def transform(self, source: CSource) -> CSource:
        self.traverser.visit(source.t_unit)
        new_contents = generate_new_contents(source)
        return CSource(source.fpath, new_contents, source.t_unit)

    def edit_cli(self) -> bool:
        options = [s.value for s in IdentifierTraverser.Style]
        options.append("placeholder")
        options.append("Finish editing")
        while True:
            prompt = f'\nChoose a style for the identifier renaming. Your current style is "{self.style.value}".\n'
            if self.minimiseIdents:
                options[len(IdentifierTraverser.Style)] = "Disable minimal identifier usage option (currently: ENABLED)"
            else:
                options[len(IdentifierTraverser.Style)] = "Enable minimal identifer usage option (currently: Disabled)"
            choice = menu_driven_option(options, prompt)
            if choice == -1:
                return False
            elif choice == len(IdentifierTraverser.Style):
                self.minimiseIdents = not self.minimiseIdents
                self.traverser.minimiseIdents = self.minimiseIdents
            elif choice == len(options) - 1:
                return True
            else:
                self.style = IdentifierTraverser.Style(options[choice])
                self.traverser.style = self.style

    def get_cli() -> Optional["IdentitifierRenameUnit"]:
        options = [s.value for s in IdentifierTraverser.Style]
        prompt = "\nChoose a style for the identifier renaming.\n"
        minimiseIdents = False
        validChoice = False
        while not validChoice:
            if minimiseIdents:
                options.append("Disable minimal identifier usage option (currently: ENABLED)")
            else:
                options.append("Enable minimal identifer usage option (currently: DISABLED)")
            choice = menu_driven_option(options, prompt)
            if choice == -1:
                return None
            elif choice == len(IdentifierTraverser.Style):
                minimiseIdents = not minimiseIdents
                options = options[:-1]
            else:
                style = IdentifierTraverser.Style(options[choice])
                return IdentitifierRenameUnit(style, minimiseIdents)
        return None

    def __eq__(self, other: ObfuscationUnit) -> bool:
        if not isinstance(other, IdentitifierRenameUnit):
            return False
        return self.style == other.style
 
    def __str__(self):
        style_flag = f"style={self.style.name}"
        minimise_ident_flag = f"minimal={'ENABLED' if self.minimiseIdents else 'DISABLED'}"
        return f"RenameIdentifiers({style_flag},{minimise_ident_flag})"

class StringEncodeTraverser(NodeVisitor):
    """Traverses the program AST looking for string literals and encoding them into
    some incomprehensible form."""
    
    escape_chars = {
        'a': '\'\\x07\'',
        'b': '\'\\x08\'',
        'e': '\'\\x1B\'',
        'f': '\'\\x0C\'',
        'n': '\'\\x0A\'',
        'r': '\'\\x0D\'',
        't': '\'\\x09\'',
        'v': '\'\\x0B\'',
        '\\': '\'\\x5C\'',
        '\'': '\'\\x27\'',
        '\"': '\'\\x22\'',
        '?': '\'\\x3F\'',
    }
    
    TO_REMOVE = True
    
    class Style(Enum):
        SIMPLE = "Simple Octal Character Encoding"
        OTHER = "OTHER Encoding (Not Yet Implemented)"
    
    def __init__(self, style):
        self.style = style
    
    def encode_string(self, node):
        chars = []
        max_index = len(node.value) - 1
        check_next = False
        for i, char in enumerate(node.value[1:-1]):
            if check_next:
                check_next = False
                if char in self.escape_chars:
                    char_node = Constant("char", self.escape_chars[char])
                    chars.append(char_node)
                    continue
                else:
                    return None
            if char == '\\' and i != max_index:
                check_next = True
                continue
            octal = '\'\\' + str(oct(ord(char)))[2:] + '\''
            char_node = Constant("char", octal)
            chars.append(char_node)
        chars.append(Constant("char", '\'\\0\''))
        return chars
    
    def make_compound_literal(self, init_node):
        identifier_node = IdentifierType(['char'])
        type_decl_node = TypeDecl(None, [], None, identifier_node)
        array_type_node = ArrayDecl(type_decl_node, None, None)
        typename_node = Typename(None, [], None, array_type_node)
        return CompoundLiteral(typename_node, init_node)
    
    def visit_Decl(self, node):
        if node.init is not None:
            if isinstance(node.init, Constant) and node.init.type == "string":
                chars = self.encode_string(node.init)
                if chars is not None:
                    node.init = InitList(chars, None)
                    if isinstance(node.type, PtrDecl):
                        node.type = ArrayDecl(node.type.type, None, None)
        NodeVisitor.generic_visit(self, node)
    
    def visit_ExprList(self, node):
        for i, expr in enumerate(node.exprs):
            if isinstance(expr, Constant) and expr.type == "string":
                chars = self.encode_string(expr)
                if chars is not None:
                    init_node = InitList(chars, None)
                    node.exprs[i] = self.make_compound_literal(init_node)
        NodeVisitor.generic_visit(self, node)

    def visit_InitList(self, node):
        for i, expr in enumerate(node.exprs):
            if isinstance(expr, Constant) and expr.type == "string":
                chars = self.encode_string(expr)
                if chars is not None:
                    node.exprs[i] = InitList(chars, None)
        NodeVisitor.generic_visit(self, node)
    
    def visit_ArrayRef(self, node):
        if node.name is not None:
            if isinstance(node.name, Constant) and node.name.type == "string":
                chars = self.encode_string(node.name)
                if chars is not None:
                    init_node = InitList(chars, None)
                    node.name = self.make_compound_literal(init_node)
        NodeVisitor.generic_visit(self, node)
        
    def visit_NamedInitializer(self, node):
        if node.expr is not None:
            if isinstance(node.expr, Constant) and node.expr.type == "string":
                chars = self.encode_string(node.expr)
                if chars is not None:
                    node.expr = InitList(chars, None)
        NodeVisitor.generic_visit(self, node)
    
    def visit_TernaryOp(self, node):
        if node.iftrue is not None:
            if isinstance(node.iftrue, Constant) and node.iftrue.type == "string":
                chars = self.encode_string(node.iftrue)
                if chars is not None:
                    init_node = InitList(chars, None)
                    node.iftrue = self.make_compound_literal(init_node)
        if node.iffalse is not None:
            if isinstance(node.iffalse, Constant) and node.iffalse.type == "string":
                chars = self.encode_string(node.iffalse)
                if chars is not None:
                    init_node = InitList(chars, None)
                    node.iffalse = self.make_compound_literal(init_node)
        NodeVisitor.generic_visit(self, node)
    
    def visit_BinaryOp(self, node):
        if node.left is not None:
            if isinstance(node.left, Constant) and node.left.type == "string":
                chars = self.encode_string(node.left)
                if chars is not None:
                    init_node = InitList(chars, None)
                    node.left = self.make_compound_literal(init_node)
        if node.right is not None:
            if isinstance(node.right, Constant) and node.right.type == "string":
                chars = self.encode_string(node.right)
                if chars is not None:
                    init_node = InitList(chars, None)
                    node.right = self.make_compound_literal(init_node)
        NodeVisitor.generic_visit(self, node)
    
    def visit_UnaryOp(self, node):
        if node.expr is not None:
            if isinstance(node.expr, Constant) and node.expr.type == "string":
                chars = self.encode_string(node.expr)
                if chars is not None:
                    init_node = InitList(chars, None)
                    node.expr = self.make_compound_literal(init_node)
        NodeVisitor.generic_visit(self, node)
    
    def visit_If(self, node):
        if node.cond is not None:
            if isinstance(node.cond, Constant) and node.cond.type == "string":
                chars = self.encode_string(node.cond)
                if chars is not None:
                    init_node = InitList(chars, None)
                    node.cond = self.make_compound_literal(init_node)
        NodeVisitor.generic_visit(self, node)
    
    def visit_While(self, node):
        if node.cond is not None:
            if isinstance(node.cond, Constant) and node.cond.type == "string":
                chars = self.encode_string(node.cond)
                if chars is not None:
                    init_node = InitList(chars, None)
                    node.cond = self.make_compound_literal(init_node)
        NodeVisitor.generic_visit(self, node)
    
    def visit_DoWhile(self, node):
        if node.cond is not None:
            if isinstance(node.cond, Constant) and node.cond.type == "string":
                chars = self.encode_string(node.cond)
                if chars is not None:
                    init_node = InitList(chars, None)
                    node.cond = self.make_compound_literal(init_node)
        NodeVisitor.generic_visit(self, node)


class StringEncodeUnit(ObfuscationUnit):
    """ Implements a string literal encoding (SLE) obfuscation transformation, which takes the
    input source code and encodes string literals in the code according to some encoding method
    such that the program still performs the same functionality, but strings can no longer be
    easily read in the code. """
    
    name = "String Literal Encoding"
    description = "Encodes string literals to make them incomprehensible"
    
    def __init__(self, style):
        self.style = style
        self.traverser = StringEncodeTraverser(style)
    
    def transform(self, source: CSource) -> CSource:
        self.traverser.visit(source.t_unit)
        new_contents = generate_new_contents(source)
        return CSource(source.fpath, new_contents, source.t_unit)
    
    def edit_cli(self) -> bool:
        options = [s.value for s in StringEncodeTraverser.Style]
        prompt = f"\nThe current encoding style is {self.style.value}.\n"
        prompt += "Choose a new style for string encoding.\n"
        choice = menu_driven_option(options, prompt)
        if choice == -1:
            return False
        self.style = self.Style(options[choice])
        self.traverser.style = self.style
        return True
    
    def get_cli() -> Optional["StringEncodeUnit"]:
        options = [s.value for s in StringEncodeTraverser.Style]
        prompt = "\nChoose a style for the string encoding.\n"
        choice = menu_driven_option(options, prompt)
        if choice == -1:
            return None
        style = StringEncodeTraverser.Style(options[choice])
        return StringEncodeUnit(style)
    
    def __eq__(self, other: ObfuscationUnit) -> bool:
        if not isinstance(other, StringEncodeUnit):
            return False
        return self.style == other.style
    
    def __str__(self):
        style_flag = f"style={self.style.name}"
        return f"StringEncode({style_flag})"

class IntegerEncodeTraverser(NodeVisitor):

    class Style(Enum):
        SIMPLE = "Simple Arithmetic Encoding (Not Yet Implemented)"
        SPLIT = "Split Integer Literals (Not Yet Implemented)"
        OPAQUE_EXPRESSION = "Opaque Expression (Not Yet Implemented)"
        MBA = "Mixed-Boolean Arithmetic (Not Yet Implemented)"
    
    pass

#class LiteralEncodeUnit(ObfuscationUnit):
#    pass # TODO

class ClutterWhitespaceUnit(ObfuscationUnit): # TODO picture extension?
    """ Implements simple source-level whitespace cluttering, breaking down the high-level abstraction of 
    indentation and program structure by altering whitespace in the file. """
    
    # TODO WARNING ORDERING - SHOULD COME LAST (BUT BEFORE DiTriGraphEncodeUnit)
    name = "Clutter Whitespace"
    description = "Clutters program whitespace, making it difficult to read"
    
    def __init__(self):
        pass
    
    def transform(self, source: CSource) -> CSource:
        # Preprocess contents
        new_contents = ""
        for line in source.contents.splitlines():
            if line.strip().startswith("#"):
                new_contents += line + "\n"
        generator = c_generator.CGenerator()
        contents = generator.visit(source.t_unit)
        # Initialise lexer
        discard_f = lambda: None
        lexer = c_lexer.CLexer(discard_f, discard_f, discard_f, lambda tok: None)
        lexer.build()
        lexer.input(contents)
        # Lex tokens and format according to whitespace rules
        cur_line_length = 0
        max_line_length = 100
        token = lexer.token()
        while token is not None:
            cur_line_length += len(token.value) + 1
            if cur_line_length <= max_line_length:
                new_contents += ' ' + token.value
                cur_line_length += 1
            else:
                cur_line_length = len(token.value)
                new_contents += "\n" + token.value
            token = lexer.token()
        return CSource(source.fpath, new_contents)
    
    def edit_cli(self) -> bool:
        return True
    
    def get_cli() -> Optional["ClutterWhitespaceUnit"]:
        return ClutterWhitespaceUnit()
    
    def __eq__(self, other: ObfuscationUnit) -> bool:
        return isinstance(other, ClutterWhitespaceUnit)

    def __str__(self):
        return "ClutterWhitespace()"

class DiTriGraphEncodeUnit(ObfuscationUnit):
    """ Implements a string literal encoding (SLE) obfuscation transformation, which takes the
    input source code and encodes string literals in the code according to some encoding method
    such that the program still performs the same functionality, but strings can no longer be
    easily read in the code. """
    
    # TODO WARNING ORDERING - SHOULD COME LAST?
    name = "Digraph/Trigraph Encoding"
    description = "Encodes certain symbols with Digraphs/Trigraphs to make them incomprehensible"
    
    digraph_map = {
        '[': "<:",
        ']': ":>",
        '{': "<%",
        '}': "%>",
        '#': "%:",
    }
    
    trigraph_map = {
        '#': "??=",
        '\\': "??/",
        '^': "??\'",
        '[': "??(",
        ']': "??)",
        '|': "??!",
        '{': "??<",
        '}': "??>",
        '~': "??-",
    }
    
    class Style(Enum):
        DIGRAPH = "Digraph Encoding"
        TRIGRAPH = "Trigraph Encoding"
        MIXED = "Mixed Digraph/Trigraph Encoding"
    
    def __init__(self, style: Style, chance: float):
        self.style = style
        if chance < 0.0:
            self.chance = 0.0
        elif chance > 1.0:
            self.chance = 1.0
        else:
            self.chance = chance  
    
    def transform(self, source: CSource) -> CSource:
        new_contents = ""
        prev = None
        str_top = None
        for char in source.contents:
            if (char == '\'' or char == '\"') and prev != '\\':
                if str_top is None:
                    str_top = char
                elif str_top == char:
                    str_top = None
            if str_top is not None or random.random() > self.chance:
                new_contents += char
                prev = char
                continue
            if self.style == self.Style.MIXED and char in self.digraph_map or char in self.trigraph_map:
                if random.randint(1,2) == 1 and char in self.digraph_map:
                    new_contents += self.digraph_map[char]
                else:
                    new_contents += self.trigraph_map[char]
            elif self.style == self.Style.DIGRAPH and char in self.digraph_map:
                new_contents += self.digraph_map[char]
            elif self.style == self.Style.TRIGRAPH and char in self.trigraph_map:
                new_contents += self.trigraph_map[char]
            else:
                new_contents += char
            prev = char
        return CSource(source.fpath, new_contents)
    
    def edit_cli(self) -> bool:
        options = [s.value for s in self.Style]
        prompt = f"\nThe current encoding style is {self.style.value}.\n"
        prompt += "Choose a new style for the digraph/trigraph encoding.\n"
        choice = menu_driven_option(options, prompt)
        if choice == -1:
            return False
        style = self.Style(options[choice])
        print(f"The current probability of encoding is {self.chance}.")
        print("What is the new probability (0.0 <= p <= 1.0) of the encoding?")
        prob = get_float(0.0, 1.0)
        if prob == float('nan'):
            return False
        self.style = style
        self.chance = prob
        return True
    
    def get_cli() -> Optional["DiTriGraphEncodeUnit"]:
        options = [s.value for s in DiTriGraphEncodeUnit.Style]
        prompt = "\nChoose a style for the digraph/trigraph encoding.\n"
        choice = menu_driven_option(options, prompt)
        if choice == -1:
            return None
        style = DiTriGraphEncodeUnit.Style(options[choice])
        print("What is the probability (0.0 <= p <= 1.0) of the encoding?")
        prob = get_float(0.0, 1.0)
        if prob == float('nan'):
            return None
        return DiTriGraphEncodeUnit(style, prob)
    
    def __eq__(self, other: ObfuscationUnit) -> bool:
        if not isinstance(other, DiTriGraphEncodeUnit):
            return False
        return self.style == other.style and self.chance == other.chance
    
    def __str__(self):
        style_flag = f"style={self.style.name}"
        probability_flag = f"p={self.chance}"
        return f"DiTriGraphEncode({style_flag},{probability_flag})"


class CFFlattenTraverser(NodeVisitor):
    
    def __init__(self):
        self.levels = []
        self.breaks = []
        self.continues = []
    
    def flatten_function(self, node):
        # We first must break the function into the basic blocks that define it
        # TODO remove below - just logic
        # We get a potential branch on:
        #  > 
        blocks = []
        
        pass
    
    def visit_FuncDef(self, node):
        self.flatten_function(node)
        NodeVisitor.generic_visit(self, node) # TODO do I do this?


class ControlFlowFlattenUnit(ObfuscationUnit):
    """ TODO """
    
    name = "Flatten Control Flow"
    description = "Flatten all Control Flow in functions into a single level to help prevent code analysis"
    
    def __init__(self):
        self.traverser = CFFlattenTraverser()
        pass # TODO
    
    def transform(self, source: CSource) -> CSource:
        self.traverser.visit(source.t_unit)
        return source # TODO
    
    def edit_cli(self) -> bool:
        return True # TODO
    
    def get_cli() -> Optional["ControlFlowFlattenUnit"]:
        return ControlFlowFlattenUnit() # TODO
    
    def __eq__(self, other: ObfuscationUnit) -> bool:
        return isinstance(other, ControlFlowFlattenUnit) # TODO

    def __str__(self) -> str:
        return "FlattenControlFlow()"