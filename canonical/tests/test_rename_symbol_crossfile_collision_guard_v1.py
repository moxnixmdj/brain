"""Do not redirect cross-file uses to an existing replacement binding."""
import pytest

from canonical.runtime.bound_capabilities import python_refactor_rename_symbol as rename


@pytest.mark.parametrize("body", [
    "new_name = lambda x: 99\ndef use():\n    return old_name(2)\n",
    "from other_module import other as new_name\ndef use():\n    return old_name(2)\n",
    "def use(new_name):\n    return old_name(2)\n",
    "def use():\n    if True:\n        new_name = lambda x: 99\n    return old_name(2)\n",
])
def test_crossfile_replacement_name_collisions_refused_before_edits(tmp_path, body):
    src = tmp_path / "src"
    (src / "pkg").mkdir(parents=True)
    (src / "pkg/__init__.py").write_text("")
    core = src / "pkg/core.py"
    core.write_text("def old_name(x):\n    return x + 1\n")
    caller = src / "caller.py"
    caller.write_text("from pkg.core import old_name\n\n" + body)
    originals = (core.read_bytes(), caller.read_bytes())
    with pytest.raises(SystemExit, match="REFUSE_CROSSFILE_"):
        rename.run({"source_root": "src", "module": "pkg/core.py", "qualname": "old_name",
                    "new_symbol": "new_name", "output_path": "out/rename.json"}, tmp_path)
    assert (core.read_bytes(), caller.read_bytes()) == originals
