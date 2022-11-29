from app.io import CSource
import sys


def test_random_testing_to_delete():
    source = CSource(sys.argv[1])

    from pycparser.c_ast import NodeVisitor, StaticAssert
    from pycparser import c_generator
    from random import choices as randchoice, randint
    from string import ascii_letters, digits as ascii_digits

    class StringEncodeTraverser(NodeVisitor):
        """Traverses the program AST looking for string literals and encoding them into
        some incomprehensible form."""
        
        def __init__(self):
            pass
        
        def visit_Constant(self, node):
            if node.type == "string":
                print(node.value)
            NodeVisitor.generic_visit(self, node)

    StringEncodeTraverser().visit(source.t_unit)
    source.t_unit.show()
    return
    v = IdentifierTraverser()
    v.visit(source.t_unit)
    new_contents = ""
    generator = c_generator.CGenerator()
    for line in open(source.fpath, "r"):
        if line.strip().startswith("#"):
            new_contents += line + "\n"
    new_contents += generator.visit(source.t_unit)
    newSource = CSource(source.fpath, new_contents, source.t_unit)
    print("NEW CONTENTS:")
    print(newSource.contents)
    # newSource.t_unit.show()


test_random_testing_to_delete()

"""from pycparser import parse_file, c_generator, c_ast

class IdentVisitor(c_ast.NodeVisitor):
    
    def __init__(self, filename):
        self.fname = filename
    def visit_TypeDecl(self, node):
        print("".join(node.type.names), node.declname, node.coord)


fname = ".\\tests\\data\\fibonacci_recursive.c"
ast = parse_file(fname, use_cpp=True, cpp_path='clang', cpp_args=['-E', r'-Iutils/fake_libc_include'])
lastf = fname.split("\\")[-1]
ast.ext = [x for x in ast.ext if lastf in x.coord.file]
ast.show(showcoord=True)
v = IdentVisitor(fname.split("\\")[-1])
v.visit(ast)
#ast.show(showcoord=True)
#generator = c_generator.CGenerator()
#for line in open(fname, "r"):
#    if line.strip().startswith("#"):
#        print(line)
#print(generator.visit(ast))"""
