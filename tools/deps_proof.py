"""Dependency-proof generator.

Scans every .py file in the project (excluding __pycache__ and .git) and
asserts that every import resolves either to (a) the Python standard
library, or (b) a module inside this project. If any third-party import
is found - or if requirements.txt lists anything - it fails with exit
code 1 and a human-readable failure line.

Regenerate the submitted proof artifact with:

    python tools/deps_proof.py > deps-proof.txt

This tool itself imports only the standard library (ast, pathlib, sys).
"""

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", "__pycache__"}

# Top-level import names that resolve to this project (not the stdlib).
LOCAL_TOP_LEVELS = {
    "main", "detective", "tests",
    "game", "mystery", "evidence", "characters", "world",
    "deduction", "storage", "tools", "ui",
}


def iter_project_files():
    for path in ROOT.rglob("*.py"):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        yield path


def collect_top_level_imports():
    """Every top-level module name imported anywhere in the project."""
    imports = set()
    for path in iter_project_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
    return imports


def requirements_packages_ignore_comments():
    """Non-comment, non-blank lines in requirements.txt, if the file exists."""
    req = ROOT / "requirements.txt"
    if not req.exists():
        return []
    entries = []
    for line in req.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        entries.append(stripped)
    return entries


def check_requirements(entries):
    """Fail loudly if requirements.txt lists a single package."""
    return [] if not entries else \
        [f"requirements.txt lists: {entries[0]!r}"]


def classify(imports):
    """Return (ok, failures) where failures are human-readable lines."""
    failures = []
    for name in sorted(imports):
        if name in LOCAL_TOP_LEVELS:
            print(f"  local   {name}")
        elif name in sys.stdlib_module_names:
            print(f"  stdlib  {name}")
        else:
            failures.append(f"third-party import: {name!r}")
    return failures


def main() -> int:
    imports = collect_top_level_imports()
    py_files = list(iter_project_files())

    print("Dependency proof: The Last Detective")
    print("=" * 44)
    print(f"Source files scanned: {len(py_files)}")
    print(f"Unique top-level imports: {len(imports)}")
    print()
    print("Import classification (stdlib vs local project):")

    failures = classify(imports)

    req_failures = check_requirements(requirements_packages_ignore_comments())
    failures.extend(req_failures)
    for line in req_failures:
        print(f"  FAIL    {line}")

    print()
    if failures:
        print(f"FAIL: {len(failures)} third-party reference(s) found.")
        for line in failures:
            print(f"  - {line}")
        return 1

    print("OK: every import is the Python standard library or this project.")
    print("Zero third-party runtime dependencies.")
    return 0


if __name__ == "__main__":
    sys.exit(main())