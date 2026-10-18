from projectlens.analysis.findings import compute_findings
from projectlens.analysis.models import DependencyEdge, FileRecord, ParsedFile, SymbolRecord
from projectlens.analysis.languages.dart import DartParser
from projectlens.analysis.languages.python import PythonParser


def file(path, cls="source", status="analyzed"):
    return FileRecord(path, "python", cls, 1, status)


def symbol(path, name, kind, start, end):
    return SymbolRecord(path, name, kind, start, end)


def test_symbol_thresholds_and_warning_levels():
    path = "src/a.py"
    records = [file(path)]
    parsed = [ParsedFile(path, (
        symbol(path, "f79", "function", 1, 79), symbol(path, "f80", "function", 1, 80),
        symbol(path, "f150", "function", 1, 150),
        symbol(path, "C399", "class", 1, 399), symbol(path, "C400", "class", 1, 400),
        symbol(path, "C800", "class", 1, 800),
    ))]
    result = compute_findings(records, parsed, [], [])
    got = {(x["symbol"], x["severity"]) for x in result["top_findings"]}
    assert ("f80", "notice") in got and ("f150", "warning") in got
    assert ("C400", "notice") in got and ("C800", "warning") in got
    assert not any(x["symbol"] in {"f79", "C399"} for x in result["top_findings"])


def test_many_members_counts_direct_qualified_children_only():
    path = "a.dart"
    symbols = [symbol(path, "C", "class", 1, 500), symbol(path, "C.Nested", "class", 2, 400)]
    symbols += [symbol(path, f"C.m{i}", "method", i + 3, i + 3) for i in range(30)]
    symbols += [symbol(path, f"C.Nested.n{i}", "method", i + 50, i + 50) for i in range(40)]
    result = compute_findings([file(path)], [ParsedFile(path, tuple(symbols))], [], [])
    members = [x for x in result["top_findings"] if x["kind"] == "many_members"]
    assert sorted((x["symbol"], x["value"]) for x in members) == [("C", 30), ("C.Nested", 40)]  # C does not absorb Nested's 40


def test_coupling_distinct_neighbors_and_exclusions():
    files = [file("hub.py"), *[file(f"u{i}.py") for i in range(10)],
             *[file(f"t{i}.py", "test") for i in range(15)]]
    edges = [DependencyEdge(f"u{i}.py", "hub.py", 1) for i in range(10)]
    edges += [DependencyEdge("u0.py", "hub.py", 2) for _ in range(2)]
    edges += [DependencyEdge("hub.py", f"t{i}.py", 1) for i in range(15)]
    result = compute_findings(files, [], edges, [])
    by_kind = {(x["kind"], x["path"]): x for x in result["top_findings"]}
    assert by_kind[("high_fan_in", "hub.py")]["value"] == 10
    assert by_kind[("high_fan_out", "hub.py")]["value"] == 15


def test_empty_invalid_ranges_determinism_and_cap():
    assert compute_findings([], [], [], []) ["total"] == 0
    path = "a.py"
    parsed = [ParsedFile(path, (symbol(path, "bad", "function", 9, 2),))]
    assert compute_findings([file(path)], parsed, [], []) ["total"] == 0
    files = [file(f"f{i}.py") for i in range(60)]
    parsed = [ParsedFile(item.path, (symbol(item.path, "huge", "function", 1, 150),)) for item in files]
    first = compute_findings(files, parsed, [], [])
    second = compute_findings(list(reversed(files)), list(reversed(parsed)), [], [])
    assert first == second
    assert first["total"] == 60 and first["truncated"] is True
    assert len(first["top_findings"]) == 50
    assert first["top_findings"][0]["path"] == "f0.py"


def test_test_and_generated_symbols_excluded_but_graph_counts_kept():
    files = [file("tests/test_big.py", "test"), file("gen.g.dart")]
    parsed = [ParsedFile(item.path, (symbol(item.path, "huge", "function", 1, 200),)) for item in files]
    assert compute_findings(files, parsed, [], []) ["total"] == 0


def test_parser_qualified_names_and_many_member_severity():
    py = PythonParser().parse("p.py", "class Box:\n    def method(self):\n        pass\n")
    dart = DartParser().parse("d.dart", "class Box {\n  void method() {}\n}")
    assert any(s.name == "Box.method" and s.kind == "method" for s in py.symbols)
    assert any(s.name == "Box.method" and s.kind == "method" for s in dart.symbols)
    path = "many.py"
    for count, expected in ((29, None), (30, "notice"), (60, "warning")):
        symbols = (symbol(path, "C", "class", 1, 900),) + tuple(
            symbol(path, f"C.m{i}", "method", i + 2, i + 2) for i in range(count)
        )
        result = compute_findings([file(path)], [ParsedFile(path, symbols)], [], [])
        finding = next(x for x in result["top_findings"] if x["kind"] == "many_members") if expected else None
        assert (finding["severity"] if finding else None) == expected


def test_fan_out_threshold_and_warning_threshold():
    for count, expected in ((14, None), (15, "notice"), (30, "warning")):
        files = [file("source.py"), *[file(f"d{i}.py") for i in range(count)]]
        edges = [DependencyEdge("source.py", f"d{i}.py", 1) for i in range(count)]
        result = compute_findings(files, [], edges, [])
        finding = next((x for x in result["top_findings"] if x["kind"] == "high_fan_out"), None)
        assert (finding["severity"] if finding else None) == expected
