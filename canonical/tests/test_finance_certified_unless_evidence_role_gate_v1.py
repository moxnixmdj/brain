import hashlib

from canonical.runtime.certified_scope_fragment_v1 import parse_scope
from canonical.runtime.finance_certified_unless_evidence_role_gate_v1 import (
    derive_roles,
    validate_supervisory_proposal_roles,
)


TEXT = "Apply Rule A unless Exception B applies."


def span_binding(eid, start, end):
    return {
        "evidence_id": eid,
        "start": start,
        "end": end,
        "text_sha256": hashlib.sha256(TEXT[start:end].encode()).hexdigest(),
    }


def bindings():
    p = parse_scope(TEXT, source="s")["parse"]
    return [
        span_binding("rule", *p["left_span"]),
        span_binding("exception", *p["right_span"]),
    ]


def test_roles_derive_from_source_spans():
    out = derive_roles(TEXT, source_id="s", evidence_bindings=bindings())
    assert out["pass"] is True, out
    assert out["derived_roles"]["rule"] == "ORDINARY_BRANCH_EVIDENCE"
    assert out["derived_roles"]["exception"] == "EXCEPTION_BRANCH_EVIDENCE"


def test_swapped_caller_labels_fail_closed():
    roles = derive_roles(TEXT, source_id="s", evidence_bindings=bindings())
    out = validate_supervisory_proposal_roles(
        {
            "rule_evidence_ids": ["exception"],
            "exception_evidence_ids": ["rule"],
        },
        roles,
    )
    assert out["pass"] is False
    assert any(x.startswith("RULE_EVIDENCE_NOT_DERIVED") for x in out["errors"])
    assert any(x.startswith("EXCEPTION_EVIDENCE_NOT_DERIVED") for x in out["errors"])


def test_correct_caller_labels_pass():
    roles = derive_roles(TEXT, source_id="s", evidence_bindings=bindings())
    out = validate_supervisory_proposal_roles(
        {
            "rule_evidence_ids": ["rule"],
            "exception_evidence_ids": ["exception"],
        },
        roles,
    )
    assert out["pass"] is True, out


def test_span_crossing_operator_fails_closed():
    p = parse_scope(TEXT, source="s")["parse"]
    start = p["left_span"][1] - 2
    end = p["right_span"][0] + 2
    out = derive_roles(
        TEXT,
        source_id="s",
        evidence_bindings=[span_binding("cross", start, end)],
    )
    assert out["pass"] is False
    assert any("NOT_CONTAINED_IN_ONE_CERTIFIED_BRANCH" in x for x in out["errors"])


def test_wrong_hash_fails_closed():
    p = parse_scope(TEXT, source="s")["parse"]
    row = span_binding("rule", *p["left_span"])
    row["text_sha256"] = "0" * 64
    out = derive_roles(TEXT, source_id="s", evidence_bindings=[row])
    assert out["pass"] is False
    assert any("HASH_MISMATCH" in x for x in out["errors"])


def test_non_unless_source_not_admitted():
    out = derive_roles(
        "Apply Rule A if condition C.",
        source_id="s",
        evidence_bindings=[],
    )
    assert out["pass"] is False
    assert "SOURCE_NOT_IN_CERTIFIED_SINGLE_UNLESS_FRAGMENT" in out["errors"]


def _complete_bundle_and_proposal():
    import copy
    from canonical.runtime.source_contract_compiler import atomize_source, semantic_unit_id
    from canonical.runtime.finance_source_coverage_certificate_v1 import build_manifest
    from canonical.runtime.semantic_operator_counterfactuals import (
        extract_semantic_operators,
        generate_counterfactual_obligations,
    )

    text = TEXT
    source = "s"
    atoms = atomize_source(text, source)
    assert len(atoms) == 1
    atom = atoms[0]
    sid = semantic_unit_id(atom.atom_id, 0, len(atom.text))

    unit = {
        "atom_id": atom.atom_id,
        "start": 0,
        "end": len(atom.text),
        "text_sha256": hashlib.sha256(atom.text.encode()).hexdigest(),
        "kind": "BEHAVIOR",
        "semantic_fingerprint": "certified-unless-supervisory-v1",
        "rationale": "single controlled supervisory rule with explicit exception branch",
    }
    requirement = {
        "id": "R1",
        "source_atom_ids": [atom.atom_id],
        "source_semantic_unit_ids": [sid],
        "evidence_ids": ["rule", "exception"],
    }
    disposition = {
        "atom_id": atom.atom_id,
        "kind": "BEHAVIOR",
        "rationale": "operative supervisory source",
        "requirement_ids": ["R1"],
    }

    ops = extract_semantic_operators(text, source=source)
    operator_bindings = []
    for op in ops:
        row = {"operator_id": op.operator_id, "semantic_class": op.semantic_class}
        if op.bound_value is not None:
            row["bound_value"] = op.bound_value
        if op.semantic_class == "AMBIGUOUS_ANY":
            row["interpretations"] = ["existential", "universal"]
        operator_bindings.append(row)
    scenarios = []
    for obligation in generate_counterfactual_obligations(text, source=source):
        disposition_value = (
            "DISAMBIGUATE"
            if obligation.counterfactual_kind == "ANY_SEMANTICS_MUST_BE_DISAMBIGUATED"
            else ("ACCEPT" if "ACCEPT" in obligation.counterfactual_kind else "REJECT")
        )
        scenarios.append({
            "operator_id": obligation.operator_id,
            "counterfactual_kind": obligation.counterfactual_kind,
            "expected_disposition": disposition_value,
        })

    decision_problem = {
        "schema": "PROJECT_BRAIN_TYPED_DECISION_PROBLEM_V1",
        "decision_id": "supervisory-unless-role-binding",
        "question": "Which terminal alternative is supported?",
        "alternatives": [{"id": "APPLY_RULE", "label": "APPLY_RULE"}],
        "constraints": [],
        "evidence": [
            {
                "id": eid,
                "alternative": "APPLY_RULE",
                "relation": "SUPPORTS",
                "confidence": 1.0,
                "strength": 1.0,
                "independence_group": "group-" + eid,
                "claim": "synthetic " + eid,
                "provenance": [{"source": source, "ref": eid}],
            }
            for eid in ["rule", "exception"]
        ],
        "policy": {
            "minimum_support_ratio": 1.0,
            "maximum_conflict_ratio": 0.0,
            "minimum_independent_support_groups": 2,
            "minimum_net_margin": 0.0,
        },
    }

    p = parse_scope(text, source=source)["parse"]
    role_bindings = [
        span_binding("rule", *p["left_span"]),
        span_binding("exception", *p["right_span"]),
    ]

    bundle = {
        "source_id": source,
        "source_text": text,
        "source_coverage_manifest": build_manifest(
            text,
            [["rule", "exception"]],
            source_id=source,
        ),
        "source_semantic_coverage": {
            "dispositions": [disposition],
            "requirements": [requirement],
            "extractor_units": {
                "extractor-a": [copy.deepcopy(unit)],
                "extractor-b": [copy.deepcopy(unit)],
            },
        },
        "finance_evidence_role_bindings": role_bindings,
        "operator_bindings": operator_bindings,
        "counterfactual_scenarios": scenarios,
        "semantic_contract": {
            "entities": [{"id": "subject", "type": "case", "source": {"span": [0, len(text)]}}],
            "facts": [{
                "subject": "subject",
                "predicate": "supported_terminal_alternative",
                "object": "APPLY_RULE",
                "source": {"span": [0, len(text)]},
            }],
            "relations": [],
            "templates": [],
            "ambiguities": [],
        },
        "interpretations": [{
            "id": "i1",
            "meaning": "APPLY_RULE",
            "consistent_with_source": True,
            "consistent_with_authorized_context": True,
            "materially_distinct": True,
            "discriminator": "",
        }],
        "authorized_context_ids": [source],
        "decision_problem": decision_problem,
    }
    proposal = {
        "decision": "CONCLUDE",
        "leaf_id": "SUPERVISORY_AND_COMPLIANCE_NUANCE_OUTSIDE_PUBLIC_BAR_SCOPE",
        "selected_alternative": "APPLY_RULE",
        "rule_evidence_ids": ["rule"],
        "exception_evidence_ids": ["exception"],
        "reconciliation_checks": [],
    }
    return bundle, proposal


def test_full_supervisory_transaction_passes_with_certified_roles():
    from canonical.runtime.finance_certified_unless_evidence_role_gate_v1 import (
        configured_finance_supervisory_terminal_decision_v2,
    )
    bundle, proposal = _complete_bundle_and_proposal()
    out = configured_finance_supervisory_terminal_decision_v2(proposal, bundle)
    assert out["accepted"] is True, out
    assert out["proposal_role_validation"]["pass"] is True


def test_same_transaction_fails_when_rule_and_exception_labels_are_swapped():
    from canonical.runtime.finance_certified_unless_evidence_role_gate_v1 import (
        configured_finance_supervisory_terminal_decision_v2,
    )
    bundle, proposal = _complete_bundle_and_proposal()
    proposal = dict(proposal)
    proposal["rule_evidence_ids"] = ["exception"]
    proposal["exception_evidence_ids"] = ["rule"]
    out = configured_finance_supervisory_terminal_decision_v2(proposal, bundle)
    assert out["accepted"] is False
    assert "FINANCE_CERTIFIED_EVIDENCE_ROLE_GATE_FAIL_CLOSED" in out["errors"]
