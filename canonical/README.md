# Project Brain Canonical

This directory is the provider-independent canonical control plane for Project Brain.

## Authority model

- **GitHub (this private repository):** canonical human/auditable state, manifests, event history, laws, hashes, and pointers.
- **Google Drive:** immutable binary/evidence mirror for large snapshots and artifacts.
- **SQLite:** active working authority/cache. It must be reconstructable from canonical evidence and must never be the only durable source.
- **Execution providers:** replaceable and non-canonical. CI, browser providers, agent platforms, model surfaces, and other providers may execute work but cannot define canonical truth by themselves.

## Current verified state

- Real integrated same-identity Superworker population: **P_real = 1**.
- Active qualified identity: `SUPERWORKER-UNIFIED-1`.
- First proof mission: `SI-REAL-UBJSON-SNAPSHOT-001`.
- Proof workflow conclusion: **SUCCESS**.
- Same-identity checkpoint/relaunch: **VERIFIED**.
- Dynamic capability discovery/acquisition: **VERIFIED on the proof mission**.
- Provider-neutral external-tool bridge: **VERIFIED on the proof mission**.
- Cross-supplier independent verification: **VERIFIED on the proof mission**.
- Hard incremental spend: **$0**.
- Full frontier capability breadth: **NOT YET PROVEN**.
- Same-identity clean-room reproduction of the verified architecture: **NOT YET PROVEN**.

See:
- `canonical/agents/SUPERWORKER_UNIFIED_1.json`
- `canonical/qualification/SUPERWORKER_UNIFIED_1_WHOLE_DEFINITION_ADJUDICATION_V1.json`
- `canonical/CANONICAL_POINTER.json`

## Active terminal objective

The existence phase is complete.

Project Brain now exists to turn the proven Superworker architecture into a **reproducible, model-independent frontier-capability system** that can match and then exceed the useful real-world capability surface demonstrated by frontier agents/models.

Frontier systems are capability references only. They are not implementation blueprints, required providers, naming targets, or proof authorities.

The canonical phase order is:

1. clean-room reproduction;
2. capability breadth;
3. frontier comparability on the same real tasks and outcome criteria;
4. capability superset through verified composition;
5. efficiency;
6. population scaling.

Population scaling is intentionally deferred until same-identity clean-room reproduction and minimum cross-domain breadth are verified.

Authoritative goal:
- `canonical/laws/FRONTIER_CAPABILITY_SUPERWORKER_MISSION_LOCK_V2.md`

Canonical capability map:
- `canonical/capabilities/FRONTIER_CAPABILITY_TARGET_MAP_V1.json`

## Immediate frontier

Run a **fresh clean-room worker from canonical state on a distinct consequential mission**, without copying hidden mutable execution state from the first worker.

Independently adjudicate that result.

If reproduction succeeds, use the smallest orthogonal portfolio of unseen consequential missions to expose missing frontier capability classes. Every failure should drive the same blocker-extinction loop:

`real mission → first causal blocker → search/reuse before invention → minimal generic repair → falsify/verify → replay → inherit → continue`

## Progress metric

The project no longer treats existence, predicate completion, benchmark completion, infrastructure, or worker count as the target.

Before scaling, progress means **verified increase in reproducible real capability**.

After the capability/reproducibility gates, the primary scaling metric becomes:

`verified consequential outcomes / wall-clock time`

## Non-negotiable law

Provider loss, suspension, deletion, outage, or account failure must not destroy canonical truth or prevent reconstruction.

No provider is canonical. Provider-specific execution is replaceable substrate only.
