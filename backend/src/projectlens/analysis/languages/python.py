"""Non-executing Python source parser based on :mod:`ast` and :mod:`tokenize`."""

from __future__ import annotations

import ast
import io
import re
import tokenize

from projectlens.analysis.models import AnalysisDiagnostic, ImportRecord, ParsedFile, SymbolRecord


class PythonParser:
    """Extract Python symbols, imports, and comment markers without executing code."""

    def supports(self, path: str) -> bool:
        return path.replace("\\", "/").rsplit("/", 1)[-1].lower().endswith((".py", ".pyi"))

    def parse(self, path: str, source: str) -> ParsedFile:
        diagnostics: list[AnalysisDiagnostic] = []
        symbols: list[SymbolRecord] = []
        imports: list[ImportRecord] = []
        markers = _comment_markers(source, path, diagnostics)
        try:
            tree = ast.parse(source, filename=path)
            _collect_symbols(tree, path, symbols)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.name if alias.asname is None else f"{alias.name} as {alias.asname}"
                        imports.append(ImportRecord(path, alias.name, (name,), 0, node.lineno))
                elif isinstance(node, ast.ImportFrom):
                    names = tuple("*" if item.name == "*" else item.name if item.asname is None else f"{item.name} as {item.asname}" for item in node.names)
                    imports.append(ImportRecord(path, node.module, names, node.level, node.lineno))
        except SyntaxError as exc:
            # Python >= 3.12 reports null bytes as SyntaxError rather than ValueError.
            kind = "NullByteError" if "null byte" in str(exc.msg).lower() else "SyntaxError"
            diagnostics.append(AnalysisDiagnostic("parse", path, kind, f"{exc.msg} (line {exc.lineno})"))
        except ValueError as exc:
            kind = "NullByteError" if "null byte" in str(exc).lower() else "ValueError"
            diagnostics.append(AnalysisDiagnostic("parse", path, kind, str(exc)))
        except (RecursionError, MemoryError) as exc:
            diagnostics.append(AnalysisDiagnostic("parse", path, type(exc).__name__, str(exc) or "parser resource limit exceeded"))
        symbols.sort(key=lambda item: (item.start_line, item.end_line, item.name, item.kind))
        imports.sort(key=lambda item: (item.line, item.module or "", item.relative_level, item.imported_names))
        return ParsedFile(path, tuple(symbols), tuple(imports), tuple(markers), tuple(sorted(diagnostics, key=lambda d: (d.error_type, d.message))))


def decode_source(data: bytes, path: str = "<bytes>") -> tuple[str | None, AnalysisDiagnostic | None]:
    """Decode Python bytes using PEP 263/BOM detection; report failures as diagnostics."""
    try:
        encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
        return data.decode(encoding), None
    except (SyntaxError, UnicodeError, LookupError) as exc:
        return None, AnalysisDiagnostic("parse", path, "EncodingError", str(exc))
    except (RecursionError, MemoryError) as exc:
        return None, AnalysisDiagnostic("parse", path, type(exc).__name__, str(exc) or "decoder resource limit exceeded")


def parse_bytes(parser: PythonParser, path: str, data: bytes) -> ParsedFile:
    """Decode and parse bytes without allowing decoding errors to escape."""
    source, diagnostic = decode_source(data, path)
    if diagnostic is not None:
        return ParsedFile(path, diagnostics=(diagnostic,))
    assert source is not None
    return parser.parse(path, source)


def _comment_markers(source: str, path: str, diagnostics: list[AnalysisDiagnostic]) -> list[str]:
    found: list[tuple[int, str]] = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        for token in tokens:
            if token.type != tokenize.COMMENT:
                continue
            found.extend((token.start[0], marker) for marker in re.findall(r"\b(TODO|FIXME)\b", token.string))
    except (tokenize.TokenError, IndentationError, SyntaxError) as exc:
        line = exc.args[1][0] if len(exc.args) > 1 and isinstance(exc.args[1], tuple) else None
        suffix = f" (line {line})" if line else ""
        diagnostics.append(AnalysisDiagnostic("parse", path, "TokenizeError", f"{exc}{suffix}"))
    return [f"{kind}:{line}" for line, kind in sorted(found, key=lambda marker: marker[0])]


def _collect_symbols(tree: ast.AST, path: str, result: list[SymbolRecord]) -> None:
    def visit(node: ast.AST, scopes: tuple[tuple[str, bool], ...]) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            decorators = getattr(node, "decorator_list", ())
            starts = [node.lineno, *(decorator.lineno for decorator in decorators)]
            name = ".".join((*[scope[0] for scope in scopes], node.name))
            kind = "class" if isinstance(node, ast.ClassDef) else "method" if scopes and scopes[-1][1] else "function"
            result.append(SymbolRecord(path, name, kind, min(starts), node.end_lineno or node.lineno))
            for child in node.body:
                visit(child, (*scopes, (node.name, isinstance(node, ast.ClassDef))))
        else:
            for child in ast.iter_child_nodes(node):
                visit(child, scopes)
    visit(tree, ())
