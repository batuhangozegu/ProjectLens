"""Resolve Dart directive URIs into a deterministic repository file graph."""

from __future__ import annotations

import posixpath
import re
from collections import defaultdict
from typing import Mapping, Sequence

import networkx as nx

from .dependency import DependencyGraphResult, ImportReference, _reference_key
from .models import AnalysisDiagnostic, DependencyEdge, ImportRecord, ParsedFile


def read_pubspec_name(content: str) -> str | None:
    """Read only a top-level pubspec ``name:`` line, without a YAML dependency."""
    for line in content.lstrip("\ufeff").splitlines():
        if not line or line[0].isspace():
            continue
        match = re.match(r"^name\s*:\s*(.*?)\s*(?:#.*)?$", line)
        if match:
            value = match.group(1).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1].strip()
            return value if value and re.fullmatch(r"[A-Za-z0-9_-]+", value) else None
    return None


def build_dart_dependency_graph(
    dart_files: Sequence[str],
    parsed_files: Sequence[ParsedFile],
    pubspec_names_or_sources: Mapping[str, str | None],
) -> DependencyGraphResult:
    """Build edges for relative and local ``package:`` Dart URIs.

    Mapping keys are repository-relative pubspec.yaml paths and values are their
    parsed package names. Pass None for a missing/invalid name.
    """
    files = tuple(sorted({_path(path) for path in dart_files if _path(path).lower().endswith(".dart")}))
    file_set = set(files)
    imports: dict[str, list[ImportRecord]] = defaultdict(list)
    for parsed in parsed_files:
        path = _path(parsed.path)
        if path.lower().endswith(".dart"):
            imports[path].extend(parsed.imports)

    roots: dict[str, list[str]] = defaultdict(list)
    declared_roots: set[str] = set()
    diagnostics: set[AnalysisDiagnostic] = set()
    for pubspec, name in sorted(pubspec_names_or_sources.items()):
        root = posixpath.dirname(_path(pubspec))
        declared_roots.add(root)
        if name:
            roots[name].append(root)
        else:
            diagnostics.add(AnalysisDiagnostic("dependency", _path(pubspec), "InvalidPubspecName", "pubspec.yaml has no valid top-level name"))
    ambiguous = {name for name, values in roots.items() if len(set(values)) > 1}
    for name in ambiguous:
        diagnostics.add(AnalysisDiagnostic("dependency", None, "AmbiguousPackageName", f"package name {name!r} is declared by multiple pubspec.yaml files"))

    root_names = {name: sorted(set(values)) for name, values in roots.items()}
    package_for_file = {}
    for source in files:
        ancestors = [root for root in declared_roots if _within(source, root)]
        if ancestors:
            nearest = max(ancestors, key=lambda value: (value.count("/"), len(value)))
            package_for_file[source] = nearest
        else:
            package_for_file[source] = None

    evidence: dict[tuple[str, str], set[int]] = defaultdict(set)
    external: set[ImportReference] = set()
    unresolved: set[ImportReference] = set()
    for source in files:
        for record in sorted(imports[source], key=lambda item: (item.line, item.module or "", item.imported_names)):
            uri = (record.module or "").strip()
            if uri.startswith("dart:"):
                external.add(ImportReference(source, record.line, uri, "dart_sdk")); continue
            if uri.startswith("package:"):
                tail = uri[len("package:"):]
                name, sep, member = tail.partition("/")
                if not name or not sep or not member:
                    unresolved.add(ImportReference(source, record.line, uri, "invalid_package_uri")); continue
                if name in ambiguous:
                    unresolved.add(ImportReference(source, record.line, uri, "ambiguous_package")); continue
                if name not in root_names:
                    external.add(ImportReference(source, record.line, uri, "package")); continue
                # Package roots with an invalid name are not indexed; names map to all roots.
                package_roots = root_names[name]
                source_root = package_for_file[source]
                target_root = source_root if source_root in package_roots else package_roots[0]
                target = _path(posixpath.join(target_root, "lib", member))
                if target.startswith("../") or target == ".." or target.startswith("/"):
                    unresolved.add(ImportReference(source, record.line, uri, "path_escapes_repository"))
                    diagnostics.add(AnalysisDiagnostic("dependency", source, "DartUriEscapesRepository", f"package URI {uri!r} escapes the repository root")); continue
                if target in file_set:
                    evidence[(source, target)].add(record.line)
                else:
                    unresolved.add(ImportReference(source, record.line, uri, "missing_local_file"))
                continue
            if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", uri):
                unresolved.add(ImportReference(source, record.line, uri, "unsupported_uri")); continue
            target = _path(posixpath.join(posixpath.dirname(source), uri))
            if target.startswith("/") or target == ".." or target.startswith("../"):
                unresolved.add(ImportReference(source, record.line, uri, "path_escapes_repository"))
                diagnostics.add(AnalysisDiagnostic("dependency", source, "DartUriEscapesRepository", f"relative URI {uri!r} escapes the repository root")); continue
            if target in file_set:
                evidence[(source, target)].add(record.line)
            else:
                unresolved.add(ImportReference(source, record.line, uri, "missing_local_file"))

    graph = nx.DiGraph()
    graph.add_nodes_from(files)
    graph.add_edges_from(sorted(evidence))
    edges = tuple(DependencyEdge(source, target, min(lines), tuple(sorted(lines))) for (source, target), lines in sorted(evidence.items()))
    groups = []
    for component in nx.strongly_connected_components(graph):
        members = tuple(sorted(component))
        if len(members) > 1 or graph.has_edge(members[0], members[0]):
            groups.append(members)
    return DependencyGraphResult(
        edges,
        tuple(sorted(external, key=_reference_key)),
        tuple(sorted(unresolved, key=_reference_key)),
        {path: graph.in_degree(path) for path in files},
        {path: graph.out_degree(path) for path in files},
        tuple(sorted(groups, key=lambda group: group[0])),
        tuple(sorted(diagnostics, key=lambda d: (d.file or "", d.error_type, d.message))),
    )


def _path(value: str) -> str:
    value = posixpath.normpath(value.replace("\\", "/"))
    return value[2:] if value.startswith("./") else value


def _within(path: str, root: str) -> bool:
    return not root or path == root or path.startswith(root.rstrip("/") + "/")
