# EXTERNAL KNOWLEDGE, CAPABILITY TRANSFER, AND RUNTIME COGNITION BOUNDARY LAW V1

Status: CANONICAL / MANDATORY / FAIL-CLOSED

Authority:
- canonical/laws/GENERAL_COGNITION_SUBSTRATE_AND_CAPABILITY_OWNERSHIP_LAW_V4.md
- canonical/laws/CAPABILITY_TRANSFER_VS_COGNITION_OUTSOURCING_LAW_V1.md
- explicit owner instruction 2026-10-11.

Every external contribution belongs to exactly one of three classes. Ambiguous classification fails closed.

## K1: external knowledge or evidence

Allowed during Brain operation only as non-authoritative information.

Examples:
- factual records;
- measurements;
- documents;
- retrieved knowledge;
- authenticated observations;
- benchmark task bytes when authorized;
- independently produced evidence.

K1 may inform Brain but may not choose the policy, plan the solution, generate the credited answer, repair the reasoning, or otherwise perform target-solving cognition.

For any policy-changing K1 fact, Brain must bind it to the exact requested observation/evidence scope and independently authenticate the source/semantics before it can affect a credited result.

K1 carries:
- cognition authority = false;
- policy authority = false;
- answer authority = false;
- capability ownership credit = 0.

## K2: acquisition-time capability donor

Allowed only in a separate capability-acquisition phase.

Examples:
- teacher model used for distillation;
- donor used for imitation or synthetic training data;
- inspectable donor used for circuit/module/algorithm extraction;
- donor used to teach or fine-tune a Brain-owned derived mechanism.

K2 must pass the complete capability-transfer ownership gate. Donor provenance persists through all derived episodes and compositions. Qualification occurs only after donor removal. The donor has zero runtime cognition authority and zero direct Brain credit.

## K3: runtime cognition provider

Forbidden in every Brain-credited producer path.

K3 includes any external/general-purpose system that materially performs reasoning, planning, policy selection, decomposition, synthesis, critique, repair, reranking, tool choice, code generation, answer generation, or other target-solving transformation on the credited task.

It remains K3 if it is local, open-weight, free, self-hosted, copied, content-addressed, wrapped, renamed, called a planner/advisor/substrate/tool, or invoked only on difficult cases.

Any K3 dependency means zero Brain capability, benchmark, acceptance, ownership, promotion, and terminal credit.

## Classification precedence

If an external contribution could plausibly fit more than one class:
1. any target-solving cognition makes it K3;
2. otherwise any donor-derived learned mechanism makes it K2 until donor deletion and transfer promotion close;
3. otherwise source-bound non-authoritative facts/evidence may be K1.

A label never overrides causal function.

## Anti-laundering examples

- Model returns a fact supported by independently authenticated source evidence: K1 may be admissible; the model itself has no authority.
- Model reads the task and proposes the solution: K3, forbidden.
- Model generates training examples before final qualification; student later solves with teacher absent: K2, potentially valid after transfer gates.
- Model supplies a fallback answer at deployment: K3, forbidden.
- Retrieval returns a document; Brain reasons over it: K1, allowed.
- Retrieval service returns a ready-made task-specific plan or answer and Brain merely relays it: K3, forbidden.
- Teacher-derived capability is recomposed days later: still K2-derived until provenance and transfer proof remain closed.

## Permanence

This boundary cannot be weakened by renaming, hosting changes, optimization pressure, benchmark urgency, or ordinary inferred supersession. Only an explicit owner instruction that directly names and rescinds this boundary may change it.
