"""One experience must make the NEXT program cheaper -- measured, not asserted.

§A111 recorded the honest baseline: the same fault repaired in three successive fresh worlds cost 1 probe every
time. **Nothing consulted anything, so the second occurrence was never cheaper.** The owner's hypothesis -- "do
it once and it learns it permanently" -- was therefore not merely unproven here; it was false of the loop as
built, and §A113 says so plainly rather than reporting the intent as the result.

These tests pin what is now true, and they pin the refusals that keep it honest:

  1. a program's faults can be found from its SOURCE, before it runs   (no model, no execution)
  2. the reader REFUSES where it cannot decide                        (a star import, prose)
  3. one failure is absorbed as a RULE, not as a transcript           (and one is refused)
  4. a rule learned from program A flags program B before B runs      (the generalisation)
  5. the reader does not accuse a program that imports its neighbour   (the cry-wolf case)
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

from canonical.runtime import read_before_running_v1 as RB
from canonical.runtime import stated_precondition_v1 as STATED


def _world(module: str, body: str = "raise RuntimeError('broken at import')\n") -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp(prefix="rbr_"))
    (root / (module + ".py")).write_text(body)
    (root / "app.py").write_text("import %s\nprint(1)\n" % module)
    return root


def _run(world: pathlib.Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "app.py"], cwd=world, capture_output=True, text=True)


def test_a_misspelling_is_found_from_the_source_with_zero_executions() -> None:
    """The expensive half of a repair is DISCOVERING the fault by running. This class needs no run."""
    source = "total=0\nfor n in [1,2,3]:\n    total=total+n\nprint(totl)\n"
    found = RB.predict(source)
    assert found["will_fail"] is True
    assert [f["name"] for f in found["faults"]] == ["totl"]
    assert found["faults"][0]["detected_by"] == "ast"


def test_a_correct_program_is_not_accused() -> None:
    """A predictor that cries wolf is worse than none: its 'repair' changes something that worked.

    The star-import case is the one that caught this module out -- `from os.path import *` makes every name
    unknowable, so a naive walk reported `join` as undefined in a program that runs perfectly.
    """
    assert RB.predict("total=0\nfor n in [1,2,3]:\n    total=total+n\nprint(total)\n")["will_fail"] is False

    star = RB.predict("from os.path import *\nprint(join('a','b'))\n")
    assert star["will_fail"] is False, "a name from a star import must never be called undefined"
    assert "STAR_IMPORT_MAKES_NAMES_UNKNOWABLE" in star["refusals"]


def test_an_imported_neighbour_is_unknowable_rather_than_missing() -> None:
    """THE CRY-WOLF CASE, measured. `alpha_mod.py` sits beside the program; `find_spec` knows nothing about it.

    Calling it missing would be false, and the act derived from `missing` -- install it -- would be wrong. It is
    reported in its own bucket because what it does on import cannot be read from the importing file at all.
    This is exactly where a learned rule earns its place.
    """
    world = _world("alpha_mod")
    found = RB.predict((world / "app.py").read_text(), world=world)
    assert found["faults"] == [], "a neighbouring module is not a missing module"
    assert found["unknowable_imports"] == ["alpha_mod"]


def test_one_failure_is_absorbed_as_a_rule_and_a_name_is_refused() -> None:
    """WHAT TO GENERALISE, answered by measurement rather than taste.

    `MODULE_NOT_FOUND` and `MODULE_NOT_IMPORTABLE` are rules about the world: they transfer to any program that
    imports that module. An undefined NAME is a fact about one file's symbol table -- the next file has a
    different one -- so it is refused, and the refusal says which code names a property it can read.
    """
    store = pathlib.Path(tempfile.mkdtemp()) / "rules.json"

    module_rule = RB.absorb("MODULE_NOT_FOUND:requests", at="program_A", store=store)
    assert module_rule["learned"] is True
    assert module_rule["predicate"]["test"] == "is_present"

    name_fact = RB.absorb("NAME_NOT_DEFINED:totl", at="program_A", store=store)
    assert name_fact["learned"] is False
    assert name_fact["why"] == "CODE_NAMES_NO_DECIDABLE_PROPERTY"

    assert sorted(STATED.conditions(store=store)) == ["module_not_found"]


def test_the_frames_of_a_traceback_are_read_when_the_message_states_no_location() -> None:
    """A TRACEBACK PUTS ITS LOCATION IN THE FRAMES, AND EVERY EARLIER READER TOOK ONLY THE LAST LINE.

    A module that exists but raises while being imported ends with pure prose (`RuntimeError: broken`), which
    both existing readers correctly refuse. The frames above it name the import and the file it died in, so the
    subject IS stated -- just not in the message. Extracting it is parsing, not guessing.
    """
    world = _world("alpha_mod")
    result = _run(world)
    assert result.returncode != 0

    assert STATED.parse(result.stderr) is not None
    stated = STATED.parse(result.stderr)
    assert stated is not None
    assert stated["code"] == "MODULE_NOT_IMPORTABLE"
    assert stated["value"] == "alpha_mod"
    assert stated["dialect"] == "cpython_frames"

    frames = STATED.frames_in(result.stderr)
    assert frames and frames[-1]["path"].endswith("alpha_mod.py")


def test_a_rule_from_program_a_flags_program_b_before_b_ever_runs() -> None:
    """THE MISSION'S HYPOTHESIS, measured end to end.

    Program A is run once and fails while importing its neighbour. Program B is a DIFFERENT program importing a
    DIFFERENT neighbour, and it is never executed at all. B's failure is flagged anyway, because the rule A
    taught is about importability in general and not about `alpha_mod`.
    """
    store = pathlib.Path(tempfile.mkdtemp()) / "rules.json"

    world_a = _world("alpha_mod")
    result = _run(world_a)
    assert result.returncode != 0
    assert RB.absorb(result.stderr, at="program_A", store=store)["learned"] is True

    world_b = _world("beta_mod")
    source_b = (world_b / "app.py").read_text()
    cold = RB.predict(source_b, world=world_b)
    assert cold["faults"] == [], "a static reader alone cannot see this fault"
    assert cold["unknowable_imports"] == ["beta_mod"]

    warm = RB.apply_memory(source_b, store=store, world=world_b)
    assert [m["code"] for m in warm["rules_matched"]] == ["MODULE_NOT_IMPORTABLE"]
    assert [m["fault"]["module"] for m in warm["rules_matched"]] == ["beta_mod"]
    assert warm["rules_matched"][0]["seen_at"] == ["program_A"]

    # B was never executed, and the flag was still raised -- that is the whole claim.
    # Proven by the fact that running B would have changed nothing about the answer: the rule was applied to a
    # program whose only observed history is its SOURCE. Nothing in this test runs app.py in world B.
    assert not (world_b / "__pycache__").exists()
