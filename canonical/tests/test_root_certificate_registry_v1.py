from pathlib import Path
import json
import tempfile

from canonical.runtime.root_certificate_registry_v1 import validate_repo, REGISTRY

ROOT = Path(__file__).resolve().parents[2]


def test_current_registry_binds_exact_three_unknown_roots():
    out = validate_repo(ROOT)
    assert out["pass"] is True, out
    assert out["root_status_vector"] == ["UNKNOWN", "UNKNOWN", "UNKNOWN"]
    assert out["proof_closure_ready"] is False
    assert out["registry_complete_for_declared_roots"] is True
    assert out["terminal_credit_delta"] == 0


def test_unknown_is_not_silently_promoted_to_proved():
    doc = json.loads((ROOT / REGISTRY).read_text(encoding="utf-8"))
    assert all(doc["roots"][k]["status"] == "UNKNOWN" for k in ("R1", "R2", "R3"))
    assert all(doc["roots"][k]["falsified"] is False for k in ("R1", "R2", "R3"))
    assert all(
        item["not_equivalent_to_root_claim"] is True
        for k in ("R1", "R2", "R3")
        for item in doc["roots"][k].get("supporting_evidence", [])
    )


def test_source_drift_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        dst = Path(td)
        # Copy only files the registry validator reads.
        paths = {
            REGISTRY,
            "canonical/governance/CURRENT_MISSION_OBJECTIVE.json",
            "canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_V1.json",
            "canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_LIVE_BINDING_V1.json",
            "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json",
            "canonical/governance/CURRENT_TERMINAL_AUTHORITY.json",
            "canonical/verification/R1_CURRENT_BYTE_LIFECYCLE_RESEAL_20261009_V1.json",
            "canonical/governance/R3_ZERO_RESIDUAL_TERMINAL_TRUTH_RECONCILIATION_20261009_V1.json",
            "canonical/verification/R3_AUTONOMOUS_VERIFIED_COMPOUNDING_LOOP_IMPLEMENTATION_20261008_V7.json",
        }
        for rel in paths:
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / rel).read_bytes())
        target = dst / "canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"
        target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        out = validate_repo(dst)
    assert out["pass"] is False
    assert any(x.startswith("EVIDENCE_BLOB_DRIFT:R2:") for x in out["errors"])
