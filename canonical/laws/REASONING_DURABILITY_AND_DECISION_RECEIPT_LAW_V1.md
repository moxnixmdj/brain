# REASONING DURABILITY AND DECISION RECEIPT LAW V1

Status: CANONICAL / MANDATORY / FAIL-CLOSED

## Purpose

Project Brain must not lose consequential reasoning conclusions between chats, agents, branches, compactions, or restarts.

This law preserves decision-relevant reasoning without requiring or storing private chain-of-thought.

## Mandatory durable reasoning record

Before a consequential conclusion or action becomes authoritative, persist a compact decision receipt containing:
- real objective;
- governing laws/invariants;
- material premises/facts;
- evidence/provenance references;
- conclusion;
- selected route or decision;
- material alternatives rejected and the decisive reason for each;
- known uncertainty;
- assumptions;
- explicit non-goals;
- next action;
- supersession conditions;
- receipts or decisions superseded.

A chat message alone has zero canonical reasoning authority.

## No silent drift

A later worker may disagree with an earlier receipt, but may not silently replace it.

A changed conclusion must:
1. cite the earlier receipt;
2. state the new evidence or changed premise;
3. mark the earlier conclusion superseded;
4. preserve both records.

## Theory invariants

Every consequential action receipt must restate or reference the current top-level theory invariants.

For the current program these include:
- target = Opus 5.5 useful capabilities equal-or-better;
- capabilities are found, configured into Brain, saved, and permanently inherited;
- capabilities are not externalized/JIT during routine operation;
- knowledge is externalized/JIT;
- knowledge is not accumulated as the capability inventory;
- underlying capability invention is forbidden;
- failure to find an existing realization becomes unresolved/theory-falsification evidence, not invention authority.

## Scope

This law applies to:
- goal changes;
- blocker claims;
- capability selection;
- route selection;
- architecture decisions;
- verification conclusions;
- promotion/demotion;
- theory corrections;
- exceptions;
- irreversible or scarce execution.

It does not require a receipt for trivial formatting, mechanical reads, or non-consequential implementation details.

## Receipt quality

Receipts must be compact enough to reread quickly and complete enough that another worker can recover the decision without the original conversation.

Do not store hidden/private chain-of-thought. Store conclusions, evidence, decisive rationale, rejected alternatives, uncertainty, and supersession rules.

## Fail closed

If a consequential action lacks a current durable reasoning receipt, it has no canonical authority.
