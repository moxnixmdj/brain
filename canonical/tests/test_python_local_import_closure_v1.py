from pathlib import Path

from canonical.runtime.python_local_import_closure_v1 import compute


def test_transitive_local_import_is_bound(tmp_path: Path):
    root = tmp_path
    (root / "canonical/runtime").mkdir(parents=True)
    (root / "canonical/runtime/a.py").write_text(
        "from canonical.runtime.b import f\n", encoding="utf-8"
    )
    (root / "canonical/runtime/b.py").write_text(
        "import math\ndef f(): return 1\n", encoding="utf-8"
    )
    out = compute("canonical/runtime/a.py", repo_root=root)
    assert out["pass"] is True, out
    assert [x["path"] for x in out["dependencies"]] == [
        "canonical/runtime/a.py",
        "canonical/runtime/b.py",
    ]


def test_dynamic_import_fails_closed(tmp_path: Path):
    root = tmp_path
    (root / "canonical/runtime").mkdir(parents=True)
    (root / "canonical/runtime/a.py").write_text(
        "import importlib\nx=importlib.import_module('canonical.runtime.b')\n",
        encoding="utf-8",
    )
    (root / "canonical/runtime/b.py").write_text("x=1\n", encoding="utf-8")
    out = compute("canonical/runtime/a.py", repo_root=root)
    assert out["pass"] is False
    assert any("DYNAMIC_IMPORT_UNSUPPORTED" in x for x in out["errors"])


def test_unresolved_canonical_import_fails_closed(tmp_path: Path):
    root = tmp_path
    (root / "canonical/runtime").mkdir(parents=True)
    (root / "canonical/runtime/a.py").write_text(
        "from canonical.runtime.missing import x\n", encoding="utf-8"
    )
    out = compute("canonical/runtime/a.py", repo_root=root)
    assert out["pass"] is False
    assert "LOCAL_IMPORT_UNRESOLVED:canonical.runtime.missing" in out["errors"]
