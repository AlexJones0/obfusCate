""" File: obfuscation.py
Implements classes for obfuscation transformations and the transform pipeline. """
from .interaction import CSource, menu_driven_option, get_float, get_int
from .utils import VariableUseAnalyzer, NewVariableUseAnalyzer, TypeKinds  # TODO remove if not used
from .debug import *
from typing import Iterable, Optional
from ctypes import Union
from abc import ABC, abstractmethod
from pycparser.c_ast import *
from pycparser import c_generator, c_lexer
from enum import Enum
from math import sqrt, floor
from string import ascii_letters, digits as ascii_digits
import random
import json

# TODO need to consider transformation ordering?
# TODO add print statements to report pipeline progress, as it could take a while for large programs?
# TODO also, add log statements throughout!
# TODO also, add an option to disable logging!
# TODO make a NodeVisitor subclass that overrides the traditional names to allow for consistent function naming


def generate_new_contents(source: CSource) -> str:
    """Generates textual obfuscated file contents from a source's abstract syntax tree (AST),
    facilitating AST manipulation for source-to-source transformation.

    Args:
        source (CSource): The source object to generate contents for.

    Returns:
        (str) The generated file contents from the source's AST"""
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
    def to_json(self) -> str:
        return json.dumps({"transformation": "ObfuscationUnit"})

    @abstractmethod
    def from_json() -> Optional["ObfuscationUnit"]:
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
        self.seed = seed
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
        # TODO remove - this is temporary
        analyzer = NewVariableUseAnalyzer(source.t_unit)
        analyzer.process()
        #defined_before = analyzer.get_definitions_at_stmt(source.t_unit.ext[-2].body.block_items[0].iffalse.iffalse.block_items[1])
        #used_from = analyzer.get_usage_from_stmt(source.t_unit.ext[-2].body.block_items[0].iffalse.iffalse.block_items[2])
        #needed_defs = defined_before.intersection(used_from)
        #print("Defined before this statement: \n  {}".format("  ".join([" ".join([str(x[1].name), x[0]]) for x in defined_before])))
        #print("Used in and after this statement: \n  {}".format("  ".join([" ".join([str(x[1].name), x[0]]) for x in used_from])))
        #print("Identifiers that must stay defined: \n  {}".format("  ".join([" ".join([str(x[1].name), x[0]]) for x in needed_defs])))
        #print(source.t_unit)
        return source

    def to_json(self) -> str:
        """Converts the pipeline of composed transformations to a serialised JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps(
            {
                "seed": self.seed,
                "transformations": [t.to_json() for t in self.transforms],
            }
        )

    def from_json(json: str) -> Optional["Pipeline"]:
        """Converts the provided serialized JSON string to a transformation pipeline.

        Args:
            json (str): The JSON string to attempt to load.

        Returns:
            The corresponding Pipeline object if the given json is valid, or None otherwise."""
        # TODO loading the string
        if "seed" not in json:
            log("Failed to load composition file - no seed supplied.", print_err=True)
            return
        try:
            seed = int(json["seed"])
        except:
            log(
                "Failed to load composition file - invalid seed supplied.",
                print_err=True,
            )
            return
        if "transformations" not in json or not isinstance(
            json["transformations"], list
        ):
            log(
                "Failed to load composition file - a list of transformations must be given.",
                print_err=True,
            )
            return
        transformations = []
        for t in json["transformations"]:
            if "type" not in t:
                log(
                    "Failed to load composition file - supplied transformation has no type.",
                    print_err=True,
                )
                return
            elif t["type"] not in [str(t) for t in ObfuscationUnit.__subclasses__]:
                log(
                    "Failed to load composition file - supplied transformation type {} is invalid.".format(
                        t["type"]
                    ),
                    print_err=True,
                )
                return
            for transform in ObfuscationUnit.__subclasses__:
                if str(transform) == t["type"]:
                    transformations.append(transform.from_json(t))
                    break
        return Pipeline(seed, *transformations)


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

    def to_json(self) -> str:
        """Converts the identity unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps({"type": str(__class__)})

    def from_json(json: str) -> Optional["IdentityUnit"]:
        """Converts the provided JSON string to an identity unit transformation, if possible.

        Args:
            json (str): The JSON string to attempt to load.

        Returns:
            The corresponding Identity Unit object if the given json is valid, or None otherwise."""
        # TODO loading the string
        return IdentityUnit()

    def __eq__(self, other: ObfuscationUnit) -> bool:
        return isinstance(other, IdentityUnit)

    def __str__(self):
        return "Identity()"


class FuncArgRandomiserTraverser(NodeVisitor):
    """TODO"""

    # TODO currently doesn't work for function pointers - need to account for this special case.
    # TODO add signed types in the future as well
    # TODO get types defined in scope also? Like enums/structs/unions etc.
    types = {
        "short": lambda: Constant("short", str(random.randint(-32767, 32767))),
        "int": lambda: Constant("int", str(random.randint(-32767, 32767))),
        "long": lambda: Constant("long", str(random.randint(-2147483647, 2147483647))),
        "long long": lambda: Constant(
            "long long", str(random.randint(-9223372036854775807, 9223372036854775807))
        ),
        "char": lambda: Constant(
            "char", f"'{random.choice(ascii_letters + ascii_digits)}'"
        ),
        "char *": lambda: Constant(
            "string",
            '"{}"'.format(
                "".join(
                    random.choices(
                        ascii_letters + ascii_digits + " ", k=random.randint(0, 50)
                    )
                )
            ),
        ),  # TODO better random strings?
        "_Bool": lambda: Constant("_Bool", str(random.choice([1, 0]))),
        "float": lambda: Constant(
            "float", str(round(random.uniform(-10000000000, 10000000000), 4))
        ),
        "double": lambda: Constant(
            "double", str(round(random.uniform(-10000000000000, 10000000000000), 6))
        ),
    }

    def __init__(self, extra: int):
        self.extra = extra
        self.func_args = dict()
        self.walk_num = 1
        self.analyzer = VariableUseAnalyzer()

    def get_extra_args(self, idents):
        extra_args = []
        basename = "extra"
        count = 0
        for i in range(self.extra):
            argname = basename + str(count)
            count += 1
            while argname in idents:
                argname = basename + str(count)
                count += 1
            argtype = IdentifierType([random.choice(list(self.types.keys()))])
            typedecl = TypeDecl(argname, [], None, argtype)
            # TODO support for pointer arguments in the future?
            # rand = random.random()
            # if rand < 0.4:
            #    typedecl = PtrDecl([], typedecl)
            #    if random < 0.075:
            #        typedecl = PtrDecl([], typedecl)
            arg = Decl(argname, [], [], [], [], typedecl, None, None, None)
            extra_args.append(arg)
        return extra_args

    def visit_FuncDef(self, node):
        if self.walk_num != 1:
            return NodeVisitor.generic_visit(self, node)
        defined_idents = self.analyzer.get_definitions_at_stmt(
            node
        )  # TODO - definitions at or used from? Which is correct?
        defined_idents = [ident[0] for ident in defined_idents]
        fname = node.decl.name
        if fname == "main":
            return NodeVisitor.generic_visit(self, node)
        fdecl = node.decl.type
        if fname not in self.func_args:
            if (
                fdecl.args is None
                or fdecl.args.params is None
                or len(fdecl.args.params) == 0
            ):
                # For empty functions, create a new ParamList, generate random extra args, and store
                extra_args = self.get_extra_args(defined_idents)
                fdecl.args = ParamList(extra_args)
                self.func_args[fname] = (fdecl.args, dict())
            elif (
                isinstance(fdecl.args.params[0], Typename)
                and fdecl.args.params[0].type.type.names[0] == "void"
            ):
                # TODO check AST for this - might be easier with Typename?
                # Don't change anything for void functions
                self.func_args[fname] = (fdecl.args, dict())
            else:
                # For non-empty functions, generate random extra args, randomise order, and store
                args = [
                    arg.name
                    for arg in fdecl.args.params
                    if not isinstance(arg, EllipsisParam)
                ]
                extra_args = self.get_extra_args(defined_idents + args)
                before_change = fdecl.args.params.copy()
                if isinstance(fdecl.args.params[-1], EllipsisParam):
                    # TODO this is wrong - all arguments need to be
                    # in the same order, bogus arguments can be inserted
                    # at the start but other args need to be in the same
                    # order otherwise va_args stuff breaks
                    ellipsis_arg = fdecl.args.params[-1]
                    fdecl.args.params = fdecl.args.params[:-1] + extra_args
                    random.shuffle(fdecl.args.params)
                    fdecl.args.params.append(ellipsis_arg)
                else:
                    fdecl.args.params += extra_args
                    random.shuffle(fdecl.args.params)
                mapping = {}
                for i, arg in enumerate(before_change):
                    if isinstance(
                        arg, EllipsisParam
                    ):  # TODO currently broken on variadic functions
                        mapping[i] = -1
                    else:
                        mapping[i] = fdecl.args.params.index(arg)
                self.func_args[fname] = (fdecl.args, mapping)
        else:
            fdecl.args = self.func_args[fname][0]
        NodeVisitor.generic_visit(self, node)

    def get_random_val(
        self, node
    ):  # TODO currently only supports a constant option - should be option to only randomise
        # using variables in the program, wherever possible - very sick idea!
        return self.types[node.type.type.names[0]]()

    def visit_FuncCall(self, node):
        fname = node.name.name
        if self.walk_num == 1 or fname not in self.func_args or node.args is None:
            return NodeVisitor.generic_visit(self, node)
        new_args, mapping = self.func_args[fname]
        first_arg = new_args.params[0].type.type
        if isinstance(first_arg, IdentifierType) and first_arg.names[0] == "void":
            return NodeVisitor.generic_visit(self, node)
        call_args = [None] * (len(node.args.exprs) + self.extra)
        for before, after in mapping.items():
            if after == -1:  # Ellipsis Param (variadic function)
                for i in range(len(node.args.exprs) - 1, before - 1, -1):
                    call_args[after] = node.args.exprs[i]
                    after -= 1
            else:
                call_args[after] = node.args.exprs[before]
        for i, arg in enumerate(call_args):
            if arg is not None:
                continue
            call_args[i] = self.get_random_val(new_args.params[i])
        node.args.exprs = call_args
        NodeVisitor.generic_visit(self, node)

    def visit_FileAST(self, node):
        self.analyzer.input(node)
        self.analyzer.process()
        NodeVisitor.generic_visit(self, node)
        self.walk_num += 1
        NodeVisitor.generic_visit(self, node)


class FuncArgumentRandomiseUnit(ObfuscationUnit):
    """Implements function argument randomising, switching around the order of function arguments
    and inserting redundant, unused arguments to make the function interface more confusing."""

    name = "Function Interface Randomisation"
    description = "Randomise Function Arguments to make them less compehensible"

    def __init__(self, extra_args: int):
        self.extra_args = extra_args
        self.traverser = FuncArgRandomiserTraverser(extra_args)

    def transform(self, source: CSource) -> CSource:
        self.traverser.visit(source.t_unit)
        new_contents = generate_new_contents(source)
        return CSource(source.fpath, new_contents, source.t_unit)

    def edit_cli(self) -> bool:  # TODO - maybe allow users to give specific functions?
        print(f"The current number of extra arguments is {self.extra_args}.")
        print("What is the new number of extra arguments per function?")
        extra = get_int(0, None)
        if extra is None:
            return False
        self.extra_args = extra
        self.traverser.extra = extra
        return True

    def get_cli() -> Optional["FuncArgumentRandomiseUnit"]:
        # TODO should I add an option to make randomisation optional?
        print("How many extra arguments should be inserted?")
        extra = get_int(0, None)
        if extra is None:
            return False
        return FuncArgumentRandomiseUnit(extra)

    def to_json(self) -> str:
        """Converts the function argument randomisation unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps({"type": str(__class__), "extra_args": self.extra_args})

    def from_json(json: str) -> Optional["FuncArgumentRandomiseUnit"]:
        """Converts the provided JSON string to a function argument randomisation transformation, if possible.

        Args:
            json (str): The JSON string to attempt to load.

        Returns:
            The corresponding argument randomisation unit object if the given json is valid, or None otherwise."""
        # TODO loading the string & rest of the function
        pass

    def __eq__(self, other: ObfuscationUnit) -> bool:
        if not isinstance(other, FuncArgumentRandomiseUnit):
            return False
        return self.extra_args == other.extra_args

    def __str__(self) -> str:
        extra_args_flag = f"extra={self.extra_args}"
        return f"RandomiseFuncArgs({extra_args_flag})"


class StringEncodeTraverser(NodeVisitor):
    """Traverses the program AST looking for string literals and encoding them into
    some incomprehensible form."""

    escape_chars = {
        "a": "'\\x07'",
        "b": "'\\x08'",
        "e": "'\\x1B'",
        "f": "'\\x0C'",
        "n": "'\\x0A'",
        "r": "'\\x0D'",
        "t": "'\\x09'",
        "v": "'\\x0B'",
        "\\": "'\\x5C'",
        "'": "'\\x27'",
        '"': "'\\x22'",
        "?": "'\\x3F'",
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
            if char == "\\" and i != max_index:
                check_next = True
                continue
            octal = "'\\" + str(oct(ord(char)))[2:] + "'"
            char_node = Constant("char", octal)
            chars.append(char_node)
        chars.append(Constant("char", "'\\0'"))
        return chars

    def make_compound_literal(self, init_node):
        identifier_node = IdentifierType(["char"])
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
    """Implements a string literal encoding (SLE) obfuscation transformation, which takes the
    input source code and encodes string literals in the code according to some encoding method
    such that the program still performs the same functionality, but strings can no longer be
    easily read in the code."""

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

    def to_json(self) -> str:
        """Converts the string encoding unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps({"type": str(__class__), "style": self.style.name})

    def from_json(json: str) -> Optional["StringEncodeUnit"]:
        """Converts the provided JSON string to a string encoding transformation, if possible.

        Args:
            json (str): The JSON string to attempt to load.

        Returns:
            The corresponding string encoding unit object if the given json is valid, or None otherwise."""
        # TODO loading the string & rest of the function
        pass

    def __eq__(self, other: ObfuscationUnit) -> bool:
        if not isinstance(other, StringEncodeUnit):
            return False
        return self.style == other.style

    def __str__(self):
        style_flag = f"style={self.style.name}"
        return f"StringEncode({style_flag})"


class IntegerEncodeTraverser(NodeVisitor):
    """TODO"""

    class Style(Enum):
        SIMPLE = "Simple Encoding (Multiply-Add)"
        # SPLIT = "Split Integer Literals (Not Yet Implemented)"
        LINKEDlIST = "Linked List Opaque Expression Encoding (Not Yet Implemented)"
        ARRAY = "Array Opaque Expression Encoding (Not Yet Implemented)"
        MBA = "Mixed-Boolean Arithmetic (Not Yet Implemented)"  # TODO input dependent? Entropy-based

    def __init__(self, style):
        self.style = style
        self.ignore = set()
        self.funcs = dict()
        self.add_args = set()
        self.current_func = []
        self.traverse_num = 1

    def simple_encode(self, child):
        # Form f(i) = a * i + b to encode f(i) as i.
        value = int(child.value)
        if abs(value) > 1000:
            upper_bound = floor(sqrt(abs(value)))
            lower_bound = upper_bound // 3
            mul_const = random.randint(lower_bound, upper_bound)
            encoded_val = value // mul_const
            add_const = value % mul_const
        else:
            mul_const = random.randint(3000, 10000)
            encoded_val = random.randint(3000, 10000)
            add_const = value - mul_const * encoded_val
        mul_const_node = Constant("int", mul_const)
        encoded_node = Constant("int", encoded_val)
        add_const_node = Constant("int", abs(add_const))
        mul_node = BinaryOp("*", mul_const_node, encoded_node)
        if add_const >= 0:
            add_node = BinaryOp("+", mul_node, add_const_node)
        else:
            add_node = BinaryOp("-", mul_node, add_const_node)
        return add_node

    def mba_encode(self, child):
        pass

    def encode_int(self, child):
        if self.style == self.Style.SIMPLE:
            encoded = self.simple_encode(child)
            self.ignore.add(encoded)
            return encoded
        elif self.style == self.Style.MBA:
            if self.traverse_num > 1:
                encoded = self.mba_encode(child)  # TODO change
                self.ignore.add(encoded)
                return encoded
            else:
                if self.current_func not in self.add_args:
                    self.add_args.add(self.current_func)
                return None

    def visit_FuncDef(self, node):
        self.current_func = node
        if self.traverse_num > 1:

            self.generic_visit(node)
            return
        self.funcs[node] = node.decl.type.args
        self.generic_visit(node)

    def generic_visit(self, node):
        if node in self.ignore:
            return
        for child in node.children():
            if isinstance(child[1], Constant) and child[1].type == "int":
                new_child = self.encode_int(child[1])
                if new_child is not None:
                    parts = [p[:-1] if p[-1] == "]" else p for p in child[0].split("[")]
                    if (
                        len(parts) == 1
                    ):  # TODO this will be broke wherever else I did this also
                        setattr(node, child[0], new_child)
                    else:
                        getattr(node, parts[0])[int(parts[1])] = new_child
        NodeVisitor.generic_visit(self, node)


class IntegerEncodeUnit(ObfuscationUnit):
    """Implements an integer literal encoding (LE) obfuscation transformation, which takes the
    input source code and encodes integer literals in the code according to some encoding method
    such that the program still performs the same functionality, but integer constants can no longer
    be easily read in code. We only encode literals and not floats due to necessary precision."""

    name = "Integer Literal Encoding"
    description = "Encode integer literals to make them hard to determine"

    def __init__(self, style):
        self.style = style
        self.traverser = IntegerEncodeTraverser(style)

    def transform(self, source: CSource) -> CSource:
        self.traverser.visit(source.t_unit)
        new_contents = generate_new_contents(source)
        return CSource(source.fpath, new_contents, source.t_unit)

    def edit_cli(self) -> bool:
        options = [s.value for s in IntegerEncodeTraverser.Style]
        prompt = f"\nThe current encoding style is {self.style.value}.\n"
        prompt += "Choose a new style for integer encoding.\n"
        choice = menu_driven_option(options, prompt)
        if choice == -1:
            return False
        self.style = self.Style(options[choice])
        self.traverser.style = self.style
        return True

    def get_cli() -> Optional["IntegerEncodeUnit"]:
        options = [s.value for s in IntegerEncodeTraverser.Style]
        prompt = "\nChoose a style for the integer encoding.\n"
        choice = menu_driven_option(options, prompt)
        if choice == -1:
            return None
        style = IntegerEncodeTraverser.Style(options[choice])
        return IntegerEncodeUnit(style)

    def to_json(self) -> str:
        """Converts the integer encoding unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps({"type": str(__class__), "style": self.style.name})

    def from_json(json: str) -> Optional["IntegerEncodeUnit"]:
        """Converts the provided JSON string to an integer encoding transformation, if possible.

        Args:
            json (str): The JSON string to attempt to load.

        Returns:
            The corresponding integer encoding unit object if the given json is valid, or None otherwise."""
        # TODO loading the string & rest of the function
        pass

    def __eq__(self, other: ObfuscationUnit) -> bool:
        if not isinstance(other, IntegerEncodeUnit):
            return False
        return self.style == other.style

    def __str__(self) -> str:
        style_flag = f"style={self.style.name}"
        return f"IntegerEncode({style_flag})"


class IdentifierRenamer:
    """Traverses the program AST looking for non-external identifiers (except main),
    transforming them to some random scrambled identifier."""

    def __init__(self, style: "IdentifierTraverser.Style", minimiseIdents: bool):
        self.mappings = [
            {
                TypeKinds.NONSTRUCTURE: {
                    "main": "main",
                },
                TypeKinds.STRUCTURE: {},
                TypeKinds.LABEL: {},
                "fields": {},
            }
        ]
        self.reverse = [
            {
                TypeKinds.NONSTRUCTURE: {
                    "main": "main",
                },
                TypeKinds.STRUCTURE: {},
                TypeKinds.LABEL: {},
            }
        ]
        self.new_idents_set = set()  # Maintain a set for fast checking
        self.new_idents = (
            []
        )  # Maintain a list for ordering (try and re-use as much as possible)
        self.current_struct = None
        self.struct_ident_index = 0
        self.style = style
        self.minimiseIdents = minimiseIdents
        self.analyzer = VariableUseAnalyzer()

    def generate_new_ident(self):
        new_ident = ""
        while len(new_ident) == 0 or new_ident in self.new_idents_set:
            if self.style == IdentifierTraverser.Style.COMPLETE_RANDOM:
                size_ = random.randint(4, 19)
                new_ident = random.choices(ascii_letters)[0]
                new_ident += "".join(
                    random.choices(ascii_letters + ascii_digits + "_" * 6, k=size_)
                )
            elif self.style == IdentifierTraverser.Style.ONLY_UNDERSCORES:
                new_ident = "_" * (len(self.new_idents) + 1)
            elif self.style == IdentifierTraverser.Style.MINIMAL_LENGTH:
                cur_num = len(self.new_idents)
                # choices = "_" + ascii_letters + ascii_digits
                choices = ascii_letters
                new_ident = ""
                # new_ident += choices[cur_num // len(ascii_digits)]
                while cur_num >= 0:
                    new_ident += choices[cur_num % len(choices)]
                    cur_num = cur_num // len(choices)
                    if cur_num == 0:
                        break
        self.new_idents_set.add(new_ident)
        self.new_idents.append(new_ident)
        return new_ident

    def get_current_mapping(self, ident, kind):
        for scope in self.mappings[::-1]:
            if ident in scope[kind]:
                return scope[kind][ident]
        return None

    def get_current_reverse(self, new_ident, kind):
        for scope in self.reverse[::-1]:
            if new_ident in scope[kind]:
                return scope[kind][new_ident]
        return None

    def transform_idents(self, scope):
        # TODO this method also breaks on while/fors with iterators in the condition:
        #   > if I have two loops with i then i should count as being delcared inside the scope
        #     but it's currently declared outside, meaning that only the latest i naming
        #     is used, generating broken code.
        # TODO this also doesn't work with labels currently - they should be handled separately and scoped
        # by function, not compound! Why is this so hard...
        scope_info = self.analyzer.info[scope]
        self.mappings.append(
            {
                TypeKinds.NONSTRUCTURE: {},
                TypeKinds.STRUCTURE: {},
                TypeKinds.LABEL: {},
                "fields": {},
            }
        )
        self.reverse.append(
            {
                TypeKinds.NONSTRUCTURE: {},
                TypeKinds.STRUCTURE: {},
                TypeKinds.LABEL: {},
            }
        )
        for ASTnode, idents in scope_info["idents"].items():
            for info in idents:
                attr, kind, structure, is_definition = info
                name = getattr(ASTnode, attr)
                if isinstance(name, list):  # TODO - is this correct?
                    name = ".".join(name)
                if is_definition:
                    if name == "main":
                        continue
                    if structure is not None and not isinstance(structure, Enum):
                        if structure != self.current_struct:
                            self.current_struct = structure
                            self.mappings[-1]["fields"][None] = {}
                            self.struct_ident_index = 0
                        if self.struct_ident_index >= len(self.new_idents):
                            # Out of idents, must generate more
                            new_ident = self.generate_new_ident()
                        else:  # Fetch the next available ident and use it
                            new_ident = self.new_idents[self.struct_ident_index]
                        self.struct_ident_index += 1
                        setattr(ASTnode, attr, new_ident)
                        struct_name = (
                            structure if isinstance(structure, str) else structure.name
                        )
                        if self.struct_ident_index <= 1:
                            self.mappings[-1]["fields"][struct_name] = {}
                        self.mappings[-1]["fields"][struct_name][name] = new_ident
                        continue

                    # Otherwise, we check what idents are defined in the current scope,
                    # and which idents are used from this point forward
                    # TODO I'm pretty sure this is WILDLY inefficient, need to figure out a way
                    # to compute this information per-statement in one pass so that this is O(n) and not O(n^2)
                    # TODO - could I also do it by maintaining a list of used/defined for each scope
                    # and just modifying as I go??? Maybe a decent idea?
                    current_stmt = self.analyzer.get_stmt(ASTnode)
                    scope_defs = self.analyzer.get_scope_definitions(
                        scope, None, current_stmt
                    )
                    current_defs = self.analyzer.get_definitions_at_stmt(
                        current_stmt, scope
                    )
                    used_after = self.analyzer.get_usage_from_stmt(current_stmt, scope)
                    still_used = current_defs.intersection(used_after)
                    found_reuse = False
                    for new_ident in self.new_idents:
                        curr_mapping = self.get_current_reverse(new_ident, kind)
                        ident = (curr_mapping, kind)
                        if curr_mapping is None or (
                            ident not in scope_defs and ident not in still_used
                        ):
                            # We found an ident that hasn't been used for this kind, or that has been used
                            # for this kind but is no longer needed (and not defined in this scope), so
                            # we can repurpose it.
                            setattr(ASTnode, attr, new_ident)
                            self.mappings[-1][kind][name] = new_ident
                            self.reverse[-1][kind][new_ident] = name
                            found_reuse = True
                            break
                    if found_reuse:
                        continue

                    # At this point we are not in a structure, have used all mappings for this kind, and have tried
                    # and failed to re-use every mapping, so we must define a new mapping
                    new_ident = self.generate_new_ident()
                    self.mappings[-1][kind][name] = new_ident
                    self.reverse[-1][kind][new_ident] = name
                    setattr(ASTnode, attr, new_ident)
                else:  # Is a reference to some identifier
                    if structure is not None and not isinstance(structure, Enum):
                        if isinstance(structure, tuple) and isinstance(
                            structure[0], StructRef
                        ):
                            if structure[1] == "name":
                                new_ident = self.get_current_mapping(name, kind)
                                if new_ident is not None:
                                    setattr(ASTnode, attr, new_ident)
                                continue
                            # TODO anything I do here will likely break under pointers :(((
                            # need to somehow make it traverse pointerdecls and arraydecls at the right point?
                            structname = ".".join(
                                self.analyzer.types[
                                    structure[0].name.name
                                ].type.type.names
                            )
                            oldname = self.get_current_reverse(
                                structname, TypeKinds.STRUCTURE
                            )  # TODO this could cause some errors? because not accounting for type aliasing?
                            if (
                                oldname is None
                            ):  # TODO BAD TEMPORARY FIX FOR NOW. WILL BREAK SOME STUFF
                                oldname = self.get_current_reverse(
                                    structname, TypeKinds.NONSTRUCTURE
                                )
                            mapping = self.get_current_mapping(oldname, "fields")
                            if mapping is None or name not in mapping:
                                continue
                            setattr(
                                ASTnode, attr, mapping[name]
                            )  # TODO names - could cause issue - need to make a list again maybe? Not sure
                            continue
                        if isinstance(structure, (NamedInitializer,)):
                            continue  # TODO figure out what to do!?!?!?
                            # Need to figure out a way to get the struct type for minimal mapping
                        if isinstance(structure, StructRef):
                            continue
                        mapping = self.get_current_mapping(structure.name, "fields")
                        if mapping is None or name not in mapping:
                            continue
                        setattr(ASTnode, attr, mapping[name])
                        continue
                    new_ident = self.get_current_mapping(name, kind)
                    if new_ident is not None:
                        setattr(ASTnode, attr, new_ident)

        for child, _ in scope_info["children"]:
            self.transform_idents(child)
        self.mappings = self.mappings[:-1]
        self.reverse = self.reverse[:-1]

    def transform(self, source: CSource) -> None:
        self.analyzer.input(source)
        self.analyzer.process()
        self.transform_idents(None)  # Perform DFS, transforming idents


class IdentifierTraverser(NodeVisitor):
    """Traverses the program AST looking for non-external identifiers (except main),
    transforming them to some random scrambled identifier."""

    class Style(Enum):
        COMPLETE_RANDOM = "Complete Randomness"
        ONLY_UNDERSCORES = "Only underscores"  # TODO will this break anything?
        MINIMAL_LENGTH = "Minimal length"

    def __init__(self, style: Style, minimiseIdents: bool):
        self.idents = {"main": "main"}
        self._new_idents = set()
        self._scopes = list()
        self.style = style
        self.minimiseIdents = minimiseIdents

    def get_new_ident(
        self, ident
    ):  # TODO could add an option for variable reuse as well using liveness?
        if (
            self.minimiseIdents
        ):  # TODO THIS OPTION IS VERY BROKE BUT COMPLEX SO JUST LEAVE IT FOR NOW?
            for new_ident in self._new_idents:
                in_scope = False  # TODO maintain a list of unused idents - will be cleaner and cheaper
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
                size_ = random.randint(4, 19)
                new_ident = random.choices(ascii_letters)[0]
                new_ident += "".join(
                    random.choices(ascii_letters + ascii_digits + "_" * 6, k=size_)
                )
            elif self.style == self.Style.ONLY_UNDERSCORES:
                new_ident = "_" * (len(self._new_idents) + 1)
            elif self.style == self.Style.MINIMAL_LENGTH:
                cur_num = len(self._new_idents)
                # choices = "_" + ascii_letters + ascii_digits
                choices = ascii_letters
                new_ident = ""
                # new_ident += choices[cur_num // len(ascii_digits)]
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
        self._scopes[-1].remove(node.name)

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

    def visit_Pragma(self, node):  # TODO maybe warn on pragma?
        # TODO something's not working with pragmas because of how pycparser handles them!
        from .debug import log, print_error

        print_error("Error: cannot currently handle pragmas!")
        log(
            "Could not continue obfuscation because the obfuscator cannot handle pragmas!"
        )
        exit()

    def visit_StaticAssert(self, node):  # TODO what's breaking here?
        from .debug import log, print_error

        print_error("Error: cannot currently handle static assertions!")
        log(
            "Could not continue obfuscation because the obfuscator cannot handle static asserts!"
        )
        exit()


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
        self.transformer = IdentifierRenamer(style, minimiseIdents)

    def transform(self, source: CSource) -> CSource:
        if self.minimiseIdents:
            transformer = IdentifierRenamer(self.style, True)
            transformer.transform(source.t_unit)
        else:
            traverser = IdentifierTraverser(self.style, False)
            traverser.visit(source.t_unit)
        new_contents = generate_new_contents(source)
        return CSource(source.fpath, new_contents, source.t_unit)

    def edit_cli(self) -> bool:
        options = [s.value for s in IdentifierTraverser.Style]
        options.append("placeholder")
        options.append("Finish editing")
        while True:
            prompt = f'\nChoose a style for the identifier renaming. Your current style is "{self.style.value}".\n'
            if self.minimiseIdents:
                options[
                    len(IdentifierTraverser.Style)
                ] = "Disable minimal identifier usage option [WARNING:EXPERIMENTAL] (currently: ENABLED)"
            else:
                options[
                    len(IdentifierTraverser.Style)
                ] = "Enable minimal identifer usage option [WARNING:EXPERIMENTAL] (currently: DISABLED)"
            choice = menu_driven_option(options, prompt)
            if choice == -1:
                return False
            elif choice == len(IdentifierTraverser.Style):
                self.minimiseIdents = not self.minimiseIdents
            elif choice == len(options) - 1:
                return True
            else:
                self.style = IdentifierTraverser.Style(options[choice])

    def get_cli() -> Optional["IdentitifierRenameUnit"]:
        options = [s.value for s in IdentifierTraverser.Style]
        prompt = "\nChoose a style for the identifier renaming.\n"
        minimiseIdents = False
        validChoice = False
        while not validChoice:
            if minimiseIdents:
                options.append(
                    "Disable minimal identifier usage option [WARNING:EXPERIMENTAL] (currently: ENABLED)"
                )
            else:
                options.append(
                    "Enable minimal identifer usage option [WARNING:EXPERIMENTAL] (currently: DISABLED)"
                )
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

    def to_json(self) -> str:
        """Converts the identifier renaming unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps(
            {
                "type": str(__class__),
                "style": self.style.name,
                "minimiseIdents": self.minimiseIdents,
            }
        )

    def from_json(json: str) -> Optional["IdentitifierRenameUnit"]:
        """Converts the provided JSON string to an identifier renaming transformation, if possible.

        Args:
            json (str): The JSON string to attempt to load.

        Returns:
            The corresponding identifier renaming unit object if the given json is valid, or None otherwise."""
        # TODO loading the string & rest of the function
        pass

    def __eq__(self, other: ObfuscationUnit) -> bool:
        if not isinstance(other, IdentitifierRenameUnit):
            return False
        return self.style == other.style

    def __str__(self):
        style_flag = f"style={self.style.name}"
        minimise_ident_flag = (
            f"minimal={'ENABLED' if self.minimiseIdents else 'DISABLED'}"
        )
        return f"RenameIdentifiers({style_flag},{minimise_ident_flag})"


class ArithmeticEncodeTraverser(NodeVisitor):
    """TODO"""

    def __init__(self, transform_depth: int):
        self.transform_depth = transform_depth
        self.var_types = []
        self.func_types = dict()
        self.type_cache = dict()
        self.ignore_list = set()

    def get_var_type(self, ident):
        for scope in self.var_types[::-1]:
            if ident in scope:
                return scope[ident]
        return None

    def get_func_type(self, ident):
        if ident in self.func_types:
            return self.func_types[ident]
        return None

    def is_int_type(self, node):
        if isinstance(node, (UnaryOp, BinaryOp)) and node in self.type_cache:
            return self.type_cache[node]
        if isinstance(node, Constant) and node.type == "int":
            return True
        elif isinstance(node, ID) and self.get_var_type(node.name) == "int":
            return True
        elif (
            isinstance(node, StructRef) and node.type == "int"
        ):  # TODO check this one - is this attr set?
            return True
        elif (
            isinstance(node, Cast) and node.to_type.type.type == "int"
        ):  # TODO check this one
            return True
        elif isinstance(node, FuncCall) and self.get_func_type(node.name) == "int":
            return True
        elif isinstance(node, ArrayRef) and self.get_var_type(node.name) == "int":
            return True
        elif isinstance(node, UnaryOp):
            self.type_cache[node] = self.is_int_type(node.expr) or node.op == "!"
            return self.type_cache[node]
        elif isinstance(node, BinaryOp):
            self.type_cache[node] = (
                self.is_int_type(node.left)
                and self.is_int_type(node.right)
                or node.op in ["<", "<=", ">", ">=", "==", "!=", "&&", "||", "%", "//"]
            )
            return self.type_cache[node]
        return False

    unary_subs = {
        "-": [
            lambda n: BinaryOp(
                "+", UnaryOp("~", n.expr), Constant("int", "1")
            ),  # -x = ¬x + 1
            lambda n: UnaryOp(
                "~", BinaryOp("-", n.expr, Constant("int", "1"))
            ),  # -x = ¬(x - 1)
        ],
        "~": [
            lambda n: BinaryOp(
                "-", UnaryOp("-", n.expr), Constant("int", "1")
            ),  # ¬x = -x - 1
        ],
    }

    # TODO can llvm detect and optimise some of these (see O-MVLL). If so, how can we stop this?
    binary_subs = {  # TODO correctness - what if one argument changes some value? Then not correct - HOW!?!?!?
        "+": [
            lambda n: BinaryOp(  # x + y = x - ¬y - 1
                "-", BinaryOp("-", n.left, UnaryOp("~", n.right)), Constant("int", "1")
            ),
            lambda n: BinaryOp(  # x + y = (x ^ y) + 2 * (x & y)
                "+",
                BinaryOp("^", n.left, n.right),
                BinaryOp("<<", BinaryOp("&", n.left, n.right), Constant("int", "1")),
            ),
            lambda n: BinaryOp(  # x + y = (x | y) + (x & y)
                "+", BinaryOp("|", n.left, n.right), BinaryOp("&", n.left, n.right)
            ),
            lambda n: BinaryOp(  # x + y = 2 * (x | y) - (x ^ y)
                "-",
                BinaryOp("<<", BinaryOp("|", n.left, n.right), Constant("int", "1")),
                BinaryOp("^", n.left, n.right),
            ),
        ],
        "-": [
            lambda n: BinaryOp(  # x - y = x + ¬y + 1
                "+", BinaryOp("+", n.left, UnaryOp("~", n.right)), Constant("int", "1")
            ),
            lambda n: BinaryOp(  # x - y = (x ^ y) - 2 * (¬x & y)
                "-",
                BinaryOp("^", n.left, n.right),
                BinaryOp(
                    "<<",
                    BinaryOp("&", UnaryOp("~", n.left), n.right),
                    Constant("int", "1"),
                ),
            ),
            lambda n: BinaryOp(  # x - y = (x & ¬y) - (¬x & y)
                "-",
                BinaryOp("&", n.left, UnaryOp("~", n.right)),
                BinaryOp("&", UnaryOp("~", n.left), n.right),
            ),
            lambda n: BinaryOp(  # x - y = 2 * (x & ¬y) - (x ^ y)
                "-",
                BinaryOp(
                    "<<",
                    BinaryOp("&", n.left, UnaryOp("~", n.right)),
                    Constant("int", "1"),
                ),
                BinaryOp("^", n.left, n.right),
            ),
        ],
        "^": [
            lambda n: BinaryOp(  # x ^ y = (x | y) - (x & y)
                "-", BinaryOp("|", n.left, n.right), BinaryOp("&", n.left, n.right)
            ),
        ],
        "|": [
            lambda n: BinaryOp(  # x | y = (x & ¬y) + y
                "+", BinaryOp("&", n.left, UnaryOp("~", n.right)), n.right
            ),
        ],
        "&": [
            lambda n: BinaryOp(  # x & y = (¬x | y) - ¬x
                "-", BinaryOp("|", UnaryOp("~", n.left), n.right), UnaryOp("~", n.left)
            ),
        ],
    }

    def generic_visit(
        self, node
    ):  # TODO broken - we just assume only integer operations for now!
        if node in self.ignore_list:
            return
        for child in node.children():
            if isinstance(child[1], (UnaryOp, BinaryOp)):
                current = child[1]
                applied_count = 0
                while applied_count < self.transform_depth:
                    if (
                        isinstance(current, UnaryOp)
                        and current.op not in self.unary_subs
                    ) or (
                        isinstance(current, BinaryOp)
                        and current.op not in self.binary_subs
                    ):
                        break
                    if isinstance(current, UnaryOp):
                        options = self.unary_subs[current.op]
                    else:
                        options = self.binary_subs[current.op]
                    chosen_func = options[random.randint(0, len(options) - 1)]
                    current = chosen_func(current)
                    parts = [p[:-1] if p[-1] == "]" else p for p in child[0].split("[")]
                    if (
                        len(parts) == 1
                    ):  # TODO this will be broke wherever else I did this also
                        setattr(node, child[0], current)
                    else:
                        getattr(node, parts[0])[int(parts[1])] = current
                    self.ignore_list.add(current)
                    applied_count += 1
        NodeVisitor.generic_visit(self, node)


class ArithmeticEncodeUnit(ObfuscationUnit):
    """TODO"""

    name = "Integer Arithmetic Encoding"
    description = "Encode integer variable arithmetic to make code less comprehensible"

    def __init__(self, level):
        self.level = level
        self.traverser = ArithmeticEncodeTraverser(level)

    def transform(self, source: CSource) -> CSource:
        self.traverser.visit(source.t_unit)
        new_contents = generate_new_contents(source)
        return CSource(source.fpath, new_contents, source.t_unit)

    def edit_cli(self) -> bool:
        print(f"The current arithmetic encoding depth is {self.level}.")
        print("What is the new depth (recommended: 1 <= d <= 5) of the encoding?")
        depth = get_int(1, None)
        if depth is None:
            return False
        self.level = depth
        self.traverser.transform_depth = depth
        return True

    def get_cli() -> Optional["IntegerEncodeUnit"]:
        print(
            "What recursive arithmetic encoding depth should be used? (recommended: 1 <= d <= 5)"
        )
        depth = get_int(1, None)
        if depth is None:
            return False
        return ArithmeticEncodeUnit(depth)

    def to_json(self) -> str:
        """Converts the arithmetic encoding unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps({"type": str(__class__), "depth": self.level})

    def from_json(json: str) -> Optional["ArithmeticEncodeUnit"]:
        """Converts the provided JSON string to an arithmetic encoding transformation, if possible.

        Args:
            json (str): The JSON string to attempt to load.

        Returns:
            The corresponding arithmetic encoding unit object if the given json is valid, or None otherwise."""
        # TODO loading the string & rest of the function
        pass

    def __eq__(self, other: ObfuscationUnit) -> bool:
        if not isinstance(other, ArithmeticEncodeUnit):
            return False
        return self.level == other.level

    def __str__(self) -> str:
        level_flag = f"depth={self.level}"
        return f"ArithmeticEncode({level_flag})"  # TODO finish/fix this method


class ClutterWhitespaceUnit(ObfuscationUnit):  # TODO picture extension?
    """Implements simple source-level whitespace cluttering, breaking down the high-level abstraction of
    indentation and program structure by altering whitespace in the file."""

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
        prev = None
        spaced_tokens = c_lexer.CLexer.keywords + c_lexer.CLexer.keywords_new + ("ID",)
        spaced_end_tokens = spaced_tokens + (
            "INT_CONST_DEC",
            "INT_CONST_OCT",
            "INT_CONST_HEX",
            "INT_CONST_BIN",
            "INT_CONST_CHAR",
            "FLOAT_CONST",
            "HEX_FLOAT_CONST",
        )
        while token is not None:
            addSpace = (
                prev is not None
                and prev.type in spaced_tokens
                and token.type in spaced_end_tokens
            )
            cur_line_length += len(token.value) + (1 if addSpace else 0)
            if cur_line_length <= max_line_length:
                if addSpace:
                    new_contents += " "
                new_contents += token.value
            elif (
                token.type
                in (
                    "STRING_LITERAL",
                    "WSTRING_LITERAL",
                    "U8STRING_LITERAL",
                    "U16STRING_LITERAL",
                    "U32STRING_LITERAL",
                )
                and cur_line_length - len(token.value) >= 4
            ):
                split_size = max_line_length - cur_line_length + len(token.value) - 1
                if addSpace:
                    new_contents += " "
                    split_size -= 1
                new_contents += token.value[:split_size] + token.value[0] + "\n"
                cur_line_length = 0
                token.value = token.value[0] + token.value[split_size:]
                continue
            else:
                cur_line_length = len(token.value)
                new_contents += "\n" + token.value
            prev = token
            token = lexer.token()
        return CSource(source.fpath, new_contents)

    def edit_cli(self) -> bool:
        return True

    def get_cli() -> Optional["ClutterWhitespaceUnit"]:
        return ClutterWhitespaceUnit()

    def to_json(self) -> str:
        """Converts the whitespace cluttering unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps({"type": str(__class__)})

    def from_json(json: str) -> Optional["ClutterWhitespaceUnit"]:
        """Converts the provided JSON string to a whitespace cluttering transformation, if possible.

        Args:
            json (str): The JSON string to attempt to load.

        Returns:
            The corresponding whitespace cluttering unit object if the given json is valid, or None otherwise."""
        # TODO loading the string & rest of the function
        pass

    def __eq__(self, other: ObfuscationUnit) -> bool:
        return isinstance(other, ClutterWhitespaceUnit)

    def __str__(self):
        return "ClutterWhitespace()"


class DiTriGraphEncodeUnit(ObfuscationUnit):
    """Implements a string literal encoding (SLE) obfuscation transformation, which takes the
    input source code and encodes string literals in the code according to some encoding method
    such that the program still performs the same functionality, but strings can no longer be
    easily read in the code."""

    # TODO WARNING ORDERING - SHOULD COME LAST?
    name = "Digraph/Trigraph Encoding"
    description = (
        "Encodes certain symbols with Digraphs/Trigraphs to make them incomprehensible"
    )

    digraph_map = {
        "[": "<:",
        "]": ":>",
        "{": "<%",
        "}": "%>",
        "#": "%:",
    }

    trigraph_map = {
        "#": "??=",
        "\\": "??/",
        "^": "??'",
        "[": "??(",
        "]": "??)",
        "|": "??!",
        "{": "??<",
        "}": "??>",
        "~": "??-",
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
            if (char == "'" or char == '"') and prev != "\\":
                if str_top is None:
                    str_top = char
                elif str_top == char:
                    str_top = None
            if str_top is not None or random.random() > self.chance:
                new_contents += char
                prev = char
                continue
            if (
                self.style == self.Style.MIXED
                and char in self.digraph_map
                or char in self.trigraph_map
            ):
                if random.randint(1, 2) == 1 and char in self.digraph_map:
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
        if prob == float("nan"):
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
        if prob == float("nan"):
            return None
        return DiTriGraphEncodeUnit(style, prob)

    def to_json(self) -> str:
        """Converts the digraph/trigraph encoding unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps(
            {"type": str(__class__), "style": self.style.name, "chance": self.chance}
        )

    def from_json(json: str) -> Optional["ArithmeticEncodeUnit"]:
        """Converts the provided JSON string to a digraph/trigraph encoding transformation, if possible.

        Args:
            json (str): The JSON string to attempt to load.

        Returns:
            The corresponding digraph/trigraph encoding unit object if the given json is valid, or None otherwise."""
        # TODO loading the string & rest of the function
        pass

    def __eq__(self, other: ObfuscationUnit) -> bool:
        if not isinstance(other, DiTriGraphEncodeUnit):
            return False
        return self.style == other.style and self.chance == other.chance

    def __str__(self):
        style_flag = f"style={self.style.name}"
        probability_flag = f"p={self.chance}"
        return f"DiTriGraphEncode({style_flag},{probability_flag})"


class AugmentOpaque:
    """Augments exiting conditional statements in the program with opaque predicates,
    obfuscating the true conditional test by introducing invariants on inputs or entropy
    that evaluate to known constants at runtime."""

    name = "Opaque Predicate Augmentation"
    description = "Augments existing conditionals with invariant opaque predicates."

    pass


class InsertOpaqueUnit:
    """Inserts new conditional statements in the program with opaque predicates,
    obfuscating the true control flow of the code by introducing conditional jumps on
    invariants on inputs or entropy that evalute to known constants at runtime."""

    name = "Opaque Predicate Insertion"
    description = "Inserts new conditionals with invariant opaque predicates"

    pass


# TODO control flow flattening


class GenerateCFG(NodeVisitor):
    
    def __init__(self):
        self.levels = []
        self.breaks = []
        self.continues = []
        self.cases = []
        self.current_function = None
        self.function_decls = None
        self.pending_decls = []
        self.checked_stmts = None
        self.unavailable_idents = None
        self.cur_number = 0
        self.parent = None
        self.attr = None
        self.analyzer = None
        self.count = 0
        
    def get_unique_number(self):
        num = self.cur_number
        self.cur_number += 1
        return str(num)
        
    def visit_FileAST(self, node):
        self.analyzer = NewVariableUseAnalyzer(node)
        self.analyzer.process()
        self.generic_visit(node)
    
    # We first must break the function into the basic blocks that define it
    # TODO remove below - just logic
    # We get a potential branch on:
    #  > A ternary operator - branch to iftrue, iffalse
    #       > Evaluate condition - jump to iftrue block or iffalse block based on result
    #       >
    #  > Any lazy operator - so also && and ||
    #  > Switch-case + default
    #  > While
    #  > Do-While
    #  > if-else
    #  > Continue stmt
    #  > Break stmt
    #  > goto
    #  > label
    #  > For loop
    #  > Return statement

    def flatten_function(self, node):
        if node.body is None or len(node.body.block_items) == 0:
            return
        while_label = "L" #self.analyzer.get_unique_identifier(node, TypeKinds.LABEL)
        switch_variable = "switchVar" #self.analyzer.get_unique_identifier(node, TypeKinds.NONSTRUCTURE)
        exit = self.get_unique_number()
        entry = self.get_unique_number()
        self.cases = []
        new_statements = [
            Decl(switch_variable, None, None, None, None, 
                 TypeDecl(switch_variable, None, None, 
                          IdentifierType(['int'])),
                 Constant("int", entry), None
            ), Label(while_label, 
                     While(
                         BinaryOp("!=", 
                                  ID(switch_variable), 
                                  Constant("int", exit)),
                         Compound([
                             Switch(
                                 ID(switch_variable), 
                                 Compound(self.cases))
                         ]))
            ) 
        ]
        self.levels.append((switch_variable, while_label))
        self.transform_block(node.body, entry, exit)
        self.levels = self.levels[:-1]
        node.body.block_items = new_statements
       
    def transform_block(self, block, entry, exit):
        block_parts = []
        current_seq = []
        if isinstance(block, Compound): # TODO logic here is a bit messy? Can I clean up?
            for stmt in block.block_items:
                if isinstance(stmt, (Compound, If, Switch, While, DoWhile, For)):
                    if len(current_seq) != 0:
                        block_parts.append(current_seq)
                        current_seq = []
                    block_parts.append(stmt)
                elif isinstance(block, Decl):
                    continue
                else:
                    current_seq.append(stmt)
            block_parts.append(current_seq)
        elif isinstance(block, Decl):
            return
        elif isinstance(block, (If, Switch, While, DoWhile, For)):
            block_parts.append(block)
        else:
            block_parts.append([block])
        #print([[type(z) for z in y] for y in block_parts])
        for part in block_parts:
            part_exit = exit if part == block_parts[-1] else self.get_unique_number()
            if isinstance(part, Compound):
                self.transform_block(part, entry, part_exit)
            elif isinstance(part, If):
                self.transform_if(part, entry, part_exit)
            elif isinstance(part, Switch):
                self.transform_switch(part, entry, part_exit)
            elif isinstance(part, While):
                self.transform_while(part, entry, part_exit)
            elif isinstance(part, DoWhile):
                self.transform_do_while(part, entry, part_exit)
            elif isinstance(part, For):
                self.transform_for(part, entry, part_exit)
            elif isinstance(part, list):
                self.transform_sequence(part, entry, part_exit)
            entry = part_exit
    
    def transform_if(self, if_stmt, entry, exit):
        switch_variable = self.levels[-1][0]
        then_entry = self.get_unique_number()
        else_entry = self.get_unique_number() if if_stmt.iffalse is not None else exit
        # TODO: Labels?
        case = Case(Constant("int", entry), Compound([
            If(if_stmt.cond, 
               Assignment("=", ID(switch_variable), Constant("int", then_entry)), 
               Assignment("=", ID(switch_variable), Constant("int", else_entry))),
            Break()]))
        self.cases.append(case)
        self.transform_block(if_stmt.iftrue, then_entry, exit)
        if if_stmt.iffalse is not None:
            self.transform_block(if_stmt.iffalse, else_entry, exit)
    
    def transform_while(self, while_stmt, entry, exit):
        switch_variable = self.levels[-1][0]
        body_entry = self.get_unique_number()
        # TODO: Labels?
        case = Case(Constant("int", entry), Compound([
            If(while_stmt.cond, 
               Assignment("=", ID(switch_variable), Constant("int", body_entry)), 
               Assignment("=", ID(switch_variable), Constant("int", exit))),
            Break()]))
        self.cases.append(case)
        self.breaks.append((len(self.levels), exit))
        self.continues.append((len(self.levels), entry))
        self.transform_block(while_stmt.stmt, body_entry, entry)
        self.breaks = self.breaks[:-1]
        self.continues = self.continues[:-1]
    
    def transform_switch(self, switch_stmt, entry, exit):
        switch_variable = self.levels[-1][0]
        # TODO: Labels?
        switch_body = Compound([])
        goto_labels = []
        for i, stmt in enumerate(switch_stmt.stmt.block_items):
            if isinstance(stmt, (Case, Default)):
                goto_label = self.analyzer.get_unique_identifier(switch_stmt, TypeKinds.LABEL)
                if isinstance(stmt, Case):
                    goto_labels.append(Case(stmt.expr, [Goto(goto_label)]))
                else:
                    goto_labels.append(Default([Goto(goto_label)]))
                if stmt.stmts is None or len(stmt.stmts) == 0:
                    switch_body.block_items.append(Label(goto_label, None))
                else:
                    switch_body.block_items.append(Label(goto_label, stmt.stmts[0]))
                    switch_body.block_items += stmt.stmts[1:]
            else:
                switch_body.block_items.append(stmt)
        case = Case(Constant("int", entry), Compound([
            Switch(switch_stmt.cond, Compound(goto_labels)),
            Assignment("=", ID(switch_variable), Constant("int", exit)),
            Break()]))
        self.cases.append(case)
        self.breaks.append((len(self.levels), exit))
        self.transform_block(switch_body, self.get_unique_number(), exit)
        self.breaks = self.breaks[:-1]
    
    def transform_do_while(self, do_stmt, entry, exit):
        switch_variable = self.levels[-1][0]
        test_entry = self.get_unique_number()
        body_entry = self.get_unique_number()
        # TODO: Labels?
        test_case = Case(Constant("int", test_entry), Compound([
            If(do_stmt.cond, 
               Assignment("=", ID(switch_variable), Constant("int", body_entry)), 
               Assignment("=", ID(switch_variable), Constant("int", exit))),
            Break()]))
        self.cases.append(test_case)
        entry_case = Case(Constant("int", entry), Compound([
            Assignment("=", ID(switch_variable), Constant("int", body_entry)),
            Break()]))
        self.cases.append(entry_case)
        self.breaks.append((len(self.levels), exit))
        self.continues.append((len(self.levels), test_entry))
        self.transform_block(do_stmt.stmt, body_entry, test_entry)
        self.breaks = self.breaks[:-1]
        self.continues = self.continues[:-1]
    
    def transform_for(self, for_stmt, entry, exit):
        switch_variable = self.levels[-1][0]
        test_entry = self.get_unique_number()
        inc_entry = self.get_unique_number()
        body_entry = self.get_unique_number()
        # TODO: Labels?
        entry_case = Case(Constant("int", entry), Compound([
            for_stmt.init, # TODO what if this is None? Need to deal with this
            Assignment("=", ID(switch_variable), Constant("int", test_entry)),
            Break()]))
        self.cases.append(entry_case)
        test_case = Case(Constant("int", test_entry), Compound([
            If(for_stmt.cond, 
               Assignment("=", ID(switch_variable), Constant("int", body_entry)),
               Assignment("=", ID(switch_variable), Constant("int", exit))),
            Break()]))
        self.cases.append(test_case)
        inc_case = Case(Constant("int", inc_entry), Compound([
            for_stmt.next, # TODO what if this is None? Need to deal with this
            Assignment("=", ID(switch_variable), Constant("int", test_entry)),
            Break()]))
        self.cases.append(inc_case)
        self.breaks.append((len(self.levels), exit))
        self.continues.append((len(self.levels), inc_entry))
        self.transform_block(for_stmt.stmt, body_entry, inc_entry)
        self.breaks = self.breaks[:-1]
        self.continues = self.continues[:-1]
        
    def transform_sequence(self, sequence, entry, exit):
        # TODO: Labels?
        stmts = []
        case = Case(Constant("int", entry), Compound(stmts))
        for stmt in sequence:
            if isinstance(stmt, Continue):
                stmts.append(
                    Assignment("=", 
                               ID(self.levels[self.continues[-1][0]-1][0]),
                               Constant("int", self.continues[-1][1])))
                if self.continues[-1][0] != len(self.levels):
                    stmts.append(
                        Goto(self.levels[self.continues[-1][0]-1][1]))
                else:
                    stmts.append(Break())
            elif isinstance(stmt, Break):
                stmts.append(
                    Assignment("=", 
                               ID(self.levels[self.breaks[-1][0]-1][0]),
                               Constant("int", self.breaks[-1][1])))
                if self.breaks[-1][0] != len(self.levels):
                    stmts.append(
                        Goto(self.levels[self.breaks[-1][0]-1][1]))
                else:
                    stmts.append(Break())
            else:
                stmts.append(stmt)
        stmts.append(Assignment("=", ID(self.levels[-1][0]), Constant("int", exit)))
        stmts.append(Break())
        self.cases.append(case)
     
    def visit_FuncDef(self, node):
        self.current_function = node
        self.function_decls = set()
        self.checked_stmts = set()
        self.pending_decls = []
        if node.decl.type.args is not None:
            start_stmt = self.analyzer.compound_stmt_map[node.body][0]
        else:
            start_stmt = self.analyzer.get_stmt_from_node(node.body)
        self.unavailable_idents = self.analyzer.get_definitions_at_stmt(start_stmt)
        self.visit(node.body)
        self.flatten_function(node)
        if node.body is not None:
            node.body.block_items = self.pending_decls + node.body.block_items
        self.pending_decls = []
        self.function_decls = None
        self.current_function = None
        self.cur_number = 0
        
    def visit_Decl(self, node):
        if self.current_function is None:
            return
        # Retrieve the statement corresponding to the declaration
        stmt = self.analyzer.get_stmt_from_node(node)
        if stmt in self.checked_stmts and not isinstance(self.parent, ExprList):
            return self.generic_visit(node)
        # Perform identifier renaming if necessary to avoid variable name clashes
        prev_decl_count = len(self.function_decls)
        for ident, kind in list(self.analyzer.get_stmt_definitions(stmt)):
            if isinstance(self.parent, ExprList) and ident != node.name:
                continue
            if (ident, kind) in self.function_decls or (ident, kind) in self.unavailable_idents: # Renaming required to avoid conflicts
                num = 2
                new_ident = ident
                while (new_ident, kind) in self.function_decls or (new_ident, kind) in self.unavailable_idents:
                    new_ident = ident + str(num)
                    num += 1
                self.analyzer.change_ident(stmt, ident, kind, new_ident)
                self.function_decls.add((new_ident, kind))
            else:
                self.function_decls.add((ident, kind))
        self.checked_stmts.add(stmt)
        # Create a relevant corresponding declaration at the start of the function
        func_body = self.current_function.body
        decl = Decl(node.name, node.quals, node.align, node.storage, node.funcspec, node.type, None, node.bitsize)
        self.pending_decls.append(decl)
        # Replace the declaration with a corresponding assignment if appropriate
        if node.init is None:
            assign = None
        elif isinstance(node.init, InitList): # TODO does this fail on multi-dimensional init lists? Check
            assign = []
            for i, expr in enumerate(node.init.exprs):
                assign.append(Assignment("=", ArrayRef(ID(node.name), Constant("int", str(i))), expr))
        else:
            assign = [Assignment("=", ID(node.name), node.init)]
        if isinstance(self.parent, Compound):
            i = self.parent.block_items.index(node)
            self.parent.block_items = self.parent.block_items[:i] + \
                ([] if assign is None else assign) + self.parent.block_items[(i+1):]
        elif isinstance(self.parent, ExprList): # DeclList after transformation
            i = self.parent.exprs.index(node)
            self.parent.exprs = self.parent.exprs[:i] + \
                ([] if assign is None else assign) + self.parent.exprs[(i+1):]
        elif assign is not None and len(assign) == 1:
            setattr(self.parent, self.attr, assign)
        else:
            setattr(self.parent, self.attr, Compound(assign))
        self.generic_visit(node)
        
    def visit_DeclList(self, node):
        expr_list = ExprList(node.decls)
        if isinstance(self.parent, Compound):
            index = self.parent.block_items.index(node)
            self.parent.block_items[index] = expr_list
            self.generic_visit(expr_list)
            if len(expr_list.exprs) == 0:
                self.parent.block_items = self.parent.block_items[:index] + self.parent.block_items[(index + 1):]
        else:
            setattr(self.parent, self.attr, expr_list)
            self.generic_visit(expr_list)
            if len(expr_list.exprs) == 0:
                setattr(self.parent, self.attr, None)

    def generic_visit(self, node):
        prev = self.parent
        self.parent = node
        for child in node.children():
            self.attr = child[0]
            self.visit(child[1])
        self.parent = prev


class ControlFlowFlattenUnit(ObfuscationUnit):

    name = "Flatten Control Flow"
    description = "Flatten all Control Flow in functions into a single level to help prevent code analysis"

    def __init__(self):
        self.traverser = GenerateCFG()
        pass  # TODO

    def transform(self, source: CSource) -> CSource:
        self.traverser.visit(source.t_unit)
        new_contents = generate_new_contents(source)
        return CSource(source.fpath, new_contents, source.t_unit)

    def edit_cli(self) -> bool:
        return True  # TODO

    def get_cli() -> Optional["ControlFlowFlattenUnit"]:
        return ControlFlowFlattenUnit()  # TODO
    
    def to_json():
        pass # TODO
    
    def from_json(json):
        pass # TODO

    def __eq__(self, other: ObfuscationUnit) -> bool:
        return isinstance(other, ControlFlowFlattenUnit)  # TODO

    def __str__(self) -> str:
        return "FlattenControlFlow()"
