# Project Brain Canonical

This directory is the provider-independent canonical control plane for Project Brain.

## Authority model

- **GitHub (this private repository):** canonical human/auditable state, manifests, event history, laws, hashes, and pointers.
- **Google Drive:** immutable binary/evidence mirror for large snapshots and artifacts.
- **SQLite:** active working authority/cache. It must be reconstructable from canonical evidence and must never be the only durable source.
- **Execution providers:** replaceable and non-canonical. CI, browser providers, agent platforms, model surfaces, and other providers may execute work but cannot define canonical truth by themselves.

## Boot rule

This README is orientation, not live scheduling authority.

Before consequential work, read:
- `canonical/CANONICAL_POINTER.json`
- `canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json`
- every mandatory law and gate named by the live pointer

If this README conflicts with those current content-addressed authorities, the current authorities win and work fails closed until the contradiction is reconciled.

## Current verified substrate

- Real integrated same-identity Superworker population: **P_real = 1**.
- Active qualified identity: `SUPERWORKER-UNIFIED-1`.
- First proof mission: `SI-REAL-UBJSON-SNAPSHOT-001`.
- Proof workflow conclusion: **SUCCESS**.
- Same-identity checkpoint/relaunch: **VERIFIED**.
- Dynamic capability discovery/acquisition: **VERIFIED on the proof mission**.
- Provider-neutral external-tool bridge: **VERIFIED on the proof mission**.
- Cross-supplier independent verification: **VERIFIED on the proof mission**.
- Hard incremental spend: **$0**.

These substrate facts do not imply completion of the terminal capability objective. Current acceptance, ownership, blockers, and scheduling state must be read from the live terminal authority.

## Core theory

Project Brain uses the current operational decomposition:

`EFFECTIVE FRONTIER INTELLIGENCE = BRAIN-OWNED CAPABILITY MECHANISMS + EXTERNAL JIT KNOWLEDGE + GENERAL COMPUTATION SUBSTRATE`

### Knowledge

Knowledge remains external/JIT:

`need knowledge -> acquire strongest relevant current knowledge -> verify -> use -> preserve only compact state/evidence needed for reproducibility`

Project Brain does not treat permanent accumulation of a frontier model's knowledge warehouse as capability ownership.

### Capabilities

Capabilities are the active ownership frontier.

For each useful target capability:

`define useful effect -> establish Opus 5.5 acceptance bar -> delete unnecessary demand -> search existing realizations -> reuse/substitute/harvest/configure -> verify exact Brain-owned route >= bar -> save permanently -> regression-protect`

External models/services may be capability specimens. White-box systems may be donors. Neither counts as Brain ownership while the external provider remains the operative target-capability implementation.

Underlying useful capability invention is forbidden by the current mission lock. Allowed creation is integration, extraction/minimization tooling, configuration, packaging, routing, persistence, verification, recovery, and adapters that encode already-existing capability mechanisms.

## Active terminal objective

Terminal target:

`OPUS_5_5_USEFUL_CAPABILITY_OWNERSHIP_V1`

Brain must permanently internalize, configure, verify, and own all useful Claude Opus 5.5 capabilities at equal-or-better useful performance, while keeping knowledge external/JIT.

Authoritative mission lock:
- `canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V7.md`

Active capability strategy:
- `canonical/laws/CAPABILITY_INTERNALIZATION_ARBITRAGE_STRATEGY_V7.md`

Canonical capability queue:
- `canonical/capabilities/FRONTIER_CAPABILITY_OBSOLESCENCE_QUEUE_V1.json`

Current terminal truth and next scheduling action:
- `canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json`

Mandatory fail-closed action gates:
- `canonical/gates/GOAL_HIERARCHY_ACTION_GATE_V8.json`
- `canonical/gates/CRITICAL_PATH_PRE_ACTION_GATE_V9.json`

## Active acquisition order

Apply the deletion-first order encoded by the current gates and strategy:

1. delete unnecessary capability demand;
2. bypass it when the same terminal effect can be obtained without it;
3. reuse already-owned Brain capability;
4. substitute deterministic/software/open existing mechanisms;
5. white-box harvest only a residual already-existing learned mechanism when needed;
6. compose existing mechanisms;
7. configure and integrate the surviving route;
8. verify the exact Brain-owned route at or above the Opus 5.5 bar;
9. save the winning capability package and regression evidence permanently.

Opaque external models/services can establish the bar or act as specimens, but cannot receive ownership credit.

## Progress metric

Primary:

`verified Brain-owned useful capability strength / wall-clock time / incremental cost`

subject to:
1. correctness;
2. capability >= Opus 5.5;
3. permanent Brain ownership;
4. donor independence when harvesting is used;
5. minimum wall-clock;
6. hard $0 incremental spend;
7. minimum compute and complexity.

Capability count, parameter count, benchmark count, worker count, infrastructure count, and scheduling activity are not progress by themselves.

## Current-work discipline

- Refresh live canonical state before consequential reasoning.
- Do not schedule from stale summaries.
- Use current content-addressed evidence before acquiring new reality.
- Do not consume fresh terminal evidence without explicit authority.
- Recompute the minimum causal/proof cut after every verified delta.
- Preserve contamination boundaries and untouched qualification populations.
- Fail closed on unresolved contradictions.
- Do not duplicate an already-open blocker lease or equivalent work intent.

## Relationship to Superworkers

The verified Superworker is execution substrate, not the terminal product.

Persistence, clean-room reproduction, recovery, provenance, independent verification, and provider replaceability remain mandatory, but they serve the terminal capability-ownership mission.

## Non-negotiable law

Provider loss, suspension, deletion, outage, or account failure must not destroy canonical truth or prevent reconstruction.

No execution provider is canonical. Provider-specific execution is replaceable substrate only.
