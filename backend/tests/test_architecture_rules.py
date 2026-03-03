from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULES_ROOT = PROJECT_ROOT / "app" / "modules"


def _iter_python_files(path: Path):
    for file_path in path.rglob("*.py"):
        if "__pycache__" in file_path.parts:
            continue
        yield file_path


def test_domain_layers_do_not_import_frameworks():
    forbidden = ("fastapi", "sqlalchemy", "httpx", "langchain", "langgraph")
    domain_paths = [p for p in MODULES_ROOT.rglob("domain") if p.is_dir()]

    violations = []
    for domain_path in domain_paths:
        for py_file in _iter_python_files(domain_path):
            content = py_file.read_text(encoding="utf-8")
            for bad in forbidden:
                if f"import {bad}" in content or f"from {bad}" in content:
                    violations.append(f"{py_file}: imports {bad}")

    assert not violations, "Domain layer import violations:\n" + "\n".join(violations)


def test_no_runtime_dependency_on_legacy_services():
    # Any non-legacy file referencing app.services means architectural regression.
    violations = []
    for py_file in _iter_python_files(PROJECT_ROOT / "app"):
        if "services" in py_file.parts:
            continue
        content = py_file.read_text(encoding="utf-8")
        if "app.services" in content or "from .services" in content or "from ..services" in content:
            violations.append(str(py_file))

    assert not violations, "Unexpected dependency on app.services in:\n" + "\n".join(violations)
