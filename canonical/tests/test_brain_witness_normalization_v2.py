import hashlib,json
from pathlib import Path
from canonical.runtime.brain_witness_normalization_verifier_v2 import evaluate

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
NORMALIZED=ROOT/"canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V2.json"

def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

source=json.loads(SOURCE.read_text())
normalized=json.loads(NORMALIZED.read_text())
out=evaluate(source,normalized,blob(SOURCE))
assert out["pass"] is True,out
assert out["witness_count"]==12,out
assert out["semantic_implication_verified"] is False
assert out["scope_relation_verified"] is False
assert out["acceptance_credit_delta"]==0
assert out["family_credit_delta"]==0
assert out["ownership_credit_delta"]==0

bad=json.loads(json.dumps(normalized))
bad["witnesses"][0]["semantic_implications"]=["invented"]
fail=evaluate(source,bad,blob(SOURCE))
assert fail["pass"] is False
assert "NORMALIZED_WITNESSES_NOT_EXACT_RECOMPUTATION" in fail["errors"]
assert any("SEMANTIC_IMPLICATION_CREDIT_FORBIDDEN" in e for e in fail["errors"])

missing=json.loads(json.dumps(normalized))
missing["witnesses"]=missing["witnesses"][:-1]
missing["witness_count"]-=1
fail2=evaluate(source,missing,blob(SOURCE))
assert fail2["pass"] is False
assert "NORMALIZED_WITNESSES_NOT_EXACT_RECOMPUTATION" in fail2["errors"]

print("test_brain_witness_normalization_v2: PASS")
