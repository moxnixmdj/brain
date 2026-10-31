"""Exact byte-preserving edits through the real planner and apply kernel."""
import json

import pytest

from canonical.runtime.bound_capabilities import python_issue_to_pr_orchestrate as orch
from canonical.runtime.bound_capabilities import python_crossfile_edit_choreograph as choreograph


@pytest.mark.parametrize("import_text", [
    "from pkg.core import (\n    other,  # helper in a comment is not a token\n    helper,\n)\n",
    "from pkg.core import (other,\n                      helper)\n",
    "from pkg.core import other, \\\n    helper\n",
    "from pkg.core import helper; answer = helper(' x ')\n",
    "from pkg.core import helper, other; answer = helper(' x ')\n",
    "label = 'é'; from pkg.core import helper; answer = helper(' x ')\n",
    "from pkg.core import helper; from pkg.core import helper\n",
    "from pkg.core import (\n    helper, helper,\n)\n",
])
def test_multiline_and_same_line_imports_preserve_unrelated_bytes(tmp_path, import_text):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg/__init__.py").write_text("")
    (tmp_path / "pkg/core.py").write_text("def helper(x):\n    return len(x)\nother = 1\n")
    usage = "\ndef use():\n    label = 'é'; return helper('a')\n"
    (tmp_path / "client.py").write_text(import_text + usage)
    op = {"op": "rename_symbol", "module": "pkg/core.py", "name": "helper", "new_name": "compute"}
    choreograph.run({"source_root": ".", "edits": json.dumps([op]), "output_path": "plan.json"}, tmp_path)
    plan = json.loads((tmp_path / "plan.json").read_bytes())
    assert plan["refused_op_count"] == 0
    assert plan["ambiguous_site_count"] == 0
    orch._apply_rename(tmp_path, op, plan["plans"][0])
    # Expected substitutions are independently explicit; never change comments.
    expected = import_text.replace("helper", "compute").replace(
        "# compute in a comment", "# helper in a comment")
    assert (tmp_path / "client.py").read_text() == expected + usage.replace("helper('a')", "compute('a')")
    assert orch._verify_application(tmp_path, [op]) == (True, [])


def test_aliased_import_is_still_refused_without_partial_file_write(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg/core.py").write_text("def helper(x): return x\n")
    text = "from pkg.core import (\n    helper as local,\n)\n"
    (tmp_path / "client.py").write_text(text)
    op = {"op": "rename_symbol", "module": "pkg/core.py", "name": "helper", "new_name": "compute"}
    with pytest.raises(ValueError, match="ALIASED_IMPORT_UNTRACKED"):
        orch._apply_rename(tmp_path, op, {"sites": [{"file": "client.py", "kind": "IMPORT_SITE"}]})
    assert (tmp_path / "client.py").read_text() == text


@pytest.mark.parametrize("line,col", [("helper_suffix", 0), ("helper", -1), ("éhelper", 1)])
def test_invalid_byte_offsets_and_identifier_boundaries_refuse(line, col):
    with pytest.raises(ValueError, match="TOKEN_"):
        orch._splice_token(line, "helper", "compute", col)
