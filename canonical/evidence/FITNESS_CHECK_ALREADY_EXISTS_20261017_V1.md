# The fitness check already exists. Do not rebuild it.

I wrote `goal_fitness_check_v1.py` to answer "can this capability act on this
goal?" It has been deleted. The grounding already computes it.

## What the grounding already emits

From `plain_goal.bound_capability.grounding`, per candidate:

    "input_bindability": {"bound_input_keys": [], ...}
    "binding_affordance": {
        "has_goal_url": false,
        "proposal_binding_count": 0,
        "proposal_bindings_cover_all_inputs": false,
        "url_consumable": false
    }

Top level:

    "input_contract_bindability_enforced": true
    "grounded_clause_count": 1
    "unresolved_clause_indexes": []

So the capability already knows the proposed bindings do NOT cover the
capability's inputs, and already says so.

## The real defect

The information was present and **not acted on**. The result was still
reported as GROUNDED.

So the gap is not a missing check. It is that an existing, correct check
computed `proposal_bindings_cover_all_inputs: false` and the caller surfaced
the match anyway.

That is a smaller and more precise bug than "the front door is only lexical".
The front door is lexical **and then ignores its own bindability verdict**.

## The fix, therefore

Not a new module. In the caller: if `input_contract_bindability_enforced` is
true and the selected candidate's `proposal_bindings_cover_all_inputs` is
false, the goal is not grounded — report it as such rather than returning
GROUNDED with a score.

## Why this is worth recording

This is the fifth time this session a thing was built or inferred that already
existed in the repository. The pattern is consistent and expensive:

1. asserted the frontier was GPT-4o (repo already said Opus 5.5);
2. made JIT a routing destination (canon already said capability is owned);
3. reported 14 broken capabilities (10 were missing nested packages);
4. searched for a provenance verifier that already existed unbound;
5. wrote a fitness check the grounding already emits.

Every one was avoided by reading before building. The canon says it directly:
"Refresh live canonical state before consequential reasoning. Do not schedule
from stale summaries."

Cost of the deletion: nothing. Cost of keeping it: a second, subtly
different answer to a question the system already answers authoritatively.
