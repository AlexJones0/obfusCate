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
from .utils import ObfuscationUnit, TransformType, generate_new_contents
from .expression_analysis import ExpressionAnalyzer
from .identifier_analysis import IdentifierAnalyzer
from pycparser.c_ast import *
from pycparser.c_lexer import CLexer
from typing import Optional
import pycparser, random, string, json, enum


class IdentifierRenamer:

    class Style(enum.Enum):
        COMPLETE_RANDOM = "Complete Randomness"
        ONLY_UNDERSCORES = "Only underscores"
        MINIMAL_LENGTH = "Minimal length"
        I_AND_L = "Blocks of l's and I's"

    def __init__(self, style: Style, minimise_idents: bool):
        self.banned_idents = set([kw.lower() for kw in CLexer.keywords])
        self.new_idents = []
        self.style = style
        self.minimise_idents = minimise_idents
        self._random_source = random.randint(0, 2**16)
        
    def generate_new_ident(self):
        new_ident = ""
        while len(new_ident) == 0 or new_ident in self.banned_idents:
            if self.style == IdentifierRenamer.Style.COMPLETE_RANDOM:
                size_ = random.randint(4, 19)
                new_ident = random.choices(string.ascii_letters)[0]
                new_ident += "".join(
                    random.choices(string.ascii_letters + string.digits + "_" * 6, k=size_)
                )
            elif self.style == IdentifierRenamer.Style.ONLY_UNDERSCORES:
                new_ident = "_" * (len(self.new_idents) + 1)
            elif self.style == IdentifierRenamer.Style.MINIMAL_LENGTH:
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
            elif self.style == IdentifierRenamer.Style.I_AND_L:
                cur_num = len(self.new_idents)
                num_chars = 8
                num_vals = 2**num_chars
                while cur_num * 4 > num_vals:
                    num_chars += 1
                    num_vals *= 2
                hash_val = (hash(str(cur_num)) + self._random_source) % (num_vals)
                new_ident = bin(hash_val)[2:]
                new_ident = "0" * (num_chars - len(new_ident)) + new_ident
                new_ident = new_ident.replace("1", "l").replace("0", "I")
                while new_ident in self.banned_idents:
                    # Linear probe for next available hash value
                    hash_val += 1
                    if hash_val >= num_vals:
                        hash_val = 0
                    new_ident = bin(hash_val)[2:]
                    new_ident = "0" * (num_chars - len(new_ident)) + new_ident
                    new_ident = new_ident.replace("1", "l").replace("0", "I")
        self.new_idents.append(new_ident)
        if new_ident in self.banned_idents:
            return self.generate_new_ident()
        self.banned_idents.add(new_ident)
        return new_ident
        
    def minimised_transform(self, source: interaction.CSource) -> None:
        analyzer = IdentifierAnalyzer()
        analyzer.load(source)
        analyzer.process()
        skip_idents = set(["main"])
        # Identifier renaming pass 1 - renames to temporary names
        # to avoid minimisation problems due to name clashes with
        # existing variables
        definition_uses = list(analyzer.definition_uses.keys())
        count = 0
        for def_use in definition_uses:
            if def_use[1] in skip_idents:
                continue
            analyzer.change_ident(*def_use, "obfusCate_tempvarname{}".format(count))
            count += 1
        # Identifier renaming pass 2 - performs actual greedy
        # minimised identifier renaming
        definition_uses = list(analyzer.definition_uses.keys())
        members_defined = {}
        for def_use in definition_uses:
            if def_use[1] in skip_idents:
                continue
            definition_node, prev_ident, namespace = def_use
            function = analyzer.get_stmt_func(definition_node)
            required = analyzer.get_required_identifiers(
                definition_node,
                namespace,
                None,
                function
            )
            required = required.difference(set((prev_ident, namespace)))
            if isinstance(namespace, tuple) and definition_node in members_defined:
                members = members_defined[definition_node]
                required = required.union(set(x[0] for x in members if x[1] == namespace))
            new_ident = None
            for ident in self.new_idents:
                if ident not in required:
                    new_ident = ident
                    break
            if new_ident is None:
                new_ident = self.generate_new_ident()
            if isinstance(namespace, tuple):
                if definition_node not in members_defined:
                    members_defined[definition_node] = set()
                members_defined[definition_node].add((new_ident, namespace))
            #print("TRANSFORM:", self.new_idents, namespace if not isinstance(namespace, tuple) else namespace[0], def_use[1], "->", new_ident, required) 
            # TODO IMPORTANT remove when done testing
            analyzer.change_ident(*def_use, new_ident)
        analyzer.update_funcspecs()
    
    def normal_transform(self, source: interaction.CSource) -> None:
        analyzer = IdentifierAnalyzer()
        analyzer.load(source)
        analyzer.process()
        skip_idents = set(["main"])
        definition_uses = list(analyzer.definition_uses.keys())
        ident_mappings = {}
        for def_use in definition_uses:
            identifier = def_use[1]
            if def_use[1] in skip_idents:
                continue
            if identifier in ident_mappings:
                new_ident = ident_mappings[identifier]
            else:
                new_ident = self.generate_new_ident()
                ident_mappings[identifier] = new_ident
            analyzer.change_ident(*def_use, new_ident)
        analyzer.update_funcspecs()
            
    def transform(self, source: interaction.CSource) -> None:
        if self.minimise_idents:
            self.minimised_transform(source)
        else:
            self.normal_transform(source)


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
        """achieved by giving many different constructs the same symbolic name.\n\n"""
        """WARNING: The `minimised identifiers` option does not currently work with function signatures\n"""
        """(those without bodies). Whilst the program will work in some cases, there are no guarantees.\n\n"""
        """WARNING: The 'minimised identifiers' option also cannot be used with nested tag scope (e.g. a\n"""
        """struct/union/enum inside a struct/union etc.) - again, this may work in some cases but is never\n""" 
        """guaranteed. """
    )
    type = TransformType.LEXICAL

    def __init__(self, style, minimise_idents):
        self.style = style
        self.minimise_idents = minimise_idents

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        transformer = IdentifierRenamer(self.style, self.minimise_idents)
        transformer.transform(source)
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
            style.name for style in IdentifierRenamer.Style
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
            {style.name: style for style in IdentifierRenamer.Style}[
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
        self.analyzer = None

    def visit_ArrayRef(self, node: ArrayRef) -> None:
        if node.name is not None and not self.analyzer.is_mutating(node.name):
            if node.subscript is not None and not self.analyzer.is_mutating(node.subscript):
                if random.random() < self.probability:
                    node.name, node.subscript = node.subscript, node.name
        NodeVisitor.generic_visit(self, node)
        
    def visit_FileAST(self, node: FileAST) -> None:
        self.analyzer = ExpressionAnalyzer(node)
        self.analyzer.process()
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
        generator = interaction.PatchedGenerator()
        contents = generator.visit(source.t_unit)
        # Initialise lexer
        lexer = pycparser.c_lexer.CLexer(
            lambda: None, lambda: None, lambda: None, lambda tok: None
        )
        lexer.build()
        lexer.input(contents)
        # Lex tokens and format according to whitespace rules
        spaced_tokens = pycparser.c_lexer.CLexer.keywords + pycparser.c_lexer.CLexer.keywords_new + ("ID",)
        spaced_end_tokens = set(spaced_tokens + (
            "INT_CONST_DEC",
            "INT_CONST_OCT",
            "INT_CONST_HEX",
            "INT_CONST_BIN",
            "INT_CONST_CHAR",
            "FLOAT_CONST",
            "HEX_FLOAT_CONST",
        ))
        spaced_tokens = set(spaced_tokens)
        # Ambiguous lexemes are lexemes of two or more characters that can in some way be split up into 
        # two other lexemes recognised by the program, such that those lexemes must be spaced so they are
        # not ambiguously greedily recognised as these larger lexemes.
        ambiguous_lexemes = set(["+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>=", "++", "--", 
                                 ">>", "<<", "==", "!=", "<=", ">=", "&&", "||", "->"])
        cur_line_length = 0
        cur_line = []
        token = lexer.token()
        prev = None
        while token is not None:
            addSpace = (
                prev is not None
                and (
                    (prev.type in spaced_tokens and token.type in spaced_end_tokens)
                    or prev.value + token.value in ambiguous_lexemes
                )
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
