from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFESSIONAL = ROOT / "canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
ASSURANCE = ROOT / "canonical/governance/CURRENT_ASSURANCE_CLOSURE_COMPILER.json"

ROOT_NAMES = {
    1: "TARGET_SPECIFICATION",
    2: "CANDIDATE_SEARCH",
    3: "REALIZATION_OBSERVATION",
    4: "MEASUREMENT_CONSTRUCT",
    5: "EVALUATOR_REFERENCE",
    6: "EVIDENCE_GROUNDING_DEPENDENCE",
    7: "CAUSAL_PRESCRIPTIVE",
    8: "POPULATION_CONTEXT_OPERATOR",
    9: "TEMPORAL_DEPLOYMENT",
    10: "ANALYSIS_DECISION",
    11: "ADAPTIVE_INTEGRITY_SECURITY",
    12: "META_COMPOSITION_CLOSURE",
}


def blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(b"blob " + str(len(raw)).encode("ascii") + bytes([0]) + raw).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_assurance_same_subject_frontier_exactly_mirrors_professional_pointer():
    professional = load(PROFESSIONAL)
    assurance = load(ASSURANCE)
    prof_frontier = professional["same_subject_root_binding_frontier"]
    mirror = assurance["professional_quality_same_subject_frontier"]

    verified = prof_frontier["verified_root_subject_binding_count"]
    root_count = prof_frontier["root_count"]

    assert mirror["current_professional_execution_path"] == "canonical/governance/CURRENT_PROFESSIONAL_QUALITY_EXECUTION.json"
    assert mirror["current_professional_execution_git_blob_sha"] == blob_sha(PROFESSIONAL)

    worklist = mirror["root_binding_worklist"]
    assert worklist["path"] == prof_frontier["path"]
    assert worklist["git_blob_sha"] == prof_frontier["git_blob_sha"]
    assert worklist["required_root_count"] == root_count
    assert worklist["verified_root_subject_binding_count"] == verified
    assert worklist["composition_admissible"] is prof_frontier["composition_admissible"]

    assert mirror["verified_root_subject_binding_count"] == verified
    assert mirror["root_count"] == root_count
    assert mirror["composition_admissible"] is prof_frontier["composition_admissible"]
    assert mirror["v7_profile_step_provenance"]["proof_bound_remaining_step_count"] == root_count - verified

    expected = {f"R{i}_{ROOT_NAMES[i]}" for i in range(1, verified + 1)}
    assert set(mirror["current_verified_root_bindings"]) == expected
    for i in range(1, verified + 1):
        key = f"R{i}_{ROOT_NAMES[i]}"
        actual = mirror["current_verified_root_bindings"][key]
        source = professional[f"r{i}_root_subject_binding"]
        for field in (
            "binding_path",
            "binding_git_blob_sha",
            "verification_path",
            "verification_git_blob_sha",
        ):
            assert actual[field] == source[field]

    next_index = verified + 1
    expected_next = "COMPLETE" if next_index > root_count else f"R{next_index}_{ROOT_NAMES[next_index]}"
    assert mirror["next"] == expected_next


def test_assurance_mirror_cannot_grant_promotion_or_quality_credit():
    assurance = load(ASSURANCE)
    mirror = assurance["professional_quality_same_subject_frontier"]

    assert assurance["live_default"] is False
    assert assurance["terminal_authority"] is False
    assert mirror["composition_admissible"] is False
    assert assurance["assurance_professional_frontier_coherence"]["terminal_credit_delta"] == 0
