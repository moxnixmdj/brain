"""Exact-current-main candidate application transaction.

This stages an overlay in isolation. It never mutates the supplied base tree. A candidate
becomes commit-eligible only when two independent current-base receipts agree, every
preimage matches those receipts, source locks pass, and the staged tree verifies.
"""
from __future__ import annotations
import hashlib, json, shutil, tempfile, zipfile
from pathlib import Path
from typing import Any, Mapping, Iterable
from canonical.runtime.canonical_tree_attestation_v1 import verify_independent_pair, tree_manifest
from canonical.runtime.source_lock_verify_v1 import verify_source_lock

SCHEMA='PROJECT_BRAIN_CANONICAL_APPLY_TRANSACTION_V1'
VENDOR_PREFIXES={
 'PROFESSIONAL_SEMANTIC_TOTALITY_ZIP':'brain_semantic_totality_patch/canonical/',
 'R12_C1_ZIP':'canonical/',
 'PROFESSIONAL_CURRENTNESS_ZIP':'brain_professional_6of24_reconcile/canonical/',
}

def _sha_bytes(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def _sha_obj(o:Any)->str: return _sha_bytes(json.dumps(o,sort_keys=True,separators=(',',':')).encode())
def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {'schema':SCHEMA,'pass':False,'status':'FAIL_CLOSED','reason':reason,'canonical_commit_eligible':False,
            'mutation_authority':False,'promotion_authority':False,'activation_authority':False,'terminal_authority':False,
            'terminal_credit_delta':0,'incremental_spend_usd':0,**extra}

def _receipt_file_map(receipt:Mapping[str,Any])->dict[str,str]:
    out={}
    for x in receipt.get('files') or []:
        if isinstance(x,Mapping) and isinstance(x.get('path'),str) and isinstance(x.get('sha256'),str): out[x['path']]=x['sha256']
    return out

def _collect_patch_files(patch_root:Path)->list[dict[str,Any]]:
    rows=[]
    for p in sorted((patch_root/'canonical').rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith('.pyc'):
            rel=p.relative_to(patch_root).as_posix(); data=p.read_bytes(); rows.append({'path':rel,'bytes':data,'sha256':_sha_bytes(data),'source':'FRONTIER_V3'})
    return rows

def _collect_vendor_files(patch_root:Path, source_lock:Mapping[str,Mapping[str,Any]])->list[dict[str,Any]]:
    rows=[]
    for sid,prefix in VENDOR_PREFIXES.items():
        row=source_lock[sid]; z=patch_root/row['path']
        with zipfile.ZipFile(z) as arc:
            for name in sorted(arc.namelist()):
                if not name.startswith(prefix) or name.endswith('/') or '__pycache__/' in name or name.endswith('.pyc'): continue
                suffix=name[len(prefix):]
                if not suffix: continue
                rel='canonical/'+suffix if not suffix.startswith('canonical/') else suffix
                data=arc.read(name); rows.append({'path':rel,'bytes':data,'sha256':_sha_bytes(data),'source':sid})
    return rows

def stage_candidate(base_root:Path, patch_root:Path, *, observed_commit_sha:str, base_receipt_a:Mapping[str,Any], base_receipt_b:Mapping[str,Any],
                    destination:Path|None=None)->dict[str,Any]:
    pair=verify_independent_pair(base_root,dict(base_receipt_a),dict(base_receipt_b),observed_commit_sha=observed_commit_sha)
    if pair.get('pass') is not True: return _fail('EXACT_CURRENT_BASE_NOT_PROVED',base_gate=pair)
    lockdoc=json.loads((patch_root/'canonical/governance/CURRENT_FRONTIER_REUSE_SOURCE_LOCK_20261011_V2.json').read_text())
    lock=verify_source_lock(patch_root,lockdoc['sources'])
    if lock.get('pass') is not True: return _fail('PATCH_SOURCE_LOCK_FAILED',source_lock=lock)
    base_map=_receipt_file_map(base_receipt_a)
    files=_collect_patch_files(patch_root)+_collect_vendor_files(patch_root,lockdoc['sources'])
    # dedupe identical targets, reject divergent writers
    by={}
    for row in files:
        prior=by.get(row['path'])
        if prior and prior['sha256']!=row['sha256']:
            return _fail('MULTIPLE_PATCH_SOURCES_DISAGREE',path=row['path'],sources=[prior['source'],row['source']])
        by[row['path']]=row
    preconditions=[]
    for rel,row in sorted(by.items()):
        p=base_root/rel
        if p.exists():
            actual=_sha_bytes(p.read_bytes()); expected=base_map.get(rel)
            if expected!=actual:
                return _fail('TARGET_PREIMAGE_NOT_BOUND_BY_BASE_RECEIPT',path=rel,expected=expected,actual=actual)
            preconditions.append({'path':rel,'preimage_sha256':actual,'action':'REPLACE' if actual!=row['sha256'] else 'NOOP_EXACT'})
        else:
            if rel in base_map: return _fail('BASE_RECEIPT_PATH_STATE_INCONSISTENT',path=rel)
            preconditions.append({'path':rel,'preimage_sha256':None,'action':'ADD'})
    if destination is None: destination=Path(tempfile.mkdtemp(prefix='brain-candidate-'))
    else:
        if destination.exists(): shutil.rmtree(destination)
        destination.mkdir(parents=True)
    for p in base_root.iterdir():
        if p.name=='.git': continue
        dst=destination/p.name
        if p.is_dir(): shutil.copytree(p,dst,symlinks=False)
        elif p.is_file(): shutil.copy2(p,dst)
    for rel,row in sorted(by.items()):
        target=destination/rel; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(row['bytes'])
    cand=tree_manifest(destination)
    if cand.get('pass') is not True: return _fail('CANDIDATE_TREE_ATTESTATION_FAILED',candidate_tree=cand)
    core={'base_commit_sha':observed_commit_sha,'base_tree_sha256':pair['tree_sha256'],'base_receipt_sha256s':pair['receipt_sha256s'],
          'candidate_tree_sha256':cand['tree_sha256'],'overlay_files':[{k:x[k] for k in ('path','sha256','source')} for x in sorted(by.values(),key=lambda x:x['path'])],
          'preconditions':preconditions,'source_lock_verified_sha256s':lock['verified']}
    return {'schema':SCHEMA,'pass':True,'status':'PASS__EXACT_CURRENT_BASE_CANDIDATE_STAGED__ISOLATED__NOT_COMMITTED',
            **core,'application_receipt_sha256':_sha_obj(core),'candidate_path':str(destination),'canonical_commit_eligible':False,
            'requires_isolated_test_receipt':True,'mutation_authority':False,'promotion_authority':False,'activation_authority':False,
            'terminal_authority':False,'terminal_credit_delta':0,'incremental_spend_usd':0}

def verify_staged_candidate(staged:Mapping[str,Any], *, test_receipt:Mapping[str,Any], independent_verifier_id:str)->dict[str,Any]:
    if staged.get('pass') is not True: return _fail('STAGED_CANDIDATE_INVALID')
    p=Path(str(staged.get('candidate_path','')))
    tm=tree_manifest(p)
    if tm.get('pass') is not True or tm.get('tree_sha256')!=staged.get('candidate_tree_sha256'):
        return _fail('STAGED_TREE_CHANGED_AFTER_APPLICATION')
    if not independent_verifier_id or independent_verifier_id in {None,''}:
        return _fail('INDEPENDENT_VERIFIER_ID_MISSING')
    if test_receipt.get('pass') is not True or test_receipt.get('candidate_tree_sha256')!=tm['tree_sha256']:
        return _fail('ISOLATED_TEST_RECEIPT_INVALID')
    if test_receipt.get('independently_verified') is not True or test_receipt.get('verifier_id')!=independent_verifier_id:
        return _fail('ISOLATED_TEST_NOT_INDEPENDENT')
    if not isinstance(test_receipt.get('test_count'),int) or test_receipt['test_count']<=0:
        return _fail('NO_ISOLATED_TESTS_PROVED')
    core={'application_receipt_sha256':staged['application_receipt_sha256'],'candidate_tree_sha256':tm['tree_sha256'],
          'test_receipt_sha256':test_receipt.get('sha256'),'test_count':test_receipt['test_count'],'verifier_id':independent_verifier_id}
    return {'schema':SCHEMA,'pass':True,'status':'PASS__EXACT_CURRENT_CANDIDATE_VERIFIED__COMMIT_ELIGIBLE__NOT_COMMITTED',
            **core,'commit_eligibility_receipt_sha256':_sha_obj(core),'canonical_commit_eligible':True,'mutation_authority':False,
            'promotion_authority':False,'activation_authority':False,'terminal_authority':False,'terminal_credit_delta':0,'incremental_spend_usd':0}
