from canonical.runtime.h100_chartreader_detector_budget_v1 import FIRST,FULL,GROUP,RESULT,BUDGET

def test_exact_static_counts():
    assert FIRST.matrix+FIRST.vector==97_206_410
    assert FIRST.matrix==97_145_728
    assert FIRST.vector==60_682
    assert FIRST.buffers==239_248
    assert FIRST.convs==90
    assert FIRST.qchannels==30_858
    assert FULL.matrix+FULL.vector==194_787_476
    assert FULL.matrix==194_665_856
    assert FULL.vector==121_620
    assert FULL.buffers==479_520
    assert FULL.convs==180
    assert FULL.qchannels==61_844
    assert GROUP.matrix+GROUP.vector==199_641_774
    assert GROUP.matrix==199_499_904
    assert GROUP.vector==141_870
    assert GROUP.qchannels==75_854

def test_h100_storage_race():
    assert RESULT["first_q4_bytes"]==49_301_704\n    assert RESULT["first_int8_bytes"]==97_874_568
    assert RESULT["full_q4_bytes"]==98_793_680
    assert RESULT["group_q4_bytes"]==101_403_784
    assert RESULT["first_q4_bytes"]<BUDGET\n    assert RESULT["first_int8_bytes"]<BUDGET
    assert RESULT["full_q4_bytes"]<BUDGET
    assert RESULT["group_q4_bytes"]>BUDGET
