"""Analysis result contracts and interfaces."""

from projectlens.analysis.models import (
    SCHEMA_VERSION,
    AnalysisDiagnostic,
    AnalysisOptions,
    AnalysisResult,
    DependencyEdge,
    FileRecord,
    FrameworkRecord,
    ImportRecord,
    ParsedFile,
    SymbolRecord,
    TestMatchRecord,
)

__all__ = [
    "SCHEMA_VERSION",
    "AnalysisDiagnostic",
    "AnalysisOptions",
    "AnalysisResult",
    "DependencyEdge",
    "FileRecord",
    "FrameworkRecord",
    "ImportRecord",
    "ParsedFile",
    "SymbolRecord",
    "TestMatchRecord",
]
