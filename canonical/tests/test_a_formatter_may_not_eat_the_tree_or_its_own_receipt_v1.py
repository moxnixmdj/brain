#!/usr/bin/env python3
"""A formatter rewrites what it is pointed at, so two things must never happen.

Measured on 2026-10-28, on this repository, through its own live door:

    goal: "Format the python file canonical/runtime/toolchain_gate_v1.py in place."

    the compiler bound   source_root = canonical/runtime   (the file's DIRECTORY)
    the adapter ran      ruff format canonical/runtime
    ruff rewrote         2238 files, 229,816 insertions
    then died            "Failed to parse livebench_legacy_predecessor_compiler_audit_v1.py"
    the adapter wrote    its own refusal JSON to output_path
    output_path was      canonical/runtime/toolchain_gate_v1.py  -- the source file

Two defects, one request: a request about ONE FILE reformatted half the repository (and stopped
where it liked, leaving the tree half-applied), and the receipt of that failure was written over
a source file, replacing a 256-line module with nine lines of JSON.

Neither is a formatting problem. They are the two laws this file pins:

  1. **A mutation is all-or-nothing.** A write pass never starts on a target that cannot be
     finished: a dry run decides first, and a dry run that cannot parse every file refuses --
     having written nothing.
  2. **A receipt never lands on the artifact.** For a verb whose target IS its output ("format
     this file in place"), the artifact is the file and the receipt travels as the return value.
     Written over the artifact, a receipt is destruction; refused before the write, it is still
     destruction if the refusal itself is written to the same path -- which is what happened.

The guards live in `bound_capabilities/toolchain_v1.py::run` and `::_format`, so every analyser
verb that mutates a target inherits them.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _ruff_is_here() -> bool:
    """The same resolution the adapter uses: beside this interpreter, or on PATH."""
    return ((pathlib.Path(sys.executable).parent / "ruff").is_file()
            or shutil.which("ruff") is not None)


pytestmark = pytest.mark.skipif(not _ruff_is_here(), reason="ruff is not installed here")

toolchain = pytest.importorskip("canonical.runtime.bound_capabilities.toolchain_v1")

UNFORMATTED = "def f(  a,b ):\n    return  a+b\n"
FORMATTED = "def f(a, b):\n    return a + b\n"
UNPARSABLE = "x = 1 \\\n  +\n"


def _run(tmp_path, verb, target, destination, **extra):
    args = {"tool_verb": verb, "capability_id": "test.v1",
            "output_path": str(destination), "source_root": str(target)}
    args.update(extra)
    return toolchain.run(args, tmp_path)


# ------------------------------------------------------------------ law 1: all-or-nothing


def test_a_directory_with_one_unparsable_file_is_refused_before_a_single_byte_is_written(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "good.py").write_text(UNFORMATTED, encoding="utf-8")
    (pkg / "bad.py").write_text(UNPARSABLE, encoding="utf-8")
    before = {path: path.read_bytes() for path in pkg.iterdir()}

    with pytest.raises(toolchain.ToolchainError) as caught:
        _run(tmp_path, "format", pkg, tmp_path / "receipt.json")

    assert "FORMAT_WOULD_LEAVE_A_HALF_FORMATTED_TREE" in str(caught.value)
    assert {path: path.read_bytes() for path in pkg.iterdir()} == before, (
        "the dry run must decide before the write pass starts"
    )


def test_a_clean_directory_is_still_formatted(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "messy.py").write_text(UNFORMATTED, encoding="utf-8")

    payload = _run(tmp_path, "format", pkg, tmp_path / "receipt.json")

    assert (pkg / "messy.py").read_text(encoding="utf-8") == FORMATTED
    assert payload["changed_count"] == 1
    assert (tmp_path / "receipt.json").is_file()


# ------------------------------------------------------------------ law 2: the receipt never lands on the artifact


def test_formatting_a_named_file_in_place_keeps_the_file_and_returns_the_receipt(tmp_path):
    """`output_path` bound to the file IS the "in place" the sentence asked for."""
    source = tmp_path / "module.py"
    source.write_text(UNFORMATTED, encoding="utf-8")

    payload = _run(tmp_path, "format", source, source)

    assert source.read_text(encoding="utf-8") == FORMATTED, "the artifact is the code, not a receipt"
    assert payload["receipt_written"] is False
    assert payload["artifact_path"] == str(source)
    assert payload["artifact_sha256"] and json.loads(json.dumps(payload))


def test_the_receipt_is_not_written_inside_a_tree_being_rewritten(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "messy.py").write_text(UNFORMATTED, encoding="utf-8")
    inside = pkg / "report.json"

    payload = _run(tmp_path, "format", pkg, inside)

    assert not inside.exists(), "a report inside the rewritten tree pollutes it and can replace a source"
    assert (pkg / "messy.py").read_text(encoding="utf-8") == FORMATTED
    assert payload["receipt_written"] is False


def test_a_failed_in_place_edit_writes_nothing_over_the_artifact(tmp_path):
    """The refusal used to be written to the very destination it objected to."""
    source = tmp_path / "broken.py"
    source.write_text(UNPARSABLE, encoding="utf-8")
    before = source.read_bytes()

    with pytest.raises(toolchain.ToolchainError):
        _run(tmp_path, "format", source, source)

    assert source.read_bytes() == before


def test_a_read_only_verb_still_writes_its_receipt_where_the_sentence_put_it(tmp_path):
    """The law is about MUTATING verbs; a lint report inside the scanned tree is legitimate."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "clean.py").write_text("def f(a, b):\n    return a + b\n", encoding="utf-8")
    destination = pkg / "lint.json"

    _run(tmp_path, "format", pkg, destination, check_only=True)

    assert destination.is_file(), "check_only writes nothing but its report, so the report is written"
    assert json.loads(destination.read_text(encoding="utf-8"))["check_only"] is True


# ------------------------------------------------------------------ the door that was measured


def test_the_door_formats_the_named_file_and_leaves_every_other_file_alone(tmp_path):
    """End to end through the live door, on a scratch repository: the measured regression."""
    from canonical.runtime import live_brain_route_admission_v1 as admission

    target = ROOT / "canonical/astra_runtime/tmp/format_scene"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    try:
        (target / "named.py").write_text(UNFORMATTED, encoding="utf-8")
        (target / "bystander.py").write_text(UNFORMATTED, encoding="utf-8")
        goal = "Format the python file %s in place." % (target / "named.py").relative_to(ROOT)
        result = admission.solve({"task_id": "T", "goal": goal})
        assert result["status"].startswith("PASS"), result.get("reason")
        assert (target / "named.py").read_text(encoding="utf-8") == FORMATTED
        assert (target / "bystander.py").read_text(encoding="utf-8") == UNFORMATTED, (
            "a request about one file must not format its neighbours"
        )
    finally:
        shutil.rmtree(target, ignore_errors=True)
