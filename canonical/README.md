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

## Core theory

Project Brain uses this operational decomposition:

`FRONTIER INTELLIGENCE = KNOWLEDGE + CAPABILITIES`

### Knowledge

The knowledge-side architecture is treated as solved for the current program unless falsified:

`need knowledge -> acquire the strongest relevant external/JIT knowledge -> verify -> preserve`

The project does not try to reproduce a frontier model's giant permanent knowledge warehouse inside another parameter store.

### Capabilities

Capabilities are now the active research frontier.

For each useful frontier capability:

`frontier capability -> define real useful effect -> establish frontier bar -> search/race all legitimate routes -> verify equal or better capability -> inherit winning route -> frontier implementation becomes unnecessary`

The objective is **not** to copy or accumulate the frontier capability inventory.

The objective is to obtain the **maximum useful capability, at least equal to the frontier bar, through the fastest and cheapest verified realizable route**.

## Active terminal objective

Systematically obsolete the useful capabilities of frontier models by finding verified equal-or-better capability routes with minimum wall-clock time and incremental cost.

Frontier models and agents are:
- sources of capability bars;
- challenge generators;
- optional capability suppliers.

They are not implementation blueprints or terminal architectures.

Authoritative goal:
- `canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_OBSOLESCENCE_MISSION_LOCK_V4.md`

Active execution strategy:
- `canonical/laws/CAPABILITY_OBSOLESCENCE_ARBITRAGE_STRATEGY_V2.md`

Canonical capability queue:
- `canonical/capabilities/FRONTIER_CAPABILITY_OBSOLESCENCE_QUEUE_V1.json`

## Active loop

1. recover and normalize the frontier capability surface;
2. choose the highest-leverage capability;
3. define its real useful behavior;
4. establish the strongest defensible frontier bar;
5. search the hidden warehouse;
6. race reuse, composition, JIT acquisition, deterministic/specialized systems, model suppliers, adaptation, and only then invention;
7. run consequential real work;
8. independently verify equal-or-better capability;
9. mark the frontier implementation obsolete or preserve the exact residual gap;
10. inherit the winner and repeat.

## Progress metric

Primary:

`verified useful capability strength / wall-clock time / incremental cost`

with correctness first and a hard $0 incremental-spend constraint unless the user changes it.

Capability count, parameter count, benchmark count, worker count, and infrastructure count are not progress by themselves.

## Relationship to Superworkers

The verified Superworker is the execution substrate for capability obsolescence, not the final product.

Clean-room reproduction, persistence, recovery, provenance, and verification remain mandatory architectural properties, but they are subordinate to the terminal capability-obsolescence mission.

## Non-negotiable law

Provider loss, suspension, deletion, outage, or account failure must not destroy canonical truth or prevent reconstruction.

No provider is canonical. Provider-specific execution is replaceable substrate only.
