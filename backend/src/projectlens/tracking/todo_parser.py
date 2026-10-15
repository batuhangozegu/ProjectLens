"""Pure parser for Markdown roadmap checklists.

Only ATX headings (# through ######) create sections; Setext headings are not
supported. A final parenthesized heading note (for example ``(sıradaki adım)``)
is removed from the section identity, but earlier parentheses are retained.
Indented checklist children are flat items and keep their heading's section
path; parent titles do not enter a key unless identical sibling titles require
the occurrence disambiguator. Keys use NFKC then casefold, preserving Turkish
dotless ``ı`` separately from ``i`` (and the combining dot produced by casefold
of ``İ``). Thus distinct Turkish spellings are not conflated. A title edit
changes its key and is treated as a new imported item.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import unicodedata
from pathlib import Path

MAX_CHECKLIST_FILE_BYTES = 1024 * 1024


class ChecklistError(ValueError):
    """Raised when a checklist file cannot safely be read or decoded."""


@dataclass(frozen=True)
class ChecklistDiagnostic:
    severity: str
    message: str
    line: int | None = None


@dataclass(frozen=True)
class ChecklistItem:
    section_path: tuple[str, ...]
    title: str
    checked: bool
    line: int
    source_key: str
    depth: int


@dataclass(frozen=True)
class ParsedChecklist:
    items: tuple[ChecklistItem, ...]
    diagnostics: tuple[ChecklistDiagnostic, ...]


_HEADING = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+|$)(.*?)[ \t]*#*[ \t]*$")
_ITEM = re.compile(r"^(?P<indent>[ \t]*)[-*+]\s+\[(?P<checked>[ xX])\](?P<tail>.*)$")
_FINAL_NOTE = re.compile(r"\s*\([^()]*\)\s*$")


def _normal(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _key(section: tuple[str, ...], title: str, occurrence: int) -> str:
    identity = "\x1f".join((*(_normal(part) for part in section), _normal(title)))
    digest = hashlib.sha256(f"{identity}\x1f{occurrence}".encode("utf-8")).hexdigest()[:12]
    # Human-readable, ASCII-safe prefix; digest preserves distinctions lost by slugging.
    prefix = re.sub(r"[^a-z0-9]+", "-", identity.encode("ascii", "ignore").decode()).strip("-")
    prefix = prefix[:80].rstrip("-") or "item"
    return f"{prefix}-{digest}"


def parse_checklist(text: str) -> ParsedChecklist:
    """Parse checklist items, section paths, and non-fatal diagnostics."""
    if not isinstance(text, str):
        raise TypeError("text must be str")
    lines = text.splitlines()
    headings: list[tuple[int, str]] = []
    raw_items: list[tuple[tuple[str, ...], str, bool, int, int]] = []
    diagnostics: list[ChecklistDiagnostic] = []
    in_comment = False
    fence_char: str | None = None
    fence_size = 0

    for number, line in enumerate(lines, 1):
        if fence_char is not None:
            close = re.match(rf"^ {{0,3}}{re.escape(fence_char)}{{{fence_size},}}[ \t]*$", line)
            if close:
                fence_char = None
            continue

        # Remove HTML comment spans while retaining visible text around them.
        visible: list[str] = []
        pos = 0
        while pos < len(line):
            if in_comment:
                end = line.find("-->", pos)
                if end < 0:
                    pos = len(line)
                    break
                in_comment = False
                pos = end + 3
            else:
                start = line.find("<!--", pos)
                if start < 0:
                    visible.append(line[pos:])
                    break
                visible.append(line[pos:start])
                end = line.find("-->", start + 4)
                if end < 0:
                    in_comment = True
                    pos = len(line)
                else:
                    pos = end + 3
        clean = "".join(visible).rstrip()
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", clean)
        if marker:
            fence_char, fence_size = marker.group(1)[0], len(marker.group(1))
            continue
        heading = _HEADING.match(clean)
        if heading:
            level = len(heading.group(1))
            name = heading.group(2).strip()
            name = _FINAL_NOTE.sub("", name).strip()
            headings = [(n, label) for n, label in headings if n < level]
            if name:
                headings.append((level, name))
            else:
                headings.append((level, ""))
            continue
        item = _ITEM.match(clean)
        if not item:
            continue
        title = " ".join(item.group("tail").split())
        section = tuple(label for _, label in headings if label)
        indent = len(item.group("indent").expandtabs(4))
        depth = indent // 2
        if not section:
            diagnostics.append(ChecklistDiagnostic("info", "Checklist item appears before any heading", number))
        if not title:
            diagnostics.append(ChecklistDiagnostic("warning", "Checklist item has an empty title and was skipped", number))
            continue
        raw_items.append((section, title, item.group("checked").lower() == "x", number, depth))

    if fence_char is not None:
        diagnostics.append(ChecklistDiagnostic("warning", "Unterminated code fence; remaining lines were treated as code", len(lines) or 1))

    counts: dict[tuple[str, str], int] = {}
    totals: dict[tuple[str, str], int] = {}
    for section, title, *_ in raw_items:
        pair = ("\x1f".join(_normal(part) for part in section), _normal(title))
        totals[pair] = totals.get(pair, 0) + 1
    items: list[ChecklistItem] = []
    for section, title, checked, line_no, depth in raw_items:
        pair = ("\x1f".join(_normal(part) for part in section), _normal(title))
        occurrence = counts.get(pair, 0) + 1
        counts[pair] = occurrence
        if totals[pair] > 1:
            diagnostics.append(ChecklistDiagnostic("info", f"Duplicate checklist title disambiguated as occurrence {occurrence}", line_no))
        items.append(ChecklistItem(section, title, checked, line_no, _key(section, title, occurrence if totals[pair] > 1 else 0), depth))
    return ParsedChecklist(tuple(items), tuple(diagnostics))


def parse_checklist_file(path: str | Path) -> ParsedChecklist:
    """Read and parse a UTF-8 (optionally BOM-prefixed) checklist file."""
    source = Path(path)
    try:
        if source.stat().st_size > MAX_CHECKLIST_FILE_BYTES:
            raise ChecklistError(f"Checklist file exceeds {MAX_CHECKLIST_FILE_BYTES} byte limit: {source}")
        data = source.read_bytes()
    except ChecklistError:
        raise
    except OSError as exc:
        raise ChecklistError(f"Cannot read checklist file {source}: {exc.strerror or exc}") from None
    if len(data) > MAX_CHECKLIST_FILE_BYTES:
        raise ChecklistError(f"Checklist file exceeds {MAX_CHECKLIST_FILE_BYTES} byte limit: {source}")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ChecklistError(f"Checklist file is not valid UTF-8: {source}") from None
    return parse_checklist(text)
