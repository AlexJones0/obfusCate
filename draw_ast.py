# Imports
import graphviz
import html
import argparse
from pycparser import parse_file, c_ast
from dot2tex import dot2tex
import math

# Parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument('file', help='C source file')
parser.add_argument('output', help='Output file name')
parser.add_argument('--tikz', action='store_true', help='Output to TikZ format in .tex file')
parser.add_argument('--edgeLabels', action='store_true', help="Label edges with their attribute names.")
args = parser.parse_args()

# Get the file name argument
file_name = args.file

# Get the output name argument
if args.output is not None:
    output_name = args.output
else:
    output_name = "ast"

# Parse a C file
ast = parse_file(file_name,
                 use_cpp=True,
                 cpp_path="clang",
                 cpp_args=["-E", r"-Iutils/fake_libc_include"])
i = -1
for i, c in enumerate(ast.ext):
    if not isinstance(c, c_ast.Typedef):
        break
ast.ext = ast.ext[i:]

# Function for checking if something is an empty list or empty tuple
is_empty_iterable = lambda x: isinstance(x, (list, tuple)) and len(x) == 0

# Define a function to format an attribute of an AST node using HTML
def format_attribute(attr, val):
    if isinstance(val, (list, tuple)):
        val = [str(x) for x in val]
        val = ",".join(val)
    return f'<br/><font point-size="11" color="#555555">{html.escape(attr)}: {html.escape(val)}</font>'

def tex_format_attribute(attr, val):
    if isinstance(val, (list, tuple)):
        val = [str(x) for x in val]
        val = ",".join(val)
    replace_chars = ["_", "&", "#", "&", "[", "]", "{", "}", "^", "%", "\\"]
    for char in replace_chars:
        attr = attr.replace(char, "\\" + char)
        val = val.replace(char, "\\" + char)
    attr = attr.replace("\\n", "\\\\n").replace("\\r", "\\\\r")
    val = val.replace("\\n", "\\\\n").replace("\\r", "\\\\r")
    return '\\\\\\\\{{\\small \\textcolor{{gray}}{{{attr}: {val}}}}}'.format(attr=attr, val=val)

def format_label(node, extra):
    return f'<{node.__class__.__name__}{extra}>'

def tex_format_label(node, extra):
    return f'{node.__class__.__name__}{extra}'

# Define a function to recursively traverse the AST
def traverse_ast(node, dot, format_func=format_attribute, label_func=format_label):
    # Collect attributes for different types of node
    extra = ""
    if isinstance(node, (c_ast.ID, c_ast.Enum, c_ast.Enumerator, c_ast.Goto, c_ast.Label,
                         c_ast.Struct, c_ast.Union)):
        if node.name is not None:
            extra += format_func("name", node.name)
    elif isinstance(node, (c_ast.UnaryOp, c_ast.BinaryOp)):
        if node.op is not None:
            extra += format_func("op", node.op)
    elif isinstance(node, c_ast.Constant):
        if node.type is not None:
            extra += format_func("type", node.type)
        if node.value is not None:
            extra += format_func("value", node.value)
    elif isinstance(node, c_ast.IdentifierType):
        if node.names is not None and not is_empty_iterable(node.names):
            extra += format_func("name", ".".join(node.names))
    elif isinstance(node, c_ast.Decl):
        if node.name is not None:
            extra += format_func("name", node.name)
        if node.quals is not None and not is_empty_iterable(node.quals):
            extra += format_func("quals", node.quals)
        if node.align is not None and not is_empty_iterable(node.align):
            extra += format_func("align", node.align)
        if node.storage is not None and not is_empty_iterable(node.storage):
            extra += format_func("storage", node.storage)
        if node.funcspec is not None and not is_empty_iterable(node.funcspec):
            extra += format_func("funcspec", node.funcspec)
    elif isinstance(node, c_ast.ArrayDecl):
        if node.dim_quals is not None and not is_empty_iterable(node.dim_quals):
            extra += format_func("dim_quals", node.dim_quals)
    elif isinstance(node, c_ast.PtrDecl):
        if node.quals is not None and not is_empty_iterable(node.quals):
            extra += format_func("quals", node.quals)
    elif isinstance(node, c_ast.StructRef):
        if node.type is not None:
            extra += format_func("type", node.type)
    elif isinstance(node, c_ast.TypeDecl):
        if node.declname is not None:
            extra += format_func("declname", node.declname)
        if node.quals is not None and not is_empty_iterable(node.quals):
            extra += format_func("quals", node.quals)
        if node.align is not None and not is_empty_iterable(node.align):
            extra += format_func("align", node.align)
    elif isinstance(node, c_ast.Typedef):
        if node.name is not None:
            extra += format_func("name", node.name)
        if node.quals is not None and not is_empty_iterable(node.quals):
            extra += format_func("quals", node.quals)
        if node.storage is not None and not is_empty_iterable(node.storage):
            extra += format_func("storage", node.storage)
    elif isinstance(node, c_ast.Typename):
        if node.name is not None:
            extra += format_func("name", node.name)
        if node.quals is not None and not is_empty_iterable(node.quals):
            extra += format_func("quals", node.quals)
        if node.align is not None and not is_empty_iterable(node.align):
            extra += format_func("align", node.align)
    elif isinstance(node, c_ast.Pragma):
        if node.string is not None:
            extra += format_func("string", node.string)
    # Format the node label and create the node
    label = label_func(node, extra)
    dot.node(str(id(node)), label=label, shape='box',style='rounded,filled', fillcolor='#FFFFFF')
    # Recursively traverse the children of the current node
    children = [c for c in list(node.children()) if isinstance(c[1], c_ast.Node)]
    for i, (child_name, child) in enumerate(children):
        traverse_ast(child, dot, format_func=format_func, label_func=label_func)
        if args.edgeLabels:
            if (i + 1) <= (len(children) // 2) or len(children) == 1:
                # Left-facing edges
                angle = "-25.0"
                distance = "1"
                lpadding = ""
                rpadding = " " * (math.ceil(1.7 * len(child_name)))
            elif i == (len(children) // 2) and (len(children) % 2) != 0:
                # Middle edge (for odd numbers of children)
                angle = "0.0"
                distance = "1"
                lpadding = " " * (math.ceil(1.7 * len(child_name)))
                rpadding = ""
            else:
                # Right-facing edges
                angle = "25.0"
                distance = "1"
                lpadding = " " * (math.ceil(1.7 * len(child_name)))
                rpadding = ""
            dot.edge(str(id(node)), str(id(child)), taillabel=(lpadding + child_name + rpadding),
                        fontsize='10', labeldistance=distance, labelangle=angle, fontcolor='#666666')
        else:
            dot.edge(str(id(node)), str(id(child)))

# Create a Graphviz graph
dot = graphviz.Graph(comment='AST')
# Traverse the AST and add nodes and edges to the graph
traverse_ast(ast, dot)

# Save the graph to a PDF file
dot.engine = 'dot'
dot.attr(rankdir='TB', ranksep="0.3", nodesep="0.125", margin="0", dpi="50")
dot.render(output_name, view=True)

if args.tikz:
    # Save the graph in tikz format
    dot = graphviz.Graph(comment='AST')
    traverse_ast(ast, dot, format_func=tex_format_attribute, label_func=tex_format_label)
    tikz = dot2tex(dot.source, format='tikz', codeonly=True, texmode="raw")
    tikz = tikz.replace(",rounded,filled]","]")
    with open(f'{output_name}.tex', 'w') as f:
        f.write(tikz)