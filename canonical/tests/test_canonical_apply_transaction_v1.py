import json,hashlib,shutil
from pathlib import Path
from canonical.runtime.canonical_tree_attestation_v1 import mint_receipt,tree_manifest
from canonical.runtime.canonical_apply_transaction_v1 import stage_candidate,verify_staged_candidate

def _sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def _make_patch(root:Path):
    (root/'canonical/governance').mkdir(parents=True); (root/'canonical/runtime').mkdir(parents=True)
    (root/'canonical/runtime/new.py').write_text('X=2\n')
    # empty valid vendor archives
    import zipfile
    (root/'evidence/source_artifacts').mkdir(parents=True)
    sources={}
    for sid,name,prefix in [
      ('PROFESSIONAL_SEMANTIC_TOTALITY_ZIP','s.zip','brain_semantic_totality_patch/canonical/'),
      ('R12_C1_ZIP','r.zip','canonical/'),('PROFESSIONAL_CURRENTNESS_ZIP','c.zip','brain_professional_6of24_reconcile/canonical/')]:
      z=root/'evidence/source_artifacts'/name
      with zipfile.ZipFile(z,'w') as a: a.writestr(prefix+'runtime/vendor_'+sid+'.py','Y=1\n')
      sources[sid]={'available_exact_bytes':True,'path':str(z.relative_to(root)),'sha256':_sha(z)}
    # lock module itself plus target module and archives
    for sid,rel in [('A','canonical/runtime/new.py')]:
      p=root/rel; sources[sid]={'available_exact_bytes':True,'path':rel,'sha256':_sha(p)}
    (root/'canonical/governance/CURRENT_FRONTIER_REUSE_SOURCE_LOCK_20261011_V2.json').write_text(json.dumps({'sources':sources}))

def test_stage_and_verify(tmp_path:Path):
    base=tmp_path/'base'; patch=tmp_path/'patch'; dest=tmp_path/'dest'; base.mkdir(); patch.mkdir()
    (base/'canonical/runtime').mkdir(parents=True); (base/'canonical/runtime/old.py').write_text('OLD=1\n')
    _make_patch(patch)
    a=mint_receipt(base,commit_sha='abcdef1',verifier_id='v1',current_main_observed=True)
    b=mint_receipt(base,commit_sha='abcdef1',verifier_id='v2',current_main_observed=True)
    s=stage_candidate(base,patch,observed_commit_sha='abcdef1',base_receipt_a=a,base_receipt_b=b,destination=dest)
    assert s['pass'] and (dest/'canonical/runtime/new.py').exists()
    tr={'pass':True,'candidate_tree_sha256':s['candidate_tree_sha256'],'independently_verified':True,'verifier_id':'testv','test_count':7,'sha256':'0'*64}
    v=verify_staged_candidate(s,test_receipt=tr,independent_verifier_id='testv')
    assert v['pass'] and v['canonical_commit_eligible']

def test_stale_base_rejected(tmp_path:Path):
    base=tmp_path/'base'; patch=tmp_path/'patch'; base.mkdir(); patch.mkdir(); (base/'a').write_text('1'); _make_patch(patch)
    a=mint_receipt(base,commit_sha='abcdef1',verifier_id='v1',current_main_observed=True)
    b=mint_receipt(base,commit_sha='abcdef1',verifier_id='v2',current_main_observed=True)
    (base/'a').write_text('2')
    s=stage_candidate(base,patch,observed_commit_sha='abcdef1',base_receipt_a=a,base_receipt_b=b)
    assert not s['pass']
