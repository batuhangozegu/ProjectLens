import shutil
from pathlib import Path

from projectlens.analysis.models import AnalysisOptions
from projectlens.analysis.pipeline import analyze


FIXTURE = Path(__file__).parents[1] / "fixtures" / "dart_repo"


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
    assert first.dependency_edges == ()
    assert first.metrics["total_file_count"] == 7
    assert first.metrics["physical_loc"]["total"] > 0
    assert first.metrics["python_loc"]["total"] == 0
    assert first.metrics["comment_markers"]["by_kind"]["TODO"] >= 1
    assert first.partial
