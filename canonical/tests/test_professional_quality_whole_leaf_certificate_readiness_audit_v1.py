from __future__ import annotations
import json
from hashlib import sha1
from pathlib import Path
import tempfile

from canonical.runtime import professional_quality_whole_leaf_certificate_readiness_audit_v1 as a

def blob(p: Path) -> str:
    raw=p.read_bytes()
    return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def write(p: Path, value) -> None:
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(value if isinstance(value,str) else json.dumps(value,indent=2)+"\n",encoding="utf-8")

def setup_repo():
    td=tempfile.TemporaryDirectory(); root=Path(td.name)
    ledger=root/a.gate.LEDGER_PATH
    write(ledger,{"leaves":[{"leaf_id":"L1"},{"leaf_id":"L2"}]})
    old=a.gate.LEDGER_BLOB
    a.gate.LEDGER_BLOB=blob(ledger)
    return td,root,old

def test_no_candidates_routes_only_to_totality_or_partition():
    td,root,old=setup_repo()
    try:
        out=a.audit(repo_root=root)
        assert out["pass"] is True
        assert out["leaf_count"]==2
        assert out["admissible_scope_certificate_count"]==0
        assert out["partition_or_totality_required_count"]==2
        assert all(x["state"]=="PARTITION_OR_TOTALITY_PROOF_REQUIRED" for x in out["leaves"])
    finally:
        a.gate.LEDGER_BLOB=old;td.cleanup()

def test_ambiguous_candidate_set_fails_closed_per_leaf():
    td,root,old=setup_repo()
    try:
        for i in (1,2):
            write(root/f"canonical/governance/c{i}.json",{"schema":a.gate.CERT_SCHEMA,"leaf_id":"L1"})
        write(root/"canonical/verification/v.json",{"schema":a.gate.VERIFY_SCHEMA,"leaf_id":"L1"})
        out=a.audit(repo_root=root)
        row=next(x for x in out["leaves"] if x["leaf_id"]=="L1")
        assert row["state"]=="FAIL_CLOSED_AMBIGUOUS_OR_INCOMPLETE_CANDIDATE_SET"
        assert row["whole_leaf_scope_complete"] is False
    finally:
        a.gate.LEDGER_BLOB=old;td.cleanup()

def test_exact_pair_delegates_to_verified_shared_gate(monkeypatch):
    td,root,old=setup_repo()
    try:
        write(root/"canonical/governance/c.json",{"schema":a.gate.CERT_SCHEMA,"leaf_id":"L1"})
        write(root/"canonical/verification/v.json",{"schema":a.gate.VERIFY_SCHEMA,"leaf_id":"L1"})
        monkeypatch.setattr(a.gate,"verify_entry",lambda entry,repo_root=None:{
            "pass":True,"status":"PASS__TEST","whole_leaf_scope_complete":True
        })
        out=a.audit(repo_root=root)
        row=next(x for x in out["leaves"] if x["leaf_id"]=="L1")
        assert row["state"]=="ADMISSIBLE_SCOPE_CERTIFICATE"
        assert row["whole_leaf_scope_complete"] is True
        assert out["admissible_scope_certificate_count"]==1
    finally:
        a.gate.LEDGER_BLOB=old;td.cleanup()

def test_stale_ledger_fails_closed():
    td,root,old=setup_repo()
    try:
        a.gate.LEDGER_BLOB="0"*40
        out=a.audit(repo_root=root)
        assert out["pass"] is False
        assert out["reason"]=="WHOLE_LEAF_LEDGER_STALE"
    finally:
        a.gate.LEDGER_BLOB=old;td.cleanup()
