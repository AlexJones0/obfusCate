import random
from typing import Iterable, Optional
from .io import CSource, menu_driven_option, get_float, get_int
from abc import ABC, abstractmethod
from pycparser.c_ast import NodeVisitor, PtrDecl, ArrayDecl, InitList, Constant, \
    CompoundLiteral, Typename, TypeDecl, IdentifierType, BinaryOp, ID, StructRef, \
    Cast, FuncCall, ArrayRef, UnaryOp, BinaryOp, FuncDecl, Decl, Goto, Label, \
    NamedInitializer, Struct, Typedef, Enumerator, Assignment, Case, Default, \
    ExprList, EmptyStatement, If, Switch, While, DoWhile, For, Break, Continue, \
    Return, Enum, Union, Compound, Node
from pycparser import c_generator, c_lexer
from random import choices as randchoice, randint
from string import ascii_letters, digits as ascii_digits
import enum
from math import sqrt, floor

# TODO remove unnecesary imports when done

# Identifier analysis - we need to determine
#  1. What identifiers exist where
#  2. What identifers are used in each
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
    """ TODO """
    
    #CS_tree_children = dict() # Tree of only Compound Statement AST nodes stored by storing the children of each node
    #CS_statements = dict() # Map of Compound Statement AST nodes to Maps of statements to index numbers.
    #identifier_usage = dict() # Map of Compound Statement AST nodes to Maps of statement indexes to identifiers used in that statement.
    #identifier_defined = dict() # Map of Compound Statement AST nodes to Maps of statement indexes to identifier definitions in that statement.
    
    class TypeKinds(enum.Enum): # Could also call tags?
        STRUCTURE = 0
        LABEL = 1
        NONSTRUCTURE = 2
    
    
    def __init__(self, t_unit=None):
        self.functions = set()
        self.typedefs = set()
        self.current_function = None
        self.info = {}
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
    
    def get_scope_definitions(self, compound: Compound):
        # TODO should I calculate and cache scope-level stuff at the end instead?
        info = self.info[compound]
        definitions = set()
        for i in range(0, info["currentIndex"]):
            stmt_defs = info["IdentDefs"][i]
            definitions = definitions.union(stmt_defs)
        return definitions
    
    def get_scope_usage(self, compound: Compound):
        info = self.info[compound]
        usage = set()
        for i in range(0, info["currentIndex"]):
            stmt_usage = info["IdentUses"][i]
            usage = usage.union(stmt_usage)
        return usage
    
    def get_nested_scope_definitions(self, compound: Compound):
        pass
    
    def get_nested_scope_usage(self, compound: Compound):
        pass
    
    def get_stmt_definitions(self, stmt: Node):
        pass
    
    def get_stmt_usage(self, stmt: Node):
        pass
    
    def get_stmt_compound(self, stmt: Node) -> Optional[Compound]:
        pass
    
    def get_definitions_at_stmt(self, stmt: Node, compound: Compound = None):
        pass
    
    def get_usage_at_stmt(self, stmt: Node, compound: Compound = None):
        pass
    
    def is_stmt(self, stmt_node) -> bool:
        info = self.info[self.processing_stack[-1]]
        return stmt_node in info["stmtIndexes"]
    
    def record_stmt(self, stmt_node):
        node = self.processing_stack[-1]
        info = self.info[node]
        index = self.info[node]["currentIndex"]
        info["currentIndex"] += 1
        info["stmtIndexes"][stmt_node] = index
        info["IdentUses"][index] = set()
        info["IdentDefs"][index] = set()
    
    def record_ident_usage(self, name, kind):
        if self.current_structure is not None:
            if isinstance(self.current_structure, StructRef) and name == self.current_structure.field.name:
                name = self.current_structure.name.name + "." + name
            elif isinstance(self.current_structure, NamedInitializer):
                return
            elif isinstance(self.current_structure, tuple) and len(self.current_structure) == 2 and \
                isinstance(self.current_structure[0], NamedInitializer):
                    name = self.current_structure[1] + "." + name
        info = self.info[self.processing_stack[-1]]
        index = info["stmtIndexes"][info["currentStmt"]]
        info["IdentUses"][index].add((name, kind))
    
    def record_ident_def(self, name, kind):
        if self.current_structure is not None and self.current_structure.name is not None:
            name = self.current_structure.name + "." + name
        info = self.info[self.processing_stack[-1]]
        index = info["stmtIndexes"][info["currentStmt"]]
        info["IdentDefs"][index].add((name, kind))
    
    def visit_FileAST(self, node):
        self.processing_stack.append(None)
        self.info[None] = {
            "children": [],
            "currentStmt": None,
            "currentIndex": 0,
            "stmtIndexes": {},
            "IdentUses": {},
            "IdentDefs": {},
        }
        for child in node.children():
            self.record_stmt(child[1])
        NodeVisitor.generic_visit(self, node)
        self.processing_stack = self.processing_stack[:-1]
    
    def visit_Compound(self, node, params=None):
        # Record the Compound Statement in the scope tree if necessary
        self.info[self.processing_stack[-1]]["children"].append(node)
        # Initialise information tracking about the block, and add to the processing stack.
        self.processing_stack.append(node)
        self.info[node] = {
            "children": [],
            "currentStmt": None,
            "currentIndex": 0,
            "stmtIndexes": {},
            "IdentUses": {},
            "IdentDefs": {},
        }
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
    
    def visit_FuncDef(self, node):
        if self.is_stmt(node):
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        # First we log information about the function as a statement
        if node.decl is not None and node.decl.name is not None:
            self.record_ident_def(node.decl.name, self.TypeKinds.NONSTRUCTURE)
        # Next we log information for the function and its block.
        temp = self.current_function
        if node.body is not None:
            self.functions.add(node)
            self.current_function = node
        # Then we augment the following compound with parameter definitions
        self.visit_Compound(node.body, params=node.decl.type.args)
        """# Finally, we continue walking the tree as normal
        if node.decl is not None:
            self.visit(node.decl)"""
        # TODO can we just ignore walking the tree like I do above?
        # TODO should I make the compound run the entire decl instead of just the params? idk
        self.current_function = temp
    
    def visit_Typedef(self, node):
        if self.is_stmt(node):
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        if node.name is not None:
            self.typedefs.add(node.name)
            self.record_ident_def(node.name, self.TypeKinds.NONSTRUCTURE)
        NodeVisitor.generic_visit(self, node)
    
    def visit_Enumerator(self, node):
        if node.name is not None:
            self.record_ident_def(node.name, self.TypeKinds.NONSTRUCTURE)
        NodeVisitor.generic_visit(self, node)
    
    def visit_Decl(self, node): # Handle variable and function definitions
        if self.is_stmt(node):
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        if node.name is not None and (node.type is None or not isinstance(node.type, FuncDecl)): # Don't re-add funcdefs
            self.record_ident_def(node.name, self.TypeKinds.NONSTRUCTURE)
        if node.name is None and node.type is not None and isinstance(node.type, (Enum, Struct, Union,)):
            self.record_ident_def(node.type.name, self.TypeKinds.STRUCTURE)
        if node.name is not None and node.type is not None and node.type.type is not None and \
            isinstance(node.type.type, (Enum, Struct, Union,)):
                self.record_ident_usage(node.type.type.name, self.TypeKinds.STRUCTURE)
        if node.name is not None and node.type is not None and node.type.type is not None and \
            isinstance(node.type.type, Struct) and node.init is not None and isinstance(node.init, InitList) \
            and node.init.exprs is not None:
                temp = self.current_structure
                for expr in node.init.exprs:
                    name = ".".join([n.name for n in expr.name])
                    self.current_structure = (expr, node.type.type.name)
                    if isinstance(expr, NamedInitializer):
                        self.record_ident_usage(name, self.TypeKinds.NONSTRUCTURE)
                self.current_structure = temp
        NodeVisitor.generic_visit(self, node)
    
    def visit_Union(self, node):
        temp = self.current_structure
        self.current_structure = node
        NodeVisitor.generic_visit(self, node)
        self.current_structure = temp
    
    def visit_Struct(self, node):
        temp = self.current_structure
        self.current_structure = node
        NodeVisitor.generic_visit(self, node)
        self.current_structure = temp
    
    def visit_Label(self, node):
        if self.is_stmt(node):
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        if node.name is not None:
            self.record_ident_def(node.name, self.TypeKinds.LABEL)
        NodeVisitor.generic_visit(self, node)
    
    def visit_ID(self, node): 
        if self.is_stmt(node):
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        if node.name is not None:
            self.record_ident_usage(node.name, self.TypeKinds.NONSTRUCTURE)
        NodeVisitor.generic_visit(self, node)
    
    def visit_IdentifierType(self, node):
        # TODO not sure why there can be multiple names here - need to check TODO
        if node.names is not None:
            for name in node.names:
                if name in self.typedefs:
                    self.record_ident_usage(name, self.TypeKinds.NONSTRUCTURE)
        NodeVisitor.generic_visit(self, node)
    
    def visit_StructRef(self, node):
        if self.is_stmt(node):
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        temp = self.current_structure
        self.current_structure = node
        NodeVisitor.generic_visit(self, node)
        self.current_structure = temp
        
    def visit_Goto(self, node):
        if self.is_stmt(node):
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        if node.name is not None:
            self.record_ident_usage(node.name, self.TypeKinds.LABEL)
        NodeVisitor.generic_visit(self, node)
    
    def visit_NamedInitializer(self, node):
        temp = self.current_structure
        self.current_structure = node
        NodeVisitor.generic_visit(self, node)
        self.current_structure = temp
    
    def generic_visit(self, node):
        if self.is_stmt(node): # TODO this is double-checked in some cases - see if I can avoid (maybe replace generic_visit in specified functions?)
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        NodeVisitor.generic_visit(self, node)


# Control Flow Graph generation - we need ...

# Expression type evaluation - we need ...