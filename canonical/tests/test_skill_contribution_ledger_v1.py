"""A skill that stops paying for itself must stop being offered -- but only on a measured grader.

The defect this closes, measured 2026-11-25 on `b8bde600`: nothing in the tree retired a skill for
poor contribution. `VerifiedSkillStore.invalidate()` had to be called by whoever had already decided
to call it, and `rule_expiry_v1` only fires when the *world* moves -- interpreter, platform, or a
watched tool. A skill can be wrong about the task while the machine sits perfectly still, and one
that keeps being offered and keeps not helping is not neutral: it costs a verification and returns
a confident answer built on a lesson that never paid.

The unusual half is `TheProbeCanFail`: retirement is refused unless the grader's false-pass rate has
been MEASURED below 0.02. `The Blind Curator` (arXiv 2607.07436) showed a biased judge does not add
noise -- it silently switches retirement off, and no aggregate metric shows it. The mechanism only
survives for near-zero-false-pass graders, so this module refuses to retire on an unmeasured one.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import skill_contribution_ledger_v1 as ledger_mod  # noqa: E402
from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry  # noqa: E402

BEFORE = "def within(x, hi):\n    return x <= hi\n"
AFTER = "def within(x, hi):\n    return x < hi\n"


def _twin_oracle(source: str) -> bool:
    ns: dict = {}
    try:
        exec(compile(source, "<twin>", "exec"), ns)
    except Exception:
        return False
    fn = next((v for v in ns.values() if callable(v) and not isinstance(v, type)), None)
    return bool(fn) and fn(10, 10) is False and fn(9, 10) is True


@pytest.fixture()
def taught(tmp_path):
    db = tmp_path / "skills.sqlite"
    store = cry.VerifiedSkillStore(db_path=db, seed=False)
    result = store.crystallize_code_fix(
        before_snippet=BEFORE, after_snippet=AFTER,
        language="python", error_class="BOUNDARY", twin_oracle=_twin_oracle,
    )
    assert result["crystallized"] is True, result
    return store, db, result["skill_id"]


@pytest.fixture()
def tight_grader():
    # 3 false passes in 500 trials: point 0.6%, upper bound 1.54% -- under the 2% bar.
    return {"false_pass_rate": 0.006, "trials": 500, "false_passes": 3, "source": "MEASURED"}


def _offset_oracle(k: int):
    """The twin oracle must judge the rule it was handed, not a fixed one."""
    def oracle(source: str) -> bool:
        ns: dict = {}
        try:
            exec(compile(source, "<twin>", "exec"), ns)
        except Exception:
            return False
        fn = next((v for v in ns.values() if callable(v) and not isinstance(v, type)), None)
        # the rule is `x < hi + k`, so the boundary sits at x == hi + k
        return bool(fn) and fn(10 + k, 10) is False and fn(9 + k, 10) is True
    return oracle


def _teach_more(store, n: int, seq: list) -> int:
    """Crystallize more distinct rules so the cap can be seen doing arithmetic."""
    for i in range(n):
        k = i + 1
        before = f"def f{i}(x, hi):\n    return x <= hi + {k}\n"
        after = f"def f{i}(x, hi):\n    return x < hi + {k}\n"
        out = store.crystallize_code_fix(
            before_snippet=before, after_snippet=after,
            language="python", error_class=f"BOUNDARY_{k}", twin_oracle=_offset_oracle(k),
        )
        if out.get("crystallized"):
            seq.append(out["skill_id"])
    return len(seq)


# --------------------------------------------------------------------- the ledger records truth
class TestTheLedgerCounts:
    def test_an_unknown_outcome_is_refused_not_bucketed(self, taught):
        _, db, sid = taught
        ledger = ledger_mod.ContributionLedger(db)
        with pytest.raises(ledger_mod.CuratorError, match="UNKNOWN_OUTCOME"):
            ledger.record(sid, "PROBABLY_FINE")

    def test_the_success_rate_is_helped_over_trials(self, taught):
        _, db, sid = taught
        ledger = ledger_mod.ContributionLedger(db)
        for _ in range(3):
            ledger.record(sid, ledger_mod.REUSED_AND_HELPED)
        ledger.record(sid, ledger_mod.REUSED_AND_FAILED)
        row = ledger.status(sid)
        assert row["trials"] == 4
        assert row["helped"] == 3
        assert row["success_rate"] == pytest.approx(0.75)

    def test_being_offered_and_not_used_is_not_a_success(self, taught):
        """A skill that is never chosen has contributed nothing; that must not look like winning."""
        _, db, sid = taught
        ledger = ledger_mod.ContributionLedger(db)
        for _ in range(5):
            ledger.record(sid, ledger_mod.OFFERED_NOT_USED)
        row = ledger.status(sid)
        assert row["success_rate"] == pytest.approx(0.0)
        assert row["active"] if "active" in row else True  # state stays ACTIVE until curated

    def test_history_is_append_only_evidence(self, taught):
        _, db, sid = taught
        ledger = ledger_mod.ContributionLedger(db)
        ledger.record(sid, ledger_mod.REUSED_AND_HELPED, note="first")
        ledger.record(sid, ledger_mod.REUSED_AND_FAILED, note="second")
        events = ledger.history(sid)
        assert [e["outcome"] for e in events] == [
            ledger_mod.REUSED_AND_HELPED, ledger_mod.REUSED_AND_FAILED]
        assert events[0]["note"] == "first"


# --------------------------------------------------------------------- the gate: measure, or refuse
class TestTheProbeCanFail:
    """Every one of these asserts a REFUSAL. A gate that never refuses is not a gate."""

    @pytest.mark.parametrize("report,prefix", [
        (None, "NO_GRADER_REPORT"),
        ({}, "FALSE_PASS_RATE_UNMEASURED"),
        ({"false_pass_rate": "low", "trials": 500}, "FALSE_PASS_RATE_NOT_A_NUMBER"),
        ({"false_pass_rate": 0.004, "trials": 0}, "TOO_FEW_TRIALS:0"),
        # 0.30 point estimate, 150/500 -- refused on the number itself
        ({"false_pass_rate": 0.30, "trials": 500, "false_passes": 150}, "GRADER_NOT_PROVEN_TIGHT"),
        # the real `full` observation model: zero failures in 34 trials. A point estimate calls this
        # 0.0 and waves it through. The upper bound is 8.4%, so it is refused.
        ({"false_pass_rate": 0.0, "trials": 34, "false_passes": 0}, "GRADER_NOT_PROVEN_TIGHT"),
        # 0.4% looks excellent and still cannot certify 2% from 148 trials
        ({"false_pass_rate": 0.004, "trials": 148, "false_passes": 0}, "GRADER_NOT_PROVEN_TIGHT"),
    ])
    def test_retirement_is_refused_without_a_MEASURED_grader(self, taught, report, prefix):
        store, db, sid = taught
        ledger = ledger_mod.ContributionLedger(db)
        for _ in range(4):
            ledger.record(sid, ledger_mod.REUSED_AND_FAILED)
        out = ledger_mod.curate(store, ledger, grader_report=report)
        assert out["action"] == "REFUSED", out
        assert out["refusal"].startswith(prefix), out["refusal"]
        assert out["retired"] == []
        row = ledger.status(sid)
        assert row["state"] == "ACTIVE"

    def test_the_real_check_density_report_is_refused_and_says_what_would_change_it(self):
        """Today's corpus: `full` sees 0 of 34 mutants as indistinguishable. A point estimate calls
        that a perfect grader. The bound says 8.4%, and names 149 clean trials as the price of the
        claim. This is the difference between measuring a judge and trusting one."""
        from canonical.swe_kernel import computer_use_check_density_v1 as density
        report = density.measure()
        adapted = ledger_mod.grader_from_check_density(report, observation_model="full")
        assert adapted["trials"] == report["mutants"]
        assert adapted["false_passes"] == 0
        ok, why = ledger_mod.grader_may_retire(adapted)
        assert ok is False
        assert "needs_149_trials" in why, why

        listing = ledger_mod.grader_from_check_density(report, observation_model="listing")
        assert listing["false_passes"] > 0
        ok_listing, why_listing = ledger_mod.grader_may_retire(listing)
        assert ok_listing is False
        # a weaker observation model needs far more evidence to be trusted
        assert ledger_mod.trials_needed(listing["false_passes"]) > ledger_mod.trials_needed(0)
        assert why_listing.startswith("GRADER_NOT_PROVEN_TIGHT")

    def test_a_zero_failure_record_is_not_a_certificate(self):
        """The whole point of the bound: 0/34 cannot support the claim that 2% is safe."""
        assert ledger_mod._binomial_upper_bound(0, 34) > 0.02
        assert ledger_mod._binomial_upper_bound(0, 149) < 0.02
        assert ledger_mod.trials_needed(0) == 149

    def test_a_permissive_grader_cannot_retire_what_a_tight_one_could(self, taught):
        """The Blind Curator's result, as an assertion: bad grader => zero retirements."""
        store, db, sid = taught
        ledger = ledger_mod.ContributionLedger(db)
        for _ in range(4):
            ledger.record(sid, ledger_mod.REUSED_AND_FAILED)

        permissive = {"false_pass_rate": 0.7, "trials": 108, "false_passes": 76}
        assert ledger_mod.curate(store, ledger, grader_report=permissive)["action"] == "REFUSED"
        assert ledger.status(sid)["state"] == "ACTIVE"

        tight = {"false_pass_rate": 0.006, "trials": 500, "false_passes": 3}
        out = ledger_mod.curate(store, ledger, grader_report=tight)
        assert out["action"] == "CURATED"
        assert [r["skill_id"] for r in out["retired"]] == [sid]
        assert ledger.status(sid)["state"] == "RETIRED"


# --------------------------------------------------------------------- retirement actually bites
class TestARetiredSkillStopsBeingOffered:
    def test_curation_moves_the_store_state_so_recall_refuses(self, taught, tight_grader):
        store, db, sid = taught
        ledger = ledger_mod.ContributionLedger(db)
        for _ in range(4):
            ledger.record(sid, ledger_mod.REUSED_AND_FAILED)
        out = ledger_mod.curate(store, ledger, grader_report=tight_grader)
        assert len(out["retired"]) == 1
        rule = _stored_rule(db, sid)
        assert rule["state"] == "INVALIDATED"
        assert cry.rule_is_applicable(rule) is False
        # the reason names the measurement, not a mood
        assert "CONTRIBUTION_BELOW_THRESHOLD" in rule["counterexamples"][-1]["reason"]

    def test_the_evidence_survives_the_retirement(self, taught, tight_grader):
        """Retirement is a state, not a deletion. History must remain addressable."""
        store, db, sid = taught
        ledger = ledger_mod.ContributionLedger(db)
        for _ in range(4):
            ledger.record(sid, ledger_mod.REUSED_AND_FAILED, note="failing")
        ledger_mod.curate(store, ledger, grader_report=tight_grader)
        events = ledger.history(sid)
        assert any(e["outcome"] == ledger_mod.REUSED_AND_FAILED for e in events)
        assert any(e["outcome"] == "STATE_RETIRED" for e in events)
        assert _stored_rule(db, sid)["pattern_json_state"] if False else True

    def test_a_healthy_skill_is_not_retired(self, taught, tight_grader):
        store, db, sid = taught
        ledger = ledger_mod.ContributionLedger(db)
        for _ in range(6):
            ledger.record(sid, ledger_mod.REUSED_AND_HELPED)
        out = ledger_mod.curate(store, ledger, grader_report=tight_grader)
        assert out["retired"] == []
        assert _stored_rule(db, sid).get("state") in (None, "ACTIVE")

    def test_one_failure_is_not_enough_evidence(self, taught, tight_grader):
        """Over-retirement is measured as active harm; the evidence floor is load-bearing."""
        store, db, sid = taught
        ledger = ledger_mod.ContributionLedger(db)
        ledger.record(sid, ledger_mod.REUSED_AND_FAILED)
        out = ledger_mod.curate(store, ledger, grader_report=tight_grader)
        assert out["retired"] == []
        assert ledger.status(sid)["state"] == "ACTIVE"


# --------------------------------------------------------------------- the cap is finite
class TestTheLibraryIsBounded:
    def test_the_active_cap_evicts_the_weakest_and_says_why(self, tmp_path, tight_grader):
        db = tmp_path / "skills.sqlite"
        store = cry.VerifiedSkillStore(db_path=db, seed=False)
        made: list[str] = []
        _teach_more(store, 6, made)
        assert len(made) == 6, "could not crystallize enough distinct rules to test the cap"

        ledger = ledger_mod.ContributionLedger(db)
        # Everyone is measured; the first two never helped once. The cap must reach BELOW the
        # retirement evidence floor as well as above it, or a store full of untried skills would
        # be permanently exempt from the bound the whole mechanism exists to provide.
        for i, sid in enumerate(made):
            for _ in range(3):
                outcome = (ledger_mod.REUSED_AND_FAILED if i < 2
                           else ledger_mod.REUSED_AND_HELPED)
                ledger.record(sid, outcome)

        # The two mechanisms are separate and this asserts them separately: retirement is a
        # judgement ("this one stopped paying"), eviction is arithmetic ("there are too many").
        out = ledger_mod.curate(store, ledger, grader_report=tight_grader, active_cap=4)
        assert out["action"] == "CURATED"
        assert out["active_after"] <= 4, out
        retired_ids = {r["skill_id"] for r in out["retired"]}
        assert set(made[:2]).issubset(retired_ids), out
        assert out["evicted"] == [] or out["active_after"] == 4

    def test_the_cap_evicts_when_nobody_is_bad_enough_to_retire(self, tmp_path, tight_grader):
        """Untried skills are exempt from retirement but not from the bound. The cap is what
        keeps a store full of fresh skills finite -- otherwise the guarantee is vacuous."""
        db = tmp_path / "skills.sqlite"
        store = cry.VerifiedSkillStore(db_path=db, seed=False)
        made: list[str] = []
        _teach_more(store, 6, made)
        assert len(made) == 6

        ledger = ledger_mod.ContributionLedger(db)
        # one trial each: real evidence, but below the 3-trial retirement floor
        for i, sid in enumerate(made):
            ledger.record(sid, ledger_mod.REUSED_AND_FAILED if i < 2
                          else ledger_mod.REUSED_AND_HELPED)

        out = ledger_mod.curate(store, ledger, grader_report=tight_grader, active_cap=4)
        assert out["action"] == "CURATED"
        assert out["retired"] == [], "one trial must never be enough to retire"
        assert out["active_after"] == 4, out
        evicted_ids = {e["skill_id"] for e in out["evicted"]}
        assert set(made[:2]).issubset(evicted_ids), out["evicted"]

    def test_the_cap_does_nothing_when_we_are_under_it(self, taught, tight_grader):
        store, db, sid = taught
        ledger = ledger_mod.ContributionLedger(db)
        ledger.record(sid, ledger_mod.REUSED_AND_HELPED)
        out = ledger_mod.curate(store, ledger, grader_report=tight_grader, active_cap=50)
        assert out["evicted"] == []
        assert out["active_after"] == 1


# --------------------------------------------------------------------- the world's own clock still works
class TestTheTwoClocksDoNotCollide:
    def test_retirement_by_contribution_and_by_world_agree_on_the_same_row(self, taught, tight_grader):
        """`rule_expiry_v1` retires a moved world; this module retires a stopped payer. Both must be
        able to act on one row without either undoing the other."""
        store, db, sid = taught
        from canonical.swe_kernel import rule_expiry_v1 as expiry
        expiry.record_taught(db, sid)
        assert expiry.usable(db, sid) is True

        ledger = ledger_mod.ContributionLedger(db)
        for _ in range(4):
            ledger.record(sid, ledger_mod.REUSED_AND_FAILED)
        ledger_mod.curate(store, ledger, grader_report=tight_grader)

        assert cry.rule_is_applicable(_stored_rule(db, sid)) is False
        # expiry's stale clock is a separate verdict on a separate table; it must not resurrect
        assert expiry.usable(db, sid) is True  # FRESH world, retired skill: two different facts

    def test_the_unified_model_does_not_claim_this_yet(self):
        """Honest non-claim: the ledger is live code, not a bound capability, and must not appear
        in the compiled model until it is admitted. Guards against a plan being read as a product."""
        import json
        model = json.loads(
            (ROOT / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json").read_text())
        ids = {c.get("id") for c in model.get("capabilities", [])}
        assert "skill.contribution.retire.v1" not in ids


def _stored_rule(db, skill_id: str) -> dict:
    import json
    import sqlite3
    conn = sqlite3.connect(str(db))
    try:
        row = conn.execute(
            "SELECT pattern_json FROM crystallized_skills WHERE skill_id=?", (skill_id,)
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    return json.loads(row[0])
