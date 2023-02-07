from typing import Iterable, Optional, Callable
from .interaction import CSource
from .debug import *
from pycparser.c_ast import *
from pycparser.c_lexer import CLexer
from pycparser.c_generator import CGenerator
from string import ascii_letters
import enum

# TODO Salvage or Scrap
"""REALISTIC_VAR_NAMES = []
with open(".\\app\\var_names.txt", "r") as f:
    for line in f.read().splitlines():
        line = line.strip()
        if not line.startswith("#") and len(line) != 0:
            REALISTIC_VAR_NAMES.append(line)"""

def is_initialised(source: CSource, libraries: Iterable[str]) -> Iterable[bool]:
    """Checks if each of the given libraries are initialised in the provided
    source file's contents such that they can be used in code safely.

    Inputs:
        - source (CSource): The source file to check within
        - libraries (Iterable[str]): The names of the libraries to check for.

    Returns an Iterable[bool] of the same size as the input libraries describing
    whether that library was initialised (included or not)."""
    libs = ["<" + l + ">" for l in libraries]
    inits = [False for lib in libraries]
    for line in source.contents.split("\n"):
        line = [t for t in line.strip().split(" ") if len(t) > 0]
        if len(line) >= 2 and line[0] in ["#include", "%:include", "??=include"]:
            for i, lib in enumerate(libs):
                if line[1] == lib:
                    inits[i] = True
    return inits


# TODO a lot of ident parsing is done in the wrong order through the AST, which will
# give random stuff in the wrong order - not a huge deal but would be nice to fix


class TypeKinds(enum.Enum):  # Could also call tags?
    STRUCTURE = 0
    LABEL = 1
    NONSTRUCTURE = 2


class NewVariableUseAnalyzer(NodeVisitor):
    """TODO"""

    def __init__(self, t_unit: CSource = None):
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
                if self.current_compound is not node:
                    self.compound_stmt_map[self.current_compound].append(node)
            self.node_stmt_map[node] = self.current_stmt
            result = func(self, node, *args, **kwargs)
            if is_stmt:
                self.current_stmt = old_stmt
            return result

        return wrapper

    def load(self, t_unit: CSource) -> None:
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

    def get_unique_identifier(self, node, type, compound=None, function=None, exclude=None):
        stmt = self.get_stmt_from_node(node)
        if compound is None:
            compound = self.get_stmt_compound(stmt)
        defined = self.get_usage_from_stmt(stmt).union(
            self.get_scope_definitions(compound)
        )
        if function is not None:
            defined = defined.union(set((x, TypeKinds.LABEL) for x in self.labels[function]))
        defined = set(x[0] for x in defined if x[1] == type)
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
            choices = ascii_letters
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
        del self.definition_uses[(stmt_node, name, kind)]

    def is_stmt(self, stmt_node):
        return stmt_node in self.stmts

    def get_stmt_from_node(self, ast_node):
        return self.node_stmt_map[ast_node]

    def get_last_definition(self, name, kind):
        for scope in self.current_definitions[::-1]:
            if (name, kind) in scope:
                return scope[(name, kind)]
        return None

    def record_ident_def(self, node, name, locations, kind, alt_scope=None):
        node = self.get_stmt_from_node(node)
        if self.current_structure is not None:
            if self.current_structure.name is not None:
                name = self.current_structure.name + "." + name
            else:  # Using an anonymous (no-name) struct/union, so don't record variables
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
        if (
            node.type is not None
            and isinstance(node.type, TypeDecl)
            and node.type.declname is not None
        ):
            self.functions.add(node.type.declname)
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
        ### TODO why was the below code necessary?
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
            attributes = [
                (node, "name"),
                (node.type, "declname"),
            ]  # TODO all 'declname' stuff doesn't account for arraydecls and pointerdecls
            self.record_ident_def(node, node.name, attributes, TypeKinds.NONSTRUCTURE)
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
                attributes = [
                    (node, "name"),
                    (node.type, "declname"),
                ]  # TODO not right - different for funcs and vars
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
                ):
                    # Enum/Struct/Union definition
                    self.record_ident_def(
                        node, type_.name, [(type_, "name")], TypeKinds.STRUCTURE
                    )  # TODO slightly different from original - both now link to node instead of type_
                    if i == 1:  # Edge case where declaring and using at the same time
                        self.record_ident_usage(
                            node, type_.name, [(type_, "name")], TypeKinds.STRUCTURE
                        )
                else:  # Enum/Struct/Union usage
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
                alt_scope=self.current_definitions[1], # TODO look into fixing this it is breaking stuff
            ) # The above defines it in the function, but when looking at usage it may not be found
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
        name = ".".join(node.names)
        if name in self.typedefs:
            self.record_ident_usage(
                node, name, [(node, "names")], TypeKinds.NONSTRUCTURE
            )  # TODO need to account for 'names' attributes when renaming
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
            choices = ascii_letters
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
        name = ".".join(node.names)
        if name in self.typedefs:
            self.record_ident_usage(node, "names", TypeKinds.NONSTRUCTURE, altname=name)
        # if node.names is not None:
        #    for name in node.names:
        #        if name in self.typedefs:
        #            self.record_ident_usage(name, TypeKinds.NONSTRUCTURE)
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


class ExpressionTypeAnalyzer(NodeVisitor):
    
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
    
    def __init__(self, t_unit: Node) -> None:
        super(ExpressionTypeAnalyzer, self).__init__()
        self.t_unit = t_unit
        self.reset()
    
    def reset(self):
        self.type_aliases = [] # Stack of scopes of defined type aliases
        self.structs = [] # Stack of scopes of defined structs/union
        self.defined = [] # Stack of scopes of defined variables
        self.functions = {}
        self.params = {}
        self.in_param_list = False
        self.types = {None: self.SimpleType.OTHER}
        self.mutating = {None: False}
        self.processed = False

    def load(self, t_unit: CSource) -> None:
        self.t_unit = t_unit
        self.processed = False

    def process(self) -> None:
        self.visit(self.t_unit)
        self.processed = True
        
    def is_type(self, expr: Node, type_) -> bool:
        if expr not in self.types:
            return type_ is None
        return self.types[expr] == type_

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
        if self.in_param_list:
            self.defined.append(self.params)
            self.in_param_list = False
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
        
    def convert_type(self, node):
        if isinstance(node, PtrDecl):
            return self.Ptr(self.convert_type(node.type))
        elif isinstance(node, ArrayDecl):
            return self.Array(self.convert_type(node.type))
        elif isinstance(node, TypeDecl):
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
            if node.name is None:
                return self.SimpleType.OTHER
            struct = self.get_struct_type(node.name)
            if struct is not None:
                return struct
            return self.SimpleType.OTHER
        else:
            return self.SimpleType.OTHER
        
    def visit_FuncDef(self, node):
        if node.decl is not None and node.decl.name is not None and node.decl.type is not None and node.decl.type.type is not None:
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
            else:
                self.defined[-1][node.name] = self.convert_type(node.type)
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
        elif node.op in ["!", "sizeof"]:
            self.types[node] = self.SimpleType.INT
            self.mutating[node] = self.mutating[node.expr]
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
        mutating = False
        if node.name is not None:
            arr_type = self.types[node.name]
            if isinstance(arr_type, (self.Array, self.Ptr)):
                self.types[node] = arr_type.val
            else:
                self.types[node] = arr_type
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
        if node.name is not None:
            self.types[node] = self.get_func_type(node.name)
        self.mutating[node] = True # Pessimistic assumption (e.g. globals)
    
    def visit_Struct(self, node):
        if node.name is None:
            return
        if node.decls is not None:
            self.structs[-1][node.name] = node
            self.mutating[node] = True
        else:
            self.types[node] = self.get_struct_type(node.name)
            self.mutating[node] = False
    
    def visit_Union(self, node):
        if node.name is None:
            return
        if node.decls is not None:
            self.structs[-1][node.name] = node
            self.mutating[node] = True
        else:
            self.types[node] = self.get_struct_type(node.name)
            self.mutating[node] = False
    
    def visit_StructRef(self, node):
        self.generic_visit(node)
        if node.type is not None and node.name is not None and node.field is not None and node.field.name is not None:
            if node.type == ".":
                struct_type = self.types[node.name]
                if isinstance(struct_type, (Struct, Union)):
                    self.types[node] = self.get_struct_field_type(struct_type, node.field.name)
                else:
                    self.types[node] = self.SimpleType.OTHER
            elif node.type == "->":
                struct_type = self.types[node.name]
                if isinstance(struct_type, (self.Ptr, self.Array)):
                    struct_type = struct_type.val
                if isinstance(struct_type, (Struct, Union)):
                    self.types[node] = self.get_struct_field_type(struct_type, node.field.name)
                else:
                    self.types[node] = self.SimpleType.OTHER
        mutating = False
        if node.name is not None:
            mutating = mutating or self.mutating[node.name]
        if node.field is not None: # TODO can this be an expr? I don't think so?
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
    
    # TODO what is a CompoundLiteral? Do I need to account for it?


# TODO: abandoned for now, maybe finish another time?
class FormattedCGenerator(CGenerator):
    # NOTE: my code, but highly based on the original CGenerator object
    # which is being extended - I'm just replacing some of its functions
    # to remove whitespace that is being generated.
    # See: https://github.com/eliben/pycparser/blob/master/pycparser/c_generator.py
    
    def visit_FuncDef(self, node):
        decl = self.visit(node.decl)
        self.indent_level = 0
        body = self.visit(node.body)
        if node.param_decls:
            params = ';\n'.join(self.visit(p) for p in node.param_decls)
            return decl + '\n' + params + '; ' + body + ''
        else:
            return decl + ' ' + body + ''
        
    def visit_If(self, node):
        string = 'if ('
        if node.cond: 
            string += self.visit(node.cond)
        string += ') '
        string += self._generate_stmt(node.iftrue, add_indent=False)
        if node.iffalse:
            string += self._make_indent() + 'else '
            string += self._generate_stmt(node.iffalse, add_indent=False)
        return string
