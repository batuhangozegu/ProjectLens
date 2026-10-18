"""Small non-executing Dart lexer/parser.

This intentionally records ``part`` and ``part of`` URI directives without
distinguishing their directive kind in ImportRecord. Unnamed extensions are
named ``<unnamed>``. Constructors with bodies may be recorded as methods;
declaration-only constructors are omitted. Interpolation expressions are
skipped as part of their containing string so their braces and declarations are
never misread.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from projectlens.analysis.models import AnalysisDiagnostic, ImportRecord, ParsedFile, SymbolRecord


@dataclass(frozen=True)
class _Token:
    value: str
    line: int
    start: int
    end: int


class DartParser:
    """Extract Dart declarations/directives and comment markers without execution."""

    def supports(self, path: str) -> bool:
        return path.replace("\\", "/").rsplit("/", 1)[-1].lower().endswith(".dart")

    def parse(self, path: str, source: str) -> ParsedFile:
        tokens: list[_Token] = []
        comments: list[tuple[int, str]] = []
        diagnostics: list[AnalysisDiagnostic] = []
        i, line, n = 0, 1, len(source)

        def advance(end: int) -> None:
            nonlocal i, line
            line += source[i:end].count("\n")
            i = end

        while i < n:
            ch = source[i]
            if ch.isspace():
                advance(i + 1)
                continue
            if source.startswith("//", i):
                end = source.find("\n", i)
                if end < 0:
                    end = n
                comments.append((line, source[i:end]))
                advance(end)
                continue
            if source.startswith("/*", i):
                start, start_line, depth, j = i, line, 1, i + 2
                while j < n and depth:
                    if source.startswith("/*", j):
                        depth += 1; j += 2
                    elif source.startswith("*/", j):
                        depth -= 1; j += 2
                    else:
                        j += 1
                if depth:
                    comments.append((start_line, source[start:]))
                    diagnostics.append(AnalysisDiagnostic("parse", path, "SyntaxError", f"unterminated block comment (line {start_line})"))
                    break
                comments.append((start_line, source[start:j]))
                advance(j)
                continue
            # Dart raw string prefixes are only special immediately before a quote.
            quote_at = i + 1 if ch in "rR" and i + 1 < n and source[i + 1] in "'\"" else i
            if source[quote_at] in "'\"":
                q = source[quote_at]
                triple = source.startswith(q * 3, quote_at)
                delim = q * (3 if triple else 1)
                start_line = line
                j = quote_at + len(delim)
                raw = quote_at != i
                closed = False
                while j < n:
                    if source.startswith(delim, j):
                        j += len(delim); closed = True; break
                    if not raw and source[j] == "\\":
                        j += 2; continue
                    if not raw and source[j] == "$":
                        # Skip interpolation, including nested quoted strings and braces.
                        if j + 1 < n and source[j + 1] == "{":
                            j = _skip_interpolation(source, j + 2)
                            continue
                        if j + 1 < n and (source[j + 1].isalpha() or source[j + 1] in "_$"):
                            j += 2
                            while j < n and (source[j].isalnum() or source[j] in "_$."):
                                j += 1
                            continue
                    j += 1
                if not closed:
                    diagnostics.append(AnalysisDiagnostic("parse", path, "SyntaxError", f"unterminated string (line {start_line})"))
                    break
                tokens.append(_Token(source[i:j], start_line, i, j))
                advance(j)
                continue
            if ch.isalpha() or ch in "_$":
                start, start_line = i, line
                j = i + 1
                while j < n and (source[j].isalnum() or source[j] in "_$"):
                    j += 1
                tokens.append(_Token(source[start:j], start_line, start, j))
                advance(j)
                continue
            tokens.append(_Token(ch, line, i, i + 1))
            advance(i + 1)

        markers = [f"{kind}:{ln}" for ln, comment in comments for kind in re.findall(r"\b(TODO|FIXME)\b", comment)]
        symbols, imports = _collect(tokens, path)
        symbols.sort(key=lambda s: (s.start_line, s.end_line, s.name, s.kind))
        imports.sort(key=lambda item: (item.line, item.module or "", item.imported_names))
        return ParsedFile(path, tuple(symbols), tuple(imports), tuple(markers), tuple(sorted(diagnostics, key=lambda d: (d.error_type, d.message))))


def _skip_interpolation(source: str, i: int) -> int:
    depth, n = 1, len(source)
    while i < n and depth:
        if source.startswith("//", i):
            end = source.find("\n", i); i = n if end < 0 else end + 1; continue
        if source.startswith("/*", i):
            d = 1; i += 2
            while i < n and d:
                if source.startswith("/*", i): d += 1; i += 2
                elif source.startswith("*/", i): d -= 1; i += 2
                else: i += 1
            continue
        if source[i] in "'\"":
            q = source[i]; delim = q * (3 if source.startswith(q * 3, i) else 1); i += len(delim)
            while i < n:
                if source.startswith(delim, i): i += len(delim); break
                if source[i] == "\\": i += 2
                else: i += 1
            continue
        if source[i] == "{": depth += 1
        elif source[i] == "}": depth -= 1
        i += 1
    return i


_CONTROL = {"if", "for", "while", "switch", "catch", "assert", "return", "throw", "new", "super", "this", "void"}
_MODIFIERS = {"abstract", "base", "final", "interface", "sealed", "mixin", "external", "static", "factory", "const", "late", "covariant", "operator", "get", "set", "async", "sync", "enum", "class", "extension", "typedef"}


def _collect(tokens: list[_Token], path: str) -> tuple[list[SymbolRecord], list[ImportRecord]]:
    symbols: list[SymbolRecord] = []; imports: list[ImportRecord] = []
    brace_depth = 0; scopes: list[tuple[str, int]] = []
    i, n = 0, len(tokens)
    while i < n:
        t = tokens[i]
        if t.value == "}":
            brace_depth = max(0, brace_depth - 1)
            while scopes and scopes[-1][1] > brace_depth: scopes.pop()
            i += 1; continue
        if t.value == "{": brace_depth += 1; i += 1; continue
        scope = scopes[-1][0] if scopes else None
        if t.value == "class" or t.value == "enum" or t.value == "mixin" or t.value == "extension" or t.value == "typedef":
            # class modifiers are consumed naturally at the declaration keyword.
            kind = t.value
            name_i = i + 1
            if kind == "extension":
                name = tokens[name_i].value if name_i < n and tokens[name_i].value not in {"on", "{"} else "<unnamed>"
            elif name_i < n: name = tokens[name_i].value
            else: i += 1; continue
            if kind == "typedef":
                symbols.append(SymbolRecord(path, name, "typedef", t.line, _statement_end(tokens, i)))
                i += 1; continue
            sym_kind = "extension" if kind == "extension" else kind
            end_i = _body_end(tokens, i)
            end_line = tokens[end_i].line if end_i is not None else t.line
            symbols.append(SymbolRecord(path, name, sym_kind, t.line, end_line))
            if end_i is not None:
                scopes.append((name, brace_depth + 1))
            i += 1; continue
        # Directives begin at a statement boundary and can span lines.
        if scope is None and t.value in {"import", "export", "part"}:
            end = i
            while end < n and tokens[end].value != ";": end += 1
            chunk = tokens[i:end]
            uri_token = next((x.value for x in chunk if x.value.startswith("'") or x.value.startswith('"')), None)
            uri = uri_token[1:-1] if uri_token else None
            if uri:
                show = []
                for p, token in enumerate(chunk):
                    if token.value == "show":
                        j = p + 1
                        while j < len(chunk) and chunk[j].value not in {"hide", "as", "if"}:
                            if chunk[j].value not in {",", "{", "}"}: show.append(chunk[j].value)
                            j += 1
                imports.append(ImportRecord(path, uri, tuple(sorted(set(show))), 0, t.line))
            i = min(end + 1, n); continue
        # Declaration candidates only at a member/top-level statement boundary.
        if t.value.isidentifier() and t.value not in _CONTROL and t.value not in _MODIFIERS:
            end = _function_end(tokens, i)
            if end is not None:
                name = t.value if scope is None else f"{scope}.{t.value}"
                kind = "function" if scope is None else "method"
                symbols.append(SymbolRecord(path, name, kind, t.line, tokens[end].line))
        brace_depth += 1 if t.value == "{" else 0
        i += 1
    return symbols, imports


def _matching(tokens: list[_Token], pos: int, left: str, right: str) -> int | None:
    depth = 0
    for i in range(pos, len(tokens)):
        if tokens[i].value == left: depth += 1
        elif tokens[i].value == right:
            depth -= 1
            if depth == 0: return i
    return None


def _body_end(tokens: list[_Token], pos: int) -> int | None:
    for i in range(pos, len(tokens)):
        if tokens[i].value == "{": return _matching(tokens, i, "{", "}")
        if tokens[i].value == ";": return None
    return None


def _statement_end(tokens: list[_Token], pos: int) -> int:
    for i in range(pos, len(tokens)):
        if tokens[i].value == ";": return tokens[i].line
    return tokens[-1].line if tokens else tokens[pos].line


def _function_end(tokens: list[_Token], name_pos: int) -> int | None:
    if name_pos > 0 and tokens[name_pos - 1].value in {"get", "set"}:
        i = name_pos + 1
        while i < len(tokens) and tokens[i].value not in {"{", ";", "}"}: i += 1
        if i < len(tokens) and tokens[i].value == "{": return _matching(tokens, i, "{", "}")
        return i if i < len(tokens) and tokens[i].value == ";" else None
    if name_pos + 1 >= len(tokens) or tokens[name_pos + 1].value != "(": return None
    close = _matching(tokens, name_pos + 1, "(", ")")
    if close is None: return None
    i = close + 1
    while i < len(tokens) and tokens[i].value not in {"{", ";", "=", "}"}: i += 1
    if i < len(tokens) and tokens[i].value == "{": return _matching(tokens, i, "{", "}")
    if i < len(tokens) and tokens[i].value == "=" and i + 1 < len(tokens) and tokens[i + 1].value == ">":
        while i < len(tokens) and tokens[i].value not in {";", "}"}: i += 1
        return i if i < len(tokens) and tokens[i].value == ";" else None
    return None
