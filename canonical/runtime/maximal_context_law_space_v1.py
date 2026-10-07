from __future__ import annotations

def residual(maximal_laws, brain_law, dominates):
    L=set(maximal_laws)
    if brain_law not in L:
        raise ValueError("BRAIN_LAW_OUTSIDE_MAXIMAL_SPACE")
    return {mu for mu in L if not dominates(brain_law,mu)}

def target_membership(maximal_laws,target_law):
    return target_law in set(maximal_laws)

def top_element(maximal_laws,brain_law,dominates):
    return len(residual(maximal_laws,brain_law,dominates))==0

def restricted_residual(maximal_laws,target_subset,brain_law,dominates):
    L=set(maximal_laws); K=set(target_subset)
    if not K <= L:
        raise ValueError("TARGET_RESTRICTION_OUTSIDE_MAXIMAL_SPACE")
    return {mu for mu in K if not dominates(brain_law,mu)}

def certificate(maximal_laws,target_law,brain_law,dominates,target_subset=None):
    L=set(maximal_laws)
    if target_law not in L:
        return {"pass":False,"reason":"TARGET_OUTSIDE_MAXIMAL_SPACE","terminal_credit_delta":0}
    R=residual(L,brain_law,dominates)
    out={
      "pass":True,
      "maximal_k_complete_for_target":True,
      "maximal_residual":sorted(R),
      "brain_is_top":not R,
      "target_information_required_for_completeness":False,
      "terminal_credit_delta":0,
    }
    if target_subset is not None:
        K=set(target_subset)
        if target_law not in K:
            out.update({"pass":False,"reason":"UNSOUND_TARGET_RESTRICTION"})
            return out
        out["restricted_residual"]=sorted(restricted_residual(L,K,brain_law,dominates))
    return out
