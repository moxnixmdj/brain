"""The world is built by reading the capability's own refusal. These tests hold that to account.

The load-bearing law is the last one: **no operator may know a capability's name.** A repair that
recognises one adapter is a person's work in a machine's clothes, and it would not transfer to the
next sixty capabilities -- which is the whole reason this exists.

Measured background (2026-11-04): the first version repaired nothing at all. Its shape parser
rejected `{"trades": [non-empty]}` because that is not JSON, and it resolved every path against the
repository, so a path inside the temporary world was reported as unreachable. Five capabilities
became drivable once both were fixed; twelve stayed unreachable for a reason no world can fix.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.tools import world_forge_v1 as forge  # noqa: E402


def _recipe(files=None):
    return {"values": {"input_path": "input.json", "output_path": "out.bin"},
            "files": files if files is not None else {"input.json": "x\n"},
            "dirs": [], "db": [], "rounds": []}


def _failure(detail: str) -> dict:
    return {"verdict": "CRASHED", "detail": detail}


# --------------------------------------------------------------------------- the repairs
def test_a_shape_it_names_becomes_a_world_it_can_run():
    """`need {"trades": [non-empty]}` is a specification written in a refusal. It is also not
    JSON, which is exactly why the first version could not read it."""
    spec = forge._json_spec_from('SACCR_INPUT_SHAPE_REJECTED:need {"trades": [non-empty]}')
    assert spec == {"trades": ["x"]}, spec

    recipe, op = forge.operators("anything", "anything", _recipe(),
                                 _failure('RuntimeError: SHAPE_REJECTED:need {"trades": [non-empty]}'))
    assert op == "BUILD_THE_SHAPE_IT_NAMED", op
    import json
    assert json.loads(recipe["files"]["input.json"]) == {"trades": ["x"]}


def test_a_relative_path_is_resolved_against_the_world_it_was_given():
    """A world is a directory. A path inside that directory is not 'outside', and saying so
    refused the one repair that could have worked."""
    import tempfile
    root = Path(tempfile.mkdtemp(prefix="world_"))
    wanted = root / "canonical" / "runtime" / "thing.py"
    recipe, op = forge.operators(
        "x", "y", _recipe(), _failure(f"FileNotFoundError: [Errno 2] No such file or directory: "
                                      f"'{wanted}'"), root)
    assert op in ("CREATE_FILE", "CREATE_DIRECTORY"), op
    assert op != "UNREPAIRABLE_ADAPTER_ESCAPES_ROOT"


def test_a_path_no_world_contains_is_reported_not_patched():
    """An adapter that looks outside the root it was handed is a finding. Writing the file it
    wants, wherever it wants it, would be the fixture covering for a capability."""
    recipe, op = forge.operators(
        "x", "y", _recipe(),
        _failure("FileNotFoundError: [Errno 2] No such file or directory: '/etc/passwd'"))
    assert op == "UNREPAIRABLE_ADAPTER_ESCAPES_ROOT", op
    assert recipe["files"] == {"input.json": "x\n"}, "it wrote outside the world anyway"


def test_a_missing_package_is_never_pretended_away():
    """Twelve capabilities need a library this machine does not have. Installing one is spending,
    which is forbidden in a credited path, so the honest answer is 'unreachable' -- not a world
    that looks like it worked."""
    recipe, op = forge.operators("x", "y", _recipe(),
                                 _failure("ModuleNotFoundError: No module named 'PIL'"))
    assert op == "UNREPAIRABLE_MISSING_PACKAGE"
    assert op.startswith("UNREPAIRABLE")
    assert recipe["files"] == {"input.json": "x\n"}


def test_text_read_as_json_turns_the_world_into_json():
    recipe, op = forge.operators(
        "x", "y", _recipe({"a.txt": "x\n", "b.json": "x\n"}),
        _failure("JSONDecodeError: Expecting value: line 1 column 1 (char 0)"))
    assert op == "MAKE_THE_WORLD_JSON", op
    assert set(recipe["files"].values()) == {"{}"}, recipe["files"]


def test_a_python_path_gets_a_python_file():
    recipe, op = forge.operators("x", "y", _recipe({"t.txt": "x\n"}),
                                 _failure("RepairLoopError: PATH_INVALID:t"))
    assert op == "WRITE_A_PARSEABLE_PYTHON_FILE", op
    compile(recipe["files"]["t.txt"], "<t>", "exec")


def test_a_database_path_gets_a_database():
    recipe, op = forge.operators("x", "y", _recipe({}),
                                 _failure("DatabaseError: file is not a database"))
    assert op == "CREATE_DATABASE", op
    assert recipe["db"], "it said it created a database and created nothing"


# --------------------------------------------------------------------------- the law
def test_no_operator_knows_a_capability_name():
    """If a repair recognises an adapter, it is a lookup table wearing a mechanism's clothes and
    it will not transfer. Checked against the real registry, not against a sample."""
    import json
    import inspect
    registry = json.loads((ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
                          .read_text(encoding="utf-8"))["capabilities"]
    source = inspect.getsource(forge.operators) + inspect.getsource(forge._json_spec_from)
    source += inspect.getsource(forge._fill)
    offenders = [cid for cid in registry if cid in source]
    offenders += sorted({entry.get("adapter_module") for entry in registry.values()
                         if entry.get("adapter_module") and entry["adapter_module"] in source})
    assert not offenders, f"a repair names a specific capability or adapter: {offenders[:5]}"
