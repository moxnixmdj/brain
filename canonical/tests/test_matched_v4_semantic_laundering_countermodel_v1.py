from canonical.runtime.matched_v4_semantic_laundering_countermodel_v1 import evaluate

def test_v4_accepts_ungrounded_semantic_tokens():
    out=evaluate()
    assert out["countermodel_confirmed"] is True,out
    assert out["semantic_grounding_present"] is False
    assert out["atom_meaning_executable_checker_present"] is False
    assert out["implication_soundness_proved"] is False
