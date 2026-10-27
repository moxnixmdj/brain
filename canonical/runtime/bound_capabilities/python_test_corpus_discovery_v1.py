"""Which files in a source tree are tests. One rule, one place.

Eleven bound capabilities refuse with ``TEST_PATHS_REQUIRED`` when the caller
does not hand them a list of test files:

    python_coupled_software_repair_loop_v1.py:158
    python_dynamic_fault_localizer_v1.py:99
    python_interprocedural_value_provenance_v1.py:140
    python_iterative_software_repair_loop_v1.py:76
    python_provenance_guided_coupled_repair_v1.py:69
    python_repair_apply_verified_v1.py:130
    python_repair_measured_acceptance_controller_v1.py:216
    python_repair_semantic_acceptance_controller_v1.py:36
    python_repository_acceptance_measurement_v1.py:191
    python_software_repair_loop_v1.py:59
    python_test_guided_patch_search_v1.py:368

Every one of them already builds the test COMMAND itself when it is not stated --
each calls ``suite_argv(sys.executable, *tests)`` on the very next line -- because
executing a unittest file as a script only runs it when the file carries a
``__main__`` guard, and 695 of the 2019 unittest files in this repository do not.
So the command was never the missing input. The list of files was, and no
sentence states one: "repair the source root so the tests pass" names no file,
because which files are tests is a fact about the TREE.

Measured on main at c57b2173, that single omission is what keeps the whole repair
lane unreachable from the front door: "Repair the python source root <D> so the
test command passes" scores python.software.repair.loop.coupled.ast.v1 at 34,
ahead of the next candidate at 31, and is dropped as unbindable on
``test_paths:no_matching_existing_files_named`` -- so a weaker capability
substitutes and reports pass=True for a repair that never happened.

The name rule is not invented here. The repository already encodes it twice:
``python_change_impact_testselect.py:286`` selects on
``name.startswith("test_") or name.endswith("_test.py")``, and
``python_test_audit.py:116`` defaults its pattern to ``test_*.py``. This module
is the third and last copy: the other two should read it.
"""

from __future__ import annotations

import pathlib
from typing import Iterable

# Directories that hold copies, caches or third-party code rather than the sources
# under test. Measured on this repository: a walk that does not skip them measures
# vendored suites and .tox environments as if they were the project's own tests.
_SKIP_DIRS = frozenset({
    ".git", ".hg", ".svn", ".tox", ".nox", "node_modules", "__pycache__",
    ".venv", "venv", "env", "build", "dist", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", "site-packages",
})


def is_test_file_name(name: str) -> bool:
    """The repository's own rule for what a test file is called.

    ``python_change_impact_testselect.py:286`` selects on exactly this pair and
    ``python_test_audit.py:116`` defaults its glob to ``test_*.py``.
    """
    return name.startswith("test_") or name.endswith("_test.py")


def discover_test_files(source_root: pathlib.Path | str, limit: int = 5000) -> list[pathlib.Path]:
    """Every test file under ``source_root``, as absolute paths.

    Recursive, because the ordinary layout puts tests in a ``tests/`` directory
    and a top-level ``glob("test_*.py")`` finds none of them -- measured on the
    very tree this was first needed for. Sorted, so two runs over one tree agree
    and a content-addressed report is reproducible. Symlinks and non-regular
    files are skipped, because every consumer of this list applies its own
    containment and regular-file law and must not be handed a link out.

    Raises ``FileNotFoundError`` rather than returning an empty list when the tree
    holds no tests: an empty list would let a caller record ``test_count: 0`` with
    ``returncode: 0``, which is a green verdict for a suite that was never found.
    """
    root = pathlib.Path(source_root).resolve()
    found: list[pathlib.Path] = []
    for path in sorted(root.rglob("*.py")):
        try:
            parts = path.relative_to(root).parts
        except ValueError:  # pragma: no cover - rglob stays under root
            continue
        if any(part in _SKIP_DIRS for part in parts):
            continue
        if not is_test_file_name(path.name):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        found.append(path)
        if len(found) >= limit:
            break
    if not found:
        raise FileNotFoundError("NO_TEST_FILES_UNDER_SOURCE_ROOT:" + str(root))
    return found


def discover_test_paths(source_root: pathlib.Path | str, limit: int = 5000) -> list[str]:
    """The same files, spelled relative to ``source_root``.

    Two spellings of one answer, because consumers differ: the acceptance
    measurement records repository- or root-relative names in its content-addressed
    spec, while the repair loops resolve each name against the repository. Neither
    spelling is more true than the other, and refusing either one made a capability
    unreachable from the front door once already -- see the docstring of
    ``_validate_test_paths`` in python_repository_acceptance_measurement_v1.py.
    """
    root = pathlib.Path(source_root).resolve()
    return [str(p.relative_to(root)) for p in discover_test_files(root, limit=limit)]


def stated_or_discovered(
    source_root: pathlib.Path | str,
    stated: Iterable[str] | None,
    limit: int = 5000,
) -> tuple[list[pathlib.Path], str]:
    """The test files to use, and where they came from.

    Returns ``(files, provenance)`` where provenance is ``"stated"`` or
    ``"discovered_under_source_root"``. A report that says ``test_count: 1``
    without saying whether the caller named that one file or the tree supplied the
    whole suite leaves the reader unable to judge the measurement, so the
    provenance travels with the answer.
    """
    given = [str(x) for x in (stated or []) if str(x).strip()]
    if given:
        root = pathlib.Path(source_root).resolve()
        return [(root / x) for x in given], "stated"
    root = pathlib.Path(source_root).resolve()
    return discover_test_files(root, limit=limit), "discovered_under_source_root"
