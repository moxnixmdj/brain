"""Run the canonical test suite against one staged candidate and bind the result to its exact tree."""
from __future__ import annotations
import hashlib,json,re,subprocess,sys
from pathlib import Path
from typing import Any
from canonical.runtime.canonical_tree_attestation_v1 import tree_manifest
SCHEMA='PROJECT_BRAIN_CANONICAL_CANDIDATE_TEST_RECEIPT_V1'

def _sha(o:Any)->str: return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def run(candidate_root:Path, *, verifier_id:str, timeout_seconds:int=300)->dict[str,Any]:
    before=tree_manifest(candidate_root)
    if before.get('pass') is not True or not verifier_id:
        return {'schema':SCHEMA,'pass':False,'status':'FAIL_CLOSED','reason':'CANDIDATE_OR_VERIFIER_INVALID','independently_verified':False}
    cp=subprocess.run([sys.executable,'-m','pytest','-q','canonical/tests'],cwd=candidate_root,text=True,capture_output=True,timeout=timeout_seconds)
    after=tree_manifest(candidate_root)
    text=(cp.stdout or '')+'\n'+(cp.stderr or '')
    m=re.search(r'(\d+) passed',text)
    count=int(m.group(1)) if m else 0
    ok=cp.returncode==0 and count>0 and after.get('tree_sha256')==before.get('tree_sha256')
    core={'candidate_tree_sha256':before.get('tree_sha256'),'verifier_id':verifier_id,'test_count':count,'returncode':cp.returncode,
          'tree_unchanged_by_tests':after.get('tree_sha256')==before.get('tree_sha256'),'output_sha256':hashlib.sha256(text.encode()).hexdigest()}
    return {'schema':SCHEMA,'pass':ok,'status':'PASS__ISOLATED_CANDIDATE_TESTS_BOUND' if ok else 'FAIL_CLOSED__CANDIDATE_TESTS',
            **core,'independently_verified':ok,'sha256':_sha(core),'promotion_authority':False,'mutation_authority':False,
            'terminal_authority':False,'terminal_credit_delta':0}
