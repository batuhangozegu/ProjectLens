from __future__ import annotations

import random

from projectlens.analysis.dependency import build_dependency_graph
from projectlens.analysis.models import ImportRecord, ParsedFile


def repo(paths: list[str], imports: dict[str, list[tuple[str | None, tuple[str, ...], int, int]]] | None = None):
    imports = imports or {}
    parsed = [
        ParsedFile(path, imports=tuple(ImportRecord(path, module, names, level, line) for module, names, level, line in imports.get(path, [])))
        for path in paths
    ]
    return build_dependency_graph(paths, parsed)


def pairs(result):
    return [(edge.source, edge.target) for edge in result.edges]


def test_flat_modules_and_imports_inside_functions():
    result = repo(["a.py", "b.py"], {"a.py": [("b", ("b",), 0, 3)]})
    assert pairs(result) == [("a.py", "b.py")]
    assert result.incoming_counts == {"a.py": 0, "b.py": 1}
    assert result.outgoing_counts == {"a.py": 1, "b.py": 0}


def test_package_init_src_layout_and_from_import_submodule_precedence():
    result = repo(
        ["src/pkg/__init__.py", "src/pkg/x.py", "src/consumer.py", "plain.py"],
        {"src/consumer.py": [("pkg", ("x",), 0, 1), ("pkg", ("other",), 0, 2)],
         "plain.py": [("pkg.x", ("pkg.x",), 0, 4)]},
    )
    assert pairs(result) == [("plain.py", "src/pkg/x.py"), ("src/consumer.py", "src/pkg/__init__.py"), ("src/consumer.py", "src/pkg/x.py")]


def test_relative_imports_from_init_and_module_at_levels_one_and_two():
    result = repo(
        ["pkg/__init__.py", "pkg/sub/__init__.py", "pkg/sub/mod.py", "pkg/sibling.py", "top.py"],
        {"pkg/__init__.py": [(None, ("sibling",), 1, 1), ("sub", ("mod",), 1, 2)],
         "pkg/sub/__init__.py": [(None, ("sibling",), 2, 3)],
         "pkg/sub/mod.py": [("sibling", ("x",), 2, 4), (None, ("y",), 1, 5)]},
    )
    assert set(pairs(result)) == {
        ("pkg/__init__.py", "pkg/sibling.py"),
        ("pkg/__init__.py", "pkg/sub/mod.py"),
        ("pkg/sub/__init__.py", "pkg/sibling.py"),
        ("pkg/sub/mod.py", "pkg/sibling.py"),
        ("pkg/sub/mod.py", "pkg/sub/__init__.py"),
    }
    assert not result.unresolved_imports


def test_relative_above_top_and_star_import():
    result = repo(["pkg.py", "consumer.py"], {"pkg.py": [("x", ("*",), 0, 1)], "consumer.py": [("x", ("m",), 2, 4)]})
    assert result.unresolved_imports[0].kind == "above_top_level"
    assert result.unresolved_imports[0].source_file == "consumer.py"


def test_stdlib_third_party_and_local_shadowing():
    result = repo(["json.py", "consumer.py"], {"consumer.py": [("json", (), 0, 1), ("os.path", (), 0, 2), ("requests", (), 0, 3)]})
    assert pairs(result) == [("consumer.py", "json.py")]
    assert [(x.module, x.kind) for x in result.external_imports] == [("os.path", "stdlib"), ("requests", "third_party")]


def test_ambiguous_module_under_two_roots():
    result = repo(["src/mod.py", "mod.py", "consumer.py"], {"consumer.py": [("mod", (), 0, 1)]})
    assert not result.edges
    assert result.unresolved_imports[0].kind == "ambiguous"


def test_isolated_node_self_loop_and_cycles():
    result = repo(
        ["a.py", "b.py", "c.py", "d.py", "e.py", "f.py", "alone.py"],
        {"a.py": [("a", (), 0, 1), ("b", (), 0, 2)], "b.py": [("a", (), 0, 1)],
         "c.py": [("d", (), 0, 1)], "d.py": [("e", (), 0, 1)], "e.py": [("c", (), 0, 1)],
         "f.py": [("f", (), 0, 1)]},
    )
    assert result.cycle_groups == (("a.py", "b.py"), ("c.py", "d.py", "e.py"), ("f.py",))
    assert "alone.py" in result.incoming_counts and "alone.py" in result.outgoing_counts


def test_diamond_is_not_a_cycle_and_neighbor_counts_are_distinct():
    result = repo(["a.py", "b.py", "c.py", "d.py"], {"a.py": [("b", (), 0, 1), ("c", (), 0, 2)], "b.py": [("d", (), 0, 1)], "c.py": [("d", (), 0, 1)]})
    assert result.cycle_groups == ()
    assert result.outgoing_counts["a.py"] == 2
    assert result.incoming_counts["d.py"] == 2


def test_multiple_imports_collapse_to_sorted_evidence_lines_and_self_edge_kept():
    result = repo(["a.py", "b.py"], {"a.py": [("b", (), 0, 8), ("b", (), 0, 2), ("a", (), 0, 9)]})
    assert pairs(result) == [("a.py", "a.py"), ("a.py", "b.py")]
    assert result.edges[1].evidence_lines == (2, 8)
    assert result.edges[1].import_line == 2
    assert result.outgoing_counts["a.py"] == 2


def test_shuffled_input_order_has_identical_result():
    paths = ["a.py", "b.py", "c.py"]
    imports = {"a.py": [("b", (), 0, 3), ("c", (), 0, 1)], "b.py": [("a", (), 0, 4)]}
    expected = repo(paths, imports)
    random.Random(71).shuffle(paths)
    shuffled = {key: list(reversed(value)) for key, value in reversed(list(imports.items()))}
    assert repo(paths, shuffled) == expected


def test_namespace_package_is_unresolved_not_a_fake_module():
    result = repo(["ns/mod.py", "consumer.py"], {"consumer.py": [("ns.mod", (), 0, 1)]})
    assert not result.edges
    assert result.unresolved_imports[0].kind == "namespace_package"
    assert result.diagnostics[0].error_type == "NamespacePackage"
