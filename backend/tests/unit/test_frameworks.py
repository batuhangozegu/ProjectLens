from projectlens.analysis.frameworks import detect_frameworks


def detected(path, content):
    return {(item.name, item.ecosystem, item.evidence_file) for item in detect_frameworks(((path, content),))}


def test_pyproject_pep621_poetry_extras_markers_and_quoted_names():
    content = '''\ufeff[project]\r\nname = "demo"\r\ndependencies = ["fastapi[all]>=0.1", "pytest; python_version >= '3.10'", "unknown"]\r\n[project.optional-dependencies]\r\ntest = [\r\n  "Django>=4"\r\n]\r\n[tool.poetry.dependencies]\r\nFlask = "*"\r\n'''
    assert detected("pyproject.toml", content) == {
        ("FastAPI", "python", "pyproject.toml"), ("pytest", "python", "pyproject.toml"),
        ("Django", "python", "pyproject.toml"), ("Flask", "python", "pyproject.toml"),
    }


def test_requirements_comments_markers_extras_and_setup_cfg():
    requirements = "\ufeff# comment\r\nfastapi[all]>=1 # inline comment\r\npytest; python_version >= '3.10'\r\n-e .\r\nunknown\r\n"
    assert detected("requirements-dev.txt", requirements) == {
        ("FastAPI", "python", "requirements-dev.txt"), ("pytest", "python", "requirements-dev.txt"),
    }
    setup = "[metadata]\nname = demo\n[options]\ninstall_requires =\n    Django>=4\n    sqlalchemy[asyncio]\n"
    assert detected("setup.cfg", setup) == {
        ("Django", "python", "setup.cfg"), ("SQLAlchemy", "python", "setup.cfg"),
    }


def test_pubspec_sdk_and_state_management_records_are_individual():
    content = """name: demo
dependencies:
  flutter:
    sdk: flutter
  flutter_riverpod: ^2.0 # state
  provider: ^6
dev_dependencies:
  flutter_test:
    sdk: flutter
"""
    result = detect_frameworks((("app/pubspec.yaml", content),))
    assert [(item.name, item.evidence_file) for item in result] == [
        ("Flutter", "app/pubspec.yaml"), ("Flutter Riverpod", "app/pubspec.yaml"),
        ("Flutter Test", "app/pubspec.yaml"), ("Provider", "app/pubspec.yaml"),
    ]


def test_malformed_and_unknown_manifest_lines_are_ignored():
    assert detect_frameworks((("requirements.txt", "not a package\n???\n"), ("pyproject.toml", "[broken\nfastapi"))) == ()


def test_detection_is_deterministic_and_evidence_is_bounded():
    manifest = "fastapi>=1 " + "x" * 400
    first = detect_frameworks((("requirements.txt", manifest),))
    second = detect_frameworks(reversed((("requirements.txt", manifest),)))
    assert first == second
    assert len(first[0].evidence) <= 240
