""" File: obfuscation.py
Implements classes for obfuscation transformations and the transform pipeline. """
from .interaction import CSource, menu_driven_option, get_float, get_int
from .utils import (
    VariableUseAnalyzer,
    NewVariableUseAnalyzer,
    TypeKinds,
    is_initialised,
)  # TODO remove if not used
from .debug import *
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtCore import Qt, QSize, QMimeData
from typing import Iterable, Optional
from abc import ABC, abstractmethod
from pycparser.c_ast import *
from pycparser import c_generator, c_lexer
from enum import Enum
from math import sqrt, floor
from string import ascii_letters, digits as ascii_digits
from copy import deepcopy
import datetime
import random
import json

# TODO some problems when using obfuscations multiple times - only designed to be used once. Need cleanup
#   ^^^ I've also had a case where StringLiteralEncode() overwrites IdentifierRenaming()? May be fixed now? Need to check
# TODO one of my opaque predicates seems to be wrong sometimes? Causes crashes/segfaults? Look into?
# TODO also sometimes combinations of all transforms causes a "change_ident" error:
#       AttributeError: 'PtrDecl' object has no attribute 'declname'
#   ^^^ think I'm not considering pointer/array types properly in ident naming unfortunately
# TODO some combinations aren't working? Why :(
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
        if (
            line.strip().startswith("#")
            or line.strip().startswith("%:")
            or line.strip().startswith("??=")
        ):
            new_contents += line + "\n"
    generator = c_generator.CGenerator()
    new_contents += generator.visit(source.t_unit)
    return new_contents


class TransformType(Enum):
    """An Enum expression the different types/categories of obfuscation transformations that
    are implemented by the program. This is used to generate the GUI display appropriately."""

    LEXICAL = 1
    ENCODING = 2
    PROCEDURAL = 3
    STRUCTURAL = 4
    # TODO better names / category split


class ObfuscationUnit(ABC):
    """An abstract base class representing some obfuscation transformation unit, such that
    any implemented transformations will be subclasses of this class. Implements methods
    for transformations, constructing the class (in a CLI), and string representation."""

    name = "ObfuscationUnit"
    description = "An abstract class representing some obfuscation transformation unit. Not yet implemented."
    extended_description = (
        """A longer description about the class, providing extended information about its use.\n"""
        """If you are seeing this generic template then this has not yet been filled in."""
    )
    type = TransformType.LEXICAL

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
    def __str__(self):
        return "ObfuscationUnit()"


class Pipeline:
    """Represents the pipeline of transformations that will be applied to some C source code
    to produce an obfuscated program. Provides functionalities for altering this pipeline
    and processing source code."""

    def __init__(self, seed: int = None, *args) -> None:
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

    def print_progress(self, index: int, start_time: datetime.datetime) -> None:
        """ Prints the current progress of the transformation pipeline to the standard
        output stream, displaying the progress through the entire pipeline as well as 
        the next transformation to process.
        
        Args:
            index (int): The index of the last processed transform. If no transforms
                are yet processed, then this is intuitvely just -1.
            start_time (datetime): The start time of the pipeline processing. """
        time_passed = str(datetime.datetime.now() - start_time)
        if "." not in time_passed:
            time_passed += ".000000"
        max_transforms = len(self.transforms)
        status = str(index + 1)
        status = (len(str(max_transforms)) - len(status)) * "0" + status
        prog_percent = "({:.2f}%)".format(100 if max_transforms == 0 else (index + 1)/max_transforms * 100)
        prog_percent = (9 - len(prog_percent)) * " " + prog_percent
        if index < len(self.transforms) - 1:
            next_transform = self.transforms[index + 1]
            next_str = str(next_transform)
        else:
            next_str = ""
        print(f"{time_passed} - [{status}/{max_transforms}] {prog_percent} {next_str}")

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
        if cfg.DISPLAY_PROGRESS:
            print("===Starting Obfuscation===")
            start_time = datetime.datetime.now()
            self.print_progress(-1, start_time)
        for i, t in enumerate(self.transforms):
            source = t.transform(source)
            if source is None:
                break
            if cfg.DISPLAY_PROGRESS:
                self.print_progress(i, start_time)
        # TODO remove - this is temporary
        analyzer = NewVariableUseAnalyzer(source.t_unit)
        analyzer.process()
        # defined_before = analyzer.get_definitions_at_stmt(source.t_unit.ext[-2].body.block_items[0].iffalse.iffalse.block_items[1])
        # used_from = analyzer.get_usage_from_stmt(source.t_unit.ext[-2].body.block_items[0].iffalse.iffalse.block_items[2])
        # needed_defs = defined_before.intersection(used_from)
        # print("Defined before this statement: \n  {}".format("  ".join([" ".join([str(x[1].name), x[0]]) for x in defined_before])))
        # print("Used in and after this statement: \n  {}".format("  ".join([" ".join([str(x[1].name), x[0]]) for x in used_from])))
        # print("Identifiers that must stay defined: \n  {}".format("  ".join([" ".join([str(x[1].name), x[0]]) for x in needed_defs])))
        # print(source.t_unit)
        return source

    def to_json(self) -> str:
        """Converts the pipeline of composed transformations to a serialised JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps(
            {
                "seed": self.seed,
                "version": cfg.VERSION,
                "transformations": [t.to_json() for t in self.transforms],
            }
        )

    def from_json(json_str: str, use_gui: bool = False) -> Optional["Pipeline"]:
        """Converts the provided serialized JSON string to a transformation pipeline.

        Args:
            json_str (str): The JSON string to attempt to load.
            use_gui (bool): Defaults false - whether to load command line units (false) or
                GUI units (true).

        Returns:
            The corresponding Pipeline object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load composition file - supplied information is not valid JSON."
            )
            return None
        if "version" not in json_obj:
            log(
                "Failed to load composition file - supplied JSON contains no version field."
            )
            return None
        elif json_obj["version"] != cfg.VERSION:
            log(
                "Failed to load composition file - version mismatch. File is of version {}, running version {}".format(
                    json_obj["version"], cfg.VERSION
                )
            )
            return None
        if "seed" not in json_obj or json_obj["seed"] is None:
            seed = None
        elif not isinstance(json_obj["seed"], int):
            log(
                "Failed to load composition file - supplied seed is not a valid integer."
            )
            return None
        else:
            seed = json_obj["seed"]
        if "transformations" not in json_obj:
            json_transformations = []
        elif not isinstance(json_obj["transformations"], list):
            log(
                "Failed to load composition file - supplied transformation is not of list type."
            )
            return None
        else:
            json_transformations = json_obj["transformations"]
        transformations = []
        if use_gui:
            subc = ObfuscationUnit.__subclasses__()
            subclasses = []
            for class_ in subc:
                subclasses += class_.__subclasses__()
        else:
            subclasses = ObfuscationUnit.__subclasses__()
        for t in json_transformations:
            json_t = json.loads(t)
            if "type" not in json_t:
                log(
                    "Failed to load composition file - supplied transformation has no type.",
                    print_err=True,
                )
                return
            elif json_t["type"] not in [t.name for t in subclasses]:
                log(
                    "Failed to load composition file - supplied transformation type '{}' is invalid.".format(
                        json_t["type"]
                    ),
                    print_err=True,
                )
                return
            for transform in subclasses:
                if transform.name == json_t["type"]:
                    transformations.append(transform.from_json(t))
                    break
        return Pipeline(seed, *transformations)


class OpaquePredicate:  # TODO use class as namespace or no?
    VALID_INT_TYPES = [
        "int8_t",
        "uint8_t",
        "int16_t",
        "uint16_t",
        "int32_t",
        "uint32_t",
        "int64_t",
        "uint64_t",
        "char",
        "unsigned char",
        "signed char",
        "unsigned int",
        "signed int",
        "int",
        "unsigned short",
        "signed short",
        "short",
        "unsigned long",
        "signed long",
        "long",
        "unsigned long long",
        "signed long long",
        "long long",
    ]
    VALID_REAL_TYPES = ["float", "double", "long double"]
    VALID_INPUT_TYPES = VALID_INT_TYPES + VALID_REAL_TYPES

    # TODO one of these (or somehow one of EITHER_PREDICATES??? is wrong sometimes - need to logic check).
    TRUE_PREDICATES = [
        # (x * x) >= 0
        lambda x: BinaryOp(
            "||",
            BinaryOp(">", x, Constant("int", "46340")),
            BinaryOp(">=", BinaryOp("*", x, x), Constant("int", "0")),
        ),
        # (x * -x) <= 0
        lambda x: BinaryOp(
            "||",
            BinaryOp(">", x, Constant("int", "23170")),
            BinaryOp(
                "<=",
                BinaryOp("*", x, UnaryOp("-", x)),
                Constant("int", "0"),
            ),
        ),
        # (7 * (y * y)) != ((x * x) + 1)
        lambda x, y: BinaryOp(
            "||",
            BinaryOp(
                "&&",
                BinaryOp(">", y, Constant("int", "6620")),
                BinaryOp(">", x, Constant("int", "46339")),
            ),
            BinaryOp(
                "!=",
                BinaryOp("*", Constant("int", "7"), BinaryOp("*", y, y)),
                BinaryOp("+", BinaryOp("*", x, x), Constant("int", "1")),
            ),
        ),
        # ((7 * (y * y)) - 1) != (x * x)
        lambda x, y: BinaryOp(
            "||",
            BinaryOp(
                "&&",
                BinaryOp(">", y, Constant("int", "6620")),
                BinaryOp(">", x, Constant("int", "46339")),
            ),
            BinaryOp(
                "!=",
                BinaryOp(
                    "-",
                    BinaryOp(
                        "*",
                        Constant("int", "7"),
                        BinaryOp("*", y, y),
                    ),
                    Constant("int", "1"),
                ),
                BinaryOp("*", x, x),
            ),
        ),
        # ((x * (x + 1)) % 2) == 0
        lambda x: BinaryOp(
            "||",
            BinaryOp(">", x, Constant("int", "46339")),
            BinaryOp(
                "==",
                BinaryOp(
                    "%",
                    BinaryOp("*", x, BinaryOp("+", x, Constant("int", "1"))),
                    Constant("int", "2"),
                ),
                Constant("int", "0"),
            ),
        ),
        # ((x * (1 + x)) % 2) != 1
        lambda x: BinaryOp(
            "||",
            BinaryOp(">", x, Constant("int", "46339")),
            BinaryOp(
                "!=",
                BinaryOp(
                    "%",
                    BinaryOp("*", x, BinaryOp("+", Constant("int", "1"), x)),
                    Constant("int", "2"),
                ),
                Constant("int", "1"),
            ),
        ),
        # ((x * ((x + 1) * (x + 2))) % 3) == 0
        lambda x: BinaryOp(
            "||",
            BinaryOp(">", x, Constant("int", "1280")),
            BinaryOp(
                "==",
                BinaryOp(
                    "%",
                    BinaryOp(
                        "*",
                        x,
                        BinaryOp(
                            "*",
                            BinaryOp("+", x, Constant("int", "1")),
                            BinaryOp("+", x, Constant("int", "2")),
                        ),
                    ),
                    Constant("int", "3"),
                ),
                Constant("int", "0"),
            ),
        ),
        # (((x + 1) * (x * (x + 2))) % 3) != 1
        lambda x: BinaryOp(
            "||",
            BinaryOp(">", x, Constant("int", "1200")),
            BinaryOp(
                "!=",
                BinaryOp(
                    "%",
                    BinaryOp(
                        "*",
                        BinaryOp("+", x, Constant("int", "1")),
                        BinaryOp(
                            "*",
                            x,
                            BinaryOp("+", x, Constant("int", "2")),
                        ),
                    ),
                    Constant("int", "3"),
                ),
                Constant("int", "1"),
            ),
        ),
        # (((x + 1) * ((x + 2) * x)) % 3) != 2
        lambda x: BinaryOp(
            "||",
            BinaryOp(">", x, Constant("int", "1200")),
            BinaryOp(
                "!=",
                BinaryOp(
                    "%",
                    BinaryOp(
                        "*",
                        BinaryOp("+", x, Constant("int", "2")),
                        BinaryOp("*", BinaryOp("+", x, Constant("int", "1")), x),
                    ),
                    Constant("int", "3"),
                ),
                Constant("int", "2"),
            ),
        ),
        # (((7 * x) * x) + 1) % 7) != 0
        lambda x: BinaryOp(
            "||",
            BinaryOp(">", x, Constant("int", "6620")),
            BinaryOp(
                "!=",
                BinaryOp(
                    "%",
                    BinaryOp(
                        "+",
                        BinaryOp("*", BinaryOp("*", Constant("int", "7"), x), x),
                        Constant("int", "1"),
                    ),
                    Constant("int", "7"),
                ),
                Constant("int", "0"),
            ),
        ),
        # ((((x * x) + x) + 7) % 81) != 0
        lambda x: BinaryOp(
            "||",
            BinaryOp(">", x, Constant("int", "46000")),
            BinaryOp(
                "!=",
                BinaryOp(
                    "%",
                    BinaryOp(
                        "+",
                        BinaryOp("+", BinaryOp("*", x, x), x),
                        Constant("int", "7"),
                    ),
                    Constant("int", "81"),
                ),
                Constant("int", "0"),
            ),
        ),
        # ((((x + 1) * x) + 7) % 81) != 0
        lambda x: BinaryOp(
            "||",
            BinaryOp(">", x, Constant("int", "46000")),
            BinaryOp(
                "!=",
                BinaryOp(
                    "%",
                    BinaryOp(
                        "+",
                        BinaryOp("*", BinaryOp("+", x, Constant("int", "1")), x),
                        Constant("int", "7"),
                    ),
                    Constant("int", "81"),
                ),
                Constant("int", "0"),
            ),
        ),
    ]

    COMPARISON_OPS = [">", ">=", "<", "<=", "==", "!="]
    BIN_ARITHMETIC_OPS = ["+", "-", "*", "/", "%"]

    EITHER_PREDICATES = [
        # x
        lambda x: x,
        # !x
        lambda x: UnaryOp("!", x),
        # x <op> 0 for some operation <op>
        lambda x: BinaryOp(
            random.choice(OpaquePredicate.COMPARISON_OPS), x, Constant("int", "0")
        ),
        # x <op> c for some constant c and operation <op>
        lambda x: BinaryOp(
            random.choice(OpaquePredicate.COMPARISON_OPS),
            x,
            Constant("int", str(random.randint(-25, 25))),
        ),
        # x <op> y for some operation <op>
        lambda x, y: BinaryOp(random.choice(OpaquePredicate.COMPARISON_OPS), x, y),
        # x <op1> y && y <op2> z for some operations <op1> and <op2>
        lambda x, y, z: BinaryOp(
            random.choice(["&&", "||"]),
            BinaryOp(random.choice(OpaquePredicate.COMPARISON_OPS), x, y),
            BinaryOp(random.choice(OpaquePredicate.COMPARISON_OPS), y, z),
        ),
        # x <op1> y <op2> z for some arithmetic operation <op1> and some comparison operation <op2>
        lambda x, y, z: BinaryOp(
            random.choice(OpaquePredicate.COMPARISON_OPS),
            BinaryOp(random.choice(OpaquePredicate.BIN_ARITHMETIC_OPS), x, y),
            z,
        ),
    ]

    def negate(expr: Node) -> Node:
        if isinstance(expr, BinaryOp):
            if expr.op == "==":
                expr.op = "!="
                return expr
            elif expr.op == "!=":
                expr.op = "=="
                return expr
            elif expr.op == "&&":  # TODO De Morgan's - check
                expr.op = "||"
                expr.left = OpaquePredicate.negate(expr.left)
                expr.right = OpaquePredicate.negate(expr.right)
                return expr
            elif expr.op == "||":
                expr.op = "&&"
                expr.left = OpaquePredicate.negate(expr.left)
                expr.right = OpaquePredicate.negate(expr.right)
                return expr
        return UnaryOp("!", expr)

    def generate_entropic_var(source, analyzer, existing_vars):
        # Create a new entropic variable to be used.
        # First determine if stdlib.h and time.h are included
        stdlib_init, time_init = is_initialised(source, ["stdlib.h", "time.h"])
        # Next determine if srand has been initialised in main
        root = source.t_unit
        if root.ext is None:
            return None
        funcs = [f for f in root.ext if isinstance(f, FuncDef) and f.decl is not None]
        main = [
            f
            for f in funcs
            if isinstance(f.decl, Decl)
            and f.decl.name is not None
            and f.decl.name == "main"
        ]
        if len(main) == 0:
            return None
        main = main[0]
        if main.body is None or main.body.block_items is None:
            return None
        srand_init = False
        for i, stmt in enumerate(main.body.block_items):
            if isinstance(stmt, FuncCall) and stmt.name is not None:
                if isinstance(stmt.name, ID) and stmt.name.name == "srand":
                    srand_init = True
                    break
        # Initialise stdlib.h/time.h/srand where necessary
        if not stdlib_init:
            source.contents = "#include <stdlib.h>\n" + source.contents
        if not time_init:
            # TODO could this break if the user already has functions used in these libraries? uh oh need to state this somewhere
            source.contents = "#include <time.h>\n" + source.contents
        if not srand_init:
            srand_call = FuncCall(
                ID("srand"),
                ExprList([FuncCall(ID("time"), ExprList([Constant("int", "0")]))]),
            )
            main.body.block_items = [srand_call] + main.body.block_items
        # Generate a new global entropic variable
        ident = analyzer.get_new_identifier(exclude=[v[0] for v in existing_vars])
        ident_decl = Decl(
            ident,
            None,
            None,
            None,
            None,
            TypeDecl(ident, None, None, IdentifierType(["int"])),
            None,
            None,
        )
        source.t_unit.ext = [ident_decl] + source.t_unit.ext
        assignment = Assignment("=", ID(ident), FuncCall(ID("rand"), None))
        for i, stmt in enumerate(main.body.block_items):
            if isinstance(stmt, FuncCall) and stmt.name is not None:
                if isinstance(stmt.name, ID) and stmt.name.name == "srand":
                    main.body.block_items = (
                        main.body.block_items[: (i + 1)]
                        + [assignment]
                        + main.body.block_items[(i + 1) :]
                    )
                    break
        return (ident, "int")


class IdentityUnit(ObfuscationUnit):
    """Implements an identity transformation, which takes the input source code and does
    nothing to it, returning it unmodified."""

    name = "Identity"
    description = "Does nothing - returns the same code entered."
    extended_description = (
        """The identity transformation is the simplest type of transform, returning \n"""
        """The exact same code that was entered. This is a simple example of a transform\n"""
        """that can be used without worrying about what might change. """
    )
    type = TransformType.LEXICAL

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
        return json.dumps({"type": str(__class__.name)})

    def from_json(json_str: str) -> Optional["IdentityUnit"]:
        """Converts the provided JSON string to an identity unit transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding Identity Unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log("Failed to load Identity() - invalid JSON provided.", print_err=True)
            return None
        if "type" not in json_obj:
            log("Failed to load Identity() - no type provided.", print_err=True)
            return None
        elif json_obj["type"] != __class__.name:
            log("Failed to load Identity() - class/type mismatch.", print_err=True)
            return None
        return IdentityUnit()

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
        self.reset()

    def reset(self):
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
        self.reset()


class FuncArgumentRandomiseUnit(ObfuscationUnit):
    """Implements function argument randomising, switching around the order of function arguments
    and inserting redundant, unused arguments to make the function interface more confusing."""

    name = "Function Interface Randomisation"
    description = "Randomise Function Arguments to make them less compehensible"
    extended_description = (
        """<html>This transformation randomises function signatures to obscure the true meanings of\n"""
        """function definitions. This is done by adding an extra number of spurious argmuments\n"""
        """that are not used to functions, and then randomising the order of these arguments.<br><br>\n\n"""
        """The only input is the number of spurious arguments to add - if no arguments are added,\n"""
        """then all that will happen is that the argument order will be randomised.<br><br>\n\n"""
        """<b>Warning:</b> does not work with pointer aliased function calls. Although variadic functions\n"""
        """are supported, they will not be transformed as correctness cannot be guaranteed.</html>"""
    )
    type = TransformType.PROCEDURAL

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
        return json.dumps({"type": str(__class__.name), "extra_args": self.extra_args})

    def from_json(json_str: str) -> Optional["FuncArgumentRandomiseUnit"]:
        """Converts the provided JSON string to a function argument randomisation transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding argument randomisation unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load RandomiseFuncArgs() - invalid JSON provided.",
                print_err=True,
            )
            return None
        if "type" not in json_obj:
            log(
                "Failed to load RandomiseFuncArgs() - no type provided.", print_err=True
            )
            return None
        elif json_obj["type"] != __class__.name:
            log(
                "Failed to load RandomiseFuncArgs() - class/type mismatch.",
                print_err=True,
            )
            return None
        elif "extra_args" not in json_obj:
            log(
                "Failed to load RandomiseFuncArgs() - no extra arguments value provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["extra_args"], int):
            log(
                "Failed to load RandomiseFuncArgs() - extra arguments is not a valid integer.",
                print_err=True,
            )
            return None
        elif json_obj["extra_args"] < 0:
            log(
                "Failed to load RandomiseFuncArgs() - extra arguments is not >= 0.",
                print_err=True,
            )
            return None
        return FuncArgumentRandomiseUnit(json_obj["extra_args"])

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
        OCTAL = "Octal"
        HEX = "Hexadecimal"
        MIXED = "Octal/Hexadecimal"
        ALL = "Octal/Hex/Regular"

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
            if self.style == self.Style.MIXED:
                style = [self.Style.OCTAL, self.Style.HEX][random.randint(0, 1)]
            elif self.style == self.Style.ALL:
                style = [self.Style.OCTAL, self.Style.HEX, None][random.randint(0, 2)]
            else:
                style = self.style
            if style == self.Style.OCTAL:
                octal_char = "'\\" + str(oct(ord(char)))[2:] + "'"
                char_node = Constant("char", octal_char)
            elif style == self.Style.HEX:
                hex_char = "'\\x" + str(hex(ord(char)))[2:] + "'"
                char_node = Constant("char", hex_char)
            else:
                char_node = Constant("char", "'" + char + "'")
            chars.append(char_node)
        chars.append(
            Constant("char", "'\\0'")
        )  # TODO can also just use a direct string instead of a (char[]) cast?
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
    extended_description = (
        """This transformation encodes literal strings as a sequence of obfuscated characters,\n"""
        """in order to make strings incomprehensible and hide their true meaning. Depending on\n"""
        """the mode selected, characters can be encoded as hexadecimal character codes, octal\n"""
        """character codes, or a mix of these and regula characters.\n\n"""
        """The only input is the encoding style to use."""
    )
    type = TransformType.ENCODING

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
        return json.dumps({"type": str(__class__.name), "style": self.style.name})

    def from_json(json_str: str) -> Optional["StringEncodeUnit"]:
        """Converts the provided JSON string to a string encoding transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding string encoding unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load StringEncode() - invalid JSON provided.", print_err=True
            )
            return None
        if "type" not in json_obj:
            log("Failed to load StringEncode() - no type provided.", print_err=True)
            return None
        elif json_obj["type"] != __class__.name:
            log("Failed to load StringEncode() - class/type mismatch.", print_err=True)
            return None
        elif "style" not in json_obj:
            log(
                "Failed to load StringEncode() - no style value provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["style"], str):
            log(
                "Failed to load StringEncode() - style is not a valid string.",
                print_err=True,
            )
            return None
        elif json_obj["style"] not in [
            style.name for style in StringEncodeTraverser.Style
        ]:
            log(
                "Failed to load StringEncode() - style '{}' is not a valid style.".format(
                    json_obj["style"]
                ),
                print_err=True,
            )
            return None
        return StringEncodeUnit(
            {style.name: style for style in StringEncodeTraverser.Style}[
                json_obj["style"]
            ]
        )

    def __str__(self):
        style_flag = f"style={self.style.name}"
        return f"StringEncode({style_flag})"


class IntegerEncodeTraverser(NodeVisitor):
    """TODO"""

    class Style(Enum):
        SIMPLE = "Simple Encoding (Multiply-Add)"
        MBA_SIMPLE = "Simple Mixed-Boolean Arithmetic Constant Hiding without Polynomial Transforms (Not Yet Implemented)"
        MBA_POLYNOMIAL = "Mixed-Boolean Arithmetic Constant Hiding with Polynomial Transforms (Not Yet Implemented)"
        # MBA_ALGORITHMIC = "Mixed-Boolean Arithmetic Hiding via. Algorithmic Encoding (Not Yet Implemented)"
        # SPLIT = "Split Integer Literals (Not Yet Implemented)"

    def __init__(self, style):
        self.style = style
        self.ignore = set()

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

    def mba_simple_encode(self, child):
        # v = int(child.value)
        # left_expr = BinaryOp("||", Constant("int", str(-v - 1)))
        # TODO in future
        pass

    def mba_polynomial_encode(self, child):
        # TODO in future
        pass

    def encode_int(self, child):
        if self.style == self.Style.SIMPLE:
            encoded = self.simple_encode(child)
            self.ignore.add(encoded)
            return encoded
        elif self.style == self.Style.MBA_SIMPLE:
            encoded = self.mba_simple_encode(child)
            self.ignore.add(encoded)
            return encoded
        elif self.style == self.Style.MBA_POLYNOMIAL:
            encoded = self.mba_polynomial_encode(child)
            self.ignore.add(encoded)
            return encoded

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

    def visit_FileAST(self, node):
        NodeVisitor.generic_visit(self, node)
        self.ignore = set()


class IntegerEncodeUnit(ObfuscationUnit):
    """Implements an integer literal encoding (LE) obfuscation transformation, which takes the
    input source code and encodes integer literals in the code according to some encoding method
    such that the program still performs the same functionality, but integer constants can no longer
    be easily read in code. We only encode literals and not floats due to necessary precision."""

    name = "Integer Literal Encoding"
    description = "Encode integer literals to make them hard to determine"
    extended_description = (
        """This transformation encodes literal integer constants in the code as the result of\n"""
        """some computation, making it harder to determine the meaning of the code from the values\n"""
        """of integers used. Note that the current implementation only allows simple encoding, which\n"""
        """can be easily automatically optimised out, and so currently only served to obfuscate source\n"""
        """code and to augment other obfuscations such as arithmetic encoding.\n\n"""
        """The only input is the integer encoding style to use, though only simple encoding is available now."""
    )
    type = TransformType.ENCODING

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
        return json.dumps({"type": str(__class__.name), "style": self.style.name})

    def from_json(json_str: str) -> Optional["IntegerEncodeUnit"]:
        """Converts the provided JSON string to an integer encoding transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding integer encoding unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load IntegerEncode() - invalid JSON provided.",
                print_err=True,
            )
            return None
        if "type" not in json_obj:
            log("Failed to load IntegerEncode() - no type provided.", print_err=True)
            return None
        elif json_obj["type"] != __class__.name:
            log("Failed to load IntegerEncode() - class/type mismatch.", print_err=True)
            return None
        elif "style" not in json_obj:
            log(
                "Failed to load IntegerEncode() - no style value provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["style"], str):
            log(
                "Failed to load IntegerEncode() - style is not a valid string.",
                print_err=True,
            )
            return None
        elif json_obj["style"] not in [
            style.name for style in IntegerEncodeTraverser.Style
        ]:
            log(
                "Failed to load IntegerEncode() - style '{}' is not a valid style.".format(
                    json_obj["style"]
                ),
                print_err=True,
            )
            return None
        return IntegerEncodeUnit(
            {style.name: style for style in IntegerEncodeTraverser.Style}[
                json_obj["style"]
            ]
        )

    def __str__(self) -> str:
        style_flag = f"style={self.style.name}"
        return f"IntegerEncode({style_flag})"


class NewNewIdentifierRenamer:
    """Traverses the program AST looking for non-external identifiers (except main),
    transform them to some random scrambled identifier."""

    def __init__(self, style: "IdentifierTraverser.Style", minimiseIdents: bool):
        self.new_idents_set = set()
        self.new_idents = []
        self.current_struct = None
        self.struct_ident_index = 0
        self.style = style

    # comehere TODO finish


class IdentifierRenamer:
    """Traverses the program AST looking for non-external identifiers (except main),
    transforming them to some random scrambled identifier."""

    def __init__(self, style: "IdentifierTraverser.Style", minimiseIdents: bool):
        self.style = style
        self.minimiseIdents = minimiseIdents
        self.reset()

    def reset(self):
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
        )  # Maintain a list for ordering (try and re-use when possible)
        self.current_struct = None
        self.struct_ident_index = 0
        self.analyzer = VariableUseAnalyzer()
        self._random_source = random.randint(0, 2**16)

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
            elif self.style == IdentifierTraverser.Style.I_AND_L:
                cur_num = len(self.new_idents)
                num_chars = 2
                num_vals = 2**num_chars
                while cur_num * 4 > num_vals:
                    num_chars += 1
                    num_vals *= 2
                hash_val = (hash(str(cur_num)) + self._random_source) % (num_vals)
                new_ident = bin(hash_val)[2:]
                new_ident = "0" * (num_chars - len(new_ident)) + new_ident
                new_ident = new_ident.replace("1", "l").replace("0", "I")
                while new_ident in self.new_idents_set:
                    # Linear probe for next available hash value
                    hash_val += 1
                    if hash_val >= num_vals:
                        hash_val = 0
                    new_ident = bin(hash_val)[2:]
                    new_ident = "0" * (num_chars - len(new_ident)) + new_ident
                    new_ident = new_ident.replace("1", "l").replace("0", "I")
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
        self.reset()


class IdentifierTraverser(NodeVisitor):
    """Traverses the program AST looking for non-external identifiers (except main),
    transforming them to some random scrambled identifier."""

    class Style(Enum):
        COMPLETE_RANDOM = "Complete Randomness"
        ONLY_UNDERSCORES = "Only underscores"  # TODO will this break anything?
        MINIMAL_LENGTH = "Minimal length"
        I_AND_L = "Blocks of l's and I's"

    def __init__(self, style: Style, minimiseIdents: bool):
        self.style = style
        self.minimiseIdents = minimiseIdents
        self.reset()

    def reset(self):
        self.idents = {"main": "main"}
        self._new_idents = set()
        self._scopes = list()
        self._random_source = random.randint(0, 2**16)

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
            elif self.style == self.Style.I_AND_L:
                cur_num = len(self._new_idents)
                num_chars = 16
                num_vals = 2**num_chars
                while cur_num * 4 > num_vals:
                    num_chars += 1
                    num_vals *= 2
                hash_val = (hash(str(cur_num)) + self._random_source) % (num_vals)
                new_ident = bin(hash_val)[2:]
                new_ident = "0" * (num_chars - len(new_ident)) + new_ident
                new_ident = new_ident.replace("1", "l").replace("0", "I")
                while new_ident in self._new_idents:
                    # Linear probe for next available hash value
                    hash_val += 1
                    if hash_val >= num_vals:
                        hash_val = 0
                    new_ident = bin(hash_val)[2:]
                    new_ident = "0" * (num_chars - len(new_ident)) + new_ident
                    new_ident = new_ident.replace("1", "l").replace("0", "I")
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
        self.reset()

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


class IdentifierRenameUnit(ObfuscationUnit):
    """Implements an identifier rename (IRN) obfuscation transformation, which takes the input
    source code and renames all identifiers (function names, parameter names, variable names, etc.)
    such that the program still performs the same functionality, but now the identifier names reveal
    no meaningful information about the program and are difficult to humanly comprehend."""

    name = "Identifier Renaming"
    description = "Renames variable/function names to make them incomprehensible."
    extended_description = (
        """This transformation randomises identifiers in the program (e.g. variable names, type names,\n"""
        """function names, etc.) to remove all symbolic meaning stored via these names in the source code.\n"""
        """Note that this will not affect the compiled code in any way.\n\n"""
        """One optional input is the style of randomisation to be used - you can choose between completely\n"""
        """random variable names, names that use only underscore characters, and minimal length names.\n"""
        """The other optional input allows you to enable identifier minimisation, where names are greedily\n"""
        """reused whenever possible to achieve the maximal overlap between names, such that obfuscation is\n"""
        """achieved by giving many different constructs the same symbolic name."""
    )
    type = TransformType.LEXICAL

    def __init__(self, style, minimiseIdents):
        self.style = style
        self.minimiseIdents = minimiseIdents
        self.transformer = IdentifierRenamer(style, minimiseIdents)

    def transform(self, source: CSource) -> CSource:
        if self.minimiseIdents:
            # TODO identifier minimisation breaking on AOCday6 example - WHY!?
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

    def get_cli() -> Optional["IdentifierRenameUnit"]:
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
                return IdentifierRenameUnit(style, minimiseIdents)
        return None

    def to_json(self) -> str:
        """Converts the identifier renaming unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps(
            {
                "type": str(__class__.name),
                "style": self.style.name,
                "minimiseIdents": self.minimiseIdents,
            }
        )

    def from_json(json_str: str) -> Optional["IdentifierRenameUnit"]:
        """Converts the provided JSON string to an identifier renaming transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding identifier renaming unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load RenameIdentifiers() - invalid JSON provided.",
                print_err=True,
            )
            return None
        if "type" not in json_obj:
            log(
                "Failed to load RenameIdentifiers() - no type provided.", print_err=True
            )
            return None
        elif json_obj["type"] != __class__.name:
            log(
                "Failed to load RenameIdentifiers() - class/type mismatch.",
                print_err=True,
            )
            return None
        elif "style" not in json_obj:
            log(
                "Failed to load RenameIdentifiers() - no style value provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["style"], str):
            log(
                "Failed to load RenameIdentifiers() - style is not a valid string.",
                print_err=True,
            )
            return None
        elif json_obj["style"] not in [
            style.name for style in IdentifierTraverser.Style
        ]:
            log(
                "Failed to load RenameIdentifiers() - style '{}' is not a valid style.".format(
                    json_obj["style"]
                ),
                print_err=True,
            )
            return None
        elif "minimiseIdents" not in json_obj:
            log(
                "Failed to load RenameIdentifiers() - no identifier minimisation flag value provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["minimiseIdents"], bool):
            log(
                "Failed to load RenameIdentifiers() - identifier minimisation flag value is not a Boolean.",
                print_err=True,
            )
            return None
        return IdentifierRenameUnit(
            {style.name: style for style in IdentifierTraverser.Style}[
                json_obj["style"]
            ],
            json_obj["minimiseIdents"],
        )

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
        self.reset()

    def reset(self):
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

    def visit_FileAST(self, node):
        NodeVisitor.generic_visit(self, node)
        self.reset()


class ArithmeticEncodeUnit(ObfuscationUnit):
    """TODO"""

    name = "Integer Arithmetic Encoding"
    description = "Encode integer variable arithmetic to make code less comprehensible"
    extended_description = (
        """<html>This transformation encodes arithmetic operations within the code, replacing simple\n"""
        """additions and multipliations with compound combinations of bitwise operations and\n"""
        """alternative arithmetic. When performed on arithmetic dependent upon inputs, this cannot be\n"""
        """optimised out by a compiler and will greatly increase obfuscation.<br><br>\n\n"""
        """The only available option is the encoding depth - arithmetic operations within encoded\n"""
        """arithmetic operations can be recursively encoded to increase code complexity, and so depth\n"""
        """refers to the maximum recursive encoding depth that is allowed. A value > 5 is not recommended\n"""
        """due to the potential slowdown.<br><br>\n\n"""
        """<b>Warning:</b> This does not currently work with programs with float operations. All\n"""
        """arithmetic is encoded, and there is currently no type analysis done to only encode integer\n"""
        """operations. Do not use in programs with floats for now.<\html>"""
    )
    type = TransformType.ENCODING

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

    def get_cli() -> Optional["ArithmeticEncodeUnit"]:
        print(
            "What recursive arithmetic encoding depth should be used? (recommended: 1 <= d <= 5)"
        )
        depth = get_int(0, None)
        if depth is None:
            return False
        return ArithmeticEncodeUnit(depth)

    def to_json(self) -> str:
        """Converts the arithmetic encoding unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps({"type": str(__class__.name), "depth": self.level})

    def from_json(json_str: str) -> Optional["ArithmeticEncodeUnit"]:
        """Converts the provided JSON string to an arithmetic encoding transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding arithmetic encoding unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load ArithmeticEncode() - invalid JSON provided.",
                print_err=True,
            )
            return None
        if "type" not in json_obj:
            log("Failed to load ArithmeticEncode() - no type provided.", print_err=True)
            return None
        elif json_obj["type"] != __class__.name:
            log(
                "Failed to load ArithmeticEncode() - class/type mismatch.",
                print_err=True,
            )
            return None
        elif "depth" not in json_obj:
            log(
                "Failed to load ArithmeticEncode() - no depth value provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["depth"], int):
            log(
                "Failed to load ArithmeticEncode() - depth is not a valid integer.",
                print_err=True,
            )
            return None
        elif json_obj["depth"] < 0:
            log(
                "Failed to load ArithmeticEncode() - depth must be >= 0.",
                print_err=True,
            )
            return None
        return ArithmeticEncodeUnit(json_obj["depth"])

    def __str__(self) -> str:
        level_flag = f"depth={self.level}"
        return f"ArithmeticEncode({level_flag})"  # TODO finish/fix this method


class OpaqueAugmenter(NodeVisitor):
    class Style(Enum):
        INPUT = "Construct predicates from dynamic user input"
        ENTROPY = "Construct predicates from entropic variables"
        # LINKED_LIST = "Predicates constructed from intractable pointer aliasing on a linked list."
        # TODO above is not implemented yet

    def __init__(self, styles: Iterable[Style], probability: float = 1.0) -> None:
        self.styles = styles
        self.probability = probability
        self.reset()

    def reset(self):
        self.current_function = None
        self.parameters = None
        self.analyzer = None
        self.source = None
        self.entropic_vars = (
            []
        )  # TODO could add both global and function level entropic vars in the future?

    def process(self, source):
        if len(self.styles) == 0:
            return
        self.analyzer = NewVariableUseAnalyzer(source.t_unit)
        self.analyzer.process()
        self.source = source
        self.visit(source.t_unit)

    def generate_opaque_predicate(self, cond_expr):
        # Retrieve a random opaque predicate and check its parameters
        predicate = random.choice(OpaquePredicate.TRUE_PREDICATES)
        num_args = predicate.__code__.co_argcount
        idents = []
        # Iteratively choose variables to use in the predicate
        while len(idents) < num_args:
            styles = [s for s in self.styles]
            # Select a random style for the list of chosen styles to use (if possible)
            valid_style = False
            while not valid_style and len(styles) != 0:
                style = random.choice(styles)
                styles.remove(style)
                if style == self.Style.INPUT:
                    valid_style = (
                        self.parameters is not None
                        and len(set(self.parameters).difference(set(idents))) != 0
                    )  # TODO check logic here just in case
                elif style == self.Style.ENTROPY:
                    valid_style = True
            if valid_style == False:
                return cond_expr  # No variables to use as parameters, so exit out
                # TODO realistically I should rework this for cases with > 1 num-args, as it
                # might be that it could use an opaque predicate but doesn't, which kind of
                # goes against how I've said that probability works. Maybe I could do
                # the whole input/entropy thing in different orders (choosing that first
                # based on context factors), and then use the context of the maximum number
                # of available args to decide on the predicate (but then that does also require
                # some mess to generate entropic variables _afterwards_)
            if style == self.Style.INPUT:
                # Choose a random function parameter (not used so far) to use
                param = random.choice(self.parameters)
            elif style == self.Style.ENTROPY:
                # Randomly either choose an existing entropic variable or create a new one
                available_vars = list(set(self.entropic_vars).difference(set(idents)))
                use_new_var = len(available_vars) == 0 or random.random() >= 0.75
                if use_new_var:
                    param = OpaquePredicate.generate_entropic_var(
                        self.source, self.analyzer, self.entropic_vars
                    )
                    if param is None:
                        return cond_expr
                    self.entropic_vars.append(param)
                    # TODO could add float support in the future for entropic vars?
                else:
                    # Choose a random existing entropic variable to use
                    param = random.choice(available_vars)
            idents.append(param)
        args = []
        for ident in idents:
            if ident[1] not in OpaquePredicate.VALID_REAL_TYPES:
                args.append(ID(ident[0]))
            else:
                args.append(
                    Cast(
                        Typename(
                            None,
                            [],
                            None,
                            TypeDecl(None, [], None, IdentifierType(["int"])),
                        ),
                        ID(ident[0]),
                    )
                )
        opaque_expr = predicate(*args)
        is_true = random.random() >= 0.5
        is_before = random.random() >= 0.5
        if is_true:
            if is_before:
                return BinaryOp("&&", opaque_expr, cond_expr)
            return BinaryOp("&&", cond_expr, opaque_expr)
        opaque_expr = OpaquePredicate.negate(opaque_expr)
        if is_before:
            return BinaryOp("||", opaque_expr, cond_expr)
        return BinaryOp("||", cond_expr, opaque_expr)

    def test_add_predicate(self, node):
        if node.cond is not None and random.random() < self.probability:
            node.cond = self.generate_opaque_predicate(node.cond)

    def visit_If(self, node):
        self.test_add_predicate(node)
        return self.generic_visit(node)

    def visit_While(self, node):
        self.test_add_predicate(node)
        return self.generic_visit(node)

    def visit_DoWhile(self, node):
        self.test_add_predicate(node)
        return self.generic_visit(node)

    def visit_For(self, node):
        self.test_add_predicate(node)
        return self.generic_visit(node)

    def visit_TernaryOp(self, node):
        self.test_add_predicate(node)
        return self.generic_visit(node)

    def visit_ParamList(self, node):
        if node.params is None:
            return
        for node in node.params:
            if isinstance(node, Decl) and node.name is not None:
                if (
                    node.type is not None
                    and isinstance(node.type, TypeDecl)
                    and node.type.type is not None
                    and node.type.type.names is not None
                ):
                    type_ = " ".join(node.type.type.names)
                    if type_ in OpaquePredicate.VALID_INPUT_TYPES:
                        self.parameters.append((node.name, type_))

    def visit_FuncDef(self, node):
        prev = self.current_function
        self.current_function = node
        self.parameters = []
        self.generic_visit(node)
        self.current_function = prev
        self.parameters = None

    def visit_FileAST(self, node):
        NodeVisitor.generic_visit(self, node)
        self.reset()


class AugmentOpaqueUnit(ObfuscationUnit):
    """Augments exiting conditional statements in the program with opaque predicates,
    obfuscating the true conditional test by introducing invariants on inputs or entropy
    that evaluate to known constants at runtime."""

    name = "Opaque Predicate Augmentation"
    description = "Augments existing conditionals with invariant opaque predicates."
    extended_description = (
        """This transformation augments existing conditional statements (if, if-else, while, do while, for\n"""
        """and ternary operations) by adding an additional opaque predicate check, which is an expression\n"""
        """whose value is always known to be true/false or either, where this cannot be quickly determined\n"""
        """by an attacker attempting to reverse engineer the code. Opaque predicates cannot generally be\n"""
        """optimised out by the compiler and will remain in compiled code.\n\n"""
        """The first available input is the set of input styles that can be used - INPUT refers to the use\n"""
        """of function parameters (i.e. user input) to construct opaque predicates, whereas ENTROPY refers\n"""
        """to the use of global random values to generate these expressions. The second input is the\n"""
        """probability of augmentation. A value of 0.0 means nothing will be augmented, 0.5 means approximately\n"""
        """half will be augmented, and 1.0 means that all will be augmented."""
    )
    type = TransformType.STRUCTURAL

    def __init__(
        self, styles: Iterable[OpaqueAugmenter.Style], probability: float
    ) -> None:
        self.styles = styles
        self.probability = probability
        self.traverser = OpaqueAugmenter(styles, probability)

    def transform(self, source: CSource) -> CSource:
        self.traverser.process(source)
        new_contents = generate_new_contents(source)
        return CSource(source.fpath, new_contents, source.t_unit)

    def edit_cli(self) -> bool:
        styles = AugmentOpaqueUnit.generic_styles(self.styles)
        if styles is None:
            return None
        print(f"The current probability of augmentation is {self.probability}.")
        print("What is the new probability (0.0 <= p <= 1.0) of the augmentation?")
        prob = get_float(0.0, 1.0)
        if prob == float("nan"):
            return None
        self.styles = styles
        self.traverser.styles = styles
        self.probability = prob
        self.traverser.probability = prob
        return True

    def get_cli() -> Optional[
        "AugmentOpaqueUnit"
    ]:  # TODO could also add a NUMBER field???
        styles = AugmentOpaqueUnit.generic_styles([s for s in OpaqueAugmenter.Style])
        if styles is None:
            return None
        print("What is the probability (0.0 <= p <= 1.0) of the augmentation?")
        prob = get_float(0.0, 1.0)
        if prob == float("nan"):
            return None
        return AugmentOpaqueUnit(styles, prob)

    def generic_styles(
        styles: Iterable[OpaqueAugmenter.Style],
    ) -> Optional[Iterable[OpaqueAugmenter.Style]]:
        available = [s for s in OpaqueAugmenter.Style]
        choice = 0
        while choice < len(OpaqueAugmenter.Style) or len(styles) == 0:
            options = [
                ("[X] " if s in styles else "[ ] ") + s.value
                for s in OpaqueAugmenter.Style
            ]
            options.append("Finish selecting styles.")
            prompt = "\nChoose which syles to enable for opaque predicate augmenting, or choose to finish.\n"
            choice = menu_driven_option(options, prompt)
            if choice == -1:
                return None
            elif choice < len(OpaqueAugmenter.Style):
                style = OpaqueAugmenter.Style(available[choice])
                if style in styles:
                    styles.remove(style)
                else:
                    styles.append(style)
            elif len(styles) == 0:
                print(
                    "No valid options are currently selected. Please select at least one option.\n"
                )
        return styles

    def to_json(self) -> str:
        """Converts the opaque augmentation unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps(
            {
                "type": str(__class__.name),
                "styles": [style.name for style in self.styles],
                "probability": self.probability,
            }
        )

    def from_json(json_str: str) -> Optional["AugmentOpaqueUnit"]:
        """Converts the provided JSON string to an opaque augmenting transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding string encoding unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load AugmentOpaqueUnit() - invalid JSON provided.",
                print_err=True,
            )
            return None
        if "type" not in json_obj:
            log(
                "Failed to load AugmentOpaqueUnit() - no type provided.", print_err=True
            )
            return None
        elif json_obj["type"] != __class__.name:
            log(
                "Failed to load AugmentOpaqueUnit() - class/type mismatch.",
                print_err=True,
            )
            return None
        elif "styles" not in json_obj:
            log(
                "Failed to load AugmentOpaqueUnit() - no style values provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["styles"], list):
            log(
                "Failed to load AugmentOpaqueUnit() - styles is not a valid list.",
                print_err=True,
            )
            return None
        styles = []
        style_map = {style.name: style for style in OpaqueAugmenter.Style}
        for style in json_obj["styles"]:
            if not isinstance(style, str):
                log(
                    "Failed to load AugmentOpaqueUnit() - style {} is not a valid string.".format(
                        style
                    ),
                    print_err=True,
                )
                return None
            elif style not in style_map.keys():
                log(
                    "Failed to load AugmentOpaqueUnit() - style {} is not a valid style.".format(
                        style
                    ),
                    print_err=True,
                )
                return None
            styles.append(style_map[style])
        if "probability" not in json_obj:
            log(
                "Failed to load AugmentOpaqueUnit() - no probability value is given.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["probability"], (int, float)):
            log(
                "Failed to load AugmentOpaqueUnit() - probability value is not a valid number.",
                print_err=True,
            )
            return None
        elif json_obj["probability"] < 0 or json_obj["probability"] > 1:
            log(
                "Failed to load AugmentOpaqueUnit() - probability value must be 0 <= p <= 1.",
                print_err=True,
            )
            return None
        return AugmentOpaqueUnit(styles, json_obj["probability"])

    def __str__(self) -> str:
        style_flag = "styles=[" + ", ".join([x.name for x in self.styles]) + "]"
        probability_flag = f"p={self.probability}"
        return f"AugmentOpaqueUnit({style_flag},{probability_flag})"


class BugGenerator(NodeVisitor):
    def visit_Constant(self, node):
        if node.value is not None:
            if node.type is None:
                pass
            elif (
                node.type in ["int", "short", "long", "long long"]
                and int(node.value) != 0
            ):  # TODO better
                node.value = str(int(node.value) + random.choice([-3, -2, -1, 1, 2, 3]))
                if node.value == "0":
                    node.value = str(random.randint(1, 3))
            elif (
                node.type in ["float", "double", "long dobule"]
                and float(node.value) != 0.0
            ):
                node.value = str(float(node.value) + random.random())
            elif node.type == "char":
                node.value = "'" + chr((ord(node.value[0]) + 1) % 256) + "'"
        self.generic_visit(node)

    def visit_BinaryOp(self, node):
        op_map = {
            ">": ("<", "<=", "!=", "=="),
            ">=": ("<", "<=", "!=", "=="),
            "<": (">", ">=", "!=", "=="),
            "<=": (">", ">=", "!=", "=="),
            "+": ("-", "*"),
            "-": ("+", "*"),
            "*": ("+", "-"),
            "==": ("!=", "<", ">"),
            "!=": ("==", "<", ">"),
            "&&": ("||"),
            "||": ("&&"),
        }
        if node.op in op_map and random.random() > 0.4:
            node.op = random.choice(op_map[node.op])
        self.generic_visit(node)


class OpaqueInserter(NodeVisitor):
    class Style(Enum):
        INPUT = "Construct predicates from dynamic user input"
        ENTROPY = "Construct predicates from entropic variables"
        # LINKED_LIST = "Predicates constructed from intractable pointer aliasing on a linked list."
        # TODO above is not implemented yet

    class Granularity(Enum):
        PROCEDURAL = "PROCEDURAL: Predicates are constructed on a whole function-level"
        BLOCK = "BLOCK: Predicates are constructed for random blocks of code (sequential statements)"
        STMT = "STATEMENT: Predictes are constructed for random individual statements"

    class Kind(Enum):
        CHECK = "CHECK: if (true predicate) { YOUR CODE } "
        FALSE = "FALSE: if (false predicate) { buggy code } "
        ELSE = "ELSE: if (false predicate) { buggy code } else { YOUR CODE } "
        EITHER = "EITHER: if (any predicate) { YOUR CODE } else { YOUR CODE } "
        WHILE_FALSE = "WHILE_FALSE: while (false predicate) { buggy code } "
        # TODO could add bug - where bogus/buggy code is generated

    def __init__(
        self,
        styles: Iterable[Style],
        granularities: Iterable[Granularity],
        kinds: Iterable[Kind],
        number: int,  # How many to add per function
    ):
        self.styles = styles
        self.granularities = granularities
        self.kinds = kinds
        self.number = number
        self.bug_generator = BugGenerator()
        self.reset()

    def reset(self):
        self.functions = []
        self.current_function = None
        self.parameters = None
        self.analyzer = None
        self.source = None
        self.entropic_vars = []

    def process(self, source):
        if (
            len(self.styles) == 0
            or len(self.granularities) == 0
            or len(self.kinds) == 0
            or self.number == 0
        ):
            return
        self.analyzer = NewVariableUseAnalyzer(source.t_unit)
        self.analyzer.process()
        self.source = source
        self.visit(source.t_unit)

    def generate_opaque_predicate_cond(self, predicate_sets=None):
        # Retrieve a random opaque predicate and check its parameters
        if predicate_sets is None:
            predicate = random.choice(OpaquePredicate.TRUE_PREDICATES)
        else:
            predicates = set()
            for pset in predicate_sets:
                predicates = predicates.union(set(pset))
            predicate = random.choice(list(predicates))
        num_args = predicate.__code__.co_argcount
        idents = []
        # Iteratively choose variables to use in the predicate
        while len(idents) < num_args:
            styles = [s for s in self.styles]
            # Select a random style for the list of chosen styles to use (if possible)
            valid_style = False
            while not valid_style and len(styles) != 0:
                style = random.choice(styles)
                styles.remove(style)
                if style == self.Style.INPUT:
                    valid_style = (
                        self.parameters is not None
                        and len(set(self.parameters).difference(set(idents))) != 0
                    )  # TODO check logic here just in case
                elif style == self.Style.ENTROPY:
                    valid_style = (  # TODO is there a better way to handle this to avoid rand decls etc.?
                        self.current_function is None
                        or self.current_function.decl is None
                        or self.current_function.decl.name is None
                        or self.current_function.decl.name != "main"
                    )
            if valid_style == False:
                return None  # No variables to use as parameters, so exit out
            if style == self.Style.INPUT:
                # Choose a random function parameter (not used so far) to use
                param = random.choice(self.parameters)
            elif style == self.Style.ENTROPY:
                # Randomly either choose an existing entropic variable or create a new one
                available_vars = list(set(self.entropic_vars).difference(set(idents)))
                use_new_var = len(available_vars) == 0 or random.random() >= 0.75
                if use_new_var:
                    param = OpaquePredicate.generate_entropic_var(
                        self.source, self.analyzer, self.entropic_vars
                    )
                    if param is None:
                        return None
                    self.entropic_vars.append(param)
                    # TODO could add float support in the future for entropic vars?
                else:
                    # Choose a random existing entropic variable to use
                    param = random.choice(available_vars)
            idents.append(param)
        args = []
        for ident in idents:
            if ident[1] not in OpaquePredicate.VALID_REAL_TYPES:
                args.append(ID(ident[0]))
            else:
                args.append(
                    Cast(
                        Typename(
                            None,
                            [],
                            None,
                            TypeDecl(None, [], None, IdentifierType(["int"])),
                        ),
                        ID(ident[0]),
                    )
                )
        return predicate(*args)

    def generate_buggy(self, stmt):
        # TODO better buggy code generation; this is more proof of concept
        return Compound([EmptyStatement()])
        # TODO currently broken - no idea why (comehere)
        # copy = deepcopy(stmt)
        # self.bug_generator.visit(copy)
        # return copy

    def generate_opaque_predicate(self, stmt):
        kind = random.choice(self.kinds)  # TODO do I make this proportional also?
        match kind:
            case self.Kind.CHECK:  # if (true) { your code }
                cond = self.generate_opaque_predicate_cond()
                if cond is None:
                    return None
                return Compound([If(cond, stmt, None)])
            case self.Kind.FALSE:  # if (false) { buggy code }
                cond = self.generate_opaque_predicate_cond()
                if cond is None:
                    return None
                cond = OpaquePredicate.negate(cond)
                buggy = self.generate_buggy(stmt)
                block_items = stmt.block_items if isinstance(stmt, Compound) else [stmt]
                return Compound([If(cond, buggy, None)] + block_items)
            case self.Kind.ELSE:  # if (false) { buggy code } else { YOUR CODE }
                cond = self.generate_opaque_predicate_cond()
                if cond is None:
                    return None
                cond = OpaquePredicate.negate(cond)
                buggy = self.generate_buggy(stmt)
                return Compound([If(cond, buggy, stmt)])
            case self.Kind.EITHER:  # if (either) { YOUR CODE } else { YOUR CODE }
                # TODO maybe add some sort of limit to this one because it doubles your code each time?
                cond = self.generate_opaque_predicate_cond(
                    [OpaquePredicate.EITHER_PREDICATES]
                )
                if cond is None:
                    return None
                copied = deepcopy(stmt)  # TODO is this truly a deep copy? Or no?
                return Compound([If(cond, stmt, copied)])
            case self.Kind.WHILE_FALSE:  # while (false) { buggy code }
                cond = self.generate_opaque_predicate_cond()
                if cond is None:
                    return None
                cond = OpaquePredicate.negate(cond)
                buggy = self.generate_buggy(stmt)
                block_items = stmt.block_items if isinstance(stmt, Compound) else [stmt]
                return Compound([While(cond, buggy)] + block_items)
            case _:
                return None

    def add_procedural_predicate(self, node):
        new_body = self.generate_opaque_predicate(node.body)
        if new_body is not None:
            node.body = new_body
        return True

    def get_random_compound(self, compounds):
        available = [c for c in compounds]
        compound = None
        while len(available) > 0 and compound is None:
            chosen_compound = random.choice(available)
            available.remove(chosen_compound)
            if chosen_compound.block_items is None:
                continue
            has_none_decl = False
            for item in chosen_compound.block_items:
                if not isinstance(item, Decl):
                    has_none_decl = True
                    break
            if has_none_decl:
                compound = chosen_compound
        return compound

    def add_block_predicate(self, compounds):
        # TODO could add a max_depth option to avoid lots of depth for small functions
        # Choose a random compound that has at least one non-decl statement available.
        compound = self.get_random_compound(compounds)
        if compound is None:
            return False  # No way to add a block predicate - Give up
        # Calculate maximal contiguous sequences of non-declarations
        blocks = [(0, len(compound.block_items) - 1)]
        for i, item in enumerate(compound.block_items):
            # TODO still having issues with label for some reason I think?
            if isinstance(item, (Decl, Case, Default, Label)):
                to_remove = []
                to_add = []
                for b in blocks:
                    if i == b[0] and b[0] == b[1]:
                        to_remove.append(b)
                    elif i == b[0]:
                        to_add.append((i + 1, b[1]))
                        to_remove.append(b)
                    elif i == b[1]:
                        to_add.append((b[0], i - 1))
                        to_remove.append(b)
                    elif b[0] < i and i < b[1]:
                        to_add.append((b[0], i - 1))
                        to_add.append((i + 1, b[1]))
                        to_remove.append(b)
                for b in to_remove:
                    blocks.remove(b)
                for b in to_add:
                    blocks.append(b)
        if len(blocks) == 0:
            return False
        # Choose a random 'block' (contiguous sequence) and transfom it
        indexes = random.choice(blocks)
        block = Compound(compound.block_items[indexes[0] : indexes[1] + 1])
        new_block = self.generate_opaque_predicate(block)
        if new_block is not None:
            compound.block_items = (
                compound.block_items[: indexes[0]]
                + new_block.block_items
                + compound.block_items[indexes[1] + 1 :]
            )
        return True

    def add_stmt_predicate(self, compounds):
        # Choose a random compound that has at least one non-decl statement available.
        compound = self.get_random_compound(compounds)
        if compound is None:
            return False  # No way to add a block predicate - Give up
        # Choose a random statement within that compound and transform it
        stmts = [
            (i, s)
            for i, s in enumerate(compound.block_items)
            if not isinstance(s, (Decl, Case, Default, Label))
        ]
        if len(stmts) == 0:
            return False
        index, stmt = random.choice(stmts)
        new_block = self.generate_opaque_predicate(stmt)
        if new_block is not None:
            compound.block_items = (
                compound.block_items[:index]
                + new_block.block_items
                + compound.block_items[index + 1 :]
            )
        return True

    def add_opaque_predicates(self, node):
        # Determine compounds in the function subtree for block/stmt predicate insertion
        compounds = self.analyzer.get_compounds_in_subtree(node.body)
        # TODO is it fine that the above is not updated and maintained?
        # TODO I could calculate it pretty easily every application if needed
        # Determine the proportion of different granularity predicates to add.
        proportions = {
            self.Granularity.PROCEDURAL: 10,
            self.Granularity.BLOCK: 70,
            self.Granularity.STMT: 20,
        }
        amounts = {g: 0 for g in self.Granularity}
        total_prop = sum([proportions[g] for g in self.granularities])
        for g in self.granularities:
            amounts[g] = floor(proportions[g] / total_prop * self.number)
        total_prop = sum(amounts.values())
        while total_prop < self.number:
            granularity = random.choice(self.granularities)
            amounts[granularity] += 1
            total_prop += 1
        for _ in range(amounts[self.Granularity.PROCEDURAL]):
            self.add_procedural_predicate(node)
        for _ in range(amounts[self.Granularity.BLOCK]):
            if not self.add_block_predicate(compounds):
                self.add_procedural_predicate(node)
        for _ in range(amounts[self.Granularity.STMT]):
            if not self.add_stmt_predicate(compounds):
                self.add_procedural_predicate(node)

    def visit_ParamList(self, node):
        if node.params is None:
            return
        for node in node.params:
            if isinstance(node, Decl) and node.name is not None:
                if (
                    node.type is not None
                    and isinstance(node.type, TypeDecl)
                    and node.type.type is not None
                    and node.type.type.names is not None
                ):
                    type_ = " ".join(node.type.type.names)
                    if type_ in OpaquePredicate.VALID_INPUT_TYPES:
                        self.parameters.append((node.name, type_))

    def visit_FuncDef(self, node):
        prev = self.current_function
        self.current_function = node
        self.functions.append(node)
        self.parameters = []
        self.generic_visit(node)
        if node.body is not None:
            self.add_opaque_predicates(node)
        self.current_function = prev
        self.parameters = None

    def visit_FileAST(self, node):
        NodeVisitor.generic_visit(self, node)
        self.reset()


class InsertOpaqueUnit(ObfuscationUnit):
    """Inserts new conditional statements in the program with opaque predicates,
    obfuscating the true control flow of the code by introducing conditional jumps on
    invariants on inputs or entropy that evalute to known constants at runtime."""

    name = "Opaque Predicate Insertion"
    description = "Inserts new conditionals with invariant opaque predicates"
    extended_description = (
        """<html>This transformation inserts new conditional statements that check opaque predicates to the code.\n"""
        """Opaque predicates are an expression whose value is always known to be true/false or either, where\n"""
        """this cannot be quickly determined by an attacker attempting to reverse engineer the code. Opaque\n"""
        """predicates cannot generally be optimised out by the compiler and will remain in compiled code.<br><br>\n\n"""
        """The first available input is the set of styles that can be used - INPUT refers to the use of\n"""
        """function parameters (i.e. user input) to construct opaque predicates, whereas ENTROPY refers\n"""
        """to the use of global random values to generate these expressions. The second input is the\n"""
        """granularity of the optimisations (i.e. code construct size) - PROCEDURAl refers to the whole\n"""
        """function, BLOCK refers to a sequence of statements, and STMT refers to single statements. The\n"""
        """third input is the kinds (type of conditional construct) to use, as follows: <br><br>\n"""
        """ > CHECK:       if (true predicate) { YOUR CODE } <br>\n"""
        """ > FALSE:       if (false predicate) { buggy code } <br>\n"""
        """ > ELSE:        if (false predicate) { buggy code } else { YOUR CODE } <br>\n"""
        """ > EITHER:      if (any predicate) { YOUR CODE } else { YOUR CODE } <br>\n"""
        """ > WHILE_FALSE: while (false predicate) { buggy code } <br><br>\n"""
        """The final input is the number of opaque predicates to insert in your function.<br><br>\n\n"""
        """<b>Warning</b>: "buggy code" generation currently just replicates the real code;\n"""
        """complexity is still increased but note this behaviour when choosing options.<\html>"""
    )
    type = TransformType.STRUCTURAL

    def __init__(
        self,
        styles: Iterable[OpaqueInserter.Style],
        granularities: Iterable[OpaqueInserter.Granularity],
        kinds: Iterable[OpaqueInserter.Kind],
        number: int,
    ) -> None:
        self.styles = styles
        self.granularities = granularities
        self.kinds = kinds
        self.number = number
        self.traverser = OpaqueInserter(styles, granularities, kinds, number)

    def transform(self, source: CSource) -> CSource:
        self.traverser.process(source)
        new_contents = generate_new_contents(source)
        return CSource(source.fpath, new_contents, source.t_unit)

    def edit_cli(self) -> bool:
        styles = InsertOpaqueUnit.generic_styles(self.styles)
        if styles is None:
            return None
        granularities = InsertOpaqueUnit.generic_granularities(self.granularities)
        if granularities is None:
            return None
        kinds = InsertOpaqueUnit.generic_kinds(self.kinds)
        if kinds is None:
            return None
        print(
            f"The current number of opaque predicate insertions per function is {self.number}."
        )
        print(
            "What is the new number (n >= 0) of the opaque predicate insertions? (recommended: 1 <= n <= 10)"
        )
        number = get_int(0, None)
        if number is None:
            return None
        self.styles = styles
        self.traverser.styles = styles
        self.granularities = granularities
        self.traverser.granularities = granularities
        self.kinds = kinds
        self.traverser.kinds = kinds
        self.number = number
        self.traverser.number = number
        return True

    def get_cli() -> Optional["InsertOpaqueUnit"]:
        styles = InsertOpaqueUnit.generic_styles([s for s in OpaqueInserter.Style])
        if styles is None:
            return None
        granularities = InsertOpaqueUnit.generic_granularities(
            [g for g in OpaqueInserter.Granularity]
        )
        if granularities is None:
            return None
        kinds = InsertOpaqueUnit.generic_kinds([k for k in OpaqueInserter.Kind])
        if kinds is None:
            return None
        print(
            "What number (n >= 0) of new opaque predicates should be added per function? (recommended: 1 <= n <= 10)"
        )
        number = get_int(0, None)
        if number is None:
            return None
        return InsertOpaqueUnit(styles, granularities, kinds, number)

    def generic_styles(
        styles: Iterable[OpaqueInserter.Style],
    ) -> Optional[Iterable[OpaqueInserter.Style]]:
        available = [s for s in OpaqueInserter.Style]
        choice = 0
        while choice < len(OpaqueInserter.Style) or len(styles) == 0:
            options = [
                ("[X] " if s in styles else "[ ] ") + s.value
                for s in OpaqueInserter.Style
            ]
            options.append("Finish selecting styles.")
            prompt = "\nChoose which syles to enable for opaque predicate insertion, or choose to finish.\n"
            choice = menu_driven_option(options, prompt)
            if choice == -1:
                return None
            elif choice < len(OpaqueInserter.Style):
                style = OpaqueInserter.Style(available[choice])
                if style in styles:
                    styles.remove(style)
                else:
                    styles.append(style)
            elif len(styles) == 0:
                print(
                    "No valid options are currently selected. Please select at least one option.\n"
                )
        return styles

    def generic_granularities(
        granularities: Iterable[OpaqueInserter.Granularity],
    ) -> Optional[Iterable[OpaqueInserter.Granularity]]:
        available = [g for g in OpaqueInserter.Granularity]
        choice = 0
        while choice < len(OpaqueInserter.Granularity) or len(granularities) == 0:
            options = [
                ("[X] " if g in granularities else "[ ] ") + g.value
                for g in OpaqueInserter.Granularity
            ]
            options.append("Finish selecting granularities.")
            prompt = "\nChoose which granularities to enable for opaque predicate insertion, or choose to finish.\n"
            choice = menu_driven_option(options, prompt)
            if choice == -1:
                return None
            elif choice < len(OpaqueInserter.Granularity):
                granularity = OpaqueInserter.Granularity(available[choice])
                if granularity in granularities:
                    granularities.remove(granularity)
                else:
                    granularities.append(granularity)
            elif len(granularities) == 0:
                print(
                    "No valid options are currently selected. Please select at least one option.\n"
                )
        return granularities

    def generic_kinds(
        kinds: Iterable[OpaqueInserter.Kind],
    ) -> Optional[Iterable[OpaqueInserter.Kind]]:
        available = [k for k in OpaqueInserter.Kind]
        choice = 0
        while choice < len(OpaqueInserter.Kind) or len(kinds) == 0:
            options = [
                ("[X] " if k in kinds else "[ ] ") + k.value
                for k in OpaqueInserter.Kind
            ]
            options.append("Finish selecting kinds.")
            prompt = "\nChoose which kinds to enable for opaque predicate insertion, or choose to finish.\n"
            choice = menu_driven_option(options, prompt)
            if choice == -1:
                return None
            elif choice < len(OpaqueInserter.Kind):
                kind = OpaqueInserter.Kind(available[choice])
                if kind in kinds:
                    kinds.remove(kind)
                else:
                    kinds.append(kind)
            elif len(kinds) == 0:
                print(
                    "No valid options are currently selected. Please select at least one option.\n"
                )
        return kinds

    def to_json(self):
        """Converts the opaque insertion unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps(
            {
                "type": str(__class__.name),
                "styles": [style.name for style in self.styles],
                "granularities": [gran.name for gran in self.granularities],
                "kinds": [kind.name for kind in self.kinds],
                "number": self.number,
            }
        )

    def from_json(json_str: str) -> Optional["InsertOpaqueUnit"]:
        """Converts the provided JSON string to an opaque augmenting transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding string encoding unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load InsertOpaqueUnit() - invalid JSON provided.",
                print_err=True,
            )
            return None
        if "type" not in json_obj:
            log("Failed to load InsertOpaqueUnit() - no type provided.", print_err=True)
            return None
        elif json_obj["type"] != __class__.name:
            log(
                "Failed to load InsertOpaqueUnit() - class/type mismatch.",
                print_err=True,
            )
            return None
        elif "styles" not in json_obj:
            log(
                "Failed to load InsertOpaqueUnit() - no style values provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["styles"], list):
            log(
                "Failed to load InsertOpaqueUnit() - styles is not a valid list.",
                print_err=True,
            )
            return None
        styles = []
        style_map = {style.name: style for style in OpaqueInserter.Style}
        for style in json_obj["styles"]:
            if not isinstance(style, str):
                log(
                    "Failed to load InsertOpaqueUnit() - style {} is not a valid string.".format(
                        style
                    ),
                    print_err=True,
                )
                return None
            elif style not in style_map.keys():
                log(
                    "Failed to load InsertOpaqueUnit() - style {} is not a valid style.".format(
                        style
                    ),
                    print_err=True,
                )
                return None
            styles.append(style_map[style])
        if "granularities" not in json_obj:
            log(
                "Failed to load InsertOpaqueUnit() - no granularity values provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["granularities"], list):
            log(
                "Failed to load InsertOpaqueUnit() - granularities is not a valid list.",
                print_err=True,
            )
            return None
        granularities = []
        granularity_map = {g.name: g for g in OpaqueInserter.Granularity}
        for granularity in json_obj["granularities"]:
            if not isinstance(granularity, str):
                log(
                    "Failed to load InsertOpaqueUnit() - granularity {} is not a valid string.".format(
                        granularity
                    ),
                    print_err=True,
                )
                return None
            elif granularity not in granularity_map.keys():
                log(
                    "Failed to load InsertOpaqueUnit() - granularity {} is not a valid granularity.".format(
                        granularity
                    ),
                    print_err=True,
                )
                return None
            granularities.append(granularity_map[granularity])
        if "kinds" not in json_obj:
            log(
                "Failed to load InsertOpaqueUnit() - no kind (type) values provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["kinds"], list):
            log(
                "Failed to load InsertOpaqueUnit() - kinds is not a valid list.",
                print_err=True,
            )
            return None
        kinds = []
        kinds_map = {kinds.name: kinds for kinds in OpaqueInserter.Kind}
        for kind in json_obj["kinds"]:
            if not isinstance(kind, str):
                log(
                    "Failed to load InsertOpaqueUnit() - kind {} is not a valid string.".format(
                        kind
                    ),
                    print_err=True,
                )
                return None
            elif kind not in kinds_map.keys():
                log(
                    "Failed to load InsertOpaqueUnit() - kind {} is not a valid kind.".format(
                        kind
                    ),
                    print_err=True,
                )
                return None
            kinds.append(kinds_map[kind])
        if "number" not in json_obj:
            log(
                "Failed to load InsertOpaqueUnit() - no number value is given.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["number"], int):
            log(
                "Failed to load InsertOpaqueUnit() - number value is not a valid number.",
                print_err=True,
            )
            return None
        elif json_obj["number"] < 0:
            log(
                "Failed to load InsertOpaqueUnit() - number value must be >= 0.",
                print_err=True,
            )
            return None
        return InsertOpaqueUnit(styles, granularities, kinds, json_obj["number"])

    def __str__(self) -> str:
        style_flag = "styles=[" + ", ".join([x.name for x in self.styles]) + "]"
        granularity_flag = (
            "granularities=[" + ", ".join([x.name for x in self.granularities]) + "]"
        )
        kind_flag = "kinds=[" + ", ".join([x.name for x in self.kinds]) + "]"
        number_flag = f"n={self.number}"
        return f"InsertOpaqueUnit({style_flag},{granularity_flag},{kind_flag},{number_flag})"


# TODO make this work with labels - shouldn't be too bad
class ControlFlowFlattener(NodeVisitor):
    def __init__(self):
        self.reset()

    def reset(self):
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
        self.reset()

    def flatten_function(self, node):
        if node.body is None or len(node.body.block_items) == 0:
            return
        while_label = self.analyzer.get_unique_identifier(
            node, TypeKinds.LABEL, node.body, node
        )
        switch_variable = self.analyzer.get_unique_identifier(
            node, TypeKinds.NONSTRUCTURE, node.body, node
        )
        exit = self.get_unique_number()
        entry = self.get_unique_number()
        self.cases = []
        new_statements = [
            Decl(
                switch_variable,
                None,
                None,
                None,
                None,
                TypeDecl(switch_variable, None, None, IdentifierType(["int"])),
                Constant("int", entry),
                None,
            ),
            Label(
                while_label,
                While(
                    BinaryOp("!=", ID(switch_variable), Constant("int", exit)),
                    Compound([Switch(ID(switch_variable), Compound(self.cases))]),
                ),
            ),
        ]
        self.levels.append((switch_variable, while_label))
        self.transform_block(node.body, entry, exit)
        self.levels = self.levels[:-1]
        node.body.block_items = new_statements

    def transform_block(self, block, entry, exit):
        block_parts = []
        current_seq = []
        if isinstance(
            block, Compound
        ):  # TODO logic here is a bit messy? Can I clean up?
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
        case = Case(
            Constant("int", entry),
            Compound(
                [
                    If(
                        if_stmt.cond,
                        Assignment(
                            "=", ID(switch_variable), Constant("int", then_entry)
                        ),
                        Assignment(
                            "=", ID(switch_variable), Constant("int", else_entry)
                        ),
                    ),
                    Break(),
                ]
            ),
        )
        self.cases.append(case)
        self.transform_block(if_stmt.iftrue, then_entry, exit)
        if if_stmt.iffalse is not None:
            self.transform_block(if_stmt.iffalse, else_entry, exit)

    def transform_while(self, while_stmt, entry, exit):
        switch_variable = self.levels[-1][0]
        body_entry = self.get_unique_number()
        # TODO: Labels?
        case = Case(
            Constant("int", entry),
            Compound(
                [
                    If(
                        while_stmt.cond,
                        Assignment(
                            "=", ID(switch_variable), Constant("int", body_entry)
                        ),
                        Assignment("=", ID(switch_variable), Constant("int", exit)),
                    ),
                    Break(),
                ]
            ),
        )
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
                goto_label = self.analyzer.get_unique_identifier(
                    switch_stmt, TypeKinds.LABEL
                )
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
        case = Case(
            Constant("int", entry),
            Compound(
                [
                    Switch(switch_stmt.cond, Compound(goto_labels)),
                    Assignment("=", ID(switch_variable), Constant("int", exit)),
                    Break(),
                ]
            ),
        )
        self.cases.append(case)
        self.breaks.append((len(self.levels), exit))
        self.transform_block(switch_body, self.get_unique_number(), exit)
        self.breaks = self.breaks[:-1]

    def transform_do_while(self, do_stmt, entry, exit):
        switch_variable = self.levels[-1][0]
        test_entry = self.get_unique_number()
        body_entry = self.get_unique_number()
        # TODO: Labels?
        test_case = Case(
            Constant("int", test_entry),
            Compound(
                [
                    If(
                        do_stmt.cond,
                        Assignment(
                            "=", ID(switch_variable), Constant("int", body_entry)
                        ),
                        Assignment("=", ID(switch_variable), Constant("int", exit)),
                    ),
                    Break(),
                ]
            ),
        )
        self.cases.append(test_case)
        entry_case = Case(
            Constant("int", entry),
            Compound(
                [
                    Assignment("=", ID(switch_variable), Constant("int", body_entry)),
                    Break(),
                ]
            ),
        )
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
        entry_case = Case(
            Constant("int", entry),
            Compound(
                [
                    for_stmt.init,  # TODO what if this is None? Need to deal with this
                    Assignment("=", ID(switch_variable), Constant("int", test_entry)),
                    Break(),
                ]
            ),
        )
        self.cases.append(entry_case)
        test_case = Case(
            Constant("int", test_entry),
            Compound(
                [
                    If(
                        for_stmt.cond,
                        Assignment(
                            "=", ID(switch_variable), Constant("int", body_entry)
                        ),
                        Assignment("=", ID(switch_variable), Constant("int", exit)),
                    ),
                    Break(),
                ]
            ),
        )
        self.cases.append(test_case)
        inc_case = Case(
            Constant("int", inc_entry),
            Compound(
                [
                    for_stmt.next,  # TODO what if this is None? Need to deal with this
                    Assignment("=", ID(switch_variable), Constant("int", test_entry)),
                    Break(),
                ]
            ),
        )
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
                    Assignment(
                        "=",
                        ID(self.levels[self.continues[-1][0] - 1][0]),
                        Constant("int", self.continues[-1][1]),
                    )
                )
                if self.continues[-1][0] != len(self.levels):
                    stmts.append(Goto(self.levels[self.continues[-1][0] - 1][1]))
                else:
                    stmts.append(Break())
            elif isinstance(stmt, Break):
                stmts.append(
                    Assignment(
                        "=",
                        ID(self.levels[self.breaks[-1][0] - 1][0]),
                        Constant("int", self.breaks[-1][1]),
                    )
                )
                if self.breaks[-1][0] != len(self.levels):
                    stmts.append(Goto(self.levels[self.breaks[-1][0] - 1][1]))
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
            if (ident, kind) in self.function_decls or (
                ident,
                kind,
            ) in self.unavailable_idents:  # Renaming required to avoid conflicts
                num = 2
                new_ident = ident
                while (new_ident, kind) in self.function_decls or (
                    new_ident,
                    kind,
                ) in self.unavailable_idents:
                    new_ident = ident + str(num)
                    num += 1
                self.analyzer.change_ident(stmt, ident, kind, new_ident)
                self.function_decls.add((new_ident, kind))
            else:
                self.function_decls.add((ident, kind))
        self.checked_stmts.add(stmt)
        # Create a relevant corresponding declaration at the start of the function
        func_body = self.current_function.body
        decl = Decl(
            node.name,
            node.quals,
            node.align,
            node.storage,
            node.funcspec,
            node.type,
            None,
            node.bitsize,
        )
        self.pending_decls.append(decl)
        # Replace the declaration with a corresponding assignment if appropriate
        if node.init is None:
            assign = None
        elif isinstance(
            node.init, InitList
        ):  # TODO does this fail on multi-dimensional init lists? Check
            assign = []
            for i, expr in enumerate(node.init.exprs):
                assign.append(
                    Assignment(
                        "=", ArrayRef(ID(node.name), Constant("int", str(i))), expr
                    )
                )
        else:
            assign = [Assignment("=", ID(node.name), node.init)]
        if isinstance(self.parent, Compound):
            i = self.parent.block_items.index(node)
            self.parent.block_items = (
                self.parent.block_items[:i]
                + ([] if assign is None else assign)
                + self.parent.block_items[(i + 1) :]
            )
        elif isinstance(self.parent, ExprList):  # DeclList after transformation
            i = self.parent.exprs.index(node)
            self.parent.exprs = (
                self.parent.exprs[:i]
                + ([] if assign is None else assign)
                + self.parent.exprs[(i + 1) :]
            )
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
                self.parent.block_items = (
                    self.parent.block_items[:index]
                    + self.parent.block_items[(index + 1) :]
                )
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
    extended_description = (
        """This transformation "flattens" the control flow of a program - normal programs are a sequential\n"""
        """sequents of code blocks with jumps between them. Control flow flattening separates these blocks,\n"""
        """numbering them all and putting every block inside a switch statement in a while loop. Jumps between\n"""
        """blocks are encoded as a variable change within the loop structure. This completely transforms the\n"""
        """control flow graph representing the program, preventing analysis of the control flow."""
    )
    type = TransformType.STRUCTURAL

    def __init__(self):
        self.traverser = ControlFlowFlattener()

    def transform(self, source: CSource) -> CSource:
        self.traverser.visit(source.t_unit)
        new_contents = generate_new_contents(source)
        return CSource(source.fpath, new_contents, source.t_unit)

    def edit_cli(self) -> bool:  # TODO case number randomisation options
        return True  # TODO

    def get_cli() -> Optional[
        "ControlFlowFlattenUnit"
    ]:  # TODO case number randomisation options
        return ControlFlowFlattenUnit()  # TODO

    def to_json(self):
        """Converts the opaque insertion unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps({"type": str(__class__.name)})

    def from_json(json_str: str) -> Optional["ControlFlowFlattenUnit"]:
        """Converts the provided JSON string to a control flow flattening transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding string encoding unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load FlattenControlFlow() - invalid JSON provided.",
                print_err=True,
            )
            return None
        if "type" not in json_obj:
            log(
                "Failed to load FlattenControlFlow() - no type provided.",
                print_err=True,
            )
            return None
        elif json_obj["type"] != __class__.name:
            log(
                "Failed to load FlattenControlFlow() - class/type mismatch.",
                print_err=True,
            )
            return None
        return ControlFlowFlattenUnit()

    def __str__(self) -> str:
        return "FlattenControlFlow()"


class ClutterWhitespaceUnit(ObfuscationUnit):  # TODO picture extension?
    """Implements simple source-level whitespace cluttering, breaking down the high-level abstraction of
    indentation and program structure by altering whitespace in the file."""

    # TODO WARNING ORDERING - SHOULD COME LAST (BUT BEFORE DiTriGraphEncodeUnit)
    name = "Clutter Whitespace"
    description = "Clutters program whitespace, making it difficult to read"
    extended_description = (
        """This transformation clutters the whitespace of a program, removing all indentation and spacing\n"""
        """where possible between program lexemes. Currently, text is wrapped to fit roughly 100 characters\n"""
        """per line, completely destroying symbolic code readability via whitespace. Note that this only\n"""
        """affects the source code - no change will be made to the compiled code. Note that any non-textual\n"""
        """transformations applied after this point will undo its changes."""
    )
    type = TransformType.LEXICAL

    def __init__(self):
        pass

    def transform(self, source: CSource) -> CSource:
        # Preprocess contents
        new_contents = ""
        for line in source.contents.splitlines():
            if (
                line.strip().startswith("#")
                or line.strip().startswith("%:")
                or line.strip().startswith("??=")
            ):
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
        max_line_length = 100  # TODO max line length option? All on one line? Random?
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
        return CSource(source.fpath, new_contents, source.t_unit)

    def edit_cli(self) -> bool:
        return True

    def get_cli() -> Optional["ClutterWhitespaceUnit"]:
        return ClutterWhitespaceUnit()

    def to_json(self) -> str:
        """Converts the whitespace cluttering unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps({"type": str(__class__.name)})

    def from_json(json_str: str) -> Optional["ClutterWhitespaceUnit"]:
        """Converts the provided JSON string to a whitespace cluttering transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding whitespace cluttering unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load ClutterWhitespace() - invalid JSON provided.",
                print_err=True,
            )
            return None
        if "type" not in json_obj:
            log(
                "Failed to load ClutterWhitespace() - no type provided.", print_err=True
            )
            return None
        elif json_obj["type"] != __class__.name:
            log(
                "Failed to load ClutterWhitespace() - class/type mismatch.",
                print_err=True,
            )
            return None
        return ClutterWhitespaceUnit()

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
    extended_description = (
        """This transformation encodes certain symbols within the program (e.g. '{', '#', ']') as digraphs\n"""
        """or trigraphs, which are respectively two- or three- character combinations that are replaced by\n"""
        """C's preprocessor to allow keyboard with less symbols to type C programs. Note that this only affects\n"""
        """the source code - no change will be made to the compiled code. Note that any non-textual\n"""
        """transformations applied after this point will undo its changes.\n\n"""
        """The first available option is the mapping type - you can choose to encode using only digraphs, only\n"""
        """trigraphs, or a mixture of both digraphs and trigraphs. For the second option, you can choose the\n"""
        """prorbability that an encoding takes place. 0.0 means no encoding, 0.5 means approximately half will\n"""
        """be encoded, and 1.0 means all symbols are encoded. This can be used to achieve a mixture of digraphs,\n"""
        """trigraphs and regular symbols as is desired."""
    )
    type = TransformType.LEXICAL

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
        DIGRAPH = "Digraphs"
        TRIGRAPH = "Trigraphs"
        MIXED = "Mixed Digraph/Trigraphs"

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
            if self.style == self.Style.MIXED and (
                char in self.digraph_map or char in self.trigraph_map
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
        return CSource(source.fpath, new_contents, source.t_unit)

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
            {
                "type": str(__class__.name),
                "style": self.style.name,
                "chance": self.chance,
            }
        )

    def from_json(json_str: str) -> Optional["DiTriGraphEncodeUnit"]:
        """Converts the provided JSON string to a digraph/trigraph encoding transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding digraph/trigraph encoding unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load DiTriGraphEncode() - invalid JSON provided.",
                print_err=True,
            )
            return None
        if "type" not in json_obj:
            log("Failed to load DiTriGraphEncode() - no type provided.", print_err=True)
            return None
        elif json_obj["type"] != __class__.name:
            log(
                "Failed to load DiTriGraphEncode() - class/type mismatch.",
                print_err=True,
            )
            return None
        elif "style" not in json_obj:
            log(
                "Failed to load DiTriGraphEncode() - no style value provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["style"], str):
            log(
                "Failed to load DiTriGraphEncode() - style is not a valid string.",
                print_err=True,
            )
            return None
        elif json_obj["style"] not in [
            style.name for style in DiTriGraphEncodeUnit.Style
        ]:
            log(
                "Failed to load DiTriGraphEncode() - style '{}' is not a valid style.".format(
                    json_obj["style"]
                ),
                print_err=True,
            )
            return None
        elif "chance" not in json_obj:
            log(
                "Failed to load AugmentOpaqueUnit() - no probability value is given.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["chance"], (int, float)):
            log(
                "Failed to load AugmentOpaqueUnit() - probability value is not a valid number.",
                print_err=True,
            )
            return None
        elif json_obj["chance"] < 0 or json_obj["chance"] > 1:
            log(
                "Failed to load AugmentOpaqueUnit() - probability value must be 0 <= p <= 1.",
                print_err=True,
            )
            return None
        return DiTriGraphEncodeUnit(
            {style.name: style for style in DiTriGraphEncodeUnit.Style}[
                json_obj["style"]
            ],
            json_obj["chance"],
        )

    def __str__(self):
        style_flag = f"style={self.style.name}"
        probability_flag = f"p={self.chance}"
        return f"DiTriGraphEncode({style_flag},{probability_flag})"
