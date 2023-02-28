""" File: obfuscation/procedural_obfs.py
Implements classes (including obfuscation unit classes) for performing
procedural obfuscation transformations, including obfuscation related
to the randomising function interfaces (the set and order of function
arguments). 
"""
from .. import interaction
from ..debug import *
from .utils import ObfuscationUnit, TransformType, generate_new_contents, NewNewVariableUseAnalyzer
from pycparser.c_ast import *
from typing import Optional
import random, string, json


class FuncArgRandomiserTraverser(NodeVisitor):
    """TODO"""

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
            "char", f"'{random.choice(string.ascii_letters + string.digits)}'"
        ),
        "char *": lambda: Constant(
            "string",
            '"{}"'.format(
                "".join(
                    random.choices(
                        string.ascii_letters + string.digits + " ", k=random.randint(0, 50)
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

    def __init__(self, extra: int, randomise: bool):
        self.extra = extra
        self.randomise = randomise
        self.reset()

    def reset(self):
        self.func_args = dict()
        self.walk_num = 1
        self.current_func = None
        self.analyzer = NewNewVariableUseAnalyzer()

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
        old_func = self.current_func
        self.current_func = node
        self.generic_visit(node)
        self.current_func = old_func

    def get_fname(self, node): # TODO is this fix good enough?
        while isinstance(node, (PtrDecl, ArrayDecl)):
            node = node.type
        if isinstance(node, TypeDecl) and node.declname is not None:
            return node.declname
        else:
            return None

    def visit_FuncDecl(self, node):
        # TODO this code could use some major cleaning up!
        if self.walk_num != 1 or node.type is None:
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
                extra_args = self.get_extra_args(defined_idents.union(set(args)))
                before_change = fdecl.args.params.copy()
                if isinstance(fdecl.args.params[-1], EllipsisParam):
                    # TODO this is wrong - all arguments need to be
                    # in the same order, bogus arguments can be inserted
                    # at the start but other args need to be in the same
                    # order otherwise va_args stuff breaks
                    ellipsis_arg = fdecl.args.params[-1]
                    fdecl.args.params = fdecl.args.params[:-1] + extra_args
                    if self.randomise:
                        random.shuffle(fdecl.args.params)
                    fdecl.args.params.append(ellipsis_arg)
                else:
                    fdecl.args.params += extra_args
                    if self.randomise:
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
        if self.walk_num == 1 or fname not in self.func_args:
            return NodeVisitor.generic_visit(self, node)
        if node.args is None and self.extra > 0:
            node.args = ExprList([]) 
            # Convert empty function calls
        elif node.args is None and self.extra == 0:
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
        NodeVisitor.generic_visit(self, node)
        self.walk_num += 1
        NodeVisitor.generic_visit(self, node)
        self.reset()
        
    def transform(self, source: interaction.CSource) -> None:
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

    def __init__(self, extra_args: int, randomise: bool):
        self.extra_args = extra_args
        self.randomise = randomise
        self.traverser = FuncArgRandomiserTraverser(extra_args, randomise)

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        self.traverser.transform(source)
        new_contents = generate_new_contents(source)
        return interaction.CSource(source.fpath, new_contents, source.t_unit)

    def to_json(self) -> str:
        """Converts the function argument randomisation unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps({
            "type": str(__class__.name), 
            "extra_args": self.extra_args,
            "randomise": self.randomise,
        })

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
        return FuncArgumentRandomiseUnit(json_obj["extra_args"], json_obj["randomise"])

    def __str__(self) -> str:
        extra_args_flag = f"extra={self.extra_args}"
        randomise_flag = f"random_order={'ENABLED' if self.randomise else 'DISABLED'}"
        return f"RandomiseFuncArgs({extra_args_flag},{randomise_flag})"