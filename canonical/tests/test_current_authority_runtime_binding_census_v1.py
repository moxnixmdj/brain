from __future__ import annotations

import json
from pathlib import Path

from canonical.runtime.current_authority_runtime_binding_census_v1 import (
    git_blob_sha,
    run,
)


def _write(root: Path, rel: str, content: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _authority(root: Path, payload: dict) -> Path:
    return _write(
        root,
        "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
        json.dumps(payload, indent=2) + "\n",
    )


def test_exact_current_binding_passes_and_superseded_stale_binding_is_ignored(tmp_path):
    runtime = _write(tmp_path, "canonical/runtime/a.py", "x = 1\n")
    _authority(
        tmp_path,
        {
            "current": {
                "runtime": {
                    "path": "canonical/runtime/a.py",
                    "git_blob_sha": git_blob_sha(runtime),
                }
            },
            "historical": {
                "status": "SUPERSEDED_RUNTIME_BINDING__EVIDENCE_RETAINED",
                "runtime": {
                    "path": "canonical/runtime/a.py",
                    "git_blob_sha": "0" * 40,
                },
            },
        },
    )
    out = run(tmp_path)
    assert out["pass"] is True, out
    assert out["current_binding_count"] == 1
    assert out["superseded_binding_count"] == 1
    assert out["drift_count"] == 0


def test_stale_current_binding_fails_closed(tmp_path):
    _write(tmp_path, "canonical/runtime/a.py", "x = 1\n")
    _authority(
        tmp_path,
        {
            "current": {
                "runtime": {
                    "path": "canonical/runtime/a.py",
                    "git_blob_sha": "0" * 40,
                }
            }
        },
    )
    out = run(tmp_path)
    assert out["pass"] is False
    assert out["drift_count"] == 1
    assert out["errors"][0]["kind"] == "RUNTIME_BLOB_DRIFT"


def test_missing_current_blob_binding_fails_closed(tmp_path):
    _write(tmp_path, "canonical/runtime/a.py", "x = 1\n")
    _authority(
        tmp_path,
        {"current": {"runtime": {"path": "canonical/runtime/a.py"}}},
    )
    out = run(tmp_path)
    assert out["pass"] is False
    assert out["missing_blob_binding_count"] == 1


def test_conflicting_non_superseded_bindings_fail_closed(tmp_path):
    runtime = _write(tmp_path, "canonical/runtime/a.py", "x = 1\n")
    good = git_blob_sha(runtime)
    _authority(
        tmp_path,
        {
            "one": {
                "runtime": {
                    "path": "canonical/runtime/a.py",
                    "git_blob_sha": good,
                }
            },
            "two": {
                "runtime": {
                    "path": "canonical/runtime/a.py",
                    "git_blob_sha": "f" * 40,
                }
            },
        },
    )
    out = run(tmp_path)
    assert out["pass"] is False
    assert out["conflicting_current_path_count"] == 1


def test_missing_runtime_file_fails_closed(tmp_path):
    _authority(
        tmp_path,
        {
            "current": {
                "runtime": {
                    "path": "canonical/runtime/missing.py",
                    "git_blob_sha": "a" * 40,
                }
            }
        },
    )
    out = run(tmp_path)
    assert out["pass"] is False
    assert out["missing_runtime_file_count"] == 1


def test_non_runtime_paths_are_ignored(tmp_path):
    _authority(
        tmp_path,
        {
            "governance": {
                "path": "canonical/governance/OTHER.json",
                "git_blob_sha": "0" * 40,
            }
        },
    )
    out = run(tmp_path)
    assert out["pass"] is True
    assert out["runtime_binding_reference_count"] == 0


def test_runtime_path_regex_matches_canonical_python_path():
    from canonical.runtime.current_authority_runtime_binding_census_v1 import (
        RUNTIME_PATH_RE,
    )

    assert RUNTIME_PATH_RE.fullmatch("canonical/runtime/a.py")
    assert RUNTIME_PATH_RE.fullmatch(
        "canonical/runtime/nested/example_v1.py"
    )
    assert not RUNTIME_PATH_RE.fullmatch(
        "canonical/governance/example.json"
    )
