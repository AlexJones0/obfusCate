""" File: obfuscation/utils.py
Implements abstract base classes and basic functions for implementing
obfuscation methods as ObfuscationUnit subclasses. Offers useful generic 
utilities including tools for AST caching and object retrieval, as well
as the generation of C code from ASTs.
"""
from .. import interaction
from ..debug import *
from pycparser.c_ast import *
from pycparser.c_lexer import CLexer
from typing import Optional, Tuple, Type, Any, Iterable
import abc, enum, json, string, copy


class NameSpace(enum.Enum):
    """ An Enum repersenting the four different identifier namespaces in C. """
    LABEL = 0
    TAG = 1
    MEMBER = 2
    ORDINARY = 3


class TransformType(enum.Enum):
    """An Enum expressing the different types/categories of obfuscation transformations that
    are implemented by the program. This is used to generate the GUI display appropriately."""

    LEXICAL = 1
    ENCODING = 2
    PROCEDURAL = 3
    STRUCTURAL = 4


class ObfuscationUnit(abc.ABC):
    """An abstract base class representing some obfuscation transformation unit, such that
    any implemented transformations will be subclasses of this class. Implements methods
    for transformations, constructing the class (in a CLI), and string representation."""

    name = "ObfuscationUnit"
    description = "An abstract class representing some obfuscation transformation unit. Not yet implemented."
    extended_description = (
        """A longer description about the class, providing extended information about its use.\n"""
        """If you are seeing this generic template then this has not yet been filled in."""
    )
    type = TransformType.LEXICAL

    @abc.abstractmethod
    def transform(self, source: interaction.CSource) -> interaction.CSource | None:
        """Perform the obfuscation transform on the given C source file, returning a new
        CSource corresponding to the obfuscated program.

        Args:
            source (interaction.CSource): The C source program to obfuscate.

        Returns:
            interaction.CSource | None: The obfuscated C Source program, or None if some 
            error occurs. """
        return NotImplemented

    @abc.abstractmethod
    def to_json(self) -> str:
        """
        Returns:
            str: A JSON string representation of the obfuscation unit. """
        return json.dumps({"transformation": "ObfuscationUnit"})

    @abc.abstractmethod
    def from_json(json_str: str) -> Optional["ObfuscationUnit"]:
        """
        Returns:
            ObfuscationUnit | None: The obfuscation transformation unit represented by
            the given JSON string, or None if the string is not valid. """
        return NotImplemented

    @abc.abstractmethod
    def __str__(self) -> str:
        """
        Returns:
            str: A human-readable string representation of the object. """
        return "ObfuscationUnit()"


class IdentityUnit(ObfuscationUnit):
    """Implements an identity transformation, which takes the input source code and does
    nothing to it, returning it unmodified."""

    name = "Identity"
    description = "Does nothing - returns the same code entered."
    extended_description = (
        """The identity transformation is the simplest type of transform, returning \n"""
        """The exact same code that was entered. This is a simple example of a transform\n"""
        """that can be used without worrying about what might change. """
    )
    type = TransformType.LEXICAL

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        """Performs the identity transformation on the source.

        Args:
            source (interaction.CSource): The source code to transform.

        Returns:
            interaction.CSource: The transformed source code.
        """
        return source

    def to_json(self) -> str:
        """Converts the identity unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps({"type": str(__class__.name)})

    def from_json(json_str: str) -> Optional["IdentityUnit"]:
        """Converts the provided JSON string to an identity unit transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding Identity Unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log("Failed to load Identity() - invalid JSON provided.", print_err=True)
            return None
        if "type" not in json_obj:
            log("Failed to load Identity() - no type provided.", print_err=True)
            return None
        elif json_obj["type"] != __class__.name:
            log("Failed to load Identity() - class/type mismatch.", print_err=True)
            return None
        return IdentityUnit()

    def __str__(self):
        return "Identity()"


class ObjectFinder(NodeVisitor):
    """ A class for finding all of the instances of a certain class (or of multiple
    classes) within an Abstract Syntax Tree. It not only finds ocurrences but also 
    stores the parent classes and the attribute that each node is stored under,
    allowing easier manipulation of the abstract syntax tree. """
    
    def __init__(self, classes: list[Type] | Type, attrs: list[str]):
        """The constructor for the ObjectFinder.

        Args:
            classes (list[Type] | Type): The class(es) to search for.
            attrs (list[str]): The list of attributes to check the nullity of. 
            Only objects with non-null values in all such attributes are retrieved. """
        super(ObjectFinder, self).__init__()
        if isinstance(classes, (list, tuple, dict, set)):
            self.classes = tuple(classes)
        else:
            self.classes = classes
        self.none_checks = attrs
        self.reset()

    def reset(self) -> None:
        """Resets the state of the ObjectFinder, allowing it to be re-used for another AST. """
        self.objs = set()
        self.parents = {}
        self.attrs = {}
        self.parent = None
        self.attr = None

    def generic_visit(self, node: Node) -> None:
        """ Visits a generic AST node, checking its class and attributes to determine whether
        it is an object that is being looked for. If so, it is recorded alongside its parent
        and the attribute of its parent that it is stored under, to allow easy manipulation
        of the objects.

        Args:
            node (Node): The node to be checked.
        """
        if isinstance(node, self.classes):
            if all(getattr(node, attr) is not None for attr in self.none_checks):
                self.objs.add(node)
                self.parents[node] = self.parent
                self.attrs[node] = self.attr
        this_parent = self.parent
        self.parent = node
        for child in node.children():
            self.attr = child[0]
            self.visit(child[1])
        self.parent = this_parent


class ASTCacher(NodeVisitor):
    """ A class for caching all the nodes in an AST as a set, to allow quick querying
    of whether a given node is in the AST or not. """
    
    def __init__(self):
        """ The constructor for the ASTCacher object. """
        super(ASTCacher, self).__init__()
        self.node_cache = set()
    
    def node_in_AST(self, node: Node) -> bool:
        """ Determines whether the given node is in the AST cache or not.

        Args:
            node (Node): The node to check

        Returns:
            bool: True if the node is in the AST cache, false if not. """
        return node in self.node_cache
    
    def generic_visit(self, node: Node) -> None:
        """ Visit a node in an AST, caching the node and then recursively caching its children.

        Args:
            node (Node): The node to visit (and recursively cache). """
        self.node_cache.add(node)
        super(ASTCacher, self).generic_visit(node)


def generate_new_contents(source: interaction.CSource) -> str:
    """Generates textual obfuscated file contents from a source's abstract syntax tree
    (AST), facilitating AST manipulation for source-to-source transformation.

    Args:
        source (interaction.CSource): The source object to generate contents for.

    Returns:
        (str) The generated file contents from the source's AST"""
    new_contents = ""
    for line in source.contents.splitlines():
        line_contents = line.strip()
        if line_contents.strip().startswith(("#", "%:", "??=")):
            new_contents += line + "\n"
    generator = interaction.PatchedGenerator()
    new_contents += generator.visit(source.t_unit)
    return new_contents
