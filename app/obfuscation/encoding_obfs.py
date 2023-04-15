""" File: obfuscation/encoding_obfs.py
Implements classes (including obfuscation unit classes) for performing
encoding obfuscation transformations, including obfuscation related
to the encoding of string literals and integer literals, as well as 
the encoding of integer arithmetic expressions/operations. 
"""
from .. import interaction
from ..debug import *
from .utils import ObfuscationUnit, TransformType, generate_new_contents
from .expression_analysis import ExpressionAnalyzer
from pycparser.c_ast import *
from typing import Optional
import random, json, math, enum, copy


class StringEncodeTraverser(NodeVisitor):
    """Traverses the program AST looking for string literals and encoding them into
    some incomprehensible form."""

    escape_chars = {
        "a": "'\\x07'",
        "b": "'\\x08'",
        "e": "'\\x1B'",
        "f": "'\\x0C'",
        "n": "'\\x0A'",
        "r": "'\\x0D'",
        "t": "'\\x09'",
        "v": "'\\x0B'",
        "\\": "'\\x5C'",
        "'": "'\\x27'",
        '"': "'\\x22'",
        "?": "'\\x3F'",
    }

    class Style(enum.Enum):
        """An enumerated type representing the available string encoding styles."""

        OCTAL = "Octal"
        HEX = "Hexadecimal"
        MIXED = "Octal/Hexadecimal"
        ALL = "Octal/Hex/Regular"

    def __init__(self, style: Style):
        """The constructor for StringEncodeTraverser objects, storing the encoding style.

        Args:
            style (Style): The encoding style to use when traversing & mutating ASTs.
        """
        self.style = style
        self.in_init_list = False

    def _represent_encoding(self, chars: list[str]) -> Node:
        """This method takes a given set of encoded characters, and probabilistically
        either encodes them using a (concatenated) string format or using an array
        (initializer list) format to represent the encoded string.

        Args:
            chars (list[str]): The list of encoded characters to diversify.

        Returns:
            Node: The final encoded string AST node.
        """
        if self.in_init_list or random.random() >= 0.5:
            # Use string encoding
            str_ = ""
            if len(chars) == 0:
                return Constant("string", '""')
            if len(chars) == 1:
                return Constant("string", '"{}"'.format(chars[0].value[1:-1]))
            prev_closed = True
            for char in chars:
                if prev_closed:
                    str_ += '"'
                elif char.value[1] != "\\":
                    str_ += '""'
                str_ += char.value[1:-1]
                prev_closed = random.random() >= 0.75
                if prev_closed:
                    str_ += '"'
            if not prev_closed:
                str_ += '"'
            return Constant("string", str_)
        # Use array (initializer list) encoding
        chars.append(Constant("char", "'\\0'"))
        return InitList(chars, None)

    def encode_string(self, node: Constant) -> Node:
        """Given an AST node representing a string constant, this method will encode
        the string using the user-specified encoding style. Specifically, it will
        randomly choose (with 50% chance) whether to perform direct string encoding
        or convert to a character list; the former will have string concatenation
        added at random valid points throughout.

        Args:
            node (Constant): The AST node of the string to encode

        Returns:
            str: The encoded string AST node
        """
        chars = []
        max_index = len(node.value) - 1
        check_next = False

        # Iterate through the string character by character
        for i, char in enumerate(node.value[1:-1]):

            # Detect and encode escape characters based on previous character combos
            if check_next:
                check_next = False
                if char in self.escape_chars:
                    char_node = Constant("char", self.escape_chars[char])
                    chars.append(char_node)
                    continue
                else:
                    return None
            # Specifically handle escaping of the escape character
            if char == "\\" and i != max_index:
                check_next = True
                continue

            # If using a mixed style, randoml pick an encoding style to use.
            if self.style == self.Style.MIXED:
                style = [self.Style.OCTAL, self.Style.HEX][random.randint(0, 1)]
            elif self.style == self.Style.ALL:
                style = [self.Style.OCTAL, self.Style.HEX, None][random.randint(0, 2)]
            else:
                style = self.style
            # Encode according to the chosen style
            if style == self.Style.OCTAL:
                octal_char = "'\\" + str(oct(ord(char)))[2:] + "'"
                char_node = Constant("char", octal_char)
            elif style == self.Style.HEX:
                hex_char = "'\\x" + str(hex(ord(char)))[2:] + "'"
                char_node = Constant("char", hex_char)
            else:
                char_node = Constant("char", "'" + char + "'")
            chars.append(char_node)

        return self._represent_encoding(chars)

    def _make_compound_literal(self, init_node: Node) -> CompoundLiteral:
        """Construct a CompoundLiteral subtree (a (char []) array to correctly
        store a given initializer list string encoding.

        Args:
            init_node (Node): The string expression node to compound.

        Returns:
            CompoundLiteral: The corresponding (char []) compound literal.
        """
        identifier_node = IdentifierType(["char"])
        type_decl_node = TypeDecl(None, [], None, identifier_node)
        array_type_node = ArrayDecl(type_decl_node, None, None)
        typename_node = Typename(None, [], None, array_type_node)
        return CompoundLiteral(typename_node, init_node)

    def visit_Decl(self, node: Decl) -> None:
        """Visits a Decl node, encoding any initialised string constant value and
        then recurisvely traversing the AST. Specficially handles array (initializer
        list) encodings in declarations by changing the character pointer type to
        declare an chater array type where appropriate."""
        if node.init is not None:
            if isinstance(node.init, Constant) and node.init.type == "string":
                encoded = self.encode_string(node.init)
                if encoded is not None:
                    node.init = encoded
                if isinstance(node.init, InitList) and isinstance(node.type, PtrDecl):
                    node.type = ArrayDecl(node.type.type, None, None)
        NodeVisitor.generic_visit(self, node)

    def visit_ExprList(self, node: ExprList) -> None:
        """Visits an ExprList node, encoding any string constant expression values,
        and then recursively traverses the AST."""
        for i, expr in enumerate(node.exprs):
            if isinstance(expr, Constant) and expr.type == "string":
                encoded = self.encode_string(expr)
                if encoded is not None:
                    if isinstance(encoded, InitList):
                        node.exprs[i] = self._make_compound_literal(encoded)
                    else:
                        node.exprs[i] = encoded
        NodeVisitor.generic_visit(self, node)

    def visit_InitList(self, node: InitList) -> None:
        """Visits an InitList node, encoding any string constant initializer expression
        value, and then recursively traversing the AST. For context we specifically track
        that we are in an initialiser list to enforce that no further nested layers of
        intiialiser lists are generated."""
        was_in_init_list = self.in_init_list
        self.in_init_list = True
        for i, expr in enumerate(node.exprs):
            if isinstance(expr, Constant) and expr.type == "string":
                encoded = self.encode_string(expr)
                if encoded is not None:
                    node.exprs[i] = encoded
        NodeVisitor.generic_visit(self, node)
        self.in_init_list = was_in_init_list

    def visit_NamedInitializer(self, node: NamedInitializer) -> None:
        """Visits a NamedInitializer AST node, encoding any string constant expression
        value, and then recursively traversing the AST. As we must be in an intialiser list
        to visit a NamedInitializer, we do not check whether make a compound literal."""
        if node.expr is not None:
            if isinstance(node.expr, Constant) and node.expr.type == "string":
                encoded = self.encode_string(node.expr)
                if encoded is not None:
                    node.expr = encoded
        NodeVisitor.generic_visit(self, node)

    def generic_visit(self, node: Node) -> None:
        """Visit a generic node, checking if its type is one of many valid types, and if so,
        checking if the node stores a valid string constant. If such a constant is stored,
        this method then encodes the string, mutating the attribute value, and consturcting
        a compound literal if necessary if the InitList representation is chosen."""
        string_attrs = {
            ArrayRef: ["name"],
            TernaryOp: ["iftrue", "iffalse"],
            BinaryOp: ["left", "right"],
            UnaryOp: ["expr"],
            If: ["cond"],
            While: ["cond"],
            DoWhile: ["cond"],
        }
        if not isinstance(node, tuple(string_attrs.keys())):
            return super().generic_visit(node)
        for attr in string_attrs[type(node)]:
            if not hasattr(node, attr):
                continue
            val = getattr(node, attr)
            if isinstance(val, Constant) and val.type == "string":
                encoded = self.encode_string(val)
                if encoded is not None:
                    if isinstance(encoded, InitList):
                        setattr(node, attr, self._make_compound_literal(encoded))
                    else:
                        setattr(node, attr, encoded)
        return super().generic_visit(node)


class StringEncodeUnit(ObfuscationUnit):
    """Implements a string literal encoding (SLE) obfuscation transformation, which takes the
    input source code and encodes string literals in the code according to some encoding method
    such that the program still performs the same functionality, but strings can no longer be
    easily read in the code."""

    name = "String Literal Encoding"
    description = "Encodes string literals to make them incomprehensible"
    extended_description = (
        "This transformation encodes literal strings as a sequence of obfuscated characters,\n"
        "in order to make strings incomprehensible and hide their true meaning. Depending on\n"
        "the mode selected, characters can be encoded as hexadecimal character codes, octal\n"
        "character codes, or a mix of these and regular characters.\n\n"
        "The only input is the encoding style to use."
    )
    type = TransformType.ENCODING

    def __init__(self, style: StringEncodeTraverser.Style):
        """The constructor for the StringEncodeUnit transformation.

        Args:
            style (StringEncodeTraverser.Style): The string encoding style to use.
        """
        self.style = style
        self.traverser = StringEncodeTraverser(style)

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        """Performs the string encoding transformation on the given source program.

        Args:
            source (interaction.CSource): The source code to transform.

        Returns:
            interaction.CSource: The transformed source code.
        """
        self.traverser.visit(source.t_unit)
        new_contents = generate_new_contents(source)
        return interaction.CSource(source.fpath, new_contents, source.t_unit)

    def to_json(self) -> str:
        """Converts the string encoding unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps({"type": str(__class__.name), "style": self.style.name})

    def from_json(json_str: str) -> Optional["StringEncodeUnit"]:
        """Converts the provided JSON string to a string encoding transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding string encoding unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load StringEncode() - invalid JSON provided.", print_err=True
            )
            return None
        if "type" not in json_obj:
            log("Failed to load StringEncode() - no type provided.", print_err=True)
            return None
        elif json_obj["type"] != __class__.name:
            log("Failed to load StringEncode() - class/type mismatch.", print_err=True)
            return None
        elif "style" not in json_obj:
            log(
                "Failed to load StringEncode() - no style value provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["style"], str):
            log(
                "Failed to load StringEncode() - style is not a valid string.",
                print_err=True,
            )
            return None
        elif json_obj["style"] not in [
            style.name for style in StringEncodeTraverser.Style
        ]:
            log(
                "Failed to load StringEncode() - style '{}' is not a valid style.".format(
                    json_obj["style"]
                ),
                print_err=True,
            )
            return None
        return StringEncodeUnit(
            {style.name: style for style in StringEncodeTraverser.Style}[
                json_obj["style"]
            ]
        )

    def __str__(self) -> str:
        """Create a readable string representation of the StringEncodeUnit.

        Returns:
            str: The readable string representation.
        """
        style_flag = f"style={self.style.name}"
        return f"StringEncode({style_flag})"


class IntegerEncodeTraverser(NodeVisitor):
    """Traverses the program AST looking for integer literals and encoding them into
    some incomprehensible form."""

    def simple_encode(self, child: Constant) -> BinaryOp:
        """Performs simple integer encoding, taking a given constant integer AST node
        and returning an arithmetic expression subtree that evaluates to the same constant.
        Specifically encodes some integer f(i) = a * i + b, encoding f(i) as a * i + b.

        Args:
            child (Constant): The integer constant to transform.

        Returns:
            BinaryOp: The arithmetic expression subtree evaluating to the same content.
        """
        value = int(child.value)
        if abs(value) > 1000:
            # For large numbers, we bound at square root to avoid representation bit issues
            upper_bound = math.floor(math.sqrt(abs(value)))
            lower_bound = upper_bound // 3
            mul_const = random.randint(lower_bound, upper_bound)
            encoded_val = value // mul_const
            add_const = value % mul_const
        else:
            # Otherwise, we choose random medimum-sized numbers
            mul_const = random.randint(5, 10000)
            encoded_val = random.randint(5, 10000)
            add_const = value - mul_const * encoded_val

        # From our generated and calculated constant values, we define an expression subtree
        # that will provide the equivalent constant value.
        mul_const_node = Constant("int", mul_const)
        encoded_node = Constant("int", encoded_val)
        add_const_node = Constant("int", abs(add_const))
        mul_node = BinaryOp("*", mul_const_node, encoded_node)
        if add_const >= 0:
            add_node = BinaryOp("+", mul_node, add_const_node)
        else:
            add_node = BinaryOp("-", mul_node, add_const_node)
        return add_node

    def generic_visit(self, node: Node) -> None:
        """Visits any generic AST node, checking if the node has a child that is some
        constant integer. If so, then the child is encoded and replaced by the
        equivalent subtree, with the relevant attribute being set. Nodes are traverse in
        post-order to avoid infinite behaviour arising from parsing constants within
        encoded constant expression subtrees.

        Args:
            node (Node): The AST node to traverse (pre-order traversal)
        """
        NodeVisitor.generic_visit(self, node)
        for child in node.children():
            if isinstance(child[1], Constant) and child[1].type == "int":
                new_child = self.simple_encode(child[1])
                if new_child is not None:
                    parts = [p[:-1] if p[-1] == "]" else p for p in child[0].split("[")]
                    if len(parts) == 1:
                        setattr(node, child[0], new_child)
                    else:
                        getattr(node, parts[0])[int(parts[1])] = new_child


class IntegerEncodeUnit(ObfuscationUnit):
    """Implements an integer literal encoding (LE) obfuscation transformation, which takes the
    input source code and encodes integer literals in the code according to some encoding method
    such that the program still performs the same functionality, but integer constants can no longer
    be easily read in code. We only encode integers and not floats due to necessary precision."""

    name = "Integer Literal Encoding"
    description = "Encode integer literals to make them hard to determine"
    extended_description = (
        "This transformation encodes literal integer constants in the code as the result of\n"
        "some computation, making it harder to determine the meaning of the code from the values\n"
        "of integers used. Note that the current implementation only allows simple encoding, which\n"
        "can be easily automatically optimised out, and so currently only served to obfuscate source\n"
        "code and to augment other obfuscations such as arithmetic encoding.\n\n"
        "The only input is the integer encoding style to use, though only simple encoding is available now.\n\n"
        "WARNING: Do not use this method if you have any implicit casts from constants to pointers (e.g. in a\n"
        "function call. For example, `int *m = 0;` might seem harmless as a null pointer, but then even though\n"
        "`int *m = 1 - 1;` seems equivalent and should be folded to the same behaviour, many compilers will\n"
        "complain about this implcit typecast. So be careful! Or use e.g. `int *m = (void *) 0;` if needed."
    )
    type = TransformType.ENCODING

    def __init__(self) -> None:
        """The constructor for the IntegerEncodeUnit transformation, which simply instantiates the traverser."""
        self.traverser = IntegerEncodeTraverser()

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        """Performs the integer encoding transformation on the given source program.

        Args:
            source (interaction.CSource): The source code to transform.

        Returns:
            interaction.CSource: The transformed source code.
        """
        self.traverser.visit(source.t_unit)
        new_contents = generate_new_contents(source)
        return interaction.CSource(source.fpath, new_contents, source.t_unit)

    def to_json(self) -> str:
        """Converts the integer encoding unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps({"type": str(__class__.name)})

    def from_json(json_str: str) -> Optional["IntegerEncodeUnit"]:
        """Converts the provided JSON string to an integer encoding transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding integer encoding unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load IntegerEncode() - invalid JSON provided.",
                print_err=True,
            )
            return None
        if "type" not in json_obj:
            log("Failed to load IntegerEncode() - no type provided.", print_err=True)
            return None
        elif json_obj["type"] != __class__.name:
            log("Failed to load IntegerEncode() - class/type mismatch.", print_err=True)
            return None
        return IntegerEncodeUnit()

    def __str__(self) -> str:
        """Create a readable string representation of the IntegerEncodeUnit.

        Returns:
            str: The readable string representation.
        """
        return f"IntegerEncode()"


class ArithmeticEncodeTraverser(NodeVisitor):
    """Traverses a given AST and performs arithmetic encoding, checking whether a given expression
    can be encoded (valid operator, integer operands, non-mutable expression) and then mutating
    the AST to perform the encoding."""

    # The list of unary boolean arithmetic identities that can be substituted
    unary_subs = {
        "-": [
            lambda n: BinaryOp(
                "+", UnaryOp("~", copy.deepcopy(n.expr)), Constant("int", "1")
            ),  # -x = ¬x + 1
            lambda n: UnaryOp(
                "~", BinaryOp("-", copy.deepcopy(n.expr), Constant("int", "1"))
            ),  # -x = ¬(x - 1)
        ],
        "~": [
            lambda n: BinaryOp(
                "-", UnaryOp("-", copy.deepcopy(n.expr)), Constant("int", "1")
            ),  # ¬x = -x - 1
        ],
    }

    # The list of binary boolean arithmetic identities that can be substituted
    binary_subs = {
        "+": [
            lambda n: BinaryOp(  # x + y = x - ¬y - 1
                "-",
                BinaryOp(
                    "-", copy.deepcopy(n.left), UnaryOp("~", copy.deepcopy(n.right))
                ),
                Constant("int", "1"),
            ),
            lambda n: BinaryOp(  # x + y = (x ^ y) + 2 * (x & y)
                "+",
                BinaryOp("^", copy.deepcopy(n.left), copy.deepcopy(n.right)),
                BinaryOp(
                    "<<",
                    BinaryOp("&", copy.deepcopy(n.left), copy.deepcopy(n.right)),
                    Constant("int", "1"),
                ),
            ),
            lambda n: BinaryOp(  # x + y = (x | y) + (x & y)
                "+",
                BinaryOp("|", copy.deepcopy(n.left), copy.deepcopy(n.right)),
                BinaryOp("&", copy.deepcopy(n.left), copy.deepcopy(n.right)),
            ),
            lambda n: BinaryOp(  # x + y = 2 * (x | y) - (x ^ y)
                "-",
                BinaryOp(
                    "<<",
                    BinaryOp("|", copy.deepcopy(n.left), copy.deepcopy(n.right)),
                    Constant("int", "1"),
                ),
                BinaryOp("^", copy.deepcopy(n.left), copy.deepcopy(n.right)),
            ),
        ],
        "-": [
            lambda n: BinaryOp(  # x - y = x + ¬y + 1
                "+",
                BinaryOp(
                    "+", copy.deepcopy(n.left), UnaryOp("~", copy.deepcopy(n.right))
                ),
                Constant("int", "1"),
            ),
            lambda n: BinaryOp(  # x - y = (x ^ y) - 2 * (¬x & y)
                "-",
                BinaryOp("^", copy.deepcopy(n.left), copy.deepcopy(n.right)),
                BinaryOp(
                    "<<",
                    BinaryOp(
                        "&", UnaryOp("~", copy.deepcopy(n.left)), copy.deepcopy(n.right)
                    ),
                    Constant("int", "1"),
                ),
            ),
            lambda n: BinaryOp(  # x - y = (x & ¬y) - (¬x & y)
                "-",
                BinaryOp(
                    "&", copy.deepcopy(n.left), UnaryOp("~", copy.deepcopy(n.right))
                ),
                BinaryOp(
                    "&", UnaryOp("~", copy.deepcopy(n.left)), copy.deepcopy(n.right)
                ),
            ),
            lambda n: BinaryOp(  # x - y = 2 * (x & ¬y) - (x ^ y)
                "-",
                BinaryOp(
                    "<<",
                    BinaryOp(
                        "&", copy.deepcopy(n.left), UnaryOp("~", copy.deepcopy(n.right))
                    ),
                    Constant("int", "1"),
                ),
                BinaryOp("^", copy.deepcopy(n.left), copy.deepcopy(n.right)),
            ),
        ],
        "^": [
            lambda n: BinaryOp(  # x ^ y = (x | y) - (x & y)
                "-",
                BinaryOp("|", copy.deepcopy(n.left), copy.deepcopy(n.right)),
                BinaryOp("&", copy.deepcopy(n.left), copy.deepcopy(n.right)),
            ),
        ],
        "|": [
            lambda n: BinaryOp(  # x | y = (x & ¬y) + y
                "+",
                BinaryOp(
                    "&", copy.deepcopy(n.left), UnaryOp("~", copy.deepcopy(n.right))
                ),
                copy.deepcopy(n.right),
            ),
        ],
        "&": [
            lambda n: BinaryOp(  # x & y = (¬x | y) - ¬x
                "-",
                BinaryOp(
                    "|", UnaryOp("~", copy.deepcopy(n.left)), copy.deepcopy(n.right)
                ),
                UnaryOp("~", copy.deepcopy(n.left)),
            ),
        ],
    }

    def __init__(self, transform_depth: int):
        """The constructor for the ArithmeticEncodeTraverser class.

        Args:
            transform_depth (int): The recursive depth to perform arithmetic encoding to
            (i.e. how many encodes within encodes).
        """
        self.transform_depth = transform_depth
        self.analyzer = None

    def generic_visit(self, node: Node) -> None:
        """Performs a pre-order traversal of an AST to perform recursive arithmetic
        encoding on the tree. Takes a given tree node, and determines whether it
        has any children that are unary or binary operations. If so, it uses analysis
        tools to determine whether the expression takes integer operands that do not
        cause any side effects in the program (no mutability). If all these conditions
        are met, then a random substitution function is chosen and used to generate
        a subtree that will replace the expression. This is applied recursively 'n'
        times until the depth limit 'n' is reached.

        Args:
            node (Node): The AST node to traverse.
        """
        NodeVisitor.generic_visit(self, node)

        for child in node.children():
            # Check for unary/binary operation children that take integer operands and
            # don't cause side effects
            if isinstance(child[1], (UnaryOp, BinaryOp)):
                current = child[1]
                if not self.analyzer.is_type(
                    current, ExpressionAnalyzer.SimpleType.INT
                ):
                    continue
                if self.analyzer.is_mutating(current):
                    continue

                # Apply recursive arithmetic encoding transformation, choosing a random
                # substitution option each time.
                applied_count = 0
                while applied_count < self.transform_depth:
                    if (
                        isinstance(current, UnaryOp)
                        and current.op not in self.unary_subs
                    ) or (
                        isinstance(current, BinaryOp)
                        and current.op not in self.binary_subs
                    ):
                        break
                    if isinstance(current, UnaryOp):
                        options = self.unary_subs[current.op]
                    else:
                        options = self.binary_subs[current.op]
                    chosen_func = options[random.randint(0, len(options) - 1)]
                    current = chosen_func(current)

                    # Set the relevant node attribute to mutate the AST
                    parts = [p[:-1] if p[-1] == "]" else p for p in child[0].split("[")]
                    if len(parts) == 1:
                        setattr(node, child[0], current)
                    else:
                        getattr(node, parts[0])[int(parts[1])] = current
                    applied_count += 1

    def visit_FileAST(self, node: FileAST) -> None:
        """Visits a FileAST (root) node, creating an expression analyzer to determine
        the type and mutability of expressions in the program, before perform a
        pre-order traversal of the AST."""
        self.analyzer = ExpressionAnalyzer(node)
        self.analyzer.process()
        NodeVisitor.generic_visit(self, node)
        self.analyzer = None


class ArithmeticEncodeUnit(ObfuscationUnit):
    """Implements an arithmetic encoding obfuscation transformation, which takes the
    input source code and encodes integer arithmetic in the code according to some encoding method
    such that the program still performs the same functionality, but arithmetic can no longer
    be easily read in code. We only encode integers and not floats due to necessary precision."""

    name = "Integer Arithmetic Encoding"
    description = "Encode integer variable arithmetic to make code less comprehensible"
    extended_description = (
        "This transformation encodes arithmetic operations within the code, replacing simple\n"
        "additions and multipliations with compound combinations of bitwise operations and\n"
        "alternative arithmetic. When performed on arithmetic dependent upon inputs, this cannot be\n"
        "optimised out by a compiler and will greatly increase obfuscation.\n\n"
        "The only available option is the encoding depth - arithmetic operations within encoded\n"
        "arithmetic operations can be recursively encoded to increase code complexity, and so depth\n"
        "refers to the maximum recursive encoding depth that is allowed. A value > 5 is not recommended\n"
        "due to the potential slowdown."
    )
    type = TransformType.ENCODING

    def __init__(self, level: int):
        """The constructor for the ArithmeticEncodeUnit transformation.

        Args:
            level (int): The recursive depth of arithmetic encoding (how many times
            to perform expression substitution per individual expression).
        """
        self.level = level
        self.traverser = ArithmeticEncodeTraverser(level)

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        """Performs the arithmetic encoding transformation on the given source program.

        Args:
            source (interaction.CSource): The source code to transform.

        Returns:
            interaction.CSource: The transformed source code.
        """
        self.traverser.visit(source.t_unit)
        new_contents = generate_new_contents(source)
        return interaction.CSource(source.fpath, new_contents, source.t_unit)

    def to_json(self) -> str:
        """Converts the arithmetic encoding unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps({"type": str(__class__.name), "depth": self.level})

    def from_json(json_str: str) -> Optional["ArithmeticEncodeUnit"]:
        """Converts the provided JSON string to an arithmetic encoding transformation, if possible.

        Args:
            json_str (str): The JSON string to attempt to load.

        Returns:
            The corresponding arithmetic encoding unit object if the given json is valid, or None otherwise."""
        try:
            json_obj = json.loads(json_str)
        except:
            log(
                "Failed to load ArithmeticEncode() - invalid JSON provided.",
                print_err=True,
            )
            return None
        if "type" not in json_obj:
            log("Failed to load ArithmeticEncode() - no type provided.", print_err=True)
            return None
        elif json_obj["type"] != __class__.name:
            log(
                "Failed to load ArithmeticEncode() - class/type mismatch.",
                print_err=True,
            )
            return None
        elif "depth" not in json_obj:
            log(
                "Failed to load ArithmeticEncode() - no depth value provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["depth"], int):
            log(
                "Failed to load ArithmeticEncode() - depth is not a valid integer.",
                print_err=True,
            )
            return None
        elif json_obj["depth"] < 0:
            log(
                "Failed to load ArithmeticEncode() - depth must be >= 0.",
                print_err=True,
            )
            return None
        return ArithmeticEncodeUnit(json_obj["depth"])

    def __str__(self) -> str:
        """Create a readable string representation of the ArithmeticEncodeUnit.

        Returns:
            str: The readable string representation.
        """
        level_flag = f"depth={self.level}"
        return f"ArithmeticEncode({level_flag})"
