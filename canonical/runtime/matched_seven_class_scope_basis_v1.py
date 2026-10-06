from __future__ import annotations

from canonical.runtime.matched_success_component_bound_v4 import RULES
from canonical.runtime.matched_success_scope_compiler_v1 import REQUIRED

LEGACY_EXTENSIONS = {
    "AGENCY_THREE_TOOL_LONG_HORIZON": {
        "dimension:state_change_after_actions_requiring_replanning",
        "dimension:tool_failure_and_recovery",
        "dimension:subtask_dependency_and_fan_in",
        "dimension:authorization_and_scope_boundaries",
        "dimension:explicit_abstention_and_fail_closed_cases",
    },
    "INSTRUCTION_CHANGE_CONTROL": {
        "dimension:routine_ambiguity",
    },
}

def class_atom_basis() -> dict[str, tuple[str, ...]]:
    out = {}
    for cid, (_, atoms) in RULES.items():
        out[cid] = tuple(sorted(set(atoms) | LEGACY_EXTENSIONS.get(cid, set())))
    return out

def verify_basis() -> dict:
    basis = class_atom_basis()
    errors = []
    if set(basis) != set(RULES):
        errors.append("CLASS_SET_DRIFT")
    if len(basis) != 7:
        errors.append("CLASS_COUNT_NOT_7")

    v4_atoms = {a for _, atoms in RULES.values() for a in atoms}
    legacy_atoms = set().union(*LEGACY_EXTENSIONS.values())
    all_atoms = set().union(*(set(v) for v in REQUIRED.values()))
    basis_atoms = set().union(*(set(v) for v in basis.values()))

    if len(v4_atoms) != 10:
        errors.append("V4_ATOM_COUNT_NOT_10")
    if len(legacy_atoms) != 6:
        errors.append("LEGACY_EXTENSION_COUNT_NOT_6")
    if v4_atoms & legacy_atoms:
        errors.append("V4_LEGACY_OVERLAP")
    if len(all_atoms) != 16:
        errors.append("SCOPE_ATOM_COUNT_NOT_16")
    if basis_atoms != all_atoms:
        errors.append("BASIS_NOT_EXACT_SCOPE_COVER")

    target_cover = {}
    for target, required in REQUIRED.items():
        target_cover[target] = {
            cid: sorted(set(atoms) & set(required))
            for cid, atoms in basis.items()
            if set(atoms) & set(required)
        }
        covered = set().union(*(set(v) for v in target_cover[target].values()))
        if covered != set(required):
            errors.append("TARGET_SCOPE_NOT_COVERED:" + target)

    ok = not errors
    return {
        "schema": "PROJECT_BRAIN_MATCHED_SEVEN_CLASS_SCOPE_BASIS_VERIFIER_V2",
        "status": "PASS__7_CLASS_FAMILIES_EXACTLY_COVER_16_MATCHED_SCOPE_ATOMS__CROSS_TARGET_REUSE_ALLOWED__ZERO_CREDIT" if ok else "FAIL_CLOSED",
        "pass": ok,
        "errors": sorted(errors),
        "class_count": len(basis),
        "scope_atom_count": len(basis_atoms),
        "v4_integrated_atom_count": len(v4_atoms),
        "legacy_extension_atom_count": len(legacy_atoms),
        "class_atom_basis": basis,
        "target_coverage_by_class": target_cover,
        "cross_target_reuse_required": True,
        "legacy_extension_classes": sorted(LEGACY_EXTENSIONS),
        "separate_legacy_case_class_required": False if ok else None,
        "execution_authority": False,
        "fresh_reality_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }

if __name__ == "__main__":
    import json
    out = verify_basis()
    print(json.dumps(out, indent=2, sort_keys=True))
    raise SystemExit(0 if out["pass"] else 1)
