""" File: complexity.py
Implements classes and functions for calculating quantitative and qualitative 
obfuscation metrics, by calculating code complexity metrics for both the 
original source program and obfuscated program and providing this information. 
Implemented metrics include aggregates (counts), McCabe's Cyclomatic Complexity
index, Halstead's Measures, Sonar's Cognitive Complexity, and the 
Maintainability Index. 
"""
from .interaction import CSource, PatchedGenerator
from abc import ABC, abstractmethod
from typing import Iterable, Optional, Tuple, TypeAlias, Any
from pycparser.c_ast import *
from pycparser import c_lexer
import statistics
import networkx
import math


Metric: TypeAlias = Tuple[str, Tuple[str, str] | str]
Metrics: TypeAlias = dict[str, Tuple[str, str] | str]


class CodeMetricUnit(ABC):
    """An abstract base class representing some code complexity metric unit, such that
    any implemented code metrics will be subclasses of this class. Implements methods
    for calculating and formatting these complexity metrics given some code."""

    name = "CodeMetricUnit"
    positions = {}
    name_tooltip = "An Abstract Base Class for implementing code metric units."
    tooltips = {}
    predecessors = []

    def __init__(self):
        """The constructor for the CodeMetricUnit base class, which defines a list of metrics"""
        self.metrics = {}

    def add_metric(self, name: str, new: str, delta: Optional[str] = None) -> None:
        """Adds a given metric to the list of metrics stored by the CodeMetricUnit,
        either directly storing the value or storing a tuple if an optional delta value
        us provided.

        Args:
            name (str): The name of the metric (that will be displayed to users)
            new (str): The value of the metric for the obfuscated program
            delta (Optional[str], optional): The change in value of the metric,
            from original source program to obfuscated program, where one exists.
            Defaults to None, representing no delta.
        """
        if delta is None:
            self.metrics[name] = new
        else:
            self.metrics[name] = (new, delta)

    @abstractmethod
    def calculate_metrics(self, old_source: CSource, new_source: CSource) -> None:
        """Calculates a set of metrics given the original source C program and the
        final obfuscated source C program, adding them to the list of stored metrics.

        Args:
            old_source (CSource): The original unobfuscated C source program
            new_source (CSource): The final obfuscated C source program
        """
        return NotImplemented

    def get_metrics(self) -> list[Metric]:
        """Retrieves the list of metrics stored by the CodeMetricUnit, sorting them
        according to the ordering defined in by the class' positions dictionary,
        and

        Returns:
            list[Metric]: The list of previously calculated metrics, in sorted order,
            where each metric is a tuple (name, value) where value is either the string
            value of that metric for the obfuscated program, or some tuple (new value, delta).
        """
        if len(self.metrics) == 0:
            return [(x, "N/A") for x in self.positions]
        return sorted(
            list(self.metrics.items()),
            key=lambda x: self.positions[x[0]]
            if x[0] in self.positions
            else len(self.positions),
        )


def int_delta(new: int | str, prev: int | str) -> str:
    """Given two integers metric values, this function calculates the delta
    (change) between the two values. If either value is the special "N/A" string
    then the delta is likewise defined to be "N/A". Also, an unary "+" is prepended
    to all positive numbers to make it clear that the value is a positive delta.

    Args:
        new (int | str): The metric value for the obfuscated program
        prev (int | str): The metric value for the original program

    Returns:
        str: The string delta (change) from the original to the obfuscated metric.
    """
    if new == "N/A" or prev == "N/A":
        return "N/A"
    delta = int(new - prev)
    return ("+" + str(delta)) if delta >= 0 else str(delta)


def float_delta(new: float | str, prev: float | str) -> str:
    """Given two float metric values, this function calculates the delta (change)
    between the two values. If either value is the special "N/A" string then the
    delta is likewise defined to be "N/A". Also, an unary "+" is prepended to all
    positive numbers to make it clear that the value is a positive delta. All decimals
    are formatted to one decimal place for display purposes.

    Args:
        new (float | str): The metric value for the obfuscated program
        prev (float | str): The metric value for the original program

    Returns:
        str: The string delta (change) from the original to the obfuscated metric.
    """
    if new == "N/A" or prev == "N/A":
        return "N/A"
    delta = new - prev
    f_str = "{:.1f}".format(delta)
    return ("+" + f_str) if delta >= 0.0 else f_str


def format_time(time: int | str) -> str:
    """Given some duration of time in unit seconds, this function formats the time
    into a more human readable format by converting it to a form %d %h %m %s
    showing the different units of time. Only the largest scale unit needed to
    represent the duration is shown to improve readability.

    Args:
        time (int | str): The duration of time in unit seconds

    Returns:
        str: A human readable time duration string like "%d %h %m %s"
    """
    if isinstance(time, str):
        return time
    fstring = "{}s".format(time % 60)
    time = time // 60
    if time == 0:
        return fstring
    fstring = "{}m ".format(time % 60) + fstring
    time = time // 60
    if time == 0:
        return fstring
    fstring = "{}h ".format(time % 24) + fstring
    time = time // 24
    if time == 0:
        return fstring
    return "{}d ".format(time) + fstring


def file_size(byte_size: int, binary_suffix: bool = False, signed: bool = True) -> str:
    """This function calculates the file size of a given file in a format with
    readable scaled units, given the size in bytes of the file, e.g. 4.5KB. All
    values are given to one decimal place in terms of accuracy.

    Args:
        byte_size (int): The number of bytes (8 bits) in the file.
        binary_suffix (bool, optional): Whether to use binary suffixes e.g.
        KiB, MiB, GiB, ... which increase by a factor of 2^10 = 1024, or not, instead
        using decimal KB, MB, GB, ... formats which increase by a factor of
        10^3 = 1000. Defaults to False, i.e. decimal suffixes.
        signed (bool, optional): Whether to calculate the absolute file size, or to
        include the plus or minus sign. Defaults to True, indicating to include the sign.
        This is to cover the case of changes in file size (deltas).

    Returns:
        str: A string representing the file size with more comprehensible units.
    """
    is_positive = byte_size >= 0
    byte_size = abs(byte_size)
    if binary_suffix:
        suffixes = ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi", "Yi"]
    else:
        suffixes = ["", "K", "M", "G", "T", "P", "E", "Z", "Y"]
    inc_size = 1024.0 if binary_suffix else 1000.0
    for suffix in suffixes[:-1]:
        if byte_size < inc_size:
            break
        byte_size = byte_size / inc_size
    if byte_size >= inc_size:
        suffix = suffixes[-1]
    f_str = "{:.1f}{}B".format(byte_size, suffix)
    if signed:
        return ("+" + f_str) if is_positive else ("-" + f_str)
    return f_str if is_positive else ("-" + f_str)


class AggregateVisitor(NodeVisitor):
    """A class that traverses an Abstract Syntax Tree (AST) to count a variety
    of occurrences of program constructs in the AST such that aggregate metrics
    can be computed."""

    __ident_attrs = (
        "name",
        "declname",
        "field",
    )

    def __init__(self):
        """The constructor for the AggregateVisitor object, initialising its state."""
        self.__reset()

    def __reset(self) -> None:
        """Resets the state of the AggregateVisitor, replcing existing counts
        and contextual parsing information to their default initial state.
        """
        self.constants = 0
        self.ast_nodes = 0
        self.functions = 0
        self.stmts = 0
        self.stmts_in_functions = 0
        self.__in_function = False
        self.ident_set = set()

    def record_stmt(self) -> None:
        """Records an occurrence of a given statement, incrementing both the
        global statement counter, and the local function statement counter (so
        long as the AST is currently traversing a function).
        """
        self.stmts += 1
        if self.__in_function:
            self.stmts_in_functions += 1

    def visit_FileAST(self, node: FileAST) -> None:
        """Traverses a FileAST root node in the AST, resetting the state of
        the AggregateVisitor before traversing the AST as normal so that
        it can be reused. It also counts all non-compound children of the
        AST as individual statements

        Args:
            node (FileAST): The FileAST root node of the AST to traverse.
        """
        self.__reset()
        if node.ext is not None:
            for child in node.ext:
                if not isinstance(child, Compound):
                    self.record_stmt()
        self.generic_visit(node)

    def visit_Constant(self, node: Constant) -> None:
        """Traverses a Constant node in the AST, recording its occurrence.

        Args:
            node (Constant): The Constant node to traverse.
        """
        self.constants += 1
        self.generic_visit(node)

    def visit_FuncDef(self, node: FuncDef) -> None:
        """Traverses a FuncDef node in the AST, recording its ocurrence and noting
        that a function is being traversed.

        Args:
            node (FuncDef): The FuncDef function definition node to traverse.
        """
        self.__in_function = True
        self.functions += 1
        self.generic_visit(node)
        self.__in_function = False

    def visit_Compound(self, node: Compound) -> None:
        """Traverses a Compound node in the AST, individually recording each
        non-compound child node to be a statement.

        Args:
            node (Compound): The Compound AST node to traverse.
        """
        if node.block_items is not None:
            for child in node.block_items:
                if not isinstance(child, Compound):
                    self.record_stmt()
        self.generic_visit(node)

    def visit_If(self, node: If) -> None:
        """Traverses an If statement in the AST, individually recording each
        branch of the if-statement to be its own individual statement (where
        such branches exist).

        Args:
            node (If): The If statement AST node to record and traverse."""
        if node.iftrue is not None and not isinstance(node.iftrue, Compound):
            self.record_stmt()
        if node.iffalse is not None and not isinstance(node.iffalse, Compound):
            self.record_stmt()
        self.generic_visit(node)

    def visit_Case(self, node: Case) -> None:
        """Traverses a Case statement node in the AST, individually recording
        each labelled statement of the case to be its own individual statement.

        Args:
            node (Case): The Case statement AST node to record and traverse.
        """
        if node.stmts is not None and not isinstance(node.stmts, Compound):
            for child in node.stmts:
                if not isinstance(child, Compound):
                    self.record_stmt()
        self.generic_visit(node)

    def visit_Default(self, node: Default) -> None:
        """Traverses a Default statement node in the AST, individually recording
        each labelled statement of the default case to be its own individual statement.

        Args:
            node (Default): The Default statement AST node to record and traverse.
        """
        if node.stmts is not None and not isinstance(node.stmts, Compound):
            for child in node.stmts:
                if not isinstance(child, Compound):
                    self.record_stmt()
        self.generic_visit(node)

    def generic_visit(self, node: Node) -> None:
        """Traverses any generic AST node, recording any statement occurrences where
        some program construct has a singular child instance (e.g. loops, switch, label).
        Also records unique string children of any nodes as identifiers.

        Args:
            node (Node): The AST node to record and traverse.
        """
        self.ast_nodes += 1
        if isinstance(node, (While, DoWhile, For, Switch, Label)):
            if node.stmt is not None and not isinstance(node.stmt, Compound):
                self.record_stmt()
        for attr in self.__ident_attrs:
            if not hasattr(node, attr):
                continue
            attr_val = getattr(node, attr)
            if attr_val is None or not isinstance(attr_val, str):
                continue
            self.ident_set.add(attr_val)
        return super(AggregateVisitor, self).generic_visit(node)


class AggregateUnit(CodeMetricUnit):
    """A class for calculating aggregate/count metrics of varying types, implementing
    methods for calculating and formatting these complexity metrics given some code.
    These metrics measure varied program units and provide aggregate cost/size information
    at different granularities."""

    name = "Aggregates"
    positions = dict(
        [
            (x, i)
            for (i, x) in enumerate(
                [
                    "File Size",
                    "Lines",
                    "Tokens",
                    "Characters",
                    "Functions",
                    "Statements",
                    "Stmts/Function",
                    "AST Nodes",
                    "Constants",
                    "Identifiers",
                    "New Identifiers",
                ]
            )
        ]
    )
    name_tooltip = (
        "A variety of simple counting/averaging metrics that represent the\n"
        "size, density and diversity of the obfuscated program.\n"
        "\nThis metric primarily helps to measure obfuscation costs and potency (complexity)."
    )
    tooltips = {
        "File Size": "The estimated file size of the program from its contents, given that text is\n"
        "saved using an extended-ASCII encoding and no header information is included.",
        "Lines": "The number of lines in the obfuscated program.\n"
        "Counted by '\\n' character occurences.",
        "Tokens": "The number of tokens/lexemes in the program generated by pycparser.\n"
        "These are contiguous sequences of characters corresponding to program constructs.",
        "Characters": "The number of raw characters in the program, including special\n"
        "characters as single character instances e.g. '\\n'.",
        "Functions": "The number of functions in the program body - only counting defined\n"
        "functions, and not just signatures. Inclues main().",
        "Statements": "The number of statements in the program, including both local and global\n"
        "declarations but not including preprocessor directives, function definitions\n"
        "or compound statements as their own statements.",
        "Stmts/Function": "The average number of statements per function definition in the program.\n"
        "This metric only counts statements within functions so as to not let global\n"
        "statements influence this average.",
        "AST Nodes": "The number of nodes in the Abstract Syntax Tree (AST) generated by pycparser\n"
        "for the program, where each node corresponds to an application of a grammar rule.",
        "Constants": "The number of constant values in the program, including constant integers/floats,\n"
        "constant strings/chars, and any other such constants.",
        "Identifiers": "The number of unique identifiers in the program, not accounting for name-reuse.\n"
        "E.g. so, if the variable 'a' is used in two separate functions, it is only counted\n"
        "once. This is essentially a measure of symbolic identifier diversity for the program.",
        "New Identifiers": "The number of new unique identifiers introduced during obfuscation - that is,\n"
        "the number of identifiers in the obfuscated result that were not in the original.",
    }
    predecessors = []
    cached = {}

    def __cache_metrics(self, metrics: Metrics) -> None:
        """Caches the provided set of metrics within the class' cache, such that
        any future metric group that wishes to use aggregate metrics in their
        calculations can access these cached values without recomputing them.

        Args:
            metrics (Metrics): The dictionary of metrics to cache.
        """
        AggregateUnit.cached = dict(x for x in AggregateUnit.cached.items())
        for k, v in metrics.items():
            AggregateUnit.cached[k] = v

    def add_AST_metrics(self, old_source: CSource, new_source: CSource) -> None:
        """Computes and formats a subset of aggregate metrics related to aggregates
        over the Abstract Syntax Tree (AST), including the: Constants, AST nodes,
        Functions, Identifiers, New Identifiers, Statements, and Statements/Function.

        Args:
            old_source (CSource): The original C source file before obfuscation.
            new_source (CSource): The final obfuscated C source file.
        """
        # Visit the counters to compute aggregates
        old_counter = AggregateVisitor()
        old_counter.visit(old_source.t_unit)
        new_counter = AggregateVisitor()
        new_counter.visit(new_source.t_unit)

        # Retrieve and format Constants, AST Nodes, and Functions, caching functions.
        new_c, old_c = new_counter.constants, old_counter.constants
        self.add_metric("Constants", str(new_c), int_delta(new_c, old_c))
        new_n, old_n = new_counter.ast_nodes, old_counter.ast_nodes
        self.add_metric("AST Nodes", str(new_n), int_delta(new_n, old_n))
        new_f, old_f = new_counter.functions, old_counter.functions
        self.add_metric("Functions", str(new_f), int_delta(new_f, old_f))
        self.__cache_metrics({"Functions": (new_f, old_f)})

        # Comptue metrics related to the number of identifiers and new identifiers
        new_id, old_id = new_counter.ident_set, old_counter.ident_set
        num_new_id, num_old_id = len(new_id), len(old_id)
        self.add_metric(
            "Identifiers", str(num_new_id), int_delta(num_new_id, num_old_id)
        )
        self.add_metric("New Identifiers", str(len(new_id.difference(old_id))))
        new_stmts, old_stmts = new_counter.stmts, old_counter.stmts

        # Comptue aggreagtes for the number of statements, and statements per function
        self.add_metric("Statements", str(new_stmts), int_delta(new_stmts, old_stmts))
        if new_counter.functions != 0:
            new_spf = new_counter.stmts_in_functions / new_counter.functions
            new_spf_str = "{:.2f}".format(new_spf)
        else:
            new_spf = "N/A"
            new_spf_str = "N/A"
        if old_counter.functions != 0:
            old_spf = old_counter.stmts_in_functions / old_counter.functions
        else:
            old_spf = "N/A"
        self.add_metric("Stmts/Function", new_spf_str, float_delta(new_spf, old_spf))

    def preprocess_contents(self, source: CSource) -> str:
        """Given a CSource object, preprocess its contents by generating its C source
        code using a patched generator.

        Args:
            source (CSource): The CSource source program to preprocess.

        Returns:
            str: The preprocessed contents of the CSource.
        """
        generator = PatchedGenerator()
        contents = generator.visit(source.t_unit)
        return contents

    def get_token_count(self, lexer: c_lexer.CLexer, contents: str) -> int:
        """Retrieves a count of the nubmer of tokens within a given program
        being parsed by a lexer.

        Args:
            lexer (c_lexer.CLexer): The C program lexer to be used.
            contents (str): The contents of the C source program to lex.

        Returns:
            int: The number of tokens within the given file contents.
        """
        lexer.input(contents)
        token = lexer.token()
        token_count = 0
        while token is not None:
            token_count += 1
            token = lexer.token()
        return token_count

    def add_lexer_metrics(self, old_source: CSource, new_source: CSource) -> None:
        """Computes and formats a subset of aggregate metrics related to lexical
        information, including the number of lines, tokens, characters and file
        size. These are not computed using any AST representation.

        Args:
            old_source (CSource): The original C source file before obfuscation.
            new_source (CSource): The final obfuscated C source file.
        """
        # Initialise and run lexer
        lexer = c_lexer.CLexer(
            lambda: None, lambda: None, lambda: None, lambda tok: None
        )
        lexer.build()

        # Get line counts
        old_contents = old_source.contents
        new_contents = new_source.contents
        old_lines, new_lines = old_contents.count("\n"), new_contents.count("\n")
        self.add_metric("Lines", str(new_lines), int_delta(new_lines, old_lines))
        self.__cache_metrics({"Lines": (new_lines, old_lines)})

        # Preprocess contents and lex to get token counts
        old_contents = self.preprocess_contents(old_source)
        new_contents = self.preprocess_contents(new_source)
        old_toks = self.get_token_count(lexer, old_contents)
        new_toks = self.get_token_count(lexer, new_contents)
        self.add_metric("Tokens", str(new_toks), int_delta(new_toks, old_toks))

        # Also consider simple character counts and file size metrics.
        old_chars, new_chars = len(old_contents), len(new_contents)
        self.add_metric("Characters", str(new_chars), int_delta(new_chars, old_chars))
        BYTES_PER_CHAR = 1
        old_size = BYTES_PER_CHAR * len(old_contents.encode("unicode_escape"))
        new_size = BYTES_PER_CHAR * len(new_contents.encode("unicode_escape"))
        self.add_metric(
            "File Size",
            file_size(new_size, signed=False),
            file_size(new_size - old_size),
        )

    def calculate_metrics(self, old_source: CSource, new_source: CSource) -> None:
        """Computes and formats the set of aggregate metrics for the given programs,
        by respectively computing metrics using the AST and lexical information.

        Args:
            old_source (CSource): The original C source file before obfuscation.
            new_source (CSource): The final obfuscated C source file.
        """
        self.add_AST_metrics(old_source, new_source)
        self.add_lexer_metrics(old_source, new_source)


class CFGGenerator(NodeVisitor):
    """This class traverses and AST to compute a directed graph representation of
    the source-level control flow graph for (each function in) the program, such
    that metrics can be computed from he CFG. This also records additional information
    about the number of compound logical statements in expressions for calculation
    of Myers' Interval."""

    def __init__(self):
        """The constructor for the CFGGenerator, resetting its state."""
        super(CFGGenerator, self).__init__()
        self.__reset()

    def __reset(self) -> None:
        """Resets the state of the CFGGenerator to use default initialised values, such
        that it can be re-used beteen different metric computations. This invovles
        resetting the valeu fo count and tracking variables, and clearing data structures
        used during traversal and to store the CFG.
        """
        # Reset tracking variables
        self.in_function = False
        self.in_cond = False
        self.functions = 0
        self.node_number = 0
        self.decisions = 0
        self.myers = 0
        self.levels = 0
        # Reset traversal strutures
        self.label_blocks = dict()
        self.gotos = dict()
        self.breaks = []
        self.continues = []
        self.escaped = []
        self.entry_stack = []
        self.exit_stack = []
        # Reset data structures storing computed CFG / decisions / Myers' Interval info
        self.cfgraph = dict()
        self.graphs = dict()
        self.func_decisions = dict()
        self.func_myers = dict()

    def __add_node(self, node: int) -> None:
        """Adds a node (represented by some unique integer) to the control flow graph (CFG).
        Creates a corresponding set in the adjacency list representation.

        Args:
            node (int): The nubmer of the node to add.
        """
        self.cfgraph[node] = set()

    def __add_edge(self, from_node: int, to_node: int) -> None:
        """Adds an edge (between two nodes represented by unique integers) to the control
        flow graph (CFG), by addnig it to the relevant node's adjacency list.

        Args:
            from_node (int): The node the directed edge is exiting from.
            to_node (int): The node the direct edge is entering towards.
        """
        self.cfgraph[from_node].add(to_node)

    def __new_node(self) -> int:
        """Create a new graph node by generating a unique integer label for that node, and
        adding it to the current CFG representation.

        Returns:
            int: The number of the newly generated node.
        """
        new_node = self.node_number
        self.__add_node(new_node)
        self.node_number += 1
        return new_node

    def __set_entry_exit(self, entry: int, exit: int) -> None:
        """Sets the entry and exit CFG node at the current level of program traversal,
        pushing them to the top of the relevant entry and exit node stacks.

        Args:
            entry (int): The node at which control flow should begin.
            exit (int): The node at which control flow should end (transition to when done).
        """
        self.entry_stack.append(entry)
        self.exit_stack.append(exit)

    def __pop_entry_exit(self) -> None:
        """Removes the top values from the entry and exit stacks, such that when traversal
        of some program construct is complete, information about its control flow can be removed.
        """
        self.entry_stack = self.entry_stack[:-1]
        self.exit_stack = self.exit_stack[:-1]

    def __get_entry_exit(self) -> Tuple[int, int]:
        """Retrieves the current entry and exit nodes from the top of the relevant stacks,
        determining where the current construct should begin and exit in control flow.

        Returns:
            Tuple[int,int]: The tuple (entry node, exit node).
        """
        return (self.entry_stack[-1], self.exit_stack[-1])

    def __modify_entry_exit(self, entry: int, exit: int) -> None:
        """Modifies the values of the current entry and exit nodes at the top of the
        relevant stacks, which is used to handle labels (branching targets) disrupting
        conventional control flow in structured code.

        Args:
            entry (int): The new entry node of the current control flow.
            exit (int): The new exit node of the current control flow.
        """
        self.entry_stack[-1] = entry
        self.exit_stack[-1] = exit

    def __visit(
        self,
        node: Node,
        entry: int,
        exit: int,
        modify: bool = False,
        escape_link: bool = True,
    ) -> None:
        """Visits a node in the AST wih a specific entry and exit control flow node in the CFG.
        This function handles the appropriate state representation of entry and exit nodes on the
        stack, and creates corresponding edges between end blocks and exit blocks so long as
        some control flow statement (break; continue), return statement or GOTO statement has not
        disrupted regualr control flow. Such exceptions are handled on a case by case basis.

        Args:
            node (Node): The AST node to visit.
            entry (int): The entry node of control flow for that AST node.
            exit (int): The exit node of control flow for that AST node.
            modify (bool, optional): Whether to modify the top of the existing entry/exit node
            stack or to add a new scope. Should generally only be true when handling control
            flow for labels (branch targets). Defaults to False.
            escape_link (bool, optional): Whether to escape the creation of a link between
            the final control flow blocks for the AST node and the exit node. Should generally
            only be used when handling branches (e.g. GOTO, return). Defaults to True.
        """
        if modify:
            # Modify the top of the entry/exit stack, visit the node, and then create new
            # entry and exit nodes.
            self.__modify_entry_exit(entry, exit)
            if isinstance(node, list):
                for item in node:
                    self.visit(item)
            else:
                self.visit(node)
            new_entry, new_exit = self.__get_entry_exit()
        else:
            # Create new values on the top of the existing entry and exit stack, visit the
            # node, record escaped edge transitions if necessary, and finally pop the newly
            # created values from the relevant stacks.
            self.escaped.append(False)
            self.__set_entry_exit(entry, exit)
            if isinstance(node, list):
                for item in node:
                    self.visit(item)
            else:
                self.visit(node)
            new_entry, new_exit = self.__get_entry_exit()
            if escape_link and not self.escaped[-1]:
                self.__add_edge(new_entry, new_exit)
            self.__pop_entry_exit()
            self.escaped = self.escaped[:-1]

    def __visit_cond(self, cond: Node) -> None:
        """Visits a condition node (some expression in a conditional program construct),
        recording the condition by incrementing relevant counters and updating state
        tracking variables, before traversing the condition (to account for Myers' Interval).

        Args:
            cond (Node): The AST node corresponding to some program condition.
        """
        self.decisions += 1
        self.myers += 1
        was_in_cond = self.in_cond
        self.in_cond = True
        self.visit(cond)
        self.in_cond = was_in_cond

    def __get_labels(self, stmt: Node) -> Tuple[Node, Label | None]:
        """Given a statment AST node, this function recursively traverses
        any labels it may have to retrieve he base statement.

        Args:
            stmt (Node): An AST node corresponding to a statement.

        Returns:
            Tuple[Node, Label | None]: A tuple (statement, label) where
            statement is the label-stripped statement AST node, and label
            is the outermost label on that statement, where one exists.
        """
        label = None
        if isinstance(stmt, Label):
            label = stmt
        while isinstance(stmt, Label):
            stmt = stmt.stmt
        return (stmt, label)

    def visit_If(self, node: If) -> None:
        """Visits an If node in the AST, creating appropriate control flow
        nodes/edges for its true and false branches and recording its condition.

        Args:
            node (If): The If statement AST node to traverse.
        """
        if not self.in_function or self.escaped[-1] or node.iftrue is None:
            return self.generic_visit(node)
        if node.cond is not None:
            self.__visit_cond(node.cond)
        entry, exit = self.__get_entry_exit()
        then_entry = self.__new_node()
        self.__add_edge(entry, then_entry)
        self.__visit(node.iftrue, then_entry, exit)
        if node.iffalse is not None:
            else_entry = self.__new_node()
            self.__add_edge(entry, else_entry)
            do_escape = not isinstance(node.iffalse, If)
            self.__visit(node.iffalse, else_entry, exit, escape_link=do_escape)
        else:
            self.__add_edge(entry, exit)

    def visit_Compound(self, node: Compound) -> None:
        """Visits a Compound node in the AST, separating the block into linear
        blocs of control flow which are each individually handled using during
        their traversal. Handles the transitions of control flow between such
        sequences.

        Args:
            node (Compound): The Compound statement AST node to traverse.
        """
        if not self.in_function or self.escaped[-1] or node.block_items is None:
            return self.generic_visit(node)
        entry, exit = self.__get_entry_exit()
        # Splti the block into straight-line sequences of control flow
        block_parts = []
        current_seq = []
        for stmt in node.block_items:
            stmt, label = self.__get_labels(stmt)
            if isinstance(stmt, (Compound, If, Switch, While, DoWhile, For)):
                if len(current_seq) != 0:
                    block_parts.append(current_seq)
                    current_seq = []
                block_parts.append((stmt, label))
            else:
                current_seq.append((stmt, label))
        if len(current_seq) > 0:
            block_parts.append(current_seq)

        # Sequentially traverse each block part, chaining control flow as is appropriate
        for part in block_parts:

            # The last node exits at the exit, all other nodes exit to a new control flow node.
            if part == block_parts[-1]:
                new_node = exit
            else:
                new_node = self.__new_node()
            part_exit = new_node
            is_escape = part == block_parts[-1]

            # Visit each node in each sequence, providing label information and creating edges
            # where necessary.
            if isinstance(part, tuple):
                part, label = part
                self.__visit(
                    part if label is None else label,
                    entry,
                    part_exit,
                    modify=True,
                    escape_link=is_escape,
                )
            elif isinstance(part, list):
                part = [p[0] if p[1] is None else p[1] for p in part]
                self.__visit(part, entry, exit, modify=True, escape_link=is_escape)
                if part != block_parts[-1]:
                    self.__add_edge(entry, part_exit)

            # Each new block enters at the exit of the previous block.
            entry = part_exit

    def visit_Switch(self, node: Switch) -> None:
        """Visits a Switch node in the AST, creating appropriate control flow
        nodes/edges for each of its conditional cases.

        Args:
            node (Switch): The Switch statement AST node to traverse.
        """
        if not self.in_function or self.escaped[-1] or node.stmt is None:
            return self.generic_visit(node)
        entry, exit = self.__get_entry_exit()

        # First add an edge for the conditional block
        cond_entry = self.__new_node()
        self.__add_edge(entry, cond_entry)
        self.__modify_entry_exit(cond_entry, exit)
        self.breaks.append((self.levels, exit))

        # Add a node/edge for each respective case entry and visit these cases.
        # we visit in reverse order to appropriately handle node exits.
        prev_exit = exit
        for stmt in node.stmt.block_items[::-1]:
            if isinstance(stmt, Label):
                labelled_stmt, _ = self.__get_labels(stmt)
                if isinstance(labelled_stmt, (Case, Default)):
                    stmt = labelled_stmt
            if isinstance(stmt, (Case, Default)):
                case_entry = self.__new_node()
                self.__add_edge(cond_entry, case_entry)
                self.__visit(stmt, case_entry, prev_exit)
                self.decisions += 1
                self.myers += 1
                prev_exit = case_entry

        # Handle control flow sequences outside of case statements in the switch.
        is_first_other = True
        new_entry = cond_entry
        for stmt in node.stmt.block_items[::-1]:
            if not isinstance(stmt, (Case, Default)):
                if is_first_other:  # Must add edge for first non-case/default in switch
                    new_entry = self.__new_node()
                    self.__add_edge(cond_entry, new_entry)
                self.__visit(stmt, new_entry, exit)
        self.breaks = self.breaks[:-1]

    def visit_While(self, node: While) -> None:
        """Visits a While node in the AST, creating appropriate control flow
        nodes/edges for its condition and loop body.

        Args:
            node (While): The While statement AST node to traverse.
        """
        if not self.in_function or self.escaped[-1] or node.stmt is None:
            return self.generic_visit(node)
        if node.cond is not None:
            self.__visit_cond(node.cond)
        entry, exit = self.__get_entry_exit()
        cond_entry = self.__new_node()
        self.__add_edge(entry, cond_entry)
        self.__modify_entry_exit(cond_entry, exit)
        body_entry = self.__new_node()
        self.__add_edge(cond_entry, body_entry)
        self.breaks.append((self.levels, exit))
        self.continues.append((self.levels, cond_entry))
        self.__visit(node.stmt, body_entry, cond_entry)
        self.breaks = self.breaks[:-1]
        self.continues = self.continues[:-1]
        self.__add_edge(cond_entry, exit)

    def visit_DoWhile(self, node: DoWhile) -> None:
        """Visits a DoWhile node in the AST, creating appropriate control flow
        nodes/edges for its loop body and its condition.

        Args:
            node (DoWhile): The DoWhile statement AST node to traverse.
        """
        if not self.in_function or self.escaped[-1] or node.stmt is None:
            return self.generic_visit(node)
        if node.cond is not None:
            self.__visit_cond(node.cond)
        entry, exit = self.__get_entry_exit()
        test_entry = self.__new_node()
        body_entry = self.__new_node()
        self.__add_edge(entry, body_entry)
        self.__add_edge(test_entry, body_entry)
        self.__add_edge(test_entry, exit)
        self.breaks.append((self.levels, exit))
        self.continues.append((self.levels, test_entry))
        self.__visit(node.stmt, body_entry, test_entry)
        self.breaks = self.breaks[:-1]
        self.continues = self.continues[:-1]

    def visit_For(self, node: For) -> None:
        """Visits a For node in the AST, creating appropriate control flow
        nodes/edges for its initialisation, condition, increment statement,
        and its main loop body.

        Args:
            node (For): The For statement AST node to traverse.
        """
        if not self.in_function or self.escaped[-1] or node.stmt is None:
            return self.generic_visit(node)
        if node.cond is not None:
            self.__visit_cond(node.cond)
        entry, exit = self.__get_entry_exit()
        test_entry = self.__new_node()
        self.__add_edge(entry, test_entry)
        inc_entry = self.__new_node()
        body_entry = self.__new_node()
        self.__add_edge(test_entry, body_entry)
        self.__add_edge(test_entry, exit)
        self.__add_edge(inc_entry, test_entry)
        self.breaks.append((self.levels, exit))
        self.continues.append((self.levels, inc_entry))
        self.__visit(node.stmt, body_entry, inc_entry)
        self.breaks = self.breaks[:-1]
        self.continues = self.continues[:-1]

    def visit_Continue(self, node: Continue) -> None:
        """Visits a Continue statement node in the AST, creating an edge in the
        control flow graph between the current CFG node and the node recorded as
        being at the beginning of the loop body. Also records that we have escaped
        so that an extra outgoing edge after this statement is not created.

        Args:
            node (Continue): The Continue statement AST node to traverse.
        """
        if not self.in_function or self.escaped[-1] or self.levels == 0:
            return self.generic_visit(node)
        entry, _ = self.__get_entry_exit()
        self.__add_edge(entry, self.continues[-1][1])
        self.escaped[-1] = True

    def visit_Break(self, node: Break) -> None:
        """Visits a Break statement node in the AST, creating an edge in the control
        flow graph between the current CFG node and the node recorded as being at the
        end of the loop.Also records that we have escaped so that an extra outgoing
        edge after this statement is not created.

        Args:
            node (Break): The Break statement AST node to traverse.
        """
        if not self.in_function or self.escaped[-1] or self.levels == 0:
            return self.generic_visit(node)
        entry, _ = self.__get_entry_exit()
        self.__add_edge(entry, self.breaks[-1][1])
        self.escaped[-1] = True

    def visit_Label(self, node: Label) -> None:
        """Visits a Label node in the AST (i.e. a branch target), creating a new
        node in the control flow graph due to the node being a branch target, with
        an edge between the current CFG node and the newly created node. It then
        visits the labelled statement, modifying the current entry/exit stack values
        so that these are updated accordingly.

        Args:
            node (Label): The Label AST node to traverse.
        """
        if (
            not self.in_function
            or self.levels == 0
            or node.name is None
            or node.stmt is None
            or self.escaped[-1]
        ):
            return self.generic_visit(node)
        entry, exit = self.__get_entry_exit()
        labelled_entry = self.__new_node()
        self.__add_edge(entry, labelled_entry)
        self.label_blocks[node.name] = entry
        self.escaped[-1] = False  # we can no longer assume we have escaped the current
        # control flow, as it may be jumped to via the label.
        self.__visit(node.stmt, labelled_entry, exit, modify=True)

    def visit_Goto(self, node: Goto) -> None:
        """Visits a Goto (unconditional branch) statement node in the AST, recording the
        goto and its existing entry block so that it can later be backfilled and used with
        the corresponding label (which may occur later in the function) to update the CFG.
        We also note that the current control flow has been escaped, such that an outgoing
        edge is not made after this statement.

        Args:
            node (Goto): The Goto statement AST node to traverse.
        """
        if (
            not self.in_function
            or self.levels == 0
            or node.name is None
            or self.escaped[-1]
        ):
            return self.generic_visit(node)
        entry, _ = self.__get_entry_exit()
        if node.name not in self.gotos:
            self.gotos[node.name] = set()
        self.gotos[node.name].add(entry)
        self.escaped[-1] = True

    def visit_Return(self, node: Return) -> None:
        """Visits a Return statement node in the AST, recording a CFG edge transitioning
        to the final end block of the function's CFG, and noting that we have escaped
        control flow such that an outgoing edge to the exit is not made after this statement.

        Args:
            node (Return): The return statment AST node to traverse.
        """
        if not self.in_function or self.escaped[-1] or self.levels == 0:
            return self.generic_visit(node)
        entry, _ = self.__get_entry_exit()
        func_exit = self.exit_stack[0]
        self.__add_edge(entry, func_exit)
        self.escaped[-1] = True

    def visit_BinaryOp(self, node: BinaryOp) -> None:
        """Visits a Binary operator (expression) node in the AST, counting instances
        of logical binary operators in conditions to implement Myers' Interval for
        extending cyclomatic complexity.

        Args:
            node (BinaryOp): The binary operation AST node to traverse.
        """
        if not self.in_function or not self.in_cond or self.escaped[-1]:
            return self.generic_visit(node)
        if node.op is not None and node.op in ["&&", "||", "^"]:
            self.myers += 1
            self.generic_visit(node)

    def visit_FuncDef(self, node: FuncDef) -> None:
        """Visits a Function Definition node in the AST, initialising a variety
        of structures and tracking variables related to the creation and storage
        of a control flow graph for that function. This also performs appropriate
        control flow updates when backfilling GOTO statements with their branch
        targets, adding edges between these blocks and their target label nodes.

        Args:
            node (FuncDef): The function definition AST node to traverse and record.
        """
        if node.decl is None or node.body is None:
            return self.generic_visit(node)

        # Update tracking variables and structures
        self.functions += 1
        was_in_function = self.in_function
        prev_node_number = self.node_number
        prev_graph = self.cfgraph
        self.in_function = True
        self.levels += 1
        self.node_number = 0
        self.escaped.append(False)
        self.cfgraph = dict()
        self.label_blocks = dict()
        self.gotos = dict()
        self.graphs[node] = self.cfgraph
        self.decisions = 1
        self.myers = 1

        # Create entry and exit nodes for the function's CFG, and visit the function.
        entry, exit = self.__new_node(), self.__new_node()
        self.__set_entry_exit(entry, exit)
        self.generic_visit(node)
        self.__pop_entry_exit()
        self.func_decisions[node] = self.decisions
        self.func_myers[node] = self.myers

        # Backfill goto branch statements with their labels (branch targets), adding
        # corresponding edges in the AST.
        for label_name, goto_entries in self.gotos.items():
            if label_name not in self.label_blocks:
                continue
            label_entry = self.label_blocks[label_name]
            for goto_entry in goto_entries:
                self.__add_edge(goto_entry, label_entry)

        # Remove redundant exit node for single-block (straight-line) graphs
        if len(self.cfgraph[entry]) == 0 or (
            len(self.cfgraph[entry]) == 1 and list(self.cfgraph[entry])[0] == exit
        ):
            self.cfgraph = {entry: set()}
            self.graphs[node] = self.cfgraph
        self.levels -= 1
        self.cfgraph = prev_graph
        self.node_number = prev_node_number
        self.in_function = was_in_function


class CyclomaticComplexityUnit(CodeMetricUnit):
    """A class for calculating metrics relating to McCabe's Cylcomatic Complexity Index,
    a measure for software complexity based on the number of possible control flow paths
    for a given piece of code. These metrics measure cyclomatic complexity based on the
    original definition for structured programs, the modern definition for unstructured
    programs (using the mathematical CFG equation), and the Myers' Interval extension."""

    name = "McCabe's Cyclomatic Complexity"
    gui_name = '<p style="line-height:80%">McCabe\'s Cyclomatic<br>Complexity</p>'
    positions = dict(
        [
            (x, i)
            for (i, x) in enumerate(
                [
                    "Rating",
                    "Orig. Rating",
                    "Source Rating",
                    "Orig. Source Rating",
                    "Avg. Cyclomatic M\u0305",
                    "Avg. Orig. M\u0305",
                    "Avg. Myers' Interval",
                    "Total Cyclomatic \u03A3M",
                    "Total Orig. \u03A3M",
                    "Total Myers' Interval",
                    "Avg. Nodes (N\u0305)",
                    "Avg. Edges (E\u0305)",
                    "Total Nodes (\u03A3N)",
                    "Total Edges (\u03A3E)",
                ]
            )
        ]
    )
    name_tooltip = (
        "A set of metrics for calculating the complexity of code in terms of\n"
        "its difficulty to understand. Roughly measures the number of possible\n"
        "paths through the code, and so is often used to determine code paths\n"
        "for maintainability (how easy it is to test a function). This comprises\n"
        "the original McCabe's cyclomatic Complexity metric for structured programs,\n"
        "my interpretation of the metric for non-structured programs, Myers' extension\n"
        "to the original metric and some of its constituent parts.\n"
        "\nThis metric primarily helps to measure obfuscation potency (complexity)."
    )
    tooltips = {
        "Rating": "The interpretation of the non-structured numerical cyclomatic\n"
        "complexity metric derived by categorizing different bands of numbers.\n"
        "Split between: Simple / More Complex / Complex / Untestable\n"
        "as in the original paper.",
        "Orig. Rating": "The interpretation of McCabe's original structured program\n"
        "cyclomatic complexity metric derived by categorizing different bands of numbers.\n"
        "Split between: Simple / More Complex / Complex / Untestable\n"
        "as in the original paper.",
        "Source Rating": "The interpretation of the non-structured numerical cyclomatic\n"
        "complexity metric of the original, unobfuscated program, derived by categorizing\n"
        "different bands of numbers.\n"
        "Split between: Simple / More Complex / Complex / Untestable\n"
        "as in the original paper.",
        "Orig. Source Rating": "The interpretation of McCabe's original structured program\n"
        "cyclomatic complexity metric of the original, unobfuscated program, derived by\n"
        "categorizing different bands of numbers.\n"
        "Split between: Simple / More Complex / Complex / Untestable\n"
        "as in the original paper.",
        "Avg. Cyclomatic M\u0305": "The mean cyclomatic number for all the functions in the\n"
        "program, where a new definition for unstructured programs has been used that considers\n"
        "the full control flow graph (minus lazy operations in decision nodes), such that multiple\n"
        "exit (return) points, labels/gotos and unreachable code are all factored into calculations.",
        "Avg. Orig. M\u0305": "The mean cyclomatic number for all the functions in the\n"
        "program, where the original definition for structured programs has been used, simply\n"
        "counting the number of decision points / loops (and switch cases) plus one. This does not\n"
        "factor in code unreachability nor non-structured programming constructs.",
        "Avg. Myers' Interval": "The mean Myers' interval for all functions in the program,\n"
        "which is a sort of 'upper bound' for the original cyclomatic complexity metric that also\n"
        "increments for each logical binary operator in a compound condition to consider hidden complexity.",
        "Total Cyclomatic \u03A3M": "The total cyclomatic number summed from all functions in the\n"
        "program, where a new definition for unstructured programs has been used that considers\n"
        "the full control flow graph (minus lazy operations in decision nodes), such that multiply\n"
        "exit (return) points, labels/gotos and unreachable code are all factored into calculations.",
        "Total Orig. \u03A3M": "The total cyclomatic number summed from all functions in the\n"
        "program, where the original definition for structured programs has been used, simply\n"
        "counting the number of decision points / loops (and switch cases) plus one. This does not\n"
        "factor in code unreachability nor non-structured programming constructs.",
        "Total Myers' Interval": "The total Myers' interval summed from all functions in the program,\n"
        "which is a sort of 'upper bound' for the original cyclomatic complexity metric that also\n"
        "increments for each logical binary operator in a compound condition to consider hidden complexity.",
        "Avg. Nodes (N\u0305)": "The mean number of nodes (per function) calculated for the new\n"
        "non-structured cyclomatic complexity metric (not the original) - each node corresponds to\n"
        "one basic block in the control flow graph, minus lazy operations and not including unreachable code.",
        "Avg. Edges (E\u0305)": "The mean number of edges (per function) calculated for the new\n"
        "non-structured cyclomatic complexity metric (not the original) - each edge corresponds to\n"
        "some jump (conditional or unconditional) between basic blocks in the control flow graph,\n"
        "minus lazy operations and not including unreachable code.",
        "Total Nodes (\u03A3N)": "The total summed number of nodes calculated for the new\n"
        "non-structured cyclomatic complexity metric (not the original) - each node corresponds to\n"
        "one basic block in the control flow graph, minus lazy operations and not including unreachable code.",
        "Total Edges (\u03A3E)": "The total summed number of edges calculated for the new\n"
        "non-structured cyclomatic complexity metric (not the original) - each edge corresponds to\n"
        "some jump (conditional or unconditional) between basic blocks in the control flow graph,\n"
        "minus lazy operations and not including unreachable code.",
    }
    predecessors = []
    cached = {}

    def __cache_metrics(self, metrics) -> None:
        """Caches the provided set of metrics within the class' cache, such that
        any future metric group that wishes to use cyclomatic complexity metrics in
        their calculations can access these cached values without recomputing them.

        Args:
            metrics (Metrics): The dictionary of metrics to cache.
        """
        CyclomaticComplexityUnit.cached = dict(
            x for x in CyclomaticComplexityUnit.cached.items()
        )
        for k, v in metrics.items():
            CyclomaticComplexityUnit.cached[k] = v

    def get_edges(self, graph: dict[int, Iterable[int]]) -> int:
        """Given a control flow graph, calculate the total number of directed edges in the CFG.

        Args:
            graph (dict[int,Iterable[int]]): The CFG in its adjacency-list representation.

        Returns:
            int: The nubmer of unique directed edges in the CFG.
        """
        return sum([len(vals) for _, vals in graph.items()])

    def get_interpretation(self, cyclo_num: int) -> str:
        """Given some Cyclomatic Complexity number, this returns the corresponding
        string interpretation as defined by McCabe in his initial publication.

        Args:
            cyclo_num (int): The cyclomatic complexity number.

        Returns:
            str: _description_
        """
        if cyclo_num == "N/A":
            interpretation = "N/A"
        elif 1 <= cyclo_num <= 10:
            interpretation = "Simple"
        elif 11 <= cyclo_num <= 20:
            interpretation = "More Complex"
        elif 21 <= cyclo_num <= 50:
            interpretation = "Complex"
        elif 50 <= cyclo_num:
            interpretation = "Untestable"
        else:
            interpretation = "Unknown"
        return interpretation

    def calculate_metrics(self, old_source: CSource, new_source: CSource) -> None:
        """Computes and formats the set of cyclomatic complexity metrics for the given
        programs, by computing the control flow graph and then performing relevant
        calculations and conversions.

        Args:
            old_source (CSource): The original C source file before obfuscation.
            new_source (CSource): The final obfuscated C source file.
        """
        # Generate the CFGs and retrieve CFG information.
        old_cfg_generator = CFGGenerator()
        old_cfg_generator.visit(old_source.t_unit)
        old_graphs = list(old_cfg_generator.graphs.values())
        old_nodes = [len(graph.values()) for graph in old_graphs]
        old_edges = [self.get_edges(graph) for graph in old_graphs]
        new_cfg_generator = CFGGenerator()
        new_cfg_generator.visit(new_source.t_unit)
        new_graphs = list(new_cfg_generator.graphs.values())
        new_nodes = [len(graph.values()) for graph in new_graphs]
        new_edges = [self.get_edges(graph) for graph in new_graphs]

        # Compute the average numbers of nodes and edges
        if len(old_graphs) != 0:
            old_total_nodes = sum(old_nodes)
            old_avg_nodes = old_total_nodes / len(old_nodes)
            old_total_edges = sum(old_edges)
            old_avg_edges = old_total_edges / len(old_edges)
        else:
            old_total_nodes = 0
            old_avg_edges = "N/A"
            old_total_edges = 0
        if len(new_graphs) != 0:
            new_total_nodes = sum(new_nodes)
            new_avg_nodes = new_total_nodes / len(new_nodes)
            node_new = "{:.1f}".format(new_avg_nodes)
            new_total_edges = sum(new_edges)
            new_avg_edges = new_total_edges / len(new_edges)
            edge_new = "{:.1f}".format(new_avg_edges)
        else:
            new_total_nodes = 0
            node_new = "N/A"
            new_total_edges = 0
            edge_new = "N/A"
        if len(old_graphs) == 0 or len(new_graphs) == 0:
            node_delta = "N/A"
            edge_delta = "N/A"
        else:
            node_delta = float_delta(new_avg_nodes, old_avg_nodes)
            edge_delta = float_delta(new_avg_edges, old_avg_edges)
        self.add_metric("Avg. Nodes (N\u0305)", node_new, node_delta)
        self.add_metric(
            "Total Nodes (\u03A3N)",
            str(new_total_nodes),
            int_delta(new_total_nodes, old_total_nodes),
        )
        self.add_metric("Avg. Edges (E\u0305)", edge_new, edge_delta)
        self.add_metric(
            "Total Edges (\u03A3E)",
            str(new_total_edges),
            int_delta(new_total_edges, old_total_edges),
        )

        # Compute the cyclomatic number and ratings
        old_cyclo_numbers = []
        for i in range(len(old_graphs)):
            cyclo_num = old_edges[i] - old_nodes[i] + 2
            old_cyclo_numbers.append(cyclo_num)
        total_old_cyclo = sum(old_cyclo_numbers)
        if len(old_graphs) != 0:
            avg_old_cyclo = total_old_cyclo / len(old_graphs)
        else:
            avg_old_cyclo = "N/A"
        new_cyclo_numbers = []
        for i in range(len(new_graphs)):
            cyclo_num = new_edges[i] - new_nodes[i] + 2
            new_cyclo_numbers.append(cyclo_num)
        total_new_cyclo = sum(new_cyclo_numbers)
        if len(new_graphs) != 0:
            avg_new_cyclo = total_new_cyclo / len(new_graphs)
            avg_new_cyclo_str = "{:.1f}".format(avg_new_cyclo)
            if len(old_graphs) != 0:
                avg_cyclo_delta = float_delta(avg_new_cyclo, avg_old_cyclo)
            else:
                avg_cyclo_delta = "N/A"
        else:
            avg_new_cyclo = "N/A"
            avg_new_cyclo_str = "N/A"
            avg_cyclo_delta = "N/A"
        self.add_metric(
            "Total Cyclomatic \u03A3M",
            str(total_new_cyclo),
            int_delta(total_new_cyclo, total_old_cyclo),
        )
        self.add_metric("Avg. Cyclomatic M\u0305", avg_new_cyclo_str, avg_cyclo_delta)
        self.add_metric("Rating", self.get_interpretation(avg_new_cyclo))
        self.add_metric("Source Rating", self.get_interpretation(avg_old_cyclo))

        # Compute the original cyclomatic complexity values and corresponding ratings
        old_orig_values = old_cfg_generator.func_decisions.values()
        new_orig_values = new_cfg_generator.func_decisions.values()
        total_old_orig_values = sum(old_orig_values)
        total_new_orig_values = sum(new_orig_values)
        if len(old_orig_values) != 0:
            avg_old_orig_values = total_old_orig_values / len(old_orig_values)
        else:
            avg_old_orig_values = "N/A"
        if len(new_orig_values) != 0:
            avg_new_orig_values = total_new_orig_values / len(new_orig_values)
            avg_new_orig_values_str = "{:.1f}".format(avg_new_orig_values)
        else:
            avg_new_orig_values = "N/A"
            avg_new_orig_values_str = "N/A"
        self.add_metric(
            "Total Orig. \u03A3M",
            str(total_new_orig_values),
            int_delta(total_new_orig_values, total_old_orig_values),
        )
        self.add_metric(
            "Avg. Orig. M\u0305",
            avg_new_orig_values_str,
            float_delta(avg_new_orig_values, avg_old_orig_values),
        )
        self.add_metric("Orig. Rating", self.get_interpretation(avg_new_orig_values))
        self.add_metric(
            "Orig. Source Rating", self.get_interpretation(avg_old_orig_values)
        )
        self.__cache_metrics(
            {"Cyclomatic Complexity": (avg_new_orig_values, avg_old_orig_values)}
        )

        # Compute the Myers' Interval representations of Cyclomatic Complexity
        old_myers = old_cfg_generator.func_myers.values()
        new_myers = new_cfg_generator.func_myers.values()
        total_old_myers = sum(old_myers)
        total_new_myers = sum(new_myers)
        if len(old_myers) != 0:
            avg_old_myers = total_old_myers / len(old_myers)
        else:
            avg_old_myers = "N/A"
        if len(new_myers) != 0:
            avg_new_myers = total_new_myers / len(new_myers)
            avg_new_myers_str = "{:.2f}".format(avg_new_myers)
        else:
            avg_new_myers = "N/A"
            avg_new_myers_str = "N/A"
        self.add_metric(
            "Avg. Myers' Interval",
            avg_new_myers_str,
            "{}".format(float_delta(avg_new_myers, avg_old_myers)),
        )
        self.add_metric(
            "Total Myers' Interval",
            str(total_new_myers),
            "{}".format(int_delta(total_new_myers, total_old_myers)),
        )


class CognitiveAnalyzer(NodeVisitor):
    """This class traverses an Abstract Syntax Tree (AST) to compute the Cognitive
    Complexity metric as according to its whitepaper definition."""

    def __init__(self):
        """The constructor for the CognitiveAnalyzer constructor."""
        super(CognitiveAnalyzer, self).__init__()
        self.__reset()

    def __reset(self) -> None:
        """Resets the state of the CognitiveAnalyzer, resetting state tracking variables
        to their initial vaues and clearing graphs/dict data structures.
        """
        self.current_function = None
        self.cognitive = 0
        self.max_nesting = 0
        self.func_nestings = dict()
        self.func_cognitives = dict()
        self.call_graph = dict()  # To detect direct/indirect recursion
        self.logical_op_seq = (
            None,
            0,
        )  # To detect sequences (chains) of logical binary ops

    def __find_recursion_cycles(self) -> None:
        """Finds recursion cycles in the call graph of a given program, adding 1 to the cognitive
        complexity of each function involved in each unique recursion cycle.
        """
        # Donald B' Johnson's algorithm to find all simple cycles in a graph
        # using the networkx library implementation
        graph = networkx.DiGraph()
        graph.add_nodes_from(self.func_cognitives.keys())
        for func, called in self.call_graph.items():
            graph.add_edges_from([(func, cfunc) for cfunc in called])
        for cycle in networkx.simple_cycles(graph):
            # We increment for each method in a recursion cycle, whether direct or indirect.
            for func in cycle:
                self.func_cognitives[func] += 1

    def visit_FileAST(self, node: FileAST) -> None:
        """Visits the FileAST root AST node, first traversing the AST and then finding
        recursion cycles.

        Args:
            node (FileAST): The FileAST root AST node to traverse.
        """
        self.generic_visit(node)
        self.__find_recursion_cycles()

    def visit_FuncDef(self, node: FuncDef) -> None:
        """Visits a Function Definition AST node, initialising the value of integer variables
        for tracking nesting levels and cognitive values, an creating the call graph.

        Args:
            node (FuncDef): The Function Defintion AST node.
        """
        if node.decl is None or node.decl.name is None or node.body is None:
            return self.visit(node)
        prev_function = self.current_function
        self.current_function = node.decl.name
        self.call_graph[node.decl.name] = set()
        self.cognitive = 0
        self.nesting = 0
        self.max_nesting = 0
        self.generic_visit(node)
        self.func_cognitives[node.decl.name] = self.cognitive
        self.func_nestings[node] = self.max_nesting
        self.current_function = prev_function

    def visit_FuncCall(self, node: FuncCall) -> None:
        """Visits a Function Call AST node, recording the ocurrence of the function
        call in the call graph (creating an edge between the current function and
        the called function))

        Args:
            node (FuncCall): The function call AST node to visit and record.
        """
        if self.current_function is None or node.name is None or node.name.name is None:
            return self.generic_visit(node)
        name = node.name.name
        reached_set = self.call_graph[self.current_function]
        if name not in reached_set and name in self.call_graph:
            reached_set.add(name)
        self.generic_visit(node)

    def visit_BinaryOp(self, node: BinaryOp) -> None:
        """Visits a Binary Operator AST node, traversing sequences of logical binary
        operands to determien the number of unique such sequences, incrementing the
        cognitive complexity count by that number. For example, the expression
            `(a && b && c || d || e && f && g || h || i)`
        would result in an increment of 4.

        Args:
            node (BinaryOp): The binary operator AST node to visit and record.
        """
        if (
            self.current_function is None
            or node.op is None
            or node.op not in ["^", "&&", "||"]
        ):
            return self.generic_visit(node)
        logical_op, sequence_len = self.logical_op_seq
        if sequence_len == 0:
            self.logical_op_seq = (node.op, 1)
        elif node.op == logical_op:
            self.logical_op_seq = (node.op, 2)
        else:
            self.logical_op_seq = (node.op, 1)
            self.cognitive += 1
        if node.left is not None and node.right is not None:
            if not isinstance(node.left, BinaryOp) and not isinstance(
                node.right, BinaryOp
            ):
                # End of sequence, so add the current sequence
                self.cognitive += 1
        self.generic_visit(node)

    def generic_visit(self, node: Node):
        """Visits a generic AST node, calculating additional layers of nesting
        and incrementing the cognitive complexity number accordingly (by the amount
        of nesting plus one). This also handles control flow statements and GOTOs,
        incrementing cognitive complexity by one accordingly.

        Args:
            node (Node): The generic AST node to traverse.
        """
        if self.current_function is None:
            return super(CognitiveAnalyzer, self).generic_visit(node)
        # A special separate case for C - a compound within a compound,
        # as compounds used inside compounds introduce additional complexity
        # via variable shadowing and scoping. I also apply a layer of
        # nesting in such a case.
        if isinstance(node, Compound) and node.block_items is not None:
            for child in node.block_items:
                if isinstance(child, Compound):
                    self.cognitive += 1 + self.nesting
                    self.nesting += 1
                    self.visit(child)
                    self.nesting -= 1
                else:
                    self.visit(child)
        elif isinstance(node, (For, While, DoWhile, If, TernaryOp, Switch)):
            self.cognitive += 1 + self.nesting
            if (
                isinstance(node, If)
                and node.iffalse is not None
                and not isinstance(node.iffalse, If)
            ):
                # Count an else branch, but not an 'else if' branch, because
                # that will be detected by the above conditional again instead.
                self.cognitive += 1 + self.nesting
            self.nesting += 1
            self.max_nesting = max(self.max_nesting, self.nesting)
            super(CognitiveAnalyzer, self).generic_visit(node)
            self.nesting -= 1
        elif isinstance(node, (Goto, Break, Continue)):
            self.cognitive += 1
            super(CognitiveAnalyzer, self).generic_visit(node)
        else:
            super(CognitiveAnalyzer, self).generic_visit(node)


class CognitiveComplexityUnit(CodeMetricUnit):
    """A class for calculating metrics relating to Sonar's Cognitive Complexity Index,
    a measure for software complexity based on how difficult code is to actually maintain
    for software engineers, based on layers of nesting, control flow statements, recursion,
    and more. Alongside this we group metrics based on the nesting depths of functions."""

    name = "Cognitive Complexity"
    positions = dict(
        [
            (x, i)
            for (i, x) in enumerate(
                [
                    "Avg. Cognitive Num",
                    "Max Cognitive Num",
                    "Total Cognitive Num",
                    "Cognitive SD",
                    "Avg. Nesting Depth",
                    "Max Nesting Depth",
                    "Nesting SD",
                ]
            )
        ]
    )
    name_tooltip = (
        "A recent (2017-2022) alternative to the cyclomatic complexity metric.\n"
        "Where cyclomatic complexity focuses on code paths for e.g. testing and\n"
        "maintainability, cognitive complexity focuses on the cognitive load of\n"
        "comprehending a method, by taking into account programming structures,\n"
        "nesting, sequential chaining of logical operators, breaks in control flow,\n"
        "recursion (both direct and indirect), and considering switches only once.\n"
        "This metric has been slightly adapted to fit the C language, adding a\n"
        "structural and nesting increment for compound nesting (compounds in compounds).\n"
        "\nThis metric primarily helps to measure obfuscation potency (complexity)."
    )
    tooltips = {
        "Avg. Cognitive Num": "The average cognitive complexity number of all the functions in\n"
        "the program, giving a rough measure for the average 'incomprehensibility' of the program.",
        "Max Cognitive Num": "The highest cognitive complexity number of all the functions in\n"
        "the program, indicating roughly how incomprehensible the most difficult parts are.",
        "Total Cognitive Num": "The total cognitive complexity number summed from all the functions\n"
        "in the program, indicating at a glance a mixture of the program's size and complexity.",
        "Cognitive SD": "The standard deviation in cognitive complexity numbers for all the functions\n"
        "in the program, where 2 or more functions exist. This indicates how varied the complexity\n"
        "of functions within the program are.",
        "Avg. Nesting Depth": "The average nesting depth for all functions in the program, measuring\n"
        "how many nested layers deep each function reaches (in the worst case) on average.",
        "Max Nesting Depth": "The maximum nesting depth reached for any one function in the entire\n"
        "program, indicating the highest level of nesting complexity in the program.",
        "Nesting SD": "The standard deviation in nesting depths for all the functions in the program,\n"
        "where 2 or more functions exist. This indicates how varied the nesting complexity of\n"
        "functions within the program are.",
    }
    predecessors = []

    def calculate_metrics(self, old_source: CSource, new_source: CSource) -> None:
        """Computes and formats the set of cognitive complexity metrics for the given
        programs.

        Args:
            old_source (CSource): The original C source file before obfuscation.
            new_source (CSource): The final obfuscated C source file.
        """
        # Travese program ASTs and gather cognitive complexity numbers
        old_analyzer = CognitiveAnalyzer()
        new_analyzer = CognitiveAnalyzer()
        old_analyzer.visit(old_source.t_unit)
        new_analyzer.visit(new_source.t_unit)
        old_cognitive = old_analyzer.func_cognitives.values()
        new_cognitive = new_analyzer.func_cognitives.values()

        # Calculate the total, average, and max cognitive numbers across functions
        total_old_cognitive = sum(old_cognitive)
        total_new_cognitive = sum(new_cognitive)
        self.add_metric(
            "Total Cognitive Num",
            str(total_new_cognitive),
            int_delta(total_new_cognitive, total_old_cognitive),
        )
        if len(old_cognitive) != 0:
            avg_old_cognitive = total_old_cognitive / len(old_cognitive)
        else:
            avg_old_cognitive = "N/A"
        if len(new_cognitive) != 0:
            avg_new_cognitive = total_new_cognitive / len(new_cognitive)
            avg_new_cognitive_str = "{:.1f}".format(avg_new_cognitive)
        else:
            avg_new_cognitive = "N/A"
            avg_new_cognitive_str = "N/A"
        self.add_metric(
            "Avg. Cognitive Num",
            avg_new_cognitive_str,
            float_delta(avg_new_cognitive, avg_old_cognitive),
        )
        max_new_cognitive = max([0] + list(new_cognitive))
        self.add_metric(
            "Max Cognitive Num",
            str(max_new_cognitive),
            int_delta(max_new_cognitive, max([0] + list(old_cognitive))),
        )

        # Calculate the standard deviation in cognitive numbers.
        if len(old_cognitive) >= 2:
            sd_old_cognitive = math.sqrt(
                statistics.variance(old_cognitive, avg_old_cognitive)
            )
        else:
            sd_old_cognitive = "N/A"
        if len(new_cognitive) >= 2:
            sd_new_cognitive = math.sqrt(
                statistics.variance(new_cognitive, avg_new_cognitive)
            )
            sd_new_cognitive_str = "{:.1f}".format(sd_new_cognitive)
        else:
            sd_new_cognitive = "N/A"
            sd_new_cognitive_str = "N/A"
        self.add_metric(
            "Cognitive SD",
            sd_new_cognitive_str,
            float_delta(sd_new_cognitive, sd_old_cognitive),
        )

        # Calcuate the average and max nesting depths, and the standard deviation in
        # nesting depth.
        old_nesting = old_analyzer.func_nestings.values()
        new_nesting = new_analyzer.func_nestings.values()
        if len(old_nesting) != 0:
            avg_old_nesting = sum(old_nesting) / len(old_nesting)
        else:
            avg_old_nesting = "N/A"
        if len(new_nesting) != 0:
            avg_new_nesting = sum(new_nesting) / len(new_nesting)
            avg_new_nesting_str = "{:.1f}".format(avg_new_nesting)
        else:
            avg_new_nesting = "N/A"
            avg_new_nesting_str = "N/A"
        self.add_metric(
            "Avg. Nesting Depth",
            avg_new_nesting_str,
            float_delta(avg_new_nesting, avg_old_nesting),
        )
        max_new_nesting = max([0] + list(new_nesting))
        self.add_metric(
            "Max Nesting Depth",
            str(max_new_nesting),
            int_delta(max_new_nesting, max([0] + list(old_nesting))),
        )
        if len(old_nesting) >= 2:
            sd_old_nesting = math.sqrt(
                statistics.variance(old_nesting, avg_old_nesting)
            )
        else:
            sd_old_nesting = "N/A"
        if len(new_nesting) >= 2:
            sd_new_nesting = math.sqrt(
                statistics.variance(new_nesting, avg_new_nesting)
            )
            sd_new_nesting_str = "{:.1f}".format(sd_new_nesting)
        else:
            sd_new_nesting = "N/A"
            sd_new_nesting_str = "N/A"
        self.add_metric(
            "Nesting SD",
            sd_new_nesting_str,
            float_delta(sd_new_nesting, sd_old_nesting),
        )


class HalsteadAnalyzer(NodeVisitor):
    """This class traverses an Abstract Syntax Tree (AST) to comptue the number
    of unique operators and operand identifiers, to separate identifier tokens into
    operands and operators as is required for Halstead's Complexity measure metrics."""

    def __init__(self):
        """The constructor for the HalsteadAnalyzer, intialising its state variables"""
        self.__reset()

    def __reset(self) -> None:
        """Resests the state of the HalsteadAnalyzer, resetting structures and counters
        for storing operands and operators."""
        self.operands = 0
        self.unique_operands = set()
        self.operators = 0
        self.unique_operators = set()

    def __add_operand(self, operand: str) -> None:
        """Records an occurrence of an operand identifier, incrementing the operand count
        and storing it if it is unique.

        Args:
            operand (str): The identifier name string to add.
        """
        self.operands += 1
        self.unique_operands.add(operand)

    def __add_operator(self, operator: str) -> None:
        """Records an occurrence of an operator identifier, incrementing the oeprator count
        and storing it if it is unique.

        Args:
            operator (str): The identifier name string to add.
        """
        self.operators += 1
        self.unique_operators.add(operator)

    def visit_FuncDef(self, node: FuncDef) -> None:
        """Visits a Function Definition AST node, recording the function name as an operator
        where it exists.

        Args:
            node (FuncDef): The FuncDef AST node to traverse.
        """
        if node.decl is not None and node.decl.name is not None:
            self.__add_operator(node.decl.name)
        if node.param_decls is not None:
            self.visit(node.param_decls)
        if node.body is not None:
            self.visit(node.body)

    def visit_FuncCall(self, node: FuncCall) -> None:
        """Visits a Function Call AST node, recording the function name as an operator
        where it exists.

        Args:
            node (FuncCall): The FuncCall AST node to traverse.
        """
        if node.name is not None and node.name.name is not None:
            self.__add_operator(node.name.name)
        if node.args is not None:
            self.visit(node.args)

    def visit_Decl(self, node: Decl) -> None:
        """Visits a declaration AST node, recording a variable name as an operand
        where it exists.

        Args:
            node (Decl): The declaration AST node to traverse.
        """
        if node.name is not None:
            self.__add_operand(node.name)
        self.generic_visit(node)

    def visit_Enum(self, node: Enum) -> None:
        """Visits an enumerator AST node, recording the enumerated type name as
        an operand where it exists.

        Args:
            node (Enum): The enumerator AST node to traverse.
        """
        if node.name is not None:
            self.__add_operand(node.name)
        self.generic_visit(node)

    def visit_Struct(self, node: Struct) -> None:
        """Visits a struct AST node, recording the struct name as an operand.

        Args:
            node (Struct): The struct AST node to traverse.
        """
        if node.name is not None:
            self.__add_operand(node.name)
        self.generic_visit(node)

    def visit_Union(self, node: Union) -> None:
        """Visits a union AST node, recording the union name as an operand.

        Args:
            node (Union): The union AST node to traverse.
        """
        if node.name is not None:
            self.__add_operand(node.name)
        self.generic_visit(node)

    def visit_ID(self, node: ID) -> None:
        """Visits an identifier AST node, recording the name of the identifier
        reference as an operand where it exists.

        Args:
            node (ID): The identifier reference AST node to traverse.
        """
        if node.name is not None:
            self.__add_operand(node.name)
        self.generic_visit(node)


class HalsteadComplexityUnit(CodeMetricUnit):
    """A class for calculating metrics related to Halstead's Complexity Measures, which are
    a group of measures for software complexity based on modelling the linguistig complexity
    of a program, splitting tokens into operators and operands and comparing the number of
    distinct (unique) and overall operators/operands to compute a variety of metrics."""

    name = "Halstead Complexity Measures"
    gui_name = '<p style="line-height:80%">Halstead Complexity<br>Measures</p>'
    positions = dict(
        [
            (x, i)
            for (i, x) in enumerate(
                [
                    "Vocabulary (\u03B7)",
                    "Length (N)",
                    "Estimated Length (\u004E\u0302)",
                    "Volume (V)",
                    "Difficulty (D)",
                    "Effort (E)",
                    "Estimated Time (T)",
                    "Delivered Bugs (B)",
                ]
            )
        ]
    )
    name_tooltip = (
        "Halstead's complexity measures are metrics that aim to determine the complexity\n"
        "of code based on their range of vocabulary and sizes, identifying measurable\n"
        "properties of software and their relations in a similar manner to physical matter.\n"
        "They provide, among other things, estimations of the difficulty/effort required to\n"
        "code (and hence likely also reverse engineer), the time to program, and the number\n"
        "of estimated bugs. Importantly note that this will not be fully correct for the given\n"
        "source code, as the preprocessing phase will naturally alter some of the syntax before\n"
        'lexing (e.g. "int a, b, c;" to "int a; int b; int c;").\n'
        "\nThis metric primarily helps to measure obfuscation resilience and potency (complexity)."
    )
    tooltips = {
        "Vocabulary (\u03B7)": "The total number of distinct (unique) operators and operands\n"
        "within the entire program body.\n  \u03B7 = \u03B71 + \u03B72",
        "Length (N)": "The total number of operators and operands within the entire program body.\n"
        "   N = N1 + N2",
        "Estimated Length (\u004E\u0302)": "The estimated size of a typical program based on\n"
        "the program's vocabulary (and not considering the actual length at all).\n"
        "   \u004E\u0302 = \u03B71 x log_2(\u03B71) + \u03B72 x log_2(\u03B72)",
        "Volume (V)": "The amount of space, in bits, necessary for storing the program\n"
        "in a minimal case where a uniform binary encoding of the vocabulary is used.\n"
        "   V = N x log_2(\u03B7)",
        "Difficulty (D)": "A quantitative metric representing how difficult the progam\n"
        "is to understand/maintain/handle based on its size and vocabulary.\n"
        " D = (\u03B71 / 2) x (N2 / \u03B72)",
        "Effort (E)": "A quantitative metric measuring the amount of mental effort/activity\n"
        "required to program this code in this language.\n   E = D x V",
        "Estimated Time (T)": "The estimated amount of time to program this code in this language, based\n"
        "on an approximated 18 (the Stoud number) seconds per unit effort.\n"
        "This Stoud number 18 has been empirically designed via psychological reasoning and\n"
        "is used as the recommende standard.\n   T = E / 18",
        "Delivered Bugs (B)": "The estimated amount of bugs (errors) that we would expect to\n"
        "find in the program based on its size and vocabulary.\n   B = E^(2/3) / 3000",
    }
    predecessors = []
    cached = {}

    __operand_toks = (
        "CHAR",
        "CONST",
        "TYPEID",
        "INT_CONST_DEC",
        "INT_CONST_OCT",
        "INT_CONST_OCT",
        "INT_CONST_HEX",
        "INT_CONST_BIN",
        "INT_CONST_CHAR",
        "FLOAT_CONST",
        "HEX_FLOAT_CONST",
        "CHAR_CONST",
        "WCHAR_CONST",
        "U8CHAR_CONST",
        "U16CHAR_CONST",
        "U32CHAR_CONST",
        "STRING_LITERAL",
        "WSTRING_LITERAL",
        "U8STRING_LITERAL",
        "U16STRING_LITERAL",
        "U32STRING_LITERAL",
        "ELLIPSIS",
    )
    __exclude_toks = (
        "ID",  # IDs are a case by case basis: variables are operands, but
        #     function names are operators
        "RBRACKET",  # For indexing, only count once (so only count '[')
        "RBRACE",  # Same as above - compounds only count once (so only count '{')
        "RPAREN",  # Same as above - parentheses only count once (so only count '(')
        "COLON",  # We count labels through identifers, so don't count again via colons
        "PPHASH",  # Ignore preprocessor tokens
        "PPPRAGMA",
        "PPPRAGMASTR",
    )

    def __cache_metrics(self, metrics) -> None:
        """Caches the provided set of metrics within the class' cache, such that
        any future metric group that wishes to use halstead's metrics in their
        calculations can access these cached values without recomputing them.

        Args:
            metrics (Metrics): The dictionary of metrics to cache.
        """
        HalsteadComplexityUnit.cached = dict(
            x for x in HalsteadComplexityUnit.cached.items()
        )
        for k, v in metrics.items():
            HalsteadComplexityUnit.cached[k] = v

    def __preprocess_contents(self, source: CSource) -> str:
        """Given a CSource object, preprocess its contents by generating its C source
        code using a patched generator.

        Args:
            source (CSource): The CSource source program to preprocess.

        Returns:
            str: The preprocessed contents of the CSource.
        """
        generator = PatchedGenerator()
        contents = generator.visit(source.t_unit)
        return contents

    def __calc_halstead(
        self, lexer: c_lexer.CLexer, source: CSource
    ) -> Tuple[int, int, int, int]:
        """Given a CSource object, calculate the total and distinct nubmers of operator and operand
        tokens respectively, such that Halstead's Complexity Measures can be computed for that
        source C program.

        Args:
            lexer (c_lexer.CLexer): A lexer to use to lex the C program into tokens.
            source (CSource): The C source program to split into operators/operands.

        Returns:
            Tuple[int, int, int, int]: The list of computed base halstead measures. In order these
            are (total operands, total operarators, unique_operands, unique_operators).
        """
        contents = self.__preprocess_contents(source)
        lexer.input(contents)
        token = lexer.token()
        num_operands = 0
        unique_operands = set()  # Distict operand lexemes
        num_operators = 0
        unique_operators = set()  # Distinct operator lexemes
        while token is not None:
            if token.type in self.__operand_toks:
                num_operands += 1
                unique_operands.add(token.value)
            elif token.type not in self.__exclude_toks:
                num_operators += 1
                unique_operators.add(token.value)
            token = lexer.token()
        context_analyzer = HalsteadAnalyzer()
        context_analyzer.visit(source.t_unit)
        num_operands += context_analyzer.operands
        num_operators += context_analyzer.operators
        unique_operands.update(context_analyzer.unique_operands)
        unique_operators.update(context_analyzer.unique_operators)
        return (
            num_operands,
            num_operators,
            len(unique_operands),
            len(unique_operators),
        )

    def calculate_metrics(self, old_source: CSource, new_source: CSource) -> None:
        """Computes and formats the set of Halstead's complexity measure metrics for
        the given programs. This includes the length and estimated length, Halstead
        Volume (V), Difficulty (D) and Effort (E), and the estimated time to program
        and estimated number of delivered bugs in the code.

        Args:
            old_source (CSource): The original C source file before obfuscation.
            new_source (CSource): The final obfuscated C source file.
        """
        # Lex the original and obfuscated programs for their halstead token numbers.
        lexer = c_lexer.CLexer(
            lambda: None, lambda: None, lambda: None, lambda tok: None
        )
        lexer.build()
        result = self.__calc_halstead(lexer, old_source)
        old_operands, old_operators, old_uq_operands, old_uq_operators = result
        result = self.__calc_halstead(lexer, new_source)
        new_operands, new_operators, new_uq_operands, new_uq_operators = result
        old_vocabulary = old_uq_operators + old_uq_operands
        new_vocabulary = new_uq_operators + new_uq_operands
        old_length = old_operators + old_operands
        new_length = new_operators + new_operands

        # Compute Halstead's Complexity Metrics, applying each formula in turn.
        if old_uq_operators != 0 and old_uq_operands != 0:
            old_estim_len = int(
                old_uq_operators * math.log2(old_uq_operators)
                + old_uq_operands * math.log2(old_uq_operands)
            )
        else:
            old_estim_len = "N/A"
        if new_uq_operators != 0 and new_uq_operands != 0:
            new_estim_len = int(
                new_uq_operators * math.log2(new_uq_operators)
                + new_uq_operands * math.log2(new_uq_operands)
            )
        else:
            new_estim_len = "N/A"
        if old_vocabulary not in [0, "N/A"]:
            old_volume = old_length * math.log2(old_vocabulary)
        else:
            old_volume = "N/A"
        if new_vocabulary not in [0, "N/A"]:
            new_volume = new_length * math.log2(new_vocabulary)
            new_volume_str = str(int(new_volume))
        else:
            new_volume = "N/A"
            new_volume_str = "N/A"
        if old_uq_operands != 0:
            old_difficulty = int(
                (old_uq_operators / 2) * (old_operands / old_uq_operands)
            )
        else:
            old_difficulty = "N/A"
        if new_uq_operands != 0:
            new_difficulty = int(
                (new_uq_operators / 2) * (new_operands / new_uq_operands)
            )
        else:
            new_difficulty = "N/A"
        if old_difficulty != "N/A" and old_volume != "N/A":
            old_effort = int(old_difficulty * old_volume)
            old_bugs = int(math.pow(old_effort, (2 / 3)) / 3000)
        else:
            old_effort = "N/A"
            old_bugs = "N/A"
        if new_difficulty != "N/A" and new_volume != "N/A":
            new_effort = int(new_difficulty * new_volume)
            new_timetp = int(new_effort / 18)
            new_bugs = math.pow(new_effort, (2 / 3)) / 3000
            new_bugs_str = "{:.1f}".format(new_bugs)
        else:
            new_effort = "N/A"
            new_timetp = "N/A"
            new_bugs = "N/A"
            new_bugs_str = "N/A"
        self.add_metric(
            "Vocabulary (\u03B7)",
            str(new_vocabulary),
            int_delta(new_vocabulary, old_vocabulary),
        )
        self.add_metric(
            "Length (N)", str(new_length), int_delta(new_length, old_length)
        )
        self.add_metric(
            "Estimated Length (\u004E\u0302)",
            str(new_estim_len),
            int_delta(new_estim_len, old_estim_len),
        )
        self.add_metric("Volume (V)", new_volume_str, int_delta(new_volume, old_volume))
        self.add_metric(
            "Difficulty (D)",
            str(new_difficulty),
            int_delta(new_difficulty, old_difficulty),
        )
        self.add_metric(
            "Effort (E)", str(new_effort), int_delta(new_effort, old_effort)
        )
        self.add_metric("Estimated Time (T)", format_time(new_timetp))
        self.add_metric(
            "Delivered Bugs (B)", new_bugs_str, float_delta(new_bugs, old_bugs)
        )

        # Cache the volume metric for reuse in the maintainability index calculation.
        self.__cache_metrics({"Volume": (new_volume, old_volume)})


class MaintainabilityUnit(CodeMetricUnit):
    """A class for calculating metrics related to the Maintainabiltiy Index measure, which
    is a compound (combined) metric that accounts for the cyclomatic complexity, halstead
    volume, and number of lines of code, using an empirical formula to arrive at a holistic
    view of program complexity and maintainbility."""

    name = "Maintainability Index"
    positions = dict(
        [
            (x, i)
            for (i, x) in enumerate(
                [
                    "Maintainability Index",
                    "Index Rating",
                    "VS Bounded Index",
                    "VS Index Rating",
                ]
            )
        ]
    )
    name_tooltip = (
        "The maintainability index is a compound metric which joins together McCabe's Cyclomatic\n"
        "Complexity, Halstead's Volume and the program's Lines of Code to create a more thorough\n"
        "outlook of the program maintainability (though it is not comprehensive, e.g. not\n"
        "considering variable naming, indentation, etc.). Note that the original metric includes\n"
        "percentage of comments but it has been opted to not include that here as comments will\n"
        "naturally be removed in obfuscated code. Also included is Microsoft Visual Studio's new\n"
        "formula and interpretation that is both bounded and more up-to-date.\n"
        "\nThis metric primarily helps to measure obfuscation resilience and potency (complexity)."
    )
    tooltips = {
        "Maintainability Index": "The maintainability index, calculated using regression models on empirical\n"
        "data. Uses the cyclomatic complexity, Halstead volume and lines of code. Note that\n"
        "this calculation removes the percentage comments metric in the original formula.\n"
        "   Maintainability = 171 - 5.2 x ln(Vol) - 0.23 x CC - 16.2 x ln(LOC)",
        "Index Rating": "A rough guideline/interpretation of the maintainability index, which is either\n"
        "'Unmaintainable', 'Moderate' or 'Maintainable', corresponding to the originally\n"
        "proposed classifications of 'Difficult to Maintain', 'Moderately Maintainable'\n"
        "and 'Highly Maintainable'.",
        "VS Bounded Index": "The Visual Studio bounded version of the maintainability index, such that\n"
        "the index value sits between 0 and 100, and using more conservative thresholds.\n"
        "   Maintainability = MAX(0, (171 - 5.2 x ln(Vol) - 0.23 x CC - 16.2 x ln(LOC)) * 100 / 171)",
        "VS Index Rating": "A rough guideline/interpretation of the VS bounded maintainability index, which\n"
        "is either 'Unmaintainable', 'Moderate', or 'Maintainable' corresponding to Visual\n"
        "Studio's 'Red', 'Yellow' and 'Green' threshold classifications.",
    }
    predecessors = [AggregateUnit, CyclomaticComplexityUnit, HalsteadComplexityUnit]

    def __skip_metrics(self) -> None:
        """Skips calculating of the maintainability index metrics due to the lack
        of availability of required predecessor metrics. Simply adds each metric
        with relevant N/A values in each field.
        """
        for metric in self.positions.keys():
            self.add_metric(metric, "N/A", "N/A")

    def __calc_maintainability_index(self, vol: float, cc: float, loc: int) -> float:
        """Calculates the maintainability index according to the initial formula, which is:
            M = 171 - 5.2 * ln(vol) - 0.23 * cc - 16.2 * ln(loc)

        Args:
            vol (float): The average Halstead Volume of the program (per function + 1)
            cc (float): The average cyclomatic complexity of a function in the program.
            loc (int): The average number of lines of code per function.

        Returns:
            float: The computed maintainability index value.
        """
        return 171 - 5.2 * math.log(vol) - 0.23 * cc - 16.2 * math.log(loc)

    def __calc_vs_maintainability_index(self, vol: float, cc: float, loc: int) -> float:
        """Calculates the Visual Studio updated variant of the maintainability index
        according to their updated, bounded formula, which is:
            M = max(0, (171 - 5.2 * ln(vol) - 0.23 * cc - 16.2 * ln(loc)) * 100 / 171)

        Args:
            vol (float): The average Halstead Volume of the program (per function + 1)
            cc (float): The average cyclomatic complexity of a function in the program.
            loc (int): The average number of lines of code per function.

        Returns:
            float: The computed Visual Studio maintainability index value.
        """
        return max(
            0,
            (171 - 5.2 * math.log(vol) - 0.23 * cc - 16.2 * math.log(loc)) * 100 / 171,
        )

    def __interpet_meaning(self, index: float) -> str:
        """Assigns some qualitative interpretation of the meaning of a maintainability
        index value.

        Args:
            index (float): The calculated maintainability index for a program.

        Returns:
            str: The corresponding interpretation according to the original definitions.
        """
        if index <= 65:
            return "Unmaintainable"
        elif index < 85:
            return "Moderate"
        else:
            return "Maintainable"

    def __interpet_vs_meaning(self, index: float) -> str:
        """Assigns some qualitative interpretation of the meaning of a Visual Studio
        maintainability index value, taking their "Red/Green/Blue" colour interpretation
        and instead assigning the original "Unmaintainable/Moderate/Maintainable" meanings
        to these ranges, to alllow more direct comparisons between the two metrics.

        Args:
            index (float): The calculated Visual Studio maintainability index for a program.

        Returns:
            str: The corresponding interpretation according to the visual studio boundaries,
            and the original definitions.
        """
        if index < 10:
            return "Unmaintainable"
        elif index < 20:
            return "Moderate"
        else:
            return "Maintainable"

    def calculate_metrics(self, old_source: CSource, new_source: CSource) -> None:
        """Computes and formats the set of Maintainability Index code complexity
        measure metrics for the given programs. This includes both the original
        maintainabiliy index and its Visual Studio variant, as well as the qualitative
        interpretations of both metrics.

        Args:
            old_source (CSource): The original C source file before obfuscation.
            new_source (CSource): The final obfuscated C source file.
        """

        # Retrieve previous cached line of code metric calculations
        count_metrics = AggregateUnit.cached
        if "Lines" not in count_metrics or count_metrics["Lines"][0] == "N/A":
            return self.__skip_metrics()
        # Get average lines of code per function
        new_loc, old_loc = count_metrics["Lines"]
        new_func, old_func = count_metrics["Functions"]
        new_func += 1
        old_func += 1
        new_loc /= new_func
        if new_loc == 0:
            new_loc = 1
        old_loc /= old_func
        if old_loc == 0:
            old_loc = 1

        # Retrieve previous cached Cyclomatic Complexiy and Halstead Volume calculations
        cyclomatic_metrics = CyclomaticComplexityUnit.cached
        if (
            "Cyclomatic Complexity" not in cyclomatic_metrics
            or cyclomatic_metrics["Cyclomatic Complexity"][0] == "N/A"
        ):
            return self.__skip_metrics()
        new_cc, old_cc = cyclomatic_metrics["Cyclomatic Complexity"]
        halstead_metrics = HalsteadComplexityUnit.cached
        if "Volume" not in halstead_metrics or halstead_metrics["Volume"][0] == "N/A":
            return self.__skip_metrics()
        new_vol, old_vol = halstead_metrics["Volume"]
        if new_vol != "N/A":
            new_vol /= new_func
        if old_vol != "N/A":
            old_vol /= old_func

        # Calculate and format new maintainbility index metrics
        if (
            old_loc == "N/A"
            or old_cc == "N/A"
            or old_vol == "N/A"
            or old_vol <= 0
            or old_loc <= 0
        ):
            old_maintainability = "N/A"
            old_vs = "N/A"
        else:
            old_maintainability = self.__calc_maintainability_index(
                old_vol, old_cc, old_loc
            )
            old_vs = self.__calc_vs_maintainability_index(old_vol, old_cc, old_loc)
        new_maintainability = self.__calc_maintainability_index(
            new_vol, new_cc, new_loc
        )
        new_vs = self.__calc_vs_maintainability_index(new_vol, new_cc, new_loc)
        self.add_metric(
            "Maintainability Index",
            str(int(new_maintainability)),
            int_delta(new_maintainability, old_maintainability),
        )
        self.add_metric("VS Bounded Index", str(int(new_vs)), int_delta(new_vs, old_vs))
        self.add_metric("Index Rating", self.__interpet_meaning(new_maintainability))
        self.add_metric("VS Index Rating", self.__interpet_vs_meaning(new_vs))
