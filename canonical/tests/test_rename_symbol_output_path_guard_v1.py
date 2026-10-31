"""A rename report must not overwrite source or an externally linked file."""
import os

import pytest

from canonical.runtime.bound_capabilities import python_refactor_rename_symbol as rename


@pytest.mark.parametrize("case", ["defining_source", "other_source", "source_config", "outside_hardlink", "internal_symlink", "symlink_directory"])
def test_report_destination_cannot_damage_other_files(tmp_path, case):
    root = tmp_path / "repo"
    src = root / "src"
    (src / "pkg").mkdir(parents=True)
    (src / "pkg/__init__.py").write_text("")
    core = src / "pkg/core.py"
    core.write_text("def old_name(x):\n    return x + 1\n")
    caller = src / "caller.py"
    caller.write_text("from pkg.core import old_name\n\ndef call():\n    return old_name(3)\n")
    outside = tmp_path / "outside.json"
    outside.write_text("outside-original\n")
    internal = root / "preexisting.json"
    internal.write_text("internal-original\n")
    output = root / "reports/report.json"
    output.parent.mkdir()
    if case == "defining_source":
        output_rel = "src/pkg/core.py"
    elif case == "other_source":
        output_rel = "src/caller.py"
    elif case == "source_config":
        config = src / "config.json"
        config.write_text("source-configuration\n")
        output_rel = "src/config.json"
    elif case == "outside_hardlink":
        os.link(outside, output)
        output_rel = "reports/report.json"
    elif case == "internal_symlink":
        output.symlink_to(internal)
        output_rel = "reports/report.json"
    else:
        (root / "linked-directory").symlink_to(root / "reports", target_is_directory=True)
        (root / "reports" / "report.json").write_text("internal-report\n")
        output_rel = "linked-directory/report.json"
    originals = {p: p.read_bytes() for p in (core, caller, outside, internal)}
    if case == "source_config":
        originals[config] = config.read_bytes()
    if case == "symlink_directory":
        originals[output] = output.read_bytes()
    try:
        rename.run({"source_root": "src", "module": "pkg/core.py", "qualname": "old_name",
                    "new_symbol": "new_name", "output_path": output_rel}, root)
    except SystemExit as exc:
        assert "REFUSE_UNSAFE_OUTPUT" in str(exc.code)
    for path, before in originals.items():
        assert path.read_bytes() == before


def test_existing_regular_report_outside_source_is_still_usable(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "core.py").write_text("def old_name(x):\n    return x + 1\n")
    report = tmp_path / "out/report.json"
    report.parent.mkdir()
    report.write_text("previous report\n")
    result = rename.run({"source_root": "src", "module": "core.py", "qualname": "old_name",
                         "new_symbol": "new_name", "output_path": "out/report.json"}, tmp_path)
    assert result["verified"] is False
    assert '"new_symbol": "new_name"' in report.read_text()
    assert "def new_name(" in (src / "core.py").read_text()
