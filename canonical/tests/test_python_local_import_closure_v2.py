from pathlib import Path
import tempfile
from canonical.runtime.python_local_import_closure_v2 import compute

def test_namespace_package_from_import_is_resolved_to_child_module():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        (root/"canonical/runtime").mkdir(parents=True)
        (root/"canonical/tests").mkdir(parents=True)
        (root/"canonical/runtime/child.py").write_text("VALUE=1\n",encoding="utf-8")
        (root/"canonical/runtime/main.py").write_text(
            "from canonical.runtime import child\nX=child.VALUE\n",encoding="utf-8"
        )
        out=compute("canonical/runtime/main.py",repo_root=root)
        assert out["pass"] is True, out
        paths={x["path"] for x in out["dependencies"]}
        assert "canonical/runtime/main.py" in paths
        assert "canonical/runtime/child.py" in paths
        assert all(not p.endswith("__init__.py") for p in paths)

def test_missing_non_namespace_base_still_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        (root/"canonical/runtime").mkdir(parents=True)
        (root/"canonical/runtime/main.py").write_text(
            "from canonical.missing import child\n",encoding="utf-8"
        )
        out=compute("canonical/runtime/main.py",repo_root=root)
        assert out["pass"] is False
        assert any("LOCAL_IMPORT_UNRESOLVED:canonical.missing" in x for x in out["errors"])
