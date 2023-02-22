""" File: obfuscation/encoding_obfs.py
Implements classes (including obfuscation unit classes) for performing
encoding obfuscation transformations, including obfuscation related
to the encoding of string literals and integer literals, as well as 
the encoding of integer arithmetic expressions/operations. 
"""
from .. import interaction
from ..debug import *
from .utils import ObfuscationUnit, TransformType, generate_new_contents, ExpressionAnalyzer
from pycparser.c_ast import *
from typing import Optional
import random, json, math, enum


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

    TO_REMOVE = True

    class Style(enum.Enum):
        OCTAL = "Octal"
        HEX = "Hexadecimal"
        MIXED = "Octal/Hexadecimal"
        ALL = "Octal/Hex/Regular"

    def __init__(self, style):
        self.style = style
        self.__reset()
        
    def __reset(self):
        self.in_init_list = False

    def encode_string(self, node):
        chars = []
        max_index = len(node.value) - 1
        check_next = False
        for i, char in enumerate(node.value[1:-1]):
            if check_next:
                check_next = False
                if char in self.escape_chars:
                    char_node = Constant("char", self.escape_chars[char])
                    chars.append(char_node)
                    continue
                else:
                    return None
            if char == "\\" and i != max_index:
                check_next = True
                continue
            if self.style == self.Style.MIXED:
                style = [self.Style.OCTAL, self.Style.HEX][random.randint(0, 1)]
            elif self.style == self.Style.ALL:
                style = [self.Style.OCTAL, self.Style.HEX, None][random.randint(0, 2)]
            else:
                style = self.style
            if style == self.Style.OCTAL:
                octal_char = "'\\" + str(oct(ord(char)))[2:] + "'"
                char_node = Constant("char", octal_char)
            elif style == self.Style.HEX:
                hex_char = "'\\x" + str(hex(ord(char)))[2:] + "'"
                char_node = Constant("char", hex_char)
            else:
                char_node = Constant("char", "'" + char + "'")
            chars.append(char_node)
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
                elif char.value[1] != '\\':
                    str_ += '""'
                str_ += char.value[1:-1]
                prev_closed = random.random() >= 0.75
                if prev_closed:
                    str_ += '"'
            if not prev_closed:
                str_ += '"'
            return Constant("string", str_)
        # Use array (initializer list) encoding
        chars.append(
            Constant("char", "'\\0'")
        )
        return InitList(chars, None)

    def make_compound_literal(self, init_node):
        identifier_node = IdentifierType(["char"])
        type_decl_node = TypeDecl(None, [], None, identifier_node)
        array_type_node = ArrayDecl(type_decl_node, None, None)
        typename_node = Typename(None, [], None, array_type_node)
        return CompoundLiteral(typename_node, init_node)

    def visit_Decl(self, node):
        if node.init is not None:
            if isinstance(node.init, Constant) and node.init.type == "string":
                encoded = self.encode_string(node.init)
                if encoded is not None:
                    node.init = encoded
                if isinstance(node.init, InitList) and isinstance(node.type, PtrDecl):
                    # TODO is this 100% correct? Seems like it might not be;
                    # may need to do some recursive changing? or maybe not?
                    node.type = ArrayDecl(node.type.type, None, None)
        NodeVisitor.generic_visit(self, node)

    def visit_ExprList(self, node):
        for i, expr in enumerate(node.exprs):
            if isinstance(expr, Constant) and expr.type == "string":
                encoded = self.encode_string(expr)
                if encoded is not None:
                    if isinstance(encoded, InitList):
                        node.exprs[i] = self.make_compound_literal(encoded)
                    else:
                        node.exprs[i] = encoded
        NodeVisitor.generic_visit(self, node)

    def visit_InitList(self, node):
        was_in_init_list = self.in_init_list
        self.in_init_list = True
        for i, expr in enumerate(node.exprs):
            if isinstance(expr, Constant) and expr.type == "string":
                encoded = self.encode_string(expr)
                if encoded is not None:
                    node.exprs[i] = encoded
        NodeVisitor.generic_visit(self, node)
        self.in_init_list = was_in_init_list

    def visit_ArrayRef(self, node):
        if node.name is not None:
            if isinstance(node.name, Constant) and node.name.type == "string":
                encoded = self.encode_string(node.name)
                if encoded is not None:
                    if isinstance(encoded, InitList):
                        node.name = self.make_compound_literal(encoded)
                    else:
                        node.name = encoded
        NodeVisitor.generic_visit(self, node)

    def visit_NamedInitializer(self, node):
        if node.expr is not None:
            if isinstance(node.expr, Constant) and node.expr.type == "string":
                encoded = self.encode_string(node.expr)
                if encoded is not None:
                    node.expr = encoded
        NodeVisitor.generic_visit(self, node)

    def visit_TernaryOp(self, node):
        if node.iftrue is not None:
            if isinstance(node.iftrue, Constant) and node.iftrue.type == "string":
                encoded = self.encode_string(node.iftrue)
                if encoded is not None:
                    if isinstance(encoded, InitList):
                        node.iftrue = self.make_compound_literal(encoded)
                    else:
                        node.iftrue = encoded
        if node.iffalse is not None:
            if isinstance(node.iffalse, Constant) and node.iffalse.type == "string":
                encoded = self.encode_string(node.iffalse)
                if encoded is not None:
                    if isinstance(encoded, InitList):
                        node.iffalse = self.make_compound_literal(encoded)
                    else:
                        node.iffalse = encoded
        NodeVisitor.generic_visit(self, node)

    def visit_BinaryOp(self, node):
        if node.left is not None:
            if isinstance(node.left, Constant) and node.left.type == "string":
                encoded = self.encode_string(node.left)
                if encoded is not None:
                    if isinstance(encoded, InitList):
                        node.left = self.make_compound_literal(encoded)
                    else:
                        node.left = encoded
        if node.right is not None:
            if isinstance(node.right, Constant) and node.right.type == "string":
                encoded = self.encode_string(node.right)
                if encoded is not None:
                    if isinstance(encoded, InitList):
                        node.right = self.make_compound_literal(encoded)
                    else:
                        node.right = encoded
        NodeVisitor.generic_visit(self, node)

    def visit_UnaryOp(self, node):
        if node.expr is not None:
            if isinstance(node.expr, Constant) and node.expr.type == "string":
                encoded = self.encode_string(node.expr)
                if encoded is not None:
                    if isinstance(encoded, InitList):
                        node.expr = self.make_compound_literal(encoded)
                    else:
                        node.expr = encoded
        NodeVisitor.generic_visit(self, node)

    def visit_If(self, node):
        if node.cond is not None:
            if isinstance(node.cond, Constant) and node.cond.type == "string":
                encoded = self.encode_string(node.cond)
                if encoded is not None:
                    if isinstance(encoded, InitList):
                        node.cond = self.make_compound_literal(encoded)
                    else:
                        node.cond = encoded
        NodeVisitor.generic_visit(self, node)

    def visit_While(self, node):
        if node.cond is not None:
            if isinstance(node.cond, Constant) and node.cond.type == "string":
                encoded = self.encode_string(node.cond)
                if encoded is not None:
                    if isinstance(encoded, InitList):
                        node.cond = self.make_compound_literal(encoded)
                    else:
                        node.cond = encoded
        NodeVisitor.generic_visit(self, node)

    def visit_DoWhile(self, node):
        if node.cond is not None:
            if isinstance(node.cond, Constant) and node.cond.type == "string":
                encoded = self.encode_string(node.cond)
                if encoded is not None:
                    if isinstance(encoded, InitList):
                        node.cond = self.make_compound_literal(encoded)
                    else:
                        node.cond = encoded
        NodeVisitor.generic_visit(self, node)


class StringEncodeUnit(ObfuscationUnit):
    """Implements a string literal encoding (SLE) obfuscation transformation, which takes the
    input source code and encodes string literals in the code according to some encoding method
    such that the program still performs the same functionality, but strings can no longer be
    easily read in the code."""

    name = "String Literal Encoding"
    description = "Encodes string literals to make them incomprehensible"
    extended_description = (
        """This transformation encodes literal strings as a sequence of obfuscated characters,\n"""
        """in order to make strings incomprehensible and hide their true meaning. Depending on\n"""
        """the mode selected, characters can be encoded as hexadecimal character codes, octal\n"""
        """character codes, or a mix of these and regula characters.\n\n"""
        """The only input is the encoding style to use."""
    )
    type = TransformType.ENCODING

    def __init__(self, style):
        self.style = style
        self.traverser = StringEncodeTraverser(style)

    def transform(self, source: interaction.CSource) -> interaction.CSource:
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

    def __str__(self):
        style_flag = f"style={self.style.name}"
        return f"StringEncode({style_flag})"


class IntegerEncodeTraverser(NodeVisitor):
    """TODO"""

    class Style(enum.Enum):
        SIMPLE = "Simple Encoding (Multiply-Add)"
        MBA_SIMPLE = "Simple Mixed-Boolean Arithmetic Constant Hiding without Polynomial Transforms (Not Yet Implemented)"
        MBA_POLYNOMIAL = "Mixed-Boolean Arithmetic Constant Hiding with Polynomial Transforms (Not Yet Implemented)"
        # MBA_ALGORITHMIC = "Mixed-Boolean Arithmetic Hiding via. Algorithmic Encoding (Not Yet Implemented)"
        # SPLIT = "Split Integer Literals (Not Yet Implemented)"

    def __init__(self, style):
        self.style = style
        self.ignore = set()

    def simple_encode(self, child):
        # Form f(i) = a * i + b to encode f(i) as i.
        value = int(child.value)
        if abs(value) > 1000:
            upper_bound = math.floor(math.sqrt(abs(value)))
            lower_bound = upper_bound // 3
            mul_const = random.randint(lower_bound, upper_bound)
            encoded_val = value // mul_const
            add_const = value % mul_const
        else:
            mul_const = random.randint(3000, 10000)
            encoded_val = random.randint(3000, 10000)
            add_const = value - mul_const * encoded_val
        mul_const_node = Constant("int", mul_const)
        encoded_node = Constant("int", encoded_val)
        add_const_node = Constant("int", abs(add_const))
        mul_node = BinaryOp("*", mul_const_node, encoded_node)
        if add_const >= 0:
            add_node = BinaryOp("+", mul_node, add_const_node)
        else:
            add_node = BinaryOp("-", mul_node, add_const_node)
        return add_node

    def mba_simple_encode(self, child):
        # v = int(child.value)
        # left_expr = BinaryOp("||", Constant("int", str(-v - 1)))
        # TODO in future
        pass

    def mba_polynomial_encode(self, child):
        # TODO in future
        pass

    def encode_int(self, child):
        if self.style == self.Style.SIMPLE:
            encoded = self.simple_encode(child)
            self.ignore.add(encoded)
            return encoded
        elif self.style == self.Style.MBA_SIMPLE:
            encoded = self.mba_simple_encode(child)
            self.ignore.add(encoded)
            return encoded
        elif self.style == self.Style.MBA_POLYNOMIAL:
            encoded = self.mba_polynomial_encode(child)
            self.ignore.add(encoded)
            return encoded

    def generic_visit(self, node):
        if node in self.ignore:
            return
        for child in node.children():
            if isinstance(child[1], Constant) and child[1].type == "int":
                new_child = self.encode_int(child[1])
                if new_child is not None:
                    parts = [p[:-1] if p[-1] == "]" else p for p in child[0].split("[")]
                    if (
                        len(parts) == 1
                    ):  # TODO this will be broke wherever else I did this also
                        setattr(node, child[0], new_child)
                    else:
                        getattr(node, parts[0])[int(parts[1])] = new_child
        NodeVisitor.generic_visit(self, node)

    def visit_FileAST(self, node):
        NodeVisitor.generic_visit(self, node)
        self.ignore = set()


class IntegerEncodeUnit(ObfuscationUnit):
    """Implements an integer literal encoding (LE) obfuscation transformation, which takes the
    input source code and encodes integer literals in the code according to some encoding method
    such that the program still performs the same functionality, but integer constants can no longer
    be easily read in code. We only encode literals and not floats due to necessary precision."""

    name = "Integer Literal Encoding"
    description = "Encode integer literals to make them hard to determine"
    extended_description = (
        """This transformation encodes literal integer constants in the code as the result of\n"""
        """some computation, making it harder to determine the meaning of the code from the values\n"""
        """of integers used. Note that the current implementation only allows simple encoding, which\n"""
        """can be easily automatically optimised out, and so currently only served to obfuscate source\n"""
        """code and to augment other obfuscations such as arithmetic encoding.\n\n"""
        """The only input is the integer encoding style to use, though only simple encoding is available now."""
    )
    type = TransformType.ENCODING

    def __init__(self, style):
        self.style = style
        self.traverser = IntegerEncodeTraverser(style)

    def transform(self, source: interaction.CSource) -> interaction.CSource:
        self.traverser.visit(source.t_unit)
        new_contents = generate_new_contents(source)
        return interaction.CSource(source.fpath, new_contents, source.t_unit)

    def to_json(self) -> str:
        """Converts the integer encoding unit to a JSON string.

        Returns:
            (str) The corresponding serialised JSON string."""
        return json.dumps({"type": str(__class__.name), "style": self.style.name})

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
        elif "style" not in json_obj:
            log(
                "Failed to load IntegerEncode() - no style value provided.",
                print_err=True,
            )
            return None
        elif not isinstance(json_obj["style"], str):
            log(
                "Failed to load IntegerEncode() - style is not a valid string.",
                print_err=True,
            )
            return None
        elif json_obj["style"] not in [
            style.name for style in IntegerEncodeTraverser.Style
        ]:
            log(
                "Failed to load IntegerEncode() - style '{}' is not a valid style.".format(
                    json_obj["style"]
                ),
                print_err=True,
            )
            return None
        return IntegerEncodeUnit(
            {style.name: style for style in IntegerEncodeTraverser.Style}[
                json_obj["style"]
            ]
        )

    def __str__(self) -> str:
        style_flag = f"style={self.style.name}"
        return f"IntegerEncode({style_flag})"


class ArithmeticEncodeTraverser(NodeVisitor):
    """TODO"""

    def __init__(self, transform_depth: int):
        self.transform_depth = transform_depth
        self.reset()

    def reset(self):
        self.ignore_list = set()
        self.analyzer = None

    unary_subs = {
        "-": [
            lambda n: BinaryOp(
                "+", UnaryOp("~", n.expr), Constant("int", "1")
            ),  # -x = ¬x + 1
            lambda n: UnaryOp(
                "~", BinaryOp("-", n.expr, Constant("int", "1"))
            ),  # -x = ¬(x - 1)
        ],
        "~": [
            lambda n: BinaryOp(
                "-", UnaryOp("-", n.expr), Constant("int", "1")
            ),  # ¬x = -x - 1
        ],
    }

    # TODO can llvm detect and optimise some of these (see O-MVLL). If so, how can we stop this?
    binary_subs = {
        "+": [
            lambda n: BinaryOp(  # x + y = x - ¬y - 1
                "-", BinaryOp("-", n.left, UnaryOp("~", n.right)), Constant("int", "1")
            ),
            # TODO for these left shifts, is it correct if an argument is negative as well?
            lambda n: BinaryOp(  # x + y = (x ^ y) + 2 * (x & y)
                "+",
                BinaryOp("^", n.left, n.right),
                BinaryOp("<<", BinaryOp("&", n.left, n.right), Constant("int", "1")),
            ),
            lambda n: BinaryOp(  # x + y = (x | y) + (x & y)
                "+", BinaryOp("|", n.left, n.right), BinaryOp("&", n.left, n.right)
            ),
            lambda n: BinaryOp(  # x + y = 2 * (x | y) - (x ^ y)
                "-",
                BinaryOp("<<", BinaryOp("|", n.left, n.right), Constant("int", "1")),
                BinaryOp("^", n.left, n.right),
            ),
        ],
        "-": [
            lambda n: BinaryOp(  # x - y = x + ¬y + 1
                "+", BinaryOp("+", n.left, UnaryOp("~", n.right)), Constant("int", "1")
            ),
            lambda n: BinaryOp(  # x - y = (x ^ y) - 2 * (¬x & y)
                "-",
                BinaryOp("^", n.left, n.right),
                BinaryOp(
                    "<<",
                    BinaryOp("&", UnaryOp("~", n.left), n.right),
                    Constant("int", "1"),
                ),
            ),
            lambda n: BinaryOp(  # x - y = (x & ¬y) - (¬x & y)
                "-",
                BinaryOp("&", n.left, UnaryOp("~", n.right)),
                BinaryOp("&", UnaryOp("~", n.left), n.right),
            ),
            lambda n: BinaryOp(  # x - y = 2 * (x & ¬y) - (x ^ y)
                "-",
                BinaryOp(
                    "<<",
                    BinaryOp("&", n.left, UnaryOp("~", n.right)),
                    Constant("int", "1"),
                ),
                BinaryOp("^", n.left, n.right),
            ),
        ],
        "^": [
            lambda n: BinaryOp(  # x ^ y = (x | y) - (x & y)
                "-", BinaryOp("|", n.left, n.right), BinaryOp("&", n.left, n.right)
            ),
        ],
        "|": [
            lambda n: BinaryOp(  # x | y = (x & ¬y) + y
                "+", BinaryOp("&", n.left, UnaryOp("~", n.right)), n.right
            ),
        ],
        "&": [
            lambda n: BinaryOp(  # x & y = (¬x | y) - ¬x
                "-", BinaryOp("|", UnaryOp("~", n.left), n.right), UnaryOp("~", n.left)
            ),
        ],
    }

    def generic_visit(self, node):  
        # TODO broken - we just assume only integer operations for now!
        if node in self.ignore_list:
            return
        for child in node.children():
            if isinstance(child[1], (UnaryOp, BinaryOp)):
                current = child[1]
                # TODO is this correct, or should I check .expr and .left/.right instead?
                if not self.analyzer.is_type(current, ExpressionAnalyzer.SimpleType.INT):
                    continue
                if self.analyzer.is_mutating(current):
                    continue
                applied_count = 0
                # TODO check how transform depth works here - is it OK?
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
                    parts = [p[:-1] if p[-1] == "]" else p for p in child[0].split("[")]
                    if (
                        len(parts) == 1
                    ):  
                        # TODO use this to fix similar issues in other code areas
                        setattr(node, child[0], current)
                    else:
                        getattr(node, parts[0])[int(parts[1])] = current
                    self.ignore_list.add(current)
                    applied_count += 1
        NodeVisitor.generic_visit(self, node)

    def visit_FileAST(self, node):
        self.analyzer = ExpressionAnalyzer(node)
        self.analyzer.process()
        NodeVisitor.generic_visit(self, node)
        self.reset()


class ArithmeticEncodeUnit(ObfuscationUnit):
    """TODO"""

    name = "Integer Arithmetic Encoding"
    description = "Encode integer variable arithmetic to make code less comprehensible"
    extended_description = (
        """This transformation encodes arithmetic operations within the code, replacing simple\n"""
        """additions and multipliations with compound combinations of bitwise operations and\n"""
        """alternative arithmetic. When performed on arithmetic dependent upon inputs, this cannot be\n"""
        """optimised out by a compiler and will greatly increase obfuscation.\n\n"""
        """The only available option is the encoding depth - arithmetic operations within encoded\n"""
        """arithmetic operations can be recursively encoded to increase code complexity, and so depth\n"""
        """refers to the maximum recursive encoding depth that is allowed. A value > 5 is not recommended\n"""
        """due to the potential slowdown."""
    )
    type = TransformType.ENCODING

    def __init__(self, level):
        # TODO could give this a probability as well (defaults 1.0)?
        self.level = level
        self.traverser = ArithmeticEncodeTraverser(level)

    def transform(self, source: interaction.CSource) -> interaction.CSource:
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
        level_flag = f"depth={self.level}"
        return f"ArithmeticEncode({level_flag})"  # TODO finish/fix this method