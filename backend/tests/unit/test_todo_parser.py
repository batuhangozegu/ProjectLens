import re
import unicodedata
from pathlib import Path

import pytest

from projectlens.tracking.todo_parser import ChecklistError, parse_checklist, parse_checklist_file


def test_real_todo_checklist_structure():
    root = Path(__file__).resolve().parents[3]
    text = (root / "TODO.md").read_text(encoding="utf-8-sig")
    # Independent count of checkbox-shaped list entries outside fenced blocks.
    outside = []
    fenced = False
    for line in text.splitlines():
        if re.match(r"^ {0,3}(`{3,}|~{3,})", line):
            fenced = not fenced
            continue
        if not fenced:
            outside.append(line)
    expected = sum(bool(re.match(r"^[ \t]*[-*+]\s+\[[ xX]\]", line)) for line in outside)
    first = parse_checklist(text)
    assert len(first.items) == expected
    assert parse_checklist(text) == first
    keys = [item.source_key for item in first.items]
    assert len(keys) == len(set(keys))
    assert all(key.isascii() and len(key) <= 120 for key in keys)
    assert all("(sıradaki adım)" not in part for item in first.items for part in item.section_path)


def test_headings_notes_bullets_and_nested_items():
    parsed = parse_checklist("""# A (sıradaki adım)
plain bullet
- [ ] root   title
  * [X] child **kept**
    + [x] grand\n## B (not a section note)\n- [ ] item
""")
    assert [i.section_path for i in parsed.items] == [("A",), ("A",), ("A",), ("A", "B")]
    assert [i.depth for i in parsed.items] == [0, 1, 2, 0]
    assert parsed.items[1].title == "child **kept**"
    assert parsed.items[2].checked is True


def test_fences_comments_and_unterminated_fence():
    text = """- [ ] visible
```md
- [ ] hidden
```
<!-- - [ ] also hidden -->
<!-- start
- [ ] hidden too
end -->
- [ ] shown
```
- [ ] under unterminated
"""
    parsed = parse_checklist(text)
    assert [i.title for i in parsed.items] == ["visible", "shown"]
    assert any(d.severity == "warning" and "Unterminated" in d.message for d in parsed.diagnostics)


def test_keys_stable_across_formatting_check_and_move_and_distinguish_title():
    a = parse_checklist("# S\n- [ ] Alpha   beta\n- [ ] elsewhere\n")
    b = parse_checklist("# S\r\n- [x] elsewhere\r\n- [X] Alpha beta   \r\n")
    assert a.items[0].source_key == b.items[1].source_key
    assert parse_checklist("# S\n- [x] Alpha beta\n").items[0].source_key == a.items[0].source_key
    assert parse_checklist("# S\n- [ ] Changed\n").items[0].source_key != a.items[0].source_key


def test_duplicate_occurrences_and_sections():
    parsed = parse_checklist("# S\n- [ ] Same\n- [ ] Same\n# T\n- [ ] Same\n")
    assert len({i.source_key for i in parsed.items}) == 3
    assert sum("Duplicate" in d.message for d in parsed.diagnostics) == 2
    assert parsed.items[0].source_key != parsed.items[1].source_key


def test_turkish_casefold_policy_and_unicode_canonical_equivalence():
    parsed = parse_checklist("# İ\n- [ ] İ\n- [ ] I\n- [ ] ı\n- [ ] i\n")
    keys = [i.source_key for i in parsed.items]
    assert len(set(keys)) == 4
    composed = "é"
    decomposed = unicodedata.normalize("NFD", composed)
    assert parse_checklist(f"- [ ] {composed}").items[0].source_key == parse_checklist(f"- [ ] {decomposed}").items[0].source_key


def test_empty_titles_pre_heading_empty_input_and_headings_only():
    parsed = parse_checklist("- [ ]\n# Heading\n## Child\n")
    assert parsed.items == ()
    assert len(parsed.diagnostics) == 2
    assert parse_checklist("").items == ()


def test_setext_not_supported_and_long_line():
    parsed = parse_checklist("Title\n=====\n- [ ] " + "x" * 100_000)
    assert parsed.items[0].section_path == ()
    assert len(parsed.items[0].title) == 100_000


def test_file_reader_bom_size_and_invalid_bytes(tmp_path):
    good = tmp_path / "good.md"
    good.write_bytes(b"\xef\xbb\xbf- [ ] ok\r\n")
    assert parse_checklist_file(good).items[0].title == "ok"
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"\xff\xfe\x00\x80")
    with pytest.raises(ChecklistError, match="valid UTF-8"):
        parse_checklist_file(bad)
    huge = tmp_path / "huge.md"
    huge.write_bytes(b"x" * (1024 * 1024 + 1))
    with pytest.raises(ChecklistError, match="exceeds"):
        parse_checklist_file(huge)
    with pytest.raises(ChecklistError, match="Cannot read"):
        parse_checklist_file(tmp_path / "missing.md")
