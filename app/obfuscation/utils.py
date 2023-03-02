""" File: obfuscation/utils.py
Implements abstract base classes and basic functions for implementing 
obfuscation methods as ObfuscationUnit subclasses. Also implements
the identity obfuscation transformation as an example for how to
implement new obfuscation methods, and to provide the method itself. 
"""
from .. import interaction
from ..debug import *
from pycparser.c_ast import *
from pycparser.c_lexer import CLexer
from typing import Optional, Tuple, Type, Any, Iterable
import abc, enum, json, string, copy


# TODO - split this long utils file into several files
# e.g. "utils.py" (for ObjectFinder, generate_new_contents, TransformType, ObfuscationUnit, IdentityUnit)
#      "identifier_analysis.py" (for NewNewVariableAnalyzer)
#      "expression_analysis.py" (for ExpressionAnalyzer)


# TODO: clear down some of these old TODOs
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


class ObjectFinder(NodeVisitor):
    def __init__(self, classes: list[Type] | Type, attrs: list[str]):
        super(ObjectFinder, self).__init__()
        if isinstance(classes, (list, tuple, dict, set)):
            self.classes = tuple(classes)
        else:
            self.classes = classes
        self.none_checks = attrs
        self.reset()

    def reset(self):
        self.objs = set()
        self.parents = {}
        self.attrs = {}
        self.parent = None
        self.attr = None

    def generic_visit(self, node: Node) -> None:
        if isinstance(node, self.classes):
            if all(getattr(node, attr) is not None for attr in self.none_checks):
                self.objs.add(node)
                self.parents[node] = self.parent
                self.attrs[node] = self.attr
        this_parent = self.parent
        self.parent = node
        for child in node.children():
            self.attr = child[0]
            self.visit(child[1])
        self.parent = this_parent


def generate_new_contents(source: interaction.CSource) -> str:
    """Generates textual obfuscated file contents from a source's abstract syntax tree
    (AST), facilitating AST manipulation for source-to-source transformation.

    Args:
        source (interaction.CSource): The source object to generate contents for.

    Returns:
        (str) The generated file contents from the source's AST"""
    new_contents = ""
    for line in source.contents.splitlines():
        line_contents = line.strip()
        if line_contents.strip().startswith(("#", "%:", "??=")):
            new_contents += line + "\n"
    generator = interaction.PatchedGenerator()
    new_contents += generator.visit(source.t_unit)
    return new_contents


class TransformType(enum.Enum):
    """An Enum expression the different types/categories of obfuscation transformations that
    are implemented by the program. This is used to generate the GUI display appropriately."""

    LEXICAL = 1
    ENCODING = 2
    PROCEDURAL = 3
    STRUCTURAL = 4


class ObfuscationUnit(abc.ABC):
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

    @abc.abstractmethod
    def transform(self, source: interaction.CSource) -> interaction.CSource | None:
        return NotImplemented

    @abc.abstractmethod
    def to_json(self) -> str:
        return json.dumps({"transformation": "ObfuscationUnit"})

    @abc.abstractmethod
    def from_json() -> Optional["ObfuscationUnit"]:
        return NotImplemented

    @abc.abstractmethod
    def __str__(self):
        return "ObfuscationUnit()"


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

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        """Performs the identity transformation on the source.

        Args:
            source (interaction.CSource): The source code to transform.

        Returns:
            interaction.CSource: The transformed source code.
        """
        return source

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



class ExpressionAnalyzer(NodeVisitor):
    class SimpleType(Enum):
        INT = 0
        REAL = 1
        OTHER = 2

    class Ptr:
        def __init__(self, val):
            self.val = val

        def __eq__(self, other):
            return type(self) == type(other) and self.val == other.val

    class Array:
        def __init__(self, val):
            self.val = val

        def __eq__(self, other):
            return type(self) == type(other) and self.val == other.val

    # TODO centralise these and combine with the opaque predicate types to reduce repetition
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
        "unsigned short int",
        "signed short",
        "signed short int",
        "short",
        "short int",
        "unsigned long",
        "unsigned long int",
        "signed long",
        "signed long int",
        "long",
        "long int",
        "unsigned long long",
        "unsigned long long int",
        "signed long long",
        "signed long long int",
        "long long",
        "long long int",
        "size_t",
        "_Bool",
    ]
    VALID_REAL_TYPES = ["float", "double", "long double"]

    def __init__(self, t_unit: FileAST) -> None:
        super(ExpressionAnalyzer, self).__init__()
        self.t_unit = t_unit
        self.reset()

    def reset(self):
        self.type_aliases = []  # Stack of scopes of defined type aliases
        self.structs = []  # Stack of scopes of defined structs/union
        self.defined = []  # Stack of scopes of defined variables
        self.functions = {}
        self.params = {}
        self.in_param_list = False
        self.types = {None: self.SimpleType.OTHER}
        self.mutating = {None: False}
        self.processed = False

    def load(self, t_unit: FileAST) -> None:
        self.t_unit = t_unit
        self.processed = False

    def process(self) -> None:
        self.visit(self.t_unit)
        self.processed = True

    def is_type(self, expr: Node, type_) -> bool:
        if expr not in self.types:
            return type_ is None
        return self.types[expr] == type_
    
    def get_type(self, expr: Node) -> SimpleType | Ptr | Array | Struct | Union | None:
        if expr not in self.types:
            return None
        return self.types[expr]

    def is_mutating(self, expr: Node) -> bool:
        if expr not in self.mutating:
            return False
        return self.mutating[expr]

    def get_type_alias(self, name):
        for scope in self.type_aliases[::-1]:
            if name in scope:
                return scope[name]
        return None

    def get_var_type(self, name):
        for scope in self.defined[::-1]:
            if name in scope:
                return scope[name]
        return None

    def get_struct_type(self, name):
        for scope in self.structs[::-1]:
            if name in scope:
                return scope[name]
        return None

    def get_struct_field_type(self, struct, field):
        for decl in struct.decls:
            if decl.name is not None and decl.name == field and decl.type is not None:
                return self.convert_type(decl.type)
        return None

    def standard_coalesce_types(self, types):
        if any([t == self.SimpleType.OTHER for t in types]):
            return self.SimpleType.OTHER
        elif any([t == self.SimpleType.REAL for t in types]):
            return self.SimpleType.REAL
        elif all([isinstance(t, self.Array) for t in types]):
            # TODO not right but idk what it should be
            return self.Array(self.standard_coalesce_types([t.val for t in types]))
        elif any([isinstance(t, self.Ptr) for t in types]):
            # TODO also not 100% sure if this is correct - seems to be?
            vals = [t.val if isinstance(t, self.Ptr) else t for t in types]
            return self.Ptr(self.standard_coalesce_types(vals))
        else:
            return self.SimpleType.INT

    def get_func_type(self, name):
        if name in self.functions:
            return self.functions[name]
        return self.SimpleType.OTHER

    def visit_FileAST(self, node):
        self.type_aliases.append({})
        self.structs.append({})
        self.defined.append({})
        self.generic_visit(node)
        self.defined = self.defined[:-1]
        self.structs = self.structs[:-1]
        self.type_aliases = self.type_aliases[:-1]

    def visit_Compound(self, node):
        self.type_aliases.append({})
        self.structs.append({})
        if self.params is not None and len(self.params) != 0:
            self.defined.append(self.params)
            self.params = {}
        else:
            self.defined.append({})
        self.generic_visit(node)
        self.defined = self.defined[:-1]
        self.structs = self.structs[:-1]
        self.type_aliases = self.type_aliases[:-1]

    def visit_ParamList(self, node):
        self.params = {}
        self.in_param_list = True
        self.generic_visit(node)
        self.in_param_list = False

    def convert_type(self, node):
        if isinstance(node, PtrDecl):
            return self.Ptr(self.convert_type(node.type))
        elif isinstance(node, ArrayDecl):
            return self.Array(self.convert_type(node.type))
        elif isinstance(node, (TypeDecl, Typename)):
            return self.convert_type(node.type)
        elif isinstance(node, (IdentifierType, str)):
            # TODO whill names (plural) cause a problem here?
            if isinstance(node, IdentifierType):
                if node.names is None or len(node.names) == 0:
                    return self.SimpleType.OTHER
                name = "".join(node.names)
            else:
                name = node
            if name in self.VALID_INT_TYPES:
                return self.SimpleType.INT
            elif name in self.VALID_REAL_TYPES:
                return self.SimpleType.REAL
            alias = self.get_type_alias(name)
            if alias is not None:
                return alias
            return self.SimpleType.OTHER
        elif isinstance(node, (Struct, Union)):
            if node.decls is not None:
                return node
            if node.name is None:
                return self.SimpleType.OTHER
            struct = self.get_struct_type(node.name)
            if struct is not None:
                return struct
            return self.SimpleType.OTHER
        else:
            return self.SimpleType.OTHER

    def visit_FuncDef(self, node):
        if (
            node.decl is not None
            and node.decl.name is not None
            and node.decl.type is not None
            and node.decl.type.type is not None
        ):
            self.functions[node.decl.name] = self.convert_type(node.decl.type.type)
        self.generic_visit(node)

    def visit_Typedef(self, node):
        if node.name is not None and node.type is not None:
            self.type_aliases[-1][node.name] = self.convert_type(node.type)
        self.generic_visit(node)

    def visit_Decl(self, node):
        if node.name is not None and node.type is not None:
            if self.in_param_list:
                self.params[node.name] = self.convert_type(node.type)
                self.types[node] = self.params[node.name]
            else:
                self.defined[-1][node.name] = self.convert_type(node.type)
                self.types[node] = self.defined[-1][node.name]
        else:
            self.types[node] = self.SimpleType.OTHER
        self.mutating[node] = True
        self.generic_visit(node)

    def visit_UnaryOp(self, node):
        self.generic_visit(node)
        if node.expr is None or node.op is None:
            return
        if node.op in ["--", "p--", "++", "p++"]:
            self.types[node] = self.types[node.expr]
            self.mutating[node] = True
        elif node.op in ["-", "+", "~"]:
            self.types[node] = self.types[node.expr]
            self.mutating[node] = self.mutating[node.expr]
        elif node.op == "!":
            self.types[node] = self.SimpleType.INT
            self.mutating[node] = self.mutating[node.expr]
        elif node.op in ["_Sizeof", "sizeof", "alignof", "_Alignof"]:
            self.types[node] = self.SimpleType.INT
            if node.expr in self.mutating:
                self.mutating[node] = self.mutating[node.expr]
            else:  # getting size/alignment of a TypeDecl
                self.mutating[node] = False
        elif node.op == "&":
            self.types[node] = self.Ptr(self.types[node.expr])
            self.mutating[node] = self.mutating[node.expr]
        elif node.op == "*":
            expr_type = self.types[node.expr]
            if isinstance(expr_type, (self.Array, self.Ptr)):
                self.types[node] = expr_type.val
            else:
                self.types[node] = expr_type
            self.mutating[node] = self.mutating[node.expr]
        else:
            log(f"Unknown unary operator {node.op} encountered.")
            self.types[node] = self.SimpleType.OTHER
            self.mutating[node] = True  # Pessimistic Assumption

    def visit_BinaryOp(self, node):
        self.generic_visit(node)
        if node.left is None or node.right is None or node.op is None:
            return
        if node.op in ["+", "-", "*", "/"]:
            left_type = self.types[node.left]
            right_type = self.types[node.right]
            self.types[node] = self.standard_coalesce_types([left_type, right_type])
            self.mutating[node] = self.mutating[node.left] or self.mutating[node.right]
        elif node.op in ["%", "<<", ">>", "<", "<=", ">", ">=", "==", "!=", "&&", "||"]:
            self.types[node] = self.SimpleType.INT
            self.mutating[node] = self.mutating[node.left] or self.mutating[node.right]
        elif node.op in ["&", "|", "^"]:
            # TODO (double check) from what I can tell, must be integers?
            self.types[node] = self.SimpleType.INT
            self.mutating[node] = self.mutating[node.left] or self.mutating[node.right]
        else:
            log(f"Unknown binary operator {node.op} encountered.")
            self.types[node] = self.SimpleType.OTHER
            self.mutating[node] = True  # Pessimistic assumption

    def visit_TernaryOp(self, node):
        self.generic_visit(node)
        if node.iftrue is not None:
            self.types[node] = self.types[node.iftrue]
        elif node.iffalse is not None:
            self.types[node] = self.types[node.iffalse]
        self.mutating[node] = self.mutating[node.iftrue] or self.mutating[node.iffalse]

    def visit_Typename(self, node):
        self.generic_visit(node)
        if node.type is not None:
            # TODO patchwork change from self.types[node.type]
            # <- Is this correct?
            self.types[node] = self.convert_type(node.type)
        self.mutating[node] = False

    def visit_Cast(self, node):
        self.generic_visit(node)
        if node.to_type is not None:
            self.types[node] = self.types[node.to_type]
        if node.expr is not None:
            self.mutating[node] = self.mutating[node.expr]
        else:
            self.mutating[node] = False

    def visit_ArrayRef(self, node):
        self.generic_visit(node)
        name_type = self.SimpleType.OTHER if node.name is None else self.types[node.name]
        sub_type = self.SimpleType.OTHER if node.subscript is None else self.types[node.subscript]
        is_name_arr = isinstance(name_type, (self.Array, self.Ptr))
        is_sub_arr = isinstance(sub_type, (self.Array, self.Ptr))
        if not is_name_arr and not is_sub_arr:
            self.types[node] = self.SimpleType.OTHER
        elif is_name_arr and is_sub_arr:
            self.types[node] = self.SimpleType.OTHER  # pessimistic assumpion ?
        elif is_name_arr:
            self.types[node] = name_type.val
        else:
            self.types[node] = sub_type.val
        mutating = False
        if node.name is not None:
            mutating = mutating or self.mutating[node.name]
        if node.subscript is not None:
            mutating = mutating or self.mutating[node.subscript]
        self.mutating[node] = mutating

    def visit_Assignment(self, node):
        self.generic_visit(node)
        if node.lvalue is not None:
            self.types[node] = self.types[node.lvalue]
        self.mutating[node] = True

    def visit_Enum(self, node):
        self.generic_visit(node)
        if node.name is not None:
            # TODO double check: Enum's are always integer (integral) type I think?
            self.types[node] = self.SimpleType.INT
        self.mutating[node] = False

    def visit_FuncCall(self, node):
        self.generic_visit(node)
        if node.name is not None and node.name.name is not None:
            self.types[node] = self.get_func_type(node.name.name)
        self.mutating[node] = True  # Pessimistic assumption (e.g. globals)

    def visit_Struct(self, node):
        # TODO removed name none check here for anon tags - is fine?
        if node.decls is not None:
            self.structs[-1][node.name] = node
            self.types[node] = node
            self.mutating[node] = True
        else:
            self.types[node] = self.get_struct_type(node.name)
            self.mutating[node] = False

    def visit_Union(self, node):
        # TODO removed name none check here for anon tags - is fine?
        if node.decls is not None:
            self.structs[-1][node.name] = node
            self.types[node] = node
            self.mutating[node] = True
        else:
            self.types[node] = self.get_struct_type(node.name)
            self.mutating[node] = False

    def visit_StructRef(self, node):
        self.generic_visit(node)
        if (
            node.type is not None
            and node.name is not None
            and node.field is not None
            and node.field.name is not None
        ):
            if node.type == ".":
                struct_type = self.types[node.name]
                if isinstance(struct_type, (Struct, Union)):
                    self.types[node] = self.get_struct_field_type(
                        struct_type, node.field.name
                    )
                else:
                    self.types[node] = self.SimpleType.OTHER
            elif node.type == "->":
                struct_type = self.types[node.name]
                if isinstance(struct_type, (self.Ptr, self.Array)):
                    struct_type = struct_type.val
                if isinstance(struct_type, (Struct, Union)):
                    self.types[node] = self.get_struct_field_type(
                        struct_type, node.field.name
                    )
                else:
                    self.types[node] = self.SimpleType.OTHER
        mutating = False
        if node.name is not None:
            mutating = mutating or self.mutating[node.name]
        if node.field is not None:  # TODO can this be an expr? I don't think so?
            mutating = mutating or self.mutating[node.field]
        self.mutating[node] = mutating

    def visit_Constant(self, node):
        self.generic_visit(node)
        if node.type is not None:
            self.types[node] = self.convert_type(node.type)
        self.mutating[node] = False

    def visit_ID(self, node):
        self.generic_visit(node)
        if node.name is not None:
            self.types[node] = self.get_var_type(node.name)
        self.mutating[node] = False

    def visit_InitList(self, node):
        self.generic_visit(node)
        mutating = False
        if node.exprs is not None:
            # Type cannot be determined from the init list (e.g. an empty list)
            # (Hence an init list can only be used in declarations)
            for expr in node.exprs:
                mutating = mutating or self.mutating[expr]
        self.mutating[node] = mutating

    def visit_ExprList(self, node):
        self.generic_visit(node)
        mutating = False
        if node.exprs is not None:
            # Type of an expr list cannot be sufficiently represented in this
            # abstraction, but is not needed, so it is ignored.
            for expr in node.exprs:
                mutating = mutating or self.mutating[expr]
        self.mutating[node] = mutating

    def visit_CompoundLiteral(self, node):
        self.generic_visit(node)
        if node.type is not None:
            self.types[node] = self.convert_type(node.type)
        else:
            self.types[node] = self.SimpleType.OTHER
        if node.init is not None:
            self.mutating[node] = self.mutating[node.init]
        else:
            self.mutating[node] = False

    def visit_NamedInitializer(self, node):
        self.generic_visit(node)
        if node.expr is not None:
            self.types[node] = self.types[node.expr]
            self.mutating[node] = True  # TODO check this?


# TODO a lot of ident parsing is done in the wrong order through the AST, which will
# give random stuff in the wrong order - not a huge deal but would be nice to fix


class TypeKinds(enum.Enum):
    # TODO turns out these are actually called "name spaces",
    STRUCTURE = 0  # TODO turns out this should be 'tag'
    LABEL = 1
    NONSTRUCTURE = 2  # TODO turns out this should be 'ordinary'/'other'


class NameSpace(enum.Enum):
    LABEL = 0
    TAG = 1
    MEMBER = 2
    ORDINARY = 3


Scope = Compound | FileAST
Identifier = Tuple[str,NameSpace]
Location = Tuple[Node, str | Tuple[str, ...]]


class NewNewVariableUseAnalyzer(NodeVisitor):
    
    def __init__(self, source: interaction.CSource | None = None) -> None:
        """A constructor for the variable use analyzer, initialising
        variables and data structures used during and after analysis.

        Args:
            source (interaction.CSource | None, optional): The source file
            to analyze. Defaults to None, where it can be passed in later 
            using the `load()` function.
        """
        # Construct membership sets/dicts
        self.stmts = set()  # Set of all program statements
        self.idents = set()  # Set of all _defined_ program idents
        self.functions = set()  # Set of all functions
        self.typedefs = set()  # Set of all types that have been typedef'd
        self.funcspecs = {} # Dict mapping functions to all their function specifications
        self.labels = {}  # Dict mapping a function to all its labels.
        self.gotos = {}  # Dict mapping a function to all its gotos (so they can 
                         # be backfilled with labels)
        self.struct_members = {}  # Dict mapping a struct/union to all of its
                                  # members, so that they can be uniquely identified
        
        # Dicts for identifying statement identifier definitions and usage
        self.stmt_usage = {}  # Dict of identifier usage in stmts
        self.stmt_definitions = {}  # Dict of identifier definitions in stmts
        self.definition_uses = {}  # Dictionary mapping (statement, ident, namespace)
                                  #  triples to all locations that use it.
        
        # Program structure tree dicts for easy traversal
        self.compound_children = {}  # Maps compound to child compounds
        self.compound_parent = {}  # Maps all compounds to their parent compound
        self.stmt_compound_map = {}  # Maps all stmt nodes to the compound they are part of
        self.compound_stmt_map = {}  # Maps all compounds to the statements they contain
        self.node_stmt_map = {}  # Maps all AST nodes to the statement they are part of
        self.stmt_func_map = {}  # Maps all stmt nodes to the function they are part of
        
        # Variables for tracking current state while analyzing
        self._current_definitions = []
        self._current_function = None
        self._current_compound = None
        self._current_struct = None
        self._current_stmt = None

        # Misc. variables related to the Analyzer's state
        self.source = source
        self.processed = False
        self.expression_analyzer = ExpressionAnalyzer(source.t_unit if source is not None else None)

    def _stmt_wrapper(func: Callable) -> Callable:
        """A wrapper for node traversal functions that checks whether the node
        is a statement, and based on the result, updates a variety of statement
        tracking values (dicts for traversing the program structure as well as 
        tracking of the current statement).

        Args:
            func (Callable): The function to be wrapped

        Returns:
            Callable: The wrapped function
        """
        def wrapper(self, node: Node, *args, **kwargs) -> Any:
            is_stmt = self.is_stmt(node)
            if is_stmt:
                prev_stmt = self._current_stmt
                self._current_stmt = node
                self.stmt_compound_map[node] = self._current_compound
                self.stmt_func_map[node] = self._current_function
                if self._current_compound is not node:
                    self.compound_stmt_map[self._current_compound].append(node)
            self.node_stmt_map[node] = self._current_stmt
            result = func(self, node, *args, **kwargs)
            if is_stmt:
                self._current_stmt = prev_stmt
            return result
        
        return wrapper
    
    def load(self, source: interaction.CSource) -> None:
        """Loads the given source file, readying it to be analysed.

        Args:
            source (interaction.CSource): The source file to load.
        """
        self.source = source
        self.expression_analyzer.load(source.t_unit)
        self.processed = False
    
    def process(self) -> None:
        """ Processes the currently loaded source file, analyzing it. """
        if self.source is None or self.processed:
            return
        self.expression_analyzer.process()
        self.visit(self.source.t_unit)
        self.processed = True
        
    def get_stmt_definitions(self, stmt: Node) -> list[Identifier]:
        """ Returns a list of identifier definitions made in a statement as are 
        known to the analyzer.

        Args:
            stmt (Node): The AST root node of the statement subtree.

        Returns:
            list[Identifier]: A list of identifiers (name and namespace pairs).
        """
        return self.stmt_definitions[stmt]
    
    def get_stmt_usage(self, stmt: Node) -> list[Identifier]:
        """ Returns a list of identifier usages made in a statement as are
        known to the analyzer.

        Args:
            stmt (Node): The AST root node of the statement subtree.

        Returns:
            list[Identifier]: A list of identifiers (name and namespace pairs).
        """
        return self.stmt_usage[stmt]
    
    def get_stmt_compound(self, stmt: Node) -> Scope:
        """ Returns the scope (compound or FileAST) that a given statement
        is located in as is known to the analyzer.

        Args:
            stmt (Node): The AST root node of the statement subtree.

        Returns:
            Scope: The Compound or FileAST the statement is a child of.
        """
        return self.stmt_compound_map[stmt]

    # TODO replaced `get_func_from_stmt` with this
    #  -- Propagate these changes to the rest of my program
    def get_stmt_func(self, stmt: Node) -> FuncDef | None:
        """ Returns the function that a given statement is located in
        as is known to the analyzer.

        Args:
            stmt (Node): The AST root node of the statement subtree.

        Returns:
            FuncDef | None: The function the statement is in, or None if
            the statement is not in a function.
        """
        return self.stmt_func_map[stmt]

    def get_stmt_from_node(self, ast_node: Node) -> Node:
        """ Returns the root AST node of the statement that the provided AST
        node is located within, as is known to the analyzer.

        Args:
            ast_node (Node): The AST node to get the statement of.

        Returns:
            Node: The root AST node of the containing statement.
        """
        return self.node_stmt_map[ast_node]

    def is_stmt(self, ast_node: Node) -> bool:
        """ Returns whether the given AST node is the root AST node of some
        statement in the program body or not, as is known to the analyzer.

        Args:
            stmt_node (Node): The AST node to check.

        Returns:
            bool: True if the AST node is a statement node, False otherwise.
        """
        return ast_node in self.stmts
    
    def get_compounds_in_subtree(self, compound: Scope) -> list[Compound]:
        """ Returns a list of all compounds that are descendants of the given
        compound in the compound's AST subtree, utilising a BFS approach.

        Args:
            compound (Scope): The compound to get the descendents of.

        Returns:
            list[Compound]: A list of Compound nodes in the given compound's AST subtree.
        """
        compounds = []
        frontier = [compound]
        while len(frontier) > 0:
            compound = frontier[0]
            frontier = frontier[1:]
            compounds.append(compound)
            for child, _ in self.compound_children[compound]:
                frontier.append(child)
        return compounds
    
    # TODO removed self.get_functions() - will this cause problems?
    
    def _coalesce_indexes(self, compound: Scope, from_stmt : Node | None, to_stmt: Node | None) -> Tuple[int,int]:
        """This function coalesces statment `from_index` and `to_index` values given
        a compound. If the values are null, then the start index (0) and end index + 1
        (len(compound)) are used respectively. Otherwise, the index of the given
        statement is found.

        Args:
            compound (Scope): The compound object to coalesce indexes of.
            from_stmt (Node | None): The statement to index from, if any.
            to_stmt (Node | None): The statement to index to (inclusive), if any.

        Returns:
            Tuple[int,int]: A tuple (from_index, to_index) for the given values.
        """
        if from_stmt is None:
            from_index = 0
        else:
            from_index = self.compound_stmt_map[compound].index(from_stmt)
        if to_stmt is None:
            to_index = len(self.compound_stmt_map[compound])
        else:
            to_index = self.compound_stmt_map[compound].index(to_stmt) + 1
        return (from_index, to_index)
    
    def get_scope_definitions(self, compound: Scope, from_stmt: Node | None = None, to_stmt: Node | None = None) -> list[Identifier]:
        """ Gets all identifier definitions of statements within a scope,
        optionally only finding definitions between a certain statement and
        another statement in the compound.

        Args:
            compound (Scope): The Compound/FileAST to search within. 
            from_stmt (Node | None, optional): The AST root node of the
            subtree of the statement to start from. Defaults to None, 
            indicating the first statement in the scope.
            to_stmt (Node | None, optional): The AST root node of the
            subtree of the statement to end at (inclusive). Defaults to
            None, indicating the last statement in the scope. 

        Returns:
            list[Identifier]: A list of identifiers (name and namespace pairs).
        """
        from_index, to_index = self._coalesce_indexes(compound, from_stmt, to_stmt)
        definitions = set()
        for i in range(from_index, to_index):
            stmt = self.compound_stmt_map[compound][i]
            definitions = definitions.union(self.stmt_definitions[stmt])
        return definitions
    
    def get_scope_usage(self, compound: Scope, from_stmt: Node | None = None, to_stmt: Node | None = None) -> list[Identifier]:
        """ Gets all identifier usages of statements within a scope,
        optionally only finding usages between a certain statement and
        another statement in the compound.

        Args:
            compound (Scope): The Compound/FileAST to search within. 
            from_stmt (Node | None, optional): The AST root node of the
            subtree of the statement to start from. Defaults to None, 
            indicating the first statement in the scope.
            to_stmt (Node | None, optional): The AST root node of the
            subtree of the statement to end at (inclusive). Defaults to
            None, indicating the last statement in the scope. 

        Returns:
            list[Identifier]: A list of identifiers (name and namespace pairs).
        """
        from_index, to_index = self._coalesce_indexes(compound, from_stmt, to_stmt)
        usage = set()
        for i in range(from_index, to_index):
            stmt = self.compound_stmt_map[compound][i]
            usage = usage.union(self.stmt_usage[stmt])
        return usage

    def get_nested_scope_definitions(self, compound: Scope, from_stmt: Node | None = None, to_stmt: Node | None = None) -> list[Identifier]:
        """ Gets all identifier definitions of statements within an entire scope 
        subtree, finding definitions within its scope and all its child scopes. 
        Optionally will only recursively find definitions between given statements.

        Args:
            compound (Scope): The Compound or FileAST to search within.
            from_stmt (Node | None, optional): The AST root node of 
            the subtree of the statement to search from. Defaults to None,
            indicating the first statement in the scope.
            to_stmt (Node | None, optional): The AST root node of the
            subtree of the statement to search up to (inclusive). Defaults to 
            None,  indicating the last statement in the scope.

        Returns:
            list[Identifier]: A list of identifiers (name and namespace pairs).
        """
        definitions = self.get_scope_definitions(compound, from_stmt, to_stmt)
        from_index, to_index = self._coalesce_indexes(compound, from_stmt, to_stmt)
        for child, stmt_node in self.compound_children[compound]:
            index = self.compound_stmt_map[compound].index(stmt_node)
            if index < from_index or index > to_index:
                continue
            child_definitions = self.get_nested_scope_definitions(child)
            definitions = definitions.union(child_definitions)
        return definitions 

    def get_nested_scope_usage(self, compound: Scope, from_stmt: Node | None = None, to_stmt: Node | None = None) -> list[Identifier]:
        """ Gets all identifier usages of statements within an entire scope 
        subtree, finding usages within its scope and all its child scopes. 
        Optionally will only recursively find usages between given statements.

        Args:
            compound (Scope): The Compound or FileAST to search within.
            from_stmt (Node | None, optional): The AST root node of 
            the subtree of the statement to search from. Defaults to None,
            indicating the first statement in the scope.
            to_stmt (Node | None, optional): The AST root node of the
            subtree of the statement to search up to (inclusive). Defaults to 
            None,  indicating the last statement in the scope.

        Returns:
            list[Identifier]: A list of identifiers (name and namespace pairs).
        """
        usages = self.get_scope_usage(compound, from_stmt, to_stmt)
        from_index, to_index = self._coalesce_indexes(compound, from_stmt, to_stmt)
        for child, stmt_node in self.compound_children[compound]:
            index = self.compound_stmt_map[compound].index(stmt_node)
            if index < from_index or index > to_index:
                continue
            child_usages = self.get_nested_scope_usage(child)
            usages = usages.union(child_usages)
        return usages
        
    def _get_scope_path(self, compound: Scope) -> list[Scope]:
        """ TODO DOCSTRING """
        scope_path = [compound]
        while compound is not None:
            compound = self.compound_parent[compound]
            scope_path.append(compound) 
        scope_path = scope_path[:-1]
        return scope_path
        
    def get_definitions_at_stmt(self, stmt: Node, compound: Scope | None = None) -> list[Identifier]:
        """ Given a statement, this will find all the identifiers that
        are currently defined by the end of that statement (inclusive).

        Args:
            stmt (Node): The AST root node of the subtree of the statement
            to search up to.
            compound (Scope | None, optional): The compound containing the 
            given statement. Defaults to None, which will make the analyzer
            manually retrieve it. This option can be used to avoid repeat
            calculations if you already know the scope.

        Returns:
            list[Identifier]: A list of identifiers (name and namespace pairs).
        """
        # Retrieve scope information
        if compound is None:
            compound = self.get_stmt_compound(stmt)
        scope_path = self._get_scope_path(compound)
        if len(scope_path) == 1:
            return self.get_scope_definitions(scope_path[0], None, stmt)

        # Compute definitions for each scope up to the statement, and union
        definitions = set()
        for i, scope in [s for s in enumerate(scope_path)][-1:0:-1]:
            child = scope_path[i - 1]
            compound_stmt = [c[1] for c in self.compound_children[scope] if c[0] == child]
            if len(compound_stmt) == 0:
                compound_stmt = None
            else:
                compound_stmt = compound_stmt[0]
            scope_defs = self.get_scope_definitions(scope, None, compound_stmt)
            definitions = definitions.union(scope_defs)
        
        # Handle last (i.e. current) scope
        scope_defs = self.get_scope_definitions(scope_path[0], None, stmt)
        definitions = definitions.union(scope_defs)
        return definitions
            
    def get_last_ident_definition(self, ast_node: Node, ident: Identifier) -> Node | None:
        """ Given an AST node corresponding to some part of the abstract 
        syntax tree for the analysed program, this method searches backwards
        from the given node to find the last instance of an identifier's
        definition, if such a definition exists.

        Args:
            ast_node (Node): The AST node to check from.
            ident (Identifier): The identifier (name & namespace) to look for.

        Returns:
            Node | None: Some AST node corresponding to the statement (i.e.
            the root of that statement's AST subtree) where the given 
            identifier was last defined, or None if the identifier is not
            defined at the given point in the program.
        """
        stmt = self.get_stmt_from_node(ast_node)
        compound = self.get_stmt_compound(stmt)
        # Recursively search backwards through scopes and find last definition instance
        scope_path = self._get_scope_path(compound)
        to_stmt = stmt
        for i, scope in enumerate(scope_path):
            from_index, to_index = self._coalesce_indexes(scope, None, to_stmt)
            for j in range(from_index, to_index):
                stmt = self.compound_stmt_map[scope][j]
                if ident in self.stmt_definitions[stmt]:
                    return stmt
            # We search the parent scope up to the statement corresponding to the
            # child scope (to avoid searching the whole scope)
            if i >= len(scope_path) - 1:
                continue
            parent = scope_path[i+1]
            to_stmt = [c[1] for c in self.compound_children[parent] if c[0] == scope]
            if len(to_stmt) == 0:
                to_stmt = None
            else:
                to_stmt = to_stmt[0]
        return None
        

    def get_usage_from_stmt(self, stmt: Node, compound: Scope | None = None) -> list[Identifier]:
        """ Given a statement, this will find all the identifiers that
        are used in and after the end of that statement (towards the 
        end of the statement's scope).

        Args:
            stmt (Node): The AST root node of the subtree of the statement
            to search up from (inclusive).
            compound (Scope | None, optional): The compound containing the 
            given statement. Defaults to None, which will make the analyzer
            manually retrieve it. This option can be used to avoid repeat
            calculations if you already know the scope.

        Returns:
            list[Identifier]: A list of identifiers (name and namespace pairs).
        """
        if compound is None:
            compound = self.get_stmt_compound(stmt)
        return self.get_nested_scope_usage(compound, stmt, None)
    
    def get_required_identifiers(self, node: Node, namespace: NameSpace, compound: Scope | None = None, function: FuncDef | None = None, include_after: bool = False) -> set[Identifier]:
        """Retrieves a list of identifiers that are required to stay defined at 
        the given AST node, of the specified namespace group. This includes:
            - Those defined in the same scope, which cannot be redefined
              (except any other struct members defined in the *same statement*,
              which have to be handled seperately).
            - Those used in descendant scopes from the statement onwards.
            - Any label identifiers within the same function

        Args:
            node (Node): The AST node of the point in the program to search from.
            namespace (NameSpace): The namespace group of idents being checked for.
            compound (Scope | None, optional): The compound (scope) the node is 
            located within. Defaults to None, where it is calculated.
            function (FuncDef | None, optional): The function the node is
            located within, if any. Defaults to None, where it is calculated.
            include_after (bool): Whether to include identifiers defined in the
            same scope that come after this statement or not. Defaults to False

        Returns:
            list[Identifier]: A list of identifiers (name and namespace pairs).
        """
        stmt = self.get_stmt_from_node(node)
        defined = set(self.get_usage_from_stmt(stmt))
        #print("USAGE:", set((x[0], x[1][0]) if isinstance(x[1], Tuple) else x for x in defined)) # TODO IMPORTANT COMEHERE REMOVE
        if compound is None:
            compound = self.get_stmt_compound(stmt)
        if include_after:
            scope_definitions = self.get_scope_definitions(compound)
        else:
            scope_definitions = self.get_scope_definitions(compound, None, stmt)
        defined = defined.union(scope_definitions)
        #print("IN SCOPE:", set((x[0], x[1][0]) if isinstance(x[1], Tuple) else x for x in scope_definitions)) # TODO IMPORTANT COMEHERE REMOVE
        if function is None:
            function = self.get_stmt_func(stmt)
        if function is not None:
            defined = defined.union(
                set((n.name, NameSpace.LABEL) for n in self.labels[function])
            )
        members_defined = self.get_stmt_definitions(stmt)
        members_defined = set(x for x in members_defined if isinstance(x[1], Tuple))
        defined = defined.difference(members_defined)
        defined = set(x[0] for x in defined if x[1] == namespace)
        return defined

    def _find_new_ident(self, exclude: Iterable[str]) -> str:
        """Given a list of identifiers to avoid, this function will iteratively 
        attempt to generate a new identifier that is not in this list (or a keyword).

        Args:
            exclude (Iterable[str]): The list of identifier names to avoid.

        Returns:
            str: The newly generated identifier.
        """
        keywords = set([kw.lower() for kw in CLexer.keywords])
        new_ident = "a"
        count = 0
        num_letters = len(string.ascii_letters)
        while new_ident in exclude or new_ident.lower() in keywords:
            count += 1
            new_ident = ""
            cur_num = count
            while cur_num >= 0:
                new_ident += string.ascii_letters[cur_num % num_letters]
                cur_num = cur_num // num_letters
                if cur_num == 0:
                    break
        return new_ident
            
    # TODO swapped get_unique_identifier and get_new_identifier names 
    #  -- Propagate this to the rest of my codebase!
    def get_new_identifier(self, node: Node, namespace: NameSpace, compound: Scope | None = None, function: FuncDef | None = None, exclude: Iterable[str] | None = None) -> str:
        """Given an AST node and a namespace (identifier type), this function gets a new
        identifier to use that will not conflict with existing identifiers defined 
        before / at / from this node. Note that these will not necessarily be unique
        and may shadow an existing identifier.

        Args:
            node (Node): The AST node to search from.
            namespace (NameSpace): The namespace (type/group) of the new identifier.
            compound (Scope | None, optional): The scope containing the node. Defaults to 
            None, where it is automatically calculated.
            function (FuncDef | None, optional): The function containing the node. 
            Defaults to None, where it is automatically calculated if such a function exists.
            exclude (Iterable[Identifier] | None, optional): A list of additional identifiers
            to exclude. Defaults to None.

        Returns:
            str: The new identifier that can be used at this node.
        """
        disallowed = self.get_required_identifiers(node, namespace, compound, function)
        if exclude is not None:
            disallowed = disallowed.union(set(exclude))
        return self._find_new_ident(disallowed)
    
    def get_unique_identifier(self, exclude: Iterable[str] | None = None) -> str:
        """ Generates an entirely new unique identifier that is not used anywhere
        else in the program, for any namespace.

        Args:
            exclude (Iterable[str] | None, optional): An optional list of additional
            identifiers to exclude from generating. Defaults to None.

        Returns:
            str: The new unique identifier that does not exist in the program.
        """
        exclude = [] if exclude is None else exclude
        exclude = self.idents.union(set(exclude))
        return self._find_new_ident(exclude)
    
    def change_ident(self, node: Node, name: str, namespace: NameSpace, new_name: str) -> None:
        """ Changes a specific instance (definition) of an identifier to use
        a different name, updating all of that identifier's usages throughout
        the program to propagate and cascade this change. Also updates the analyzer
        tracking structures to allow further analyzer use.  

        Args:
            node (Node): The AST node where the identifier was defined.
            name (str): The old name of the identifier.
            namespace (NameSpace): The namespace of the identifier.
            new_name (str): The new name to use for the identifier, replacing the old name.
        """
        # Update AST attributes for all locations referring to this specific
        # definition, to propagate identifier changes.
        stmt_node = self.get_stmt_from_node(node)
        if isinstance(stmt_node, FuncDef) and name in self.funcspecs:
            self.funcspecs[new_name] = self.funcspecs[name]
            self.funcspecs[name] = None
        for (change_node, attr) in self.definition_uses[(stmt_node, name, namespace)]:
            if isinstance(attr, tuple):
                attr_name = attr[0]
                cur_obj = getattr(change_node, attr_name)
                for attr_index in attr[1:-1]:
                    cur_obj = cur_obj[attr_index]
                cur_obj[attr[-1]] = new_name
            else:
                setattr(change_node, attr, new_name)
        # Update processed tracking variables accordingly to allow further analysis
        ident = (name, namespace)
        new_ident = (new_name, namespace)
        if ident in self.stmt_usage[stmt_node]:
            self.stmt_usage[stmt_node].remove(ident)
            self.stmt_usage[stmt_node].add(new_ident)
        if ident in self.stmt_definitions[stmt_node]:
            self.stmt_definitions[stmt_node].remove(ident)
            self.stmt_definitions[stmt_node].add(new_ident)
        for (node, _) in self.definition_uses[(stmt_node, name, namespace)]:
            other_stmt_node = self.get_stmt_from_node(node)
            if ident in self.stmt_usage[other_stmt_node]:
                self.stmt_usage[other_stmt_node].remove(ident)
                self.stmt_usage[other_stmt_node].add(new_ident)
        old_ident_def = (stmt_node, name, namespace)
        new_ident_def = (stmt_node, new_name, namespace)
        self.definition_uses[new_ident_def] = self.definition_uses[old_ident_def]
        self.definition_uses.pop(old_ident_def)
    
    def update_funcspecs(self) -> None:
        """ Performs a backfill of function specifications, updating any incomplete
        function specifications to the final, changed specifications of their full
        function definitions after all analysis and changing of identifiers has been
        completed. Defined as a seperate function rather than an implicit behaviour
        to help reduce programming complexity somewhat.
        """
        for func_name, funcspecs in self.funcspecs.items():
            if funcspecs is None:
                continue
            new_func_spec = None
            func_spec_found = False
            for node in self.source.t_unit.ext:
                if isinstance(node, FuncDef) and node.decl.name == func_name:
                    new_func_spec = node.decl.type.args
                    func_spec_found = True
                    break
            if not func_spec_found:
                continue
            for funcspec in funcspecs:
                funcspec.type.args = copy.deepcopy(new_func_spec)
                funcspec.name = func_name
                typedecl = self._get_typedecl(funcspec.type.type)
                if typedecl is not None:
                    typedecl.declname = func_name
    
    def _record_stmt(self, stmt_node: Node) -> None:
        """ Records a node as a statement, updating analysis tracking
        values and structures to reflect this fact.

        Args:
            stmt_node (Node): The root node of the subtree corresponding to
            a statement.
        """
        self.stmts.add(stmt_node)
        self.stmt_usage[stmt_node] = set()
        self.stmt_definitions[stmt_node] = set()
        self.node_stmt_map[stmt_node] = stmt_node
        self.stmt_func_map[stmt_node] = self._current_function
    
    # TODO changed _current_definitions to only store node (not locations
    #   -- Might need to remember to propagate some parts of this change
    def _get_last_definition(self, name: str, namespace: NameSpace) -> Node | None:
        """ Given an identifier (name and namespace), this function iterates
        backwards through the current list of scoped definitions to find which
        definition that applies to, returning the definition node.

        Args:
            name (str): The name of the identifier
            namespace (NameSpace): The namespace of the identifier

        Returns:
            Node | None: The AST node of the last definition of the identifier.
            None if no such definition exists in the current scope stack. 
        """
        if namespace == NameSpace.LABEL:
            labels = self.labels[self._current_function]
            for label in labels:
                if label.name == name:
                    return self.get_stmt_from_node(label)
            return None
        for i, scope in enumerate(self._current_definitions[::-1]):
            if (name, namespace) in scope:
                return scope[(name, namespace)]
        return None
    
    def _get_typedecl(self, node: Node) -> TypeDecl | None:
        """ Recursively iterates through the type attributes of AST nodes in
        order to traverse pointer declaration or array declaration components
        and find the base type declaration.

        Args:
            node (Node): The node to get the typedecl of.

        Returns:
            TypeDecl | None: The typedecl if one exists, or None otherwise.
        """
        if node is None:
            return None
        if isinstance(node, (PtrDecl, ArrayDecl)):
            return self._get_typedecl(node.type)
        elif isinstance(node, TypeDecl):
            return node
        return None
    
    def _record_definition(self, node: Node, name: str, locations: list[Location], namespace: NameSpace, alt_scope: Scope | None = None) -> None:
        """ Records an instance of an identifier definition at a given AST 
        node, such that this can be tracked and used by the analyzer.

        Args:
            node (Node): The AST node where the definition occurred.
            name (str): The name of the identifier that was defined.
            locations (list[Location]): A list of locations (nodes and 
            their attributes) where the definition occurs, such that the 
            identifier can be updated by changing these attributes.
            namespace (NameSpace): The namespace of the defined identifier.
            alt_scope (Scope | None, optional): An alternate scope to use
            instead of the top of the current scope stack. Defaults to None.
            Useful if parsing out of order (e.g. parameter declarations).
        """
        node = self.get_stmt_from_node(node)
        if alt_scope is None:
            scope = self._current_definitions[-1]
        else:
            scope = alt_scope
        scope[(name, namespace)] = node
        self.definition_uses[(node, name, namespace)] = locations
        self.stmt_definitions[node].add((name, namespace))
        self.idents.add(name)
        
    def _record_usage(self, node: Node, name: str, locations: list[Location], namespace: NameSpace) -> None:
        """ Records an instance of an identifier's usage at a given
        AST node, such that this can be tracked and used by the analyzer. 

        Args:
            node (Node): The AST node where the usage occurred.
            name (str): The name of the identifier that was used.
            locations (list[Location]): A list of locations (nodes and 
            their attributes) where the usage occurs, such that the 
            identifier can be updated by changing these attributes.
            namespace (NameSpace): The namespace of the used identifier.
        """
        node = self.get_stmt_from_node(node)
        last_def = self._get_last_definition(name, namespace)
        if last_def is not None:
            def_ = (last_def, name, namespace)
            self.definition_uses[def_] = self.definition_uses[def_] + locations
        self.stmt_usage[node].add((name, namespace))
        
    def visit_FileAST(self, node: FileAST) -> None:
        """ Visits a FileAST node, recording it as a scope. """
        # Record the scope information
        self._current_definitions.append({})
        self.compound_children[node] = set()
        self.compound_parent[node] = None # The FileAST has no parent
        self.stmt_compound_map[node] = None
        self.compound_stmt_map[node] = []
        self._current_compound = node
        # Record children as statements
        if node.ext is not None:
            for child in node.ext:
                self._record_stmt(child)
        # Visit the node as normal
        self.generic_visit(node)
        self._current_definitions = self._current_definitions[:-1]
    
    @_stmt_wrapper
    def visit_Compound(self, node: Compound, params: ParamList | None = None) -> None:
        """ Visits a Compound node, recording it as both a statement in its 
        current scope, and a scope itself. Optionally takes parameters as an 
        argument, which should be used if the compound is a function body, 
        where the declaration of the parameters should occur _inside_ the 
        succeeding compound.

        Args:
            node (Compound): The Compound AST node to traverse.
            params (ParamList | None, optional): The ParamList of the relevant 
            function if this compound is a function body. Defaults to None.
        """
        # Record the scope information
        self._current_definitions.append({})
        self.compound_children[node] = set()
        self.compound_children[self._current_compound].add((node, self._current_stmt))
        self.compound_parent[node] = self._current_compound
        self.stmt_compound_map[node] = self._current_compound
        self.compound_stmt_map[node] = []
        prev_compound = self._current_compound
        self._current_compound = node
        
        # Record any parameters, if given
        if params is not None:
            self._record_stmt(params)
            scope_stmt = self._current_stmt
            self._current_stmt = params
            self.generic_visit(params)
            self._current_stmt = scope_stmt
        
        # Record all children as statements
        for child in node.children():
            self._record_stmt(child[1])
        
        # Walk the AST as normal
        NodeVisitor.generic_visit(self, node)
        self._current_definitions = self._current_definitions[:-1]
        self._current_compound = prev_compound
    
    @_stmt_wrapper
    def visit_FuncDecl(self, node: FuncDecl) -> None:
        """ Visits a FuncDecl node, recording the declared function. Avoids
        traversing the parameter list, so that it is traversed in the function
        body where one exists. If one doesn't exist (a signature), this can
        be backfilled. """
        # Visit all children as normal except the parameter list,
        # as that gets walked by the compound body instead.
        for child in node.children():
            if child[0] != 'args' or self._current_function is None:
                self.visit(child[1])
        if node.type is not None:
            typedecl = self._get_typedecl(node.type)
            if typedecl is not None and typedecl.declname is not None:
                self.functions.add(typedecl.declname)
                locs = [(typedecl, "declname")]
                self._record_usage(typedecl, typedecl.declname, locs, NameSpace.ORDINARY)

    
    @_stmt_wrapper
    def visit_FuncDef(self, node: FuncDef) -> None:
        """ Visits a FuncDef node, recording the function signature,
        and passing parameters to be parsed by the function body 
        where possible. """
        # Log information for the function and its block
        prev_function = self._current_function
        if node.body is not None:
            self._current_function = node
            self.labels[node] = set()
            self.gotos[node] = set()
        # Augment the following compound with parameter definitions
        for child in node.children():
            if child[0] != "body":
                self.visit(child[1])
        self.visit_Compound(node.body, params=node.decl.type.args)
        # Track goto usage of labels (as these are an out-of-order
        # intra-function reference)
        for goto in self.gotos[node]:
            locs = [(goto, "name")]
            self._record_usage(goto, goto.name, locs, NameSpace.LABEL)
        self._current_function = prev_function
    
    @_stmt_wrapper
    def visit_Typedef(self, node: Typedef) -> None:
        """ Visits a Typedef node, recording the typedef as well as any 
        relevant identifier definitions/usages. """
        if node.name is None or node.type is None:
            return NodeVisitor.generic_visit(self, node)
        # Add the name identifier definition
        self.typedefs.add(node.name)
        locations = [(node, "name")]
        typedecl = self._get_typedecl(node.type)
        has_declname = typedecl is not None and typedecl.declname is not None
        if has_declname:
            locations.append((typedecl, "declname"))
        self._record_definition(node, node.name, locations, NameSpace.ORDINARY)
        # Add the type identifier usage, if one exists
        if has_declname:
            locations = [(node, "name"), (typedecl, "declname")]
            if isinstance(typedecl.type, (Struct, Union, Enum)) and typedecl.type.name is not None:
                # TODO: is any struct/union/enum types elsewhere?
                # Can I just put this into visit_Struct, visit_Enum and visit_Union
                # with relevant attribute checks?
                type_locs = [(typedecl.type, "name")]
                if isinstance(typedecl.type, (Struct, Union)) and typedecl.type.decls is not None:
                    self._record_definition(node, typedecl.type.name, type_locs, NameSpace.TAG)
            else:
                self._record_usage(node, typedecl.declname, locations, NameSpace.ORDINARY)
        NodeVisitor.generic_visit(self, node)
    
    def _record_var_func_decl(self, node: Decl) -> None:
        """ Records a regular function/variable/parameter declaration definition. """
        locations = [(node, "name")]
        typedecl = self._get_typedecl(node.type)
        if typedecl is not None and typedecl.declname is not None:
            locations.append((typedecl, "declname"))
        if self._current_struct is None:
            self._record_definition(node, node.name, locations, NameSpace.ORDINARY)
        else:
            self._record_definition(node, node.name, locations, (NameSpace.MEMBER, self._current_struct))
    
    def _record_tag_decl(self, node: Decl) -> None:
        """ Records definitions of enums/structs/unions (tag namespace) idents
        in Decl AST nodes. """
        # Parse type declaration for structs/unions/enums, account for pointers etc.
        #node.show() # TODO important comehere remove when done testing!
        types = []
        cur_node = node
        while cur_node.type is not None and isinstance(cur_node.type, (PtrDecl, ArrayDecl)):
            types.append(cur_node.type)
            cur_node = cur_node.type
        if isinstance(cur_node.type, (Enum, Struct, Union)):
            types.append(cur_node.type)
        for i, type_ in enumerate(types):
            if (isinstance(type_, Enum) and type_.values is not None) or (isinstance(type_, (Struct, Union)) and type_.decls is not None and type_.name is not None):
                locs = [(type_, "name")]
                self._record_definition(node, type_.name, locs, NameSpace.TAG)
                if i == 1:  # Edge case where declaring & using at the same time
                    self._record_usage(node, type_.name, locs, NameSpace.TAG)
            elif isinstance(type_, (Enum, Struct, Union)) and type_.name is not None:
                locs = [(type_, "name")]
                self._record_definition(node, type_.name, locs, NameSpace.TAG)
    
    def _record_funcspec_decl(self, node: Decl) -> None:
        """ Records definitions of function specifications, including
        within function bodies. """
        if node.type is None or node.name is None:
            return
        if isinstance(node.type, FuncDecl) and (self._current_function is None or node.name != self._current_function.decl.name):
            # A function specification has been found
            if node.name in self.funcspecs:
                self.funcspecs[node.name].add(node)
            else:
                self.funcspecs[node.name] = set([node])
            
    
    def _record_initializer_decl(self, node: Decl) -> None:
        """ Records definitions of elements in Initializer Lists 
        and Named Initializers / Designated Initializers. """
        decl_type = self.expression_analyzer.get_type(node)
        if not isinstance(decl_type, (Struct, Union)) or not isinstance(node.init, InitList) or node.init.exprs is None:
            return NodeVisitor.generic_visit(self, node)
        self.visit(node.type)
        for expr in node.init.exprs:
            if not isinstance(expr, NamedInitializer) or len(expr.name) == 0:
                self.visit(expr)
                continue
            # TODO COMEHERE IMPORTANT: HANDLE CASE WHERE more than one name, i.e.
            # .struct.structmember1.structmember2.structmember3 = "abc";
            name = expr.name[-1].name
            locs = [(expr.name[-1], "name")]
            self._record_usage(node, name, locs, (NameSpace.MEMBER, decl_type))
            self.visit_ID(expr.name[-1], record=False)
            self.visit(expr.expr)
    
    @_stmt_wrapper
    def visit_Decl(self, node: Decl) -> None:
        """ Visits a Decl node, recording any identifier definitions or usages
        that have occurred within the declaration. """
        if node.name is not None and self._current_function != "IGNORE":
            self._record_var_func_decl(node)
        self._record_tag_decl(node)
        self._record_funcspec_decl(node)
        if node.name is None or node.type is None or node.init is None:
            return NodeVisitor.generic_visit(self, node)
        self._record_initializer_decl(node)
    
    @_stmt_wrapper
    def visit_CompoundLiteral(self, node: CompoundLiteral) -> None:
        """ TODO DOCSTRING """
        type_ = self.expression_analyzer.get_type(node)
        if not isinstance(type_, (Struct, Union)) or not isinstance(node.init, InitList) or node.init.exprs is None:
            return NodeVisitor.generic_visit(self, node)
        self.visit(node.type)
        for expr in node.init.exprs:
            if not isinstance(expr, NamedInitializer) or len(expr.name) == 0:
                self.visit(expr)
                continue
            # TODO COMEHERE IMPORTANT: HANDLE CASE WHERE more than one name, i.e.
            # .struct.structmember1.structmember2.structmember3 = "abc";
            name = expr.name[-1].name
            locs = [(expr.name[-1], "name")]
            self._record_usage(node, name, locs, (NameSpace.MEMBER, type_))
            self.visit_ID(expr.name[-1], record=False)
            self.visit(expr.expr)
    
    def visit_ParamList(self, node: ParamList) -> None:
        """ TODO DOCSTRING"""
        if self._current_function is None:
            # TODO check if this is still needed
            prev_function = self._current_function
            self._current_function = "IGNORE"
            self.generic_visit(node)
            self._current_function = prev_function
        else:
            self.generic_visit(node)

    @_stmt_wrapper
    def visit_Enumerator(self, node: Enumerator) -> None:
        """ Visits an Enumerator node, recording the identifier definition. """
        if node.name is not None:
            locs = [(node, "name")]
            self._record_definition(node, node.name, locs, NameSpace.ORDINARY)
            # TODO is this namespace correct? I think so but...?
        self.generic_visit(node)
    
    def _wrap_struct_definitions(self, struct: Struct | Union) -> None:
        """ Wraps any definitions inside a struct/union by annotating
        their definitions with the 'MEMBER' namespace for that struct/union,
        and moving them to the enclosing parent scope of the struct/union.
        This allows for correct field usage analysis.

        Args:
            struct (Struct | Union): The struct/union whose field declaration
            definitions are being wrapped.
        """
        if len(self._current_definitions) <= 1:
            return
        if struct not in self.struct_members or self.struct_members[struct] is None:
            members = set()
            self.struct_members[struct] = members
        else:
            members = self.struct_members[struct]
        for (name, namespace), node in self._current_definitions[-1].items():
            if isinstance(namespace, Tuple) and namespace[0] == NameSpace.MEMBER:
                # If already a member (i.e. struct in a struct), pass through
                self._current_definitions[-2][(name, namespace)] = node
                if namespace[1] == struct: 
                    # If a member of this struct, record as a mamber
                    members.add(name) 
            else:
                # If not already a member, put identifiers in the member namespace
                new_namespace = (NameSpace.MEMBER, struct)
                members.add(name)
                self._current_definitions[-2][(name, new_namespace)] = node
                self.definition_uses[(node, name, new_namespace)] = self.definition_uses.pop((node, name, namespace))
                self.stmt_definitions[node].remove((name, namespace))
                self.stmt_definitions[node].add((name, new_namespace))
        self._current_definitions[-1] = []
    
    @_stmt_wrapper
    def visit_Union(self, node: Union) -> None:
        """ Visits a Union node, recording the structure occurrence. """
        # TODO can I put this here? Can I think of an edge case?
        if node.name is not None:
            locs = [(node, "name")]
            self._record_usage(node, node.name, locs, NameSpace.TAG)
        prev_struct = self._current_struct
        self._current_struct = node
        self._current_definitions.append({})
        NodeVisitor.generic_visit(self, node)
        self._current_struct = prev_struct
        self._wrap_struct_definitions(node)
        self._current_definitions = self._current_definitions[:-1]
    
    @_stmt_wrapper
    def visit_Struct(self, node: Struct) -> None:
        """ Visits a Struct node, recording the structure occurrence. """
        # TODO can I put this here? Can I think of an edge case?
        if node.name is not None:
            locs = [(node, "name")]
            self._record_usage(node, node.name, locs, NameSpace.TAG)
        prev_struct = self._current_struct
        self._current_struct = node
        self._current_definitions.append({})
        NodeVisitor.generic_visit(self, node)
        self._current_struct = prev_struct
        self._wrap_struct_definitions(node)
        self._current_definitions = self._current_definitions[:-1]
    
    @_stmt_wrapper
    def visit_Enum(self, node: Enum) -> None:
        """ Visits an Enum node, recording the structure occurrence. """
        # TODO can I put this here? Can I think of an edge case?
        if node.name is not None:
            locs = [(node, "name")]
            self._record_usage(node, node.name, locs, NameSpace.TAG)
        NodeVisitor.generic_visit(self, node)
        
    @_stmt_wrapper
    def visit_Label(self, node: Label) -> None:
        """ Visits a Label node, recording the label occurence and the
        corresponding identifier definition. """
        if node.stmt is not None: # TODO is this right?
            self._record_stmt(node.stmt)
        if node.name is not None:
            locs = [(node, "name")]
            self._record_definition(node, node.name, locs, NameSpace.LABEL, 
                                    alt_scope=self._current_definitions[1])
            #comehere
            self.labels[self._current_function].add(node)
        NodeVisitor.generic_visit(self, node)
    
    @_stmt_wrapper
    def visit_ID(self, node: ID, record: bool = True) -> None:
        """Visits an ID node, recording the identifier usage. This optionally allows
        you to disable recording the identifier, in case it is not an ordinary
        identifier (e.g. it is a struct field/member name).

        Args:
            node (ID): The ID (identifier) node to traverse.
            record (bool, optional): Whether to record the identifier as an
            ordinary namespace identifier usage or not. Defaults to True.
        """
        if record and node.name is not None:
            locs = [(node, "name")]
            self._record_usage(node, node.name, locs, NameSpace.ORDINARY)
        NodeVisitor.generic_visit(self, node)
    
    @_stmt_wrapper
    def visit_IdentifierType(self, node: IdentifierType) -> None:
        """ Visits an IdentifierType node, recording the identifier usage
        if the name is a typedef. """
        if node.names is None or len(node.names) == 0:
            return NodeVisitor.generic_visit(self, node)
        name = node.names[-1]
        if name in self.typedefs:
            locs = [(node, ("names", -1))]
            self._record_usage(node, name, locs, NameSpace.ORDINARY)
            # TODO again is ordinary correct or can this be e.g. struct?
            # TODO seems too specific.
        NodeVisitor.generic_visit(self, node)
    
    @_stmt_wrapper
    def visit_StructRef(self, node: StructRef) -> None:
        """ Visits a StructRef node, recording the structure information
        so that its identifiers can be parsed correctly. """
        # Fetch the corresponding member definition from the tag that matches
        # the expression's type
        if node.name is not None and node.field is not None and node.field.name is not None:
            struct_type = self.expression_analyzer.get_type(node.name)
            if struct_type is not None and node.type == "->" and isinstance(struct_type, ExpressionAnalyzer.Ptr) and isinstance(struct_type.val, (Struct, Union)):
                struct_type = struct_type.val
            if struct_type is not None and isinstance(struct_type, (Struct, Union)):
                members = self.struct_members[struct_type]
                if node.field.name in members:
                    locs = [(node.field, "name")]
                    self._record_usage(node, node.field.name, locs, (NameSpace.MEMBER, struct_type))
        self.visit(node.name)
        self.visit_ID(node.field, record=False)
    
    @_stmt_wrapper
    def visit_Goto(self, node: Goto) -> None:
        """ Visits a Goto node, recording the label identifier usage. """
        if node.name is not None:
            self.gotos[self._current_function].add(node)
        NodeVisitor.generic_visit(self, node)
    
    @_stmt_wrapper
    def generic_visit(self, node: Node) -> None:
        """ Visits any generic node in the AST, recording the current
        statement for each AST node. """
        self.node_stmt_map[node] = self._current_stmt
        NodeVisitor.generic_visit(self, node)


class NewVariableUseAnalyzer(NodeVisitor):
    """TODO"""

    def __init__(self, t_unit: interaction.CSource = None):
        self.stmt_usage = {}
        self.stmt_definitions = {}
        self.stmts = set()
        self.idents = set()
        self.functions = set()
        self.typedefs = set()
        self.labels = {}
        self.definition_uses = {}
        self.compound_children = {}
        self.compound_parent = {}
        self.stmt_compound_map = {}
        self.compound_stmt_map = {}
        self.node_stmt_map = {}
        self.stmt_func_map = {}
        self.current_compound = None
        self.current_stmt = None
        self.current_structure = None
        self.current_definitions = []
        self.current_function = None
        self.t_unit = t_unit
        self.processed = False

    def stmt_wrapper(func: Callable) -> Callable:
        def wrapper(self, node: Node, *args, **kwargs):
            is_stmt = self.is_stmt(node)
            if is_stmt:
                old_stmt = self.current_stmt
                self.current_stmt = node
                self.stmt_compound_map[node] = self.current_compound
                self.stmt_func_map[node] = self.current_function
                if self.current_compound is not node:
                    self.compound_stmt_map[self.current_compound].append(node)
            self.node_stmt_map[node] = self.current_stmt
            result = func(self, node, *args, **kwargs)
            if is_stmt:
                self.current_stmt = old_stmt
            return result

        return wrapper

    def load(self, t_unit: interaction.CSource) -> None:
        self.t_unit = t_unit
        self.processed = False

    def process(self) -> None:
        self.visit(self.t_unit)
        self.processed = True

    def record_stmt(self, stmt_node):
        self.stmts.add(stmt_node)
        self.stmt_usage[stmt_node] = set()
        self.stmt_definitions[stmt_node] = set()
        self.node_stmt_map[stmt_node] = stmt_node
        self.stmt_func_map[stmt_node] = self.current_function

    def get_stmt_definitions(self, stmt):
        return self.stmt_definitions[stmt]

    def get_stmt_usage(self, stmt):
        return self.stmt_usage[stmt]

    def get_compounds_in_subtree(self, compound):
        compounds = []
        frontier = [compound]
        while len(frontier) > 0:
            compound = frontier[0]
            frontier = frontier[1:]
            compounds.append(compound)
            for child, _ in self.compound_children[compound]:
                frontier.append(child)
        return compounds

    def get_functions(self):
        return self.functions

    def get_scope_definitions(
        self, compound: Compound, from_stmt: Node = None, to_stmt: Node = None
    ):
        from_index = (
            0
            if from_stmt is None
            else self.compound_stmt_map[compound].index(from_stmt)
        )
        to_index = (
            len(self.compound_stmt_map[compound])
            if to_stmt is None
            else (self.compound_stmt_map[compound].index(to_stmt) + 1)
        )
        definitions = set()
        for i in range(from_index, to_index):
            stmt = self.compound_stmt_map[compound][i]
            definitions = definitions.union(self.stmt_definitions[stmt])
        return definitions

    def get_scope_usage(
        self, compound: Compound, from_stmt: Node = None, to_stmt: Node = None
    ):
        from_index = (
            0
            if from_stmt is None
            else self.compound_stmt_map[compound].index(from_stmt)
        )
        to_index = (
            len(self.compound_stmt_map[compound])
            if to_stmt is None
            else (self.compound_stmt_map[compound].index(to_stmt) + 1)
        )
        usage = set()
        for i in range(from_index, to_index):
            stmt = self.compound_stmt_map[compound][i]
            usage = usage.union(self.stmt_usage[stmt])
        return usage

    def get_nested_scope_definitions(
        self, compound: Compound, from_stmt: Node = None, to_stmt: Node = None
    ):
        definitions = self.get_scope_definitions(compound, from_stmt, to_stmt)
        if from_stmt is not None:
            from_stmt = self.compound_stmt_map[compound].index(from_stmt)
        if to_stmt is not None:
            to_stmt = self.compound_stmt_map[compound].index(to_stmt)
        for child, stmt in self.compound_children[compound]:
            index = self.compound_stmt_map[compound].index(stmt)
            if from_stmt is not None and index < from_stmt:
                continue
            if to_stmt is not None and index > to_stmt:
                continue
            child_defs = self.get_nested_scope_definitions(child)
            definitions = definitions.union(child_defs)
        return definitions

    def get_nested_scope_usage(
        self, compound: Compound, from_stmt: Node = None, to_stmt: Node = None
    ):
        usage = self.get_scope_usage(compound, from_stmt, to_stmt)
        if from_stmt is not None:
            from_stmt = self.compound_stmt_map[compound].index(from_stmt)
        if to_stmt is not None:
            to_stmt = self.compound_stmt_map[compound].index(to_stmt)
        for child, stmt in self.compound_children[compound]:
            index = self.compound_stmt_map[compound].index(stmt)
            if from_stmt is not None and index < from_stmt:
                continue
            if to_stmt is not None and index > to_stmt:
                continue
            child_defs = self.get_nested_scope_usage(child)
            usage = usage.union(child_defs)
        return usage

    def get_stmt_compound(self, stmt: Node) -> Optional[Compound]:
        return self.stmt_compound_map[stmt]

    def get_definitions_at_stmt(self, stmt: Node, compound: Compound = None):
        # Get containing scope (compound)
        if compound is None:
            compound = self.get_stmt_compound(stmt)
        # Generate the stack path of scopes back to the program root (FileAST)
        scope_path = [compound]
        while compound is not None:
            compound = self.compound_parent[compound]
            scope_path.append(compound)
        scope_path = scope_path[:-1]
        # Compute definitions for each scope up to the statement, and find their union
        if len(scope_path) == 1:
            return self.get_scope_definitions(scope_path[0], None, stmt)
        definitions = set()
        for i, scope in [s for s in enumerate(scope_path)][-1:0:-1]:
            child = scope_path[i - 1]
            compound_stmt = None
            for c in self.compound_children[scope]:
                if c[0] == child:
                    compound_stmt = c[1]
                    break
            scope_defs = self.get_scope_definitions(scope, None, compound_stmt)
            definitions = definitions.union(scope_defs)
        # Handle last scope (current scope)
        scope_defs = self.get_scope_definitions(scope_path[0], None, stmt)
        definitions = definitions.union(scope_defs)
        return definitions

    def get_usage_from_stmt(self, stmt: Node, compound: Compound = None):
        if compound is None:
            compound = self.get_stmt_compound(stmt)
        return self.get_nested_scope_usage(compound, stmt, None)

    def get_required_identifiers(
        self, node, type, compound=None, function=None
    ):
        stmt = self.get_stmt_from_node(node)
        if compound is None:
            compound = self.get_stmt_compound(stmt)
        defined = self.get_usage_from_stmt(stmt).union(
            self.get_scope_definitions(compound)
        )
        if function is not None:
            defined = defined.union(
                set((x, TypeKinds.LABEL) for x in self.labels[function])
            )
        defined = set(x[0] for x in defined if x[1] == type)
        return defined

    def get_unique_identifier(
        self, node, type, compound=None, function=None, exclude=None
    ):
        defined = self.get_required_identifiers(node, type, compound, function)
        if exclude is not None:
            defined = defined.union(set(exclude))
        return self.__find_new_ident(defined)

    def get_new_identifier(self, exclude=None):
        exclude = [] if exclude is None else exclude
        return self.__find_new_ident(self.idents.union(set(exclude)))

    def __find_new_ident(self, banned):
        # TODO can I ban header functions as well? Or no?
        banned = banned.union(set(CLexer.keywords))
        banned = banned.union(set([kw.lower() for kw in CLexer.keywords]))
        new_ident = "a"
        count = 0
        while new_ident in banned:
            count += 1
            choices = string.ascii_letters
            new_ident = ""
            cur_num = count
            while cur_num >= 0:
                new_ident += choices[cur_num % len(choices)]
                cur_num = cur_num // len(choices)
                if cur_num == 0:
                    break
        return new_ident

    def change_ident(self, node, name, kind, new_name):
        # Update AST attributes for all locations referring to
        # this specific definition to propagate identifier change.
        stmt_node = self.get_stmt_from_node(node)
        for location_set in self.definition_uses[(stmt_node, name, kind)]:
            for (change_node, attr) in location_set:
                if isinstance(attr, tuple):
                    attr_name = attr[0]
                    cur_val = getattr(change_node, attr_name)
                    for attr_index in attr[1:-1]:
                        cur_val = cur_val[attr_index]
                    cur_val[attr[-1]] = new_name
                else:
                    setattr(change_node, attr, new_name)
        # Update processed tracking variables accordingly to allow further analyzer usage
        if (name, kind) in self.stmt_usage[stmt_node]:
            self.stmt_usage[stmt_node].remove((name, kind))
            self.stmt_usage[stmt_node].add((new_name, kind))
        if (name, kind) in self.stmt_definitions[stmt_node]:
            self.stmt_definitions[stmt_node].remove((name, kind))
            self.stmt_definitions[stmt_node].add((new_name, kind))
        self.definition_uses[(stmt_node, new_name, kind)] = self.definition_uses[
            (stmt_node, name, kind)
        ]
        self.definition_uses.pop((stmt_node, name, kind))

    def is_stmt(self, stmt_node):
        return stmt_node in self.stmts

    def get_stmt_from_node(self, ast_node):
        return self.node_stmt_map[ast_node]
    
    def get_func_from_stmt(self, stmt_node):
        return self.stmt_func_map[stmt_node]

    def get_last_definition(self, name, kind):
        for scope in self.current_definitions[::-1]:
            if (name, kind) in scope:
                return scope[(name, kind)]
        return None

    def __get_typedecl(self, node: Node) -> TypeDecl | None:
        if node is None:
            return None
        if isinstance(node, (PtrDecl, ArrayDecl)):
            return self.__get_typedecl(node.type)
        elif isinstance(node, TypeDecl):
            return node
        return None

    def record_ident_def(self, node, name, locations, kind, alt_scope=None):
        node = self.get_stmt_from_node(node)
        if self.current_structure is not None:
            if self.current_structure.name is not None:
                name = self.current_structure.name + "." + name
            else:  # Using an anonymous (no-name) struct/union, so don't record variables
                # TODO probably can't ignore these?
                self.idents.add(name)
                return
        if alt_scope is None:
            self.current_definitions[-1][(name, kind)] = (node, locations)
        else:
            alt_scope[(name, kind)] = (node, locations)
        self.definition_uses[(node, name, kind)] = [locations]
        self.stmt_definitions[node].add(
            (name, kind)
        )  # TODO do I need to store locations here as well?
        # TODO also do I need to store self.current_structure?
        self.idents.add(name)

    def record_ident_usage(self, node, name, locations, kind):
        node = self.get_stmt_from_node(node)
        if self.current_structure is not None:
            if (
                isinstance(self.current_structure, StructRef)
                and name == self.current_structure.field.name
            ):
                name = self.current_structure.name.name + "." + name
            elif isinstance(self.current_structure, NamedInitializer):
                return
            elif (
                isinstance(self.current_structure, tuple)
                and len(self.current_structure) == 2
                and isinstance(self.current_structure[0], NamedInitializer)
            ):
                name = self.current_structure[1] + "." + name
        last_definition = self.get_last_definition(name, kind)
        if last_definition is not None:
            self.definition_uses[(last_definition[0], name, kind)].append(locations)
        self.stmt_usage[node].add((name, kind))

    def visit_FileAST(self, node) -> None:
        self.current_definitions.append({})
        self.compound_children[node] = set()
        self.compound_parent[node] = None
        self.stmt_compound_map[node] = node
        self.compound_stmt_map[node] = []
        self.current_compound = node
        if node.ext is not None:
            for child in node.ext:
                self.record_stmt(child)
        self.generic_visit(node)
        self.current_definitions = self.current_definitions[:-1]

    @stmt_wrapper
    def visit_Compound(self, node, params=None):
        self.current_definitions.append({})
        self.compound_children[node] = set()
        self.compound_children[self.current_compound].add((node, self.current_stmt))
        self.compound_parent[node] = self.current_compound
        self.stmt_compound_map[node] = node
        self.compound_stmt_map[node] = []
        prev_compound = self.current_compound
        self.current_compound = node
        # Record parameters if given
        if params is not None:
            self.record_stmt(params)
            old_stmt = self.current_stmt
            self.current_stmt = params
            self.generic_visit(params)
            self.current_stmt = old_stmt
        # Record all children if statements
        for child in node.children():
            self.record_stmt(child[1])
        # Walk the AST as normal
        NodeVisitor.generic_visit(self, node)
        self.current_definitions = self.current_definitions[:-1]
        self.current_compound = prev_compound

    @stmt_wrapper
    def visit_FuncDecl(self, node):
        # Visit all children as normal except for the parameter list, as this will be
        # walked by the body to record the parameters inside the compound.
        if node.type is not None:
            typedecl = self.__get_typedecl(node.type)
            if typedecl is not None and typedecl.declname is not None:
                self.functions.add(typedecl.declname)
        for child in node.children():
            if child[0] != "args" or self.current_function is None:
                self.visit(child[1])

    @stmt_wrapper
    def visit_FuncDef(self, node):
        # Log information for the function and its block
        old_func = self.current_function
        if node.body is not None:
            self.current_function = node
            self.labels[node] = set()
        # Augment the following compound with parameter definitions to ensure correct scoping
        for child in node.children():
            if child[0] != "body":
                self.visit(child[1])
        self.visit_Compound(node.body, params=node.decl.type.args)
        self.current_function = old_func

    def visit_TypeDecl(self, node):
        ### TODO I think I can (and need to); but can I happily get rid of this?
        ### Note: this would work, but typedecl can be both used and defined
        ### I believe (not 100% sure), so I don't want to do it like this
        # COMEHERE is this right?
        """info = self.info[self.processing_stack[-1]]
        if node in info["idents"]:
            info["idents"][node].append(('declname', TypeKinds.NONSTRUCTURE, self.current_structure, False))
        else:
            info["idents"][node] = [('declname', TypeKinds.NONSTRUCTURE, self.current_structure, False)]"""
        self.generic_visit(node)

    @stmt_wrapper
    def visit_Typedef(self, node):
        if node.name is not None:
            self.typedefs.add(node.name)
            attributes = [(node, "name")]
            typedecl = self.__get_typedecl(node.type)
            if typedecl is not None and typedecl.declname is not None:
                attributes.append((typedecl, "declname"))
            self.record_ident_def(node, node.name, attributes, TypeKinds.NONSTRUCTURE)
        if node.type is not None:
            typedecl = self.__get_typedecl(node.type)
            if typedecl.declname is not None:
                attributes = [(typedecl, "declname")]
                if typedecl.type is not None:
                    # TODO struct/union/enum types elsewhere? Can I just
                    # put this into visit_Struct, visit_Enum and visit_Union
                    # with relevant attribute checks?
                    # TODO - where else can these be used apart from
                    # typedef and decl? Surely some missing cases?
                    if (
                        isinstance(typedecl.type, (Struct, Union, Enum))
                        and typedecl.type.name is not None
                    ):
                        attributes.append((typedecl.type, "name"))
                self.record_ident_usage(
                    node, typedecl.declname, attributes, TypeKinds.STRUCTURE
                )
        NodeVisitor.generic_visit(self, node)

    @stmt_wrapper
    def visit_Enumerator(self, node):
        if node.name is not None:
            self.record_ident_def(
                node, node.name, [(node, "name")], TypeKinds.NONSTRUCTURE
            )  # TODO is NONSTRUCTURE correct?
        self.generic_visit(node)

    @stmt_wrapper
    def visit_Decl(self, node):
        # Handle variable and function definitions
        if node.name is not None:
            # TODO technically generating in the wrong order - should visit then record ident?
            if (
                self.current_function != "IGNORE"
            ):  # Regular parameter/function definition
                attributes = [(node, "name")]
                typedecl = self.__get_typedecl(node.type)
                if typedecl is not None and typedecl.declname is not None:
                    attributes.append((typedecl, "declname"))
                # TODO is this right - apparently different for funcs and vars?
                self.record_ident_def(
                    node, node.name, attributes, TypeKinds.NONSTRUCTURE
                )
        # Handle Enum/Struct/Union definition and usage
        types = []
        if node.type is not None:
            types.append(node.type)
            if hasattr(node.type, "type") and node.type.type is not None:
                types.append(
                    node.type.type
                )  # Accounts for enum/struct/union usages (which are also
                # types of declarations)
        for i, type_ in enumerate(types):
            if isinstance(type_, (Enum, Struct, Union)):
                if (
                    isinstance(type_, Enum)
                    and type_.values is not None
                    or isinstance(type_, (Struct, Union))
                    and type_.decls is not None
                    and type_.name is not None
                ):  # TODO check new .name checks not break anything ^v
                    # Enum/Struct/Union definition
                    self.record_ident_def(
                        node, type_.name, [(type_, "name")], TypeKinds.STRUCTURE
                    )  # TODO slightly different from original - both now link to node instead of type_
                    if i == 1:  # Edge case where declaring and using at the same time
                        self.record_ident_usage(
                            node, type_.name, [(type_, "name")], TypeKinds.STRUCTURE
                        )
                elif type_.name is not None:  # Enum/Struct/Union usage
                    self.record_ident_usage(
                        node, type_.name, [(type_, "name")], TypeKinds.STRUCTURE
                    )
        # Handle Initializer Lists and Named Initializers
        if (
            node.name is not None
            and node.type is not None
            and node.type.type is not None
            and isinstance(node.type.type, Struct)
            and node.init is not None
            and isinstance(node.init, InitList)
            and node.init.exprs is not None
        ):
            old_structure = self.current_structure
            for expr in [e for e in node.init.exprs if isinstance(e, NamedInitializer)]:
                name = ".".join([n.name for n in expr.name])
                self.current_structure = (expr, node.type.type.name)
                self.record_ident_usage(
                    node, name, [(expr, "name")], TypeKinds.NONSTRUCTURE
                )  # TODO again, slightly different - tying it to node instead of expr
            self.current_structure = old_structure
        # Parse children as normal
        NodeVisitor.generic_visit(self, node)

    def visit_ParamList(self, node):
        if self.current_function is None:
            # If parsing parameters but not in a function (i.e. parsing a prototype), ignore
            # IDENT instances. TODO - is this even necessary after removing them?
            old_function = self.current_function
            self.current_function = "IGNORE"
            self.generic_visit(node)
            self.current_function = old_function
        else:
            self.generic_visit(node)

    def visit_Union(self, node):
        old_structure = self.current_structure
        self.current_structure = node
        self.generic_visit(node)
        self.current_structure = old_structure

    def visit_Struct(self, node):
        old_structure = self.current_structure
        self.current_structure = node
        self.generic_visit(node)
        self.current_structure = old_structure

    def visit_NamedInitializer(self, node):
        old_structure = self.current_structure
        self.current_structure = node
        self.generic_visit(node)
        self.current_structure = old_structure

    @stmt_wrapper
    def visit_Label(self, node):
        if node.stmt is not None:
            self.record_stmt(node.stmt)
        if node.name is not None:
            self.record_ident_def(
                node,
                node.name,
                [(node, "name")],
                TypeKinds.LABEL,
                alt_scope=self.current_definitions[
                    1
                ],  # TODO look into fixing this it is breaking stuff
            )  # The above defines it in the function, but when looking at usage it may not be found
            self.labels[self.current_function].add(node.name)
        NodeVisitor.generic_visit(self, node)

    @stmt_wrapper
    def visit_ID(self, node):
        if node.name is not None:
            self.record_ident_usage(
                node, node.name, [(node, "name")], TypeKinds.NONSTRUCTURE
            )
        NodeVisitor.generic_visit(self, node)

    @stmt_wrapper
    def visit_IdentifierType(self, node):
        # TODO not sure why there can be multiple names here - need to check
        if node.names is None or len(node.names) == 0:
            return NodeVisitor.generic_visit(self, node)
        name = node.names[-1]
        if name in self.typedefs:
            self.record_ident_usage(
                node, name, [(node, ("names", -1))], TypeKinds.NONSTRUCTURE
            )
        NodeVisitor.generic_visit(self, node)

    @stmt_wrapper
    def visit_StructRef(self, node):
        old_structure = self.current_structure
        self.current_structure = (node, "field")
        if node.field is not None:
            self.visit(node.field)
        self.current_structure = (node, "name")
        if node.name is not None:
            self.visit(node.name)
        self.current_structure = old_structure

    @stmt_wrapper
    def visit_Goto(self, node):
        if node.name is not None:
            self.record_ident_usage(node, node.name, [(node, "name")], TypeKinds.LABEL)
        NodeVisitor.generic_visit(self, node)

    @stmt_wrapper
    def generic_visit(self, node):
        self.node_stmt_map[node] = self.current_stmt
        NodeVisitor.generic_visit(self, node)


# Identifier analysis - we need to determine
#  1. What identifiers exist where
#  2. What identifiers are used in each
#       (i) Function - CompoundStmt
#       (ii) Scope - CompoundStmt
#  So, could we just make a mapping of compound statements to usage information?
#  For each compound statement, we store
#   1. A per-statement map storing the identifiers that exist
#   2. The last (end/OUT) set of such values
#   3. A per-block map storing the identifiers that are used
#  Then to find what identifiers exist at a function we:
#   1. Give the statement AST node
#   2. Use that to determine the current stack of scopes
#   3. Use that to determine the currently available identifiers from previous scope
#   4. Combine with current block map to determine
#  And to find what identifiers are used in the block containing a statement we:
#   1. Give the statement AST node
#   2. Use that to determine the current stack of scopes
#   3. Use that to get the used identifiers (those in _this_ block and its child blocks)
#  So I think we also need to store a tree of compound statements (rather than a stack/map)
#  so that we can determine child nodes I think?
class VariableUseAnalyzer(NodeVisitor):
    """TODO"""

    # TODO it feels like switches might break this? Maybe need to
    # do some testing?

    def __init__(self, t_unit=None):
        self.functions = set()
        self.typedefs = set()
        self.parent_block = dict()
        self.parent_statement = dict()
        self.current_function = None
        self.defined = []
        self.definition_uses = {}
        self.info = {}
        self.types = {}
        self.processing_stack = []
        self.current_structure = None
        self.t_unit = t_unit
        self.processed = False

    def input(self, t_unit) -> None:
        self.processed = False
        self.t_unit = t_unit

    def process(self) -> None:
        self.visit(self.t_unit)
        self.processed = True

    # TODO can I generalise some of these functions - just the same but use "IdentDefs" or "IdentUses" - can definitely make higher order

    def get_usage_definition(self, ident, type, stmt):  # TODO is this useful or no?
        compound = self.get_stmt_compound(stmt)
        info = self.info[compound]
        while compound is not None:
            for i in range(info["stmtIndexes"][stmt], -1, -1):
                stmt_defs = info["IdentDefs"][i]
                if (ident, type) in stmt_defs:
                    for match_stmt in info["stmtIndexes"].keys():
                        if info["stmtIndexes"][match_stmt] == i:
                            return match_stmt
            stmt = compound
            compound = info["parent"]
            info = self.info[compound]
            stmt = [x[1] for x in info["children"] if x[0] == stmt][0]
        return None

    def get_stmt_idents(self, stmt):  # TODO is this useful or no?
        compound = self.get_stmt_compound(stmt)
        return (
            []
            if stmt not in self.info[compound]["idents"]
            else self.info[compound]["idents"][stmt]
        )

    def get_scope_definitions(
        self, compound: Compound, from_stmt: Node = None, to_stmt: Node = None
    ):
        # TODO should I calculate and cache scope-level stuff at the end instead?
        info = self.info[compound]
        if from_stmt is None:
            from_index = 0  # Set to start, whole scope
        else:
            from_index = info["stmtIndexes"][from_stmt]
        if to_stmt is None:
            to_index = info["currentIndex"]  # Set to end, whole scope
        else:
            to_index = info["stmtIndexes"][to_stmt] + 1  # Set to include up to the stmt
        definitions = set()
        for i in range(from_index, to_index):
            stmt_defs = info["IdentDefs"][i]
            definitions = definitions.union(stmt_defs)
        return definitions

    def get_scope_usage(
        self, compound: Compound, from_stmt: Node = None, to_stmt: Node = None
    ):
        info = self.info[compound]
        if from_stmt is None:
            from_index = 0  # Set to start, whole scope
        else:
            from_index = info["stmtIndexes"][from_stmt]
        if to_stmt is None:
            to_index = info["currentIndex"]  # Set to end, whole scope
        else:
            to_index = info["stmtIndexes"][to_stmt] + 1  # Set to include up to the stmt
        usage = set()
        for i in range(from_index, to_index):
            stmt_usage = info["IdentUses"][i]
            usage = usage.union(stmt_usage)
        return usage

    def get_nested_scope_definitions(
        self, compound: Compound, from_stmt=None, to_stmt=None
    ):
        definitions = self.get_scope_definitions(compound, from_stmt, to_stmt)
        if from_stmt is not None:
            from_stmt = self.info[compound]["stmtIndexes"][from_stmt]
        if to_stmt is not None:
            to_stmt = self.info[compound]["stmtIndexes"][to_stmt]
        for child, index in self.info[compound]["children"]:
            index = self.info[compound]["stmtIndexes"][index]
            if from_stmt is not None and index < from_stmt:
                continue
            if to_stmt is not None and index > to_stmt:
                continue
            child_defs = self.get_nested_scope_definitions(child)
            definitions = definitions.union(child_defs)
        return definitions

    def get_nested_scope_usage(self, compound: Compound, from_stmt=None, to_stmt=None):
        usage = self.get_scope_usage(compound, from_stmt, to_stmt)
        if from_stmt is not None:
            from_stmt = self.info[compound]["stmtIndexes"][from_stmt]
        if to_stmt is not None:
            to_stmt = self.info[compound]["stmtIndexes"][to_stmt]
        for child, index in self.info[compound]["children"]:
            index = self.info[compound]["stmtIndexes"][index]
            if from_stmt is not None and index < from_stmt:
                continue
            if to_stmt is not None and index > to_stmt:
                continue
            child_usage = self.get_nested_scope_usage(child)
            usage = usage.union(child_usage)
        return usage

    def get_stmt_compound(self, stmt: Node) -> Optional[Compound]:
        return self.parent_block[stmt]

    def get_stmt_definitions(self, stmt: Node, compound: Compound = None):
        if compound is None:
            compound = self.get_stmt_compound(stmt)
        info = self.info[compound]
        return info["IdentDefs"][info["stmtIndexes"][stmt]]

    def get_stmt_usage(self, stmt: Node, compound: Compound = None):
        if compound is None:
            compound = self.get_stmt_compound(stmt)
        info = self.info[compound]
        return info["IdentUses"][info["stmtIndexes"][stmt]]

    def get_definitions_at_stmt(self, stmt: Node, compound: Compound = None):
        # Get containing scope (compound)
        if compound is None:
            compound = self.get_stmt_compound(stmt)
        # Generate the stack path of scopes back to the program root (FileAST)
        scope_path = [compound]
        while compound is not None:
            compound = self.info[compound]["parent"]
            scope_path.append(compound)
        # Compute definitions for each scope up to the statement, and find their union
        if len(scope_path) == 1:
            return self.get_scope_definitions(scope_path[0], None, stmt)
        definitions = set()
        for i, scope in [s for s in enumerate(scope_path)][-1:0:-1]:
            child = scope_path[i - 1]
            compound_stmt = None
            for c in self.info[scope]["children"]:
                if c[0] == child:
                    compound_stmt = c[1]
                    break
            scope_defs = self.get_scope_definitions(scope, None, compound_stmt)
            definitions = definitions.union(scope_defs)
        # Handle last scope (current scope)
        scope_defs = self.get_scope_definitions(scope_path[0], None, stmt)
        definitions = definitions.union(scope_defs)
        return definitions

    def get_usage_from_stmt(self, stmt: Node, compound: Compound = None):
        if compound is None:
            compound = self.get_stmt_compound(stmt)
        return self.get_nested_scope_usage(compound, stmt, None)

    def is_stmt(self, stmt_node) -> bool:
        info = self.info[self.processing_stack[-1]]
        return stmt_node in info["stmtIndexes"]

    def get_stmt(self, ast_node):
        return self.parent_statement[ast_node]

    def get_unique_identifier(self, node, type):  # TODO not needed anymore?
        defined = self.get_usage_from_stmt(self.get_stmt(node))
        defined = self.get_nested_scope_usage()
        defined = set(x for x in defined if x[1] == type)
        new_ident = "a"
        count = 0
        while new_ident in defined:
            count += 1
            choices = string.ascii_letters
            new_ident = ""
            cur_num = count
            while cur_num >= 0:
                new_ident += choices[cur_num % len(choices)]
                cur_num = cur_num // len(choices)
                if cur_num == 0:
                    break
        return new_ident

    def record_stmt(self, stmt_node):
        node = self.processing_stack[-1]
        info = self.info[node]
        index = self.info[node]["currentIndex"]
        info["currentIndex"] += 1
        info["stmtIndexes"][stmt_node] = index
        info["IdentUses"][index] = set()
        info["IdentDefs"][index] = set()
        self.parent_block[stmt_node] = node

    # TODO check all analysis still works after changes to record_ident_usage and record_ident_def

    def get_last_definition(self, name, kind):
        for scope in self.defined[::-1]:
            if (name, kind) in scope:
                return scope[(name, kind)]
        return None

    def change_ident(self, node, name, new_name):
        stmt_node = self.get_stmt(node)
        for (change_node, attr) in self.definition_uses[(stmt_node, name)]:
            if attr == "names":  # TODO stopgap fix, need to make more robust
                setattr(change_node, attr, [new_name])
                continue
            setattr(change_node, attr, new_name)

    def record_ident_usage(self, node, attr, kind, altname=None):
        name = altname if altname is not None else getattr(node, attr)
        def_node = self.get_last_definition(name, kind)
        if def_node is not None:
            self.definition_uses[(def_node[0], name)].append((node, attr))
        info = self.info[self.processing_stack[-1]]
        if node in info["idents"]:
            info["idents"][node].append((attr, kind, self.current_structure, False))
        else:
            info["idents"][node] = [(attr, kind, self.current_structure, False)]
        if self.current_structure is not None:
            if (
                isinstance(self.current_structure, StructRef)
                and name == self.current_structure.field.name
            ):
                name = self.current_structure.name.name + "." + name
            elif isinstance(self.current_structure, NamedInitializer):
                return
            elif (
                isinstance(self.current_structure, tuple)
                and len(self.current_structure) == 2
                and isinstance(self.current_structure[0], NamedInitializer)
            ):
                name = self.current_structure[1] + "." + name
        index = info["stmtIndexes"][info["currentStmt"]]
        info["IdentUses"][index].add((name, kind))

    def record_ident_def(self, node, attr, kind, altname=None):
        name = altname if altname is not None else getattr(node, attr)
        self.defined[-1][(name, kind)] = (node, attr)  # TODO new remove if not used
        self.definition_uses[(node, name)] = [(node, attr)]
        info = self.info[self.processing_stack[-1]]
        if node in info["idents"]:
            info["idents"][node].append((attr, kind, self.current_structure, True))
        else:
            info["idents"][node] = [(attr, kind, self.current_structure, True)]
        if self.current_structure is not None:
            if self.current_structure.name is not None:
                name = self.current_structure.name + "." + name
            else:  # Using an anonymous (no-name) struct/union, so don't record variables
                return
        index = info["stmtIndexes"][info["currentStmt"]]
        info["IdentDefs"][index].add((name, kind))

    def visit_FileAST(self, node):
        self.processing_stack.append(None)
        self.info[None] = {
            "parent": None,
            "children": [],
            "idents": {},
            "currentStmt": None,
            "currentIndex": 0,
            "stmtIndexes": {},
            "IdentUses": {},
            "IdentDefs": {},
        }
        self.defined.append({})
        for child in node.children():
            self.record_stmt(child[1])
        self.generic_visit(node)
        self.processing_stack = self.processing_stack[:-1]
        self.defined = self.defined[:-1]

    def visit_Compound(self, node, params=None):
        if self.is_stmt(node):  # TODO check and test with this added
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        self.parent_statement[node] = self.info[self.processing_stack[-1]][
            "currentStmt"
        ]
        # Record the Compound Statement in the scope tree if necessary
        parent = self.processing_stack[-1]
        currentStmt = self.info[parent]["currentStmt"]
        self.info[parent]["children"].append((node, currentStmt))
        # Initialise information tracking about the block, and add to the processing stack.
        self.info[node] = {
            "parent": self.processing_stack[-1],
            "children": [],
            "idents": {},
            "currentStmt": None,
            "currentIndex": 0,
            "stmtIndexes": {},
            "IdentUses": {},
            "IdentDefs": {},
        }
        self.processing_stack.append(node)
        self.defined.append({})
        # Record parameters if any given
        if params is not None:
            self.record_stmt(params)
            self.info[node]["currentStmt"] = params
            NodeVisitor.generic_visit(self, params)
        # Record all the children as statements
        for child in node.children():
            self.record_stmt(child[1])
        # Walk the AST as normal
        NodeVisitor.generic_visit(self, node)
        # Pop the compound from the processing stack
        self.processing_stack = self.processing_stack[:-1]
        self.defined = self.defined[:-1]

    def visit_FuncDecl(self, node):
        # Visit all children as normal except for the parameter list, as this will be
        # walked by the body to record the parameters inside the compound.
        self.parent_statement[node] = self.info[self.processing_stack[-1]][
            "currentStmt"
        ]
        for child in node.children():
            if child[0] != "args" or self.current_function is None:
                self.visit(child[1])

    def visit_FuncDef(self, node):
        if self.is_stmt(node):
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        self.parent_statement[node] = self.info[self.processing_stack[-1]][
            "currentStmt"
        ]
        # Next we log information for the function and its block.
        temp = self.current_function
        if node.body is not None:
            self.functions.add(node)
            self.current_function = node
        # Then we augment the following compound with parameter definitions
        for child in node.children():
            if child[0] != "body":
                self.visit(child[1])
        self.visit_Compound(node.body, params=node.decl.type.args)
        self.current_function = temp

    def visit_TypeDecl(self, node):
        info = self.info[self.processing_stack[-1]]
        if node in info["idents"]:
            info["idents"][node].append(
                ("declname", TypeKinds.NONSTRUCTURE, self.current_structure, False)
            )
        else:
            info["idents"][node] = [
                ("declname", TypeKinds.NONSTRUCTURE, self.current_structure, False)
            ]
        self.generic_visit(node)

    def visit_Typedef(self, node):
        # TODO technically generating in wrong order - should visit _then_ record ident?
        if self.is_stmt(node):
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        self.parent_statement[node] = self.info[self.processing_stack[-1]][
            "currentStmt"
        ]
        if node.name is not None:
            self.typedefs.add(node.name)
            self.record_ident_def(node, "name", TypeKinds.NONSTRUCTURE)
        NodeVisitor.generic_visit(self, node)

    def visit_Enumerator(self, node):
        if node.name is not None:
            self.record_ident_def(node, "name", TypeKinds.NONSTRUCTURE)
        self.generic_visit(node)

    def visit_Decl(self, node):  # Handle variable and function definitions
        if self.is_stmt(node):
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        self.parent_statement[node] = self.info[self.processing_stack[-1]][
            "currentStmt"
        ]
        if (
            node.name is not None
        ):  # TODO changed this to add FuncDef's here, check it is still right
            # TODO technically generating in wrong order - should visit _then_ record ident?
            if self.current_function == "IGNORE":
                # Parameter in function prototype - record instance but not definition
                info = self.info[self.processing_stack[-1]]
                if node in info["idents"]:
                    info["idents"][node].append(
                        ("name", TypeKinds.NONSTRUCTURE, "IGNORE", True)
                    )
                else:
                    info["idents"][node] = [
                        ("name", TypeKinds.NONSTRUCTURE, "IGNORE", True)
                    ]
            else:  # Regular parameter/function definition
                self.record_ident_def(node, "name", TypeKinds.NONSTRUCTURE)
                self.types[node.name] = node  # TODO is this correcT? was a quick fix
        # TODO coalesce the below two if statements into one simple conditional?
        #      why does the second conditional need a name? does it? prob not?
        types = []
        if node.type is not None:
            types.append(node.type)  # Consider enum/struct/union declarations
            if hasattr(node.type, "type") and node.type.type is not None:
                types.append(
                    node.type.type
                )  # Consider enum/struct/union usages (which may also be declarations)
        for i, type_ in enumerate(types):
            if isinstance(
                type_,
                (
                    Enum,
                    Struct,
                    Union,
                ),
            ):
                if (
                    isinstance(type_, Enum)
                    and type_.values is not None
                    or isinstance(
                        type_,
                        (
                            Struct,
                            Union,
                        ),
                    )
                    and type_.decls is not None
                ):
                    # Record enum/struct/union definition
                    self.record_ident_def(type_, "name", TypeKinds.STRUCTURE)
                    if (
                        i == 1
                    ):  # Consider edge case where declaring and using at the same time
                        self.record_ident_usage(type_, "name", TypeKinds.STRUCTURE)
                else:  # Record enum/struct/union usage
                    self.record_ident_usage(type_, "name", TypeKinds.STRUCTURE)
        if (
            node.name is not None
            and node.type is not None
            and node.type.type is not None
            and isinstance(node.type.type, Struct)
            and node.init is not None
            and isinstance(node.init, InitList)
            and node.init.exprs is not None
        ):
            temp = self.current_structure
            for expr in node.init.exprs:
                if isinstance(expr, NamedInitializer):
                    name = ".".join([n.name for n in expr.name])
                    self.current_structure = (expr, node.type.type.name)
                    self.record_ident_usage(
                        expr, "name", TypeKinds.NONSTRUCTURE, altname=name
                    )
            self.current_structure = temp
        NodeVisitor.generic_visit(self, node)

    def visit_ParamList(self, node):
        if self.current_function is None:
            # If parsing parameters but not in a function (i.e. just parsing a function
            # prototype), then record ident instances but don't note them as definitions
            # as there is no body for them to be defined in.
            temp = self.current_function
            self.current_function = "IGNORE"
            self.generic_visit(node)
            self.current_function = temp
        else:
            self.generic_visit(node)

    def visit_Union(self, node):
        temp = self.current_structure
        self.current_structure = node
        self.generic_visit(node)
        self.current_structure = temp

    def visit_Struct(self, node):
        temp = self.current_structure
        self.current_structure = node
        self.generic_visit(node)
        self.current_structure = temp

    def visit_Label(self, node):
        if self.is_stmt(node):
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        self.parent_statement[node] = self.info[self.processing_stack[-1]][
            "currentStmt"
        ]
        if node.name is not None:
            self.record_ident_def(node, "name", TypeKinds.LABEL)
        NodeVisitor.generic_visit(self, node)

    def visit_ID(self, node):
        if self.is_stmt(node):
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        self.parent_statement[node] = self.info[self.processing_stack[-1]][
            "currentStmt"
        ]
        if node.name is not None:
            self.record_ident_usage(node, "name", TypeKinds.NONSTRUCTURE)
        NodeVisitor.generic_visit(self, node)

    def visit_IdentifierType(self, node):
        # TODO not sure why there can be multiple names here - need to check TODO
        if node.names is not None:
            self.record_ident_usage(
                node, "names", TypeKinds.NONSTRUCTURE, altname=node.names[-1]
            )
            # TODO this attribute it surely not updated correctly?
        # name = ".".join(node.names)
        # if name in self.typedefs:
        #    self.record_ident_usage(node, "names", TypeKinds.NONSTRUCTURE, altname=name)
        self.generic_visit(node)

    def visit_StructRef(self, node):
        if self.is_stmt(node):
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        self.parent_statement[node] = self.info[self.processing_stack[-1]][
            "currentStmt"
        ]
        temp = self.current_structure
        self.current_structure = (node, "field")
        if node.field is not None:
            self.visit(node.field)
        self.current_structure = (node, "name")
        if node.name is not None:
            self.visit(node.name)
        self.current_structure = temp

    def visit_Goto(self, node):
        if self.is_stmt(node):
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        self.parent_statement[node] = self.info[self.processing_stack[-1]][
            "currentStmt"
        ]
        if node.name is not None:
            self.record_ident_usage(node, "name", TypeKinds.LABEL)
        NodeVisitor.generic_visit(self, node)

    def visit_NamedInitializer(self, node):
        temp = self.current_structure
        self.current_structure = node
        self.generic_visit(node)
        self.current_structure = temp

    def generic_visit(self, node):
        if self.is_stmt(
            node
        ):  # TODO this is double-checked in some cases - see if I can avoid (maybe replace generic_visit in specified functions?)
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        # Record the statement the node is related to
        self.parent_statement[node] = self.info[self.processing_stack[-1]][
            "currentStmt"
        ]
        NodeVisitor.generic_visit(self, node)


class ASTCacher(NodeVisitor):
    
    def __init__(self):
        super(ASTCacher, self).__init__()
        self.node_cache = set()
    
    def node_in_AST(self, node: Node) -> bool:
        return node in self.node_cache
    
    def generic_visit(self, node: Node) -> None:
        self.node_cache.add(node)
        return super(ASTCacher, self).generic_visit(node)


class DebugDuplicationVisitor(NodeVisitor):
    
    def __init__(self):
        super(DebugDuplicationVisitor, self).__init__()
        self.node_cache = set()
    
    def generic_visit(self, node: Node) -> None:
        if node in self.node_cache:
            node.show()
        else:
            self.node_cache.add(node)
        return super(DebugDuplicationVisitor, self).generic_visit(node)