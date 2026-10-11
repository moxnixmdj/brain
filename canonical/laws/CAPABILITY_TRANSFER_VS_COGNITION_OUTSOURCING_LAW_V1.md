# CAPABILITY TRANSFER VS COGNITION OUTSOURCING LAW V1

Status: CANONICAL / MANDATORY / FAIL-CLOSED

Authority:
- explicit owner instruction, 2026-10-11;
- canonical/laws/GENERAL_COGNITION_SUBSTRATE_AND_CAPABILITY_OWNERSHIP_LAW_V4.md;
- canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V10.md.

## Purpose

Permanently distinguish legitimate capability internalization from forbidden cognition outsourcing.

The distinction is causal, not lexical. Renaming a model call as distillation, transfer, teacher use, adapter use, fine-tuning, imitation, retrieval, substrate, planner, agent, or local inference does not change its class.

## Forbidden cognition outsourcing

A route is FORBIDDEN for Brain credit when, on the future task being credited, any external/general-purpose donor model remains load-bearing for reasoning, planning, synthesis, judgment, tool choice, recovery, code/answer generation, or another target-solving transformation.

If the donor/model must be callable, loaded, queried, prompted, or inferred through to solve the credited task, the route is model-assisted cognition outsourcing and receives zero Brain capability, benchmark, acceptance, ownership, promotion, and terminal credit.

## Allowed capability transfer

A donor may be used only during a bounded acquisition phase to create a new Brain-owned mechanism.

Potential transfer methods include:
- distillation;
- behavioral imitation;
- supervised or preference training from donor-produced examples;
- synthetic-data training;
- fine-tuning of an already Brain-owned substrate;
- checkpoint/task-vector transfer;
- sparse or low-rank deltas/adapters;
- module/expert/circuit extraction;
- algorithm or procedure recovery;
- mechanistic reimplementation;
- verified composition of transferred mechanisms.

The method name grants no ownership. Promotion requires every transfer condition below.

## Mandatory transfer conditions

A transferred capability is Brain-owned only when ALL are true:

1. PHASE SEPARATION: donor use is confined to acquisition. Qualification and credited deployment occur after donor removal.
2. BRAIN-OWNED OPERATIVE ARTIFACT: exact future-solving bytes/configuration are durably stored under Brain authority with complete provenance and applicable rights.
3. ZERO DONOR RUNTIME DEPENDENCY: donor model/service/code/weights are absent from the credited producer path.
4. ZERO EXTERNAL MODEL COGNITION DEPENDENCY: no other general-purpose model replaces the donor in the producer path.
5. DONOR-DELETION PROOF: capability survives with donor access disabled/unavailable.
6. INDEPENDENT QUALIFICATION: exact Brain artifact meets the target bar on frozen held-out evidence not used for teaching, selection, tuning, pruning, or minimization.
7. CAUSAL OWNERSHIP: ablation degrades the capability and restoration of the transferred Brain mechanism rescues it under matched conditions.
8. FULL DEPENDENCY CLOSURE: every unavoidable runtime dependency is enumerated and none is a hidden cognition provider.
9. NO ANSWER LEAKAGE: retained bytes/data/configuration do not encode qualification answers or task-specific hidden solutions.
10. RECONSTRUCTIBILITY: future use does not require rediscovering, requerying, or re-extracting the capability from the donor.
11. ATTRIBUTION: evidence records the donor as acquisition provenance, not as the operative solver.
12. FAIL-CLOSED AMBIGUITY: if acquisition-vs-deployment separation cannot be proved, the route is treated as forbidden outsourcing.

## Distillation-specific rule

Distillation is permitted as capability acquisition only when the student/derived mechanism becomes the operative Brain artifact and the teacher is absent during qualification and deployment.

Teacher-at-inference, teacher fallback, teacher reranking, teacher critique, teacher hidden-state access, teacher-generated online plans, or teacher calls triggered on hard cases make the route model-assisted and non-creditable.

A copied or lightly wrapped external model is not distillation merely because its weights are stored locally. A student artifact must be a distinct derived mechanism with provenance, dependency closure, and independent post-deletion verification.

## Training data rule

Donor outputs may be acquisition data when rights/provenance permit, but final qualification examples and hidden benchmark items must remain untouched by acquisition, selection, and tuning.

Knowledge learned into the transferred mechanism is allowed; direct JIT cognition from the donor on the credited task is not.

## Permanence

This law is subordinate only to an explicit owner instruction that directly names and rescinds this distinction. Scheduler pressure, benchmark urgency, zero cost, local hosting, open weights, model renaming, or a new transfer label cannot create an exception.
