"""Resolve parsed Python imports and build a deterministic file dependency graph.

Only paths and parser records are inspected: repository code is never imported or
executed. NetworkX is kept as an implementation detail of graph/SCC analysis.
"""

from __future__ import annotations

import posixpath
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

import networkx as nx

from .models import AnalysisDiagnostic, DependencyEdge, ImportRecord, ParsedFile


@dataclass(frozen=True)
class ImportReference:
    """An import not represented by a local edge."""

    source_file: str
    line: int
    module: str
    kind: str = ""


@dataclass(frozen=True)
class DependencyGraphResult:
    edges: tuple[DependencyEdge, ...]
    external_imports: tuple[ImportReference, ...]
    unresolved_imports: tuple[ImportReference, ...]
    incoming_counts: dict[str, int]
    outgoing_counts: dict[str, int]
    cycle_groups: tuple[tuple[str, ...], ...]
    diagnostics: tuple[AnalysisDiagnostic, ...]


def build_dependency_graph(
    python_files: Sequence[str], parsed_files: Sequence[ParsedFile]
) -> DependencyGraphResult:
    """Resolve imports and return local edges, external/unresolved records and cycles.

    A top-level ``src/`` directory is treated as an additional source root; paths
    under it also receive a root-relative module name. The repository root is
    always a source root. If both roots provide the same module, resolution is
    ambiguous instead of choosing one. ``.pyi`` paths are ignored as module
    sources (their imports, if passed, are ignored too).

    Edges point only at the most specific imported module. Parent package
    ``__init__.py`` execution is deliberately not represented as an edge. For
    ``from package import name``, a local ``package.name`` module wins over the
    package initializer; otherwise the edge targets the package initializer.
    Namespace package directories (directories without ``__init__.py``) are
    not indexed as packages: a lookup traversing one is unresolved with a
    ``NamespacePackage`` diagnostic. Local top-level names shadow external
    names. External stdlib labeling uses this interpreter's
    ``sys.stdlib_module_names`` and therefore follows its Python version.

    Counts are distinct incoming/outgoing neighbor files, not import statement
    counts. Every ``.py`` input remains a graph node, including isolated files.
    """

    files = tuple(sorted({_path(path) for path in python_files if _path(path).endswith(".py")}))
    imports_by_file: dict[str, list[ImportRecord]] = defaultdict(list)
    for parsed in parsed_files:
        path = _path(parsed.path)
        if path.endswith(".py"):
            imports_by_file[path].extend(parsed.imports)

    candidates: dict[str, set[str]] = defaultdict(set)
    namespace_reasons: dict[tuple[str, str], str] = {}
    for path in files:
        for module, namespace in _module_names(path, files):
            candidates[module].add(path)
            if namespace:
                namespace_reasons[(module, path)] = namespace

    graph = nx.DiGraph()
    graph.add_nodes_from(files)
    evidence: dict[tuple[str, str], set[int]] = defaultdict(set)
    external: set[ImportReference] = set()
    unresolved: set[ImportReference] = set()
    diagnostics: set[AnalysisDiagnostic] = set()

    for source in files:
        for record in sorted(imports_by_file[source], key=_import_key):
            requested, names, bad_relative = _requested_modules(source, record)
            if bad_relative:
                ref = ImportReference(source, record.line, _display_module(record), "above_top_level")
                unresolved.add(ref)
                diagnostics.add(AnalysisDiagnostic("dependency", source, "RelativeImportBeyondTopLevel", f"relative import {_display_module(record)!r} goes above the top-level package"))
                continue
            if not requested:
                ref = ImportReference(source, record.line, _display_module(record), "ambiguous")
                unresolved.add(ref)
                diagnostics.add(AnalysisDiagnostic("dependency", source, "UnresolvedImport", "import has no resolvable module name"))
                continue

            # The parser's record shape is shared by Import and ImportFrom.
            # An imported name equal to the module spelling denotes ``import x``;
            # otherwise the statement is a from-import with possible submodules.
            from_names = names
            if record.relative_level == 0 and record.module and names and all(name == record.module for name in names):
                from_names = None
            local_found = False
            classified_unresolved = False
            for target_module in requested:
                # Resolve each from-imported name independently: a single
                # statement can import more than one local submodule.
                if from_names is None or not from_names or "*" in from_names:
                    lookup_groups = [[target_module]]
                else:
                    lookup_groups = [[f"{target_module}.{name}", target_module] for name in from_names]
                for lookup_modules in lookup_groups:
                    resolution = _resolve(lookup_modules, candidates, namespace_reasons)
                    if resolution[0] == "local":
                        _, target = resolution
                        evidence[(source, target)].add(record.line)
                        local_found = True
                    elif resolution[0] == "ambiguous":
                        module_name = resolution[1]
                        ref = ImportReference(source, record.line, module_name, "ambiguous")
                        unresolved.add(ref)
                        diagnostics.add(AnalysisDiagnostic("dependency", source, "AmbiguousLocalModule", f"module {module_name!r} maps to multiple local files"))
                        classified_unresolved = True
                    elif resolution[0] == "namespace":
                        module_name = resolution[1]
                        ref = ImportReference(source, record.line, module_name, "namespace_package")
                        unresolved.add(ref)
                        diagnostics.add(AnalysisDiagnostic("dependency", source, "NamespacePackage", f"module {module_name!r} traverses a directory without __init__.py"))
                        classified_unresolved = True
            if not local_found and not classified_unresolved:
                module = requested[0]
                top_level = module.split(".", 1)[0]
                kind = "stdlib" if top_level in sys.stdlib_module_names else "third_party"
                external.add(ImportReference(source, record.line, module, kind))

    edges = tuple(
        DependencyEdge(source, target, min(lines), tuple(sorted(lines)))
        for (source, target), lines in sorted(evidence.items())
    )
    for source, target in evidence:
        graph.add_edge(source, target)
    incoming = {path: graph.in_degree(path) for path in files}
    outgoing = {path: graph.out_degree(path) for path in files}
    groups = []
    for component in nx.strongly_connected_components(graph):
        members = tuple(sorted(component))
        if len(members) > 1 or graph.has_edge(members[0], members[0]):
            groups.append(members)
    cycle_groups = tuple(sorted(groups, key=lambda group: group[0]))
    return DependencyGraphResult(
        edges,
        tuple(sorted(external, key=_reference_key)),
        tuple(sorted(unresolved, key=_reference_key)),
        incoming,
        outgoing,
        cycle_groups,
        tuple(sorted(diagnostics, key=lambda d: (d.file or "", d.error_type, d.message))),
    )


def _path(value: str) -> str:
    normalized = posixpath.normpath(value.replace("\\", "/"))
    return normalized[2:] if normalized.startswith("./") else normalized


def _module_names(path: str, all_paths: Sequence[str]) -> list[tuple[str, str | None]]:
    parts = path.split("/")
    roots = [(parts, 0)]
    if len(parts) > 1 and parts[0] == "src":
        roots.append((parts[1:], 1))
    result: list[tuple[str, str | None]] = []
    for rooted, offset in roots:
        name_parts = rooted[:-1] + [rooted[-1][:-3]]
        if name_parts[-1] == "__init__":
            name_parts = name_parts[:-1]
        if not name_parts or any(not part.isidentifier() for part in name_parts):
            continue
        module = ".".join(name_parts)
        missing = []
        # Intermediate directories and the containing directory of an __init__
        # must be regular packages. Missing init means ambiguous namespace scope.
        for depth in range(1, len(rooted)):
            dir_path = "/".join(parts[: offset + depth])
            if f"{dir_path}/__init__.py" not in all_paths:
                missing.append("/".join(rooted[:depth]))
        result.append((module, "/".join(missing) if missing else None))
    return result


def _requested_modules(source: str, record: ImportRecord) -> tuple[list[str], tuple[str, ...] | None, bool]:
    module = record.module
    names = tuple(_unaliased(item) for item in record.imported_names)
    names = tuple(name for name in names if name)
    if record.relative_level == 0:
        if not module:
            return [], names, False
        return [module], names, False

    source_parts = source.split("/")
    module_path_parts = source_parts[:-1]
    if source_parts and source_parts[0] == "src":
        module_path_parts = module_path_parts[1:]
    climb = record.relative_level - 1
    if climb >= len(module_path_parts):
        return [], names, True
    base = module_path_parts[:len(module_path_parts) - climb]
    if module:
        base.extend(module.split("."))
    return ([".".join(base)] if base else []), names, False


def _resolve(lookups: list[str], candidates: dict[str, set[str]], namespace_reasons: dict[tuple[str, str], str]):
    for lookup in lookups:
        if not lookup:
            continue
        prefixes = [lookup[:index] for index, char in enumerate(lookup) if char == "."]
        for candidate in [lookup, *reversed(prefixes)]:
            if candidate in candidates:
                paths = candidates[candidate]
                if len(paths) > 1:
                    return "ambiguous", candidate
                path = next(iter(paths))
                if namespace_reasons.get((candidate, path)):
                    return "namespace", candidate
                return "local", path
        # If a concrete file exists below an implicit namespace, report that
        # limitation rather than misclassifying it as external.
        for prefix in prefixes:
            matching = [name for name in candidates if name == lookup or name.startswith(prefix + ".")]
            if matching:
                for name in matching:
                    for path in candidates[name]:
                        if namespace_reasons.get((name, path)):
                            return "namespace", name
    return "external", ""


def _unaliased(value: str) -> str:
    return value.split(" as ", 1)[0].strip()


def _display_module(record: ImportRecord) -> str:
    return "." * record.relative_level + (record.module or "")


def _import_key(item: ImportRecord) -> tuple:
    return item.line, item.module or "", item.relative_level, item.imported_names


def _reference_key(item: ImportReference) -> tuple:
    return item.source_file, item.line, item.module, item.kind
