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


def test_v3_json_keeps_version_and_defaults_new_fields():
    old = sample_result().to_dict()
    old["schema_version"] = "3"
    old.pop("frameworks")
    old.pop("test_matches")
    restored = AnalysisResult.from_dict(old)
    assert restored.schema_version == "3"
    assert restored.frameworks == ()
    assert restored.test_matches == ()
    assert restored.to_dict()["schema_version"] == "3"
