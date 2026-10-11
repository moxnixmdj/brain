from pathlib import Path
from canonical.runtime.canonical_candidate_test_receipt_v1 import run

def test_candidate_suite_receipt(tmp_path:Path):
    (tmp_path/'canonical/tests').mkdir(parents=True)
    (tmp_path/'canonical/tests/test_one.py').write_text('def test_one():\n    assert 1+1==2\n')
    r=run(tmp_path,verifier_id='independent-test',timeout_seconds=60)
    assert r['pass']
    assert r['test_count']==1
