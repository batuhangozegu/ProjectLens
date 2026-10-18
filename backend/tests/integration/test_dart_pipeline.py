import shutil
from pathlib import Path

from projectlens.analysis.models import AnalysisOptions
from projectlens.analysis.pipeline import analyze


FIXTURE = Path(__file__).parents[1] / "fixtures" / "dart_repo"
GRAPH_FIXTURE = Path(__file__).parents[1] / "fixtures" / "dart_dependency_repo"


def test_dart_fixture_pipeline_and_determinism(tmp_path):
    first = analyze(AnalysisOptions(str(FIXTURE)))
    copied = tmp_path / "dart_repo"
    shutil.copytree(FIXTURE, copied)
    second = analyze(AnalysisOptions(str(copied)))
    assert first.to_json() == second.to_json()
    records = {item.path: item for item in first.files}
    assert records["lib/main.dart"].language == "dart"
    assert records["lib/main.dart"].file_class == "dart_source"
    assert records["test/user_test.dart"].file_class == "test"
    assert records["pubspec.yaml"].file_class == "config"
    assert records["lib/broken.dart"].analysis_status == "parse_failed"
    assert [(edge.source, edge.target) for edge in first.dependency_edges] == [
        ("lib/main.dart", "lib/src/widgets/home.dart"),
        ("lib/src/widgets/home.dart", "lib/src/models/user.dart"),
        ("test/user_test.dart", "lib/src/models/user.dart"),
    ]
    assert first.metrics["total_file_count"] == 7
    assert first.metrics["physical_loc"]["total"] > 0
    assert first.metrics["python_loc"]["total"] == 0
    assert first.metrics["comment_markers"]["by_kind"]["TODO"] >= 1
    assert first.partial


def test_mixed_python_dart_graph_and_repeat_stability(tmp_path):
    (tmp_path / "pubspec.yaml").write_text("name: mixed_app\n", encoding="utf-8")
    (tmp_path / "py.py").write_text("import helper\n", encoding="utf-8")
    (tmp_path / "helper.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "main.dart").write_text("import 'part.dart';\n", encoding="utf-8")
    (tmp_path / "lib" / "part.dart").write_text("class Part {}\n", encoding="utf-8")
    first = analyze(AnalysisOptions(str(tmp_path)))
    second = analyze(AnalysisOptions(str(tmp_path)))
    assert first.to_json() == second.to_json()
    assert [(edge.source, edge.target) for edge in first.dependency_edges] == [
        ("lib/main.dart", "lib/part.dart"), ("py.py", "helper.py")
    ]
    assert first.metrics["dependencies"]["edge_count"] == 2


def test_dart_dependency_fixture_covers_directives_and_diagnostics():
    result = analyze(AnalysisOptions(str(GRAPH_FIXTURE)))
    assert [(edge.source, edge.target) for edge in result.dependency_edges] == [
        ("lib/main.dart", "lib/part.dart"),
        ("lib/main.dart", "lib/src/a.dart"),
        ("lib/main.dart", "lib/src/api.dart"),
        ("lib/part.dart", "lib/main.dart"),
        ("lib/src/a.dart", "lib/src/b.dart"),
        ("lib/src/b.dart", "lib/src/a.dart"),
    ]
    assert ("lib/src/a.dart", "lib/src/b.dart") in [(a, b) for cycle in result.cycles for a, b in zip(cycle, cycle[1:])]
    assert {item["kind"] for item in result.external_imports} == {"dart_sdk", "package"}
    assert {item["kind"] for item in result.unresolved_imports} == {"path_escapes_repository"}
    assert all("lib/isolated.dart" not in (edge.source, edge.target) for edge in result.dependency_edges)
