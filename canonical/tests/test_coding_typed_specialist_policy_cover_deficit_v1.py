import ast
import hashlib
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REG = ROOT / "canonical/runtime/p3_conditioned_policy_adequacy_registry_v1.py"
DOC = ROOT / "canonical/governance/CODING_TYPED_SPECIALIST_POLICY_COVER_DEFICIT_20261009_V1.json"
POLICY = "BRAIN_INDEPENDENT_ACCEPTANCE_MODEL_TYPED_PLAN_V1"

def git_blob_sha(path):
    data = path.read_bytes()
    h = hashlib.sha1()
    h.update(b"blob " + str(len(data)).encode() + b"\0" + data)
    return h.hexdigest()

def registry_literal():
    tree = ast.parse(REG.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [x.id for x in node.targets if isinstance(x, ast.Name)]
            if "_REGISTRY" in names:
                return ast.literal_eval(node.value)
    raise AssertionError("_REGISTRY_NOT_FOUND")

def condition_holds(condition, valuation):
    op = condition["op"]
    if op == "ATOM":
        return valuation[condition["id"]]
    if op == "AND":
        return all(condition_holds(row, valuation) for row in condition["args"])
    if op == "OR":
        return any(condition_holds(row, valuation) for row in condition["args"])
    if op == "NOT":
        return not condition_holds(condition["arg"], valuation)
    raise AssertionError("UNSUPPORTED_OP:" + op)

def test_exact_current_typed_specialist_cover_is_one_of_32():
    doc = json.loads(DOC.read_text(encoding="utf-8"))
    registry = registry_literal()
    assert git_blob_sha(REG) == doc["source"]["git_blob_sha"]
    condition = registry[POLICY]["condition"]
    assert condition == doc["exact_current_condition"]
    basis = doc["decision_basis"]
    covered = []
    for bits in itertools.product([False, True], repeat=len(basis)):
        valuation = dict(zip(basis, bits))
        if condition_holds(condition, valuation):
            covered.append("".join("1" if valuation[a] else "0" for a in basis))
    assert len(basis) == 5
    assert covered == ["11111"]
    exact = doc["exhaustive_boolean_result"]
    assert exact["total_boolean_valuations"] == 32
    assert exact["specialist_condition_true_valuations"] == 1
    assert exact["specialist_condition_false_valuations"] == 31
    assert exact["current_specialist_cover_fraction"] == "1/32"
    assert doc["deduction"]["current_registry_by_itself_scope_complete_on_unconstrained_typed_lattice"] is False
    assert doc["deduction"]["p3_common_policy_can_close_on_current_unconstrained_typed_lattice"] is False
    assert doc["accounting"]["acceptance_credit_delta"] == 0
    assert doc["accounting"]["terminal_credit_delta"] == 0

if __name__ == "__main__":
    test_exact_current_typed_specialist_cover_is_one_of_32()
    print("PASS 1/1")
