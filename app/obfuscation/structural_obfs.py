""" File: obfuscation/structural_obfs.py
Implements classes (including obfuscation unit classes) for performing
structural obfuscation transformations, including obfuscation related
to the augmenting of existing conditionals with opaque predicates,
and the insertion of new conditional opaque predicates into the program. 
"""
from .. import utils, interaction, settings as cfg
from ..debug import *
from .utils import *
from .identifier_analysis import IdentifierAnalyzer
from pycparser.c_ast import *
from typing import Iterable, Tuple, Optional
import random, json, copy, math, enum


Conditional = If | While | DoWhile | For | TernaryOp


class OpaquePredicate:
    """A namespace class encapsulating various constants and functions used for opaque predicate
    obfuscation methods, which are predicates (conditional expressions) whose value is known during
    obfuscation but that is hard to quickly determine at de-obfuscation time."""

    VALID_INPUT_TYPES = VALID_INT_TYPES + VALID_REAL_TYPES

    # A list of number-theoretic predicates that are known to always be true.
    TRUE_PREDICATES = [
        # (x * x) >= 0
        lambda x: BinaryOp(
            "||",
            BinaryOp(
                "||",
                BinaryOp(">", copy.deepcopy(x), Constant("int", "46340")),
                BinaryOp("<", copy.deepcopy(x), Constant("int", "-46340")),
            ),
            BinaryOp(
                ">=",
                BinaryOp("*", copy.deepcopy(x), copy.deepcopy(x)),
                Constant("int", "0"),
            ),
        ),
        # (x * -x) <= 0
        lambda x: BinaryOp(
            "||",
            BinaryOp(
                "||",
                BinaryOp(">", copy.deepcopy(x), Constant("int", "23170")),
                BinaryOp("<", copy.deepcopy(x), Constant("int", "-23170")),
            ),
            BinaryOp(
                "<=",
                BinaryOp("*", copy.deepcopy(x), UnaryOp("-", copy.deepcopy(x))),
                Constant("int", "0"),
            ),
        ),
        # (7 * (y * y)) != ((x * x) + 1)
        lambda x, y: BinaryOp(
            "||",
            BinaryOp(
                "||",
                BinaryOp(
                    "||",
                    BinaryOp(">", copy.deepcopy(y), Constant("int", "6620")),
                    BinaryOp("<", copy.deepcopy(y), Constant("int", "-6620")),
                ),
                BinaryOp(
                    "||",
                    BinaryOp(">", copy.deepcopy(x), Constant("int", "46339")),
                    BinaryOp("<", copy.deepcopy(x), Constant("int", "-46339")),
                ),
            ),
            BinaryOp(
                "!=",
                BinaryOp(
                    "*",
                    Constant("int", "7"),
                    BinaryOp("*", copy.deepcopy(y), copy.deepcopy(y)),
                ),
                BinaryOp(
                    "+",
                    BinaryOp("*", copy.deepcopy(x), copy.deepcopy(x)),
                    Constant("int", "1"),
                ),
            ),
        ),
        # ((7 * (y * y)) - 1) != (x * x)
        lambda x, y: BinaryOp(
            "||",
            BinaryOp(
                "||",
                BinaryOp(
                    "||",
                    BinaryOp(">", copy.deepcopy(y), Constant("int", "6620")),
                    BinaryOp("<", copy.deepcopy(y), Constant("int", "-6620")),
                ),
                BinaryOp(
                    "||",
                    BinaryOp(">", copy.deepcopy(x), Constant("int", "46339")),
                    BinaryOp("<", copy.deepcopy(x), Constant("Int", "-46339")),
                ),
            ),
            BinaryOp(
                "!=",
                BinaryOp(
                    "-",
                    BinaryOp(
                        "*",
                        Constant("int", "7"),
                        BinaryOp("*", copy.deepcopy(y), copy.deepcopy(y)),
                    ),
                    Constant("int", "1"),
                ),
                BinaryOp("*", copy.deepcopy(x), copy.deepcopy(x)),
            ),
        ),
        # ((x * (x + 1)) % 2) == 0
        lambda x: BinaryOp(
            "||",
            BinaryOp(
                "||",
                BinaryOp(">", copy.deepcopy(x), Constant("int", "46339")),
                BinaryOp("<", copy.deepcopy(x), Constant("int", "-46339")),
            ),
            BinaryOp(
                "==",
                BinaryOp(
                    "%",
                    BinaryOp(
                        "*",
                        copy.deepcopy(x),
                        BinaryOp("+", copy.deepcopy(x), Constant("int", "1")),
                    ),
                    Constant("int", "2"),
                ),
                Constant("int", "0"),
            ),
        ),
        # ((x * (1 + x)) % 2) != 1
        lambda x: BinaryOp(
            "||",
            BinaryOp(
                "||",
                BinaryOp(">", copy.deepcopy(x), Constant("int", "46339")),
                BinaryOp("<", copy.deepcopy(x), Constant("int", "-46339")),
            ),
            BinaryOp(
                "!=",
                BinaryOp(
                    "%",
                    BinaryOp(
                        "*",
                        copy.deepcopy(x),
                        BinaryOp("+", Constant("int", "1"), copy.deepcopy(x)),
                    ),
                    Constant("int", "2"),
                ),
                Constant("int", "1"),
            ),
        ),
        # ((x * ((x + 1) * (x + 2))) % 3) == 0
        lambda x: BinaryOp(
            "||",
            BinaryOp(
                "||",
                BinaryOp(">", copy.deepcopy(x), Constant("int", "1280")),
                BinaryOp("<", copy.deepcopy(x), Constant("int", "-1280")),
            ),
            BinaryOp(
                "==",
                BinaryOp(
                    "%",
                    BinaryOp(
                        "*",
                        copy.deepcopy(x),
                        BinaryOp(
                            "*",
                            BinaryOp("+", copy.deepcopy(x), Constant("int", "1")),
                            BinaryOp("+", copy.deepcopy(x), Constant("int", "2")),
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
            BinaryOp(
                "||",
                BinaryOp(">", copy.deepcopy(x), Constant("int", "1200")),
                BinaryOp("<", copy.deepcopy(x), Constant("int", "-1200")),
            ),
            BinaryOp(
                "!=",
                BinaryOp(
                    "%",
                    BinaryOp(
                        "*",
                        BinaryOp("+", copy.deepcopy(x), Constant("int", "1")),
                        BinaryOp(
                            "*",
                            copy.deepcopy(x),
                            BinaryOp("+", copy.deepcopy(x), Constant("int", "2")),
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
            BinaryOp(
                "||",
                BinaryOp(">", copy.deepcopy(x), Constant("int", "1200")),
                BinaryOp("<", copy.deepcopy(x), Constant("int", "-1200")),
            ),
            BinaryOp(
                "!=",
                BinaryOp(
                    "%",
                    BinaryOp(
                        "*",
                        BinaryOp("+", copy.deepcopy(x), Constant("int", "2")),
                        BinaryOp(
                            "*",
                            BinaryOp("+", copy.deepcopy(x), Constant("int", "1")),
                            copy.deepcopy(x),
                        ),
                    ),
                    Constant("int", "3"),
                ),
                Constant("int", "2"),
            ),
        ),
        # (((7 * x) * x) + 1) % 7) != 0
        lambda x: BinaryOp(
            "||",
            BinaryOp(
                "||",
                BinaryOp(">", copy.deepcopy(x), Constant("int", "6620")),
                BinaryOp("<", copy.deepcopy(x), Constant("int", "-6620")),
            ),
            BinaryOp(
                "!=",
                BinaryOp(
                    "%",
                    BinaryOp(
                        "+",
                        BinaryOp(
                            "*",
                            BinaryOp("*", Constant("int", "7"), copy.deepcopy(x)),
                            copy.deepcopy(x),
                        ),
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
            BinaryOp(
                "||",
                BinaryOp(">", copy.deepcopy(x), Constant("int", "46000")),
                BinaryOp("<", copy.deepcopy(x), Constant("int", "-46000")),
            ),
            BinaryOp(
                "!=",
                BinaryOp(
                    "%",
                    BinaryOp(
                        "+",
                        BinaryOp(
                            "+",
                            BinaryOp("*", copy.deepcopy(x), copy.deepcopy(x)),
                            copy.deepcopy(x),
                        ),
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
            BinaryOp(
                "||",
                BinaryOp(">", copy.deepcopy(x), Constant("int", "46000")),
                BinaryOp("<", copy.deepcopy(x), Constant("int", "-46000")),
            ),
            BinaryOp(
                "!=",
                BinaryOp(
                    "%",
                    BinaryOp(
                        "+",
                        BinaryOp(
                            "*",
                            BinaryOp("+", copy.deepcopy(x), Constant("int", "1")),
                            copy.deepcopy(x),
                        ),
                        Constant("int", "7"),
                    ),
                    Constant("int", "81"),
                ),
                Constant("int", "0"),
            ),
        ),
    ]

    COMPARISON_OPS = [">", ">=", "<", "<=", "==", "!="]
    BIN_ARITHMETIC_OPS = ["+", "-", "*"]
    BIN_DIV_OPS = ["/", "%"]

    # A list of functions for generating predicates that may either be true or false (either predicates)
    EITHER_PREDICATES = [
        # x
        lambda x: copy.deepcopy(x),
        # !x
        lambda x: UnaryOp("!", copy.deepcopy(x)),
        # x <op> 0 for some operation <op>
        lambda x: BinaryOp(
            random.choice(OpaquePredicate.COMPARISON_OPS),
            copy.deepcopy(x),
            Constant("int", "0"),
        ),
        # x <op> c for some constant c and operation <op>
        lambda x: BinaryOp(
            random.choice(OpaquePredicate.COMPARISON_OPS),
            copy.deepcopy(x),
            Constant("int", str(random.randint(-25, 25))),
        ),
        # x <op> y for some operation <op>
        lambda x, y: BinaryOp(
            random.choice(OpaquePredicate.COMPARISON_OPS),
            copy.deepcopy(x),
            copy.deepcopy(y),
        ),
        # x <op1> y && y <op2> z for some comparsion operations <op1> and <op2>
        lambda x, y, z: BinaryOp(
            random.choice(["&&", "||"]),
            BinaryOp(
                random.choice(OpaquePredicate.COMPARISON_OPS),
                copy.deepcopy(x),
                copy.deepcopy(y),
            ),
            BinaryOp(
                random.choice(OpaquePredicate.COMPARISON_OPS),
                copy.deepcopy(y),
                copy.deepcopy(z),
            ),
        ),
        # x <op1> y <op2> z for some arithmetic operation <op1> and some comparison operation <op2>
        lambda x, y, z: BinaryOp(
            random.choice(OpaquePredicate.COMPARISON_OPS),
            BinaryOp(
                random.choice(OpaquePredicate.BIN_ARITHMETIC_OPS),
                copy.deepcopy(x),
                copy.deepcopy(y),
            ),
            copy.deepcopy(z),
        ),
        # y == 0 || x <op1> y <op2> z for some division operation <op1> and some comparison operation <op2>
        lambda x, y, z: BinaryOp(
            "||",
            BinaryOp("==", copy.deepcopy(y), Constant("int", "0")),
            BinaryOp(
                random.choice(OpaquePredicate.COMPARISON_OPS),
                BinaryOp(
                    random.choice(OpaquePredicate.BIN_DIV_OPS),
                    copy.deepcopy(x),
                    copy.deepcopy(y),
                ),
                copy.deepcopy(z),
            ),
        ),
    ]

    # Map from comparison operators to their negated operators
    negation_map = {">": "<=", "<": ">=", ">=": "<", "<=": ">", "==": "!=", "!=": "=="}

    def negate(expr: Node) -> Node:
        """Given an AST node of some opaque predicate expression subtree, this function
        negates the predicate. For example, if the predicate was always true, it will now be
        always false. This is done by application of de Morgan's law and flipping of operators
        in a recursive definition.

        Args:
            expr (Node): The AST node of some expression subtree to negate

        Returns:
            Node: The negated AST subtree (root node).
        """
        if isinstance(expr, BinaryOp):
            if expr.op in OpaquePredicate.negation_map.keys():
                expr.op = OpaquePredicate.negation_map[expr.op]
                return expr
            elif expr.op == "&&":  # De Morgan's Law AND form
                expr.op = "||"
                expr.left = OpaquePredicate.negate(expr.left)
                expr.right = OpaquePredicate.negate(expr.right)
                return expr
            elif expr.op == "||":  # De Morgan's Law OR form
                expr.op = "&&"
                expr.left = OpaquePredicate.negate(expr.left)
                expr.right = OpaquePredicate.negate(expr.right)
                return expr
        return UnaryOp("!", expr)

    def get_main_func(source: interaction.CSource) -> FuncDef | None:
        """Given a source C program, this function will find and retrieve
        the body of the main function where such a function exists.

        Args:
            source (interaction.CSource): The source C program to search in

        Returns:
            FuncDef | None: The FuncDef node of the main function if it exists,
            or None if no valid main function exists.
        """
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
        return main[0]

    def is_srand_init(source: interaction.CSource, main: FuncDef) -> bool | None:
        """Given a source C program, this function will determine whether
        the srand function (random seed / source) has been initialised to use
        the current time value, such that the `rand()` function can reliably be used
        within the program for random number generation.

        Args:
            source (interaction.CSource): The source C program to check
            main (FuncDef): The main function body

        Returns:
            bool | None: True if it is initialised. False if not. None if the
            program AST is invalid.
        """
        if main.body is None or main.body.block_items is None:
            return None
        for stmt in main.body.block_items:
            if isinstance(stmt, FuncCall) and stmt.name is not None:
                if isinstance(stmt.name, ID) and stmt.name.name == "srand":
                    return True
        return False

    def init_srand(main: FuncDef) -> None:
        """Given the FuncDef AST node corresponding to the main function definition,
        this function initialised srand (with a current time pointer) such that
        randomness can be used throughout the program with rand().

        Args:
            main (FuncDef): The AST node of the main function definition.
        """
        time_argtype = Typename(
            None,
            [],
            None,
            PtrDecl([], TypeDecl(None, [], None, IdentifierType(["void"]))),
        )
        time_funccall = FuncCall(
            ID("time"), ExprList([Cast(time_argtype, Constant("int", "0"))])
        )
        srand_call = FuncCall(
            ID("srand"),
            ExprList([time_funccall]),
        )
        main.body.block_items = [srand_call] + main.body.block_items

    def generate_entropic_var(
        source: interaction.CSource,
        analyzer: IdentifierAnalyzer,
        existing_vars: Iterable[str],
    ) -> Tuple[str, str]:
        """Given a source program, an identifier usage analyzer that has run on that program, and a list
        of the names of existing (already generated) entropic variables to avoid, this function will
        generate a new entropic (randomised) variable and add it to the program body. This includes
        defining it globally and initialising it with a random value at the start of the main function.

        Args:
            source (interaction.CSource): The source C program to add a variable to.
            analyzer (IdentifierAnalyzer): The analyzer that has run on the source program.
            existing_vars (Iterable[str]): The list of existing entropic variable names to avoid.

        Returns:
            Tuple[str, str]: A tuple (ident, "int") where ident is the new name, as all
            random variables are of an integer type by default.
        """
        # First determine if stdlib.h and time.h are included
        stdlib_init, time_init = utils.is_initialised(source, ["stdlib.h", "time.h"])
        # Next determine if srand has been initialised in main
        main = OpaquePredicate.get_main_func(source)
        if main is None:
            return None
        srand_init = OpaquePredicate.is_srand_init(source, main)
        if srand_init is None:
            return None

        # Initialise stdlib.h/time.h/srand where necessary
        if not stdlib_init:
            source.contents = "#include <stdlib.h>\n" + source.contents
        if not time_init:
            source.contents = "#include <time.h>\n" + source.contents
        if not srand_init:
            OpaquePredicate.init_srand(main)

        # Generate a new global entropic variable
        ident = analyzer.get_unique_identifier([v[0] for v in existing_vars])
        typedecl = TypeDecl(ident, [], None, IdentifierType(["int"]))
        ident_decl = Decl(ident, [], [], [], [], typedecl, None, None)
        source.t_unit.ext = [ident_decl] + source.t_unit.ext
        assignment = Assignment("=", ID(ident), FuncCall(ID("rand"), None))
        for i, stmt in enumerate(main.body.block_items):
            if isinstance(stmt, FuncCall) and stmt.name is not None:
                if isinstance(stmt.name, ID) and stmt.name.name == "srand":
                    # Ensure the variable is created just after srand is set.
                    main.body.block_items = (
                        main.body.block_items[: (i + 1)]
                        + [assignment]
                        + main.body.block_items[(i + 1) :]
                    )
                    break

        return (ident, "int")

    def get_opaque_predicate_args(
        object_: NodeVisitor,
        predicate: Callable,
        parameters: list[Tuple[str, str]],
        allow_main: bool,
    ) -> list[ID | Cast] | None:
        """Based on the traverser's settings, this method selects a list of arguments
        (operands) to use in the creation of an opaque predicate. These are selected
        according to the selected predicate styles, as well as the existing program
        state.

        Args:
            object_ (NodeVisitor): The NodeVisitor subclass implementing either opaque
            predicate insertion or augmentation. Must define a Style enum.
            predicate (function): A function that will take argument nodes to output
            an opaque predicate subtree.
            parameters (list[Tuple[str, str]]): A list of (unshadowed) parameters defined
            by the current function. Parameters are of the form (name, type).
            allow_main (bool): Whether to allow entropic variable operands in opaque predicates
            in the main function. Yes for augmentation; no for insertion.

        Returns:
            list[ID | Cast] | None: Returns the list of argument nodes/subtrees to be used
            to create the opaque predicate. These are either identifiers (directly), or casted
            values of identifiers (to make them the right type). Returns None if the current
            context and settings makes it impossible to fulfill the needed arguments.
        """
        num_args = predicate.__code__.co_argcount
        idents = []
        # Iteratively fill the number of required arguments
        while len(idents) < num_args:
            styles = [s for s in object_.styles]

            # Select a random style from the list of chosen styles to use (if possible)
            valid_style = False
            while not valid_style and len(styles) != 0:
                style = random.choice(styles)
                styles.remove(style)
                if style == object_.Style.INPUT:
                    valid_style = (
                        parameters is not None
                        and len(set(parameters).difference(set(idents))) != 0
                    )
                elif style == object_.Style.ENTROPY:
                    valid_style = (
                        allow_main
                        or object_.current_function is None
                        or object_.current_function.decl is None
                        or object_.current_function.decl.name is None
                        or object_.current_function.decl.name != "main"
                    )
            if valid_style == False:
                return None

            if style == object_.Style.INPUT:
                # Choose a random function parameter (not used so far) to use
                param = random.choice(parameters)
            elif style == object_.Style.ENTROPY:
                # Randomly either choose an existing entropic variable or create a new one
                available_vars = list(
                    set(object_.entropic_vars).difference(set(idents))
                )
                use_new_var = len(available_vars) == 0 or random.random() >= 0.5
                if use_new_var:
                    # Generate a new entropic variable
                    param = OpaquePredicate.generate_entropic_var(
                        object_.source, object_.analyzer, object_.entropic_vars
                    )
                    if param is None:
                        return None
                    object_.entropic_vars.append(param)
                else:
                    # Choose a random existing entropic variable to use
                    param = random.choice(available_vars)
            idents.append(param)

        # Create identifier nodes or casted identifiers based on the type of the
        # identifiers used.
        args = []
        for ident in idents:
            if ident[1] not in VALID_REAL_TYPES:
                args.append(ID(ident[0]))
            else:
                cast_type = TypeDecl(None, [], None, IdentifierType(["int"]))
                typename = Typename(None, [], None, cast_type)
                args.append(Cast(typename, ID(ident[0])))
        return args


class OpaqueAugmenter(NodeVisitor):
    """This class directly performs the opaque augmentation obfuscation method by traversing and
    mutating a given program AST, generating new opaque predicates to augment existing conditionals
    in the code."""

    class Style(enum.Enum):
        """An enumerated type representing currently supported opaque predicate generation styles."""

        INPUT = "Construct predicates from dynamic user input"
        ENTROPY = "Construct predicates from entropic variables"

    def __init__(
        self, styles: Iterable[Style], probability: float = 1.0, number: int = 1
    ):
        """The constructor for the OpaqueAugmenter class, storing input options
        and initialising the object.

        Args:
            styles (Iterable[Style]): The collection of possible opaque predicate
            parameter styles to use.
            probability (float, optional): The independent probability with which
            to augment conditionals. Defaults to 1.0.
            number (int, optional): The number of opaque predicates to augment
            each conditional with. Defaults to 1.
        """
        self.styles = styles
        self.probability = probability
        self.number = number
        self._reset()

    def _reset(self) -> None:
        """Resets the OpaqueAugmenter's state (tracking variables), allowing
        it to perform obfuscation for a new program."""
        self.global_typedefs = {}
        self.current_function = None
        self.parameters = None
        self.analyzer = None
        self.source = None
        self.entropic_vars = []

    def process(self, source: interaction.CSource) -> None:
        """Processes a source C program, first performing identifier usage analysis on it,
        and then adding traversing (and mutating) the AST.

        Args:
            source (interaction.CSource): The source C program to obfuscate.
        """
        if len(self.styles) == 0:
            return
        self.analyzer = IdentifierAnalyzer(source)
        self.analyzer.process()
        self.source = source
        self.visit(source.t_unit)

    def _get_unshadowed_parameters(self, ast_node: Node) -> list[Tuple[str, str]]:
        """Retrieves a list of parameters for the function that the source_ancestor node
        is contained within, but only including the parameters that have not since been
        shadowed by another variable definition.

        Args:
            ast_node (Node): The AST node from which to retrieve parameters.

        Returns:
            list[Tuple[str,str]]: A list of parameters not shadowed at the current
            point in the program. Parameters are describes as (name, type).
        """
        parameters = []
        for param in self.parameters:
            def_node = self.analyzer.get_last_ident_definition(
                ast_node, (param[0], NameSpace.ORDINARY)
            )
            if isinstance(def_node, ParamList):
                # Only non-redefined (non-shadowed) parameters
                parameters.append(param)
        return parameters

    def generate_opaque_predicate(self, cond_expr: Node, source_ancestor: Node) -> Node:
        """Generates a tautological opaque predicate and augments the given conditional
        expression with it, such that the runtime conditional value of that expression
        remains the same, but the expression is more complex.

        Args:
            cond_expr (Node): The AST root node corresponding to the conditional expression
            source_ancestor (Node): The first ancestor of cond_expr that existed in the
            original program; used to allow multiple-augmentation of conditionals without
            breaking analysis by reasoning about nodes not in the original AST.

        Returns:
            Node: The augmented conditional expression, or just the original expression
            if no augmentation can be performed.
        """
        parameters = self._get_unshadowed_parameters(source_ancestor)
        predicate = random.choice(OpaquePredicate.TRUE_PREDICATES)
        args = OpaquePredicate.get_opaque_predicate_args(
            self, predicate, parameters, True
        )
        if args is None:
            return cond_expr

        # Generate the opaque predicate and randmoly decide the truth value
        # and position of the predicate, negating if false.
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

    def test_add_predicate(self, node: Conditional) -> None:
        """Given some conditional AST node (e.g. if, while), this function will test it
        to check that the condition is not null, and then augment it with random chance
        depending upon the defined probability. It will augment multiple times to achieve
        the desired number of augmentations also.

        Args:
            node (Conditional): The AST node to potentially augment the condition of.
        """
        if node.cond is not None and random.random() < self.probability:
            ancestor = node.cond
            for _ in range(self.number):
                node.cond = self.generate_opaque_predicate(node.cond, ancestor)

    def visit_If(self, node: If) -> None:
        """Visits an If AST node, maybe augmenting its condition."""
        self.test_add_predicate(node)
        if node.iftrue is not None:
            self.visit(node.iftrue)
        if node.iffalse is not None:
            self.visit(node.iffalse)

    def visit_While(self, node: While) -> None:
        """Visits a While AST node, maybe augmenting its condition."""
        self.test_add_predicate(node)
        if node.stmt is not None:
            self.visit(node.stmt)

    def visit_DoWhile(self, node: DoWhile) -> None:
        """Visits a DoWhile AST node, maybe augmenting its condition."""
        self.test_add_predicate(node)
        if node.stmt is not None:
            self.visit(node.stmt)

    def visit_For(self, node: For) -> None:
        """Visits a For AST node, maybe augmenting its condition."""
        self.test_add_predicate(node)
        if node.init is not None:
            self.visit(node.init)
        if node.next is not None:
            self.visit(node.next)
        if node.stmt is not None:
            self.visit(node.stmt)

    def visit_TernaryOp(self, node: TernaryOp) -> None:
        """Visits a TernaryOp AST node, maybe augmenting its condition."""
        self.test_add_predicate(node)
        if node.iftrue is not None:
            self.visit(node.iftrue)
        if node.iffalse is not None:
            self.visit(node.iffalse)

    def visit_ParamList(self, node: ParamList) -> None:
        """Visits a ParamList AST node, determining if any contained parameters
        are valid parameters for use in opaque predicates. Such parameters are
        directly stored in the self.parameters attribute, and as such nothing is
        returned by this method.

        Args:
            node (ParamList): The ParamList to traverse and record.
        """
        if node.params is None or self.parameters is None:
            return  # No parameters or just parsing a signature.

        for node in node.params:
            if not isinstance(node, Decl) or node.name is None:
                continue
            if node.type is None or not isinstance(node.type, TypeDecl):
                continue  # We don't touch pointers
            if node.type.type is None or not isinstance(node.type.type, IdentifierType):
                continue  # We don't touch structs/unions
            if node.type.type.names is None or len(node.type.type.names) == 0:
                continue
            type_ = " ".join(node.type.type.names)
            if type_ in VALID_INT_TYPES:
                self.parameters.append((node.name, type_))
            elif type_ in self.global_typedefs.keys():
                # Handle typedef'd parameters
                if self.global_typedefs[type_] in VALID_INT_TYPES:
                    self.parameters.append((node.name, self.global_typedefs[type_]))

    def visit_Typedef(self, node: Typedef) -> None:
        """Visits a Typedef AST node, recording the type alias so long as it
        exists in the global namespace (outside of a function), and as such
        might be used in function parameter definitions. This is necessary as
        a lot of C programs use custom typedefs to rename common types.

        Args:
            node (Typedef): The Typedef to traverse and record.
        """
        if node.name is None or node.type is None or self.current_function is not None:
            return self.generic_visit(node)
        if not isinstance(node.type, TypeDecl) or node.type.type is None:
            return self.generic_visit(node)
        if (
            not isinstance(node.type.type, IdentifierType)
            or node.type.type.names is None
            or len(node.type.type.names) == 0
        ):
            # Ignore pointer/array types; we don't use them
            return self.generic_visit(node)
        typetype = node.type.type.names[-1]
        if typetype in self.global_typedefs.keys():
            # Handle the case of a Typedef to a typedef!
            self.global_typedefs[node.name] = self.global_typedefs[typetype]
        else:
            # Typedef to some standard C type
            self.global_typedefs[node.name] = typetype
        NodeVisitor.generic_visit(self, node)

    def visit_FuncDef(self, node: FuncDef) -> None:
        """Visits a FuncDef AST node, recording the function and resetting
        the current list of parameters available to use in opaque predicates.

        Args:
            node (FuncDef): The FuncDef node to traverse and record.
        """
        prev = self.current_function
        self.current_function = node
        self.parameters = []
        NodeVisitor.generic_visit(self, node)
        self.current_function = prev
        self.parameters = None

    def visit_FileAST(self, node: FileAST) -> None:
        """Visits the FileAST root node, traversing the AST before resetting
        the object's state, such that it can be used again for future mutation.

        Args:
            node (FileAST): The FileAST root node to traverse.
        """
        NodeVisitor.generic_visit(self, node)
        self._reset()


class AugmentOpaqueUnit(ObfuscationUnit):
    """Augments exiting conditional statements in the program with opaque predicates,
    obfuscating the true conditional test by introducing invariants on inputs or entropy
    that evaluate to known constants at runtime."""

    name = "Opaque Predicate Augmentation"
    description = "Augments existing conditionals with invariant opaque predicates."
    extended_description = (
        "This transformation augments existing conditional statements (if, if-else, while, do while, for\n"
        "and ternary operations) by adding an additional opaque predicate check, which is an expression\n"
        "whose value is always known to be true/false or either, where this cannot be quickly determined\n"
        "by an attacker attempting to reverse engineer the code. Opaque predicates cannot generally be\n"
        "optimised out by the compiler and will remain in compiled code.\n\n"
        "The first available input is the set of input styles that can be used - INPUT refers to the use\n"
        "of function parameters (i.e. user input) to construct opaque predicates, whereas ENTROPY refers\n"
        "to the use of global random values to generate these expressions. The second input is the\n"
        "probability of augmentation. A value of 0.0 means nothing will be augmented, 0.5 means approximately\n"
        "half will be augmented, and 1.0 means that all will be augmented. The third option corresponds to\n"
        "the number of opaque predicates that will be used to augment each transformed conditional. "
    )
    type = TransformType.STRUCTURAL

    def __init__(
        self, styles: Iterable[OpaqueAugmenter.Style], probability: float, number: int
    ):
        """The constructor for the AugmentOpaqueUnit transformation, storing the
        different user-customisable options.

        Args:
            styles (Iterable[OpaqueAugmenter.Style]): The list of opaque predicate
            parameter generation styles that can be used.
            probability (float): The probability of augmenting a program conditional;
            between 0 and 1.
            number (int): The number of opaque predicates to augment each encoded
            conditional with; a non-negative integer.
        """
        self.styles = styles
        self.probability = probability
        self.number = number
        self.traverser = OpaqueAugmenter(styles, probability, number)

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        """Performs the opaque predicate augmentation transformation on the given source program.

        Args:
            source (interaction.CSource): The source code to transform.

        Returns:
            interaction.CSource: The transformed source code.
        """
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
        """Create a readable string representation of the AugmentOpaqueUnit.

        Returns:
            str: The readable string representation.
        """
        style_flag = "styles=[" + ", ".join([x.name for x in self.styles]) + "]"
        probability_flag = f"p={self.probability}"
        number_flag = f"n={self.number}"
        return f"AugmentOpaqueUnit({style_flag},{probability_flag},{number_flag})"


class BugGenerator(NodeVisitor):
    """This class takes an AST subtree corresponding to some part (or whole) of a program,
    and subtly mutates the program to introduce bugs and incorrect behaviour by making subtle
    changes. This includes the mutation of constant values and substitution of operators
    such that the same instructions are used but the end result is a different program."""

    # A map from binary operators to valid buggy substitution targets
    bin_op_map = {
        ">": ("<", "<=", "!=", "=="),
        ">=": ("<", "<=", "!=", "=="),
        "<": (">", ">=", "!=", "=="),
        "<=": (">", ">=", "!=", "=="),
        "+": ("-",),
        "-": ("+",),
        "*": ("+", "-"),
        "==": ("!=", "<", ">"),
        "!=": ("==", "<", ">"),
        "&&": ("||",),
        "||": ("&&",),
    }

    # A map from unary operators to valid buggy substitution targets
    unary_op_map = {
        "--": ("++", "p--", "p++"),
        "++": ("--", "p++", "p--"),
        "p--": ("p++", "--", "++"),
        "p++": ("p--", "++", "--"),
        "-": ("+",),
        "+": ("-",),
    }

    def __init__(self, p_replace_op: float, p_change_constants: float):
        """The constructor for the BugGenerator class, taking probabilities for mutation.

        Args:
            p_replace_op (float): The probability that any supported unary or binary operator
            will be exchanged for some false alternative. Should be 0 <= p <= 1.
            p_change_constants (float): The probability that any individual constant value will
            be be mutated to become a slightly different value. Should be 0 <= p <= 1.
        """
        super(BugGenerator, self).__init__()
        self.p_replace_op = p_replace_op
        self.p_change_constants = p_change_constants
        self.in_case = False
        self.changed = False

    def reset(self) -> None:
        """Resets the state of object variables afterwards to permit reuse of the BugGenerator."""
        self.in_case = False
        self.changed = False

    def visit_Constant(self, node: Constant) -> None:
        """Visits a Constant AST node, traversing the node after probabilistically mutating
        the node to introduce a bug. Nodes are mutated where they contain some integer,
        float, or char value, and where state variables indicate that we are not currently in
        the middle of traversing a case label.

        Args:
            node (Constant): The Constant node to mutate or traverse.
        """
        if (
            node.value is None
            or node.type is None
            or self.in_case
            or (self.changed and random.random() >= self.p_change_constants)
        ):
            return self.generic_visit(node)
        int_types = ["int", "short", "long", "long long"]
        float_types = ["float", "double", "long double"]
        if node.type in int_types and int(node.value) != 0:
            # Modify the integer by a small random amount
            node.value = str(
                max(1, int(node.value) + random.choice([-3, -2, -1, 1, 2, 3]))
            )
            self.changed = True
        elif node.type in float_types and float(node.value) != 0.0:
            # Flip every significant figure in the decimal with 50% change
            new_val = ""
            digits = [str(i) for i in range(0, 10)]
            for char in node.value:
                if char not in digits or random.random() < 0.5:
                    new_val += char
                else:
                    new_val += random.choice(digits)
            node.value = new_val
            self.changed = True
        elif node.type == "char":
            # Shift to a random extended ASCII character value
            node.value = "'" + chr((ord(node.value[0]) + 1) % 256) + "'"
            self.changed = True
        self.generic_visit(node)

    def visit_BinaryOp(self, node: BinaryOp) -> None:
        """Visit a binary operator (expression) AST node in the program, probabilistically
        substituting the the operator for some other valid operator that introduces buggy
        behaviour. The operator subtree is then traversed (pre-order traversal).

        Args:
            node (BinaryOp): The binary operator AST node to traverse and mutate.
        """
        if (
            node.op in self.bin_op_map
            and not self.in_case
            and (not self.changed or random.random() < self.p_replace_op)
        ):
            node.op = random.choice(self.bin_op_map[node.op])
            self.changed = True
        self.generic_visit(node)

    def visit_UnaryOp(self, node: UnaryOp) -> None:
        """Visit an unary operator (expression) AST node in the program, probabilistically
        substituting the the operator for some other valid operator that introduces buggy
        behaviour. The operator subtree is then traversed (pre-order traversal).

        Args:
            node (UnaryOp): The binary operator AST node to traverse and mutate.
        """
        if (
            node.op in self.unary_op_map
            and not self.in_case
            and (not self.changed or random.random() < self.p_replace_op)
        ):
            node.op = random.choice(self.unary_op_map[node.op])
            self.changed = True
        self.generic_visit(node)

    def visit_Case(self, node: Case) -> None:
        """Visit a Case label AST node in the program, updating internal state object
        state variables to flag this context, such that we know not to perform any
        mutation inside the case label. This is because mutation could cause two cases
        to have the same value, which when folded by a compiler will cause a compilation
        error even though the two cases might use different expressions, and will never
        be executed. This is to avoid that error.

        Args:
            node (Case): The case label AST node to traverse.
        """
        was_in_case = self.in_case
        self.in_case = True
        if node.expr is not None:
            self.visit(node.expr)
        self.in_case = was_in_case
        if node.stmts is not None:
            for child in node.stmts:
                NodeVisitor.generic_visit(self, child)


class OpaqueInserter(NodeVisitor):
    """This class directly performs the opaque insertion obfuscation method by traversing and
    mutating a given program AST, generating new opaque predicates to augment existing conditionals
    in the code."""

    class Style(enum.Enum):
        """An enumerated type representing currently supported opaque predicate generation styles."""

        INPUT = "Construct predicates from dynamic user input"
        ENTROPY = "Construct predicates from entropic variables"

    class Granularity(enum.Enum):
        """An enumerated type representing currently supported granularities for newly inserted
        opaque predicate conditionals."""

        PROCEDURAL = "PROCEDURAL: Predicates are constructed on a whole function-level"
        BLOCK = "BLOCK: Predicates are constructed for random blocks of code (sequential statements)"
        STMT = "STATEMENT: Predictes are constructed for random individual statements"

    class Kind(enum.Enum):
        """An enumerated type representing currently supported kinds (structures) for newly
        inserted opaque predicate conditionals, changing the format of generated conditional trees."""

        CHECK = "CHECK: if (true predicate) { YOUR CODE } "
        FALSE = "FALSE: if (false predicate) { buggy code } "
        ELSE_TRUE = "ELSE_TRUE: if (true predicate) { YOUR CODE } else { buggy code }"
        ELSE_FALSE = (
            "ELSE_FALSE: if (false predicate) { buggy code } else { YOUR CODE } "
        )
        WHILE_FALSE = "WHILE_FALSE: while (false predicate) { buggy code } "
        DO_WHILE = "DO_WHILE: do { YOUR CODE } while (false predicate); "
        EITHER = "EITHER: if (any predicate) { YOUR CODE } else { YOUR CODE } "

    def __init__(
        self,
        styles: Iterable[Style],
        granularities: Iterable[Granularity],
        kinds: Iterable[Kind],
        number: int,
    ):
        """The constructor for the the OpaqueInserter traverser object.

        Args:
            styles (Iterable[Style]): The list of styles of opaque predicate operand
            generation that can be used.
            granularities (Iterable[Granularity]): The list of granularities at which
            new opaque predicate conditionals can be inserted.
            kinds (Iterable[Kind]): The list of kinds (structures/formats) in which
            new opaque predicate conditionals can be created.
            number (int): The target number of opaque predicates to try to insert
            per function.
        """
        self.styles = styles
        self.granularities = granularities
        self.kinds = kinds
        self.number = number
        self.bug_generator = BugGenerator(0.5, 0.4)
        self.label_finder = ObjectFinder((Label, Goto), ["name"])
        self.reset()

    def reset(self) -> None:
        """Resets the state of the OpaqueInserter, resetting all of the state variables
        and internal representatons used when traversing an AST. This includes variables
        for tracking functions and type definitions, AST node parents, the functions and
        parameters being parsed, and analysis tools, among other things.
        """
        self.functions = []
        self.global_typedefs = {}
        self.parent = None
        self.parent_map = {}
        self.node_cache = None
        self.current_function = None
        self.parameters = None
        self.analyzer = None
        self.source = None
        self.entropic_vars = []
        self.label_names = set()

    def process(self, source: interaction.CSource) -> None:
        """Processes the given C source program to perform the opaque predicate insertion
        obfuscation method. This requires performing identifier analysis on the program,
        and then traversing (and mutating) its AST to add additional opaque predicates.

        Args:
            source (interaction.CSource): The source C program to obfuscate.
        """
        # Instantly returned if no styles/granularities/kinds or number, as this means
        # that no opaque predicates will be inserted.
        if (
            len(self.styles) == 0
            or len(self.granularities) == 0
            or len(self.kinds) == 0
            or self.number == 0
        ):
            return
        self.analyzer = IdentifierAnalyzer(source)
        self.analyzer.process()
        self.source = source
        self.visit(source.t_unit)

    def _get_source_ancestor(self, node: Node) -> Node | None:
        """Retrieves the 'source ancestor' i.e. the lowest ancestor of a given node
        in the tree that existed in the original AST, before any mutation by inserting
        opaque predicates. This allows us to reason using our existing identifier tools
        without worrying about mutations made to the program AST.

        Args:
            node (Node): The node to find the source ancestor of.

        Returns:
            Node | None: The corresponding source ancestor, or None if no known
            source ancestor exists (the node is not in the parent map or is
            described as having no parent).
        """
        while node is not None:
            if self.node_cache.node_in_AST(node):
                return node
            elif node not in self.parent_map:
                return None
            node = self.parent_map[node]
        return None

    def _get_unshadowed_parameters(self, ast_node: Node) -> list[Tuple[str, str]]:
        """Retrieves a list of parameters for the function that the source_ancestor node
        is contained within, but only including the parameters that have not since been
        shadowed by another variable definition.

        Args:
            ast_node (Node): The AST node from which to retrieve parameters.

        Returns:
            list[Tuple[str,str]]: A list of parameters not shadowed at the current
            point in the program. Parameters are describes as (name, type).
        """
        parameters = []
        if len(self.parameters) != 0:
            source_ancestor = self._get_source_ancestor(ast_node)
            if source_ancestor is not None:
                for param in self.parameters:
                    def_node = self.analyzer.get_last_ident_definition(
                        source_ancestor, (param[0], NameSpace.ORDINARY)
                    )
                    if isinstance(def_node, ParamList):
                        # Only non-redefined parameters
                        parameters.append(param)
        return parameters

    def _get_opaque_predicate_args(
        self, predicate: Callable, parameters: list[Tuple[str, str]]
    ) -> list[ID | Cast] | None:
        """Based on the traverser's settings, this method selects a list of arguments
        (operands) to use in the creation of an opaque predicate. These are selected
        according to the selected predicate styles, as well as the existing program
        state.

        Args:
            predicate (function): A function that will take argument nodes to output
            an opaque predicate subtree.
            parameters (list[Tuple[str, str]]): A list of (unshadowed) parameters defined
            by the current function. Parameters are of the form (name, type).

        Returns:
            list[ID | Cast] | None: Returns the list of argument nodes/subtrees to be used
            to create the opaque predicate. These are either identifiers (directly), or casted
            values of identifiers (to make them the right type). Returns None if the current
            context and settings makes it impossible to fulfill the needed arguments.
        """
        num_args = predicate.__code__.co_argcount
        idents = []
        # Iteratively fill the number of required arguments
        while len(idents) < num_args:
            styles = [s for s in self.styles]

            # Select a random style from the list of chosen styles to use (if possible)
            valid_style = False
            while not valid_style and len(styles) != 0:
                style = random.choice(styles)
                styles.remove(style)
                if style == self.Style.INPUT:
                    valid_style = (
                        parameters is not None
                        and len(set(parameters).difference(set(idents))) != 0
                    )
                elif style == self.Style.ENTROPY:
                    valid_style = (
                        self.current_function is None
                        or self.current_function.decl is None
                        or self.current_function.decl.name is None
                        or self.current_function.decl.name != "main"
                    )
            if valid_style == False:
                return None  # No variables to use as parameters, so exit out
            if style == self.Style.INPUT:
                param = random.choice(parameters)
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
                else:
                    # Choose a random existing entropic variable to use
                    param = random.choice(available_vars)
            idents.append(param)
        args = []
        for ident in idents:
            if ident[1] not in VALID_REAL_TYPES:
                args.append(ID(ident[0]))
            else:
                cast_type = TypeDecl(None, [], None, IdentifierType(["int"]))
                typename = Typename(None, [], None, cast_type)
                args.append(Cast(typename, ID(ident[0])))
        return args

    def generate_opaque_predicate_cond(
        self, node: Node, predicate_sets: Iterable[Iterable[Callable]] | None = None
    ) -> Node | None:
        """Generates a tautological opaque predicate condition expression, such that the
        runtime conditional value of that expression is always true, but this cannot be
        immediately easily derived.

        Args:
            node (Node): The AST node corresponding to the real program statement subtree
            that will be encoded by the opaque predicate. This might be an individual
            statement or a compound statement.
            predicate_sets (Iterable[Iterable[Callable]] | None, optional): The sets of
            predicate generation functions that should be used to create opaque predicates.
            Each element of this should be an individual collection of functions that can
            generate opaque predicate expression trees from given expression arguments.
            Defaults to None, indicating that the default set of tautological predicates
            `[OpaquePredicate.TRUE_PREDICATES]`
            should be used.

        Returns:
            Node | None: Returns the opaque predicate condtional expression. Alternatively
            retuns None if the current context makes it impossible to generate an opaque
            predicate validating required constraints.
        """
        parameters = self._get_unshadowed_parameters(node)
        if predicate_sets is None:
            predicate = random.choice(OpaquePredicate.TRUE_PREDICATES)
        else:
            predicates = set()
            for pset in predicate_sets:
                predicates = predicates.union(set(pset))
            predicate = random.choice(list(predicates))
        args = OpaquePredicate.get_opaque_predicate_args(
            self, predicate, parameters, False
        )
        if args is None:
            return None
        return predicate(*args)

    def replace_labels(self, node: Node) -> None:
        """Given an AST node corresponding to some part (or whole) of a C program, this method
        finds all occurrences of labels (and GOTOs referring to these labels) in the program and
        changes these labels to use a different, unique name. This permits the duplication of
        code whilst maintaining validity by using alternate label names.

        Args:
            node (Node): The AST root node of the subtree to replace labels in.
        """
        # First find all labels, and rename them to some unique identifier
        local_label_idents = {}
        self.label_finder.visit(node)
        for obj in self.label_finder.objs:
            if not isinstance(obj, Label):
                continue
            if obj.name in local_label_idents:  # Rename repeat label occurrences
                obj.name = local_label_idents[obj.name]
                continue
            new_ident = self.analyzer.get_unique_identifier(list(self.label_names))
            local_label_idents[obj.name] = new_ident
            self.label_names.add(new_ident)
            obj.name = new_ident

        # Then, for all GOTOs, change relevant label names to locally defined labels.
        for obj in self.label_finder.objs:
            if isinstance(obj, Goto) and obj.name in local_label_idents:
                obj.name = local_label_idents[obj.name]
        self.label_finder.reset()

    def generate_buggy(self, stmt: Node) -> Compound:
        """Given some AST node relating to a given program statement oset of statements, this
        method copies the subtree and inserts some bugs at random, also replacing the labels of
        the copied subtree. It then returns this wrapped by a compound for direct, easy use as
        buggy code in conditional statements.

        Args:
            stmt (Node): _description_

        Returns:
            Compound: _description_
        """
        copied = copy.deepcopy(stmt)
        self.bug_generator.visit(copied)
        self.bug_generator.reset()
        self.replace_labels(copied)
        return Compound([copied])

    def generate_opaque_predicate(self, stmt: Node) -> Compound | None:
        """Given some AST node whose subtree corresponds to some program statement or collection
        of statements, this function randomly generates an opaque predicate conditional using
        that statement, based upon the OpaqueInsert's options. This includes the generation of
        an opaque expression and buggy code to create a compound with statements of the desired
        form.

        Args:
            stmt (Node): The AST node of a statement or compound (collection of statements)
            to insert an opaque predicate into.

        Returns:
            Compound | None: Returns a set of statements (a Compound statement) corresponding
            to the original statement with an opaque predicate inserted. This code will give
            the same result at runtime. Returns None if generation of an opaque predicate is
            impossible at the provided context using the specified settings.
        """
        # Work around for pycparser incorrect C generation; wrap statements in compounds
        # to avoid ambiguity in else branches.
        if not isinstance(stmt, Compound):
            new_stmt = Compound([stmt])
            self.parent_map[new_stmt] = self.parent_map[stmt]
            self.parent_map[stmt] = new_stmt
            stmt = new_stmt

        kind = random.choice(self.kinds)
        match kind:
            case self.Kind.CHECK:  # if (true) { your code }
                cond = self.generate_opaque_predicate_cond(stmt)
                if cond is None:
                    return None
                return Compound([If(cond, stmt, None)])
            case self.Kind.FALSE:  # if (false) { buggy code }
                cond = self.generate_opaque_predicate_cond(stmt)
                if cond is None:
                    return None
                cond = OpaquePredicate.negate(cond)
                buggy = self.generate_buggy(stmt)
                block_items = stmt.block_items if isinstance(stmt, Compound) else [stmt]
                return Compound([If(cond, buggy, None)] + block_items)
            case self.Kind.ELSE_TRUE:  # if (true) { YOUR CODE } else { buggy code }
                cond = self.generate_opaque_predicate_cond(stmt)
                if cond is None:
                    return None
                buggy = self.generate_buggy(stmt)
                return Compound([If(cond, stmt, buggy)])
            case self.Kind.ELSE_FALSE:  # if (false) { buggy code } else { YOUR CODE }
                cond = self.generate_opaque_predicate_cond(stmt)
                if cond is None:
                    return None
                cond = OpaquePredicate.negate(cond)
                buggy = self.generate_buggy(stmt)
                return Compound([If(cond, buggy, stmt)])
            case self.Kind.EITHER:  # if (either) { YOUR CODE } else { YOUR CODE }
                cond = self.generate_opaque_predicate_cond(
                    stmt, [OpaquePredicate.EITHER_PREDICATES]
                )
                if cond is None:
                    return None
                copied = copy.deepcopy(stmt)
                self.replace_labels(copied)
                return Compound([If(cond, stmt, copied)])
            case self.Kind.WHILE_FALSE:  # while (false) { buggy code }
                cond = self.generate_opaque_predicate_cond(stmt)
                if cond is None:
                    return None
                cond = OpaquePredicate.negate(cond)
                buggy = self.generate_buggy(stmt)
                block_items = stmt.block_items if isinstance(stmt, Compound) else [stmt]
                return Compound([While(cond, buggy)] + block_items)
            case self.Kind.DO_WHILE:  # do { YOUR CODE } while (false)
                cond = self.generate_opaque_predicate_cond(stmt)
                if cond is None:
                    return None
                cond = OpaquePredicate.negate(cond)
                return Compound([DoWhile(cond, stmt)])
            case _:
                return None

    def add_procedural_predicate(self, node: FuncDef) -> None:
        """This function adds a 'procedural-granularity' opaque predicate conditional
        to a given function, essentially wrapping the entirity of the function body within
        the conditional.

        Args:
            node (FuncDef): The FuncDef corresponding to the function to insert the
            opaque predicate conditional into.
        """
        new_body = self.generate_opaque_predicate(node.body)
        if new_body is None:
            return
        node.body = new_body
        old_parent = self.parent
        self.parent = node
        self.visit(node.body)
        self.parent = old_parent

    def _get_random_compound(self, compounds: list[Compound]) -> Compound | None:
        """Retrieves a random compound from a list of given compound, where the
        retrieved compound must be non-empty and must contain at least one statement
        that is not either a declaration, case/default label of a switch statement,
        or a label. This means the compound contains some statements that permit
        opaque predicate generation.

        Args:
            compounds (list[Compound]): The list of compounds to select from.

        Returns:
            Compound | None: Either the randomly selected compound that has the
            required properties, or None if no such compound exists.
        """
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

    def add_block_predicate(self, compounds: list[Compound]) -> bool:
        """This function adds a 'block-granularity' opaque predicate conditional to a given
        function, taking a random maximal-length contiguous sequence of statements in the
        program and creating an opaque predicate conditional surrounding these statements.

        Args:
            compounds (list[Compound]): The list of compounds from which predicates can
            be added to. This should usually be every compound in a function's AST subtree.

        Returns:
            bool: True if an opaque predicate was successfully generated, or False if an
            opaque predicate conditional could not be inserted due to the applied settings
            not permitting valid generation at that point in the program.
        """
        compound = self._get_random_compound(compounds)
        if compound is None:
            return False  # No way to add a block predicate - give up

        # Calculate maximal contiguous sequences of non-declarations
        # This is a special case of interval partitioning where intervals are sorted
        # and based upon contiguous positions.
        blocks = []
        for i, item in enumerate(compound.block_items):
            if not isinstance(item, (Decl, Case, Default, Label)):
                if len(blocks) == 0:
                    blocks.append((i, i))
                elif blocks[-1][1] == (i - 1):
                    blocks[-1] = (blocks[-1][0], i)
                else:
                    blocks.append((i, i))
        if len(blocks) == 0:
            return False

        # Choose a random 'block' (maximal contiguous sequence) and transfom it
        indexes = random.choice(blocks)
        block = Compound(compound.block_items[indexes[0] : indexes[1] + 1])
        if indexes[0] == 0:
            self.parent_map[block] = compound
        else:
            self.parent_map[block] = compound.block_items[indexes[0] - 1]
        new_block = self.generate_opaque_predicate(block)
        if new_block is not None:
            # Store the block 'in-place' in the AST, and update the parent
            # map internal representation.
            compound.block_items = (
                compound.block_items[: indexes[0]]
                + new_block.block_items
                + compound.block_items[indexes[1] + 1 :]
            )
            old_parent = self.parent
            self.parent = self.parent_map[compound]
            self.visit(compound)
            self.parent = old_parent
        return True

    def add_stmt_predicate(self, compounds: list[Compound]) -> bool:
        """This function adds a 'statement-granularity' opaque predicate conditional to a
        given function, taking a random non-declaration statement in the function body and
        creating an opaque predicate conditional surrounding it.

        Args:
            compounds (list[Compound]): The list of compounds from which predicates can
            be added to. This should usually be every compound in a function's AST subtree.

        Returns:
            bool: True if an opaque predicate was successfully generated, or False if an
            opaque predicate conditional could not be inserted due to the applied settings
            not permitting valid generation at that point in the program.
        """
        # Choose a random non-empty compound
        compound = self._get_random_compound(compounds)
        if compound is None:
            return False  # No way to add a block predicate - give up

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
            # Store the block 'in-place' in the AST, and update the parent
            # map internal representation.
            compound.block_items = (
                compound.block_items[:index]
                + new_block.block_items
                + compound.block_items[index + 1 :]
            )
            old_parent = self.parent
            self.parent = self.parent_map[compound]
            self.visit(compound)
            self.parent = old_parent
        return True

    def add_opaque_predicates(self, node: FuncDef) -> None:
        """Perform opaque predicate insertion on a given function, attempting to insert a
        specified number of opaque predicates specified by the settings values. Predicate
        granularity is randomly chosen following a 1:2:7 proportion of procedural, statement
        and block granularities respectively, with this proportion being normalised depending
        upon the selected granularities (so e.g. using only procedural and statement will give
        a 1:2 split).

        Args:
            node (FuncDef): The FuncDef AST node corresponding to a C function.
        """
        compounds = self.analyzer.get_compounds_in_subtree(node.body)
        # Normalise proportional representations based on chosen granularities
        # and determine the number of conditionals of each granularity to insert
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

        # Insert the opaque predicates; any failures at the statement or block
        # level should be retried at the procedural level which is more likely to
        # succeed (as e.g. a function might contain only declarations), such that
        # the desired number of predicates per function can be hit.
        for _ in range(amounts[self.Granularity.PROCEDURAL]):
            self.add_procedural_predicate(node)
        for _ in range(amounts[self.Granularity.BLOCK]):
            if not self.add_block_predicate(compounds):
                if self.Granularity.PROCEDURAL in self.granularities:
                    self.add_procedural_predicate(node)
        for _ in range(amounts[self.Granularity.STMT]):
            if not self.add_stmt_predicate(compounds):
                if self.Granularity.PROCEDURAL in self.granularities:
                    self.add_procedural_predicate(node)

    def visit_ParamList(self, node: ParamList) -> None:
        """Visits a ParamList AST node, traversing the parameter list to record
        all function parameters of valid types that may be used in opaque predicate
        generation.

        Args:
            node (ParamList): The parameter list AST node to traverse.
        """
        if node.params is None or self.parameters is None:
            return  # No parameters or just parsing a signature.

        for node in node.params:
            if not isinstance(node, Decl) or node.name is None:
                continue
            if node.type is None or not isinstance(node.type, TypeDecl):
                continue  # We don't touch pointers
            if node.type.type is None or not isinstance(node.type.type, IdentifierType):
                continue  # We don't touch structs/unions
            if node.type.type.names is None or len(node.type.type.names) == 0:
                continue
            type_ = " ".join(node.type.type.names)
            if type_ in VALID_INT_TYPES:
                self.parameters.append((node.name, type_))
            elif type_ in self.global_typedefs.keys():
                # Handle typedef'd parameters
                if self.global_typedefs[type_] in VALID_INT_TYPES:
                    self.parameters.append((node.name, self.global_typedefs[type_]))

    def visit_Typedef(self, node: Typedef) -> None:
        """Visits a Typedef AST node, recording the type alias so long as it
        exists in the global namespace (outside of a function), and as such
        might be used in function parameter definitions.

        Args:
            node (Typedef): The Typedef to traverse and record.
        """
        if node.name is None or node.type is None or self.current_function is not None:
            return self.generic_visit(node)
        if not isinstance(node.type, TypeDecl) or node.type.type is None:
            return self.generic_visit(node)
        if (
            not isinstance(node.type.type, IdentifierType)
            or node.type.type.names is None
            or len(node.type.type.names) == 0
        ):
            # Ignore pointer/array types; we don't use them
            return self.generic_visit(node)
        typetype = node.type.type.names[-1]
        if typetype in self.global_typedefs.keys():
            # Handle the case of a Typedef to a typedef!
            self.global_typedefs[node.name] = self.global_typedefs[typetype]
        else:
            # Typedef to some standard C type
            self.global_typedefs[node.name] = typetype
        self.generic_visit(node)

    def visit_FuncDef(self, node: FuncDef) -> None:
        """Visits a FuncDef AST node representing a function, recording the function
        and traversing it to find its parameters. Provided that the function offers an
        implementation and is not the main function, we then insert opaque predicates.

        Args:
            node (FuncDef): The FuncDef node to traverse, record and add conditionals to."""
        prev = self.current_function
        self.current_function = node
        self.functions.append(node)
        self.parameters = []
        self.generic_visit(node)
        if node.body is not None and node.decl is not None and node.decl.name != "main":
            self.add_opaque_predicates(node)
        self.current_function = prev
        self.parameters = None

    def visit_FileAST(self, node: FileAST) -> None:
        """Visits the FileAST root node, traversing and caching the AST before
        resetting the object's state, such that it can be used again for future obfuscation.

        Args:
            node (FileAST): The FileAST root node to traverse.
        """
        self.node_cache = ASTCacher()
        self.node_cache.visit(node)
        self.generic_visit(node)
        self.reset()

    def generic_visit(self, node: Node) -> None:
        """Visits (generically) all nodes in the AST, recording a node's parent in an
        associative array to create a simplfied tree extending the AST that can be
        traversed to find a node's ancestors within the original AST.

        Args:
            node (Node): The node to record and traverse.
        """
        self.parent_map[node] = self.parent
        self.parent = node
        super(OpaqueInserter, self).generic_visit(node)
        self.parent = self.parent_map[node]


class InsertOpaqueUnit(ObfuscationUnit):
    """Inserts new conditional statements in the program with opaque predicates,
    obfuscating the true control flow of the code by introducing conditional jumps on
    invariants on inputs or entropy that evalute to known constants at runtime."""

    name = "Opaque Predicate Insertion"
    description = "Inserts new conditionals with invariant opaque predicates"
    extended_description = (
        "This transformation inserts new conditional statements that check opaque predicates to the code.\n"
        "Opaque predicates are an expression whose value is always known to be true/false or either, where\n"
        "this cannot be quickly determined by an attacker attempting to reverse engineer the code. Opaque\n"
        "predicates cannot generally be optimised out by the compiler and will remain in compiled code.\n\n"
        "The first available input is the set of styles that can be used - INPUT refers to the use of\n"
        "function parameters (i.e. user input) to construct opaque predicates, whereas ENTROPY refers\n"
        "to the use of global random values to generate these expressions. The second input is the\n"
        "granularity of the optimisations (i.e. code construct size) - PROCEDURAl refers to the whole\n"
        "function, BLOCK refers to a sequence of statements, and STMT refers to single statements. The\n"
        "third input is the kinds (type of conditional construct) to use, as follows:\n"
        " > CHECK:       if (true predicate) { YOUR CODE }\n"
        " > FALSE:       if (false predicate) { buggy code }\n"
        " > ELSE_TRUE:   if (true predicate) { YOUR CODE } else { buggy code }\n"
        " > ELSE_FALSE:  if (false predicate) { buggy code } else { YOUR CODE }\n"
        " > EITHER:      if (any predicate) { YOUR CODE } else { YOUR CODE }\n"
        " > WHILE_FALSE: while (false predicate) { buggy code }\n"
        " > DO_WHILE:    do { YOUR CODE } while (false);\n"
        "The final input is the number of opaque predicates to insert in your function."
    )
    type = TransformType.STRUCTURAL

    def __init__(
        self,
        styles: Iterable[OpaqueInserter.Style],
        granularities: Iterable[OpaqueInserter.Granularity],
        kinds: Iterable[OpaqueInserter.Kind],
        number: int,
    ):
        """The constructor for the InsertOpaqueUnit transformation.

        Args:
            styles (Iterable[Style]): The list of styles of opaque predicate operand
            generation that can be used.
            granularities (Iterable[Granularity]): The list of granularities at which
            new opaque predicate conditionals can be inserted.
            kinds (Iterable[Kind]): The list of kinds (structures/formats) in which
            new opaque predicate conditionals can be created.
            number (int): The target number of opaque predicates to try to insert
            per function.
        """
        self.styles = styles
        self.granularities = granularities
        self.kinds = kinds
        self.number = number
        self.traverser = OpaqueInserter(styles, granularities, kinds, number)

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        """Performs the opaque predicate insertion transformation on the given source program.

        Args:
            source (interaction.CSource): The source code to transform.

        Returns:
            interaction.CSource: The transformed source code.
        """
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
        """Create a readable string representation of the InsertOpaqueUnit.

        Returns:
            str: The readable string representation.
        """
        style_flag = "styles=[" + ", ".join([x.name for x in self.styles]) + "]"
        granularity_flag = (
            "granularities=[" + ", ".join([x.name for x in self.granularities]) + "]"
        )
        kind_flag = "kinds=[" + ", ".join([x.name for x in self.kinds]) + "]"
        number_flag = f"n={self.number}"
        return f"InsertOpaqueUnit({style_flag},{granularity_flag},{kind_flag},{number_flag})"


class ControlFlowFlattener(NodeVisitor):
    """This class directly performs the control flow flattening obfuscation method, by traversing
    and mutating a given program AST, parsing a source-level 'control flow graph' representation
    and dispatching each basic block into a switch statement in a while loop to achieve flattening
    of each function."""

    class Style(enum.Enum):
        """An enumerated type representing currently supported control flow flattening case styles."""

        SEQUENTIAL = "Sequential Integers"
        RANDOM_INT = "Random Integers"
        ENUMERATOR = "Random Enum Members"

    def __init__(self, randomise_cases: bool, style: Style):
        """The constructor for ControlFlowFlattener objects.

        Args:
            randomise_cases (bool): Whether to randomise the order of flattened cases or not.
            style (Style): The style to use for generating case values used by the case variable
            when dispatching into a switch statement.
        """
        self.reset()
        self.randomise_cases = randomise_cases
        self.style = style

    def reset(self) -> None:
        """Resets the state of the ControlFlowFlattener, clearing its internal representation of
        the ASTs and resetting its tracking variables such that it can be re-used to flatten
        another AST (and hence antoher program).
        """
        # Stacks for tracking control flow while flattening
        self.levels = []
        self.breaks = []
        self.continues = []

        # Lists & variables for tracking control flow cases and function properties
        self.labels = []
        self.pending_head = []  # List of statements to prepend to the function head
        self.frees = []  # List of allocated variables to free at the end of a func
        self.added_idents = []
        self.current_function = None
        self.function_decls = None
        self.needs_stdlib = False  # if stdlib must be initialised (to malloc & free)

        # Structures for tracking control flow cases and their values
        self.cases = []
        self.numbers = set()
        self.checked_stmts = None
        self.unavailable_idents = None
        self.cur_number = 0

        # Misc. variables for augmenting AST traversal to move declarations as needed
        self.parent = None
        self.attr = None
        self.analyzer = None
        self.count = 0

    def transform(self, source: interaction.CSource) -> None:
        """Transforms a given C source program, applying the control flow flattening
        obfuscation method (with the current settings) to obfuscate the program.
        This involes running identifier analysis, traversing the AST, and intialising
        certain libraries if required.

        Args:
            source (interaction.CSource): The C source program to obfuscate.
        """
        self.analyzer = IdentifierAnalyzer(source)
        self.analyzer.process()
        self.visit(source.t_unit)
        if self.needs_stdlib and not utils.is_initialised(source, ["stdlib.h"])[0]:
            source.contents = "#include <stdlib.h>\n" + source.contents
        self.reset()

    def get_unique_number(self) -> Constant | ID:
        """Retrieves a new unique number to use as a new case label expression
        in the flattened control flow's switch dispatch statement. The number
        generated depends on the case variable generation style, either returning
        some constant integer node or an identifier reference to an enumerated
        value (which is similarly an integral type).

        Returns:
            Constant | ID: The AST expression of a unique case number. Returns
            the constant "0" if no valid supported style is defined.
        """
        if self.style == self.Style.SEQUENTIAL:
            # Simply generate the next sequential number
            num = self.cur_number
            self.cur_number += 1
            return Constant("int", str(num))
        elif self.style == self.Style.RANDOM_INT:
            # Generate a random number, increasing the side of the
            # random range as the number of generated numbers grows.
            self.cur_number += 1
            power = int(math.log2(self.cur_number) + 3)
            range_ = 2**power
            num = None
            while num is None or num in self.numbers:
                num = random.randint(
                    max(-2147483647, -range_), min(2147483647, range_ - 1)
                )
            self.numbers.add(num)
            return Constant("int", str(num))
        elif self.style == self.Style.ENUMERATOR:
            # Insert a new enumerated value (member) into some enumerated type used
            # for the case variable, and then return an identifier reference to
            # that new enumerated type for the case.
            exclude_set = self.numbers.union(set(level[0] for level in self.levels))
            enum = self.analyzer.get_unique_identifier(exclude_set)
            self.numbers.add(enum)
            return ID(enum)
        return Constant("int", "0")

    def __free_at_returns(self, func_body: Compound) -> None:
        """This function retroactively inserts `free(x)` statements before all
        return statements in a function body, freeing any malloc'd/alloca'd objects
        that were created during control flow flattening. These specifically free
        any variable length array (VLA) replacements, which must be malloc'd/alloca'd
        to replace the dynamic behaviour whilst moving the declaration to the beginning
        of the function.

        Args:
            func_body (Compound): _description_
        """
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

    def _get_unique_identifier(self) -> str:
        """Generates a unique identifier not used in the program, and adds it to
        the added_ident of identifiers added to the function during control flow
        flattening, before returning it. Generation simply uses the equivalent
        identifier analaysis tool.

        Returns:
            str: The new unique identifier not used elsewhere in the function.
        """
        new_ident = self.analyzer.get_unique_identifier(self.added_idents + self.labels)
        self.added_idents.append(new_ident)
        return new_ident

    def flatten_function(self, node: FuncDef) -> None:
        """Given the AST node corresponding to the root of a function definition tree,
        this method will perform control flow flattening on the function. Note that this
        assumes all variable declarations have already been moved to the beginning of
        the function, such that the first `x` statements will all be declarations, and all
        statements that follow will be non-declarations.

        Args:
            node (FuncDef): The AST FuncDef root node of the function declaration to flatten.
        """
        if (
            node.body is None
            or node.body.block_items is None
            or len(node.body.block_items) == 0
        ):
            return
        # Define while label and switch variable identifiers
        while_label = self._get_unique_identifier()
        self.labels = [while_label]
        switch_variable = self._get_unique_identifier()
        self.levels.append((switch_variable, while_label))

        # Generate a case number for the entry and exit case.
        exit = self.get_unique_number()
        entry = self.get_unique_number()
        self.cases = []
        if self.style == self.Style.ENUMERATOR:
            # If using enumerated value cases, define the enumerated type
            enum = Enum(self._get_unique_identifier(), EnumeratorList([]))
            new_statements = [Decl(None, [], [], [], [], enum, None, None)]
            switch_var_type = TypeDecl(switch_variable, [], [], Enum(enum.name, None))
        else:
            new_statements = []
            switch_var_type = TypeDecl(switch_variable, [], [], IdentifierType(["int"]))

        # Add statements for the while label/loop and switch dispatch
        switch_var_decl = Decl(
            switch_variable, [], [], [], [], switch_var_type, copy.deepcopy(entry), None
        )
        loop = Label(
            while_label,
            While(
                BinaryOp("!=", ID(switch_variable), copy.deepcopy(exit)),
                Compound([Switch(ID(switch_variable), Compound(self.cases))]),
            ),
        )
        new_statements += [switch_var_decl, loop]

        # Run the top-down flattening function on the function body compound
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
        self.__free_at_returns(node.body)

        # Shuffle cases if necessary
        if self.randomise_cases:
            random.shuffle(self.cases)

    def get_labels(self, stmt: Node) -> Tuple[Node, Label | None]:
        """Given an AST node representing some program statement, this function
        recursively traverses any labels to provide both the labelled statement
        and the first encountered label. So for example the statement
            a: b: c: d: e: f: g: int x = 4;
        would be returned as (Decl(...int x = 4...), Label("a", ...)).

        Args:
            stmt (Node): The AST node representing the root of some program
            statement subtree to strip labels from.

        Returns:
            Tuple[Node, Label | None]: A tuple containing the unlabelled
            statement node followed by the first such label. The second item
            is None if the given statement is not labelled at all.
        """
        label = None
        if isinstance(stmt, Label):
            label = stmt
        while isinstance(stmt, Label):
            stmt = stmt.stmt
        return (stmt, label)

    def get_labelled_stmt(self, label: Label | None, stmt: Node) -> Node:
        """Labels a statement with a given label, placing that label at the end
        of the list of existing labels such that labels are in the correct order.

        Args:
            label (Label): The label to add to the statement.
            stmt (Node): The program statement (AST node subtree root) to label.

        Returns:
            Node: The labelled statement.
        """
        if label is None:
            return stmt
        initial_label = label
        label_stmt = label.stmt
        while isinstance(label_stmt, Label):
            label = label_stmt
            label_stmt = label.stmt
        label.stmt = stmt
        return initial_label

    def transform_block(
        self, block: Node, entry: Node, exit: Node, label: Label | None = None
    ) -> None:
        """Flattens the control flow of a given 'block', where that block is either a sequence
        of contiguous statements or just a single statement. Takes an entry expression (the case
        of the first basic block of statements in the current block)

        Args:
            block (Node): An AST node whose subtree corresponds to either a statement or contiguous
            sequence of statements, which should be flattened.
            entry (Node): The case at which the first basic block of the provided statement block
            should be placed.
            exit (Node): The case to which the last basic block(s) of the provided statement block
            should jump to (by changing the value of the case variable to this value).
            label (Label | None, optional): The highest-level label applied to the given block
            (i.e. the highest ancestor label surrounding that statement). Defaults to None.
        """
        if label is None:
            block, label = self.get_labels(block)
        block_parts = []
        current_seq = []

        # Split the given block into sequences of statements, seperating out statements that contain
        # control flow altering structures (Compound, If, Switch, While, Do While, and For).
        if isinstance(block, Compound):
            for stmt in block.block_items:
                stmt, label = self.get_labels(stmt)
                if isinstance(stmt, (Compound, If, Switch, While, DoWhile, For)):
                    if len(current_seq) != 0:
                        block_parts.append(current_seq)
                        current_seq = []
                    block_parts.append((stmt, label))
                elif isinstance(stmt, Decl):
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

        # Continually transform block sequence parts using relevant transformation methods
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

    def transform_if(
        self, if_stmt: If, entry: Node, exit: Node, label: Label | None = None
    ) -> None:
        """Flattens the control flow of a given if statement, transforming the true and
        false statements encapsulated by the if statement to have different entry cases, and
        creating an if statement at the current block's entry. Note this is not full flattening;
        conditional jumps are not supported and as such technically we still have some
        control flow here until compiler optimisation is applied.

        Args:
            if_stmt (If): The if statement to flatten.
            entry (Node): The case at which the first basic block of the provided if statement
            should be placed.
            exit (Node): The case to which the last basic block(s) of the provided if statement
            should jump to (by changing the value of the case variable to this value).
            label (Label | None, optional): The highest-level label applied to the given statement
            (i.e. the highest ancestor label surrounding that statement). Defaults to None.
        """
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

    def transform_while(
        self, while_stmt: While, entry: Node, exit: Node, label: Label | None = None
    ) -> None:
        """Flattens the control flow of a given while statement, creating a basic block (case) for the
        conditional 'test' branching statement and for the loop body. The entry basic block is the
        test block, which then either transitions to the end block or loop block. The loop block is
        defined such that it exits by returning to the test block.

        Args:
            while_stmt (While): The while statement to flatten.
            entry (Node): The case at which the first basic block of the provided while statement
            should be placed.
            exit (Node): The case to which the last basic block(s) of the provided while statement
            should jump to (by changing the value of the case variable to this value).
            label (Label | None, optional): The highest-level label applied to the given statement
            (i.e. the highest ancestor label surrounding that statement). Defaults to None.
        """
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

        # Add break/continue stack levels before transforming to track which block break/continue
        # control flow statements should transition to.
        self.breaks.append((len(self.levels), exit))
        self.continues.append((len(self.levels), entry))
        self.transform_block(while_stmt.stmt, body_entry, entry)
        self.breaks = self.breaks[:-1]
        self.continues = self.continues[:-1]

    def transform_switch(
        self, switch_stmt: Switch, entry: Node, exit: Node, label: Label | None = None
    ) -> None:
        """Flattens the control flow of a given switch statement, creating a labelled block for
        each case and then jumping to that label, such that the control flow within the switch
        compound is preserved whilst case labels are correctly kept in place. The entry block
        switches over the case variable to jump to each case label, and each case is transformed
        such that they point to the next case, except for the last case which points to the exit.

        Args:
            while_stmt (While): The switch statement to flatten.
            entry (Node): The case at which the first basic block of the provided switch statement
            should be placed.
            exit (Node): The case to which the last basic block(s) of the provided switch statement
            should jump to (by changing the value of the case variable to this value).
            label (Label | None, optional): The highest-level label applied to the given statement
            (i.e. the highest ancestor label surrounding that statement). Defaults to None.
        """
        switch_variable = self.levels[-1][0]
        switch_body = Compound([])
        goto_labels = []
        goto_label = None
        for stmt in switch_stmt.stmt.block_items:
            # Parse additional labels from case statements
            if isinstance(stmt, Label):
                labelled_stmt, stmt_label = self.get_labels(stmt)
                if isinstance(labelled_stmt, (Case, Default)):
                    stmt = labelled_stmt
            else:
                stmt_label = None

            # Handle both normal cases and defaults, creating a new label identifier and labelling the
            # statement, as well as creating a switch case for a GOTO to that label
            if isinstance(stmt, (Case, Default)):
                if goto_label is None:
                    goto_label = self._get_unique_identifier()
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

                # Appent subsequent non-labeled case/default statements at the end
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
                # Handle statements inside the switch statement but that are not cases/defaults,
                # appending them to the switch block body without any extra labelling.
                if goto_label is not None:
                    switch_body.block_items.append(Label(goto_label, stmt))
                    goto_label = None
                else:
                    switch_body.block_items.append(stmt)
        if goto_label is not None:
            switch_body.block_items.append(Label(goto_label, EmptyStatement()))
            goto_label = None

        # Construct the main case statement which goes to relevant basic block
        # labels on relevent case values, and then transitions to the exit block.
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

    def transform_do_while(
        self, do_stmt: DoWhile, entry: Node, exit: Node, label: Label | None = None
    ) -> None:
        """Flattens the control flow of a given do while statement, creating a basic block (case) for
        the conditional 'test' branching statement and for the loop body. The entry basic block is
        the body block, which then transitions to the test block, which in turn either transitions to
        the end block or loop block depending on the condition value.

        Args:
            do_stmt (DoWhile): The do while statement to flatten.
            entry (Node): The case at which the first basic block of the provided do while statement
            should be placed.
            exit (Node): The case to which the last basic block(s) of the provided do while statement
            should jump to (by changing the value of the case variable to this value).
            label (Label | None, optional): The highest-level label applied to the given statement
            (i.e. the highest ancestor label surrounding that statement). Defaults to None.
        """
        # Define the basic block case for the do while conditional block
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

        # Define the basic block case for the do while body entry
        body_entry_case = Case(
            copy.deepcopy(entry),
            [
                self.get_labelled_stmt(
                    label,
                    Assignment("=", ID(switch_variable), copy.deepcopy(body_entry)),
                ),
                Break(),
            ],
        )
        self.cases.append(body_entry_case)

        # Add break/continue stack levels before transforming to track which block break/continue
        # control flow statements should transition to.
        self.breaks.append((len(self.levels), exit))
        self.continues.append((len(self.levels), test_entry))
        self.transform_block(do_stmt.stmt, body_entry, test_entry)
        self.breaks = self.breaks[:-1]
        self.continues = self.continues[:-1]

    def transform_for(
        self, for_stmt: For, entry: Node, exit: Node, label: Label | None = None
    ) -> None:
        """Flattens the control flow of a given for statement, creating a basic block (case) for
        the for loop's initialisation statement if one exists, which transitions to a basic block
        for the for loop's conditional statement, which either transititions to the exit basic block,
        or to a basic block for the loop body, which exits by transitioning to a basic block to the
        increment case (where one exists), which itself finally transitions back to the conditional block.

        Args:
            for_stmt (For): The for statement to flatten.
            entry (Node): The case at which the first basic block of the provided for statement
            should be placed.
            exit (Node): The case to which the last basic block(s) of the provided for statement
            should jump to (by changing the value of the case variable to this value).
            label (Label | None, optional): The highest-level label applied to the given statement
            (i.e. the highest ancestor label surrounding that statement). Defaults to None.
        """
        # Create a basic block for initialization if one exists
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

        # Create a basic block for the for loop condition
        # As is defined in the C99 specification, if the conditional is empty (i.e.
        # for (;;) { ... }) then this is treated as a conditional with constant value 1.
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

        # Create a basic block for the loop's increment
        inc_case = Case(
            copy.deepcopy(inc_entry),
            ([for_stmt.next] if for_stmt.next is not None else [])
            + [
                Assignment("=", ID(switch_variable), copy.deepcopy(test_entry)),
                Break(),
            ],
        )
        self.cases.append(inc_case)

        # Add break/continue stack levels before transforming to track which block break/continue
        # control flow statements should transition to.
        self.breaks.append((len(self.levels), exit))
        self.continues.append((len(self.levels), inc_entry))
        self.transform_block(for_stmt.stmt, body_entry, inc_entry)
        self.breaks = self.breaks[:-1]
        self.continues = self.continues[:-1]

    def transform_sequence(self, sequence: list[Node], entry: Node, exit: Node) -> None:
        """Flattens the control flow of a given sequence of (non-conditional statements), which exclude
        If, For, Switch, While, Compound and Do While statements. Examples of statements that might be
        included are Continue, Break, Assignments, FuncCalls and other expressions. These statements
        are flattened by storing all of the given statements in the provided entry basic block (case),
        except creating unconditional branches on labels for control flow statements like Continue or
        Goto using the exit locations stored in relevant stacks. Otherwise, the basic block then
        exits by transitioning to the given exit case as normal.

        Args:
            sequence (list[Node]): The sequence of statements to flatten
            entry (Node): The case at which the basic block of the provided statements should be placed.
            exit (Node): The case to which the basic block of the provided statements should jump to
            if no Continue/Break control flow statements are specified.
        """
        stmts = []
        case = Case(copy.deepcopy(entry), stmts)
        for stmt in sequence:
            stmt, label = stmt
            if isinstance(stmt, Continue):
                # Continues should jump to the innermost loop's conditional 'test' block, whose case value
                # is specified by the top value on the continues stack.
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
                # Breaks should jup to the innermost loop's designated exit block, whose case
                # value is specified by the top value on the breaks stack.
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
                # Other statements (e.g. assignments, function calls) are included as is
                stmts.append(self.get_labelled_stmt(label, stmt))
        stmts.append(Assignment("=", ID(self.levels[-1][0]), copy.deepcopy(exit)))
        stmts.append(Break())
        self.cases.append(case)

    def visit_FuncDef(self, node: FuncDef) -> None:
        """Visits a FuncDef AST node whose subtree corresponds to a function definition.
        This method calls relevant methods for first traversing the function (which mutates
        it, moving its declarations to the start of the function body), and then flattens
        the function. This primarily involves the creation and maintenance of various function
        state tracking variables.

        Args:
            node (FuncDef): The FuncDef AST node to traverse (corresponds to a function).
        """
        # Maintain function state variables
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
        # Traverse & flatten the function
        self.visit(node.body)
        self.flatten_function(node)
        if node.body is not None and node.body.block_items is not None:
            node.body.block_items = self.pending_head + node.body.block_items
        # Maintain function state variables
        self.function_decls = None
        self.current_function = None
        self.cur_number = 0
        self.numbers = set()

    def _replace_statement(self, node: Node, replacement: list[Node] | None):
        """Replace a given statement in the program with some other list of statements,
        or with nothing (essentially removing the statement entirely).

        Args:
            node (Node): The AST node corresponding to the root of the statement
            subtree to be replaced.
            replacement (list[Node] | None): Either the list of AST nodes corresponding
            to the the statements to replace the statement with, or None to signify
            that the statement should just be removed, replaced by nothing.
        """
        replace_with = [] if replacement is None else replacement
        if isinstance(self.parent, Compound):
            i = self.parent.block_items.index(node)
            self.parent.block_items = (
                self.parent.block_items[:i]
                + replace_with
                + self.parent.block_items[(i + 1) :]
            )
        elif isinstance(self.parent, (Case, Default)):
            i = self.parent.stmts.index(node)
            self.parent.stmts = (
                self.parent.stmts[:i] + replace_with + self.parent.stmts[(i + 1) :]
            )
        elif isinstance(self.parent, ExprList):  # DeclList after transformation
            i = self.parent.exprs.index(node)
            self.parent.exprs = (
                self.parent.exprs[:i] + replace_with + self.parent.exprs[(i + 1) :]
            )
        elif replacement is None or len(replacement) == 1:
            setattr(self.parent, self.attr, replacement)
        else:
            setattr(self.parent, self.attr, Compound(replacement))

    def visit_Typedef(self, node: Typedef) -> None:
        """Visits a Typedef AST node, which performs some form of type aliasing. This
        function specifically finds non-global type aliases (those within some function),
        and records the declaration such that it can be moved to the beginning of the
        function body. If some program construct (in the same name space) with that name
        already exists, then the type alias and all of its occurrences are renamed using
        identifier analysis utilities to avoid naming conflicts.

        Args:
            node (Typedef): The Typedef AST node to traverse and move.
        """
        if self.current_function is None:
            return

        # Retrieve the statement corresponding to the typedef
        stmt = self.analyzer.get_stmt_from_node(node)
        if stmt in self.checked_stmts:
            return self.generic_visit(node)

        # Perform identifier renaming if necessary to avoid typedef clashes
        unavailable_names = set(self.function_decls)
        unavailable_names.update(set(self.unavailable_idents))
        for definition in list(self.analyzer.get_stmt_definitions(stmt)):
            ident, kind = definition
            if definition in unavailable_names or ident in self.added_idents:
                # Renaming required to avoid conflicts
                num = 2
                new_ident = ident
                new_definition = (new_ident, kind)
                while (
                    new_definition in unavailable_names
                    or new_ident in self.added_idents
                ):
                    new_ident = ident + str(num)
                    new_definition = (new_ident, kind)
                    num += 1
                self.analyzer.change_ident(stmt, ident, kind, new_ident)
                self.function_decls.add((new_ident, kind))
            else:
                self.function_decls.add((ident, kind))
        self.checked_stmts.add(stmt)

        # Create a relevant corresponding typedef at the start of the function
        typedef = Typedef(node.name, node.quals, node.storage, node.type)
        self.pending_head.append(typedef)
        self.generic_visit(node)

        # Remove the existing typedef in the tree from its parent
        self._replace_statement(node, None)

    def __get_array_size(self, node: Node) -> list[int] | None:
        """Given a declaration for some array type with unspecified dimensions,
            e.g. char x[] = 'example';
        This function calculates the array's size such that the declaration can
        be moved to the start of the function. This is extended to multi-dimensional
        arrays, finding the sizes in such cases.

        Args:
            node (Node): The AST node corresponding to some declaration for some
            variable with an array type of unspecified dimensions.

        Returns:
            list[int] | None: Returns a list specifying the size the array, where
            each list item corresponds to the size of a subsequent list dimension.
            These go from outermost-to-innermost array dimensions. [] represents a
            0-dimensional scalar value. Returns None if the provided array is not
            of a valid format.
        """
        if node is None:
            return None
        if isinstance(node, InitList):
            # Measure the size of each array element recursively
            if node.exprs is None:
                return [0]
            cur_dim = len(node.exprs)
            elem_dims = [self.__get_array_size(e) for e in node.exprs]
            if all(x is None for x in elem_dims):
                return [cur_dim]
            # Coalesce None sizes, and coalesce shapes to max dimension
            elem_dims = [[0] if x is None else x for x in elem_dims]
            max_dims = max(len(x) for x in elem_dims)
            elem_dims = [x + [0] * (max_dims - len(x)) for x in elem_dims]
            # Find and return max dimension sizes
            return [cur_dim] + [max(col) for col in zip(*elem_dims)]
        elif isinstance(node, CompoundLiteral):
            if node.init is None:
                return None
            return self.__get_array_size(node.init)
        elif isinstance(node, Constant):
            # Constants are 1 dimensional values not modelled by array dimensions,
            # and thus are given a 0-dimensional size of "[]".
            if node.type is None or node.value is None:
                return None
            if node.type == "string":
                return [len(node.value)]
            else:
                return []
        return None

    def __is_variable_expr(self, node: Node) -> bool:
        """Determines if some expression contains any identifiers (variable
        references), and as such whether it uses runtime values.

        Args:
            node (Node): The AST node corresponding to the expression subtree root.

        Returns:
            bool: True if the expression references a variable, false if not.
        """
        if node is None:
            return False
        id_finder = ObjectFinder(ID, ["name"])
        id_finder.visit(node)
        return len(id_finder.objs) != 0

    def __get_init_list_exprs(self, node: Node) -> list[Tuple[Node, list[int]]]:
        """Recursively retrieves a list of expressions from a nested initializer
        list structure (e.g. {{1, 2, 3}, {4, 5, 6}}) using a simple breadth-first
        search recursive definition, traversing items in the same order that they
        are provided.

        Args:
            node (Node): An AST node corresponding to either an initializer list
            or some expression within that intialzier list.

        Returns:
            list[Tuple[Node, list[int]]]: The linear sequence of items stored in the 
            nested list structure, given in the same order that they are written. Each
            item is represented by a tuple (item, indexes) whose first element is the
            array element, and whose second element is the list of sequential array
            indexes that the elemtn is located at.
        """
        if not isinstance(node, InitList):
            return [(node, [])]
        if node.exprs is None:
            return []
        exprs = []
        for i, expr in enumerate(node.exprs):
            item_exprs = self.__get_init_list_exprs(expr)
            exprs += [(expr, [i] + dims) for expr, dims in item_exprs]
        return exprs

    def _rename_decl(self, node: Decl, stmt: Node) -> None:
        """Given a declaration and the statement within which that declaration occurs,
        this function determines if the declaration has the same name as any declared
        constuct already moved to the start of the function. If so, it renames the
        declaration and all of its references/occurrences accordingly using identifier
        analysis tools. Also records the new name of the declaration.

        Args:
            node (Decl): The declaration AST root node.
            stmt (Node): The AST root node whose subtree coresponds to the statement
            containing the given declaration.
        """
        unavailable_names = set(self.function_decls)
        unavailable_names.update(set(self.unavailable_idents))
        for definition in list(self.analyzer.get_stmt_definitions(stmt)):
            ident, kind = definition
            if isinstance(self.parent, ExprList) and ident != node.name:
                continue
            if definition in unavailable_names or ident in self.added_idents:
                # Renaming required to avoid conflicts
                num = 2
                new_ident = ident
                new_definition = (new_ident, kind)
                while (
                    new_definition in unavailable_names
                    or new_ident in self.added_idents
                ):
                    new_ident = ident + str(num)
                    new_definition = (new_ident, kind)
                    num += 1
                self.analyzer.change_ident(stmt, ident, kind, new_ident)
                self.function_decls.add((new_ident, kind))
            else:
                self.function_decls.add((ident, kind))

    def _create_start_declaration(self, node: Decl, is_variable_expr: bool) -> Decl:
        """Given a declaration in the program, this function returns a corresponding
        declaration for the variable that could be placed at the start of the function
        for flattening, with (a) any assignment removed, (b) unknown array sizes filled
        in and (c) variable-length array declarations replaced.

        Args:
            node (Decl): The declaration AST node you're trying to move.
            is_variable_expr (Bool): Whether the declaration contains reference to
            some runtime variable or not (i.e. as in a VLA).

        Returns:
            Decl: The corresponding declaration that could be placed at the start
            of the function body.
        """
        if (
            node.type is not None
            and isinstance(node.type, ArrayDecl)
            and node.type.dim is None
        ):
            # Determine the size of arrays with no specified size (can be multi-dimensional)
            array_dims = self.__get_array_size(node.init)
            node_type = copy.deepcopy(node.type)
            arr_decl = node_type
            for dim in array_dims:
                arr_decl.dim = Constant("int", str(dim))
                arr_decl = arr_decl.type
                if arr_decl is None or not isinstance(arr_decl, ArrayDecl):
                    # Log unexpected array dimension parsing issues
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
                next_decl = PtrDecl(None, None)
                ptr_decl.type = next_decl
                ptr_decl = next_decl
                arr_decl = arr_decl.type
            ptr_decl.type = arr_decl.type
        else:
            node_type = node.type

        # Recurisvely parse array/pointers to modify relevant qualification information.
        cur_type = node_type
        while isinstance(cur_type, (ArrayDecl, PtrDecl)):
            cur_type = cur_type.type
        if (
            cur_type is not None
            and isinstance(cur_type, TypeDecl)
            and cur_type.quals is not None
        ):
            cur_type.quals = [q for q in node.quals if q != "const"]

        # Create the new start declaration
        if node.quals is None:
            quals = None
        else:
            quals = [q for q in node.quals if q != "const"]
        return Decl(
            node.name,
            quals,
            node.align,
            node.storage,
            node.funcspec,
            node_type,
            None,  # No assignment
            node.bitsize,
        )

    def replace_initlist_assignment(self, node: Decl) -> list[Node]:
        """ Given an declaration that assigns an initializer list to some array type,
        that is being moved to the start of a function body to allow for control flow 
        flattening, this function creates a series of statement equivalent to 
        assignments to place elements in their correct indexes.

        Args:
            node (Decl): The declaration AST node to replace, using an InitList
            to assign to some array type.

        Returns:
            list[Node]: A list of program statements equivalent to the given declaration's
            assignment. Normally one statement, but can be multiple assignments to replace 
            array initialisation with individual index accesses.
        """
        # We first retrieve a list of expressions from the initializer lists and their
        # corresponding indexes.
        exprs = self.__get_init_list_exprs(node.init)
        
        # We then parse array dimension information out in case the initializer list
        # is flattened, and hence its indexes cannot be used. 
        dims = []
        elem_type = node.type
        while isinstance(elem_type, ArrayDecl) and elem_type.type is not None:
            if elem_type.dim is None:
                dims = []
                break
            dims.append(elem_type.dim)
            elem_type = elem_type.type
        
        # We take the indexing locations and use them to construct n-dimensional
        # array accesses for each individual element
        assign = []
        for i, (expr, indexes) in enumerate(exprs):
            # For 1D arrays we do simple standard 1D indexing
            if indexes is None or indexes == [] or len(dims) == 1:
                ref = ArrayRef(ID(node.name), Constant("int", str(i)))
                assign.append(Assignment("=", ref, expr))
                continue
            
            # For 2 or more dimensional arrays, we recursively build an array index.
            ref = ArrayRef(None, None)
            current_ref = ref
            if len(indexes) == len(dims) or len(dims) == 0: 
                # The initializer list is not flattened; use its indexes.
                for index in indexes[::-1]:
                    current_ref.name = ArrayRef(None, Constant("int", str(index)))
                    current_ref = current_ref.name
            else:
                # The initializer list is flattened; calculate new indexes.
                prod = Constant("int", "1")
                for dim in dims[::-1]:
                    current_ref.name = ArrayRef(
                        None,
                        BinaryOp(
                            "%", BinaryOp("/", Constant("int", str(i)), prod), dim
                        ),
                    )
                    current_ref = current_ref.name
                    prod = BinaryOp("*", dim, prod)

            # Assign the element at its derived location.
            current_ref.name = ID(node.name)
            ref = ref.name
            assign.append(Assignment("=", ref, expr))
        return assign

    def replace_decl_with_assignment(self, node: Decl) -> list[Node]:
        """ Given a declaration that is being moved to the start of a function body to
        allow for control flow flattening, this function creates a series of statement
        equivalent to assignments to place the correct value in the declaration. Most
        of the time this is one assignment, but can be a list as array initializer lists
        must unfortunately be replaced by individual assignments. 

        Args:
            node (Decl): The declaration AST node to replace

        Returns:
            list[Node]: A list of program statements equivalent to the given declaration's
            assignment. Normally one statement, but can be multiple assignments to replace 
            array initialisation with individual index accesses.
        """
        if node.init is None:
            assign = []
        elif (
            isinstance(node.init, InitList)
            and isinstance(node.type, TypeDecl)
            and isinstance(node.type.type, Union)
        ):
            # Handle translating an InitList for unions
            # We only consider 1 element - can't have > 1 for unions, and we ignore 0.
            assign = []
            if node.init.exprs is not None and len(node.init.exprs) != 0:
                first_field = node.type.type.decls[0].name
                assign.append(
                    Assignment(
                        "=",
                        StructRef(ID(node.name), ".", ID(first_field)),
                        node.init.exprs[0],
                    )
                )
        elif (
            isinstance(node.init, InitList)
            and isinstance(node.type, TypeDecl)
            and isinstance(node.type.type, Struct)
        ):
            # Handle translating an InitList for structs
            # All struct members must be individually parsed and assigned.
            assign = []
            decls = node.type.type.decls
            if decls is None:
                decls = []
            if node.init.exprs is not None:
                if len(node.init.exprs) > len(decls):
                    exprs = node.init.exprs[: len(decls)]
                else:
                    exprs = node.init.exprs
                for i, expr in enumerate(exprs):
                    field = node.type.type.decls[i].name
                    assign.append(
                        Assignment("=", StructRef(ID(node.name), ".", ID(field)), expr)
                    )
        elif isinstance(node.init, InitList):
            # Handle translating an InitList for arrays
            assign = self.replace_initlist_assignment(node)
        else:
            # Replace all other assignments directly 
            assign = [Assignment("=", ID(node.name), node.init)]
        return assign

    def visit_Decl(self, node: Decl) -> None:
        """Visits a declaration AST node, whose subtree corresponds to some declaration statement
        in the program, declaring a variable's creation. This method traverses the node, and
        moves the declaration to the top of the current function body, ignoring any delcarations
        outside functions. This is a non-trivial process involving potential variable renaming,
        array initializer list conversions and array allocation to replace variable-length array
        (VLA) structures.

        Args:
            node (Decl): The declaration AST node to traverse and move to the function start.
        """
        if self.current_function is None or isinstance(self.parent, ParamList):
            return
        # Retrieve the declaration statement and rename the identifier if necessary
        stmt = self.analyzer.get_stmt_from_node(node)
        if stmt in self.checked_stmts and not isinstance(self.parent, ExprList):
            return self.generic_visit(node)
        self._rename_decl(node, stmt)
        self.checked_stmts.add(stmt)

        # Create a relevant corresponding declaration at the start of the function,
        # and replace the declaration itself with an assignment
        is_variable_expr = self.__is_variable_expr(node.type)
        decl = self._create_start_declaration(node, is_variable_expr)
        self.pending_head.append(decl)
        assign = self.replace_decl_with_assignment(node)
        
        # Replace variable length array instances specifically with (almost)
        # equivalent malloc/alloca arrays.
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

            # Create an alloca/malloc for the Variable Length Array (VLA)
            alloc_func = FuncCall(
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
            )
            assign = [Assignment("=", ID(node.name), alloc_func)] + assign
            if not cfg.USE_ALLOCA:
                self.frees.append(ID(node.name))
            self.needs_stdlib = True

        # Finally replace the declaration and continue traversal as normal.
        self._replace_statement(node, assign)
        self.generic_visit(node)

    def visit_DeclList(self, node: DeclList) -> None:
        """Traverses a DeclList declaration list AST node, corresponding to some list
        of declarations in the program. This simply involves traversing the node to 
        visit its child declarations, but we first translate the DeclList to be a list
        of declarations followed by an ExprList of assignments, such as that the the
        regular declaration movement function can handle this case. 

        Args:
            node (DeclList): _description_
        """
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

    def generic_visit(self, node: Node) -> None:
        """Visits all generic AST nodes, tracking which node is a parent of the node 
        currently being traversed and in which attribute of that parent node the 
        current child node is stored.

        Args:
            node (Node): The AST node being traversed.
        """
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
        "This transformation \"flattens\" the control flow of a program - normal programs are a sequential\n"
        "sequents of code blocks with jumps between them. Control flow flattening separates these blocks,\n"
        "numbering them all and putting every block inside a switch statement in a while loop. Jumps between\n"
        "blocks are encoded as a variable change within the loop structure. This completely transforms the\n"
        "control flow graph representing the program, preventing analysis of the control flow.\n\n"
        "WARNING: Due to limitations of pycparser, this currently does not work with labelled case statements, e.g.\n"
        "switch (x) {\n"
        "    abc: case 1: do_stuff(); break;\n"
        "}\n\n"
        "WARNING: Currently requires to translate variable length arrays (VLAs) to MALLOCs or ALLOCAs.\n"
        "This is mostly equivalent, but does have some semantic differences - e.g. sizeof() will give a\n"
        "different result. So, do not use this method with variable length arrays if you rely on sizeof()."
    )
    type = TransformType.STRUCTURAL

    def __init__(self, randomise_cases: bool, style: ControlFlowFlattener.Style):
        """The constructor for the ControlFlowFlattenUnit transformation.

        Args:
            randomise_cases (bool): Whether to randomise dispatched switch
            cases or not when flattening control flow.
            style (ControlFlowFlattener.Style): The case variable generation 
            style to use in the control flow flattening transformation. 
        """
        self.randomise_cases = randomise_cases
        self.style = style
        self.traverser = ControlFlowFlattener(randomise_cases, style)

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        """Performs the control flow flattening transformation on the given source program.

        Args:
            source (interaction.CSource): The source code to transform.

        Returns:
            interaction.CSource: The transformed source code.
        """
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
        """Create a readable string representation of the ControlFlowFlattenUnit.

        Returns:
            str: The readable string representation.
        """
        randomise_flag = (
            f"random_order={'ENABLED' if self.randomise_cases else 'DISABLED'}"
        )
        style_flag = f"style={self.style.name}"
        return f"FlattenControlFlow({randomise_flag},{style_flag})"
