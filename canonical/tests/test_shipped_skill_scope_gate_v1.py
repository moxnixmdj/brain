"""The shipped store carries scope, and recall withholds on it exactly when the law says.

These tests judge `skill_scope_bundle_v1` in the directions that matter, each of which fails
silently rather than loudly if it regresses:

  * BOTH NUMBERS MUST MOVE. Unscoped, each identified rule repairs its nine defective paired
    victims and breaks the nine already-correct ones. Gated, all eighteen repairs are still
    admitted and all eighteen breakages are refused by name. If only one number moves the
    scope is decoration.
  * WITHHOLD ONLY ON IDENTIFIED. No scope, or a scope the evidence never identified, must
    ADMIT with a named `NOTHING_TO_WITHHOLD_ON` basis -- a pretended check is the failure this
    module exists to prevent, in the opposite direction from the breakage.
  * AN UNEXECUTED BASELINE IS NOT A FACT. An identified scope with no oracle refuses by name
    instead of guessing.
  * THE LABEL IS EARNED. Evidence with successes only must not identify a requirement.
  * THE WIRING IS REAL. `recall_and_apply_verified` on a scoped store probes the baseline and
    proposes nothing against already-correct code; on the same store without scope the
    candidate is evaluated exactly as before. Import/export round-trips keep both the scope
    blocks and every content address.

Authority: NONE. Constructed paired fixtures executed against their own specifications, the
same standard `skill_scope_acquisition_probe_v1` is judged by.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import skill_scope_acquisition_v1 as acq  # noqa: E402
from canonical.swe_kernel import skill_scope_bundle_v1 as ssb  # noqa: E402
from canonical.swe_kernel import verified_skill_crystallizer_v1 as cry  # noqa: E402

BUNDLE_PATH = ROOT / "canonical" / "astra_runtime" / "skills" / "VERIFIED_SKILLS_BUNDLE_V1.json"


@pytest.fixture(scope="module")
def original():
    return ssb.load_bundle(BUNDLE_PATH)


@pytest.fixture(scope="module")
def attached(original):
    bundle, report = ssb.attach_scopes(original)
    return bundle, report


def _identified_rules(bundle):
    return [e["rule"] for e in bundle.get("rules") or ()
            if ssb.has_identified_scope(e.get("rule") or {})]


def _victims(rule):
    victims, not_bought = ssb.paired_victims(rule)
    assert not_bought is None, not_bought
    defective = [v for v in victims if v["label"].endswith("_defect")]
    correct = [v for v in victims if v["label"].endswith("_already_correct")]
    assert len(defective) == len(correct) == 9, (len(defective), len(correct))
    return defective, correct


# --------------------------------------------------------------------------- buying
def test_attach_identifies_scope_for_exactly_the_python_shipped_rules(attached):
    bundle, report = attached
    by_lang = {e["skill_id"]: e for e in report["entries"]}
    identified = [e for e in report["entries"] if e["status"].startswith("IDENTIFIED")]
    assert report["identified"] == len(identified) == 2
    for entry in identified:
        assert entry["language"] == "python"
        assert entry["required"] == ["baseline.violates_own_spec"]
        assert entry["observations_spent"] >= 2  # a failure had to be observed
        assert entry["evidence_rows"] == entry["observations_spent"]
    # the other three carry a state, not silence -- the deepest true reason per rule
    assert by_lang["skill_72276765c53ffea4"]["status"] == (
        "SCOPE_NOT_BOUGHT__NOT_A_SINGLE_OPERATOR_LESSON")
    assert by_lang["skill_9df30abeb867023c"]["status"] == (
        "SCOPE_NOT_BOUGHT__NOT_A_SINGLE_OPERATOR_LESSON")
    assert by_lang["skill_f8b41c7e705cda49"]["status"] == (
        "SCOPE_NOT_BOUGHT__NO_FACT_EXTRACTOR_FOR_LANGUAGE")
    assert report["not_bought"] == 3


def test_attachment_preserves_every_content_address(attached, original):
    """The scope block must not move the identity of a single shipped rule."""
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import skill_identity
    for before, after in zip(original["rules"], attached[0]["rules"]):
        assert before["skill_id"] == after["skill_id"]
        assert skill_identity(after["rule"]) == before["skill_id"]
        assert "scope" in after["rule"]


def test_the_label_is_earned_not_a_constant(attached):
    """Successes alone may not name a requirement: necessity is only refuted by failure."""
    rule = _identified_rules(attached[0])[0]
    victims, _ = ssb.paired_victims(rule)
    successes_only = [v for v in victims if v["label"].endswith("_defect")]
    assert len(successes_only) == 9
    report = acq.buy_scope(rule, successes_only, budget=len(successes_only), language="python")
    assert report["failures"] == 0
    assert not report["status"].startswith("IDENTIFIED"), report["status"]
    assert report["required"] in (None, ())


# --------------------------------------------------------------------------- both numbers move
def test_unscoped_the_skill_repairs_defects_and_breaks_correct_code(attached):
    for rule in _identified_rules(attached[0]):
        defective, correct = _victims(rule)
        verdicts_d = [acq.observe(rule, v["source"], v["spec"])["verdict"] for v in defective]
        verdicts_c = [acq.observe(rule, v["source"], v["spec"])["verdict"] for v in correct]
        assert verdicts_d == [acq.REPAIRED] * 9, verdicts_d
        assert verdicts_c == [acq.BROKE_CORRECT] * 9, verdicts_c


def test_gated_every_repair_is_kept_and_every_breakage_is_refused_by_name(attached):
    for rule in _identified_rules(attached[0]):
        defective, correct = _victims(rule)
        for victim in defective:
            faithful = lambda s, spec=victim["spec"]: ssb._exec_ok(s, spec)  # noqa: E731
            gate = ssb.admit(rule, victim["source"], verifier=faithful)
            assert gate["admitted"] is True, gate
            assert gate["basis"] == "REQUIREMENT_SATISFIED", gate
            assert gate["missing"] == []
        for victim in correct:
            faithful = lambda s, spec=victim["spec"]: ssb._exec_ok(s, spec)  # noqa: E731
            gate = ssb.admit(rule, victim["source"], verifier=faithful)
            assert gate["admitted"] is False, gate
            assert gate["missing"] == ["baseline.violates_own_spec"], gate
            assert gate["scope_status"].startswith("IDENTIFIED")


# --------------------------------------------------------------------------- the law, both sides
def test_a_rule_without_scope_admits_with_a_named_basis(attached):
    rule = dict(_identified_rules(attached[0])[0])
    rule.pop("scope", None)
    gate = ssb.admit(rule, "def f(a, b):\n    return a + b\n", verifier=lambda s: True)
    assert gate["admitted"] is True
    assert gate["basis"] == "NO_IDENTIFIED_SCOPE__NOTHING_TO_WITHHOLD_ON"
    assert gate["scope_status"] is None


def test_a_scope_the_evidence_never_identified_also_admits_by_name(attached):
    rule = dict(_identified_rules(attached[0])[0])
    rule["scope"] = {"status": "SCOPE_NOT_BOUGHT__NOT_A_SINGLE_OPERATOR_LESSON",
                     "required": None}
    gate = ssb.admit(rule, "def f(a, b):\n    return a + b\n", verifier=lambda s: True)
    assert gate["admitted"] is True
    assert gate["basis"] == (
        "SCOPE_SCOPE_NOT_BOUGHT__NOT_A_SINGLE_OPERATOR_LESSON__NOTHING_TO_WITHHOLD_ON")
    assert gate["missing"] == []


def test_an_identified_scope_without_an_oracle_refuses_by_name(attached):
    rule = _identified_rules(attached[0])[0]
    gate = ssb.admit(rule, "def f(a, b):\n    return a + a * b\n", verifier=None)
    assert gate["admitted"] is False
    assert "NO_ORACLE__BASELINE_NOT_EXECUTED" in gate["basis"]
    assert gate["missing"] == ["baseline.violates_own_spec"]


# --------------------------------------------------------------------------- storage round-trip
def test_import_and_export_keep_scope_and_addresses(attached, tmp_path):
    path = tmp_path / "scoped.json"
    ssb.save_bundle(attached[0], path)
    store = cry.VerifiedSkillStore(db_path=tmp_path / "store.sqlite", seed=False)
    result = store.import_bundle(path)
    assert result["accepted"] == 5, result
    assert result["refused"] == 0, result.get("refusals")
    exported = store.export_bundle()
    assert exported["rule_count"] == 5
    from canonical.swe_kernel.verified_skill_crystallizer_v1 import skill_identity
    for entry in exported["rules"]:
        assert "scope" in entry["rule"], entry["skill_id"]
        assert skill_identity(entry["rule"]) == entry["skill_id"]


def test_reimporting_a_scoped_bundle_into_a_populated_store_upgrades_scope(attached, tmp_path):
    """A merge must never silently roll a record back to EXACT_MATCH_ONLY."""
    original_plain = ssb.load_bundle(BUNDLE_PATH)
    path_plain = tmp_path / "plain.json"
    path_scoped = tmp_path / "scoped.json"
    ssb.save_bundle(original_plain, path_plain)
    ssb.save_bundle(attached[0], path_scoped)
    store = cry.VerifiedSkillStore(db_path=tmp_path / "store.sqlite", seed=False)
    assert store.import_bundle(path_plain)["accepted"] == 5
    upgraded = store.import_bundle(path_scoped)
    assert upgraded["merged"] + upgraded["accepted"] == 5, upgraded
    exported = store.export_bundle()
    identified = [e for e in exported["rules"] if ssb.has_identified_scope(e["rule"])]
    assert len(identified) == 2, [e["rule"].get("scope") for e in exported["rules"]]


# --------------------------------------------------------------------------- the wiring
def _recording_verifier(victim):
    calls: list[str] = []
    def verifier(source: str) -> bool:
        calls.append(source)
        return ssb._exec_ok(source, victim["spec"])
    return verifier, calls


def _recall(store, victim):
    verifier, calls = _recording_verifier(victim)
    result = store.recall_and_apply_verified(
        source_text=victim["source"], language="python", verifier=verifier,
        error_class="python_test_repair")
    return result, calls


def test_recall_withholds_from_correct_code_and_still_repairs_defects(attached, tmp_path):
    path = tmp_path / "scoped.json"
    ssb.save_bundle(attached[0], path)
    store = cry.VerifiedSkillStore(db_path=tmp_path / "store.sqlite", seed=False)
    assert store.import_bundle(path)["accepted"] == 5

    rule = _identified_rules(attached[0])[0]
    defective, correct = _victims(rule)

    # Already-correct target: the gate probes the BASELINE and proposes nothing -- exactly
    # one verifier call, and it is the original source, never a candidate.
    result, calls = _recall(store, correct[0])
    assert result is None
    assert calls == [correct[0]["source"]], "a candidate was evaluated against correct code"

    # Defective target: baseline says violates, candidate is proposed and verified -> hit.
    result, calls = _recall(store, defective[0])
    assert result is not None, "the scope withheld a repair it was bought to permit"
    assert result.get("patched_source")
    assert calls[0] == defective[0]["source"]
    assert len(calls) >= 2, "the candidate was never evaluated"


def test_without_scope_recall_evaluates_candidates_exactly_as_before(attached, tmp_path):
    """The gate is inert on an unscoped store: the same correct target gets its candidate
    evaluated (and rejected by the verifier), proving the withholding above is the scope and
    not some other change to the recall path."""
    # The control store: the same shipped rules with their scope blocks stripped, so any
    # difference in recall behaviour above is attributable to the scope and nothing else.
    original_plain = ssb.load_bundle(BUNDLE_PATH)
    for entry in original_plain["rules"]:
        entry["rule"].pop("scope", None)
    path = tmp_path / "plain.json"
    ssb.save_bundle(original_plain, path)
    store = cry.VerifiedSkillStore(db_path=tmp_path / "store.sqlite", seed=False)
    assert store.import_bundle(path)["accepted"] == 5

    # The attached bundle is a deep copy of the original: same order, same payloads.
    assert original_plain["rules"][0]["skill_id"] == attached[0]["rules"][0]["skill_id"]
    assert ssb.has_identified_scope(attached[0]["rules"][0]["rule"])
    rule_plain = original_plain["rules"][0]["rule"]
    assert "scope" not in rule_plain
    defective, correct = _victims(rule_plain)

    result, calls = _recall(store, correct[0])
    assert result is None
    assert len(calls) == 1
    assert calls[0] != correct[0]["source"], "unscoped recall should evaluate a candidate"

    result, calls = _recall(store, defective[0])
    assert result is not None
    assert calls[0] != defective[0]["source"], "unscoped recall evaluates candidates only"
