"""Deterministic exact-tree attestation for canonical application.

This deliberately rejects symlinks and ignores only repository/runtime metadata that
cannot be part of the canonical content claim (.git, pytest/python caches).
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Iterable

SCHEMA="PROJECT_BRAIN_CANONICAL_TREE_ATTESTATION_V1"
_EXCLUDE_DIRS={'.git','__pycache__','.pytest_cache'}

def _sha_bytes(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def _sha_obj(o:Any)->str: return _sha_bytes(json.dumps(o,sort_keys=True,separators=(',',':')).encode())
def _valid_sha(v:Any)->bool: return isinstance(v,str) and len(v)==64 and all(c in '0123456789abcdef' for c in v)

def tree_manifest(root:Path, *, exclude_dirs:Iterable[str]=())->dict[str,Any]:
    root=root.resolve(); excluded=_EXCLUDE_DIRS|set(exclude_dirs); files=[]; rejected=[]
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root).as_posix()
        if any(part in excluded for part in p.relative_to(root).parts): continue
        if p.is_symlink(): rejected.append({'path':rel,'reason':'SYMLINK_REJECTED'}); continue
        if not p.is_file() or p.name.endswith('.pyc'): continue
        data=p.read_bytes(); files.append({'path':rel,'bytes':len(data),'sha256':_sha_bytes(data)})
    core={'files':files}
    return {'schema':SCHEMA,'pass':not rejected,'status':'PASS__EXACT_TREE_ATTESTED' if not rejected else 'FAIL_CLOSED__UNSUPPORTED_TREE_ENTRY',
            'root':str(root),'file_count':len(files),'tree_sha256':_sha_obj(core),'files':files,'rejected':rejected}

def mint_receipt(root:Path, *, commit_sha:str, verifier_id:str, current_main_observed:bool)->dict[str,Any]:
    if not isinstance(commit_sha,str) or len(commit_sha)<7 or not verifier_id:
        return {'schema':SCHEMA,'pass':False,'status':'FAIL_CLOSED','reason':'RECEIPT_INPUT_INVALID','mutation_authority':False}
    tm=tree_manifest(root)
    if tm['pass'] is not True: return {**tm,'mutation_authority':False}
    core={'commit_sha':commit_sha,'tree_sha256':tm['tree_sha256'],'file_count':tm['file_count'],
          'files':tm['files'],'verifier_id':verifier_id,'current_main_observed':current_main_observed}
    return {'schema':SCHEMA,'pass':True,'status':'PASS__BASE_RECEIPT_MINTED__NOT_MUTATION_AUTHORITY',**core,
            'receipt_sha256':_sha_obj(core),'mutation_authority':False,'terminal_authority':False,'terminal_credit_delta':0}

def verify_receipt(root:Path, receipt:dict[str,Any], *, observed_commit_sha:str)->dict[str,Any]:
    if receipt.get('pass') is not True or receipt.get('current_main_observed') is not True:
        return {'schema':SCHEMA,'pass':False,'status':'FAIL_CLOSED','reason':'BASE_NOT_ATTESTED_AS_CURRENT_MAIN','mutation_authority':False}
    if observed_commit_sha!=receipt.get('commit_sha'):
        return {'schema':SCHEMA,'pass':False,'status':'FAIL_CLOSED','reason':'CURRENT_COMMIT_MISMATCH','mutation_authority':False}
    tm=tree_manifest(root)
    if tm.get('pass') is not True or tm.get('tree_sha256')!=receipt.get('tree_sha256'):
        return {'schema':SCHEMA,'pass':False,'status':'FAIL_CLOSED','reason':'BASE_TREE_MISMATCH','mutation_authority':False,
                'observed_tree_sha256':tm.get('tree_sha256'),'receipt_tree_sha256':receipt.get('tree_sha256')}
    core={k:receipt.get(k) for k in ('commit_sha','tree_sha256','file_count','files','verifier_id','current_main_observed')}
    if not _valid_sha(receipt.get('receipt_sha256')) or _sha_obj(core)!=receipt['receipt_sha256']:
        return {'schema':SCHEMA,'pass':False,'status':'FAIL_CLOSED','reason':'BASE_RECEIPT_DIGEST_INVALID','mutation_authority':False}
    return {'schema':SCHEMA,'pass':True,'status':'PASS__EXACT_CURRENT_BASE_RECEIPT_VERIFIED','commit_sha':observed_commit_sha,
            'tree_sha256':tm['tree_sha256'],'receipt_sha256':receipt['receipt_sha256'],'verifier_id':receipt['verifier_id'],
            'mutation_authority':False,'terminal_authority':False,'terminal_credit_delta':0}

def verify_independent_pair(root:Path, a:dict[str,Any], b:dict[str,Any], *, observed_commit_sha:str)->dict[str,Any]:
    va=verify_receipt(root,a,observed_commit_sha=observed_commit_sha); vb=verify_receipt(root,b,observed_commit_sha=observed_commit_sha)
    if va.get('pass') is not True or vb.get('pass') is not True:
        return {'schema':SCHEMA,'pass':False,'status':'FAIL_CLOSED','reason':'BASE_RECEIPT_PAIR_INVALID','a':va,'b':vb,'mutation_authority':False}
    if a.get('verifier_id')==b.get('verifier_id'):
        return {'schema':SCHEMA,'pass':False,'status':'FAIL_CLOSED','reason':'VERIFIERS_NOT_INDEPENDENT','mutation_authority':False}
    if (a.get('commit_sha'),a.get('tree_sha256'))!=(b.get('commit_sha'),b.get('tree_sha256')):
        return {'schema':SCHEMA,'pass':False,'status':'FAIL_CLOSED','reason':'INDEPENDENT_BASE_RECEIPTS_DISAGREE','mutation_authority':False}
    return {'schema':SCHEMA,'pass':True,'status':'PASS__TWO_INDEPENDENT_EXACT_CURRENT_BASE_RECEIPTS_AGREE',
            'commit_sha':a['commit_sha'],'tree_sha256':a['tree_sha256'],'receipt_sha256s':sorted([a['receipt_sha256'],b['receipt_sha256']]),
            'mutation_authority':False,'terminal_authority':False,'terminal_credit_delta':0}
