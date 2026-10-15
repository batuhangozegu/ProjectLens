from projectlens.analysis.models import (
    SCHEMA_VERSION,
    AnalysisDiagnostic,
    AnalysisResult,
    DependencyEdge,
    FileRecord,
)


def sample_result() -> AnalysisResult:
    return AnalysisResult(
        files=(
            FileRecord("z.py", "python", "source", 8, "analyzed"),
            FileRecord("src\\a.py", "python", "source", 4, "analyzed"),
        ),
        dependency_edges=(DependencyEdge("z.py", "src\\a.py", 3),),
        cycles=(("z.py", "src\\a.py"),),
        metrics={"python_files": 2},
        diagnostics=(AnalysisDiagnostic("parse", "z.py", "SyntaxError", "invalid syntax"),),
    )


def test_result_json_round_trip_is_deterministic_and_paths_are_normalized() -> None:
    result = sample_result()
    serialized = result.to_json()

    assert AnalysisResult.from_json(serialized).to_json() == serialized
    assert serialized == sample_result().to_json()
    assert '"path":"src/a.py"' in serialized
    assert serialized.index('"path":"src/a.py"') < serialized.index('"path":"z.py"')


def test_schema_version_is_present() -> None:
    value = sample_result().to_dict()

    assert value["schema_version"] == SCHEMA_VERSION
