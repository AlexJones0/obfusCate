import random
from typing import Iterable, Optional
from ctypes import Union
from .io import CSource, menu_driven_option, get_float, get_int
from abc import ABC, abstractmethod
from pycparser.c_ast import NodeVisitor, PtrDecl, ArrayDecl, InitList, Constant, \
    CompoundLiteral, Typename, TypeDecl, IdentifierType, BinaryOp, ID, StructRef, \
    Cast, FuncCall, ArrayRef, UnaryOp, BinaryOp, FuncDecl, Decl, Goto, Label, \
    NamedInitializer, Struct, Typedef, Enumerator, Assignment, Case, Default, \
    ExprList, EmptyStatement, If, Switch, While, DoWhile, For, Break, Continue, \
    Return
from pycparser import c_generator, c_lexer
from random import choices as randchoice, randint
from string import ascii_letters, digits as ascii_digits
from enum import Enum
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
    
    STRUCTURES_DEF = (Struct, Union, Enum,)
    STRUCTURES_REF = (StructRef, Union, Enum,)
    NONSTRUCTURES_DEF = (Decl, FuncDecl, Enumerator, Typedef,)
    NONSTRUCTURES_REF = None # TODO(,)
    LABELS_DEF = (Label,)
    LABELS_REF = (Goto,)
    kind_groups = dict()
    
    
    def __init__(self, t_unit=None):
        self.functions = set()
        self.info = {}
        self.processing_stack = []
        self.current_stmt = None
        self.current_function = None
        self.t_unit = t_unit
        self.processed = False
    
    def input(self, t_unit) -> None:
        self.processed = False
        self.t_unit = t_unit
    
    def process(self) -> None:
        self.visit(self.t_unit)
        self.processed = True
    
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
        if self.current_stmt is None:
            return # TODO error?
        info = self.info[self.processing_stack[-1]]
        index = info["stmtIndexes"][self.current_stmt]
        info["IdentUses"][index].add((name, kind))
    
    def record_ident_def(self, name, kind):
        if self.current_stmt is None:
            return # TODO error?
        info = self.info[self.processing_stack[-1]]
        index = info["stmtIndexes"][self.current_stmt]
        info["IdentDefs"][index].add((name, kind))
    
    def visit_FileAST(self, node):
        self.processing_stack.append(None)
        self.info[None] = {
            "node": None,
            "children": [],
            "currentIndex": 0,
            "stmtIndexes": {},
            "IdentUses": {},
            "IdentDefs": {},
        }
        for child in node.children():
            self.record_stmt(child)
        NodeVisitor.generic_visit(self, node)
        self.processing_stack = self.processing_stack[:-1]
    
    def visit_Compound(self, node, params=None):
        # Record the Compound Statement in the scope tree if necessary
        self.info[self.processing_stack[-1]]["children"].append(node)
        # Initialise information tracking about the block, and add to the processing stack.
        self.processing_stack.append(node)
        self.info[node] = {
            "node": node,
            "children": [],
            "currentIndex": 0,
            "stmtIndexes": {},
            "IdentUses": {},
            "IdentDefs": {},
        }
        # Record parameters if any given
        if params is not None:
            self.record_stmt(params)
            NodeVisitor.generic_visit(self, params)
        # Record all the children as statements 
        for child in node.children():
            self.record_stmt(child)
        # Walk the AST as normal
        NodeVisitor.generic_visit(self, node)
        # Pop the compound from the processing stack
        self.processing_stack = self.processing_stack[:-1]
    
    def visit_FuncDef(self, node):
        # First we log information for the function and its block.
        if node.body is not None:
            self.functions.add(node)
        # Then we augment the following compound with parameter definitions
        self.visit_Compound(node.body, params=node.param_decls)
        # Finally, we continue walking the tree as normal
        if node.decl is not None:
            self.visit(node.decl)
    
    def generic_visit(self, node):
        if self.is_stmt(node):
            self.current_stmt = node
        return NodeVisitor.generic_visit(self, node)
        
        
        
        """# Available symbol types (which can have the same names) are:
        # We first consider type declarations 
        if isinstance(node, (Typedef, ))
        
        # TODO what is a Typename? What is it actually used for? Think its a reference but idk?
        if isinstance(node, (Decl, Enumerator, Label, Struct, Typedef, ))
        # TODO Enum can be used in decl (definition) or referenced in a TypeDecl (used)
        
        if isinstance(node, (Decl, Enum, Enumerator, Label, Struct, Typedef, Union,)): # 
        if isinstance(node, (ArrayRef, Decl, Enum, Enumerator, FuncCall, Goto, ID, Label, NamedInitializer, Struct, StructRef, Typedef, Typename, Union, ))
        # IdentifierType -> self.names # TODO is this typedef stuff? check? yeah its for references!
        # TypeDecl -> declname
        return NodeVisitor.generic_visit(self, node)"""


# Control Flow Graph generation - we need ...

# Expression type evaluation - we need ...