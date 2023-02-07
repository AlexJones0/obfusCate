""" File: complexity.py
Implements classes and functions for handling input and output. """
from app import settings as config
from .interaction import CSource
from abc import ABC, abstractmethod
from typing import Iterable, Optional, Any
from pycparser.c_ast import *
from pycparser import c_generator, c_lexer


class CodeMetricUnit(ABC):
    """An abstract base class representing some code complexity metric unit, such that
    any implemented code metrics will be subclasses of this class. Implements methods
    for calculating and formatting these complexity metrics given some code. """
    
    name = "CodeMetricUnit"
    positions = {}
    
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
            return [(x, 'N/A') for x in self.positions]
        return sorted(list(self.metrics.items()), 
                      key = lambda x: 
                        self.positions[x[0]]
                        if x[0] in self.positions
                        else len(self.positions))


def int_delta(new: int, prev: int) -> str:
    if new == 'N/A' or prev == 'N/A':
        return 'N/A'
    delta = new - prev
    return ("+" + str(delta)) if delta >= 0 else str(delta)

def float_delta(new: float, prev: float) -> str:
    if new == 'N/A' or prev == 'N/A':
        return 'N/A'
    delta = new - prev
    f_str = "{:.1f}".format(delta)
    return ("+" + f_str) if delta >= 0.0 else f_str


class CountVisitor(NodeVisitor):

    __ident_attrs = ('name', 'declname', 'field',)
    
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
    positions = dict([(x, i) for (i, x) in enumerate([
        "Lines", "Tokens", "Characters", "Functions", "Statements",
        "Stmts/Function", "AST Nodes", "Constants", "Identifiers", 
        "New Identifiers"
    ])])
    
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
        self.add_metric("Identifiers", str(num_new_id), int_delta(num_new_id, num_old_id))
        self.add_metric("New Identifiers", str(len(new_id.difference(old_id))))
        new_stmts, old_stmts = new_counter.stmts, old_counter.stmts
        self.add_metric("Statements", str(new_stmts), int_delta(new_stmts, old_stmts))
        if new_counter.functions != 0:
            new_spf = new_counter.stmts_in_functions / new_counter.functions
        else:
            new_spf = 'N/A'
        if old_counter.functions != 0:
            old_spf = old_counter.stmts_in_functions / old_counter.functions
        else:
            old_spf = 'N/A'
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
            lambda x, y, z: print(x,y,z), lambda: None, lambda: None, lambda tok: None
        )
        lexer.build()
        # Get line counts
        old_contents = old_source.contents
        new_contents = new_source.contents
        old_lines, new_lines = old_contents.count('\n'), new_contents.count('\n')
        self.add_metric("Lines", str(new_lines), int_delta(new_lines, old_lines))
        # Preprocess contents and lex to get token counts
        old_contents = self.preprocess_contents(old_source)
        new_contents = self.preprocess_contents(new_source)
        old_toks = self.get_token_count(lexer, old_contents)
        new_toks = self.get_token_count(lexer, new_contents)
        self.add_metric("Tokens", str(new_toks), int_delta(new_toks, old_toks))
        # Also consider simple character counts
        old_chars, new_chars = len(old_contents), len(new_contents)
        self.add_metric("Characters", str(new_chars), int_delta(new_chars, old_chars))
    
    def calculate_metrics(self, old_source: CSource, new_source: CSource) -> None:
        self.add_AST_metrics(old_source, new_source)
        self.add_lexer_metrics(old_source, new_source)
    
    
class CyclomatricComplexityUnit(CodeMetricUnit):

    name = "McCabe's Cyclomatic Complexity"
    gui_name = "<p style=\"line-height:80%\">McCabe's Cyclomatic<br>Complexity</p>"
    positions = dict([(x, i) for (i, x) in enumerate([
        "Cyclomatic Number (M)", "Cyclomatic Interpretation", 
        "Connected Components (P)", "Nodes (N)", "Edges (E)",
    ])])
    
    def calculate_metrics(self, old_source: CSource, new_source: CSource) -> None:
        pass # TODO
    
    def get_metrics(self) -> Iterable[Any]:
        return super().get_metrics()


class HalsteadComplexityUnit(CodeMetricUnit):

    name = "Halstead Complexity Measures"
    gui_name = "<p style=\"line-height:80%\">Halstead Complexity<br>Measures</p>"
    positions = dict([(x, i) for (i, x) in enumerate([
        "Program vocabulary (\u03B7)", 
        "Program Length (N)", 
        "Estimated Length (\u004E\u0302)", 
        "Volume (V)", 
        "Difficulty (D)",
        "Effort (E)",
        "Time to Program (T)",
        "Delivered Bugs (B)",
    ])])
    
    def calculate_metrics(self, old_source: CSource, new_source: CSource) -> None:
        pass # TODO
    
    def get_metrics(self) -> Iterable[Any]:
        return super().get_metrics()

# TODO add more metrics. Could add:
#   > Multiclass performance metrics for similarity
#       > e.g. Precision, Recall, F-measure (f1-score)
#   > Matching algorithms (strings/function name matching)
#   > Entropy Similarity (Shannon/Behavioural/String)
#   > Cosine / Longest Common Subsequence / Edit / Euclidean / K-L divergence,
#     Hamming Distance, Gaussian Kernel, Distance between n-grams and context
#     (ALL SIMILARY METRICS - DON'T HAVE ANY YET, SO AT LEAST 1 IS GOOD)
#   > Cost (time/space overhead) metrics - kinda only have counts right now
#   > There is more complex potency metrics (nesting complexity, data flow
#     complexity, fan-in/out complexity, etc.) but I do already have three
#     metrics for this.
