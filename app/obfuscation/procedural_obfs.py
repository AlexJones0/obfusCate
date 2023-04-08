""" File: obfuscation/procedural_obfs.py
Implements classes (including obfuscation unit classes) for performing
procedural obfuscation transformations, including obfuscation related
to the randomising function interfaces (the set and order of function
arguments). 
"""
from .. import interaction
from ..debug import *
from .utils import ObfuscationUnit, TransformType, generate_new_contents, NameSpace
from .identifier_analysis import IdentifierAnalyzer
from pycparser.c_ast import *
from typing import Iterable
import random, string, json


class FuncArgRandomiserTraverser(NodeVisitor):
    """Traverses an AST, finding function definitions and function specifications within
    the AST, and performs function argument randomisation, inserting spurious arguments
    and randomising the argument order depending on set options."""

    # Types and anonymous functions to generate their values
    # for spurious argument creation
    types = {
        "short": lambda: Constant("short", str(random.randint(-10, 10))),
        "int": lambda: Constant("int", str(random.randint(-10, 10))),
        "long": lambda: Constant("long", str(random.randint(-100, 100))),
        "long long": lambda: Constant(
            "long long", str(random.randint(-9223372036854775807, 9223372036854775807))
        ),
        "char": lambda: Constant(
            "char", f"'{random.choice(string.ascii_letters + string.digits)}'"
        ),
        "char *": lambda: Constant(
            "string",
            '"{}"'.format(
                "".join(
                    random.choices(
                        string.ascii_letters + string.digits + " ",
                        k=random.randint(0, 50),
                    )
                )
            ),
        ),
        "_Bool": lambda: Constant("_Bool", str(random.choice([1, 0]))),
        "float": lambda: Constant(
            "float",
            str(
                random.choice(
                    [
                        random.randint(-20, 20) * 0.25,
                        round(random.uniform(-10000000000, 10000000000), 4),
                    ]
                )
            ),
        ),
        "double": lambda: Constant(
            "double",
            str(
                random.choice(
                    [
                        random.randint(-200, 200) * 0.125,
                        round(random.uniform(-10000000000, 10000000000), 4),
                    ]
                )
            ),
        ),
    }

    def __init__(self, extra: int, probability: float, randomise: bool):
        """The constructor for the FuncArgRandomiserTraverser.

        Args:
            extra (int): The number of extra spurious arguments to insert
            probability (float): The independent probability that where possible, a
            program variable will be used to fill spurious function call arguments
            instead of a new constant value. Value from 0 to 1.
            randomise (bool): Whether to randomise function argument orders or not.
        """
        self.extra = extra
        self.variable_probability = probability
        self.randomise = randomise
        self.reset()

    def reset(self) -> None:
        """Reset the FuncArgRandomiserTraverser such that it can be used to traverse and
        mutate another AST, resetting its state variables and internal data structures."""
        self.func_args = dict()
        self.walk_num = 1
        self.current_func = None
        self.analyzer = IdentifierAnalyzer()

    def get_extra_args(self, idents: Iterable[str]) -> list[Decl]:
        """Given a list of function parameter identifier names, this function generates
        the required number of extra parameters, returning this is a list of declarations
        to append to the end of the function signature parameter list. Created parameters
        are ensured to be unique, and are of the form extra1, extra2, extra3, etc.

        Args:
            idents (Iterable[str]): The list of current parameter identifier names

        Returns:
            list[Decl]: The list of Decl subtrees for new spurious parameters.
        """
        extra_args = []
        basename = "extra"
        count = 0
        for _ in range(self.extra):
            argname = basename + str(count)
            count += 1
            while argname in idents:
                argname = basename + str(count)
                count += 1
            argtype = IdentifierType([random.choice(list(self.types.keys()))])
            typedecl = TypeDecl(argname, [], None, argtype)
            arg = Decl(argname, [], [], [], [], typedecl, None, None, None)
            extra_args.append(arg)
        return extra_args

    def visit_FuncDef(self, node: FuncDef) -> None:
        """Visit a FuncDef AST node, updating the current_func attribute to reflect
        the current function that is being parsed in the AST."""
        old_func = self.current_func
        self.current_func = node
        self.generic_visit(node)
        self.current_func = old_func

    def get_fname(self, node: Node) -> str | None:
        """Given an AST node corresponding to a function's type subtree, this function
        attempts to retrieve the relevant function name from the subtree, iteratively
        parsing through any pointer or array declaration nodes until a TypeDecl node
        is found, retrieving the declname.

        Args:
            node (Node): The function delcaration type subtree root node.

        Returns:
            str | None: Returns the function name from the subtree, or None if
            the subtree does not contain valid function information.
        """
        while isinstance(node, (PtrDecl, ArrayDecl)):
            node = node.type
        if isinstance(node, TypeDecl) and node.declname is not None:
            return node.declname
        else:
            return None

    def _mutate_non_empty_func(self, fdecl: FuncDecl, fname: str) -> None:
        """_summary_

        Args:
            fdecl (FuncDecl): _description_
            fname (str): _description_
        """
        # Get a list of defined identifiers and arguments
        defined_idents = self.analyzer.idents
        args = [
            arg.name for arg in fdecl.args.params if not isinstance(arg, EllipsisParam)
        ]

        # Generate extra spurious arguments - we do not modify ellipsis parameters
        # (for variadic functions) to ensure correctness - this is kept at the end.
        extra_args = self.get_extra_args(defined_idents.union(set(args)))
        before_change = fdecl.args.params.copy()
        if isinstance(fdecl.args.params[-1], EllipsisParam):
            ellipsis_arg = fdecl.args.params[-1]
            fdecl.args.params = fdecl.args.params[:-1] + extra_args
            if self.randomise:
                random.shuffle(fdecl.args.params)
            fdecl.args.params.append(ellipsis_arg)
        else:
            fdecl.args.params += extra_args
            if self.randomise:
                random.shuffle(fdecl.args.params)

        # Create a mapping from previous to new argument positions such that
        # function calls can be appropriately modified.
        mapping = {}
        for i, arg in enumerate(before_change):
            if isinstance(arg, EllipsisParam):
                mapping[i] = -1
            else:
                mapping[i] = fdecl.args.params.index(arg)
        self.func_args[fname] = (fdecl.args, mapping)

    def visit_FuncDecl(self, node: FuncDecl) -> None:
        """Visit a FuncDecl node, recording the function declaration and mutating
        it to add spurious arguments and randomise the function argument order. Variadic
        functions with EllipsisParam nodes are not manipulated. We first check for existing
        mutations (in the case of function signatures meaning repeats), and if not, any
        extra function args are stored in a dictionary such that later signatures or calls
        can use the same arguments.

        Args:
            node (FuncDecl): The FuncDecl node to mutate and traverse.
        """
        if self.walk_num != 1 or node.type is None:
            # We only record function declarations on the first walk.
            return NodeVisitor.generic_visit(self, node)

        defined_idents = self.analyzer.idents
        fdecl = node
        fname = self.get_fname(fdecl.type)
        if fname is None:
            return NodeVisitor.generic_visit(self, node)
        if fname == "main":
            return NodeVisitor.generic_visit(self, node)
        if fname not in self.func_args:
            if (
                fdecl.args is None
                or fdecl.args.params is None
                or len(fdecl.args.params) == 0
            ):
                # For empty functions, we create a new ParamList, generate random
                # extra args, and store them.
                extra_args = self.get_extra_args(defined_idents)
                fdecl.args = ParamList(extra_args)
                self.func_args[fname] = (fdecl.args, dict())
            elif (
                isinstance(fdecl.args.params[0], Typename)
                and fdecl.args.params[0].type.type.names[0] == "void"
            ):
                # Do not change functions with a void parameter.
                self.func_args[fname] = (fdecl.args, dict())
            else:
                # For non-empty functions, generate random args and store
                self._mutate_non_empty_func(fdecl, fname)
        else:
            fdecl.args = self.func_args[fname][0]
        NodeVisitor.generic_visit(self, node)

    def get_random_val(self, node: Node, var_types: dict[str, list[str]]) -> Constant:
        """Given the AST subtree root for a parameter, this function will
        generate a random constant value fitting that parameter such that
        function calls can be modified to fit spurious arguments.

        Args:
            node (Node): The parameter AST subtree root

        Returns:
            Constant: A random constant value of the same type as that parameter.
        """
        node_type = node.type.type.names[0]
        if node_type in var_types and random.random() <= self.variable_probability:
            return ID(random.choice(var_types[node_type]))
        return self.types[node.type.type.names[0]]()

    def get_variables_at_call(self, node: FuncCall) -> dict[str, list[str]]:
        """Given a function call AST subtree, this function creates a list of variables
        (of certain valid types) defined at that point in the program where the function is
        called.

        Args:
            node (FuncCall): The AST node (subtree root) corresponding to a function call.

        Returns:
            dict[str, list[str]]: This variables are returned as a dictionary where each key is
            a type e.g. "int", "long long", "double" and the values are a list of identifiers of
            variables of that type defined at this point in the program.
        """
        var_types = {}
        # Retrieve a list of variable identifiers defined at the function call.
        stmt = self.analyzer.get_stmt_from_node(node)
        vars = []
        for def_ in self.analyzer.get_definitions_at_stmt(stmt):
            if (
                def_[0] not in self.func_args
                and def_[0] != "main"
                and def_[1] == NameSpace.ORDINARY
            ):
                vars.append(def_)
        # Retrieve the types of relevant variable identifiers
        for var in vars:
            # Get the definition corresponding to the variable
            def_stmt = self.analyzer.get_last_ident_definition(stmt, var)
            definition = (def_stmt, *var)
            if def_stmt is None or definition not in self.analyzer.definition_uses:
                continue
            defs = self.analyzer.definition_uses[(def_stmt, *var)]
            if defs is None or len(defs) == 0 or type(defs[0][0]) != Decl:
                continue
            # Get the type of the definition and check if it is a valid arg type.
            # If so, add it to the dictionary.
            typedecl = defs[0][0].type
            if not isinstance(typedecl, TypeDecl) or not isinstance(
                typedecl.type, IdentifierType
            ):
                continue
            var_type = " ".join(typedecl.type.names)
            if var_type in self.types.keys():
                if var_type not in var_types:
                    var_types[var_type] = []
                var_types[var_type].append(var[0])
        # Return the dictionary of defined variables and their types.
        return var_types

    def visit_FuncCall(self, node: FuncCall) -> None:
        """Visit a FuncCall AST node, mutating the function call such that arguments
        are moved to match their new randomised order, and constant values of the correct
        type are inserted to match extra inserted spurious arguments.

        Args:
            node (FuncCall): The FuncCall AST node to traverse and mutate.
        """
        fname = node.name.name
        if self.walk_num == 1 or fname not in self.func_args:
            # We only mutate on the second walk of the abstract syntax tree (AST)
            return NodeVisitor.generic_visit(self, node)
        if node.args is None and self.extra > 0:
            node.args = ExprList([])  # Convert empty func calls
        elif node.args is None and self.extra == 0:
            return NodeVisitor.generic_visit(self, node)

        # Retrieve the stored function specification mapping
        new_args, mapping = self.func_args[fname]
        first_arg = new_args.params[0].type.type
        if isinstance(first_arg, IdentifierType) and first_arg.names[0] == "void":
            return NodeVisitor.generic_visit(self, node)
        call_args = [None] * (len(node.args.exprs) + self.extra)
        for before, after in mapping.items():
            if after == -1:  # Handle Ellipsis Param (variadic function)
                for i in range(len(node.args.exprs) - 1, before - 1, -1):
                    call_args[after] = node.args.exprs[i]
                    after -= 1
            else:
                call_args[after] = node.args.exprs[before]

        # Generate spurious function arguments
        var_types = self.get_variables_at_call(node)
        for i, arg in enumerate(call_args):
            if arg is not None:
                continue
            call_args[i] = self.get_random_val(new_args.params[i], var_types)
        node.args.exprs = call_args
        NodeVisitor.generic_visit(self, node)

    def visit_FileAST(self, node: FileAST) -> None:
        """Visit a FileAST node (the abstracy syntax tree root), performing two walks
        of the AST. The first walk is to find and mutate all possible function signatures,
        whereas the second walk is to correspondingly mutate all function calls; this is
        needed because pycparser doesn't store another information for just function
        signatures alone, and hence their usage can break single-traversal functionality.

        Args:
            node (FileAST): The FileAST node to traverse.
        """
        NodeVisitor.generic_visit(self, node)
        self.walk_num += 1
        NodeVisitor.generic_visit(self, node)
        self.reset()

    def transform(self, source: interaction.CSource) -> None:
        """Transform the given C source program, by first performing identifier usage
        analysis (to get a list of defined identifiers to avoid shadowing their names) and
        then traversing the AST.

        Args:
            source (interaction.CSource): The C source program to transform.
        """
        self.analyzer.load(source)
        self.analyzer.process()
        self.visit(source.t_unit)


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

    def __init__(self, extra_args: int, probability: float, randomise: bool):
        """The constructor for the FuncArgumentRandomiseUnit transformation.

        Args:
            extra_args (int): The number of extra spurious arguments to insert.
            probability (float): The independent probability that where possible, a
            program variable will be used to fill spurious function call arguments
            instead of a new constant value. Value from 0 to 1.
            randomise (bool): Whether to randomise argument orders or not.
        """
        self.extra_args = extra_args
        self.probability = probability
        self.randomise = randomise
        self.traverser = FuncArgRandomiserTraverser(extra_args, probability, randomise)

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        """Performs the function interface randomisation transformation on the given source program.

        Args:
            source (interaction.CSource): The source code to transform.

        Returns:
            interaction.CSource: The transformed source code.
        """
        self.traverser.transform(source)
        new_contents = generate_new_contents(source)
        return interaction.CSource(source.fpath, new_contents, source.t_unit)

    def to_json(self) -> str:
        """Converts the function argument randomisation unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps(
            {
                "type": str(__class__.name),
                "extra_args": self.extra_args,
                "probability": self.probability,
                "randomise": self.randomise,
            }
        )

    def from_json(json_str: str) -> "FuncArgumentRandomiseUnit":
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
        elif "probability" not in json_obj:
            log(
                "Failed to load RandomiseFuncArgs() - no probability provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["probability"], (float, int)):
            log(
                "Failed to load RandomiseFuncArgs() - given probability {} is not a valid number.".format(
                    json_obj["probability"]
                ),
                print_err=True,
            )
            return None
        elif json_obj["probability"] < 0 or json_obj["probability"] > 1:
            log(
                "Failed to load RandomiseFuncArgs() - given probability {} is not 0 <= p <= 1.".format(
                    json_obj["probability"]
                ),
                print_err=True,
            )
            return None
        elif "randomise" not in json_obj:
            log(
                "Failed to load RandomiseFuncArgs() - no randomise flag value provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["randomise"], bool):
            log(
                "Failed to load RandomiseFuncArgs() - randomise flag is not a valid Boolean value.",
                print_err=True,
            )
            return None
        return FuncArgumentRandomiseUnit(
            json_obj["extra_args"], json_obj["probability"], json_obj["randomise"]
        )

    def __str__(self) -> str:
        """Create a readable string representation of the FuncArgRandomiseUnit.

        Returns:
            str: The readable string representation.
        """
        extra_args_flag = f"extra={self.extra_args}"
        probability_flag = f"p={self.probability}"
        randomise_flag = f"random_order={'ENABLED' if self.randomise else 'DISABLED'}"
        return (
            f"RandomiseFuncArgs({extra_args_flag},{probability_flag},{randomise_flag})"
        )
