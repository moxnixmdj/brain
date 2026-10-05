import copy
import hashlib
import json
from pathlib import Path
from canonical.runtime.brain_witness_normalization_verifier_v3 import evaluate

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
NORMALIZED=ROOT/"canonical/governance/OPUS55_BRAIN_WITNESS_NORMALIZATION_V3.json"

def blob(p):
    b=p.read_bytes()
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def load(p):
    return json.loads(p.read_text())

source=load(SOURCE)
normalized=load(NORMALIZED)
out=evaluate(source,normalized,blob(SOURCE))
assert out["pass"] is True,out
assert out["witness_count"]==14,out
assert out["semantic_implication_verified"] is False
assert out["scope_relation_verified"] is False

bad=copy.deepcopy(normalized)
bad["witnesses"][0]["semantic_implications"]=["invented"]
o=evaluate(source,bad,blob(SOURCE))
assert o["pass"] is False
assert "NORMALIZED_WITNESSES_NOT_EXACT_RECOMPUTATION" in o["errors"]
assert any("SEMANTIC_IMPLICATION_CREDIT_FORBIDDEN" in e for e in o["errors"])

bad2=copy.deepcopy(normalized)
bad2["witnesses"][0]["normalized_metric_bounds"]={"invented":1}
o=evaluate(source,bad2,blob(SOURCE))
assert o["pass"] is False
assert any("METRIC_BOUND_CREDIT_FORBIDDEN" in e for e in o["errors"])

missing=copy.deepcopy(normalized)
missing["witnesses"]=missing["witnesses"][:-1]
missing["witness_count"]-=1
o=evaluate(source,missing,blob(SOURCE))
assert o["pass"] is False
assert "NORMALIZED_WITNESSES_NOT_EXACT_RECOMPUTATION" in o["errors"]

print("test_brain_witness_normalization_v3: PASS")
