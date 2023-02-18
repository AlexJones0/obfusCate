""" File: obfuscation/lexical_obfs.py
Implements classes (including obfuscation unit classes) for performing
lexical obfuscation transformations that manipulate either the character
or token streams that comprise a program (as opposed to some more structured 
intermediate representation), including obfuscation related to identifier 
renaming, reversal of indexes, whitespace cluttering and digraph/trigraph
macro encoding. 
"""
from .. import interaction
from ..debug import *
from .utils import ObfuscationUnit, TransformType, generate_new_contents, TypeKinds, \
    VariableUseAnalyzer
from pycparser.c_ast import *
from typing import Optional
import pycparser, random, string, json, enum


class NewNewIdentifierRenamer:
    """Traverses the program AST looking for non-external identifiers (except main),
    transform them to some random scrambled identifier."""

    def __init__(self, style: "IdentifierTraverser.Style", minimise_idents: bool):
        self.new_idents_set = set()
        self.new_idents = []
        self.current_struct = None
        self.struct_ident_index = 0
        self.style = style

    # comehere TODO finish


class IdentifierRenamer:
    """Traverses the program AST looking for non-external identifiers (except main),
    transforming them to some random scrambled identifier."""

    def __init__(self, style: "IdentifierTraverser.Style", minimise_idents: bool):
        self.style = style
        self.minimise_idents = minimise_idents
        self.reset()

    def reset(self):
        self.mappings = [
            {
                TypeKinds.NONSTRUCTURE: {
                    "main": "main",
                },
                TypeKinds.STRUCTURE: {},
                TypeKinds.LABEL: {},
                "fields": {},
            }
        ]
        self.reverse = [
            {
                TypeKinds.NONSTRUCTURE: {
                    "main": "main",
                },
                TypeKinds.STRUCTURE: {},
                TypeKinds.LABEL: {},
            }
        ]
        self.new_idents_set = set()  # Maintain a set for fast checking
        self.new_idents = (
            []
        )  # Maintain a list for ordering (try and re-use when possible)
        self.current_struct = None
        self.struct_ident_index = 0
        self.analyzer = VariableUseAnalyzer()
        self._random_source = random.randint(0, 2**16)

    def generate_new_ident(self):
        new_ident = ""
        while len(new_ident) == 0 or new_ident in self.new_idents_set:
            if self.style == IdentifierTraverser.Style.COMPLETE_RANDOM:
                size_ = random.randint(4, 19)
                new_ident = random.choices(string.ascii_letters)[0]
                new_ident += "".join(
                    random.choices(string.ascii_letters + string.digits + "_" * 6, k=size_)
                )
            elif self.style == IdentifierTraverser.Style.ONLY_UNDERSCORES:
                new_ident = "_" * (len(self.new_idents) + 1)
            elif self.style == IdentifierTraverser.Style.MINIMAL_LENGTH:
                cur_num = len(self.new_idents)
                # choices = "_" + ascii_letters + ascii_digits
                choices = string.ascii_letters
                new_ident = ""
                # new_ident += choices[cur_num // len(ascii_digits)]
                while cur_num >= 0:
                    new_ident += choices[cur_num % len(choices)]
                    cur_num = cur_num // len(choices)
                    if cur_num == 0:
                        break
            elif self.style == IdentifierTraverser.Style.I_AND_L:
                cur_num = len(self.new_idents)
                num_chars = 2
                num_vals = 2**num_chars
                while cur_num * 4 > num_vals:
                    num_chars += 1
                    num_vals *= 2
                hash_val = (hash(str(cur_num)) + self._random_source) % (num_vals)
                new_ident = bin(hash_val)[2:]
                new_ident = "0" * (num_chars - len(new_ident)) + new_ident
                new_ident = new_ident.replace("1", "l").replace("0", "I")
                while new_ident in self.new_idents_set:
                    # Linear probe for next available hash value
                    hash_val += 1
                    if hash_val >= num_vals:
                        hash_val = 0
                    new_ident = bin(hash_val)[2:]
                    new_ident = "0" * (num_chars - len(new_ident)) + new_ident
                    new_ident = new_ident.replace("1", "l").replace("0", "I")
            # TODO figure out if salvageable or scrap
            """elif self.style == IdentifierTraverser.Style.REALISTIC:
                chosen_ident = random.choice(REALISTIC_VAR_NAMES)
                cur_num = 1
                new_ident = chosen_ident
                while new_ident in self.new_idents_set:
                    cur_num += 1
                    new_ident = chosen_ident + str(cur_num)"""
        self.new_idents_set.add(new_ident)
        self.new_idents.append(new_ident)
        return new_ident

    def get_current_mapping(self, ident, kind):
        for scope in self.mappings[::-1]:
            if ident in scope[kind]:
                return scope[kind][ident]
        return None

    def get_current_reverse(self, new_ident, kind):
        for scope in self.reverse[::-1]:
            if new_ident in scope[kind]:
                return scope[kind][new_ident]
        return None

    def transform_idents(self, scope):
        # TODO this method also breaks on while/fors with iterators in the condition:
        #   > if I have two loops with i then i should count as being delcared inside the scope
        #     but it's currently declared outside, meaning that only the latest i naming
        #     is used, generating broken code.
        scope_info = self.analyzer.info[scope]
        self.mappings.append(
            {
                TypeKinds.NONSTRUCTURE: {},
                TypeKinds.STRUCTURE: {},
                TypeKinds.LABEL: {},
                "fields": {},
            }
        )
        self.reverse.append(
            {
                TypeKinds.NONSTRUCTURE: {},
                TypeKinds.STRUCTURE: {},
                TypeKinds.LABEL: {},
            }
        )
        for ASTnode, idents in scope_info["idents"].items():
            for info in idents:
                attr, kind, structure, is_definition = info
                name = getattr(ASTnode, attr)
                if isinstance(name, list):  # TODO - is this correct? <--- NO
                    name = ".".join(name) 
                    # TODO - breaks on ptrs etc. if expected str but found ID
                if is_definition:
                    if name == "main":
                        continue
                    if structure is not None and not isinstance(structure, Enum):
                        if structure != self.current_struct:
                            self.current_struct = structure
                            self.mappings[-1]["fields"][None] = {}
                            self.struct_ident_index = 0
                        if self.struct_ident_index >= len(self.new_idents):
                            # Out of idents, must generate more
                            new_ident = self.generate_new_ident()
                        else:  # Fetch the next available ident and use it
                            new_ident = self.new_idents[self.struct_ident_index]
                        self.struct_ident_index += 1
                        setattr(ASTnode, attr, new_ident)
                        struct_name = (
                            structure if isinstance(structure, str) else structure.name
                        )
                        if self.struct_ident_index <= 1:
                            self.mappings[-1]["fields"][struct_name] = {}
                        self.mappings[-1]["fields"][struct_name][name] = new_ident
                        continue

                    # Otherwise, we check what idents are defined in the current scope,
                    # and which idents are used from this point forward
                    # TODO I'm pretty sure this is WILDLY inefficient, need to figure out a way
                    # to compute this information per-statement in one pass so that this is O(n) and not O(n^2)
                    # TODO - could I also do it by maintaining a list of used/defined for each scope
                    # and just modifying as I go??? Maybe a decent idea?
                    current_stmt = self.analyzer.get_stmt(ASTnode)
                    scope_defs = self.analyzer.get_scope_definitions(
                        scope, None, current_stmt
                    )
                    current_defs = self.analyzer.get_definitions_at_stmt(
                        current_stmt, scope
                    )
                    used_after = self.analyzer.get_usage_from_stmt(current_stmt, scope)
                    still_used = current_defs.intersection(used_after)
                    found_reuse = False
                    for new_ident in self.new_idents:
                        curr_mapping = self.get_current_reverse(new_ident, kind)
                        ident = (curr_mapping, kind)
                        if curr_mapping is None or (
                            ident not in scope_defs and ident not in still_used
                        ):
                            # We found an ident that hasn't been used for this kind, or that has been used
                            # for this kind but is no longer needed (and not defined in this scope), so
                            # we can repurpose it.
                            setattr(ASTnode, attr, new_ident)
                            self.mappings[-1][kind][name] = new_ident
                            self.reverse[-1][kind][new_ident] = name
                            found_reuse = True
                            break
                    if found_reuse:
                        continue

                    # At this point we are not in a structure, have used all mappings for this kind, and have tried
                    # and failed to re-use every mapping, so we must define a new mapping
                    new_ident = self.generate_new_ident()
                    self.mappings[-1][kind][name] = new_ident
                    self.reverse[-1][kind][new_ident] = name
                    setattr(ASTnode, attr, new_ident)
                else:  # Is a reference to some identifier
                    if structure is not None and not isinstance(structure, Enum):
                        if isinstance(structure, tuple) and isinstance(
                            structure[0], StructRef
                        ):
                            if structure[1] == "name":
                                new_ident = self.get_current_mapping(name, kind)
                                if new_ident is not None:
                                    setattr(ASTnode, attr, new_ident)
                                continue
                            # TODO anything I do here will likely break under pointers :(((
                            # need to somehow make it traverse pointerdecls and arraydecls at the right point?
                            structname = ".".join(
                                self.analyzer.types[
                                    structure[0].name.name
                                ].type.type.names
                            )
                            oldname = self.get_current_reverse(
                                structname, TypeKinds.STRUCTURE
                            )  # TODO this could cause some errors? because not accounting for type aliasing?
                            if (
                                oldname is None
                            ):  # TODO BAD TEMPORARY FIX FOR NOW. WILL BREAK SOME STUFF
                                oldname = self.get_current_reverse(
                                    structname, TypeKinds.NONSTRUCTURE
                                )
                            mapping = self.get_current_mapping(oldname, "fields")
                            if mapping is None or name not in mapping:
                                continue
                            setattr(
                                ASTnode, attr, mapping[name]
                            )  # TODO names - could cause issue - need to make a list again maybe? Not sure
                            continue
                        if isinstance(structure, (NamedInitializer,)):
                            continue  # TODO figure out what to do!?!?!?
                            # Need to figure out a way to get the struct type for minimal mapping
                        if isinstance(structure, StructRef):
                            continue
                        mapping = self.get_current_mapping(structure.name, "fields")
                        if mapping is None or name not in mapping:
                            continue
                        setattr(ASTnode, attr, mapping[name])
                        continue
                    new_ident = self.get_current_mapping(name, kind)
                    if new_ident is not None:
                        setattr(ASTnode, attr, new_ident)

        for child, _ in scope_info["children"]:
            self.transform_idents(child)
        self.mappings = self.mappings[:-1]
        self.reverse = self.reverse[:-1]

    def transform(self, source: interaction.CSource) -> None:
        self.analyzer.input(source)
        self.analyzer.process()
        self.transform_idents(None)  # Perform DFS, transforming idents
        self.reset()


class IdentifierTraverser(NodeVisitor):
    """Traverses the program AST looking for non-external identifiers (except main),
    transforming them to some random scrambled identifier."""

    class Style(enum.Enum):
        COMPLETE_RANDOM = "Complete Randomness"
        ONLY_UNDERSCORES = "Only underscores"  # TODO will this break anything?
        MINIMAL_LENGTH = "Minimal length"
        I_AND_L = "Blocks of l's and I's"
        #REALISTIC = "Realistic Names" # TODO salvage or scrap

    def __init__(self, style: Style, minimise_idents: bool):
        self.style = style
        self.minimise_idents = minimise_idents
        self.reset()

    def reset(self):
        self.idents = {"main": "main"}
        self._new_idents = set()
        self._scopes = list()
        self._random_source = random.randint(0, 2**16)

    def get_new_ident(
        self, ident
    ):  # TODO could add an option for variable reuse as well using liveness?
        if (
            self.minimise_idents
        ):  # TODO THIS OPTION IS VERY BROKE BUT COMPLEX SO JUST LEAVE IT FOR NOW?
            for new_ident in self._new_idents:
                in_scope = False  # TODO maintain a list of unused idents - will be cleaner and cheaper
                for scope in self._scopes[::-1]:
                    if new_ident in scope:
                        in_scope = True
                        break
                if not in_scope:
                    self.idents[ident] = new_ident
                    return new_ident
        new_ident = ""
        while len(new_ident) == 0 or new_ident in self._new_idents:
            if self.style == self.Style.COMPLETE_RANDOM:
                size_ = random.randint(4, 19)
                new_ident = random.choices(string.ascii_letters)[0]
                new_ident += "".join(
                    random.choices(string.ascii_letters + string.digits + "_" * 6, k=size_)
                )
            elif self.style == self.Style.ONLY_UNDERSCORES:
                new_ident = "_" * (len(self._new_idents) + 1)
            elif self.style == self.Style.MINIMAL_LENGTH:
                cur_num = len(self._new_idents)
                # choices = "_" + ascii_letters + ascii_digits
                choices = string.ascii_letters
                new_ident = ""
                # new_ident += choices[cur_num // len(ascii_digits)]
                while cur_num >= 0:
                    new_ident += choices[cur_num % len(choices)]
                    cur_num = cur_num // len(choices)
                    if cur_num == 0:
                        break
            elif self.style == self.Style.I_AND_L:
                cur_num = len(self._new_idents)
                num_chars = 16
                num_vals = 2**num_chars
                while cur_num * 4 > num_vals:
                    num_chars += 1
                    num_vals *= 2
                hash_val = (hash(str(cur_num)) + self._random_source) % (num_vals)
                new_ident = bin(hash_val)[2:]
                new_ident = "0" * (num_chars - len(new_ident)) + new_ident
                new_ident = new_ident.replace("1", "l").replace("0", "I")
                while new_ident in self._new_idents:
                    # Linear probe for next available hash value
                    hash_val += 1
                    if hash_val >= num_vals:
                        hash_val = 0
                    new_ident = bin(hash_val)[2:]
                    new_ident = "0" * (num_chars - len(new_ident)) + new_ident
                    new_ident = new_ident.replace("1", "l").replace("0", "I")
            # TODO salvage or remove
            """elif self.style == self.Style.REALISTIC:
                chosen_ident = random.choice(REALISTIC_VAR_NAMES)
                cur_num = 1
                new_ident = chosen_ident
                while new_ident in self._new_idents:
                    cur_num += 1
                    new_ident = chosen_ident + str(cur_num)"""
        self._new_idents.add(new_ident)
        self.idents[ident] = new_ident
        return new_ident

    def scramble_ident(self, node):
        if hasattr(node, "name") and node.name is not None:
            if node.name not in self.idents:
                self.get_new_ident(node.name)
            node.name = self.idents[node.name]
            self._scopes[-1].add(node.name)

    def visit_FileAST(self, node):
        self._scopes.append(set())
        NodeVisitor.generic_visit(self, node)
        self._scopes = self._scopes[:-1]
        self.reset()

    def visit_FuncDef(self, node):
        self._scopes.append(set())
        NodeVisitor.generic_visit(self, node)
        self._scopes = self._scopes[:-1]

    def visit_Compound(self, node):
        self._scopes.append(set())
        NodeVisitor.generic_visit(self, node)
        self._scopes = self._scopes[:-1]

    def visit_Decl(self, node):
        self.scramble_ident(node)
        NodeVisitor.generic_visit(self, node)

    def visit_Union(self, node):
        self.scramble_ident(node)
        NodeVisitor.generic_visit(self, node)

    def visit_Enum(self, node):
        self.scramble_ident(node)
        NodeVisitor.generic_visit(self, node)
        self._scopes[-1].remove(node.name)

    def visit_Enumerator(self, node):
        self.scramble_ident(node)
        NodeVisitor.generic_visit(self, node)

    def visit_Label(self, node):
        self.scramble_ident(node)
        NodeVisitor.generic_visit(self, node)

    def visit_Goto(self, node):
        self.scramble_ident(node)
        NodeVisitor.generic_visit(self, node)

    def visit_TypeDecl(self, node):
        if node.declname is not None:
            if node.declname not in self.idents:
                self.get_new_ident(node.declname)
            node.declname = self.idents[node.declname]
            self._scopes[-1].add(node.declname)
        NodeVisitor.generic_visit(self, node)

    def visit_ID(self, node):
        if node.name in self.idents:
            node.name = self.idents[node.name]
        NodeVisitor.generic_visit(self, node)

    def visit_FuncCall(self, node):
        if node.name in self.idents:
            node.name = self.idents[node.name]
        NodeVisitor.generic_visit(self, node)

    def visit_IdentifierType(self, node):
        for i, name in enumerate(node.names):
            if name in self.idents:
                node.names[i] = self.idents[name]
        NodeVisitor.generic_visit(self, node)

    def visit_Pragma(self, node):  # TODO maybe warn on pragma?
        # TODO something's not working with pragmas because of how pycparser handles them!
        print_error("Error: cannot currently handle pragmas!")
        log(
            "Could not continue obfuscation because the obfuscator cannot handle pragmas!"
        )
        exit()

    def visit_StaticAssert(self, node):  # TODO what's breaking here?
        print_error("Error: cannot currently handle static assertions!")
        log(
            "Could not continue obfuscation because the obfuscator cannot handle static asserts!"
        )
        exit()


# TODO this transformation still breaks sometimes, even without minimisation
# e.g. try linpack_nodefs.c with most other options first, it will break. Why?
class IdentifierRenameUnit(ObfuscationUnit):
    """Implements an identifier rename (IRN) obfuscation transformation, which takes the input
    source code and renames all identifiers (function names, parameter names, variable names, etc.)
    such that the program still performs the same functionality, but now the identifier names reveal
    no meaningful information about the program and are difficult to humanly comprehend."""

    name = "Identifier Renaming"
    description = "Renames variable/function names to make them incomprehensible."
    extended_description = (
        """This transformation randomises identifiers in the program (e.g. variable names, type names,\n"""
        """function names, etc.) to remove all symbolic meaning stored via these names in the source code.\n"""
        """Note that this will not affect the compiled code in any way.\n\n"""
        """One optional input is the style of randomisation to be used - you can choose between completely\n"""
        """random variable names, names that use only underscore characters, and minimal length names.\n"""
        """The other optional input allows you to enable identifier minimisation, where names are greedily\n"""
        """reused whenever possible to achieve the maximal overlap between names, such that obfuscation is\n"""
        """achieved by giving many different constructs the same symbolic name."""
    )
    type = TransformType.LEXICAL

    def __init__(self, style, minimise_idents):
        self.style = style
        self.minimise_idents = minimise_idents
        self.transformer = IdentifierRenamer(style, minimise_idents)

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        if self.minimise_idents:
            # TODO identifier minimisation breaking on AOCday6 example - WHY!?
            transformer = IdentifierRenamer(self.style, True)
            transformer.transform(source.t_unit)
        else:
            traverser = IdentifierTraverser(self.style, False)
            traverser.visit(source.t_unit)
        new_contents = generate_new_contents(source)
        return interaction.CSource(source.fpath, new_contents, source.t_unit)

    def to_json(self) -> str:
        """Converts the identifier renaming unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps(
            {
                "type": str(__class__.name),
                "style": self.style.name,
                "minimise_idents": self.minimise_idents,
            }
        )

    def from_json(json_str: str) -> Optional["IdentifierRenameUnit"]:
        """Converts the provided JSON string to an identifier renaming transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding identifier renaming unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load RenameIdentifiers() - invalid JSON provided.",
                print_err=True,
            )
            return None
        if "type" not in json_obj:
            log(
                "Failed to load RenameIdentifiers() - no type provided.", print_err=True
            )
            return None
        elif json_obj["type"] != __class__.name:
            log(
                "Failed to load RenameIdentifiers() - class/type mismatch.",
                print_err=True,
            )
            return None
        elif "style" not in json_obj:
            log(
                "Failed to load RenameIdentifiers() - no style value provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["style"], str):
            log(
                "Failed to load RenameIdentifiers() - style is not a valid string.",
                print_err=True,
            )
            return None
        elif json_obj["style"] not in [
            style.name for style in IdentifierTraverser.Style
        ]:
            log(
                "Failed to load RenameIdentifiers() - style '{}' is not a valid style.".format(
                    json_obj["style"]
                ),
                print_err=True,
            )
            return None
        elif "minimise_idents" not in json_obj:
            log(
                "Failed to load RenameIdentifiers() - no identifier minimisation flag value provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["minimise_idents"], bool):
            log(
                "Failed to load RenameIdentifiers() - identifier minimisation flag value is not a Boolean.",
                print_err=True,
            )
            return None
        return IdentifierRenameUnit(
            {style.name: style for style in IdentifierTraverser.Style}[
                json_obj["style"]
            ],
            json_obj["minimise_idents"],
        )

    def __str__(self):
        style_flag = f"style={self.style.name}"
        minimise_ident_flag = (
            f"minimal={'ENABLED' if self.minimise_idents else 'DISABLED'}"
        )
        return f"RenameIdentifiers({style_flag},{minimise_ident_flag})"


class IndexReverser(NodeVisitor):
    def __init__(self, probability: float) -> None:
        self.probability = probability

    def visit_ArrayRef(self, node):
        if node.name is not None and node.subscript is not None:
            if random.random() < self.probability:
                node.name, node.subscript = node.subscript, node.name
        NodeVisitor.generic_visit(self, node)


class ReverseIndexUnit(ObfuscationUnit):
    """Implements a simple source-level obfuscation in which array indexes e.g. a[i] are swapped
    so that the index becomes the array and vice versa, e.g. i[a]. This exploits the symmetry
    of indexing in C, as technically a[i] == *(a + i) == *(i + a) == i[a] by the commutativity
    of the addition operation on integers."""

    name = "Reverse Indexes"
    description = "Reverses indexing operations, swapping the array and the index"
    extended_description = (
        "This transformation reverses indexes, i.e. it changes all indexing operations a[i]\n"
        "into equivalent indexing operations i[a], which are non-intuitive and difficult to\n"
        "comprehend at a glance. This exploits the symmetry of indexing in C, as technically\n"
        "a[i] == *(a + i) == *(i + a) == i[a] by the commutativity of the addition operation."
    )
    type = TransformType.LEXICAL  # TODO lexical or encoding?

    def __init__(self, probability: float) -> None:
        self.probability = probability
        self.traverser = IndexReverser(probability)

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        self.traverser.visit(source.t_unit)
        new_contents = generate_new_contents(source)
        return interaction.CSource(source.fpath, new_contents, source.t_unit)

    def to_json(self) -> str:
        """Converts the whitespace cluttering unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps(
            {"type": str(__class__.name), "probability": self.probability}
        )

    def from_json(json_str: str) -> Optional["ReverseIndexUnit"]:
        """Converts the provided JSON string to an index reversing transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding index reversing unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load ReverseIndexes() - invalid JSON provided.",
                print_err=True,
            )
            return None
        if "type" not in json_obj:
            log("Failed to load ReverseIndexes() - no type provided.", print_err=True)
            return None
        elif json_obj["type"] != __class__.name:
            log(
                "Failed to load ReverseIndexes() - class/type mismatch.",
                print_err=True,
            )
            return None
        elif "probability" not in json_obj:
            log(
                "Failed to load ReverseIndexes() - no probability provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["probability"], (float, int)):
            log(
                "Failed to load ReverseIndexes() - given probability {} is not a valid number.".format(
                    json_obj["probability"]
                ),
                print_err=True,
            )
            return None
        elif json_obj["probability"] < 0 or json_obj["probability"] > 1:
            log(
                "Failed to load ReverseIndexes() - given probability {} is not 0 <= p <= 1.".format(
                    json_obj["probability"]
                ),
                print_err=True,
            )
            return None
        return ReverseIndexUnit(json_obj["probability"])

    def __str__(self):
        probability_flag = f"p={self.probability}"
        return f"ReverseIndexes({probability_flag})"


class ClutterWhitespaceUnit(ObfuscationUnit):  # TODO picture extension?
    """Implements simple source-level whitespace cluttering, breaking down the high-level abstraction of
    indentation and program structure by altering whitespace in the file."""

    name = "Clutter Whitespace"
    description = "Clutters program whitespace, making it difficult to read"
    extended_description = (
        """This transformation clutters the whitespace of a program, removing all indentation and spacing\n"""
        """where possible between program lexemes. Currently, text is wrapped to fit roughly 100 characters\n"""
        """per line, completely destroying symbolic code readability via whitespace. Note that this only\n"""
        """affects the source code - no change will be made to the compiled code. Note that any non-textual\n"""
        """transformations applied after this point will undo its changes."""
    )
    type = TransformType.LEXICAL

    def __init__(self, target_length: int, pad_lines: bool):
        # TODO could add a random line length option in the future
        self.target_length = target_length
        self.pad_lines = pad_lines

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        # Preprocess contents
        new_contents = ""
        for line in source.contents.splitlines():
            if (
                line.strip().startswith("#")
                or line.strip().startswith("%:")
                or line.strip().startswith("??=")
            ):
                new_contents += line + "\n"
        generator = pycparser.c_generator.CGenerator()
        contents = generator.visit(source.t_unit)
        # Initialise lexer
        lexer = pycparser.c_lexer.CLexer(
            lambda: None, lambda: None, lambda: None, lambda tok: None
        )
        lexer.build()
        lexer.input(contents)
        # Lex tokens and format according to whitespace rules
        spaced_tokens = pycparser.c_lexer.CLexer.keywords + pycparser.c_lexer.CLexer.keywords_new + ("ID",)
        spaced_end_tokens = spaced_tokens + (
            "INT_CONST_DEC",
            "INT_CONST_OCT",
            "INT_CONST_HEX",
            "INT_CONST_BIN",
            "INT_CONST_CHAR",
            "FLOAT_CONST",
            "HEX_FLOAT_CONST",
        )
        cur_line_length = 0
        cur_line = []
        token = lexer.token()
        prev = None
        while token is not None:
            addSpace = (
                prev is not None
                and prev.type in spaced_tokens
                and token.type in spaced_end_tokens
            )
            cur_line_length += (1 if addSpace else 0) + len(token.value)
            if cur_line_length <= self.target_length:
                if addSpace:
                    cur_line.append(" ")
                cur_line.append(token.value)
            # TODO do escape characters make this non-salvageable? How can I detect these cases?
            #elif (
            #    token.type
            #    in (
            #        "STRING_LITERAL",
            #        "WSTRING_LITERAL",
            #        "U8STRING_LITERAL",
            #        "U16STRING_LITERAL",
            #        "U32STRING_LITERAL",
            #    )
            #    and cur_line_length - len(token.value) >= 4
            #):  # Split strings across multiple lines where possible and required
                #split_size = self.target_length - cur_line_length + len(token.value) - 1
                #if addSpace:
                #    cur_line.append(" ")
                #    split_size -= 1
                #cur_line.append(token.value[:split_size] + token.value[0] + "\n")
                #new_contents += "".join(cur_line)
                #cur_line = []
                #cur_line_length = 0
                #token.value = token.value[0] + token.value[split_size:]
                #continue
            else:
                cur_line_length -= (1 if addSpace else 0) + len(token.value)
                if len(cur_line) > 0 and cur_line_length <= self.target_length:
                    if self.pad_lines and len(cur_line) > 1:
                        # Pad from a random position in random increments of 1-3 so
                        # that padding is adequately spread out
                        token_index = random.randint(0, max(0, len(cur_line) - 2))
                        while cur_line_length < self.target_length:
                            cur_line[token_index] = cur_line[token_index] + " "
                            cur_line_length += 1
                            token_index = (token_index + random.randint(1, 3)) % (
                                len(cur_line) - 1
                            )
                    cur_line.append("\n")
                    new_contents += "".join(cur_line)
                    cur_line = [token.value]
                    cur_line_length = len(token.value)
                elif len(cur_line) > 0:
                    cur_line.append("\n")
                    new_contents += "".join(cur_line)
                    cur_line = [token.value]
                    cur_line_length = len(token.value)
                else:  # Nothing else on line and token size > max -> Must overflow
                    new_contents += token.value + "\n"
                    cur_line = []
                    cur_line_length = 0
            prev = token
            token = lexer.token()
        if len(cur_line) != 0:
            cur_line.append("\n")
            new_contents += "".join(cur_line)
        return interaction.CSource(source.fpath, new_contents, source.t_unit)

    def to_json(self) -> str:
        """Converts the whitespace cluttering unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps(
            {
                "type": str(__class__.name),
                "target_length": self.target_length,
                "pad_lines": self.pad_lines,
            }
        )

    def from_json(json_str: str) -> Optional["ClutterWhitespaceUnit"]:
        """Converts the provided JSON string to a whitespace cluttering transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding whitespace cluttering unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load ClutterWhitespace() - invalid JSON provided.",
                print_err=True,
            )
            return None
        if "type" not in json_obj:
            log(
                "Failed to load ClutterWhitespace() - no type provided.", print_err=True
            )
            return None
        elif json_obj["type"] != __class__.name:
            log(
                "Failed to load ClutterWhitespace() - class/type mismatch.",
                print_err=True,
            )
            return None
        elif "target_length" not in json_obj:
            log(
                "Failed to load ClutterWhitespace() - target length not provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["target_length"], int):
            log(
                "Failed to load ClutterWhitespace() - target length {} is not a valid integer.".format(
                    json_obj["target_length"]
                ),
                print_err=True,
            )
            return None
        elif json_obj["target_length"] < 0:
            log(
                "Failed to load ClutterWhitespace() - target length {} is not >= 0.".format(
                    json_obj["target_length"]
                ),
                print_err=True,
            )
            return None
        elif "pad_lines" not in json_obj:
            log(
                "Failed to load ClutterWhitespace() - line padding flag not provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["pad_lines"], bool):
            log(
                "Failed to load ClutterWhitespace() - line padding flag is not a valid Boolean.",
                print_err=True,
            )
            return None
        return ClutterWhitespaceUnit(json_obj["target_length"], json_obj["pad_lines"])

    def __str__(self):
        target_length_flag = f"target_len={self.target_length}"
        pad_flag = f"padding={'ENABLED' if self.pad_lines else 'DISABLED'}"
        return f"ClutterWhitespace({target_length_flag},{pad_flag})"


class DiTriGraphEncodeUnit(ObfuscationUnit):
    """Implements a string literal encoding (SLE) obfuscation transformation, which takes the
    input source code and encodes string literals in the code according to some encoding method
    such that the program still performs the same functionality, but strings can no longer be
    easily read in the code."""

    # TODO WARNING ORDERING - SHOULD COME LAST?
    name = "Digraph/Trigraph Encoding"
    description = (
        "Encodes certain symbols with Digraphs/Trigraphs to make them incomprehensible"
    )
    extended_description = (
        """This transformation encodes certain symbols within the program (e.g. '{', '#', ']') as digraphs\n"""
        """or trigraphs, which are respectively two- or three- character combinations that are replaced by\n"""
        """C's preprocessor to allow keyboard with less symbols to type C programs. Note that this only affects\n"""
        """the source code - no change will be made to the compiled code. Note that any non-textual\n"""
        """transformations applied after this point will undo its changes.\n\n"""
        """The first available option is the mapping type - you can choose to encode using only digraphs, only\n"""
        """trigraphs, or a mixture of both digraphs and trigraphs. For the second option, you can choose the\n"""
        """prorbability that an encoding takes place. 0.0 means no encoding, 0.5 means approximately half will\n"""
        """be encoded, and 1.0 means all symbols are encoded. This can be used to achieve a mixture of digraphs,\n"""
        """trigraphs and regular symbols as is desired."""
    )
    type = TransformType.LEXICAL

    digraph_map = {
        "[": "<:",
        "]": ":>",
        "{": "<%",
        "}": "%>",
        "#": "%:",
    }

    trigraph_map = {
        "#": "??=",
        "\\": "??/",
        "^": "??'",
        "[": "??(",
        "]": "??)",
        "|": "??!",
        "{": "??<",
        "}": "??>",
        "~": "??-",
    }

    class Style(enum.Enum):
        DIGRAPH = "Digraphs"
        TRIGRAPH = "Trigraphs"
        MIXED = "Mixed Digraph/Trigraphs"

    def __init__(self, style: Style, chance: float):
        self.style = style
        if chance < 0.0:
            self.chance = 0.0
        elif chance > 1.0:
            self.chance = 1.0
        else:
            self.chance = chance

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        new_contents = ""
        prev = None
        str_top = None
        for char in source.contents:
            if (char == "'" or char == '"') and prev != "\\":
                if str_top is None:
                    str_top = char
                elif str_top == char:
                    str_top = None
            if str_top is not None or random.random() > self.chance:
                new_contents += char
                prev = char
                continue
            if self.style == self.Style.MIXED and (
                char in self.digraph_map or char in self.trigraph_map
            ):
                if random.randint(1, 2) == 1 and char in self.digraph_map:
                    new_contents += self.digraph_map[char]
                else:
                    new_contents += self.trigraph_map[char]
            elif self.style == self.Style.DIGRAPH and char in self.digraph_map:
                new_contents += self.digraph_map[char]
            elif self.style == self.Style.TRIGRAPH and char in self.trigraph_map:
                new_contents += self.trigraph_map[char]
            else:
                new_contents += char
            prev = char
        return interaction.CSource(source.fpath, new_contents, source.t_unit)

    def to_json(self) -> str:
        """Converts the digraph/trigraph encoding unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps(
            {
                "type": str(__class__.name),
                "style": self.style.name,
                "chance": self.chance,
            }
        )

    def from_json(json_str: str) -> Optional["DiTriGraphEncodeUnit"]:
        """Converts the provided JSON string to a digraph/trigraph encoding transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding digraph/trigraph encoding unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load DiTriGraphEncode() - invalid JSON provided.",
                print_err=True,
            )
            return None
        if "type" not in json_obj:
            log("Failed to load DiTriGraphEncode() - no type provided.", print_err=True)
            return None
        elif json_obj["type"] != __class__.name:
            log(
                "Failed to load DiTriGraphEncode() - class/type mismatch.",
                print_err=True,
            )
            return None
        elif "style" not in json_obj:
            log(
                "Failed to load DiTriGraphEncode() - no style value provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["style"], str):
            log(
                "Failed to load DiTriGraphEncode() - style is not a valid string.",
                print_err=True,
            )
            return None
        elif json_obj["style"] not in [
            style.name for style in DiTriGraphEncodeUnit.Style
        ]:
            log(
                "Failed to load DiTriGraphEncode() - style '{}' is not a valid style.".format(
                    json_obj["style"]
                ),
                print_err=True,
            )
            return None
        elif "chance" not in json_obj:
            log(
                "Failed to load AugmentOpaqueUnit() - no probability value is given.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["chance"], (int, float)):
            log(
                "Failed to load AugmentOpaqueUnit() - probability value is not a valid number.",
                print_err=True,
            )
            return None
        elif json_obj["chance"] < 0 or json_obj["chance"] > 1:
            log(
                "Failed to load AugmentOpaqueUnit() - probability value must be 0 <= p <= 1.",
                print_err=True,
            )
            return None
        return DiTriGraphEncodeUnit(
            {style.name: style for style in DiTriGraphEncodeUnit.Style}[
                json_obj["style"]
            ],
            json_obj["chance"],
        )

    def __str__(self):
        style_flag = f"style={self.style.name}"
        probability_flag = f"p={self.chance}"
        return f"DiTriGraphEncode({style_flag},{probability_flag})"