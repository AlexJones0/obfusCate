""" File: obfuscation/structural_obfs.py
Implements classes (including obfuscation unit classes) for performing
structural obfuscation transformations, including obfuscation related
to the augmenting of existing conditionals with opaque predicates,
and the insertion of new conditional opaque predicates into the program. 
"""
from .. import utils, interaction, settings as cfg
from ..debug import *
from .utils import (
    ObfuscationUnit,
    TransformType,
    generate_new_contents,
    NewVariableUseAnalyzer,
    TypeKinds,
    ObjectFinder,
)
from pycparser.c_ast import *
from typing import Iterable, Tuple, Optional
import random, json, copy, math, enum


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
        stdlib_init, time_init = utils.is_initialised(source, ["stdlib.h", "time.h"])
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
            [],
            [],
            [],
            [],
            TypeDecl(ident, [], None, IdentifierType(["int"])),
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


# TODO a lot of duplicated code between OpaqueAugmenter and OpaqueInserter
class OpaqueAugmenter(NodeVisitor):
    class Style(enum.Enum):
        INPUT = "Construct predicates from dynamic user input"
        ENTROPY = "Construct predicates from entropic variables"
        # LINKED_LIST = "Predicates constructed from intractable pointer aliasing on a linked list."
        # TODO above is not implemented yet

    def __init__(
        self, styles: Iterable[Style], probability: float = 1.0, number: int = 1
    ) -> None:
        self.styles = styles
        self.probability = probability
        self.number = number
        self.reset()

    def reset(self):
        self.global_typedefs = {}
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
            for _ in range(self.number):
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
        if node.params is None or self.parameters is None:
            return  # No parameters or just parsing a signature.
        for node in node.params:
            # Parsing out the names (and types) of parameter variables
            if not isinstance(node, Decl) or node.name is None:
                continue
            if node.type is None or not isinstance(node.type, TypeDecl):
                continue  # We don't touch pointers!
            if node.type.type is None or not isinstance(node.type.type, IdentifierType):
                continue  # We don't touch structs/unions (we could; but we simplify this)
            if node.type.type.names is None or len(node.type.type.names) == 0:
                continue
            type_ = node.type.type.names[-1]  # TODO is [-1] right?
            if type_ in OpaquePredicate.VALID_INPUT_TYPES:
                self.parameters.append((node.name, type_))
            elif type_ in self.global_typedefs.keys():
                # Handle typedef'd parameters
                if self.global_typedefs[type_] in OpaquePredicate.VALID_INPUT_TYPES:
                    self.parameters.append((node.name, type_))

    def visit_Typedef(self, node: Typedef) -> None:
        # Parse valid global typedefs to find permissible input params
        # as a lot of C programs use custom typedefs to rename
        # common (esp. integer) types.
        if node.name is None or node.type is None or self.current_function is not None:
            return self.generic_visit(node)
        if not isinstance(node.type, TypeDecl) or node.type.type is None:
            return self.generic_visit(node)
        if (
            not isinstance(node.type.type, IdentifierType)
            or node.type.type.names is None
            or len(node.type.type.names) == 0
        ):
            return self.generic_visit(
                node
            )  # Ignore pointer/array types; we don't use them
        typetype = node.type.type.names[-1]
        if typetype in self.global_typedefs.keys():
            # Typedef to a typedef!
            self.global_typedefs[node.name] = self.global_typedefs[typetype]
        else:  # Typedef to some standard C type
            self.global_typedefs[node.name] = typetype
        self.generic_visit(node)

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
        self, styles: Iterable[OpaqueAugmenter.Style], probability: float, number: int
    ) -> None:
        self.styles = styles
        self.probability = probability
        self.number = number
        self.traverser = OpaqueAugmenter(styles, probability, number)

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        self.traverser.process(source)
        new_contents = generate_new_contents(source)
        return interaction.CSource(source.fpath, new_contents, source.t_unit)

    def to_json(self) -> str:
        """Converts the opaque augmentation unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps(
            {
                "type": str(__class__.name),
                "styles": [style.name for style in self.styles],
                "probability": self.probability,
                "number": self.number,
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
        elif "number" not in json_obj:
            log(
                "Failed to load AugmentOpaqueUnit() - no number value is given.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["number"], (int)):
            log(
                "Failed to load AugmentOpaqueUnit() - number value is not a valid integer.",
                print_err=True,
            )
            return None
        elif json_obj["number"] < 0:
            log(
                "Failed to load AugmentOpaqueUnit() - number value must be n >= 0.",
                print_err=True,
            )
            return None
        return AugmentOpaqueUnit(styles, json_obj["probability"], json_obj["number"])

    def __str__(self) -> str:
        style_flag = "styles=[" + ", ".join([x.name for x in self.styles]) + "]"
        probability_flag = f"p={self.probability}"
        number_flag = f"n={self.number}"
        return f"AugmentOpaqueUnit({style_flag},{probability_flag},{number_flag})"


class BugGenerator(NodeVisitor):
    def __init__(self, p_replace_op: float, p_change_constants: float):
        super(BugGenerator, self).__init__()
        self.p_replace_op = p_replace_op
        self.p_change_constants = p_change_constants
        self.reset()

    def reset(self):
        self.in_case = False
        self.changed = False  # Flag to guarantee at least 1 change if possible
        # so we can ensure that the generated statement is buggy (and not just
        # identical by random chance)

    def visit_Constant(self, node):
        if (
            node.value is not None
            and not self.in_case
            and (not self.changed or random.random() < self.p_change_constants)
        ):
            if node.type is None:
                pass
            elif (
                node.type in ["int", "short", "long", "long long"]
                and int(node.value) != 0
            ):
                node.value = str(
                    max(1, int(node.value) + random.choice([-3, -2, -1, 1, 2, 3]))
                )
                self.changed = True
            elif (
                node.type in ["float", "double", "long double"]
                and float(node.value) != 0.0
            ):
                node.value = str(float(node.value) + random.random())
                self.changed = True
            elif node.type == "char":
                node.value = "'" + chr((ord(node.value[0]) + 1) % 256) + "'"
                self.changed = True
        self.generic_visit(node)

    op_map = {  # TODO check these over - can get weird with pointer math sometimes
        ">": ("<", "<=", "!=", "=="),
        ">=": ("<", "<=", "!=", "=="),
        "<": (">", ">=", "!=", "=="),
        "<=": (">", ">=", "!=", "=="),
        "+": ("-"),
        "-": ("+"),
        "*": ("+", "-"),
        "==": ("!=", "<", ">"),
        "!=": ("==", "<", ">"),
        "&&": ("||"),
        "||": ("&&"),
    }

    def visit_BinaryOp(self, node):
        if node.op in self.op_map and (
            not self.changed or random.random() < self.p_replace_op
        ):
            node.op = random.choice(self.op_map[node.op])
            self.changed = True
        self.generic_visit(node)

    def visit_Case(self, node):
        was_in_case = self.in_case
        self.in_case = True
        if node.expr is not None:
            NodeVisitor.generic_visit(self, node)
        self.in_case = was_in_case
        if node.stmts is not None:
            for child in node.stmts:
                NodeVisitor.generic_visit(self, child)


class OpaqueInserter(NodeVisitor):
    class Style(enum.Enum):
        INPUT = "Construct predicates from dynamic user input"
        ENTROPY = "Construct predicates from entropic variables"
        # LINKED_LIST = "Predicates constructed from intractable pointer aliasing on a linked list."
        # TODO above is not implemented yet

    class Granularity(enum.Enum):
        PROCEDURAL = "PROCEDURAL: Predicates are constructed on a whole function-level"
        BLOCK = "BLOCK: Predicates are constructed for random blocks of code (sequential statements)"
        STMT = "STATEMENT: Predictes are constructed for random individual statements"

    class Kind(enum.Enum):
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
        self.bug_generator = BugGenerator(0.5, 0.4)
        self.label_finder = ObjectFinder(Label, ["name"])
        self.reset()

    def reset(self):
        self.functions = []
        self.global_typedefs = {}
        self.current_function = None
        self.parameters = None
        self.analyzer = None
        self.source = None
        self.entropic_vars = []
        self.label_names = set()

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

    def replace_labels(self, node):
        self.label_finder.visit(node)
        for label in self.label_finder.objs:
            new_ident = self.analyzer.get_new_identifier(exclude=self.label_names)
            self.label_names.add(new_ident)
            label.name = new_ident
        self.label_finder.reset()

    def generate_buggy(self, stmt):
        copied = copy.deepcopy(stmt)
        self.bug_generator.visit(copied)
        self.bug_generator.reset()
        self.replace_labels(copied)
        return Compound([copied])

    def generate_opaque_predicate(self, stmt):
        # Work around for pycparser incorrect C generation
        # TODO need to check if this issue occurs anywhere else
        # TODO also check this doesn't break anything
        if not isinstance(stmt, Compound):
            stmt = Compound([stmt])

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
                cond = self.generate_opaque_predicate_cond(
                    [OpaquePredicate.EITHER_PREDICATES]
                )
                if cond is None:
                    return None
                copied = copy.deepcopy(stmt)
                self.replace_labels(copied)
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
            # TODO with new label copying I don't think I need to check the label case any more?
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
        ]  # TODO with new label copying I don't think I need to check the label case any more?
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
            amounts[g] = math.floor(proportions[g] / total_prop * self.number)
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
        if node.params is None or self.parameters is None:
            return  # No parameters or just parsing a signature.
        for node in node.params:
            # Parsing out the names (and types) of parameter variables
            if not isinstance(node, Decl) or node.name is None:
                continue
            if node.type is None or not isinstance(node.type, TypeDecl):
                continue  # We don't touch pointers!
            if node.type.type is None or not isinstance(node.type.type, IdentifierType):
                continue  # We don't touch structs/unions (we could; but we simplify this)
            if node.type.type.names is None or len(node.type.type.names) == 0:
                continue
            type_ = node.type.type.names[-1]  # TODO is [-1] right?
            if type_ in OpaquePredicate.VALID_INPUT_TYPES:
                self.parameters.append((node.name, type_))
            elif type_ in self.global_typedefs.keys():
                # Handle typedef'd parameters
                if self.global_typedefs[type_] in OpaquePredicate.VALID_INPUT_TYPES:
                    self.parameters.append((node.name, type_))

    def visit_Typedef(self, node: Typedef) -> None:
        # Parse valid global typedefs to find permissible input params
        # as a lot of C programs use custom typedefs to rename
        # common (esp. integer) types.
        if node.name is None or node.type is None or self.current_function is not None:
            return self.generic_visit(node)
        if not isinstance(node.type, TypeDecl) or node.type.type is None:
            return self.generic_visit(node)
        if (
            not isinstance(node.type.type, IdentifierType)
            or node.type.type.names is None
            or len(node.type.type.names) == 0
        ):
            return self.generic_visit(
                node
            )  # Ignore pointer/array types; we don't use them
        typetype = node.type.type.names[-1]
        if typetype in self.global_typedefs.keys():
            # Typedef to a typedef!
            self.global_typedefs[node.name] = self.global_typedefs[typetype]
        else:  # Typedef to some standard C type
            self.global_typedefs[node.name] = typetype
        self.generic_visit(node)

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
        """This transformation inserts new conditional statements that check opaque predicates to the code.\n"""
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
        """Warning: "buggy code" generation currently just replicates the real code;\n"""
        """complexity is still increased but note this behaviour when choosing options."""
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

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        self.traverser.process(source)
        new_contents = generate_new_contents(source)
        return interaction.CSource(source.fpath, new_contents, source.t_unit)

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


class ControlFlowFlattener(NodeVisitor):
    class Style(enum.Enum):
        SEQUENTIAL = "Sequential Integers"
        RANDOM_INT = "Random Integers"
        ENUMERATOR = "Random Enum Members"

    def __init__(self, randomise_cases: bool, style):
        self.reset()
        self.randomise_cases = randomise_cases
        self.style = style

    def reset(self):
        self.levels = []
        self.breaks = []
        self.continues = []
        self.cases = []
        self.labels = []
        self.current_function = None
        self.function_decls = None
        self.pending_head = []
        self.frees = []
        self.malloced = False
        self.checked_stmts = None
        self.unavailable_idents = None
        self.numbers = set()
        self.cur_number = 0
        self.parent = None
        self.attr = None
        self.analyzer = None
        self.count = 0

    def transform(self, source: interaction.CSource) -> None:
        self.analyzer = NewVariableUseAnalyzer(source.t_unit)
        self.analyzer.process()
        self.visit(source.t_unit)
        if self.malloced and not utils.is_initialised(source, ["stdlib.h"]):
            # TODO could this break if the user already has functions used in these libraries? uh oh need to state this somewhere
            source.contents = "#include <stdlib.h>\n" + source.contents
        self.reset()

    def get_unique_number(self):
        if self.style == self.Style.SEQUENTIAL:
            num = self.cur_number
            self.cur_number += 1
            return Constant("int", str(num))
        elif self.style == self.Style.RANDOM_INT:
            self.cur_number += 1
            power = int(math.log2(self.cur_number) + 3)
            range_ = 2**power
            num = None
            while num is None or num in self.numbers:
                num = random.randint(-range_, range_ - 1)
            self.numbers.add(num)
            return Constant("int", str(num))
        elif self.style == self.Style.ENUMERATOR:
            exclude_set = self.numbers.union(set(level[0] for level in self.levels))
            # TODO: could use get_new_identifer for the set below instead?
            enum = self.analyzer.get_unique_identifier(
                self.current_function,
                TypeKinds.NONSTRUCTURE,
                function=self.current_function,
                exclude=exclude_set,
            )
            self.numbers.add(enum)
            return ID(enum)

    def __free_at_returns(self, func_body: Compound) -> None:
        # Generate free statements
        free_stmts = [
            FuncCall(ID("free"), ExprList([free_id])) for free_id in self.frees
        ]
        # Find returns in the function body
        return_finder = ObjectFinder(Return, [])
        return_finder.visit(func_body)
        # Add frees before all returns
        for return_node in return_finder.objs:
            parent = return_finder.parents[return_node]
            attr = return_finder.attrs[return_node]
            if isinstance(parent, Compound):
                i = parent.block_items.index(return_node)
                parent.block_items = (
                    parent.block_items[:i] + free_stmts + parent.block_items[i:]
                )
            elif isinstance(parent, (Case, Default)):
                i = parent.stmts.index(return_node)
                parent.stmts = parent.stmts[:i] + free_stmts + parent.stmts[i:]
            elif isinstance(parent, ExprList):
                i = parent.exprs.index(return_node)
                parent.exprs = parent.exprs[:i] + free_stmts + parent.exprs[i:]
            else:
                setattr(parent, attr, Compound(free_stmts + [return_node]))

    def flatten_function(self, node):
        if (
            node.body is None
            or node.body.block_items is None
            or len(node.body.block_items) == 0
        ):
            return
        while_label = self.analyzer.get_unique_identifier(
            node, TypeKinds.LABEL, node.body, node
        )
        self.labels = [while_label]
        switch_variable = self.analyzer.get_unique_identifier(
            node, TypeKinds.NONSTRUCTURE, node.body, node
        )
        self.levels.append((switch_variable, while_label))
        exit = self.get_unique_number()
        entry = self.get_unique_number()
        self.cases = []
        if self.style == self.Style.ENUMERATOR:
            enumerator = self.analyzer.get_unique_identifier(
                node, TypeKinds.STRUCTURE, node.body, node
            )
            new_statements = [
                Decl(
                    None,
                    [],
                    [],
                    [],
                    [],
                    Enum(enumerator, EnumeratorList([])),
                    None,
                    None,
                )
            ]
            switch_var_type = TypeDecl(switch_variable, [], [], Enum(enumerator, None))
        else:
            new_statements = []
            switch_var_type = TypeDecl(switch_variable, [], [], IdentifierType(["int"]))
        new_statements += [
            Decl(
                switch_variable,
                [],
                [],
                [],
                [],
                switch_var_type,
                copy.deepcopy(entry),
                None,
            ),
            Label(
                while_label,
                While(
                    BinaryOp("!=", ID(switch_variable), copy.deepcopy(exit)),
                    Compound([Switch(ID(switch_variable), Compound(self.cases))]),
                ),
            ),
        ]
        self.transform_block(node.body, entry, exit)
        self.levels = self.levels[:-1]
        if self.style == self.Style.ENUMERATOR:
            new_statements[0].type.values.enumerators = [
                Enumerator(enum, None) for enum in self.numbers
            ]
        # Free any mallocs at the end of the function
        for free_id in self.frees:
            new_statements.append(FuncCall(ID("free"), ExprList([free_id])))
        node.body.block_items = new_statements
        self.__free_at_returns(node.body)  # Free any mallocs before each return
        if self.randomise_cases:
            random.shuffle(self.cases)

    def get_labels(self, stmt: Node) -> Tuple[Node, Label | None]:
        label = None
        if isinstance(stmt, Label):
            label = stmt
        while isinstance(stmt, Label):
            stmt = stmt.stmt
        return (stmt, label)

    def get_labelled_stmt(self, label: Label, stmt: Node) -> None:
        if label is None:
            return stmt
        initial_label = label
        label_stmt = label.stmt
        while isinstance(label_stmt, Label):
            label = label_stmt
            label_stmt = label.stmt
        label.stmt = stmt
        return initial_label

    def transform_block(self, block, entry, exit, label=None):
        block_parts = []
        current_seq = []
        if label is None:
            block, label = self.get_labels(block)
        if isinstance(
            block, Compound
        ):  # TODO logic here is a bit messy? Can I clean up?
            for stmt in block.block_items:
                stmt, label = self.get_labels(stmt)
                if isinstance(stmt, (Compound, If, Switch, While, DoWhile, For)):
                    if len(current_seq) != 0:
                        block_parts.append(current_seq)
                        current_seq = []
                    block_parts.append((stmt, label))
                elif isinstance(stmt, Decl):
                    # TODO URGENT TODO Changed 'block' above to 'stmt' - not sure if this broke anything,
                    # might be worth changing back and seeing if anything ever ran this branch before
                    continue
                else:
                    current_seq.append((stmt, label))
            block_parts.append(current_seq)
        elif isinstance(block, Decl):
            return
        elif isinstance(block, (If, Switch, While, DoWhile, For)):
            block_parts.append((block, label))
        else:
            block_parts.append([(block, label)])
        for part in block_parts:
            part_exit = exit if part == block_parts[-1] else self.get_unique_number()
            if isinstance(part, tuple):
                part, label = part
                if isinstance(part, Compound):
                    self.transform_block(part, entry, part_exit, label)
                elif isinstance(part, If):
                    self.transform_if(part, entry, part_exit, label)
                elif isinstance(part, Switch):
                    self.transform_switch(part, entry, part_exit, label)
                elif isinstance(part, While):
                    self.transform_while(part, entry, part_exit, label)
                elif isinstance(part, DoWhile):
                    self.transform_do_while(part, entry, part_exit, label)
                elif isinstance(part, For):
                    self.transform_for(part, entry, part_exit, label)
            elif isinstance(part, list):
                self.transform_sequence(part, entry, part_exit)
            entry = part_exit

    def transform_if(self, if_stmt, entry, exit, label=None):
        switch_variable = self.levels[-1][0]
        then_entry = self.get_unique_number()
        else_entry = self.get_unique_number() if if_stmt.iffalse is not None else exit
        case = Case(
            copy.deepcopy(entry),
            [
                self.get_labelled_stmt(
                    label,
                    If(
                        if_stmt.cond,
                        Assignment("=", ID(switch_variable), copy.deepcopy(then_entry)),
                        Assignment("=", ID(switch_variable), copy.deepcopy(else_entry)),
                    ),
                ),
                Break(),
            ],
        )
        self.cases.append(case)
        self.transform_block(if_stmt.iftrue, then_entry, exit)
        if if_stmt.iffalse is not None:
            self.transform_block(if_stmt.iffalse, else_entry, exit)

    def transform_while(self, while_stmt, entry, exit, label=None):
        switch_variable = self.levels[-1][0]
        body_entry = self.get_unique_number()
        case = Case(
            copy.deepcopy(entry),
            [
                self.get_labelled_stmt(
                    label,
                    If(
                        while_stmt.cond,
                        Assignment("=", ID(switch_variable), copy.deepcopy(body_entry)),
                        Assignment("=", ID(switch_variable), copy.deepcopy(exit)),
                    ),
                ),
                Break(),
            ],
        )
        self.cases.append(case)
        self.breaks.append((len(self.levels), exit))
        self.continues.append((len(self.levels), entry))
        self.transform_block(while_stmt.stmt, body_entry, entry)
        self.breaks = self.breaks[:-1]
        self.continues = self.continues[:-1]

    def transform_switch(self, switch_stmt, entry, exit, label=None):
        # TODO feels like I might be able to do this without labels, i.e.
        # Encode every label section as a block, then just make each block link
        # to the next at the very end? Could work better, but not worth it for now
        switch_variable = self.levels[-1][0]
        switch_body = Compound([])
        goto_labels = []
        goto_label = None
        # TODO the code below is quite messy and probably has some incorrect logic, need to check it
        # TODO can I make this dropdown _without_ using labels to flatten better?
        for stmt in switch_stmt.stmt.block_items:
            if isinstance(stmt, Label):
                labelled_stmt, stmt_label = self.get_labels(stmt)
                if isinstance(labelled_stmt, (Case, Default)):
                    stmt = labelled_stmt
            else:
                stmt_label = None
            if isinstance(stmt, (Case, Default)):
                if goto_label is None:
                    goto_label = self.analyzer.get_unique_identifier(
                        switch_stmt,
                        TypeKinds.LABEL,
                        function=self.current_function,
                        exclude=self.labels,
                    )
                    self.labels.append(goto_label)
                if isinstance(stmt, Case):
                    goto_labels.append(
                        self.get_labelled_stmt(
                            stmt_label, Case(stmt.expr, [Goto(goto_label)])
                        )
                    )
                else:
                    goto_labels.append(
                        self.get_labelled_stmt(stmt_label, Default([Goto(goto_label)]))
                    )
                if stmt.stmts is not None:
                    if isinstance(stmt.stmts, list):
                        if len(stmt.stmts) != 0:
                            switch_body.block_items.append(
                                Label(goto_label, stmt.stmts[0])
                            )
                            switch_body.block_items += stmt.stmts[1:]
                            goto_label = None
                    else:
                        switch_body.block_items.append(Label(goto_label, stmt.stmts))
                        goto_label = None
            else:
                if goto_label is not None:
                    switch_body.block_items.append(Label(goto_label, stmt))
                    goto_label = None
                else:
                    switch_body.block_items.append(stmt)
        if goto_label is not None:  # TODO is this needed?
            switch_body.block_items.append(Label(goto_label, EmptyStatement()))
            goto_label = None
        case = Case(
            copy.deepcopy(entry),
            [
                self.get_labelled_stmt(
                    label, Switch(switch_stmt.cond, Compound(goto_labels))
                ),
                Assignment("=", ID(switch_variable), copy.deepcopy(exit)),
                Break(),
            ],
        )
        self.cases.append(case)
        self.breaks.append((len(self.levels), exit))
        self.transform_block(switch_body, self.get_unique_number(), exit)
        self.breaks = self.breaks[:-1]

    def transform_do_while(self, do_stmt, entry, exit, label=None):
        switch_variable = self.levels[-1][0]
        test_entry = self.get_unique_number()
        body_entry = self.get_unique_number()
        test_case = Case(
            copy.deepcopy(test_entry),
            [
                If(
                    do_stmt.cond,
                    Assignment("=", ID(switch_variable), copy.deepcopy(body_entry)),
                    Assignment("=", ID(switch_variable), copy.deepcopy(exit)),
                ),
                Break(),
            ],
        )
        self.cases.append(test_case)
        entry_case = Case(
            copy.deepcopy(entry),
            [
                self.get_labelled_stmt(
                    label,
                    Assignment("=", ID(switch_variable), copy.deepcopy(body_entry)),
                ),
                Break(),
            ],
        )
        self.cases.append(entry_case)
        self.breaks.append((len(self.levels), exit))
        self.continues.append((len(self.levels), test_entry))
        self.transform_block(do_stmt.stmt, body_entry, test_entry)
        self.breaks = self.breaks[:-1]
        self.continues = self.continues[:-1]

    def transform_for(self, for_stmt, entry, exit, label=None):
        switch_variable = self.levels[-1][0]
        if for_stmt.init is not None:
            test_entry = self.get_unique_number()
            entry_case = Case(
                copy.deepcopy(entry),
                [
                    self.get_labelled_stmt(label, for_stmt.init),
                    Assignment("=", ID(switch_variable), copy.deepcopy(test_entry)),
                    Break(),
                ],
            )
            self.cases.append(entry_case)
        else:
            test_entry = entry
        inc_entry = self.get_unique_number()
        body_entry = self.get_unique_number()
        test_case = Case(
            copy.deepcopy(test_entry),
            [
                If(
                    for_stmt.cond
                    if for_stmt.cond is not None
                    else Constant("int", "1"),
                    Assignment("=", ID(switch_variable), copy.deepcopy(body_entry)),
                    Assignment("=", ID(switch_variable), copy.deepcopy(exit)),
                ),
                Break(),
            ],
        )
        self.cases.append(test_case)
        inc_case = Case(
            copy.deepcopy(inc_entry),
            ([for_stmt.next] if for_stmt.next is not None else [])
            + [
                Assignment("=", ID(switch_variable), copy.deepcopy(test_entry)),
                Break(),
            ],
        )
        self.cases.append(inc_case)
        self.breaks.append((len(self.levels), exit))
        self.continues.append((len(self.levels), inc_entry))
        self.transform_block(for_stmt.stmt, body_entry, inc_entry)
        self.breaks = self.breaks[:-1]
        self.continues = self.continues[:-1]

    def transform_sequence(self, sequence, entry, exit):
        stmts = []
        case = Case(copy.deepcopy(entry), stmts)
        for stmt in sequence:
            stmt, label = stmt
            if isinstance(stmt, Continue):
                stmts.append(
                    self.get_labelled_stmt(
                        label,
                        Assignment(
                            "=",
                            ID(self.levels[self.continues[-1][0] - 1][0]),
                            copy.deepcopy(self.continues[-1][1]),
                        ),
                    )
                )
                if self.continues[-1][0] != len(self.levels):
                    stmts.append(Goto(self.levels[self.continues[-1][0] - 1][1]))
                else:
                    stmts.append(Break())
            elif isinstance(stmt, Break):
                stmts.append(
                    self.get_labelled_stmt(
                        label,
                        Assignment(
                            "=",
                            ID(self.levels[self.breaks[-1][0] - 1][0]),
                            copy.deepcopy(self.breaks[-1][1]),
                        ),
                    )
                )
                if self.breaks[-1][0] != len(self.levels):
                    stmts.append(Goto(self.levels[self.breaks[-1][0] - 1][1]))
                else:
                    stmts.append(Break())
            else:
                stmts.append(self.get_labelled_stmt(label, stmt))
        stmts.append(Assignment("=", ID(self.levels[-1][0]), copy.deepcopy(exit)))
        stmts.append(Break())
        self.cases.append(case)

    def visit_FuncDef(self, node):
        self.current_function = node
        self.function_decls = set()
        self.checked_stmts = set()
        self.pending_head = []
        self.frees = []
        if node.decl.type.args is not None:
            start_stmt = self.analyzer.compound_stmt_map[node.body][0]
        else:
            start_stmt = self.analyzer.get_stmt_from_node(node.body)
        self.unavailable_idents = self.analyzer.get_definitions_at_stmt(start_stmt)
        self.visit(node.body)
        self.flatten_function(node)
        if node.body is not None and node.body.block_items is not None:
            node.body.block_items = self.pending_head + node.body.block_items
        self.function_decls = None
        self.current_function = None
        self.cur_number = 0
        self.numbers = set()

    def visit_Typedef(self, node):
        if self.current_function is None:
            return
        # Retrieve the statement corresponding to the typedef
        stmt = self.analyzer.get_stmt_from_node(node)
        if stmt in self.checked_stmts:
            return self.generic_visit(node)
        # Perform identifier renaming if necessary to avoid typedef clashes
        for ident, kind in list(self.analyzer.get_stmt_definitions(stmt)):
            if (ident, kind) in self.function_decls or (
                ident,
                kind,
            ) in self.unavailable_idents:
                # Renaming required to avoid conflicts
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
        # Create a relevant corresponding typedef at the start of the function
        typedef = Typedef(node.name, node.quals, node.storage, node.type)
        self.pending_head = [typedef] + self.pending_head
        self.generic_visit(node)

    def __get_array_size(self, node: Node) -> list[int] | None:
        """TODO finish this docstring: given a declaration using some array
        with unspecified dimensions,
            e.g. char x[] = 'hello there.';
        This calculates the array's size such that the declaration can
        be moved to the start of the function."""
        # TODO are there any more complex cases I may have to handle?
        if node is None:
            return None
        if isinstance(node, InitList):
            if node.exprs is None:
                return [0]
            cur_dim = len(node.exprs)
            elem_dims = [self.__get_array_size(e) for e in node.exprs]
            if all(x is None for x in elem_dims):
                return [cur_dim]
            # Coalesce None sizes
            elem_dims = [[0] if x is None else x for x in elem_dims]
            # Coalesce shapes to max dimension
            max_dims = max(len(x) for x in elem_dims)
            elem_dims = [x + [0] * (max_dims - len(x)) for x in elem_dims]
            # Find and return max dimension sizes
            return [cur_dim] + [max(col) for col in zip(*elem_dims)]
        elif isinstance(node, CompoundLiteral):
            if node.init is None:
                return None
            return self.__get_array_size(node.init)
        elif isinstance(node, Constant):
            if node.type is None or node.value is None:
                return None
            if node.type == "string":
                return [len(node.value)]
            else:
                return []
        return None

    def __get_array_values(
        self, node: Node, dims: list[int]
    ) -> list[Tuple[Node, list[int]]] | None:
        # TODO docstring
        # TODO NOT currently used - remove if not needed!
        if node is None:
            return None
        if isinstance(node, InitList):
            if node.exprs is None or len(node.exprs) < dims[0]:
                return None
            exprs = node.exprs[: (dims[0] + 1)]
            vals = [
                (i, self.__get_array_values(e, dims[1:])) for i, e in enumerate(exprs)
            ]
            return [(x[0], [i] + x[1]) for i, x in vals if x is not None]
        elif isinstance(node, CompoundLiteral):
            if node.init is None:
                return None
            return self.__get_array_values(node.init, dims)
        elif isinstance(node, Constant):
            if node.type is None or node.value is None:
                return None
            if node.type == "string":
                vals = min(len(node.value), dims[0])
                if vals < dims[0]:
                    return None
                return [(Constant("char", node.value[i]), [i]) for i in range(vals)]
            else:
                return [(node, [])]
        return None

    def __is_variable_expr(self, node: Node) -> bool:
        if node is None:
            return False
        id_finder = ObjectFinder(ID, ["name"])
        id_finder.visit(node)
        return len(id_finder.objs) != 0

    def visit_Decl(self, node):
        # TODO modularise!
        if self.current_function is None:
            return
        # Retrieve the statement corresponding to the declaration
        stmt = self.analyzer.get_stmt_from_node(node)
        if stmt in self.checked_stmts and not isinstance(self.parent, ExprList):
            return self.generic_visit(node)
        # Perform identifier renaming if necessary to avoid variable name clashes
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
        is_variable_expr = self.__is_variable_expr(node.type)
        if (
            node.type is not None
            and isinstance(node.type, ArrayDecl)
            and node.type.dim is None
        ):
            array_dims = self.__get_array_size(node.init)
            node_type = copy.deepcopy(node.type)
            arr_decl = node_type
            for dim in array_dims:
                arr_decl.dim = Constant("int", str(dim))
                arr_decl = arr_decl.type
                if arr_decl is None or not isinstance(arr_decl, ArrayDecl):
                    log(
                        "Unexpected array dimension error: name={} dims={} dim={}".format(
                            node.name, array_dims, dim
                        )
                    )
                    break
        elif is_variable_expr and isinstance(node.type, ArrayDecl):
            # Convert variable-length array to pointer (will be malloced later)
            arr_decl = copy.deepcopy(node.type)
            node_type = PtrDecl(None, None)
            ptr_decl = node_type
            while arr_decl.type is not None and isinstance(arr_decl.type, ArrayDecl):
                # TODO what about arr_decl.quals?
                next_decl = PtrDecl(None, None)
                ptr_decl.type = next_decl
                ptr_decl = next_decl
                arr_decl = arr_decl.type
            ptr_decl.type = arr_decl.type
        else:
            node_type = node.type
        decl = Decl(
            node.name,
            node.quals,
            node.align,
            node.storage,
            node.funcspec,
            node_type,
            None,
            node.bitsize,
        )
        if isinstance(node.init, InitList):
            # TODO does this work with multi-dimensional arrays? Probably not
            decl.type.dim = Constant("int", str(len(node.init.exprs)))
        self.pending_head.append(decl)
        # Replace the declaration with a corresponding assignment if appropriate
        if node.init is None:
            assign = []
        elif isinstance(
            node.init, InitList
        ):  # TODO does this fail on multi-dimensional init lists? Check. Probably.
            # TODO can I use any of the array_dim stuff above for this?
            assign = []
            for i, expr in enumerate(node.init.exprs):
                assign.append(
                    Assignment(
                        "=", ArrayRef(ID(node.name), Constant("int", str(i))), expr
                    )
                )
        elif (
            isinstance(node.init, Constant)
            and node.init.type == "string"
            and node.init.value is not None
        ):
            assign = []
            for i, val in enumerate(node.init.value[1:-1]):
                assign.append(
                    Assignment(
                        "=",
                        ArrayRef(ID(node.name), Constant("int", str(i))),
                        Constant("char", "'{}'".format(val)),
                    )
                )
            assign.append(
                Assignment(
                    "=",
                    ArrayRef(
                        ID(node.name), Constant("int", str(len(node.init.value) - 2))
                    ),
                    Constant("char", "'\\0'"),
                )
            )
        else:
            assign = [Assignment("=", ID(node.name), node.init)]
        if is_variable_expr and isinstance(node.type, ArrayDecl):
            # Parse out element type information and array dimensions
            elem_type = node.type
            while (
                isinstance(elem_type, (PtrDecl, ArrayDecl))
                and elem_type.type is not None
            ):
                elem_type = elem_type.type
            if node.type.dim is None:
                array_dims = self.__get_array_size(node.init)
                if array_dims is None:
                    arr_size = Constant("int", str(arr_size))
                else:
                    arr_size = Constant("int", str(math.prod(array_dims)))
            else:
                arr_size = node.type.dim
            # Create a malloc for the Variable Length Array (VLA)
            assign = [
                Assignment(
                    "=",
                    ID(node.name),
                    FuncCall(
                        ID("alloca" if cfg.USE_ALLOCA else "malloc"),
                        ExprList(
                            [
                                BinaryOp(
                                    "*",
                                    UnaryOp("sizeof", elem_type),
                                    arr_size,
                                )
                            ]
                        ),
                    ),
                )
            ] + assign
            ### TODO TODO TODO: NOT CURRENTLY MULTIDIMENSIONAL ARRAY STUFF? IS THIS NEEDED?
            if not cfg.USE_ALLOCA:
                self.frees.append(ID(node.name))
            self.malloced = True
        # I do this in frees before returning as well - just make utility functions for inserting
        # a node before/after/replacing a given node to cut down on repeated code?
        if isinstance(self.parent, Compound):
            i = self.parent.block_items.index(node)
            self.parent.block_items = (
                self.parent.block_items[:i]
                + assign
                + self.parent.block_items[(i + 1) :]
            )
        elif isinstance(self.parent, (Case, Default)):
            i = self.parent.stmts.index(node)
            self.parent.stmts = self.parent.stmts[:i] + assign + self.parent.stmts[i:]
        elif isinstance(self.parent, ExprList):  # DeclList after transformation
            i = self.parent.exprs.index(node)
            self.parent.exprs = (
                self.parent.exprs[:i] + assign + self.parent.exprs[(i + 1) :]
            )
        elif len(assign) == 1:
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
        """control flow graph representing the program, preventing analysis of the control flow.\n\n"""
        """WARNING: Due to limitations of pycparser, this currently does not work with labelled case statements, e.g.\n"""
        """switch (x) {\n"""
        """    abc: case 1: do_stuff(); break;\n"""
        """}\n\n"""
        """WARNING: Currently requires to translate variable length arrays (VLAs) to MALLOCs (stored on heap\n"""
        """instead of stack) - make note of this for memory allocation! """
    )  # TODO talk about this limitation of pycparser in my report - downside to switching / Open source!
    type = TransformType.STRUCTURAL

    def __init__(self, randomise_cases: bool, style: ControlFlowFlattener.Style):
        self.randomise_cases = randomise_cases
        self.style = style
        self.traverser = ControlFlowFlattener(randomise_cases, style)

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        self.traverser.transform(source)
        new_contents = generate_new_contents(source)
        return interaction.CSource(source.fpath, new_contents, source.t_unit)

    def to_json(self):
        """Converts the opaque insertion unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps(
            {
                "type": str(__class__.name),
                "randomise_cases": self.randomise_cases,
                "style": self.style.name,
            }
        )

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
        elif "randomise_cases" not in json_obj:
            log(
                "Failed to load FlattenControlFlow() - no case randomisation flag value provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["randomise_cases"], bool):
            log(
                "Failed to load FlattenControlFlow() - case randomisation flag value is not a Boolean.",
                print_err=True,
            )
            return None
        elif "style" not in json_obj:
            log(
                "Failed to load FlattenControlFlow() - no style value provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["style"], str):
            log(
                "Failed to load FlattenControlFlow() - style is not a valid string.",
                print_err=True,
            )
            return None
        elif json_obj["style"] not in [
            style.name for style in ControlFlowFlattener.Style
        ]:
            log(
                "Failed to load FlattenControlFlow() - style '{}' is not a valid style.".format(
                    json_obj["style"]
                ),
                print_err=True,
            )
            return None
        return ControlFlowFlattenUnit(
            json_obj["randomise_cases"],
            {style.name: style for style in ControlFlowFlattener.Style}[
                json_obj["style"]
            ],
        )

    def __str__(self) -> str:
        randomise_flag = (
            f"random_order={'ENABLED' if self.randomise_cases else 'DISABLED'}"
        )
        style_flag = f"style={self.style.name}"
        return f"FlattenControlFlow({randomise_flag},{style_flag})"
