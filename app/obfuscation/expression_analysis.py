""" File: obfuscation/expression_analysis.py
Implements the ExpressionAnalyzer class for performing expression type and 
mutability (the ability to cause potential side effects) analysis on C programs,
which are required both for identifier analysis techniques, and to determine
when certain obfuscation methods can be safely applied without potentially changing
the output of a program. 
"""
from .. import interaction
from ..debug import *
from .utils import VALID_INT_TYPES, VALID_REAL_TYPES
from pycparser.c_ast import *
from pycparser.c_lexer import CLexer
from typing import Optional, Tuple, Type, Any, Iterable
import abc, enum, json, string, copy


class ExpressionAnalyzer(NodeVisitor):
    """This class implements AST expression analysis, using bottom-up AST traversal
    to derive a type and mutability for the majority of nodes in the AST."""

    class SimpleType(Enum):
        """An Enum simplifying data types into integers, reals (floats/decimals), and
        other values to simplify the analysis process, as these are all that is needed."""

        INT = 0
        REAL = 1
        OTHER = 2

    class Ptr:
        """A simplified class to represent a pointer type in a C program."""

        def __init__(self, val: Any):
            """A constructor for the simplified Ptr type, taking the type it points to."""
            self.val = val

        def __eq__(self, other: Any) -> bool:
            """Determines whether this type is equivalent to another type, by specifically
            checking whether the other class is also a Ptr, and that both point to equal types."""
            return type(self) == type(other) and self.val == other.val

    class Array:
        """A simplified class to represent an array type in a C program."""

        def __init__(self, val: Any):
            """A constructor for the simplified Array type, taking the the type of values that are
            stored in the array."""
            self.val = val

        def __eq__(self, other: Any) -> bool:
            """Determines whether this type is equivalent to another type, by specifically
            checking whether the other class is also an Array, and that both store equal types."""
            return type(self) == type(other) and self.val == other.val

    NodeType = SimpleType | Ptr | Array | Struct | Union

    def __init__(self, t_unit: FileAST):
        """The constructor for the ExpressionAnalyzer class, creating necessary data structures.

        Args:
            t_unit (FileAST): The pycparser FileAST node representing the translation
            unit to analyze.
        """
        super(ExpressionAnalyzer, self).__init__()
        self.t_unit = t_unit
        self.reset()

    def reset(self) -> None:
        """Resets the state of the ExpressionAnalyzer, allowing it to be re-used."""
        # Attributes to store current state whilst traversing
        self.type_aliases = []  # Stack of scopes of defined type aliases
        self.structs = []  # Stack of scopes of defined structs/union
        self.defined_vars = []  # Stack of scopes of defined variables
        self.in_param_list = False
        self.processed = False

        # Attributes to track function and parameter definitions globally
        self.functions = {}
        self.params = {}

        # Attributes to represent the type and mutability of nodes.
        self.types = {None: self.SimpleType.OTHER}
        self.mutating = {None: False}

    def load(self, t_unit: FileAST) -> None:
        """Loads a given FileAST to analyse.

        Args:
            t_unit (FileAST): The FileAST representing the C translation unit.
        """
        self.t_unit = t_unit
        self.processed = False

    def process(self) -> None:
        """Processes the current AST, updating internal representations."""
        self.visit(self.t_unit)
        self.processed = True

    def is_type(self, expr: Node, type_: Type) -> bool:
        """Determines whether the program construct represented by a given AST node
        is of the type provided by using the stored internal representation.

        Args:
            expr (Node): The AST node to check.
            type_ (Type): The type to check for.

        Returns:
            bool: True if the construct is of that type, or False if not.
        """
        if expr not in self.types:
            return type_ is None
        return self.types[expr] == type_

    def get_type(self, expr: Node) -> NodeType | None:
        """Retrives the ExpressionAnalyzer's internal simplified type representation of
        the type of the given expression AST node.

        Args:
            expr (Node): The AST node to get the type of.

        Returns:
            NodeType | None: The type of the node.
        """
        if expr not in self.types:
            return None
        return self.types[expr]

    def is_mutating(self, expr: Node) -> bool:
        """Determines whether the program construct represented by a given AST node
        is mutating or not by using the stored internal representation.

        Args:
            expr (Node): The AST node to check.

        Returns:
            bool: True if the node *may* cause mutation in a C program, or false otherwise.
        """
        if expr not in self.mutating:
            return False
        return self.mutating[expr]

    def get_type_alias(self, name: str) -> NodeType | None:
        """Retrieves the current type that is aliased by a given name, if such an alias exists.

        Args:
            name (str): The type alias (typedef) to check for.

        Returns:
            NodeType | None: The corresponding type if an alias is defined; None if not.
        """
        for scope in self.type_aliases[::-1]:
            if name in scope:
                return scope[name]
        return None

    def get_var_type(self, name: str) -> NodeType | None:
        """Retrives the type of the current variable represented by a given name, if such
        a variable exists at this point in the program.

        Args:
            name (str): The name of the variable to get the type of.

        Returns:
            NodeType | None: The corresponding type if such a variable is defined; None if not.
        """
        for scope in self.defined_vars[::-1]:
            if name in scope:
                return scope[name]
        return None

    def get_struct_type(self, name: str) -> NodeType | None:
        """Retrieves the type of the current struct/union represented by a given name, if
        such a struct/union exists at this point in the program.

        Args:
            name (str): The name of the struct/union/enum to get the type of.

        Returns:
            NodeType | None: The corresponding type if such a tag is defined; None if not.
        """
        for scope in self.structs[::-1]:
            if name in scope:
                return scope[name]
        return None

    def get_struct_field_type(
        self, struct: Struct | Union, field: str
    ) -> NodeType | None:
        """Retrieves the type of the specified field of the specified struct/union, by
        recursively finding the type of any typed tag declarations with a matching name.

        Args:
            struct (Struct | Union): The struct/union to search for a field in.
            field (str): The name of the field to find the type of.

        Returns:
            NodeType | None: The corresponding type if such a field is defined; None if not.
        """
        for decl in struct.decls:
            if decl.name is not None and decl.name == field and decl.type is not None:
                return self.convert_type(decl.type)
        return None

    def standard_coalesce_types(self, types: Iterable[NodeType]) -> NodeType:
        """Performs 'standard' coalescing of types, which is defined such that
        the presence of any 'OTHER' type makes an 'OTHER', otherwise the presence
        of any 'REAL' type makes a 'REAL', otherwise the presence of any array or
        pointer makes an array or pointer to the coalescence of referenced types,
        and finally an integer otherwise. This essentially performs standard
        type coercion as is required by *most* functions in C, to avoid repeat
        definitions of functionality.

        Args:
            types (Iterable[NodeType]): The types to coalesce.

        Returns:
            NodeType: The coalesced type as described above.
        """
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

    def get_func_type(self, name: str) -> NodeType:
        """Fetches the type of a given function as it is known to the analyzer.

        Args:
            name (str): The name of the function to retrieve the type of.

        Returns:
            NodeType: The internally represented type of the function, or 'OTHER' otherwise
            (pessimistic assumption).
        """
        if name in self.functions:
            return self.functions[name]
        return self.SimpleType.OTHER

    def convert_type(self, node: Node | NodeType) -> NodeType:
        """Given an AST node or an existing simplified type, this method converts the
        type of that node to the analyzer's simplified type representation, recursively
        parsing to determine the type and construct an appropriate representation.

        Args:
            node (Node | NodeType): The AST node or type to convert.

        Returns:
            NodeType: The (recursively) converted simplified type.
        """
        if isinstance(node, PtrDecl):
            return self.Ptr(self.convert_type(node.type))
        elif isinstance(node, ArrayDecl):
            return self.Array(self.convert_type(node.type))
        elif isinstance(node, (TypeDecl, Typename)):
            return self.convert_type(node.type)
        elif isinstance(node, (IdentifierType, str)):
            if isinstance(node, IdentifierType):
                if node.names is None or len(node.names) == 0:
                    return self.SimpleType.OTHER
                name = "".join(node.names)
            else:
                name = node
            if name in VALID_INT_TYPES:
                return self.SimpleType.INT
            elif name in VALID_REAL_TYPES:
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

    def visit_FileAST(self, node: FileAST) -> None:
        """Visit a FileAST node, appending a dictionary to each tracking stack as
        this is the creation of a new scope, and then traversing the node."""
        self.type_aliases.append({})
        self.structs.append({})
        self.defined_vars.append({})
        self.generic_visit(node)
        self.defined_vars = self.defined_vars[:-1]
        self.structs = self.structs[:-1]
        self.type_aliases = self.type_aliases[:-1]

    def visit_Compound(self, node: Compound) -> None:
        """Visit a Compound node, appending a dictionary to each tacking stack as
        this is the creation of a new scope, and then traversing the node. If
        this compound refers to a function body (and as such the analyzer is storing
        some parameters), these parameters are incldued in the scope's defined variables."""
        self.type_aliases.append({})
        self.structs.append({})
        if self.params is not None and len(self.params) != 0:
            self.defined_vars.append(self.params)
            self.params = {}
        else:
            self.defined_vars.append({})
        self.generic_visit(node)
        self.defined_vars = self.defined_vars[:-1]
        self.structs = self.structs[:-1]
        self.type_aliases = self.type_aliases[:-1]

    def visit_ParamList(self, node: ParamList) -> None:
        """Visits a ParamList node, creating a dictionary to store contained parameters
        and setting a flag such that this context is known to the analyzer."""
        self.params = {}
        self.in_param_list = True
        self.generic_visit(node)
        self.in_param_list = False

    def visit_FuncDef(self, node: FuncDef) -> None:
        """Visits a FuncDef node, recording the function alongside its type so
        long as the function specifies a valid name and type, and then traversing it."""
        if (
            node.decl is not None
            and node.decl.name is not None
            and node.decl.type is not None
            and node.decl.type.type is not None
        ):
            self.functions[node.decl.name] = self.convert_type(node.decl.type.type)
        self.generic_visit(node)

    def visit_Typedef(self, node: Typedef) -> None:
        """Visits a Typedef node, recording the type alias so long as a valid
        name and type is specified, and then traverses the node normally."""
        if node.name is not None and node.type is not None:
            self.type_aliases[-1][node.name] = self.convert_type(node.type)
        self.generic_visit(node)

    def visit_Decl(self, node: Decl) -> None:
        """Visits a Decl node, recording the variable type listed by the declaration,
        alongside the type of the node itself. If the analyzer is currently in a parameter
        list, the declaration is stored as a parameter instead of a variable, such that
        it is included within the correct scope. A decl is considered to be mutating, as it
        involves creating a new variable."""
        if node.name is not None and node.type is not None:
            if self.in_param_list:
                self.params[node.name] = self.convert_type(node.type)
                self.types[node] = self.params[node.name]
            else:
                self.defined_vars[-1][node.name] = self.convert_type(node.type)
                self.types[node] = self.defined_vars[-1][node.name]
        else:
            self.types[node] = self.SimpleType.OTHER
        self.mutating[node] = True
        self.generic_visit(node)

    def visit_UnaryOp(self, node: UnaryOp) -> None:
        """Visits an UnaryOp node, first traversing it and then bottom-up deriving its type
        and mutability. Must separately consider increments/decrements, unary arithmetic/bitwise
        negation, logical negation, size and alignment retrieval, and pointer referencing and
        de-referencing."""
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
            self.mutating[node] = True  # pessimistic Assumption

    def visit_BinaryOp(self, node: BinaryOp) -> None:
        """Visits a BinaryOp node, first traversing it and then bottom-up deriving its type
        and mutability. Must separately consider arithmetic, logical operations, and bitwise
        operations in expressions."""
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
            self.types[node] = self.SimpleType.INT
            self.mutating[node] = self.mutating[node.left] or self.mutating[node.right]
        else:
            log(f"Unknown binary operator {node.op} encountered.")
            self.types[node] = self.SimpleType.OTHER
            self.mutating[node] = True  # Pessimistic assumption

    def visit_TernaryOp(self, node: TernaryOp) -> None:
        """Visits an UnaryOp node, first traversing it and then bottom-up deriving its type
        and mutability. Type is determined from either expression; mutability from both."""
        self.generic_visit(node)
        if node.iftrue is not None:
            self.types[node] = self.types[node.iftrue]
        elif node.iffalse is not None:
            self.types[node] = self.types[node.iffalse]
        self.mutating[node] = self.mutating[node.iftrue] or self.mutating[node.iffalse]

    def visit_Typename(self, node: Typename) -> None:
        """Visits a Typename node, first traversing it and then bottom-up deriving its type
        and mutability. Simply converts and stores the node's types, with no mutability."""
        self.generic_visit(node)
        if node.type is not None:
            self.types[node] = self.convert_type(node.type)
        self.mutating[node] = False

    def visit_Cast(self, node: Cast) -> None:
        """Visits a Cast node, first traversing it and then bottom-up deriving its type
        and mutability. The node's type is determined from the type expression being casted
        to, whereas mutability is determined by the node's expression."""
        self.generic_visit(node)
        if node.to_type is not None:
            self.types[node] = self.types[node.to_type]
        self.mutating[node] = (
            self.mutating[node.expr] if node.expr is not None else False
        )

    def visit_ArrayRef(self, node: ArrayRef) -> None:
        """Visits an ArrayRef node, first traversing it and then bottom-up deriving its type
        and mutability. The 'name' and 'subscript' are checked to determine which corresponds
        to an array type and which correspodns to an integer type, as this is not enforced.
        Type is then determined by accessing the value of the Array/Ptr value type, and
        mutability is derived from the mutability of the 'name' and 'subscript' expressions."""
        self.generic_visit(node)
        name_type = (
            self.SimpleType.OTHER if node.name is None else self.types[node.name]
        )
        sub_type = (
            self.SimpleType.OTHER
            if node.subscript is None
            else self.types[node.subscript]
        )
        is_name_arr = isinstance(name_type, (self.Array, self.Ptr))
        is_sub_arr = isinstance(sub_type, (self.Array, self.Ptr))
        if not is_name_arr and not is_sub_arr:
            self.types[node] = self.SimpleType.OTHER
        elif is_name_arr and is_sub_arr:
            self.types[node] = self.SimpleType.OTHER  # Pessimistic assumpion
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

    def visit_Assignment(self, node: Assignment) -> None:
        """Visits an Assignment node, first traversing it and then bottom-up deriving its type
        and mutability. Type is determined from the expression (lvalue) type, and mutability
        is set to True as we are performing assignment, changing the value of something."""
        self.generic_visit(node)
        if node.lvalue is not None:
            self.types[node] = self.types[node.lvalue]
        self.mutating[node] = True

    def visit_Enum(self, node: Enum) -> None:
        """Visits an Enum node, first traversing it and then bottom-up deriving its type
        and mutability. This is static: they are of integral (int) type, with no mutability."""
        self.generic_visit(node)
        if node.name is not None:
            self.types[node] = self.SimpleType.INT
        self.mutating[node] = False

    def visit_FuncCall(self, node: FuncCall) -> None:
        """Visits a FuncCall node, first traversing it and then bottom-up deriving its type
        and mutability. Type is determined by retrieving the relevant type of the function
        being called, and we assume mutation pessimistically."""
        self.generic_visit(node)
        if node.name is not None and node.name.name is not None:
            self.types[node] = self.get_func_type(node.name.name)
        self.mutating[node] = True  # Pessimistic assumption (e.g. globals)

    def visit_Struct(self, node: Struct) -> None:
        """Visits a Struct node, first traversing it and then bottom-up deriving its type
        and mutability. Type and mutability is based on context, deriving whether the
        struct is a definition (it has decls) or not."""
        if node.decls is not None:
            self.structs[-1][node.name] = node
            self.types[node] = node
            self.mutating[node] = True
        else:
            self.types[node] = self.get_struct_type(node.name)
            self.mutating[node] = False

    def visit_Union(self, node: Union) -> None:
        """Visits a Union node, first traversing it and then bottom-up deriving its type
        and mutability. Type and mutability is based on context, deriving whether the
        union is a definition (it has decls) or not."""
        if node.decls is not None:
            self.structs[-1][node.name] = node
            self.types[node] = node
            self.mutating[node] = True
        else:
            self.types[node] = self.get_struct_type(node.name)
            self.mutating[node] = False

    def visit_StructRef(self, node: StructRef) -> None:
        """Visits a StructRef node, first traversing it and then bottom-up deriving its type
        and mutability. Type and mutability is determined by coalesing the type and mutability
        of the 'name' and 'field' expressions. '.' and '->' are parsed seperately to retrieve
        the type directly or dereference first."""
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
        if node.field is not None:
            mutating = mutating or self.mutating[node.field]
        self.mutating[node] = mutating

    def visit_Constant(self, node: Constant) -> None:
        """Visits a Constant node, first traversing it and then bottom-up deriving its type
        and mutability. Type is directly converted and stored, and constants are non-mutable."""
        self.generic_visit(node)
        if node.type is not None:
            self.types[node] = self.convert_type(node.type)
        self.mutating[node] = False

    def visit_ID(self, node: ID) -> None:
        """Visits an ID node, first traversing it and then bottom-up deriving its type
        and mutability. IDs do not cause mutation, and type is based on the type of the current
        defined variable with that identifier name."""
        self.generic_visit(node)
        if node.name is not None:
            self.types[node] = self.get_var_type(node.name)
        self.mutating[node] = False

    def visit_InitList(self, node: InitList) -> None:
        """Visits an InitList node, first traversing it and then bottom-up deriving its type
        and mutability. Lists themselves have no type, but mutability is determined
        by the mutability of the relevant initialiser expressions."""
        self.generic_visit(node)
        mutating = False
        if node.exprs is not None:
            # Type cannot be determined from the init list (e.g. an empty list)
            for expr in node.exprs:
                mutating = mutating or self.mutating[expr]
        self.mutating[node] = mutating

    def visit_ExprList(self, node: ExprList) -> None:
        """Visits an ExprList node, first traversing it and then bottom-up deriving its type
        and mutability. Lists themselves have no single type that can be represented in this
        simplified abstraction, but mutability is determined by the mutability of the relevant
        constituent expressions."""
        self.generic_visit(node)
        mutating = False
        if node.exprs is not None:
            for expr in node.exprs:
                mutating = mutating or self.mutating[expr]
        self.mutating[node] = mutating

    def visit_CompoundLiteral(self, node: CompoundLiteral) -> None:
        """Visits a CompoundLiteral node, first traversing it and then bottom-up deriving its type
        and mutability. Type and mutability are directly derived/converted from the type and
        mutability of the initialisation value expression."""
        self.generic_visit(node)
        if node.type is not None:
            self.types[node] = self.convert_type(node.type)
        else:
            self.types[node] = self.SimpleType.OTHER
        if node.init is not None:
            self.mutating[node] = self.mutating[node.init]
        else:
            self.mutating[node] = False

    def visit_NamedInitializer(self, node: NamedInitializer) -> None:
        """Visits a NamedInitializer node, first traversing it and then bottom-up deriving its type
        and mutability. Type is directly determined from the type of the intializer list, and this
        is always set to be mutating as values are being initialized."""
        self.generic_visit(node)
        if node.expr is not None:
            self.types[node] = self.types[node.expr]
            self.mutating[node] = True
