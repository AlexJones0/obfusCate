""" File: complexity.py
Implements classes and functions for handling input and output. """
from app import settings as config
from .interaction import CSource
from abc import ABC, abstractmethod
from typing import Iterable, Optional, Tuple, Callable, Any
from pycparser.c_ast import *
from pycparser import c_generator, c_lexer
import statistics
import networkx
import math


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
        self.metrics = {}

    def add_metric(self, name: str, new: str, delta: Optional[str] = None) -> None:
        if delta is None:
            self.metrics[name] = new
        else:
            self.metrics[name] = (new, delta)

    @abstractmethod
    def calculate_metrics(self, old_source: CSource, new_source: CSource) -> None:
        return NotImplemented

    def get_metrics(self) -> Iterable[Any]:
        if len(self.metrics) == 0:
            return [(x, "N/A") for x in self.positions]
        return sorted(
            list(self.metrics.items()),
            key=lambda x: self.positions[x[0]]
            if x[0] in self.positions
            else len(self.positions),
        )


def int_delta(new: int, prev: int) -> str:
    if new == "N/A" or prev == "N/A":
        return "N/A"
    delta = int(new - prev)
    return ("+" + str(delta)) if delta >= 0 else str(delta)


def float_delta(new: float, prev: float) -> str:
    if new == "N/A" or prev == "N/A":
        return "N/A"
    delta = new - prev
    f_str = "{:.1f}".format(delta)
    return ("+" + f_str) if delta >= 0.0 else f_str

def format_time(time: int) -> str:
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


class CountVisitor(NodeVisitor):

    __ident_attrs = (
        "name",
        "declname",
        "field",
    )

    def __init__(self):
        self.__reset()

    def __reset(self):
        self.constants = 0
        self.ast_nodes = 0
        self.functions = 0
        self.stmts = 0
        self.stmts_in_functions = 0
        self.__in_function = False
        self.ident_set = set()

    def record_stmt(self):
        self.stmts += 1
        if self.__in_function:
            self.stmts_in_functions += 1

    def visit_FileAST(self, node):
        self.__reset()
        self.generic_visit(node)

    def visit_Constant(self, node):
        self.constants += 1
        self.generic_visit(node)

    def visit_FuncDef(self, node):
        self.__in_function = True
        self.functions += 1
        self.generic_visit(node)
        self.__in_function = False

    def visit_Compound(self, node):
        if node.block_items is not None:
            for child in node.block_items:
                if not isinstance(child, Compound):
                    self.record_stmt()
        self.generic_visit(node)

    def visit_If(self, node):
        if node.iftrue is not None and not isinstance(node.iftrue, Compound):
            self.record_stmt()
        if node.iffalse is not None and not isinstance(node.iffalse, Compound):
            self.record_stmt()
        self.generic_visit(node)

    def visit_While(self, node):
        if node.stmt is not None and not isinstance(node.stmt, Compound):
            self.record_stmt()
        self.generic_visit(node)

    def visit_DoWhile(self, node):
        if node.stmt is not None and not isinstance(node.stmt, Compound):
            self.record_stmt()
        self.generic_visit(node)

    def visit_For(self, node):
        if node.stmt is not None and not isinstance(node.stmt, Compound):
            self.record_stmt()
        self.generic_visit(node)

    def visit_Switch(self, node):
        if node.stmt is not None and not isinstance(node.stmt, Compound):
            self.record_stmt()
        self.generic_visit(node)

    def visit_Case(self, node):
        if node.stmts is not None and not isinstance(node.stmts, Compound):
            for child in node.stmts:
                if not isinstance(child, Compound):
                    self.record_stmt()
        self.generic_visit(node)

    def visit_Default(self, node):
        if node.stmts is not None and not isinstance(node.stmts, Compound):
            for child in node.stmts:
                if not isinstance(child, Compound):
                    self.record_stmt()
        self.generic_visit(node)

    def visit_Label(self, node):
        if node.stmt is not None and not isinstance(node.stmt, Compound):
            self.record_stmt()
        self.generic_visit(node)

    def generic_visit(self, node):
        self.ast_nodes += 1
        for attr in self.__ident_attrs:
            if not hasattr(node, attr):
                continue
            attr_val = getattr(node, attr)
            if attr_val is None or not isinstance(attr_val, str):
                continue
            self.ident_set.add(attr_val)
        return super(CountVisitor, self).generic_visit(node)


class CountUnit(CodeMetricUnit):

    name = "Counts"
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
    
    def __cache_metrics(self, metrics) -> None:
        CountUnit.cached = metrics

    def add_AST_metrics(self, old_source: CSource, new_source: CSource) -> None:
        old_counter = CountVisitor()
        old_counter.visit(old_source.t_unit)
        new_counter = CountVisitor()
        new_counter.visit(new_source.t_unit)
        new_c, old_c = new_counter.constants, old_counter.constants
        self.add_metric("Constants", str(new_c), int_delta(new_c, old_c))
        new_n, old_n = new_counter.ast_nodes, old_counter.ast_nodes
        self.add_metric("AST Nodes", str(new_n), int_delta(new_n, old_n))
        new_f, old_f = new_counter.functions, old_counter.functions
        self.add_metric("Functions", str(new_f), int_delta(new_f, old_f))
        new_id, old_id = new_counter.ident_set, old_counter.ident_set
        num_new_id, num_old_id = len(new_id), len(old_id)
        self.add_metric(
            "Identifiers", str(num_new_id), int_delta(num_new_id, num_old_id)
        )
        self.add_metric("New Identifiers", str(len(new_id.difference(old_id))))
        new_stmts, old_stmts = new_counter.stmts, old_counter.stmts
        self.add_metric("Statements", str(new_stmts), int_delta(new_stmts, old_stmts))
        if new_counter.functions != 0:
            new_spf = new_counter.stmts_in_functions / new_counter.functions
        else:
            new_spf = "N/A"
        if old_counter.functions != 0:
            old_spf = old_counter.stmts_in_functions / old_counter.functions
        else:
            old_spf = "N/A"
        self.add_metric("Stmts/Function", str(new_spf), float_delta(new_spf, old_spf))

    def preprocess_contents(self, source: CSource) -> str:
        generator = c_generator.CGenerator()
        contents = generator.visit(source.t_unit)
        return contents

    def get_token_count(self, lexer: c_lexer.CLexer, contents: str):
        lexer.input(contents)
        token = lexer.token()
        token_count = 0
        while token is not None:
            token_count += 1
            token = lexer.token()
        return token_count

    def add_lexer_metrics(self, old_source: CSource, new_source: CSource) -> None:
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
        # Also consider simple character counts
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
        self.add_AST_metrics(old_source, new_source)
        self.add_lexer_metrics(old_source, new_source)


class CFGGenerator(NodeVisitor):
    # TODO this is very probably not correct but is it close enough
    # and justifiably close enough?
    
    def __init__(self) -> None:
        super(CFGGenerator, self).__init__()
        self.__reset()

    def __reset(self) -> None:
        self.functions = 0
        self.in_function = False
        self.in_cond = False
        self.cfgraph = dict()
        self.entry_stack = []
        self.exit_stack = []
        self.node_number = 0
        self.graphs = dict()
        self.decisions = 0
        self.myers = 0
        self.func_decisions = dict()
        self.func_myers = dict()
        self.label_blocks = dict()
        self.gotos = dict()
        self.breaks = []
        self.continues = []
        self.escaped = []
        self.levels = 0

    def __add_node(self, node: int) -> None:
        self.cfgraph[node] = set()
    
    def __add_edge(self, from_node: int, to_node: int) -> None:
        self.cfgraph[from_node].add(to_node)
    
    def __new_node(self) -> None:
        new_node = self.node_number
        self.__add_node(new_node)
        self.node_number += 1
        return new_node

    def __set_entry_exit(self, entry: int, exit: int) -> None:
        self.entry_stack.append(entry)
        self.exit_stack.append(exit)
    
    def __pop_entry_exit(self) -> None:
        self.entry_stack = self.entry_stack[:-1]
        self.exit_stack = self.exit_stack[:-1]
    
    def __get_entry_exit(self) -> Tuple[int,int]:
        return (self.entry_stack[-1], self.exit_stack[-1])
        
    def __modify_entry_exit(self, entry: int, exit: int) -> None:
        self.entry_stack[-1] = entry
        self.exit_stack[-1] = exit
        
    def __visit(self, node: Node, entry: int, exit: int, modify: bool = False, escape_link: bool = True) -> None:
        if modify:
            self.__modify_entry_exit(entry, exit)
            if isinstance(node, list):
                for item in node:
                    self.visit(item)
            else:
                self.visit(node)
            new_entry, new_exit = self.__get_entry_exit()
        else:
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
        self.decisions += 1
        self.myers += 1
        was_in_cond = self.in_cond
        self.in_cond = True
        self.visit(cond)
        self.in_cond = was_in_cond

    def __get_labels(self, stmt: Node) -> Tuple[Node, Optional[Label]]:
        label = None
        if isinstance(stmt, Label):
            label = stmt
        while isinstance(stmt, Label):
            stmt = stmt.stmt
        return (stmt, label)

    def visit_If(self, node: If) -> None:
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
        if not self.in_function or self.escaped[-1] or node.block_items is None:
            return self.generic_visit(node)
        entry, exit = self.__get_entry_exit()
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
        #print([len(part) if isinstance(part, list) else 1 for part in block_parts]) # TODO remove when done
        #print([type(part[0]) if isinstance(part, tuple)
        #       else [type(p[0]) for p in part] 
        #       for part in block_parts])
        for part in block_parts:
            if part == block_parts[-1]: # TODO COMEHERE IS ANY OF THIS RIGHT?
                new_node = exit
            else:
                new_node = self.__new_node()
            part_exit = new_node
            is_escape = part == block_parts[-1]
            if isinstance(part, tuple):
                part, label = part
                self.__visit(part if label is None else label, entry, part_exit, modify=True, escape_link=is_escape)
            elif isinstance(part, list):
                part = [p[0] if p[1] is None else p[1] for p in part]
                self.__visit(part, entry, exit, modify=True, escape_link=is_escape) 
                # TODO is exit here right
                if part != block_parts[-1]:
                    self.__add_edge(entry, part_exit)
            entry = part_exit

    def visit_Switch(self, node: Switch) -> None:
        # TODO we make a simple assumption - each case should be one edge
        # Might not 100% hold, need to think about it
        if not self.in_function or self.escaped[-1] or node.stmt is None:
            return self.generic_visit(node)
        # TODO not sure if 100% correct
        entry, exit = self.__get_entry_exit()
        cond_entry = self.__new_node()
        self.__add_edge(entry, cond_entry)
        self.__modify_entry_exit(cond_entry, exit)
        self.breaks.append((self.levels, exit))
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
        is_first_other = True
        new_entry = cond_entry
        for stmt in node.stmt.block_items[::-1]: # TODO is this right? Seems wrong
            if not isinstance(stmt, (Case, Default)):
                if is_first_other: # Must add edge for first non-case/default in switch
                    new_entry = self.__new_node()
                    self.__add_edge(cond_entry, new_entry)
                self.__visit(stmt, new_entry, exit)
        self.breaks = self.breaks[:-1]

    def visit_While(self, node: While) -> None:
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
        if not self.in_function or self.escaped[-1] or node.stmt is None:
            return self.generic_visit(node)
        if node.cond is not None:
            self.__visit_cond(node.cond)
        # TODO some init, cond, next stuff here seems wrong
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
        if not self.in_function or self.escaped[-1] or self.levels == 0:
            return self.generic_visit(node)
        entry, _ = self.__get_entry_exit()
        self.__add_edge(entry, self.continues[-1][1])
        self.escaped[-1] = True

    def visit_Break(self, node: Break) -> None:
        if not self.in_function or self.escaped[-1] or self.levels == 0:
            return self.generic_visit(node)
        entry, _ = self.__get_entry_exit()
        self.__add_edge(entry, self.breaks[-1][1])
        self.escaped[-1] = True

    def visit_Label(self, node: Label) -> None:
        if not self.in_function or self.levels == 0 or node.name is None \
            or node.stmt is None or self.escaped[-1]:
                return self.generic_visit(node)
        entry, exit = self.__get_entry_exit()
        labelled_entry = self.__new_node()
        self.__add_edge(entry, labelled_entry)
        self.label_blocks[node.name] = entry
        self.__visit(node.stmt, labelled_entry, exit, modify=True)

    def visit_Goto(self, node: Goto) -> None:
        if not self.in_function or self.levels == 0 or node.name is None or self.escaped[-1]:
            return self.generic_visit(node)
        entry, _ = self.__get_entry_exit()
        if node.name not in self.gotos:
            self.gotos[node.name] = set()
        self.gotos[node.name].add(entry)
        self.escaped[-1] = True

    def visit_Return(self, node: Return) -> None:
        if not self.in_function or self.escaped[-1] or self.levels == 0:
            return self.generic_visit(node)
        entry, _ = self.__get_entry_exit()
        func_exit = self.exit_stack[0]
        self.__add_edge(entry, func_exit)
        self.escaped[-1] = True

    def visit_BinaryOp(self, node: BinaryOp) -> None:
        if not self.in_function or not self.in_cond or self.escaped[-1]:
            return self.generic_visit(node)
        if node.op is not None and node.op in ["&&", "||", "^"]: 
            # TODO just these ops?
            self.myers += 1
            self.generic_visit(node)
        # Note: we don't consider basic blocks from lazy evaluation

    def visit_FuncDef(self, node: FuncDef) -> None:
        # TODO do I need to record this in any more detail?
        if node.decl is None or node.body is None:
            return self.generic_visit(node)
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
        entry, exit = self.__new_node(), self.__new_node()
        self.__set_entry_exit(entry, exit)
        self.generic_visit(node)
        self.__pop_entry_exit()
        self.func_decisions[node] = self.decisions
        self.func_myers[node] = self.myers
        for label_name, goto_entries in self.gotos.items():
            label_entry = self.label_blocks[label_name]
            for goto_entry in goto_entries:
                self.__add_edge(goto_entry, label_entry)
        # Remove redundant extra exit node for single-block graphs
        if len(self.cfgraph[entry]) == 0 or (len(self.cfgraph[entry]) == 1 and list(self.cfgraph[entry])[0] == exit):
            self.cfgraph = {entry: set()}
            self.graphs[node] = self.cfgraph
        self.levels -= 1
        self.cfgraph = prev_graph
        self.node_number = prev_node_number
        self.in_function = was_in_function


class CyclomaticComplexityUnit(CodeMetricUnit):

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
        "the full control flow graph (minus lazy operations in decision nodes), such that multiply\n"
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
        CyclomaticComplexityUnit.cached = metrics

    def get_edges(self, graph: dict[int,Iterable[int]]) -> int:
        return sum([len(vals) for _, vals in graph.items()])

    def get_interpretation(self, cyclo_num: int) -> str:
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
        if len(old_graphs) != 0:
            old_total_nodes = sum(old_nodes)
            old_avg_nodes = old_total_nodes / len(old_nodes)
            old_total_edges = sum(old_edges)
            old_avg_edges = old_total_edges / len(old_edges)
        else:
            old_total_nodes = 0
            old_avg_edges = 'N/A'
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
            node_new = 'N/A'
            new_total_edges = 0
            edge_new = 'N/A'
        if len(old_graphs) == 0 or len(new_graphs) == 0:
            node_delta = 'N/A'
            edge_delta = 'N/A'
        else:
            node_delta = float_delta(new_avg_nodes, old_avg_nodes)
            edge_delta = float_delta(new_avg_edges, old_avg_edges)
        self.add_metric("Avg. Nodes (N\u0305)", node_new, node_delta)
        self.add_metric("Total Nodes (\u03A3N)", str(new_total_nodes), 
                        int_delta(new_total_nodes, old_total_nodes))
        self.add_metric("Avg. Edges (E\u0305)", edge_new, edge_delta)
        self.add_metric("Total Edges (\u03A3E)", str(new_total_edges),
                        int_delta(new_total_edges, old_total_edges))
        old_cyclo_numbers = []
        for i in range(len(old_graphs)):
            cyclo_num = old_edges[i] - old_nodes[i] + 2
            old_cyclo_numbers.append(cyclo_num)
        total_old_cyclo = sum(old_cyclo_numbers)
        if len(old_graphs) != 0:
            avg_old_cyclo = total_old_cyclo / len(old_graphs)
        else: # TODO is this even needed?
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
            avg_cyclo_delta = "N/A"
        self.add_metric("Total Cyclomatic \u03A3M", str(total_new_cyclo),
                        int_delta(total_new_cyclo, total_old_cyclo))
        self.add_metric("Avg. Cyclomatic M\u0305", avg_new_cyclo_str,
                        avg_cyclo_delta)
        self.add_metric("Rating", self.get_interpretation(avg_new_cyclo))
        self.add_metric("Source Rating", self.get_interpretation(avg_old_cyclo))
        old_orig_values = old_cfg_generator.func_decisions.values()
        new_orig_values = new_cfg_generator.func_decisions.values()
        total_old_orig_values = sum(old_orig_values)
        total_new_orig_values = sum(new_orig_values)
        avg_old_orig_values = total_old_orig_values / len(old_orig_values)
        avg_new_orig_values = total_new_orig_values / len(new_orig_values)
        self.add_metric("Total Orig. \u03A3M", str(total_new_orig_values),
                        int_delta(total_new_orig_values, total_old_orig_values))
        self.add_metric("Avg. Orig. M\u0305", "{:.1f}".format(avg_new_orig_values),
                        float_delta(avg_new_orig_values, avg_old_orig_values))
        self.add_metric("Orig. Rating", 
                        self.get_interpretation(avg_new_orig_values))
        self.add_metric("Orig. Source Rating", 
                        self.get_interpretation(avg_old_orig_values))
        old_myers = old_cfg_generator.func_myers.values()
        new_myers = new_cfg_generator.func_myers.values()
        total_old_myers = sum(old_myers)
        total_new_myers = sum(new_myers)
        avg_old_myers = total_old_myers / len(old_myers)
        avg_new_myers = total_new_myers / len(new_myers)
        self.add_metric("Avg. Myers' Interval", str(avg_new_myers), "{}".format(
            float_delta(avg_new_myers, avg_old_myers)
        ))
        self.add_metric("Total Myers' Interval", str(total_new_myers), "{}".format(
            int_delta(total_new_myers, total_old_myers)
        ))
        self.__cache_metrics({"Cyclomatic Complexity": (avg_new_orig_values, avg_old_orig_values)})


class CognitiveAnalyzer(NodeVisitor):
    
    def __init__(self) -> None:
        super(CognitiveAnalyzer, self).__init__()
        self.__reset()

    def __reset(self) -> None:
        self.current_function = None
        self.cognitive = 0
        self.max_nesting = 0
        self.func_nestings = dict()
        self.func_cognitives = dict()
        self.call_graph = dict() # To detect direct/indirect recursion
        self.logical_op_seq = (None, 0) # To detect sequences (chains) of logical binary ops
    
    def __find_recursion_cycles(self) -> None:
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
        self.generic_visit(node)
        self.__find_recursion_cycles()
    
    def visit_FuncDef(self, node: FuncDef) -> None:
        if node.decl is None or node.decl.name is None or node.body is None:
            return self.visit(node)
        prev_function = self.current_function
        self.current_function = node.decl.name
        self.call_graph[node.decl.name] = set()
        self.cognitive = 0
        self.nesting = 0
        self.max_nesting = 0
        self.generic_visit(node)
        self.func_cognitives[node] = self.cognitive
        self.func_nestings[node] = self.max_nesting
        self.current_function = prev_function
    
    def visit_FuncCall(self, node: FuncCall) -> None:
        if self.current_function is None or node.name is None or node.name.name is None:
            return self.generic_visit(node)
        name = node.name.name
        reached_set = self.call_graph[self.current_function]
        if name not in reached_set and name in self.call_graph:
            reached_set.add(name)
        self.generic_visit(node)
    
    def visit_BinaryOp(self, node: BinaryOp) -> None:
        if self.current_function is None or node.op is None or node.op not in ["^", "&&", "||"]:
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
            if not isinstance(node.left, BinaryOp) and not isinstance(node.right, BinaryOp):
                # End of sequence, so add the current sequence
                self.cognitive += 1
        self.generic_visit(node)
    
    def generic_visit(self, node: Node) -> None:
        if self.current_function is None:
            return super(CognitiveAnalyzer, self).generic_visit(node)
        # A personal special separate case for C - a compound within a compound, 
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
            if isinstance(node, If) and node.iffalse is not None and not isinstance(node.iffalse, If):
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
    # TODO could do a personal c extension where I propose additional
    # cognitive load on pointer referencing/dereferencing etc.?

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
        old_analyzer = CognitiveAnalyzer()
        new_analyzer = CognitiveAnalyzer()
        old_analyzer.visit(old_source.t_unit)
        new_analyzer.visit(new_source.t_unit)
        old_cognitive = old_analyzer.func_cognitives.values()
        new_cognitive = new_analyzer.func_cognitives.values()
        total_old_cognitive = sum(old_cognitive)
        total_new_cognitive = sum(new_cognitive)
        self.add_metric("Total Cognitive Num", str(total_new_cognitive),
                        int_delta(total_new_cognitive, total_old_cognitive))
        avg_old_cognitive = total_old_cognitive / len(old_cognitive)
        avg_new_cognitive = total_new_cognitive / len(new_cognitive)
        self.add_metric("Avg. Cognitive Num", "{:.1f}".format(avg_new_cognitive),
                        float_delta(avg_new_cognitive, avg_old_cognitive))
        max_new_cognitive = max(new_cognitive)
        self.add_metric("Max Cognitive Num", str(max_new_cognitive),
                        int_delta(max_new_cognitive, max(old_cognitive)))
        if len(old_cognitive) >= 2:
            sd_old_cognitive = math.sqrt(statistics.variance(old_cognitive, avg_old_cognitive))
        else:
            sd_old_cognitive = 'N/A'
        if len(new_cognitive) >= 2:
            sd_new_cognitive = math.sqrt(statistics.variance(new_cognitive, avg_new_cognitive))
            sd_new_cognitive_str = "{:.1f}".format(sd_new_cognitive)
        else:
            sd_new_cognitive = 'N/A'
            sd_new_cognitive_str = 'N/A'
        self.add_metric("Cognitive SD", sd_new_cognitive_str,
                        float_delta(sd_new_cognitive, sd_old_cognitive))
        old_nesting = old_analyzer.func_nestings.values()
        new_nesting = new_analyzer.func_nestings.values()
        avg_old_nesting = sum(old_nesting) / len(old_nesting)
        avg_new_nesting = sum(new_nesting) / len(new_nesting)
        self.add_metric("Avg. Nesting Depth", "{:.1f}".format(avg_new_nesting),
                        float_delta(avg_new_nesting, avg_old_nesting))
        max_new_nesting = max(new_nesting)
        self.add_metric("Max Nesting Depth", str(max_new_nesting),
                        int_delta(max_new_nesting, max(old_nesting)))
        if len(old_nesting) >= 2:
            sd_old_nesting = math.sqrt(statistics.variance(old_nesting, avg_old_nesting))
        else:
            sd_old_nesting = 'N/A'
        if len(new_nesting) >= 2:
            sd_new_nesting = math.sqrt(statistics.variance(new_nesting, avg_new_nesting))
            sd_new_nesting_str = "{:.1f}".format(sd_new_nesting)
        else:
            sd_new_nesting = 'N/A'
            sd_new_nesting_str = 'N/A'
        self.add_metric("Nesting SD", sd_new_nesting_str,
                        float_delta(sd_new_nesting, sd_old_nesting))


class HalsteadAnalyzer(NodeVisitor):
    
    def __init__(self) -> None:
        self.__reset()

    def __reset(self) -> None:
        self.operands = 0
        self.unique_operands = set()
        self.operators = 0
        self.unique_operators = set()
    
    def __add_operand(self, operand: str) -> None:
        self.operands += 1
        self.unique_operands.add(operand)
        
    def __add_operator(self, operator: str) -> None:
        self.operators += 1
        self.unique_operators.add(operator)
    
    def visit_FuncDef(self, node: FuncDef) -> None:
        if node.decl is not None and node.decl.name is not None:
            self.__add_operator(node.decl.name)
        if node.param_decls is not None:
            self.visit(node.param_decls)
        if node.body is not None:
            self.visit(node.body)
    
    def visit_FuncCall(self, node: FuncCall) -> None:
        if node.name is not None and node.name.name is not None:
            self.__add_operator(node.name.name)
        if node.args is not None:
            self.visit(node.args)
    
    def visit_Decl(self, node: Decl) -> None:
        if node.name is not None:
            self.__add_operand(node.name)
        self.generic_visit(node)
    
    def visit_Enum(self, node: Enum) -> None:
        if node.name is not None:
            self.__add_operand(node.name)
        self.generic_visit(node)
    
    def visit_Struct(self, node: Struct) -> None:
        if node.name is not None:
            self.__add_operand(node.name)
        self.generic_visit(node)
    
    def visit_Union(self, node: Union) -> None:
        if node.name is not None:
            self.__add_operand(node.name)
        self.generic_visit(node)
    
    def visit_ID(self, node: ID) -> None:
        if node.name is not None:
            self.__add_operand(node.name)
        self.generic_visit(node)


class HalsteadComplexityUnit(CodeMetricUnit):

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
        "lexing (e.g. \"int a, b, c;\" to \"int a; int b; int c;\").\n"
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
        'CHAR',
        'CONST',
        'TYPEID', # TODO check this one
        'INT_CONST_DEC',
        'INT_CONST_OCT',
        'INT_CONST_OCT',
        'INT_CONST_HEX',
        'INT_CONST_BIN',
        'INT_CONST_CHAR',
        'FLOAT_CONST',
        'HEX_FLOAT_CONST',
        'CHAR_CONST',
        'WCHAR_CONST',
        'U8CHAR_CONST',
        'U16CHAR_CONST',
        'U32CHAR_CONST',
        'STRING_LITERAL',
        'WSTRING_LITERAL',
        'U8STRING_LITERAL',
        'U16STRING_LITERAL',
        'U32STRING_LITERAL',
        'ELLIPSIS', # TODO I have no idea where this one would go actually
        
    )
    __exclude_toks = (
        'ID',       # IDs are a case by case basis: variables are operands, but
                    #     function names are operators
        'RBRACKET', # For indexing, only count once (so only count '[')
        'RBRACE',   # Same as above - compounds only count once (so only count '{')
        'RPAREN',   # Same as above - parentheses only count once (so only count '(')
        'COLON',    # We count labels through identifers, so don't count again via colons 
        'PPHASH',   # Ignore preprocessor tokens
        'PPPRAGMA',
        'PPPRAGMASTR',
    )
    
    def __cache_metrics(self, metrics) -> None:
        HalsteadComplexityUnit.cached = metrics

    def __preprocess_contents(self, source: CSource) -> str:
        generator = c_generator.CGenerator()
        contents = generator.visit(source.t_unit)
        return contents

    def __calc_halstead(self, lexer: c_lexer.CLexer, source: CSource) -> Tuple[int, int, int, int]:
        contents = self.__preprocess_contents(source)
        lexer.input(contents)
        token = lexer.token()
        num_operands = 0
        unique_operands = set() # Distict operand lexemes
        num_operators = 0
        unique_operators = set() # Distinct operator lexemes
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
        return (num_operands, num_operators, len(unique_operands), len(unique_operators))

    def calculate_metrics(self, old_source: CSource, new_source: CSource) -> None:
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
        if old_uq_operators != 0:
            old_estim_len = int(
                old_uq_operators * math.log2(old_uq_operators)
                + old_uq_operands * math.log2(old_uq_operands)
            )
        else:
            old_estim_len = 'N/A'
        if new_uq_operators != 0:
            new_estim_len = int(
                new_uq_operators * math.log2(new_uq_operators)
                + new_uq_operands * math.log2(new_uq_operands)
            )
        else:
            new_estim_len = 'N/A'
        if old_vocabulary != 0:
            old_volume = old_length * math.log2(old_vocabulary)
        else:
            old_volume = 'N/A'
        if new_vocabulary != 0:
            new_volume = new_length * math.log2(new_vocabulary)
        else:
            new_volume = 'N/A'
        if old_uq_operands != 0:
            old_difficulty = (old_uq_operators / 2) * (old_operands / old_uq_operands)
        else:
            old_difficulty = 'N/A'
        if new_uq_operands != 0:
            new_difficulty = (new_uq_operators / 2) * (new_operands / new_uq_operands)
        else:
            new_difficulty = 'N/A'
        if old_difficulty != 'N/A' and old_volume != 'N/A':
            old_effort = int(old_difficulty * old_volume)
            old_bugs = math.pow(old_effort, (2 / 3)) / 3000
        else:
            old_effort = 'N/A'
            old_bugs = 'N/A'
        if new_difficulty != 'N/A' and new_volume != 'N/A':
            new_effort = int(new_difficulty * new_volume)
            new_timetp = int(new_effort / 18)
            new_bugs = math.pow(new_effort, (2 / 3)) / 3000
        else:
            new_effort = 'N/A'
            new_timetp = 'N/A'
            new_bugs = 'N/A'
        self.add_metric("Vocabulary (\u03B7)", str(new_vocabulary),
                        int_delta(new_vocabulary, old_vocabulary))
        self.add_metric("Length (N)", str(new_length),
                        int_delta(new_length, old_length))
        self.add_metric("Estimated Length (\u004E\u0302)", str(new_estim_len),
                        int_delta(new_estim_len, old_estim_len))
        self.add_metric("Volume (V)", str(int(new_volume)), 
                        int_delta(int(new_volume), int(old_volume)))
        self.add_metric("Difficulty (D)", str(int(new_difficulty)),
                        int_delta(int(new_difficulty), int(old_difficulty)))
        self.add_metric("Effort (E)", str(int(new_effort)), 
                        int_delta(new_effort, old_effort))
        self.add_metric("Estimated Time (T)", format_time(new_timetp))
        self.add_metric("Delivered Bugs (B)", "{:.1f}".format(new_bugs),
                        float_delta(new_bugs, old_bugs))
        self.__cache_metrics({"Volume": (new_volume, old_volume)})


class MaintainabilityUnit(CodeMetricUnit):

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
    predecessors = [CountUnit, CyclomaticComplexityUnit, HalsteadComplexityUnit]

    def __skip_metrics(self) -> None:
        for metric in self.positions.keys():
            self.add_metric(metric, 'N/A', 'N/A')

    def __calc_maintainability_index(self, vol: float, cc: float, loc: int) -> float:
        return 171 - 5.2 * math.log(vol) - 0.23 * cc - 16.2 * math.log(loc)
    
    def __calc_vs_maintainability_index(self, vol: float, cc: float, loc: int) -> float:
        return max(0, (171 - 5.2 * math.log(vol) - 0.23 * cc - 16.2 * math.log(loc)) * 100 / 171)

    def __interpet_meaning(self, index: float) -> str:
        if index <= 65:
            return "Unmaintainable"
        elif index < 85:
            return "Moderate"
        else:
            return "Maintainable"
    
    def __interpet_vs_meaning(self, index: float) -> str:
        if index < 10:
            return "Unmaintainable"
        elif index < 20:
            return "Moderate"
        else:
            return "Maintainable"
        

    def calculate_metrics(self, old_source: CSource, new_source: CSource) -> None:
        # Retrieve previous cached metric calculations
        count_metrics = CountUnit.cached
        if "Lines" not in count_metrics or count_metrics["Lines"][0] == 'N/A':
            return self.__skip_metrics()
        new_loc, old_loc = count_metrics["Lines"]
        cyclomatic_metrics = CyclomaticComplexityUnit.cached
        if "Cyclomatic Complexity" not in cyclomatic_metrics or \
            cyclomatic_metrics["Cyclomatic Complexity"][0] == 'N/A':
                return self.__skip_metrics()
        new_cc, old_cc = cyclomatic_metrics["Cyclomatic Complexity"]
        halstead_metrics = HalsteadComplexityUnit.cached
        if "Volume" not in halstead_metrics or halstead_metrics["Volume"][0] == 'N/A':
            return self.__skip_metrics()
        new_vol, old_vol = halstead_metrics["Volume"]
        # Calculate new metrics
        if old_loc == 'N/A' or old_cc == 'N/A' or old_vol == 'N/A' or old_vol <= 0 or old_loc <= 0:
            old_maintainability = 'N/A'
            old_vs = 'N/A'
        else:
            old_maintainability = self.__calc_maintainability_index(old_vol, old_cc, old_loc)
            old_vs = self.__calc_vs_maintainability_index(old_vol, old_cc, old_loc)
        new_maintainability = self.__calc_maintainability_index(new_vol, new_cc, new_loc)
        new_vs = self.__calc_vs_maintainability_index(new_vol, new_cc, new_loc)
        # Add (and format) new metrics
        self.add_metric("Maintainability Index", str(int(new_maintainability)),
                        int_delta(new_maintainability, old_maintainability))
        self.add_metric("VS Bounded Index", str(int(new_vs)), int_delta(new_vs, old_vs))
        self.add_metric("Index Rating", self.__interpet_meaning(new_maintainability))
        self.add_metric("VS Index Rating", self.__interpet_vs_meaning(new_vs))
        


# TODO one more metric here - probably Gaussian Kernel / K-L divergence / distance between n-grams and context


# TODO add more metrics. Could add:
#   > Multiclass performance metrics for similarity
#       > e.g. Precision, Recall, F-measure (f1-score)
#   > Cognitive Complexity Metric
#   > Matching algorithms (strings/function name matching)
#   > Entropy Similarity (Shannon/Behavioural/String)
#   > Cosine / Longest Common Subsequence / Edit / Euclidean / K-L divergence,
#     Hamming Distance, Gaussian Kernel, Distance between n-grams and context
#     (ALL SIMILARY METRICS - DON'T HAVE ANY YET, SO AT LEAST 1 IS GOOD)
#   > Cost (time/space overhead) metrics - kinda only have counts right now
#   > There is more complex potency metrics (nesting complexity, data flow
#     complexity, fan-in/out complexity, etc.) but I do already have three
#     metrics for this.
