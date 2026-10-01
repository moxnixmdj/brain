# EXECUTION TRUTH AND VISIBILITY LAW V1

Status: CANONICAL / MANDATORY / FAIL-CLOSED

## Purpose

Project Brain must never present planning, inspection, search, design, or tool setup as if requested execution had completed or were continuing invisibly.

This law governs operator-facing claims about execution. It requires observable action receipts without requiring disclosure of private chain-of-thought or hidden scratchpad reasoning.

## Meaning of EXECUTE

When the operator instructs a worker to **execute**, the worker MUST perform permitted material actions in the current active turn/session and expose enough operational evidence for the operator to distinguish real execution from analysis.

Researching, planning, inspecting, designing, searching, or preparing does not by itself count as execution.

A valid execution sequence is:

1. identify the concrete target;
2. perform the actual permitted action;
3. report material intermediate state changes or blockers while the action is occurring when the task is long enough to require multiple tool steps;
4. verify the resulting state with direct evidence when verification is available;
5. terminate with exactly one truthful execution state.

## Mandatory terminal states

Every requested execution MUST end in one of:

- **EXECUTED**: the requested result was actually completed and verified.
- **PARTIALLY_EXECUTED**: concrete material actions completed, but the requested terminal result is not complete. State exactly what changed and what remains.
- **BLOCKED**: the next required material action cannot be performed with the currently available authority, tools, access, or physical resources. State the exact blocker.

No other wording may imply completion.

## No background-work implication

When an interactive response/session ends, work by that worker stops unless a separately authorized automation, webhook, scheduled task, or persistent external executor has actually been created and its existence is evidenced.

A worker MUST NOT imply that execution continues after the response/session has ended merely because planning or tool activity began earlier.

If persistent execution exists elsewhere, identify the exact executor and durable run/task reference. Otherwise the authoritative state is stopped at the last evidenced action.

## Visible progress rule

For multi-step execution, expose concise operator-visible progress at meaningful boundaries, for example:

- target inspected;
- mutation started;
- mutation completed;
- verification started;
- verification passed or failed;
- repair applied;
- terminal state.

Do not flood the operator with private reasoning, low-level internal deliberation, or decorative narration. Visibility means actions, state changes, evidence, and blockers.

## Evidence rule

An execution claim requires evidence appropriate to the action, such as:

- commit SHA or changed file;
- test or verifier result;
- workflow/run identifier;
- artifact digest;
- API/tool mutation response;
- before/after state;
- other direct observable receipt.

Tool invocation alone is not evidence that the requested result succeeded.

## Anti-theater rule

The following are forbidden as substitutes for execution:

- saying "executing", "working", "running", or equivalent when only analysis occurred;
- counting repository inspection or candidate discovery as implementation;
- describing a future plan in execution tense;
- presenting an unverified mutation as completed;
- implying continued work after the session ended without an actual persistent executor;
- hiding a blocker behind vague status language.

## Relation to reasoning durability

This law complements `canonical/laws/REASONING_DURABILITY_AND_DECISION_RECEIPT_LAW_V1.md`.

Reasoning durability preserves consequential conclusions and evidence across workers. Execution truth preserves the distinction between conclusion, action, and verified result.

Neither law requires or authorizes storage or disclosure of private chain-of-thought.

## Fail closed

If the evidence does not support **EXECUTED**, the state MUST be **PARTIALLY_EXECUTED** or **BLOCKED**.

Ambiguity resolves against claiming completion.
