from canonical.runtime.arc_novelty_compiler_v1 import compile_hypotheses, describe_scene, predict


def _kinds(result):
    return {(h["kind"], h.get("operator"), h.get("selector")) for h in result["hypotheses"]}


def test_rotation_hypothesis_from_raw_grids():
    result = compile_hypotheses([
        {"input": [[1, 0], [1, 1]], "output": [[1, 1], [1, 0]]},
        {"input": [[2, 2, 0], [0, 2, 0]], "output": [[0, 2], [2, 2], [0, 0]]},
    ])
    assert result["status"] == "HYPOTHESES"
    assert ("GLOBAL_GEOMETRY", "ROTATE_90", None) in _kinds(result)
    hyp = next(h for h in result["hypotheses"] if h.get("operator") == "ROTATE_90")
    assert predict(hyp, [[3, 0], [3, 3]])["prediction"] == [[3, 3], [3, 0]]


def test_recolor_hypothesis_is_inferred_positionwise():
    result = compile_hypotheses([
        {"input": [[1, 0], [0, 1]], "output": [[2, 0], [0, 2]]},
        {"input": [[1, 1, 0]], "output": [[2, 2, 0]]},
    ])
    recolor = [h for h in result["hypotheses"] if h["kind"] == "RECOLOR"]
    assert len(recolor) == 1
    assert recolor[0]["mapping"] == {"0": 0, "1": 2}
    assert predict(recolor[0], [[1, 0, 1]])["prediction"] == [[2, 0, 2]]


def test_non_background_crop_from_raw_grid():
    result = compile_hypotheses([
        {
            "input": [[0, 0, 0, 0], [0, 4, 4, 0], [0, 4, 0, 0], [0, 0, 0, 0]],
            "output": [[4, 4], [4, 0]],
        }
    ])
    assert any(h["kind"] == "CROP_NON_BACKGROUND" for h in result["hypotheses"])


def test_scene_extraction_creates_connected_components():
    scene = describe_scene([[0, 1, 0, 2], [0, 1, 0, 2], [0, 0, 0, 2]])
    assert scene["background"] == 0
    assert len(scene["components"]) == 2
    assert sorted(c["area"] for c in scene["components"]) == [2, 3]


def test_ambiguity_is_preserved_not_ranked_away():
    result = compile_hypotheses([{"input": [[1]], "output": [[1]]}])
    assert result["hypothesis_count"] > 1
    assert result["ranking_performed"] is False
    assert result["open_world_complete"] is False


def test_no_matching_grammar_is_truthfully_reported():
    result = compile_hypotheses([
        {"input": [[1, 0], [0, 0]], "output": [[1, 1], [1, 1], [1, 1]]}
    ])
    assert result["status"] == "NO_HYPOTHESIS_IN_DECLARED_GRAMMAR"
    assert result["hypotheses"] == []


def test_malformed_grid_fails_closed():
    result = compile_hypotheses([
        {"input": [[1, 0], [1]], "output": [[1]]}
    ])
    assert result["status"] == "FAIL_CLOSED"
