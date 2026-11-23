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
    # AND THE ANSWER IS A FACT, NOT A REPEATED ACCUSATION: beta_mod.py raises on import, so a one-line probe
    # of the module alone establishes that without running the program that imports it.
    assert warm["rules_matched"][0]["fault"]["class"] == "module_fails_to_import"
    assert warm["rules_matched"][0]["observed"]["importable"] is False

    # B WAS NEVER RUN, and the flag was still raised -- that is the whole claim. The proof must be about
    # `app.py`, not about the directory: the PROBE imports `beta_mod` alone (which legitimately writes a
    # __pycache__ for that module), so a directory-level assertion would fail for a reason that has nothing to
    # do with the claim. What must not exist is any trace of the program itself having been executed.
    cached = [p.name for p in (world_b / "__pycache__").glob("*.pyc")]
    assert not any(name.startswith("app.") for name in cached), \
        "the program must not have been executed: %s" % cached
    assert any(name.startswith("beta_mod.") for name in cached), \
        "the PROBE did run, which is how the fact was established: %s" % cached


def test_the_prediction_asks_the_interpreter_that_will_run_the_program() -> None:
    """ASKING THE WRONG INTERPRETER IS A CONFIDENT ANSWER ABOUT THE WRONG THING.

    Measured 2026-11-23: a prediction made in the harness's own process reported a module present while the
    program was going to run under an interpreter where it was absent -- the same class of error as §A110's
    guard watching the wrong tree. A virtualenv created here is the cleanest available witness: it exists, it is
    real, and the module is provably absent from it.
    """
    import venv

    store = pathlib.Path(tempfile.mkdtemp()) / "venv"
    venv.EnvBuilder(with_pip=False, clear=True).create(store)
    other = str(store / "bin" / "python")
    assert pathlib.Path(other).exists(), other

    source = "import cowsay\nprint(1)\n"
    asked_here = RB.predict(source)
    asked_other = RB.predict(source, interpreter=other)

    # `cowsay` may or may not be installed here, but it is certainly NOT in a fresh venv without pip
    assert asked_other["faults"], "a fresh venv cannot have cowsay"
    assert asked_other["faults"][0]["module"] == "cowsay"
    # the two questions are genuinely different questions: if this process also lacks cowsay the test still
    # holds (both report it), so the assertion that matters is that the OTHER interpreter's answer is used and
    # is not silently replaced by this one's.
    assert asked_other["imports_predictable"] is True
    assert asked_here["schema"] == asked_other["schema"]


def test_a_repair_that_worked_on_the_last_attempt_is_not_reported_as_a_failure() -> None:
    """§A113's most consequential defect: a VERIFIED-GOOD REPAIR REPORTED AS A FAILURE.

    `repair_v1.attempt(max_attempts=1)` installed the module correctly -- `setup_ok=True`, and the module was
    importable afterwards -- and still returned `ok: False` with the reason "python module cowsay is not
    installed". The loop's final iteration applied the setup and then `continue`d into an exhausted range, so
    the success was never observed and the stale diagnosis was returned instead.

    The damage is not cosmetic: every caller reads `ok`, so a caller re-attempts a fault that is gone, and a
    report can say a repairable world was unrepairable. The module's own docstring already states the rule
    that was broken -- "success is whatever actually exited zero -- never an assumption that the repair
    helped" -- so the fix runs the program once more and looks, rather than assuming.
    """
    import venv

    from canonical.runtime import repair_v1 as R

    base = pathlib.Path(tempfile.mkdtemp())
    # WITH PIP, and that is the whole point. The first version of this test built the venv WITHOUT pip, so the
    # install could never succeed, the test always took the "nothing was repaired" branch, and it PASSED with
    # the fix reverted. A test that cannot fail is not a test -- it was caught by deliberately reverting the
    # fix and watching it stay green.
    venv.EnvBuilder(with_pip=True, clear=True).create(base / "venv")
    python = str(base / "venv" / "bin" / "python")
    assert pathlib.Path(python).exists()
    if subprocess.run([python, "-m", "pip", "--version"], capture_output=True).returncode != 0:
        import pytest
        pytest.skip("this venv has no pip, so no repair can be attempted honestly")

    world = base / "world"
    world.mkdir()
    (world / "app.py").write_text("import cowsay\nprint(1)\n")

    result = R.attempt("%s app.py" % python, str(world), timeout=300, max_attempts=1)
    importable = subprocess.run([python, "-c", "import cowsay"], capture_output=True).returncode == 0

    if not importable:
        # pip could not reach an index in this sandbox: nothing was repaired, and `ok=False` is then correct.
        assert result["ok"] is False, result
        return
    # the repair demonstrably worked, so the report must say so
    assert result["ok"] is True, result
    assert result["attempts"][-1]["class"] == "after_setup"


def test_the_rule_says_ask_and_the_probe_answers_so_a_healthy_module_is_left_alone() -> None:
    """THE CRY-WOLF TEST. A rule learned from ONE broken module must not accuse the next, healthy one.

    Measured 2026-11-23, and this is what made the design right: the first version matched `MODULE_NOT_IMPORTABLE`
    against every local import and reported a perfectly good `beta.py` as a fault. The rule's knowledge is that
    IMPORTABILITY IS WORTH ASKING ABOUT -- not that any particular module is broken. The question is decidable
    in one cheap probe that imports the module and nothing else, so the rule triggers the question and the
    probe supplies the fact.
    """
    store = pathlib.Path(tempfile.mkdtemp()) / "rules.json"

    broken = pathlib.Path(tempfile.mkdtemp(prefix="teach_"))
    (broken / "alpha.py").write_text("raise RuntimeError('broken')\n")
    (broken / "app.py").write_text("import alpha\n")
    result = _run(broken)
    assert RB.absorb(result.stderr, at="program_A", store=store)["learned"] is True

    healthy = pathlib.Path(tempfile.mkdtemp(prefix="healthy_"))
    (healthy / "beta.py").write_text("VALUE = 42\n")
    (healthy / "app.py").write_text("import beta\nprint(beta.VALUE)\n")
    warm_healthy = RB.apply_memory((healthy / "app.py").read_text(), store=store, world=healthy)
    assert warm_healthy["rules_matched"] == [], "a healthy module must never be reported as a fault"

    raising = pathlib.Path(tempfile.mkdtemp(prefix="raising_"))
    (raising / "gamma.py").write_text("raise RuntimeError('boom')\n")
    (raising / "app.py").write_text("import gamma\n")
    warm_raising = RB.apply_memory((raising / "app.py").read_text(), store=store, world=raising)
    assert [m["fault"]["class"] for m in warm_raising["rules_matched"]] == ["module_fails_to_import"]
    assert warm_raising["rules_matched"][0]["observed"]["importable"] is False


def test_knowledge_persists_across_processes_and_is_removable_without_retraining() -> None:
    """§2's TEST, LITERALLY. Knowledge lives outside the weights, is addable and removable, and no parameter
    changes -- because there are no parameters. What accumulates is a JSON file a person can read and edit.

    Three separate claims, each checked in its own process where it matters:
      persistence  a fact learned by one process is seen by the NEXT one
      effect       the fact changes behaviour, or it is not knowledge
      removal      deleting it restores the cold behaviour, with no retraining
    """
    store = pathlib.Path(tempfile.mkdtemp()) / "knowledge.json"
    world = pathlib.Path(tempfile.mkdtemp(prefix="persist_"))
    (world / "gamma.py").write_text("raise RuntimeError('broken')\n")
    (world / "app.py").write_text("import gamma\nprint(1)\n")
    source = (world / "app.py").read_text()

    def matched() -> list[str]:
        return [m["fault"]["class"] for m in RB.apply_memory(source, store=store, world=world)["rules_matched"]]

    assert matched() == [], "cold: nothing known"

    # PERSISTENCE: learn in a SEPARATE process, then read it back in another one
    taught = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, %r)\n"
         "from canonical.runtime import read_before_running_v1 as RB\n"
         "print(RB.absorb('MODULE_NOT_IMPORTABLE:alpha', at='program_A', store=%r)['learned'])"
         % (str(pathlib.Path(RB.__file__).resolve().parents[2]), str(store))],
        capture_output=True, text=True)
    assert taught.stdout.strip() == "True", taught.stderr[-400:]

    read_back = subprocess.run(
        [sys.executable, "-c",
         "import sys; sys.path.insert(0, %r)\n"
         "from canonical.runtime import stated_precondition_v1 as S\n"
         "print(sorted(S.conditions(store=%r)))"
         % (str(pathlib.Path(RB.__file__).resolve().parents[2]), str(store))],
        capture_output=True, text=True)
    assert "module_not_importable" in read_back.stdout, read_back.stderr[-400:]

    # EFFECT
    assert matched() == ["module_fails_to_import"]

    # REMOVAL, with no retraining
    STATED.forget("module_not_importable", store=store)
    assert matched() == []
