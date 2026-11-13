"""A skill's applicability is bought with executed observations, and every refusal here is two-sided.

These tests exist to make the scope acquisition falsifiable in the directions that matter. The
load-bearing ones are the traps this module was built out of, each of which was hit for real while
prototyping and each of which fails silently rather than loudly if it regresses:

  * A victim the skill never fires on is NOT a failure. Counting a non-firing as a failure builds a
    boundary out of the tokenizer's reach instead of the skill's domain.
  * A substring is not an observation. `"return " in source` is true of a function whose return is
    nowhere near the operator, and that crude fact was measured to produce a plausible, WRONG,
    narrower scope -- `{baseline.violates_own_spec, site.return}` instead of the identified
    `{baseline.violates_own_spec}`.
  * A label reachable from successes alone is a constant, not a measurement.
  * An unexecuted baseline is not a fact.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import applicability_v1 as app  # noqa: E402
from canonical.runtime import contrast_selection_v1 as cs  # noqa: E402
from canonical.swe_kernel import skill_scope_acquisition_v1 as acq  # noqa: E402
from canonical.tools.skill_scope_acquisition_probe_v1 import VICTIMS, demonstration  # noqa: E402


@pytest.fixture(scope="module")
def doc():
    return demonstration()


@pytest.fixture(scope="module")
def taught_rule():
    """One crystallized boundary lesson, taught through the production store."""
    import tempfile
    from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry
    from canonical.tools.skill_scope_acquisition_probe_v1 import (
        TAUGHT_AFTER, TAUGHT_BEFORE, _twin_oracle)
    with tempfile.TemporaryDirectory() as td:
        store = cry.VerifiedSkillStore(db_path=pathlib.Path(td) / "s.sqlite", seed=False)
        taught = store.crystallize_code_fix(before_snippet=TAUGHT_BEFORE,
                                            after_snippet=TAUGHT_AFTER, language="python",
                                            error_class="BOUNDARY", twin_oracle=_twin_oracle)
        assert taught.get("crystallized"), taught.get("reason")
        rules = store.lookup_rules("python", "BOUNDARY")
        assert len(rules) == 1
        yield rules[0]


# --------------------------------------------------------------------------- the capability, both sides
def test_without_a_scope_the_same_skill_breaks_correct_code(doc):
    """The defect, measured: proposing wherever the tokens match ruins already-correct targets."""
    assert doc["fired_on"] == 8
    assert doc["repaired"] == 5
    assert doc["broke_correct_code_before_scope"] == 3


def test_the_bought_scope_refuses_every_breakage_and_keeps_every_repair(doc):
    """Both numbers must move, in opposite directions, or the scope is decoration."""
    assert doc["status"].startswith("IDENTIFIED"), doc["status"]
    assert doc["required"] == ["baseline.violates_own_spec"]
    assert doc["repairs_after_scope"] == doc["repaired"] == 5
    assert doc["broke_correct_code_after_scope"] == 0
    assert doc["refusals"] == doc["broke_correct_code_before_scope"] == 3
    # and each refusal says what it prevented, rather than only that it declined
    assert all(r["would_have_been"] == acq.BROKE_CORRECT for r in doc["refusals_named"])
    assert all(r["missing"] == ["baseline.violates_own_spec"] for r in doc["refusals_named"])


def test_the_boundary_is_bought_one_observation_at_a_time(doc):
    """A dose-response, not a verdict: three successes buy nothing, the first failure changes that."""
    ladder = doc["ladder"]
    assert [s["observations"] for s in ladder] == [1, 2, 3, 4, 5]
    for step in ladder[:3]:
        assert step["status"] == "UNDETERMINED__NO_CONTRASTING_OUTCOME", step
        assert step["required"] is None
    assert ladder[3]["status"] == "AMBIGUOUS__SEVERAL_CONSISTENT_REQUIREMENTS"
    assert ladder[3]["verdict"] == acq.BROKE_CORRECT
    assert ladder[4]["status"] == "IDENTIFIED__ONE_CONSISTENT_REQUIREMENT"
    assert ladder[4]["required"] == ("baseline.violates_own_spec",)
    assert doc["observations_to_identify"] == 5


def test_the_label_is_earned_and_not_a_constant(doc):
    """Remove the failures and the same code must refuse to name any requirement."""
    ctl = doc["earnability_control"]
    assert ctl["successes_only_status"] == "UNDETERMINED__NO_CONTRASTING_OUTCOME"
    assert ctl["successes_only_reason"] == "NO_FAILURE__NECESSITY_IS_ONLY_REFUTED_BY_FAILURE"
    assert ctl["successes_only_required"] is None


# --------------------------------------------------------------------------- the semantics trap
def test_a_victim_the_skill_never_fires_on_is_not_a_failure():
    """No firing, no observation. This is the trap that would manufacture a boundary."""
    rule = {"language": "python",
            "pattern_tokens": [["kw", "return"], ["ws", " "], ["hole_id", "?id0"], ["ws", " "],
                               ["op", "<="], ["ws", " "], ["hole_id", "?id1"]],
            "replacement_tokens": [["kw", "return"], ["ws", " "], ["hole_id", "?id0"], ["ws", " "],
                                   ["op", "<"], ["ws", " "], ["hole_id", "?id1"]]}
    obs = acq.observe(rule, "def f(x, hi):\n    return x + hi\n", "assert f(1, 2) == 3\n")
    assert obs["fired"] is False
    assert obs["verdict"] == acq.NOT_APPLICABLE
    assert obs["row"] is None, "a non-firing must not become an evidence row"
    assert obs["verdict"] not in acq.IS_EVIDENCE


def test_only_a_firing_can_be_evidence_and_only_a_repair_can_be_success():
    assert acq.NOT_APPLICABLE not in acq.IS_EVIDENCE
    assert acq.IS_SUCCESS == frozenset({acq.REPAIRED})
    assert acq.BROKE_CORRECT in acq.IS_EVIDENCE and acq.BROKE_CORRECT not in acq.IS_SUCCESS


# --------------------------------------------------------------------------- a substring is not a fact
def test_a_substring_is_not_an_observation():
    """The crude extractor's exact failure, pinned.

    This source contains the word `return`, but the comparison sits in an assignment. A substring
    test would report `site.return` and the law would then identify the narrower, wrong requirement
    `{baseline.violates_own_spec, site.return}`.
    """
    src = "def f(x, hi):\n    ok = x <= hi\n    return not ok\n"
    facts = acq.observable_facts(src, baseline_ok=False)
    assert "site.assignment" in facts
    assert "site.return" not in facts, "the return is nowhere near the operator"
    assert "operator.LtE" in facts


def test_the_site_facts_follow_the_node_not_the_keyword():
    cases = {
        "def f(x, hi):\n    return x <= hi\n": {"site.return"},
        "def f(x, hi):\n    if x <= hi:\n        return 1\n    return 0\n": {"site.if_guard"},
        "def f(x, hi):\n    i = 0\n    while i <= hi:\n        i += 1\n    return i\n": {"site.while_guard"},
        "def f(x, hi):\n    return not (x > hi)\n": {"form.negated"},
        "def f(x, hi):\n    return (x >= 0) and (x <= hi)\n": {"form.compound_boolean"},
        "def f(x, hi):\n    return hi >= x\n": {"order_flipped_marker"},
        # an `if` that merely CONTAINS the return is not a guard on the comparison
        "def f(x, hi):\n    if hi:\n        return x <= hi\n    return False\n": {"site.return"},
        # a `while` that merely CONTAINS the comparison is not a loop guard on it. The test is
        # `True` rather than a comparison, so nothing else in the source can earn `site.while_guard`.
        "def f(x, hi):\n    while True:\n        ok = x <= hi\n        break\n    return ok\n":
            {"site.assignment"},
    }
    for src, expected in cases.items():
        facts = acq.observable_facts(src, baseline_ok=True)
        for e in expected:
            if e == "order_flipped_marker":
                assert "left_operand.name.hi" in facts, src
            else:
                assert e in facts, (src, sorted(facts))
    contained = acq.observable_facts(
        "def f(x, hi):\n    if hi:\n        return x <= hi\n    return False\n", baseline_ok=True)
    assert "site.if_guard" not in contained, "the comparison is not the if's test"
    in_body = acq.observable_facts(
        "def f(x, hi):\n    while True:\n        ok = x <= hi\n        break\n    return ok\n",
        baseline_ok=True)
    assert "site.while_guard" not in in_body, "the comparison is not the while's test"
    assert "site.assignment" in in_body


# A victim whose source holds no comparison at all, so the taught token pattern cannot match it.
NEVER_FIRES = {"label": "no_operator_anywhere", "source": "def f(x, hi):\n    return x + hi\n",
               "spec": "assert f(1, 2) == 3\n"}


def test_a_non_firing_costs_an_observation_and_yields_no_evidence(taught_rule):
    """`not_applicable` is a load-bearing count, not decoration.

    If a victim the skill never fires on were silently dropped from the trace, the report would claim
    the boundary was bought with fewer observations than were actually spent -- the same shape of
    inflation as counting a process that merely started as a check that passed.
    """
    # The non-firing victim goes FIRST: with no evidence yet there is nothing to contrast, so the
    # chooser takes the first remaining victim and the observation is certainly spent. Anywhere later
    # it may be skipped entirely once the scope is identified, and then the count would be 0 for a
    # reason that has nothing to do with this test.
    corpus = [NEVER_FIRES, VICTIMS[0], VICTIMS[1], VICTIMS[2], VICTIMS[5], VICTIMS[6]]
    out = acq.buy_scope(taught_rule, corpus, budget=len(corpus))
    assert out["status"].startswith("IDENTIFIED"), out["status"]
    assert out["not_applicable"] == 1
    assert out["evidence_rows"] == out["observations_spent"] - 1, (
        "a non-firing is spent but is not evidence")
    silent = [t for t in out["trace"] if t["verdict"] == acq.NOT_APPLICABLE]
    assert len(silent) == 1 and silent[0]["label"] == "no_operator_anywhere"
    assert silent[0]["evidence"] is False


def test_the_verdict_table_is_two_sided():
    """A firing that does not repair is evidence but NOT a success.

    Without this the table collapses to fired/succeeded, and `NOOP_CORRECT` -- a skill firing on code
    that was already right and leaving it right -- would be counted as a repair. Injecting the
    proposer is what makes the two rows reachable without inventing a victim whose spec contradicts
    the probe's pinned numbers.
    """
    src = "def f(x, hi):\n    return x >= hi\n"
    spec = "assert f(10, 10) is True\n"
    rule = {"language": "python", "pattern_tokens": [], "replacement_tokens": []}

    def echo(source, rule, language=None):
        return [source]

    def ruin(source, rule, language=None):
        return ["def f(x, hi):\n    return 0\n"]

    noop = acq.observe(rule, src, spec, propose=echo)
    assert noop["verdict"] == acq.NOOP_CORRECT
    assert noop["fired"] and noop["baseline_ok"] and noop["solved"]
    assert noop["row"][1] is False, "leaving correct code correct is not a repair"

    # NB `x <= hi` would SATISFY this spec, so the baseline would be correct and a failed candidate
    # would read as BROKE_CORRECT_CODE. The source has to actually fail its own specification.
    wrong = acq.observe(rule, "def f(x, hi):\n    return x < hi\n", spec, propose=ruin)
    assert wrong["verdict"] == acq.FIRED_STILL_WRONG
    assert wrong["baseline_ok"] is False and wrong["solved"] is False
    assert wrong["row"][1] is False

    for verdict in (acq.NOOP_CORRECT, acq.FIRED_STILL_WRONG, acq.BROKE_CORRECT):
        assert verdict in acq.IS_EVIDENCE and verdict not in acq.IS_SUCCESS
    assert acq.REPAIRED in acq.IS_EVIDENCE and acq.REPAIRED in acq.IS_SUCCESS


def test_an_unexecuted_baseline_is_not_a_fact():
    facts = acq.observable_facts("def f(x, hi):\n    return x <= hi\n", baseline_ok=None)
    assert "baseline.not_executed" in facts
    assert acq.BASELINE_VIOLATES not in facts
    assert acq.BASELINE_SATISFIES not in facts


def test_a_language_with_no_extractor_refuses_rather_than_guessing():
    """The walker is a Python AST walker. A fact from the wrong parser is worse than no fact."""
    with pytest.raises(acq.ScopeAcquisitionError) as exc:
        acq.observable_facts("func f(x int) bool { return x <= 10 }\n", baseline_ok=False,
                             language="go")
    assert "NO_FACT_EXTRACTOR_FOR_LANGUAGE:go" in str(exc.value)


def test_an_unparseable_source_says_so_instead_of_inventing_sites():
    facts = acq.observable_facts("def f(:\n", baseline_ok=False)
    assert "source.unparseable" in facts
    assert not any(f.startswith("site.") for f in facts)


# --------------------------------------------------------------------------- admits, both directions
def test_admits_refuses_only_when_the_identified_requirement_is_absent():
    req = ["baseline.violates_own_spec"]
    yes = acq.admits(req, {"baseline.violates_own_spec", "site.return"})
    no = acq.admits(req, {"baseline.satisfies_own_spec", "site.return"})
    assert yes["admitted"] is True and yes["basis"] == "REQUIREMENT_SATISFIED"
    assert no["admitted"] is False and no["basis"] == "IDENTIFIED_REQUIREMENT_ABSENT"
    assert no["missing"] == ["baseline.violates_own_spec"]


def test_admits_without_an_identified_requirement_does_not_pretend_to_a_check():
    out = acq.admits(None, {"site.return"})
    assert out["admitted"] is True
    assert out["basis"] == "NO_IDENTIFIED_REQUIREMENT__NOTHING_TO_WITHHOLD_ON"


# --------------------------------------------------------------------------- the pool is the caller's
def test_the_probe_chooser_needs_realisable_states_and_says_so_without_them(taught_rule):
    """Observed states alone cannot split the survivors; the caller owns realisability.

    This is the trap that produced `NO_REACHABLE_STATE_SPLITS_THE_SURVIVORS` on real evidence: the
    pool must contain states that could still be OBSERVED, and inventing them is not the same as
    making them. Here the pool is built by executing the remaining victims' own specifications, so
    an already-correct victim contributes `baseline.satisfies_own_spec` -- the very fact that
    distinguishes it -- rather than a fact asserted about it.
    """
    observed = [acq.observe(taught_rule, v["source"], v["spec"]) for v in VICTIMS[:4]]
    rows = [(list(o["row"][0]), bool(o["row"][1])) for o in observed if o["row"]]
    assert len(rows) == 4
    # four successes and no failure: the law refuses to name anything, and there is nothing to split
    assert app.learn(rows).status == "UNDETERMINED__NO_CONTRASTING_OUTCOME"

    observed_only = cs.select_contrast(rows, cs.observed_states(rows))
    assert observed_only.informative is False
    assert observed_only.status == "NO_REACHABLE_STATE_SPLITS_THE_SURVIVORS"

    realisable = [acq.observable_facts(v["source"],
                                       baseline_ok=acq._default_executor(v["source"], v["spec"]))
                  for v in VICTIMS[4:]]
    assert any(acq.BASELINE_SATISFIES in s for s in realisable), "the pool must be genuinely realisable"
    chosen = cs.select_contrast(rows, realisable)
    assert chosen.status.startswith("SELECTED"), chosen.status
    assert chosen.informative is True
    assert chosen.worst_case_survivors_after < chosen.survivors_before


def test_once_identified_no_contrast_is_needed(taught_rule):
    """The other side: after the boundary is bought, offering a pool must not manufacture work."""
    observed = [acq.observe(taught_rule, v["source"], v["spec"]) for v in VICTIMS]
    rows = [(list(o["row"][0]), bool(o["row"][1])) for o in observed if o["row"]]
    assert app.learn(rows).status.startswith("IDENTIFIED")
    out = cs.select_contrast(rows, [frozenset(o["state"]) for o in observed])
    assert out.informative is False
    assert out.status == "ALREADY_IDENTIFIED__NO_CONTRAST_NEEDED"


# --------------------------------------------------------------------------- discipline
def test_buy_scope_refuses_an_empty_corpus():
    with pytest.raises(acq.ScopeAcquisitionError) as exc:
        acq.buy_scope({}, [])
    assert "REQUIRES_VICTIMS" in str(exc.value)


def test_the_module_exposes_no_acceptance_surface():
    """`admits` decides whether to PROPOSE; the caller's verifier still decides the outcome."""
    public = {n for n in dir(acq) if not n.startswith("_")}
    assert not (public & {"apply", "accept", "commit", "store", "save"}), public


def test_the_demonstration_is_reproducible(doc):
    again = demonstration()
    for key in ("repaired", "broke_correct_code_before_scope", "observations_to_identify",
                "required", "status", "repairs_after_scope", "broke_correct_code_after_scope",
                "refusals"):
        assert again[key] == doc[key], key


def test_the_law_used_is_the_trees_own_and_not_a_private_one():
    """If this module grew its own learner, the production law and the measurement could drift."""
    assert acq.scope_of is not None
    rows = [(["a"], True), (["b"], False)]
    assert acq.scope_of(rows).status == app.learn(rows).status
    assert acq.scope_of(rows).required == app.learn(rows).required
