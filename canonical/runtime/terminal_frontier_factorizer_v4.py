from canonical.runtime.terminal_frontier_factorizer_v3 import ATOMIC, TARGET_TUPLE_ATOMS, EXTERNAL_RESULT_ATOMS, UNIVERSAL_SCOPE_ATOMS

META=("TARGET_COMPLETE_TERMINAL_COVERAGE_CERTIFICATE",)

def factorize():
    obligations=list(ATOMIC)+list(META)
    req={x:[] for x in obligations}
    for x in TARGET_TUPLE_ATOMS: req[x].append("TARGET_TUPLE_BINDING")
    for x in EXTERNAL_RESULT_ATOMS: req[x].append("EXTERNAL_RESULT_OR_ACCESS")
    for x in UNIVERSAL_SCOPE_ATOMS: req[x].append("UNIVERSAL_SCOPE_AND_COMPOSITION")
    req[META[0]].append("TARGET_COMPLETENESS_AND_GLOBAL_COVERAGE")
    if any(not v for v in req.values()): raise RuntimeError("UNMAPPED")
    return {"atomic_count":len(ATOMIC),"meta_count":1,"truth_obligation_count":len(obligations),"D_count":len(EXTERNAL_RESULT_ATOMS),"U_count":len(obligations)-len(EXTERNAL_RESULT_ATOMS),"terminal_credit_delta":0,"obligation_interfaces":req}
