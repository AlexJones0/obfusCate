from .. import interaction
from ..debug import *
from pycparser.c_ast import *
from pycparser.c_lexer import CLexer
from typing import Optional, Tuple, Type, Any, Iterable
import abc, enum, json, string, copy

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