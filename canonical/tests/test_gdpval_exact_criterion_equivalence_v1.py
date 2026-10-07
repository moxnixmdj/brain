from canonical.runtime.gdpval_exact_criterion_equivalence_v1 import compile_classes

REV="11e7900"

def rows():
    return [
        {"task_id":"t1","rubric":[
            {"rubric_item_id":"a","criterion":"Overall formatting and style of the deliverable","score":5},
            {"rubric_item_id":"b","criterion":"Must be a PDF","score":2},
        ]},
        {"task_id":"t2","rubric":[
            {"rubric_item_id":"c","criterion":"Overall formatting and style of the deliverable","score":5},
            {"rubric_item_id":"d","criterion":"Must be a PDF.","score":2},
        ]},
        {"task_id":"t3","rubric":[
            {"rubric_item_id":"e","criterion":"Overall formatting and style of the deliverable","score":3},
        ]},
    ]

def test_exact_identity_only_compresses_identical_text():
    out=compile_classes(rows(),source_revision=REV)
    assert out["pass"] is True
    assert out["criterion_occurrence_count"]==5
    assert out["exact_text_class_count"]==3
    assert out["repeated_class_count"]==1
    assert out["exact_text_compression_savings"]==2

def test_punctuation_difference_does_not_merge():
    out=compile_classes(rows(),source_revision=REV)
    texts={x["criterion"]:x["occurrence_count"] for x in out["classes"]}
    assert texts["Must be a PDF"]==1
    assert texts["Must be a PDF."]==1

def test_same_text_different_scores_preserves_context_difference():
    out=compile_classes(rows(),source_revision=REV)
    cls=next(x for x in out["classes"] if x["criterion"]=="Overall formatting and style of the deliverable")
    assert cls["occurrence_count"]==3
    assert cls["task_count"]==3
    assert cls["score_values"]==["3","5"]
    assert cls["score_context_invariant"] is False
    assert out["context_specific_threshold_equivalence_claimed"] is False

def test_duplicate_rubric_item_id_fails_closed():
    x=rows()
    x[1]["rubric"][0]["rubric_item_id"]="a"
    out=compile_classes(x,source_revision=REV)
    assert out["pass"] is False
    assert out["reason"]=="RUBRIC_ITEM_ID_DUPLICATE"

def test_missing_criterion_fails_closed():
    x=rows()
    x[0]["rubric"][0]["criterion"]=" "
    out=compile_classes(x,source_revision=REV)
    assert out["pass"] is False
    assert out["reason"]=="CRITERION_REQUIRED"

def test_no_semantic_or_terminal_authority():
    out=compile_classes(rows(),source_revision=REV)
    assert out["semantic_equivalence_claimed"] is False
    assert out["task_closure_authority"] is False
    assert out["u_deletion_authority"] is False
    assert out["terminal_authority"] is False
