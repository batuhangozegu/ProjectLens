from projectlens.analysis.languages.dart import DartParser


def test_symbols_modifiers_qualified_methods_and_control_flow():
    parsed = DartParser().parse("x.dart", """abstract class A { void f() { if (true) { while (false) {} } } }
base mixin M {}
enum E { a }
extension X on A { int get value => 1; }
extension on A {}
typedef Callback = void Function();
Widget build() { return A(); }
""")
    assert [(s.name, s.kind) for s in parsed.symbols] == [
        ("A", "class"), ("A.f", "method"), ("M", "mixin"), ("E", "enum"),
        ("X", "extension"), ("X.value", "method"), ("<unnamed>", "extension"),
        ("Callback", "typedef"), ("build", "function"),
    ]


def test_directives_show_alias_conditional_multiline_and_part_of():
    parsed = DartParser().parse("x.dart", """import 'package:a/a.dart' as a show Z, A if (dart.library.io) 'io.dart';
export
  '../x.dart' show B, A;
part 'piece.dart';
part of 'library.dart';
""")
    assert [(x.module, x.imported_names, x.line) for x in parsed.imports] == [
        ("package:a/a.dart", ("A", "Z"), 1), ("../x.dart", ("A", "B"), 2),
        ("piece.dart", (), 4), ("library.dart", (), 5),
    ]


def test_comments_strings_interpolation_raw_and_nested_block_comment():
    parsed = DartParser().parse("x.dart", """// TODO one
/* TODO /* FIXME nested */ FIXME */
final a = r'TODO { class X {} }';
final b = 'TODO ${'class Hidden {}'} { if (true) {} }';
final c = '''FIXME
TODO''';
class Kept {}
""")
    assert parsed.comment_markers == ("TODO:1", "TODO:2", "FIXME:2", "FIXME:2")
    assert [s.name for s in parsed.symbols] == ["Kept"]


def test_unterminated_constructs_keep_prior_results_and_empty_crlf_support():
    parser = DartParser()
    for source in ("void ok() {}\nfinal x = 'bad", "class A {}\n/* bad"):
        parsed = parser.parse("bad.dart", source)
        assert parsed.symbols
        assert parsed.diagnostics[0].error_type == "SyntaxError"
        assert parsed.diagnostics[0].stage == "parse"
    assert parser.parse("empty.dart", "").symbols == ()
    assert parser.parse("crlf.dart", "class A {\r\n void f() {}\r\n}\r\n").symbols[1].start_line == 2
    assert parser.supports("A.DART") and parser.supports("src\\a.dart") and not parser.supports("a.py")
