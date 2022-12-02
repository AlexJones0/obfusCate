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

class TypeKinds(enum.Enum): # Could also call tags?
    STRUCTURE = 0
    LABEL = 1
    NONSTRUCTURE = 2

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
    
    # TODO it feels like switches might break this? Maybe need to
    # do some testing?
    
    def __init__(self, t_unit=None):
        self.functions = set()
        self.typedefs = set()
        self.parent_block = dict()
        self.parent_statement = dict()
        self.idents = dict() # Maps AST node to ident name attr, Kind
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
    
    # TODO can I generalise some of these functions - just the same but use "IdentDefs" or "IdentUses" - can definitely make higher order
    
    def get_scope_definitions(self, compound: Compound, from_stmt: Node = None, to_stmt: Node = None):
        # TODO should I calculate and cache scope-level stuff at the end instead?
        info = self.info[compound]
        if from_stmt is None:
            from_index = 0 # Set to start, whole scope
        else:
            from_index = info["stmtIndexes"][from_stmt]
        if to_stmt is None:
            to_index = info["currentIndex"] # Set to end, whole scope
        else:
            to_index = info["stmtIndexes"][to_stmt] + 1 # Set to include up to the stmt
        definitions = set()
        for i in range(from_index, to_index):
            stmt_defs = info["IdentDefs"][i]
            definitions = definitions.union(stmt_defs)
        return definitions
    
    def get_scope_usage(self, compound: Compound, from_stmt: Node = None, to_stmt: Node = None):
        info = self.info[compound]
        if from_stmt is None:
            from_index = 0 # Set to start, whole scope
        else:
            from_index = info["stmtIndexes"][from_stmt]
        if to_stmt is None:
            to_index = info["currentIndex"] # Set to end, whole scope
        else:
            to_index = info["stmtIndexes"][to_stmt] + 1 # Set to include up to the stmt
        usage = set()
        for i in range(from_index, to_index):
            stmt_usage = info["IdentUses"][i]
            usage = usage.union(stmt_usage)
        return usage
    
    def get_nested_scope_definitions(self, compound: Compound, from_stmt = None, to_stmt = None):
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
    
    def get_nested_scope_usage(self, compound: Compound, from_stmt = None, to_stmt = None):
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
            child = scope_path[i-1]
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
    
    def record_ident_usage(self, node, attr, kind, altname=None):
        name = altname if altname is not None else getattr(node, attr)
        if node in self.idents:
            self.idents[node].append((attr, kind))
        else:
            self.idents[node] = [(attr, kind)]
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
    
    def record_ident_def(self, node, attr, kind, altname=None):
        name = altname if altname is not None else getattr(node, attr)
        if node in self.idents:
            self.idents[node].append((attr, kind))
        else:
            self.idents[node] = [(attr, kind)]
        if self.current_structure is not None and self.current_structure.name is not None:
            name = self.current_structure.name + "." + name
        info = self.info[self.processing_stack[-1]]
        index = info["stmtIndexes"][info["currentStmt"]]
        info["IdentDefs"][index].add((name, kind))
    
    def visit_FileAST(self, node):
        self.processing_stack.append(None)
        self.info[None] = {
            "parent": None,
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
        if self.is_stmt(node): # TODO check and test with this added
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        # Record the Compound Statement in the scope tree if necessary
        parent = self.processing_stack[-1]
        currentStmt = self.info[parent]["currentStmt"]
        self.info[parent]["children"].append((node, currentStmt))
        # Initialise information tracking about the block, and add to the processing stack.
        self.info[node] = {
            "parent": self.processing_stack[-1],
            "children": [],
            "currentStmt": None,
            "currentIndex": 0,
            "stmtIndexes": {},
            "IdentUses": {},
            "IdentDefs": {},
        }
        self.processing_stack.append(node)
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
            self.record_ident_def(node.decl, 'name', TypeKinds.NONSTRUCTURE)
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
        self.parent_statement[node.decl] = self.info[self.processing_stack[-1]]["currentStmt"]
        self.parent_statement[node.decl.type] = self.info[self.processing_stack[-1]]["currentStmt"]
        self.parent_statement[node.decl.type.args] = self.info[self.processing_stack[-1]]["currentStmt"]
        # TODO can we just ignore walking the tree like I do above?
        # TODO should I make the compound run the entire decl instead of just the params? idk
        self.current_function = temp
    
    def visit_Typedef(self, node):
        if self.is_stmt(node):
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        if node.name is not None:
            self.typedefs.add(node.name)
            self.record_ident_def(node, 'name', TypeKinds.NONSTRUCTURE)
        NodeVisitor.generic_visit(self, node)
    
    def visit_Enumerator(self, node):
        if node.name is not None:
            self.record_ident_def(node, 'name', TypeKinds.NONSTRUCTURE)
        NodeVisitor.generic_visit(self, node)
    
    def visit_Decl(self, node): # Handle variable and function definitions
        if self.is_stmt(node):
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        if node.name is not None and (node.type is None or not isinstance(node.type, FuncDecl)): # Don't re-add funcdefs
            self.record_ident_def(node, 'name', TypeKinds.NONSTRUCTURE)
        if node.name is None and node.type is not None and isinstance(node.type, (Enum, Struct, Union,)):
            self.record_ident_def(node.type, 'name', TypeKinds.STRUCTURE)
        if node.name is not None and node.type is not None and node.type.type is not None and \
            isinstance(node.type.type, (Enum, Struct, Union,)):
                self.record_ident_usage(node.type.type, 'name', TypeKinds.STRUCTURE)
        if node.name is not None and node.type is not None and node.type.type is not None and \
            isinstance(node.type.type, Struct) and node.init is not None and isinstance(node.init, InitList) \
            and node.init.exprs is not None:
                temp = self.current_structure
                for expr in node.init.exprs:
                    if isinstance(expr, NamedInitializer):
                        name = ".".join([n.name for n in expr.name])
                        self.current_structure = (expr, node.type.type.name)
                        self.record_ident_usage(expr, 'name', TypeKinds.NONSTRUCTURE, altname=name)
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
            self.record_ident_def(node, 'name', TypeKinds.LABEL)
        NodeVisitor.generic_visit(self, node)
    
    def visit_ID(self, node): 
        if self.is_stmt(node):
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        if node.name is not None:
            self.record_ident_usage(node, 'name', TypeKinds.NONSTRUCTURE)
        NodeVisitor.generic_visit(self, node)
    
    def visit_IdentifierType(self, node):
        # TODO not sure why there can be multiple names here - need to check TODO
        name = ".".join(node.names)
        self.record_ident_usage(node, 'names', TypeKinds.NONSTRUCTURE, altname=name)
        #if node.names is not None:
        #    for name in node.names:
        #        if name in self.typedefs:
        #            self.record_ident_usage(name, TypeKinds.NONSTRUCTURE)
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
            self.record_ident_usage(node, 'name', TypeKinds.LABEL)
        NodeVisitor.generic_visit(self, node)
    
    def visit_NamedInitializer(self, node):
        temp = self.current_structure
        self.current_structure = node
        NodeVisitor.generic_visit(self, node)
        self.current_structure = temp
    
    def generic_visit(self, node):
        if self.is_stmt(node): # TODO this is double-checked in some cases - see if I can avoid (maybe replace generic_visit in specified functions?)
            self.info[self.processing_stack[-1]]["currentStmt"] = node
        # Record the statement the node is related to
        self.parent_statement[node] = self.info[self.processing_stack[-1]]["currentStmt"]
        NodeVisitor.generic_visit(self, node)


# Control Flow Graph generation - we need ...

# Expression type evaluation - we need ...