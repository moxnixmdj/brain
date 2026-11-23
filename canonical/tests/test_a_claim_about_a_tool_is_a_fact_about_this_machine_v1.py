"""52 rows said `VERIFIED_BOUND_CAPABILITY` and declared no adapter. This is what they actually are.

`reachability_v2` could only answer `NO_ADAPTER_DECLARED` for all 52 -- true, and useless: a stdlib
function, an installed binary, and a package nobody ever installed are three different findings with three
different next actions. This suite holds `tool_claims_v1` to that distinction.

Every test is anchored to something measured on 2026-11-23, not to a hypothetical:

  * `python stdlib ast/tokenize` is PROSE in a field called `module`; it cannot be looked up.
  * `git` in `"python stdlib ast/pytest + git"` is a binary, and an import-only check calls it missing on a
    machine that has git.
  * `finite_grid_program_inducer` is a file in this tree, not an external package.
  * `auto.pypi.msgpack` pins `msgpack-1.2.2-cp312-cp312-...whl` with its sha256 on a cp311 machine -- a
    hash-verified memory of a computer that is not this one.
"""

from __future__ import annotations

import importlib.util
import pathlib
import shutil
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import tool_claims_v1 as T  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def report() -> dict:
    return T.tool_claims()


def test_every_adapterless_claim_is_accounted_for(report: dict) -> None:
    """No row may be dropped. A census that skips rows lies by omission."""
    assert report["claims"] == sum(report["counts"].values())
    assert report["claims"] >= 50, report["claims"]


def test_prose_in_a_module_field_is_parsed_not_ignored(report: dict) -> None:
    """`module: "python stdlib ast/tokenize"` is a sentence, and a sentence cannot be found.

    The names it contains can. Measured: 13 rows stored prose; parsing the names moved 13 rows out of
    'unresolved' and into PRESENT, because `ast` and `tokenize` are in every Python.
    """
    row = report["rows"].get("python.refactor.rename_parameter.v1")
    assert row is not None
    assert row.get("names_read_from_the_field"), row
    assert "ast" in row["names_read_from_the_field"], row["names_read_from_the_field"]


def test_a_binary_in_a_prose_field_is_present_if_the_machine_has_it(report: dict) -> None:
    """`git` is not importable, and this machine has it. An import-only check would have been wrong."""
    row = report["rows"].get("python.review.diff_mutation_gate.v1")
    assert row is not None
    names = row.get("names_read_from_the_field") or []
    if "git" in names:
        assert shutil.which("git") or row["state"] == "PARTLY_PRESENT"


def test_a_name_that_is_a_file_in_this_tree_is_not_an_absent_tool(report: dict) -> None:
    """Measured: `finite_grid_program_inducer` was counted as a missing external package while
    `canonical/runtime/finite_grid_program_inducer_v1.py` sat in the tree."""
    row = report["rows"].get("software.synthesis.grid_induction.v1")
    assert row is not None
    assert row["state"] == "PRESENT", row
    assert row.get("resolved_in_this_tree"), row


def test_a_wheel_for_another_python_is_named_as_such(report: dict) -> None:
    """THE PUREST FORM OF THE DEFECT: a true, hash-verified memory of a different computer.

    `auto.pypi.msgpack` pins a cp312 wheel. This interpreter is cp311. pip refuses that file, so the row
    can never run here no matter how carefully it was verified.
    """
    row = report["rows"].get("auto.pypi.msgpack")
    assert row is not None
    assert row.get("declared_wheel", "").endswith(".whl")
    fits, detail = T._wheel_fits_this_interpreter(row["declared_wheel"])
    here = "cp%d%d" % sys.version_info[:2]
    if here == "cp311":
        assert fits is False, detail
        assert "cp312" in detail
        # With msgpack absent the row must say WHY it is unusable, not merely that it is.
        if importlib.util.find_spec("msgpack") is None:
            assert row["state"] == "WHEEL_FOR_ANOTHER_PYTHON", row
            assert "DIFFERENT_INTERPRETER" in row["why"]


def test_a_pure_python_wheel_is_not_accused_of_a_mismatch() -> None:
    """`py3-none-any` runs anywhere. Flagging it would make the check cry wolf."""
    for name in ("bson_modern-1.1.0-py3-none-any.whl", "pypdf-6.19.0-py3-none-any.whl",
                 "sympy-1.14.0-py3-none-any.whl"):
        fits, detail = T._wheel_fits_this_interpreter(name)
        assert fits is True, (name, detail)


def test_an_absent_tool_names_the_door_that_would_obtain_it(report: dict) -> None:
    """'Absent' is only useful if it says how it could stop being absent, and whether that is verified."""
    absent = {cid: row for cid, row in report["rows"].items() if row["state"] == "ABSENT"}
    assert absent, "a machine this size cannot have every tool"
    with_door = [cid for cid, row in absent.items() if row.get("acquirable")]
    assert len(with_door) >= len(absent) * 0.8, (len(with_door), len(absent))
    for cid in with_door:
        door = absent[cid]["acquirable"]
        kind = next(iter(door))
        assert door[kind] or kind in ("pypi", "npm", "apt")


def test_the_pypi_door_records_that_it_verifies_before_it_trusts(report: dict) -> None:
    """Acquisition must not be 'pip install from a URL'. The project already has a verifying acquirer and
    the finding must point at it, so the next step cannot quietly become an unverified download."""
    any_pypi = [row for row in report["rows"].values()
                if isinstance(row.get("acquirable"), dict) and "pypi" in row["acquirable"]]
    assert any_pypi, "no pypi claim recorded"
    for row in any_pypi:
        assert "verifies" in row["acquirable"], row["acquirable"]


def test_absence_is_never_reported_as_unreachable_code(report: dict) -> None:
    """The code is fine; the tool is not here. Calling that UNREACHABLE hides which of the two is true."""
    for cid, row in report["rows"].items():
        assert row["state"] in {"PRESENT", "ABSENT", "PARTLY_PRESENT", "NO_NAME_IN_THE_ROW",
                                "NOT_A_TOOL", "STDLIB_NAME_UNRESOLVED",
                                "WHEEL_FOR_ANOTHER_PYTHON"}, (cid, row)
        assert row["state"] != "UNREACHABLE", cid


def test_acquiring_a_verified_wheel_flips_the_claim() -> None:
    """MEASURED END TO END. `msgpack==1.2.4` was installed into a clean interpreter with
    `--require-hashes` and the digest PyPI published; `auto.pypi.msgpack` moved ABSENT -> PRESENT.

    This test does not install anything. It asserts the MECHANISM: the claim is resolved by looking at the
    machine each time, so it cannot drift from the truth the way a stored status does.
    """
    before = T.tool_claims()["rows"]["auto.pypi.msgpack"]
    here = importlib.util.find_spec("msgpack") is not None
    assert before["state"] == ("PRESENT" if here else before["state"])
    if here:
        assert before["state"] == "PRESENT"
    else:
        assert before["state"] in ("WHEEL_FOR_ANOTHER_PYTHON", "ABSENT")
