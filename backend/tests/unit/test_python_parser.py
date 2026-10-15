from projectlens.analysis.languages.python import PythonParser, decode_source, parse_bytes


def test_symbols_ranges_nested_async_and_unicode():
    source = """@decorate
class Café:
    @staticmethod
    async def run(self):
        def inner():
            return 1
        return inner()

def plain():
    pass
"""
    parsed = PythonParser().parse("a.py", source)
    assert [(s.name, s.kind, s.start_line, s.end_line) for s in parsed.symbols] == [
        ("Café", "class", 1, 7),
        ("Café.run", "method", 3, 7),
        ("Café.run.inner", "function", 5, 6),
        ("plain", "function", 9, 10),
    ]


def test_import_forms_aliases_relative_and_nested():
    source = """import a.b as c
from x import y as z, q
from . import m
from ..pkg import n
from x import *
from x import (a as aa,
               b)
def f():
    import local.mod as lm
try:
    from .maybe import thing
except ImportError:
    pass
if True:
    import conditional
"""
    parsed = PythonParser().parse("pkg/mod.py", source)
    assert [(i.module, i.imported_names, i.relative_level, i.line) for i in parsed.imports] == [
        ("a.b", ("a.b as c",), 0, 1),
        ("x", ("y as z", "q"), 0, 2),
        (None, ("m",), 1, 3),
        ("pkg", ("n",), 2, 4),
        ("x", ("*",), 0, 5),
        ("x", ("a as aa", "b"), 0, 6),
        ("local.mod", ("local.mod as lm",), 0, 9),
        ("maybe", ("thing",), 1, 11),
        ("conditional", ("conditional",), 0, 15),
    ]


def test_diagnostics_for_syntax_null_bytes_and_decode_errors():
    parser = PythonParser()
    syntax = parser.parse("bad.py", "def x(:\n")
    assert syntax.diagnostics[0].error_type == "SyntaxError"
    assert "line 1" in syntax.diagnostics[0].message
    null = parser.parse("null.py", "x = '\0'")
    assert null.diagnostics[0].error_type == "NullByteError"
    result = parse_bytes(parser, "bad.py", b"# coding: utf-8\n\xff")
    assert result.symbols == () and result.diagnostics[0].error_type == "EncodingError"


def test_pep263_and_bom_decoding():
    source, error = decode_source("# coding: latin-1\nname = 'café'\n".encode("latin-1"), "x.py")
    assert error is None and "café" in source
    source, error = decode_source("name = 'ok'\n".encode("utf-8-sig"), "x.py")
    assert error is None and source.startswith("name")


def test_markers_only_in_comment_tokens_and_per_occurrence():
    source = '''text = "TODO FIXME"
"""TODO docstring"""
# TODO FIXME TODOs FIXME!
# nothing
'''
    parsed = PythonParser().parse("markers.py", source)
    assert parsed.comment_markers == ("TODO:3", "FIXME:3", "FIXME:3")


def test_tokenization_failure_keeps_markers_seen_before_error():
    parsed = PythonParser().parse("broken.py", "# TODO first\n'''unterminated\n# FIXME hidden\n")
    assert parsed.comment_markers == ("TODO:1",)
    assert any(d.error_type == "TokenizeError" for d in parsed.diagnostics)


def test_empty_comment_only_support_and_determinism():
    parser = PythonParser()
    assert parser.supports("x.py") and parser.supports("x.pyi") and not parser.supports("x.pyx")
    assert parser.parse("empty.py", "").symbols == ()
    assert parser.parse("comments.py", "# TODO later\n").comment_markers == ("TODO:1",)
    source = "import z\nimport a\ndef b(): pass\ndef a(): pass\n"
    assert parser.parse("x.py", source) == parser.parse("x.py", source)
    assert [i.line for i in parser.parse("x.py", source).imports] == [1, 2]
