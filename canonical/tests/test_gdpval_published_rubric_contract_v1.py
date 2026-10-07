import json

from canonical.runtime.gdpval_published_rubric_contract_v1 import compile_published_rubric


def _row(item_id="r1", **extra):
    row = {
        "score": 2,
        "criterion": "The workbook contains a worksheet named exactly 'Sample'.",
        "required": None,
        "rubric_item_id": item_id,
        "author_type": "human",
        "tags": ["true"],
        "read_only": None,
        "form_content": None,
    }
    row.update(extra)
    return row


def test_valid_rubric_is_losslessly_bound_and_content_addressed():
    rows = [
        _row("r1", future_metadata={"source": "publisher"}),
        _row(
            "r2",
            score=5,
            criterion="Overall formatting and style of the deliverable",
            tags=["true", "quality"],
        ),
    ]
    out = compile_published_rubric(
        json.dumps(rows),
        task_id="task-001",
        prompt_sha256="a" * 64,
    )
    assert out["pass"] is True
    assert out["criterion_count"] == 2
    assert out["total_published_weight"] == 7
    assert out["requirements"][0]["published_row"]["future_metadata"] == {"source": "publisher"}
    assert out["unknown_published_row_metadata_dropped"] is False
    assert len(out["contract_sha256"]) == 64
    assert out["prompt_to_rubric_semantic_completeness_proved"] is False
    assert out["rubric_equals_full_human_pairwise_preference_law_proved"] is False
    assert out["terminal_authority"] is False


def test_duplicate_rubric_item_id_fails_closed():
    raw = json.dumps([_row("same"), _row("same")])
    out = compile_published_rubric(raw, task_id="task-001")
    assert out["pass"] is False
    assert out["errors"] == ["RUBRIC_ITEM_ID_DUPLICATE:same"]


def test_duplicate_json_key_fails_closed():
    raw = (
        '[{"score":2,"score":3,"criterion":"x","required":null,'
        '"rubric_item_id":"r1","author_type":"human","tags":[]}]'
    )
    out = compile_published_rubric(raw, task_id="task-001")
    assert out["pass"] is False
    assert out["errors"] == ["DUPLICATE_JSON_KEY:score"]


def test_empty_or_nonlist_rubric_fails_closed():
    assert compile_published_rubric("[]", task_id="task-001")["pass"] is False
    assert compile_published_rubric("{}", task_id="task-001")["pass"] is False


def test_bad_prompt_sha_fails_closed():
    out = compile_published_rubric(
        json.dumps([_row("r1")]),
        task_id="task-001",
        prompt_sha256="not-a-sha",
    )
    assert out["pass"] is False
    assert out["errors"] == ["PROMPT_SHA256_INVALID"]
