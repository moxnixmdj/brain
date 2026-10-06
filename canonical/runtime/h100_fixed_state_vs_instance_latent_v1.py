class FixedStateLatentError(ValueError):
    pass

def analyze(*, same_runtime_observation, required_outputs, latent_scope):
    if not isinstance(same_runtime_observation, bool):
        raise FixedStateLatentError("BOOLEAN_REQUIRED")
    if not isinstance(required_outputs, list) or not required_outputs:
        raise FixedStateLatentError("OUTPUTS_INVALID")
    if latent_scope not in {"GLOBAL_FIXED","PER_INSTANCE"}:
        raise FixedStateLatentError("SCOPE_INVALID")
    k=len({repr(x) for x in required_outputs})
    if (not same_runtime_observation) or k<=1:
        return {"exact_possible_with_fixed_state":True,"persistent_bits_may_help":False,"reason":"NO_OUTPUT_AMBIGUITY"}
    if latent_scope=="PER_INSTANCE":
        return {"exact_possible_with_fixed_state":False,"persistent_bits_may_help":False,"reason":"MISSING_INSTANCE_INFORMATION"}
    return {"exact_possible_with_fixed_state":True,"persistent_bits_may_help":True,"reason":"GLOBAL_TARGET_CAN_BE_ENCODED"}
