""" File: obfuscation/identifier_analysis.py
Implements the IdentifierAnalyzer class for performing identifer usage and 
liveness analysis on C programs, allowing the reasoning about different
identifier names within a program.
"""
from .. import interaction
from ..debug import *
from .expression_analysis import ExpressionAnalyzer
from .utils import NameSpace
from pycparser.c_ast import *
from pycparser.c_lexer import CLexer
from typing import Tuple, Any, Iterable
import string, copy


Scope = Compound | FileAST
Identifier = Tuple[str, NameSpace]
Location = Tuple[Node, str | Tuple[str, ...]]


class IdentifierAnalyzer(NodeVisitor):
    """A class for analysing the liveness and usage of identifiers throughout C programs."""

    def __init__(self, source: interaction.CSource | None = None) -> None:
        """A constructor for the variable use analyzer, initialising
        variables and data structures used during and after analysis.

        Args:
            source (interaction.CSource | None, optional): The source file
            to analyze. Defaults to None, where it can be passed in later
            using the `load()` function.
        """

        # Construct membership sets/dicts
        self.stmts = set()
        self.idents = set()
        self.functions = set()
        self.typedefs = set()
        self.struct_members = {}
        self.funcspecs = {}  # Dict mapping functions to their specifications
        self.funclabels = {}  # Dict mapping a function to all its labels.
        self.funcgotos = {}  # Same as above for gotos, to allow backfilling.

        # Dicts for statement identifier definitions and usage
        self.stmt_usage = {}
        self.stmt_definitions = {}
        self.definition_uses = {}  # Dictionary mapping (statement, ident, namespace)
        # triples to all locations that use it.

        # Program structure trees
        self.compound_children = {}
        self.compound_parent = {}
        self.stmt_compound_map = {}
        self.compound_stmt_map = {}
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
        self.expression_analyzer = ExpressionAnalyzer(
            source.t_unit if source is not None else None
        )

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
        """Processes the currently loaded source file, analyzing it."""
        if self.source is None or self.processed:
            return
        self.expression_analyzer.process()
        self.visit(self.source.t_unit)
        self.processed = True

    def get_stmt_definitions(self, stmt: Node) -> list[Identifier]:
        """Returns a list of identifier definitions made in a statement as are
        known to the analyzer.

        Args:
            stmt (Node): The AST root node of the statement subtree.

        Returns:
            list[Identifier]: A list of identifiers (name and namespace pairs).
        """
        return self.stmt_definitions[stmt]

    def get_stmt_usage(self, stmt: Node) -> list[Identifier]:
        """Returns a list of identifier usages made in a statement as are
        known to the analyzer.

        Args:
            stmt (Node): The AST root node of the statement subtree.

        Returns:
            list[Identifier]: A list of identifiers (name and namespace pairs).
        """
        return self.stmt_usage[stmt]

    def get_stmt_compound(self, stmt: Node) -> Scope:
        """Returns the scope (compound or FileAST) that a given statement
        is located in as is known to the analyzer.

        Args:
            stmt (Node): The AST root node of the statement subtree.

        Returns:
            Scope: The Compound or FileAST the statement is a child of.
        """
        return self.stmt_compound_map[stmt]

    def get_stmt_func(self, stmt: Node) -> FuncDef | None:
        """Returns the function that a given statement is located in
        as is known to the analyzer.

        Args:
            stmt (Node): The AST root node of the statement subtree.

        Returns:
            FuncDef | None: The function the statement is in, or None if
            the statement is not in a function.
        """
        return self.stmt_func_map[stmt]

    def get_stmt_from_node(self, ast_node: Node) -> Node:
        """Returns the root AST node of the statement that the provided AST
        node is located within, as is known to the analyzer.

        Args:
            ast_node (Node): The AST node to get the statement of.

        Returns:
            Node: The root AST node of the containing statement.
        """
        return self.node_stmt_map[ast_node]

    def is_stmt(self, ast_node: Node) -> bool:
        """Returns whether the given AST node is the root AST node of some
        statement in the program body or not, as is known to the analyzer.

        Args:
            stmt_node (Node): The AST node to check.

        Returns:
            bool: True if the AST node is a statement node, False otherwise.
        """
        return ast_node in self.stmts

    def get_compounds_in_subtree(self, compound: Scope) -> list[Compound]:
        """Returns a list of all compounds that are descendants of the given
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

    def _coalesce_indexes(
        self, compound: Scope, from_stmt: Node | None, to_stmt: Node | None
    ) -> Tuple[int, int]:
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

    def get_scope_definitions(
        self,
        compound: Scope,
        from_stmt: Node | None = None,
        to_stmt: Node | None = None,
    ) -> list[Identifier]:
        """Gets all identifier definitions of statements within a scope,
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

    def get_scope_usage(
        self,
        compound: Scope,
        from_stmt: Node | None = None,
        to_stmt: Node | None = None,
    ) -> list[Identifier]:
        """Gets all identifier usages of statements within a scope,
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

    def get_nested_scope_definitions(
        self,
        compound: Scope,
        from_stmt: Node | None = None,
        to_stmt: Node | None = None,
    ) -> list[Identifier]:
        """Gets all identifier definitions of statements within an entire scope
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

    def get_nested_scope_usage(
        self,
        compound: Scope,
        from_stmt: Node | None = None,
        to_stmt: Node | None = None,
    ) -> list[Identifier]:
        """Gets all identifier usages of statements within an entire scope
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
        """Given a scope, this function finds and returns the path through the
        program's scope tree from the program (translation unit) root up to that point.

        Args:
            compound (Scope): The scope to find a path to - either a Compound or "None"
            (to indicate the file itself).

        Returns:
            list[Scope]: The in-order sequence of scopes from the program root to the
            given scope."""
        scope_path = [compound]
        while compound is not None:
            compound = self.compound_parent[compound]
            scope_path.append(compound)
        scope_path = scope_path[:-1]
        return scope_path

    def get_definitions_at_stmt(
        self, stmt: Node, compound: Scope | None = None
    ) -> list[Identifier]:
        """Given a statement, this will find all the identifiers that
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
            compound_stmt = [
                c[1] for c in self.compound_children[scope] if c[0] == child
            ]
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

    def get_last_ident_definition(
        self, ast_node: Node, ident: Identifier
    ) -> Node | None:
        """Given an AST node corresponding to some part of the abstract
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
        if isinstance(ast_node, Compound):
            stmt = None
            compound = ast_node
        else:
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
            parent = scope_path[i + 1]
            to_stmt = [c[1] for c in self.compound_children[parent] if c[0] == scope]
            if len(to_stmt) == 0:
                to_stmt = None
            else:
                to_stmt = to_stmt[0]
        return None

    def get_usage_from_stmt(
        self, stmt: Node, compound: Scope | None = None
    ) -> list[Identifier]:
        """Given a statement, this will find all the identifiers that
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

    def get_required_identifiers(
        self,
        node: Node,
        namespace: NameSpace,
        compound: Scope | None = None,
        function: FuncDef | None = None,
        include_after: bool = False,
    ) -> set[Identifier]:
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
        if compound is None:
            compound = self.get_stmt_compound(stmt)
        if include_after:
            scope_definitions = self.get_scope_definitions(compound)
        else:
            scope_definitions = self.get_scope_definitions(compound, None, stmt)
        defined = defined.union(scope_definitions)
        if function is None:
            function = self.get_stmt_func(stmt)
        if function is not None:
            defined = defined.union(
                set((n.name, NameSpace.LABEL) for n in self.funclabels[function])
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

    def get_new_identifier(
        self,
        node: Node,
        namespace: NameSpace,
        compound: Scope | None = None,
        function: FuncDef | None = None,
        exclude: Iterable[str] | None = None,
    ) -> str:
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
        """Generates an entirely new unique identifier that is not used anywhere
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

    def change_ident(
        self, node: Node, name: str, namespace: NameSpace, new_name: str
    ) -> None:
        """Changes a specific instance (definition) of an identifier to use
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
        """Performs a backfill of function specifications, updating any incomplete
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
                typedecl = self.get_typedecl(funcspec.type.type)
                if typedecl is not None:
                    typedecl.declname = func_name

    def _record_stmt(self, stmt_node: Node) -> None:
        """Records a node as a statement, updating analysis tracking
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

    def _get_last_definition(self, name: str, namespace: NameSpace) -> Node | None:
        """Given an identifier (name and namespace), this function iterates
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
            labels = self.funclabels[self._current_function]
            for label in labels:
                if label.name == name:
                    return self.get_stmt_from_node(label)
            return None
        for scope in self._current_definitions[::-1]:
            if (name, namespace) in scope:
                return scope[(name, namespace)]
        return None

    def get_typedecl(self, node: Node) -> TypeDecl | None:
        """Recursively iterates through the type attributes of AST nodes in
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
            return self.get_typedecl(node.type)
        elif isinstance(node, TypeDecl):
            return node
        return None

    def _record_definition(
        self,
        node: Node,
        name: str,
        locations: list[Location],
        namespace: NameSpace,
        alt_scope: Scope | None = None,
    ) -> None:
        """Records an instance of an identifier definition at a given AST
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

    def _record_usage(
        self, node: Node, name: str, locations: list[Location], namespace: NameSpace
    ) -> None:
        """Records an instance of an identifier's usage at a given
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
        """Visits a FileAST node, recording it as a scope."""
        # Record the scope information
        self._current_definitions.append({})
        self.compound_children[node] = []
        self.compound_parent[node] = None  # The FileAST has no parent
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
        """Visits a Compound node, recording it as both a statement in its
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
        self.compound_children[node] = []
        self.compound_children[self._current_compound].append(
            (node, self._current_stmt)
        )
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
        """Visits a FuncDecl node, recording the declared function. Avoids
        traversing the parameter list, so that it is traversed in the function
        body where one exists. If one doesn't exist (a signature), this can
        be backfilled."""
        # Visit all children as normal except the parameter list,
        # as that gets walked by the compound body instead.
        for child in node.children():
            if child[0] != "args" or self._current_function is None:
                self.visit(child[1])
        if node.type is not None:
            typedecl = self.get_typedecl(node.type)
            if typedecl is not None and typedecl.declname is not None:
                self.functions.add(typedecl.declname)
                locs = [(typedecl, "declname")]
                self._record_usage(
                    typedecl, typedecl.declname, locs, NameSpace.ORDINARY
                )

    @_stmt_wrapper
    def visit_FuncDef(self, node: FuncDef) -> None:
        """Visits a FuncDef node, recording the function signature,
        and passing parameters to be parsed by the function body
        where possible."""
        # Log information for the function and its block
        prev_function = self._current_function
        if node.body is not None:
            self._current_function = node
            self.funclabels[node] = set()
            self.funcgotos[node] = set()
        # Augment the following compound with parameter definitions
        for child in node.children():
            if child[0] != "body":
                self.visit(child[1])
        self.visit_Compound(node.body, params=node.decl.type.args)
        # Track goto usage of labels (as these are an out-of-order
        # intra-function reference)
        for goto in self.funcgotos[node]:
            locs = [(goto, "name")]
            self._record_usage(goto, goto.name, locs, NameSpace.LABEL)
        self._current_function = prev_function

    @_stmt_wrapper
    def visit_Typedef(self, node: Typedef) -> None:
        """Visits a Typedef node, recording the typedef as well as any
        relevant identifier definitions/usages."""
        if node.name is None or node.type is None:
            return NodeVisitor.generic_visit(self, node)
        # Add the name identifier definition
        self.typedefs.add(node.name)
        locations = [(node, "name")]
        typedecl = self.get_typedecl(node.type)
        has_declname = typedecl is not None and typedecl.declname is not None
        if has_declname:
            locations.append((typedecl, "declname"))
        self._record_definition(node, node.name, locations, NameSpace.ORDINARY)
        # Add the type identifier usage, if one exists
        if not has_declname:
            return NodeVisitor.generic_visit(self, node)
        locations = [(node, "name"), (typedecl, "declname")]
        type_ = typedecl.type
        if isinstance(type_, (Struct, Union, Enum)) and type_.name is not None:
            type_locs = [(type_, "name")]
            if not isinstance(type_, Enum) and type_.decls is not None:
                self._record_definition(node, type_.name, type_locs, NameSpace.TAG)
        else:
            self._record_usage(node, typedecl.declname, locations, NameSpace.ORDINARY)
        NodeVisitor.generic_visit(self, node)

    def _record_var_func_decl(self, node: Decl) -> None:
        """Records a regular function/variable/parameter declaration definition."""
        locations = [(node, "name")]
        typedecl = self.get_typedecl(node.type)
        if typedecl is not None and typedecl.declname is not None:
            locations.append((typedecl, "declname"))
        if self._current_struct is None:
            self._record_definition(node, node.name, locations, NameSpace.ORDINARY)
        else:
            self._record_definition(
                node, node.name, locations, (NameSpace.MEMBER, self._current_struct)
            )

    def _record_tag_decl(self, node: Decl) -> None:
        """Records definitions of enums/structs/unions (tag namespace) idents
        in Decl AST nodes."""
        # Parse type declaration for structs/unions/enums, account for pointers etc.
        types = []
        cur_node = node
        while cur_node.type is not None and isinstance(
            cur_node.type, (PtrDecl, ArrayDecl)
        ):
            types.append(cur_node.type)
            cur_node = cur_node.type
        if isinstance(cur_node.type, (Enum, Struct, Union)):
            types.append(cur_node.type)
        for i, type_ in enumerate(types):
            if (isinstance(type_, Enum) and type_.values is not None) or (
                isinstance(type_, (Struct, Union))
                and type_.decls is not None
                and type_.name is not None
            ):
                locs = [(type_, "name")]
                self._record_definition(node, type_.name, locs, NameSpace.TAG)
                if i == 1:  # Edge case where declaring & using at the same time
                    self._record_usage(node, type_.name, locs, NameSpace.TAG)
            elif isinstance(type_, (Enum, Struct, Union)) and type_.name is not None:
                locs = [(type_, "name")]
                self._record_definition(node, type_.name, locs, NameSpace.TAG)

    def _record_funcspec_decl(self, node: Decl) -> None:
        """Records definitions of function specifications, including
        within function bodies."""
        if node.type is None or node.name is None:
            return
        if isinstance(node.type, FuncDecl) and (
            self._current_function is None
            or node.name != self._current_function.decl.name
        ):
            # A function specification has been found
            if node.name in self.funcspecs:
                self.funcspecs[node.name].add(node)
            else:
                self.funcspecs[node.name] = set([node])

    def _record_initializer_decl(self, node: Decl) -> None:
        """Records definitions of elements in Initializer Lists
        and Named Initializers / Designated Initializers."""
        decl_type = self.expression_analyzer.get_type(node)
        if (
            not isinstance(decl_type, (Struct, Union))
            or not isinstance(node.init, InitList)
            or node.init.exprs is None
        ):
            return NodeVisitor.generic_visit(self, node)
        self.visit(node.type)
        for expr in node.init.exprs:
            if not isinstance(expr, NamedInitializer) or len(expr.name) == 0:
                self.visit(expr)
                continue
            name = expr.name[-1].name
            locs = [(expr.name[-1], "name")]
            self._record_usage(node, name, locs, (NameSpace.MEMBER, decl_type))
            self.visit_ID(expr.name[-1], record=False)
            self.visit(expr.expr)

    @_stmt_wrapper
    def visit_Decl(self, node: Decl) -> None:
        """Visits a Decl node, recording any identifier definitions or usages
        that have occurred within the declaration."""
        if node.name is not None and self._current_function != "IGNORE":
            self._record_var_func_decl(node)
        self._record_tag_decl(node)
        self._record_funcspec_decl(node)
        if node.name is None or node.type is None or node.init is None:
            return NodeVisitor.generic_visit(self, node)
        self._record_initializer_decl(node)

    @_stmt_wrapper
    def visit_CompoundLiteral(self, node: CompoundLiteral) -> None:
        """Visits a CompoundLiteral node, specifically to detect and
        record compound literals storing named initializers as definition
        usages of the corresponding name in the "MEMBER" name space.
        Otherwise normally visits the node, traversing it."""
        type_ = self.expression_analyzer.get_type(node)
        if (
            not isinstance(type_, (Struct, Union))
            or not isinstance(node.init, InitList)
            or node.init.exprs is None
        ):
            return NodeVisitor.generic_visit(self, node)
        self.visit(node.type)
        for expr in node.init.exprs:
            if not isinstance(expr, NamedInitializer) or len(expr.name) == 0:
                self.visit(expr)
                continue
            name = expr.name[-1].name
            locs = [(expr.name[-1], "name")]
            self._record_usage(node, name, locs, (NameSpace.MEMBER, type_))
            self.visit_ID(expr.name[-1], record=False)
            self.visit(expr.expr)

    @_stmt_wrapper
    def visit_ParamList(self, node: ParamList) -> None:
        """Visits a ParamList node, setting a relevant flag to ignore parsing
        for certain types of identifier usages whilst within the parameter
        list (so as to ensure that parameters are defined within the compound
        scope)."""
        if self._current_function is None:
            prev_function = self._current_function
            self._current_function = "IGNORE"
            self.generic_visit(node)
            self._current_function = prev_function
        else:
            self.generic_visit(node)

    @_stmt_wrapper
    def visit_Enumerator(self, node: Enumerator) -> None:
        """Visits an Enumerator node, recording the identifier definition."""
        if node.name is not None:
            locs = [(node, "name")]
            self._record_definition(node, node.name, locs, NameSpace.ORDINARY)
        self.generic_visit(node)

    def _wrap_struct_definitions(self, struct: Struct | Union) -> None:
        """Wraps any definitions inside a struct/union by annotating
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
        """Visits a Union node, recording the union tag occurence so long
        as an appropriate union name is provided."""
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
        """Visits a Struct node, recording the structure occurrence."""
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
        """Visits an Enum node, recording the structure occurrence."""
        if node.name is not None:
            locs = [(node, "name")]
            self._record_usage(node, node.name, locs, NameSpace.TAG)
        NodeVisitor.generic_visit(self, node)

    @_stmt_wrapper
    def visit_Label(self, node: Label) -> None:
        """Visits a Label node, recording the label occurence and the
        corresponding identifier definition."""
        if node.stmt is not None:
            self._record_stmt(node.stmt)
        if node.name is not None:
            locs = [(node, "name")]
            self._record_definition(
                node,
                node.name,
                locs,
                NameSpace.LABEL,
                alt_scope=self._current_definitions[1],
            )
            self.funclabels[self._current_function].add(node)
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
        """Visits an IdentifierType node, recording the identifier usage
        if the name is a typedef."""
        if node.names is None or len(node.names) == 0:
            return NodeVisitor.generic_visit(self, node)
        name = node.names[-1]
        if name in self.typedefs:
            locs = [(node, ("names", -1))]
            self._record_usage(node, name, locs, NameSpace.ORDINARY)
        NodeVisitor.generic_visit(self, node)

    @_stmt_wrapper
    def visit_StructRef(self, node: StructRef) -> None:
        """Visits a StructRef node, recording the structure information
        so that its identifiers can be parsed correctly."""
        # Fetch the corresponding member definition from the tag that matches
        # the expression's type
        if (
            node.name is not None
            and node.field is not None
            and node.field.name is not None
        ):
            struct_type = self.expression_analyzer.get_type(node.name)
            if (
                struct_type is not None
                and node.type == "->"
                and isinstance(struct_type, ExpressionAnalyzer.Ptr)
                and isinstance(struct_type.val, (Struct, Union))
            ):
                struct_type = struct_type.val
            if struct_type is not None and isinstance(struct_type, (Struct, Union)):
                members = self.struct_members[struct_type]
                if node.field.name in members:
                    locs = [(node.field, "name")]
                    self._record_usage(
                        node, node.field.name, locs, (NameSpace.MEMBER, struct_type)
                    )
        self.visit(node.name)
        self.visit_ID(node.field, record=False)

    @_stmt_wrapper
    def visit_Goto(self, node: Goto) -> None:
        """Visits a Goto node, recording the label identifier usage."""
        if node.name is not None:
            self.funcgotos[self._current_function].add(node)
        NodeVisitor.generic_visit(self, node)

    @_stmt_wrapper
    def generic_visit(self, node: Node) -> None:
        """Visits any generic node in the AST, recording the current
        statement for each AST node."""
        self.node_stmt_map[node] = self._current_stmt
        NodeVisitor.generic_visit(self, node)
