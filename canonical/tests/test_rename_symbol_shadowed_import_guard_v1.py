"""A cross-file imported name can be shadowed by a local binding."""
import pytest

from canonical.runtime.bound_capabilities import python_refactor_rename_symbol as rename


@pytest.mark.parametrize("body", [
    "def use(old_name):\n    return old_name(2)\n",
    "use = lambda old_name: old_name(2)\n",
    "def use(flag):\n    if flag:\n        old_name = lambda x: x\n    return old_name(2)\n",
    "def use(funcs):\n    return [old_name(2) for old_name in funcs]\n",
])
def test_imported_symbol_shadow_is_not_renamed(tmp_path, body):
    src = tmp_path / "src"
    (src / "pkg").mkdir(parents=True)
    (src / "pkg/__init__.py").write_text("")
    core = src / "pkg/core.py"
    core.write_text("def old_name(x):\n    return x + 1\n")
    caller = src / "caller.py"
    original = "from pkg.core import old_name\n\n" + body
    caller.write_text(original)
    before_core = core.read_bytes()
    try:
        result = rename.run({"source_root": "src", "module": "pkg/core.py", "qualname": "old_name",
                             "new_symbol": "new_name", "output_path": "out/rename.json"}, tmp_path)
    except SystemExit as exc:
        assert "REFUSE_CROSSFILE_SHADOWED_BINDING" in str(exc.code)
        assert core.read_bytes() == before_core
        assert caller.read_text() == original
    else:
        assert result["verified"] is False
        assert caller.read_text().endswith(body)
        assert caller.read_text().startswith("from pkg.core import new_name\n")
