from canonical.runtime.arc_zero_learned_solver_v2 import solve_with_trace


def run(train, test_input):
    out = solve_with_trace(train, test_input)
    assert out["persistent_learned_state_bytes"] == 0
    return out


def test_pairwise_color_key():
    train = [{
        "input": [[1,2,0,0],[3,4,1,3],[0,0,2,4]],
        "output": [[1,2,0,0],[3,4,2,4],[0,0,1,3]],
    }]
    out = run(train, [[5,6,0],[7,8,5],[6,7,8]])
    assert out["strategy"].startswith("TOPLEFT_2X2")
    assert out["prediction"] == [[5,6,0],[7,8,6],[5,8,7]]


def test_cell_to_block_motif_substitution():
    train = [{
        "input": [[0,5],[5,0]],
        "output": [
            [0,0,1,2],[0,0,2,1],
            [1,2,0,0],[2,1,0,0],
        ],
    }]
    out = run(train, [[5,5]])
    assert out["strategy"] == "CELL_TO_BLOCK_MOTIF_SUBSTITUTION"
    assert out["prediction"] == [[1,2,1,2],[2,1,2,1]]


def test_macrogrid_extraction():
    train = [{
        "input": [
            [8,8,8,8,8,8],
            [8,2,2,8,3,3],
            [8,2,2,8,3,3],
            [8,8,8,8,8,8],
            [8,4,4,8,8,8],
            [8,4,4,8,8,8],
        ],
        "output": [[2,3],[4,0]],
    }]
    out = run(train, [
        [8,8,8,8,8,8],
        [8,5,5,8,6,6],
        [8,5,5,8,6,6],
        [8,8,8,8,8,8],
        [8,7,7,8,9,9],
        [8,7,7,8,9,9],
    ])
    assert out["strategy"] == "UNIFORM_OBJECT_MACROGRID_EXTRACTION"
    assert out["prediction"] == [[5,6],[7,9]]


def test_marker_line_propagates_and_recolors_touched_object():
    train = [{
        "input": [
            [0,0,1,0,0],
            [0,2,2,0,0],
            [1,2,2,0,1],
            [0,0,0,0,0],
            [0,0,1,0,0],
        ],
        "output": [
            [0,0,1,0,0],
            [0,1,1,0,0],
            [1,1,1,1,1],
            [0,0,1,0,0],
            [0,0,1,0,0],
        ],
    }]
    out = run(train, [
        [0,0,1,0,0],
        [0,3,3,0,0],
        [1,3,3,0,1],
        [0,0,0,0,0],
        [0,0,1,0,0],
    ])
    assert out["strategy"] == "MARKER_LINE_PROPAGATION_COLOR_1"
    assert out["prediction"][1][1:3] == [1,1]


def test_periodic_repair():
    train = [{
        "input": [
            [1,2,1,2],
            [3,4,3,4],
            [1,0,1,2],
            [3,4,0,4],
        ],
        "output": [
            [1,2,1,2],
            [3,4,3,4],
            [1,2,1,2],
            [3,4,3,4],
        ],
    }]
    out = run(train, [
        [5,6,5,0],
        [7,8,7,8],
        [5,6,5,6],
        [7,0,7,8],
    ])
    assert out["strategy"] == "PERIODIC_REPAIR"
    assert out["prediction"] == [
        [5,6,5,6],
        [7,8,7,8],
        [5,6,5,6],
        [7,8,7,8],
    ]
