# The front door works — plain goal to bound capability

`plain_goal.bound_capability.grounding.stdlib` is the entry the whole system
has been missing. It takes a plain-language goal as a STRING and returns a
scored, grounded capability.

## Live run

Input:

    "Find out whether Brain owns its capability mechanisms and report the evidence"

Output:

    status:   GROUNDED
    index:    0, start 0, end 77
    candidate: terminal.kstar.root.assess.stdlib
    combined_score: 25.266666666666666
    lexical.score: 12
    matched_goal_tokens: [brain, capability, evidence]

## Why this is the front door

Everything before this required a caller who already knew which capability to
invoke and what fields to fill. That is not autonomy; that is a library.

With this, the sequence becomes:

    plain goal (string)
      -> grounded capability, scored
      -> execute
      -> decision synthesis
      -> independent verification

No human naming the tool. No hand-filled fields.

## Note on the selection

It selected `terminal.kstar.root.assess.stdlib`, which has an EMPTY signature
in the registry — it takes no arguments. That is worth attention: a capability
that scores highest on a goal but declares no inputs cannot currently be
executed through the typed chain. Either its signature is under-declared or it
genuinely needs no input; both need checking before this front door is wired
to the executor.

## Interface notes gathered

| Capability | Signature | Provides |
|---|---|---|
| plain_goal.bound_capability.grounding | goal: STRING, output_path | plain_goal.bound_capability.grounding |
| decision.synthesis.typed.stdlib | input_path, output_path | decision.synthesis.typed |
| decision.synthesis.verify.stdlib | input_path, result_path | decision.synthesis.verified |
| terminal.kstar.root.assess.stdlib | {} (empty) | terminal.kstar.root.assessment, proof_or_minimum_residual, tournament.failure.witness |

`terminal.kstar.root.assess.stdlib` provides a "proof or minimum residual" and
a "tournament failure witness" — that is a decision capability that reports
either a proof or the smallest remaining gap, and if it fails, the witness
showing why. Worth wiring into the decision path directly.
