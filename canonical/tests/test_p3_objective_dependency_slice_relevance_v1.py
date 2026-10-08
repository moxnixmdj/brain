import hashlib

from canonical.runtime.p3_objective_dependency_slice_relevance_v1 import evaluate


def sha(x):
    if isinstance(x, str):
        x = x.encode("utf-8")
    return hashlib.sha256(x).hexdigest()


def extraction():
    page = sha(b"page")
    texts = [
        "System A latency was 40 ms.",
        "System B latency was 55 ms.",
        "The deployment region was north.",
    ]
    visible = "\n".join(texts)
    visible_sha = sha(visible)
    rows = []
    offset = 0
    for text in texts:
        start = offset
        end = start + len(text)
        text_sha = sha(text)
        uid = sha(f"{page}:{start}:{end}:{text_sha}")
        rows.append(
            {
                "evidence_unit_id": uid,
                "source_url": "https://example.org/data",
                "page_raw_sha256": page,
                "visible_text_sha256": visible_sha,
                "text": text,
                "text_sha256": text_sha,
                "visible_text_start": start,
                "visible_text_end": end,
            }
        )
        offset = end + 1
    return {
        "schema": "PROJECT_BRAIN_OBJECTIVE_EVIDENCE_UNIT_EXTRACTION_V2",
        "status": "OBJECTIVE_GROUNDED_EVIDENCE_UNITS_EXTRACTED",
        "output_verified": True,
        "source_url": "https://example.org/data",
        "page_raw_sha256": page,
        "visible_text_sha256": visible_sha,
        "evidence_units": rows,
    }


def test_numeric_objective_selects_only_relation_operands():
    data = extraction()
    out = evaluate(
        {
            "objective": "whether latency of System A is lower than latency of System B",
            "extraction": data,
        }
    )
    assert out["pass"] is True
    ids = [x["evidence_unit_id"] for x in data["evidence_units"]]
    assert out["selected_evidence_unit_ids"] == ids[:2]
    assert out["irrelevant_to_bounded_relation_evaluator_evidence_unit_ids"] == [ids[2]]
    assert out["relation_result"]["predicate"] is True


def test_unrelated_extra_evidence_does_not_enter_slice():
    data = extraction()
    first = evaluate(
        {
            "objective": "whether latency of System A is lower than latency of System B",
            "extraction": data,
        }
    )
    assert first["pass"] is True
    assert len(first["selected_evidence_unit_ids"]) == 2


def test_overlapping_decoy_causes_fail_closed_ambiguity():
    data = extraction()
    text = "Backup report: System A latency was 41 ms."
    start = len("\n".join(x["text"] for x in data["evidence_units"])) + 1
    end = start + len(text)
    text_sha = sha(text)
    uid = sha(f"{data['page_raw_sha256']}:{start}:{end}:{text_sha}")
    data["evidence_units"].append(
        {
            "evidence_unit_id": uid,
            "source_url": "https://example.org/data",
            "page_raw_sha256": data["page_raw_sha256"],
            "visible_text_sha256": data["visible_text_sha256"],
            "text": text,
            "text_sha256": text_sha,
            "visible_text_start": start,
            "visible_text_end": end,
        }
    )
    out = evaluate(
        {
            "objective": "whether latency of System A is lower than latency of System B",
            "extraction": data,
        }
    )
    assert out["pass"] is False
    assert out["reason"] == "OBJECTIVE_NOT_SOUNDLY_BOUND"


def test_unsupported_paraphrase_fails_closed():
    out = evaluate(
        {
            "objective": "which system seems speedier overall?",
            "extraction": extraction(),
        }
    )
    assert out["pass"] is False
    assert out["reason"] == "OBJECTIVE_NOT_SOUNDLY_BOUND"


def test_hidden_relevance_label_is_forbidden():
    data = extraction()
    data["evidence_units"][0]["relevance"] = "high"
    out = evaluate(
        {
            "objective": "whether latency of System A is lower than latency of System B",
            "extraction": data,
        }
    )
    assert out["reason"] == "UNVERIFIED_RELEVANCE_LABEL_FORBIDDEN"


def test_tampered_hash_fails_closed():
    data = extraction()
    data["evidence_units"][0]["text"] += " altered"
    out = evaluate(
        {
            "objective": "whether latency of System A is lower than latency of System B",
            "extraction": data,
        }
    )
    assert out["pass"] is False
    assert out["reason"] == "OBJECTIVE_BINDING_OR_RELATION_EVALUATION_FAILED"


def test_exact_quoted_support_selects_single_unit():
    data = extraction()
    out = evaluate(
        {
            "objective": 'verify whether the source states "System A latency was 40 ms."',
            "extraction": data,
        }
    )
    assert out["pass"] is True
    assert len(out["selected_evidence_unit_ids"]) == 1
    assert out["binding_mode"] == "VERBATIM_SUPPORT"


def test_no_authority_escalation():
    out = evaluate(
        {
            "objective": "whether latency of System A is lower than latency of System B",
            "extraction": extraction(),
        }
    )
    assert out["pass"] is True
    assert out["policy_adequacy_authority"] is False
    assert out["db_admission_authority"] is False
    assert out["u_subtraction_authority"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0
