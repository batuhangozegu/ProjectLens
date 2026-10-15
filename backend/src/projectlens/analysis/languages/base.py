"""Protocol implemented by language-specific source parsers."""

from typing import Protocol

from projectlens.analysis.models import ParsedFile


class LanguageParser(Protocol):
    def supports(self, path: str) -> bool:
        """Return whether this parser handles the given repository-relative path."""

    def parse(self, path: str, source: str) -> ParsedFile:
        """Parse source text for a repository-relative path."""
