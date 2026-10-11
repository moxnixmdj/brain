from pathlib import Path
from canonical.runtime.canonical_tree_attestation_v1 import mint_receipt,verify_independent_pair

def test_pair(tmp_path:Path):
    (tmp_path/'a.txt').write_text('x')
    a=mint_receipt(tmp_path,commit_sha='abcdef1',verifier_id='v1',current_main_observed=True)
    b=mint_receipt(tmp_path,commit_sha='abcdef1',verifier_id='v2',current_main_observed=True)
    assert verify_independent_pair(tmp_path,a,b,observed_commit_sha='abcdef1')['pass']

def test_pair_rejects_same_verifier(tmp_path:Path):
    (tmp_path/'a').write_text('1')
    a=mint_receipt(tmp_path,commit_sha='abcdef1',verifier_id='v',current_main_observed=True)
    b=mint_receipt(tmp_path,commit_sha='abcdef1',verifier_id='v',current_main_observed=True)
    assert not verify_independent_pair(tmp_path,a,b,observed_commit_sha='abcdef1')['pass']
