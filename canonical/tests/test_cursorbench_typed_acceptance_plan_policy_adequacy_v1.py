import hashlib
import json
from pathlib import Path

from canonical.runtime.independent_acceptance_model import (
    COUNTEREXAMPLE_TEMPLATES,
    NONINDEPENDENT_PROVENANCE,
    OBLIGATIONS,
    assess,
)

ROOT = Path(__file__).resolve().parents[2]
CERT = ROOT / "canonical/governance/CURSORBENCH_TYPED_ACCEPTANCE_PLAN_POLICY_ADEQUACY_CERTIFICATE_20261009_V1.json"

def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode("ascii") + b"\0" + data)
    return h.hexdigest()

def load_bound(ref):
    p = ROOT / ref["path"]
    assert p.is_file()
    assert git_blob_sha(p) == ref["git_blob_sha"]
    return json.loads(p.read_text(encoding="utf-8"))

def test_exact_sources_and_target_relevance_are_bound():
    cert = json.loads(CERT.read_text(encoding="utf-8"))
    assert cert["behavior_id"] == "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001"
    assert cert["target_predicate"] == "CODING_CURSORBENCH_GE_57_8"
    assert git_blob_sha(ROOT / cert["exact_policy"]["path"]) == cert["exact_policy"]["git_blob_sha"]

    candidate = load_bound(cert["exact_sources"]["candidate"])
    evidence = load_bound(cert["exact_sources"]["heldout_evidence"])
    measurement = load_bound(cert["exact_sources"]["measurement_semantics_extension"])
    registry = load_bound(cert["exact_sources"]["behavior_registry"])
    reduction = load_bound(cert["exact_sources"]["cursorbench_residual_basis"])

    assert candidate["behavior_id"] == cert["behavior_id"]
    assert "WHOLE_SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001" in evidence["not_owned"]
    assert measurement["behavior_id"] == cert["behavior_id"]
    row = next(x for x in registry["active_contracted_residuals"] if x["behavior_id"] == cert["behavior_id"])
    assert row["required_output_or_action"].startswith("derive acceptance consequences independently")
    assert cert["behavior_id"] in reduction["reduction"]["surviving_residual_ids"]
    assert cert["target_relevance"]["current_hidden_cursorbench_task_membership_proved"] is False
    assert cert["adequacy_theorem"]["whole_cursorbench_adequacy"] is False
    assert cert["accounting"]["acceptance_credit_delta"] == 0
    assert cert["accounting"]["terminal_credit_delta"] == 0

def _model(kind, detects, *, provenance="independent_oracle", builder_dep="builder:semantic-A", checker_dep="oracle:semantic-B", derived=False):
    return {
        "requirements": [{
            "id": "R",
            "critical": True,
            "transform_kinds": [kind],
            "builder_dependencies": ["raw:source", builder_dep],
        }],
        "checks": [{
            "id": "C",
            "covers": ["R"],
            "provenance": provenance,
            "dependencies": ["raw:source", checker_dep],
            "detects": list(detects),
            "derived_from_builder_output": derived,
        }],
    }

def test_every_supported_transform_kind_has_nonempty_complete_positive_mechanics():
    assert OBLIGATIONS
    for kind, modes in OBLIGATIONS.items():
        assert modes, kind
        assert all(mode in COUNTEREXAMPLE_TEMPLATES for mode in modes), kind
        out = assess(_model(kind, modes))
        assert out["pass"] is True, (kind, out)
        row = out["requirements"][0]
        assert set(row["obligations"]) == set(modes)
        assert set(row["independently_covered"]) == set(modes)
        assert row["uncovered"] == ()

def test_every_single_obligation_omission_fails_closed_and_emits_counterexample():
    exercised = 0
    for kind, modes in OBLIGATIONS.items():
        for omitted in modes:
            detects = [x for x in modes if x != omitted]
            out = assess(_model(kind, detects))
            assert out["pass"] is False, (kind, omitted, out)
            row = out["requirements"][0]
            assert omitted in row["uncovered"]
            emitted = {x["failure_mode"] for x in row["counterexample_templates"]}
            assert omitted in emitted
            exercised += 1
    assert exercised >= 40

def test_builder_correlated_checks_cannot_satisfy_region_policy():
    modes = next(iter(OBLIGATIONS.values()))
    for provenance in sorted(NONINDEPENDENT_PROVENANCE):
        out = assess(_model(next(iter(OBLIGATIONS)), modes, provenance=provenance))
        assert out["pass"] is False, provenance

    kind = next(iter(OBLIGATIONS))
    modes = OBLIGATIONS[kind]
    shared = assess(_model(kind, modes, builder_dep="shared:semantic", checker_dep="shared:semantic"))
    assert shared["pass"] is False

    derived = assess(_model(kind, modes, derived=True))
    assert derived["pass"] is False

def test_shared_raw_inputs_remain_allowed_but_nonraw_independence_is_load_bearing():
    kind = next(iter(OBLIGATIONS))
    modes = OBLIGATIONS[kind]
    out = assess({
        "requirements": [{
            "id": "R",
            "critical": True,
            "transform_kinds": [kind],
            "builder_dependencies": ["raw:source"],
        }],
        "checks": [{
            "id": "C",
            "covers": ["R"],
            "provenance": "independent_oracle",
            "dependencies": ["raw:source"],
            "detects": list(modes),
        }],
    })
    assert out["pass"] is True

def test_region_condition_excludes_unknown_transform_semantics_from_adequacy_claim():
    cert = json.loads(CERT.read_text(encoding="utf-8"))
    reqs = cert["policy_condition"]["requirements"]
    assert "EVERY_TRANSFORM_KIND_IS_ONE_OF_THE_EXACT_RUNTIME_SUPPORTED_KINDS" in reqs
    assert "GENERATED_OBLIGATIONS_ARE_COMPLETE_FOR_EVERY_MATERIAL_INDEPENDENTLY_KNOWABLE_FAILURE_MODE_IN_THE_BOUND_REGION" in reqs
    assert cert["membership_self_certified"] is False
    assert cert["adequacy_self_certified"] is False
