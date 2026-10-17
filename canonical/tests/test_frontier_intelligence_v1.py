"""Tests for PROJECT_BRAIN_FRONTIER_INTELLIGENCE_V1.

The claim is that all three terms of the equation are present and wired:

    EFFECTIVE FRONTIER INTELLIGENCE
      = CAPABILITY + JIT KNOWLEDGE + COMPUTATION SUBSTRATE

and that the seam between owned capability and fetched knowledge is visible
rather than blurred -- ownership is what the law scores, so a capability is
never counted in both columns.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "runtime"))
sys.path.insert(0, str(ROOT))

import capability_composer_v1 as C  # noqa: E402
import frontier_intelligence_v1 as FI  # noqa: E402

G = C.graph()
WORLD = C.external_tokens(G)


# --------------------------------------------------------------------------- #
# the three terms
# --------------------------------------------------------------------------- #
def test_all_three_terms_are_present():
    t = FI.terms(G)
    assert len(t["CAPABILITY"]) == 64
    assert len(t["JIT_KNOWLEDGE"]) == 4
    assert sum(len(v) for v in t.values()) == 68
    assert FI.substrate()["available"] is True


def test_owned_and_fetched_do_not_overlap():
    t = FI.terms(G)
    assert not set(t["CAPABILITY"]) & set(t["JIT_KNOWLEDGE"])


def test_jit_is_the_external_knowledge_path():
    assert FI.is_jit("knowledge.json.fetch.external")
    assert not FI.is_jit("pdf.extract.text.pypdf")


def test_jit_tokens_are_the_knowledge_lifecycle():
    toks = FI.jit_produced_tokens(G)
    assert "knowledge.observation.available" in toks   # acquire
    assert "knowledge.assessment.available" in toks    # verify
    assert "knowledge.status.verified" in toks         # assert
    assert "knowledge.fact.materialized" in toks       # preserve compact evidence


# --------------------------------------------------------------------------- #
# the seam
# --------------------------------------------------------------------------- #
def test_owned_goal_uses_no_external_knowledge():
    out = FI.solve("evidence.claim.exact_quoted_bound", WORLD, G)
    assert out["owned_capability"] == [
        "source.objective_relevance.rank.bm25",
        "source.evidence.extract.objective_grounded.stdlib",
        "evidence.claim_relation.generic_units.stdlib",
        "evidence.claim_spec.bind.explicit_comparison.stdlib",
    ]
    assert out["jit_knowledge"] == []
    assert out["unresolved_gaps"] == []


def test_knowledge_goal_routes_to_the_jit_path():
    out = FI.solve("knowledge.status.verified", WORLD, G)
    assert out["owned_capability"] == []
    assert out["jit_knowledge"] == [
        "knowledge.json.fetch.external",
        "knowledge.consistency.assess",
        "knowledge.status.assert",
    ]


def test_nothing_is_counted_as_both_owned_and_fetched():
    for goal in (
        "evidence.claim.exact_quoted_bound",
        "knowledge.status.verified",
        "decision.synthesis.verified",
        "pdf.extract.text",
    ):
        out = FI.solve(goal, WORLD, G)
        assert not set(out["owned_capability"]) & set(out["jit_knowledge"]), goal


def test_jit_path_only_answers_for_knowledge_tokens():
    assert FI.jit_path_for("pdf.file.available", WORLD, G) is None
    assert FI.jit_path_for("knowledge.status.verified", WORLD, G) is not None


# --------------------------------------------------------------------------- #
# fail closed
# --------------------------------------------------------------------------- #
def test_unreachable_goal_reports_gaps_as_data_not_an_exception():
    out = FI.solve("no.such.goal.anywhere", WORLD, G)
    assert out["owned_capability"] == []
    assert out["jit_knowledge"] == []
    assert isinstance(out["unresolved_gaps"], list)


def test_substrate_reports_a_reason_when_it_is_absent(monkeypatch):
    monkeypatch.setattr(FI, "SUBSTRATE_MODULE", "definitely_not_a_real_module")
    s = FI.substrate()
    assert s["available"] is False
    assert "reason" in s
    assert s["module"] == "definitely_not_a_real_module"


# --------------------------------------------------------------------------- #
# gap report
# --------------------------------------------------------------------------- #
def test_gap_report_is_internally_consistent():
    r = FI.gap_report([], WORLD)
    assert r["schema"] == FI.SCHEMA
    c = r["counts"]
    assert c["owned"] > 0
    assert c["borrowed"] > 0
    assert c["owned"] == len(r["owned_goals"])
    assert c["borrowed"] == len(r["borrowed_goals"])
    assert c["blocked"] == len(r["blocked"])
    assert not set(r["owned_goals"]) & set(r["borrowed_goals"])
    assert r["substrate"]["available"] is True


def test_knowledge_goals_are_borrowed_not_blocked():
    """Reachable through the JIT path is still reachable -- just not owned."""
    r = FI.gap_report([], WORLD)
    assert "knowledge.status.verified" in r["borrowed_goals"]
    assert "knowledge.status.verified" not in r["blocked"]


def test_owned_goals_never_depend_on_external_knowledge():
    r = FI.gap_report([], WORLD)
    for goal in r["owned_goals"]:
        out = FI.solve(goal, WORLD, G)
        assert out["jit_knowledge"] == [], goal
