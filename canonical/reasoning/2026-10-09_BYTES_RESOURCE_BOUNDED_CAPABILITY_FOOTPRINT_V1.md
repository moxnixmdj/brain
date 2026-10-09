# Bytes Research — Resource-Bounded Capability Footprint V1

Status: CANONICAL RESEARCH LEDGER / ZERO CAPABILITY CREDIT / FAIL-CLOSED
Date: 2026-10-09
Base main: 7891422979a25feeaffc72380676e239ee22bd46
Scope: Project Brain Bytes research after parameter-obsolescence. This is NOT Sub-Agent causal Bits research.

## Mission

After externalizing task knowledge JIT and deleting capability machinery already replaced by deterministic software, tools, memory, verification, retrieval, or existing Brain mechanisms, minimize the permanent Brain-owned representation required for the remaining useful capability envelope.

The target is not "compress a model." The target is the smallest resource-feasible, donor-independent executable description of required capability, conditional on the Brain substrate already owned.

## Core metric

For a required capability set C and fixed owned substrate S:

B*_R(C | S) = minimum unique persistent dependency-closure bytes of an executable mechanism set M

subject to:
- every required contracted behavior meets or exceeds its target bar;
- donor deletion holds;
- held-out qualification holds;
- non-target interference remains within limits;
- runtime latency, RAM, compute, and reliability constraints remain acceptable;
- hidden base models, adapters, masks, routers, decoders, runtimes, and other unavoidable dependencies are counted.

Two byte measures are mandatory:
1. Marginal bytes: Delta B_i = B(C_1..C_i) - B(C_1..C_{i-1})
2. Terminal bytes: B_terminal = unique content-addressed dependency closure for the whole required capability set.

Path size, parameter count, adapter size, repo size, and compressed archive size are diagnostics only.

## Accounting laws discovered in this research

1. Count dependency closure, not advertised artifact size.
A small adapter that requires a large base inherits the base as an unavoidable dependency unless that base is already fixed, owned substrate.

2. Count unique content-addressed bytes once.
Duplicate blobs across capability packages do not increase terminal capability bytes.

3. Separate:
- B_exec: bytes required to execute capability;
- B_verify: online verification bytes required by the route;
- B_proof: receipts/history/evidence retained for governance;
- B_JIT: transient task knowledge, not permanent capability storage.

4. Resource-bound the objective.
Raw shortest-description length is pathological if a tiny program regenerates a huge mechanism with absurd compute. Storage reduction is accepted only when latency, memory, reliability, and verification remain acceptable.

5. Candidate warehouse bytes are not owned capability bytes.
Internalized but unqualified/falsified packages stay outside terminal owned-capability accounting.

6. Elicit before teach.
Before retaining new learned machinery, test whether the behavior is already latent in an owned/shared substrate and can be activated by zero-byte composition, routing/configuration, a tiny control key, sparse delta, or small residual. Evidence from excess-description-length style research can guide this search, but does NOT prove runtime minimum bytes.

7. Joint optimization dominates independent capsule minimization.
Shared machinery must be factored globally:
B_terminal = B_shared + B_router + sum(B_true_residual_i)

8. Capability family labels are evaluation surfaces, not one-module-per-family architecture. Optimization operates on atomic causal transformations and verified mechanism coverage.

## Capability-to-Bytes compiler

Required search order:

RESIDUALIZE
-> atomic behavioral contract
-> zero-byte Brain composition
-> deterministic/symbolic/software substitute
-> elicitation/tiny-key search
-> sparse/low-rank/expert/module harvest
-> compact learned residual only when necessary
-> causal ablation/rescue/specificity
-> held-out qualification
-> donor deletion
-> cross-capability shared-substrate factoring
-> global minimum-byte mechanism cover
-> promotion only after exact Brain route verifies at the required bar.

For a finite discovered mechanism library, solve a minimum-weight dependency-aware set-cover / hypergraph problem over required atomic behaviors. Heuristics may propose mechanisms; exact or branch-and-bound optimization should certify the optimum over the known candidate set when feasible.

## Counterexample-guided minimization

Use the smallest current candidate. When an independent falsifier finds a failure witness, add only the minimum mechanism needed to close that witness, then re-minimize the entire dependency closure.

R_(t+1) = argmin_R |closure(R)| subject to passing all witnesses W_<=t and all protected qualification gates.

The stop claim is "byte-optimal within the certified candidate/representation envelope," never an unsupported absolute Kolmogorov minimum.

## Current canonical observations measured during this session

At inspected main state:
- repository tree: ~115.82 MB across 10,249 files;
- canonical/capabilities/internalized/: 1,293,871 logical path-bytes across 209 files;
- same internalized store by unique Git blob identity: 1,248,496 bytes;
- duplicate path overcount: 45,375 bytes;
- major internalized groups:
  - professional_work: 608,669 bytes;
  - software_engineering: 572,272 bytes;
  - causal_falsification: 78,705 bytes;
  - artifact_creation: 34,225 bytes.

Interpretation: repo size is not capability size. Governance, runtime, verification history, and candidate packages dominate storage differently from the actual promoted capability closure.

The ownership matrix inspected in-session reported seven VERIFIED_OWNED_EQUAL_OR_BETTER families at that state:
- EXACT_SYMBOLIC_COMPUTATION
- LONG_HORIZON_MEMORY_AND_CONTINUITY
- SELF_VERIFICATION_DEBUGGING_AND_RECOVERY
- SUBAGENT_DELEGATION_AND_COORDINATION
- TOOL_DISCOVERY_SELECTION_AND_LEARNING
- INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT
- COMPLEX_MULTI_TOOL_AGENCY

Do not infer current terminal completion from this list; later authority may supersede it.

Real sharing was observed: canonical/runtime/tool_discovery_information_safe_candidate.py is itself an owned Tool Discovery mechanism and also appears inside the Instruction Following exact operative closure. This proves acquisition-order-dependent marginal bytes and supports joint terminal factoring.

## SymPy white-box donor experiment

Purpose: test dependency obsolescence on an already verified deterministic capability rather than speculate about neural compression.

Target contract: bounded exact symbolic computation represented by the existing frozen Brain suite:
- exact rational sum
- polynomial factor
- coefficient extraction
- exact roots for exercised low-degree classes
- symbolic differentiation
- bounded definite integration class
- Hilbert determinant
- binomial-square sum
- sin(x)/x-style limit class
- exact small linear systems
- series coefficient

Method used in-session:
- treat SymPy 1.14.0 + mpmath as temporary white-box donors;
- identify broad public-facade and optional-type coupling;
- delete only branches outside the declared contract;
- preserve donor-derived specialized procedures where possible;
- rerun calibration and fresh post-freeze generated variants after accepted cuts;
- reject cuts with no byte gain or unacceptable runtime cost.

Accepted experimental observations reported during this session:
- baseline donor Python-source footprint used for comparison: ~28.10 MB SymPy + mpmath;
- earlier donor-derived joint slice: ~9.93 MB source;
- later physical capsule: 7,691,851 Python-source bytes after tensor/combinatorics deletion;
- quintic constants branch deletion: -96,031 bytes for current <=4 root scope;
- generic integration replaced for the contracted even-sin-power [0, pi] class with donor-derived specialized _sin_pow_integrate path;
- best reported physical donor-derived capsule: 7,044,219 Python-source bytes;
- best reported xz persistent archive: 1,207,652 bytes;
- best reported physical capsule qualification: 397/397 calibration plus 1,854/1,854 fresh post-freeze cases;
- other fresh post-freeze runs reported in the same line included 1,824, 1,902, 1,914, 1,920, 1,934-case passes on intermediate accepted states;
- a narrow generic-limit replacement was REJECTED because it produced no meaningful dependency-byte reduction and worsened runtime.

Important truth boundary:
THE TEMPORARY EXPERIMENTAL CAPSULES, GENERATED QUALIFICATION CORPORA, TRACE OUTPUTS, AND HASHED RECEIPTS FROM THIS CHAT WERE NOT PERSISTED INTO THE CANONICAL REPOSITORY BEFORE THIS ledger was written. Therefore all numeric SymPy slicing results above are SESSION-REPORTED RESEARCH EVIDENCE ONLY, NOT REPRODUCIBLE CANONICAL PROOF, NOT PROMOTION EVIDENCE, AND ZERO CAPABILITY CREDIT. They must be independently reconstructed or recovered before any canonical capability/minimum-byte claim relies on them.

## Rejected / non-promotable route

A ~13.3 KB standalone exact-symbolic standard-library kernel was reported to pass 981 generated checks and avoid SymPy/mpmath, but:
- it was newly constructed rather than harvested from an existing donor;
- a broader untouched holdout did not complete inside the execution window;
- current Brain law forbids treating newly invented underlying capability as the promoted solution.

Disposition: retain only as an existence/research hint. ZERO capability credit.

## Important negative results

- Dynamic execution trace alone is insufficient for general operation-class slicing.
- Plain source byte count is not the terminal persistent metric because lossless compression removes syntax redundancy.
- Plain compressed archive size is also insufficient unless decoder/runtime costs are included.
- EDL/learned-information estimates are not lower bounds on deployed runtime bytes.
- A smaller mechanism that materially worsens wall-clock time can lose under the resource-bounded objective.
- Interpretability features/circuits without a donor-independent operative route provide zero capability ownership.

## Current Bytes frontier

Highest-value next work:
1. Reconstruct the SymPy white-box experiment reproducibly from exact donor version and exact Brain frozen contract.
2. Freeze a protected hidden qualification generator/corpus BEFORE new pruning.
3. Reproduce accepted donor deletions and persist hashes/trace/qualification receipts.
4. Attack the current largest residual dependency concentration: sympy.polys.
5. Preserve only donor-derived factor/coefficient/low-degree-root machinery required by the qualified contract; keep everything else fail-closed.
6. Recompute unique compressed dependency closure, latency, RAM, and qualification.
7. Only after exact reproducibility may a harvested capsule enter the canonical white-box promotion pipeline.
8. Apply the same dependency-obsolescence compiler to larger capability packages and eventually learned donors.

## Research conclusion

The strongest current hypothesis is:

frontier capability packaging >> irreducible causal capability information.

But this is a hypothesis to keep falsifying, not a theorem.

Bytes research should optimize:
one minimum shared capability basis
+ tiny true residuals
+ JIT knowledge
+ explicit verification
while preserving real capability, latency, reliability, donor independence, and provenance.

No capability credit changes from this ledger.
