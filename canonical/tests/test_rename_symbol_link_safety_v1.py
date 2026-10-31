"""A repository rename must not alter files through external links."""
import os

import pytest

from canonical.runtime.bound_capabilities import python_refactor_rename_symbol as rename


@pytest.mark.parametrize("link_kind,relative", [
    ("symlink", "caller.py"), ("symlink", "consumer/reader.py"),
    ("hardlink", "caller.py"), ("hardlink", "consumer/reader.py"),
])
def test_linked_python_file_is_refused_before_any_write(tmp_path, link_kind, relative):
    root = tmp_path / "repo"
    src = root / "src"
    (src / "pkg").mkdir(parents=True)
    (src / "pkg/__init__.py").write_text("")
    core = src / "pkg/core.py"
    core.write_text("def old_name(x):\n    return x + 1\n")
    external = tmp_path / "outside.py"
    external.write_text("from pkg.core import old_name\n\ndef call():\n    return old_name(3)\n")
    link = src / relative
    link.parent.mkdir(parents=True, exist_ok=True)
    if link_kind == "symlink":
        link.symlink_to(external)
    else:
        os.link(external, link)
    original_core, original_external = core.read_bytes(), external.read_bytes()
    try:
        rename.run({"source_root": "src", "module": "pkg/core.py", "qualname": "old_name",
                    "new_symbol": "new_name", "output_path": "out/report.json"}, root)
    except SystemExit as exc:
        assert "REFUSE_LINKED_PYTHON_FILE" in str(exc.code)
    assert external.read_bytes() == original_external
    assert core.read_bytes() == original_core
    assert not (root / "out/report.json").exists()
