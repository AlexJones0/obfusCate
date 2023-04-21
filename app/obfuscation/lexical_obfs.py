""" File: obfuscation/lexical_obfs.py
Implements classes (including obfuscation unit classes) for performing
lexical obfuscation transformations that manipulate either the character
or token streams that comprise a program (as opposed to some more structured 
intermediate representation), including obfuscation related to identifier 
renaming, reversal of indexes, whitespace cluttering and digraph/trigraph
encoding. 
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


class IdentifierRenameUnit(ObfuscationUnit):
    """Implements an identifier rename (IRN) obfuscation transformation, which takes the input
    source code and renames all identifiers (function names, parameter names, variable names, etc.)
    such that the program still performs the same functionality, but now the identifier names reveal
    no meaningful information about the program and are difficult to humanly comprehend."""

    name = "Identifier Renaming"
    description = "Renames variable/function names to make them incomprehensible."
    extended_description = (
        "This transformation randomises identifiers in the program (e.g. variable names, type names,\n"
        "function names, etc.) to remove all symbolic meaning stored via these names in the source code.\n"
        "Note that this will not affect the compiled code in any way.\n\n"
        "One optional input is the style of randomisation to be used - you can choose between completely\n"
        "random variable names, names that use only underscore characters, and minimal length names.\n"
        "The other optional input allows you to enable identifier minimisation, where names are greedily\n"
        "reused whenever possible to achieve the maximal overlap between names, such that obfuscation is\n"
        "achieved by giving many different constructs the same symbolic name."
    )
    type = TransformType.LEXICAL

    class Style(enum.Enum):
        """An enumerated type representing the four different identifier renaming styles."""

        COMPLETE_RANDOM = "Complete Randomness"
        ONLY_UNDERSCORES = "Only underscores"
        MINIMAL_LENGTH = "Minimal length"
        I_AND_L = "Blocks of l's and I's"

    def __init__(self, style: Style, minimise_idents: bool):
        """A constructor for the IdentifierRenameUnit obfuscation transform.

        Args:
            style (Style): The identifier renaming style to apply.
            minimise_idents (bool): Whether to minimise identifier usage or not.
        """
        self.style = style
        self.minimise_idents = minimise_idents

    def _reset(self) -> None:
        """Resets the IdentifierRenameUnit's state (tracking variables), allowing
        it to perform obfuscation for a new program."""
        self.banned_idents = set([kw.lower() for kw in CLexer.keywords])
        self.new_idents = []
        self._random_source = random.randint(0, 2**16)
        self.skip_idents = set(["main"])

    def _generate_min_lenth_ident(self) -> str:
        """Generates a new identifier using the minimised identifier length renaming style,
        generating the shortest length identifier that is not currently banned.

        Returns:
            str: The new identifier to use."""
        cur_num = len(self.new_idents)
        choices = string.ascii_letters + "_"  # Idents cannot start with digits
        new_ident = ""
        while cur_num >= 0:
            new_ident += choices[cur_num % len(choices)]
            cur_num = cur_num // len(choices)
            if cur_num == 0:
                break
            if len(new_ident) == 1:  # But digits can appear later on in idents
                choices = string.ascii_letters + "_" + string.digits
        return new_ident

    def _generate_i_and_l_ident(self) -> str:
        """Generates a new identifier using the "Block of I's and L's" renaming style,
        generating indistinguishable identifiers like "IlllIIIlIlIllI". Random patterns
        (rather than sequential) are achieved by using an appropriate modular hash
        function alongside linear probing in the case of collisions.

        Returns:
            str: The new identifier to use."""
        # Determine block size; resize if necessary
        cur_num = len(self.new_idents)
        num_chars = 8
        num_vals = 2**num_chars
        while cur_num * 4 > num_vals:
            num_chars += 1
            num_vals *= 2

        # Create a new random block by hashing
        hash_val = (hash(str(cur_num)) + self._random_source) % (num_vals)
        new_ident = bin(hash_val)[2:]
        new_ident = "0" * (num_chars - len(new_ident)) + new_ident
        new_ident = new_ident.replace("1", "l").replace("0", "I")

        # Handle collision by linear probing for next available hash value
        while new_ident in self.banned_idents:
            hash_val += 1
            if hash_val >= num_vals:
                hash_val = 0
            new_ident = bin(hash_val)[2:]
            new_ident = "0" * (num_chars - len(new_ident)) + new_ident
            new_ident = new_ident.replace("1", "l").replace("0", "I")

        return new_ident

    def generate_new_ident(self) -> str:
        """Generates a new identifier, by calling the appropriate method for the selected
        identifier generation style. New identifiers are then cached such that they are
        not re-generated.

        Returns:
            str: The next new identifier to use.
        """
        new_ident = ""
        while len(new_ident) == 0 or new_ident in self.banned_idents:
            if self.style == self.Style.COMPLETE_RANDOM:
                size_ = random.randint(4, 19)
                new_ident = random.choices(string.ascii_letters)[0]
                valid_char_set = string.ascii_letters + string.digits + "_" * 6
                new_ident += "".join(random.choices(valid_char_set, k=size_))
            elif self.style == self.Style.ONLY_UNDERSCORES:
                new_ident = "_" * (len(self.new_idents) + 1)
            elif self.style == self.Style.MINIMAL_LENGTH:
                new_ident = self._generate_min_lenth_ident()
            elif self.style == self.Style.I_AND_L:
                new_ident = self._generate_i_and_l_ident()

        # Cache the new identifier such that it is banned in future generation
        self.new_idents.append(new_ident)
        if new_ident in self.banned_idents:
            return self.generate_new_ident()
        self.banned_idents.add(new_ident)
        return new_ident

    def minimised_transform(
        self, source: interaction.CSource, analyzer: IdentifierAnalyzer
    ) -> None:
        """Transforms the given provided source program by renaming its identifiers such that minimal
        unique identifiers are used. This involves a first renaming clash to avoid naming conflicts
        during the name minimisation process.

        Args:
            source (interaction.CSource): The C Source program to obfuscate
            analyzer (IdentifierAnalyzer): The identifier analyzer that has analysed the program."""
        # Perform first renaming pass: rename to temporary names to avoid name clashes
        definition_uses = list(analyzer.definition_uses.keys())
        for i, def_use in enumerate(definition_uses):
            if def_use[1] in self.skip_idents:
                continue
            analyzer.change_ident(*def_use, "obfusCate_tempvarname{}".format(i))

        # Second renaming pass: performs actual greedy minimised identifier renaming
        definition_uses = list(analyzer.definition_uses.keys())
        members_defined = {}
        for def_use in definition_uses:
            if def_use[1] in self.skip_idents:
                continue

            # Retrieve the set of identifiers required to be defined from this point
            # onwards, with the exception of the current identifier
            definition_node, prev_ident, namespace = def_use
            function = analyzer.get_stmt_func(definition_node)
            required = analyzer.get_required_identifiers(
                definition_node, namespace, None, function
            )
            required = required.difference(set((prev_ident, namespace)))
            if isinstance(namespace, tuple) and definition_node in members_defined:
                members = members_defined[definition_node]
                required = required.union(
                    set(x[0] for x in members if x[1] == namespace)
                )

            # Iteratively check through already-created identifiers; use the first one that
            # is no longer required if such an identifier already exists. If it does not,
            # then generate a new identifier
            new_ident = None
            for ident in self.new_idents:
                if ident not in required:
                    new_ident = ident
                    break
            if new_ident is None:
                new_ident = self.generate_new_ident()

            # Change the identifier to use its new name; update struct members accordingly
            if isinstance(namespace, tuple):
                if definition_node not in members_defined:
                    members_defined[definition_node] = set()
                members_defined[definition_node].add((new_ident, namespace))
            analyzer.change_ident(*def_use, new_ident)

    def normal_transform(
        self, source: interaction.CSource, analyzer: IdentifierAnalyzer
    ) -> None:
        """Transforms the given provided source program by renaming its identifiers such that each unique
        identifier name in the original program receives a new unique name.

        Args:
            source (interaction.CSource): The C Source program to obfuscate
            analyzer (IdentifierAnalyzer): The identifier analyzer that has analysed the program."""
        definition_uses = list(analyzer.definition_uses.keys())
        ident_mappings = {}
        for def_use in definition_uses:
            identifier = def_use[1]
            if identifier in self.skip_idents:
                continue
            if identifier in ident_mappings:
                new_ident = ident_mappings[identifier]
            else:
                new_ident = self.generate_new_ident()
                ident_mappings[identifier] = new_ident
            analyzer.change_ident(*def_use, new_ident)

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        """Performs the identifier renaming transformation on the given source program.

        Args:
            source (interaction.CSource): The source code to transform.

        Returns:
            interaction.CSource: The transformed source code.
        """
        # Reset the transform unit's state and analyze the program's identifer usage.
        self._reset()
        analyzer = IdentifierAnalyzer()
        analyzer.load(source)
        analyzer.process()

        # Perform the transformation, and generate the new obfuscated CSource
        if self.minimise_idents:
            self.minimised_transform(source, analyzer)
        else:
            self.normal_transform(source, analyzer)
        analyzer.update_funcspecs()  # Backfill to update function specifications

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
            style.name for style in IdentifierRenameUnit.Style
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
            {style.name: style for style in IdentifierRenameUnit.Style}[
                json_obj["style"]
            ],
            json_obj["minimise_idents"],
        )

    def __str__(self) -> str:
        """Create a readable string representation of the IdentifierRenameUnit.

        Returns:
            str: The readable string representation.
        """
        style_flag = f"style={self.style.name}"
        minimise_ident_flag = (
            f"minimal={'ENABLED' if self.minimise_idents else 'DISABLED'}"
        )
        return f"RenameIdentifiers({style_flag},{minimise_ident_flag})"


class IndexReverser(NodeVisitor):
    """An AST traversal class that performs index reversal obfuscation on a given AST."""

    def __init__(self, probability: float) -> None:
        """The constructor for the IndexReverse, storing its probability.

        Args:
            probability (float): The probability of index reversal (0-1).
        """
        self.probability = probability
        self.analyzer = None

    def visit_ArrayRef(self, node: ArrayRef) -> None:
        """Visit an ArrayRef AST node, probabilistically reversing the index by swapping
        the 'name' and 'subscript' fields of the node, and then continuing in-order tree
        traversal. This is only applied if the two expressions are not mutating, in order
        to enforce correct obfuscation.

        Args:
            node (ArrayRef): The AST node corresponding to the array reference.
        """
        if node.name is not None and not self.analyzer.is_mutating(node.name):
            if node.subscript is not None and not self.analyzer.is_mutating(
                node.subscript
            ):
                if random.random() < self.probability:
                    node.name, node.subscript = node.subscript, node.name
        NodeVisitor.generic_visit(self, node)

    def visit_FileAST(self, node: FileAST) -> None:
        """Visit a FileAST node (the program root), initialising the expression analyzer and
        using it to process the AST for use in the `visit_ArrayRef` method.

        Args:
            node (FileAST): The FileAST root node.
        """
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
    type = TransformType.LEXICAL

    def __init__(self, probability: float) -> None:
        """The constructor for the ReverseIndexUnit transformation.

        Args:
            probability (float): The probability of index reversal.
        """
        self.probability = probability
        self.traverser = IndexReverser(probability)

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        """Performs the index reversal transformation on the source.

        Args:
            source (interaction.CSource): The source code to transform.

        Returns:
            interaction.CSource: The transformed source code.
        """
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

    def __str__(self) -> str:
        """Create a readable string representation of the IndexReverseUnit.

        Returns:
            str: The readable string representation.
        """
        probability_flag = f"p={self.probability}"
        return f"ReverseIndexes({probability_flag})"


class ClutterWhitespaceUnit(ObfuscationUnit):
    """Implements simple source-level whitespace cluttering, breaking down the high-level abstraction of
    indentation and program structure by altering whitespace in the file."""

    name = "Clutter Whitespace"
    description = "Clutters program whitespace, making it difficult to read"
    extended_description = (
        "This transformation clutters the whitespace of a program, removing all indentation and spacing\n"
        "where possible between program lexemes. Currently, text is wrapped to fit roughly 100 characters\n"
        "per line, completely destroying symbolic code readability via whitespace. Note that this only\n"
        "affects the source code - no change will be made to the compiled code. Note that any non-textual\n"
        "transformations applied after this point will undo its changes."
    )
    type = TransformType.LEXICAL

    spaced_tokens = (
        pycparser.c_lexer.CLexer.keywords
        + pycparser.c_lexer.CLexer.keywords_new
        + ("ID",)
    )
    spaced_end_tokens = set(
        spaced_tokens
        + (
            "INT_CONST_DEC",
            "INT_CONST_OCT",
            "INT_CONST_HEX",
            "INT_CONST_BIN",
            "INT_CONST_CHAR",
            "FLOAT_CONST",
            "HEX_FLOAT_CONST",
        )
    )
    spaced_tokens = set(spaced_tokens)

    # Ambiguous lexemes are lexemes of two or more characters that can in some way be split up into
    # two other lexemes recognised by the program, such that those lexemes must be spaced so they are
    # not ambiguously greedily recognised as these larger lexemes.
    ambiguous_lexemes = set(
        [
            "+=",
            "-=",
            "*=",
            "/=",
            "%=",
            "&=",
            "|=",
            "^=",
            "<<=",
            ">>=",
            "++",
            "--",
            ">>",
            "<<",
            "==",
            "!=",
            "<=",
            ">=",
            "&&",
            "||",
            "->",
        ]
    )

    def __init__(self, target_length: int, pad_lines: bool):
        """The constructor for the ClutterWhitespaceUnit transformation.

        Args:
            target_length (int): The target max line length to clutter contents towards
            pad_lines (bool): Whether to pad tokens (with evenly distributed spacing)
            to exactly meet the target line length or not.
        """
        self.target_length = target_length
        self.pad_lines = pad_lines

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        """Performs the whitespace cluttering transformation on the given source program.

        Args:
            source (interaction.CSource): The source code to transform.

        Returns:
            interaction.CSource: The transformed source code.
        """

        # Preprocess contents to remove directives.
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

        # Build lexer and lex tokens
        lexer = pycparser.c_lexer.CLexer(
            lambda: None, lambda: None, lambda: None, lambda tok: None
        )
        lexer.build()
        lexer.input(contents)

        # Space out and pad tokens where appropriate
        cur_line_length = 0
        cur_line = []
        token = lexer.token()
        prev = None
        while token is not None:

            # We add a space if the previous and current token are of types enforcing a space
            # is requieed between the two (e.g. two identifiers), or if the combination of
            # the two would cause an ambiguous lexeme (e.g. - and > make ->).
            addSpace = prev is not None and (
                (
                    prev.type in self.spaced_tokens
                    and token.type in self.spaced_end_tokens
                )
                or prev.value + token.value in self.ambiguous_lexemes
            )

            cur_line_length += (1 if addSpace else 0) + len(token.value)
            if cur_line_length <= self.target_length:
                if addSpace:
                    cur_line.append(" ")
                cur_line.append(token.value)
            else:  # Current line has overflown
                cur_line_length -= (1 if addSpace else 0) + len(token.value)
                if len(cur_line) > 0 and cur_line_length <= self.target_length:
                    # If space is left over, we pad if required in random
                    # increments to spread padding out.
                    if self.pad_lines and len(cur_line) > 1:
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
                    # Line is overflowing but not empty - go to next line
                    cur_line.append("\n")
                    new_contents += "".join(cur_line)
                    cur_line = [token.value]
                    cur_line_length = len(token.value)
                else:
                    # Nothing else on line and token size > max -> Must overflow
                    new_contents += token.value + "\n"
                    cur_line = []
                    cur_line_length = 0

            prev = token
            token = lexer.token()

        # Cleanup for final line and return new CSource
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

    def __str__(self) -> str:
        """Create a readable string representation of the ClutterWhitespaceUnit.

        Returns:
            str: The readable string representation.
        """
        target_length_flag = f"target_len={self.target_length}"
        pad_flag = f"padding={'ENABLED' if self.pad_lines else 'DISABLED'}"
        return f"ClutterWhitespace({target_length_flag},{pad_flag})"


class DiTriGraphEncodeUnit(ObfuscationUnit):
    """Implements a string literal encoding (SLE) obfuscation transformation, which takes the
    input source code and encodes string literals in the code according to some encoding method
    such that the program still performs the same functionality, but strings can no longer be
    easily read in the code."""

    name = "Digraph/Trigraph Encoding"
    description = (
        "Encodes certain symbols with Digraphs/Trigraphs to make them incomprehensible"
    )
    extended_description = (
        "This transformation encodes certain symbols within the program (e.g. '{', '#', ']') as digraphs\n"
        "or trigraphs, which are respectively two- or three- character combinations that are replaced by\n"
        "C's preprocessor to allow keyboard with less symbols to type C programs. Note that this only affects\n"
        "the source code - no change will be made to the compiled code. Note that any non-textual\n"
        "transformations applied after this point will undo its changes.\n\n"
        "The first available option is the mapping type - you can choose to encode using only digraphs, only\n"
        "trigraphs, or a mixture of both digraphs and trigraphs. For the second option, you can choose the\n"
        "probability that an encoding takes place. 0.0 means no encoding, 0.5 means approximately half will\n"
        "be encoded, and 1.0 means all symbols are encoded. This can be used to achieve a mixture of digraphs,\n"
        "trigraphs and regular symbols as is desired."
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
        """An enumerator storing the different encoding styles."""

        DIGRAPH = "Digraphs"
        TRIGRAPH = "Trigraphs"
        MIXED = "Mixed Digraph/Trigraphs"

    def __init__(self, style: Style, chance: float):
        """The constructor for the DiTriGraphEncodeUnit transformation, storing the style
        of the transformation and the probability with which it is applied.

        Args:
            style (Style): The encoding style to use
            chance (float): The indepdendent probability (0-1) of encoding each symbol
        """
        self.style = style
        if chance < 0.0:
            self.chance = 0.0
        elif chance > 1.0:
            self.chance = 1.0
        else:
            self.chance = chance

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        """Performs the digraph / trigraph encoding transformation on the given source program.

        Args:
            source (interaction.CSource): The source code to transform.

        Returns:
            interaction.CSource: The transformed source code.
        """
        new_contents = ""
        prev = None
        str_top = None
        # Iterate through each character in the program
        for char in source.contents:

            # Determine when entering or existing a string.
            if (char == "'" or char == '"') and prev != "\\":
                if str_top is None:
                    str_top = char
                elif str_top == char:
                    str_top = None

            # Encode probabilistically, outside of strings
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

    def __str__(self) -> str:
        """Create a readable string representation of the DiTriGraphEncodeUnit.

        Returns:
            str: The readable string representation.
        """
        style_flag = f"style={self.style.name}"
        probability_flag = f"p={self.chance}"
        return f"DiTriGraphEncode({style_flag},{probability_flag})"
