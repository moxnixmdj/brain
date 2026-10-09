# BYTES RESEARCH — RESOURCE-BOUNDED CAPABILITY FOOTPRINT V1

Status: CANONICAL RESEARCH RECORD / ZERO CAPABILITY CREDIT / NOT A MANDATORY LAW  
Date: 2026-10-09  
Base commit: `10b69a7eff33780d6d6677144c6eca8af6151888`  
Authority-compatible with: `canonical/laws/WHITE_BOX_CAPABILITY_HARVESTING_LAW_V1.md`

## Mission lock

This research exists only to reduce the durable information footprint required for Brain to permanently own the useful Opus-5.5-or-better capability envelope.

It does **not** weaken the terminal objective, does **not** count external provider access as ownership, and does **not** grant capability credit from compression or interpretability work alone.

Knowledge remains external/JIT by default. Learned or software machinery is retained only when it is causally necessary for capability that Brain cannot already realize more cheaply and soundly.

## Correct problem

The target is not "compress a model."

The target is:

> Find the shortest resource-feasible executable description of the complete required capability set, conditional on everything Brain already owns, with all unavoidable dependencies counted and with the exact deployed route still meeting the required capability bar.

For a capability set \(\mathcal C\) and already-owned substrate \(S\):

```
B*_R(C | S) = minimum persistent description length of an executable mechanism set
              subject to:
              - every target capability remains >= required bar,
              - donor deletion holds,
              - held-out generalization holds,
              - interference constraints hold,
              - runtime/latency/memory/reliability bounds hold.
```

The unrestricted Kolmogorov minimum is not computable in general and is not the claim.

## Two byte quantities

Do not mix marginal acquisition cost with total terminal footprint.

```
DeltaB(C_i | S) = bytes added by C_i given the already-owned substrate S.

B_terminal(C_1...C_n) = unique persistent bytes required by the final complete capability substrate.
```

A capability may have near-zero marginal cost if its machinery is already shared. The shared machinery itself is not free.

## Count dependency closures, not advertised artifacts

A 2 MB adapter that requires a 40 GB base does not cost 2 MB.

For every promoted mechanism, count the complete unavoidable dependency closure:

```
B = B_values
  + B_indices_or_masks
  + B_router
  + B_decoder_or_loader
  + B_unavoidable_base
  + B_configuration
```

The correct terminal accounting is content-addressed and counts identical blobs once.

## Resource-bounded metric

Raw byte minimization is pathological because a tiny program could regenerate a huge mechanism using absurd computation.

Bytes therefore optimizes storage only under explicit execution constraints:

```
minimize persistent_bytes
subject to:
  capability >= frontier_bar
  latency <= allowed_latency
  peak_memory <= allowed_memory
  reliability >= required_reliability
  verification >= required_verification
```

A storage reduction that materially worsens the root objective can be rejected.

## Separate byte classes

At minimum record:

- `B_exec`: bytes necessary to perform the capability.
- `B_verify`: online verification machinery required for autonomous correctness.
- `B_proof`: historical receipts, traces, evidence, and adjudications.
- `B_JIT`: transient task knowledge.

`B_proof` belongs to governance/evidence storage, not to the cognitive execution footprint.  
`B_JIT` is knowledge traffic, not durable capability storage.

## Substitution lattice

Before neural or learned extraction, search in this order:

1. zero-new-byte composition of already-owned Brain mechanisms;
2. deterministic or symbolic existing mechanism;
3. small explicit configuration/routing policy;
4. sparse or low-rank residual on already-owned shared substrate;
5. compact specialized learned module;
6. donor circuit/expert/module subset;
7. larger learned mechanism only when lower classes falsify.

This operationalizes parameter obsolescence rather than merely saying it.

## Elicit-before-teach distinction

Session research identified a useful distinction from 2026 work on excess description length:

- when a capability is already latent in a substrate, very little new information may be sufficient to elicit it;
- when a capability must genuinely be taught, much more information may be needed.

Use this as a **search heuristic**, not as a proof of deployed byte lower bounds.

Search increasing information budgets:

```
0 bytes -> tiny key/router/policy -> sparse/low-rank delta -> compact module -> larger residual
```

Stop immediately when the exact Brain route passes the capability contract.

## Global joint factoring

Independent capsule minimization is not globally optimal.

If multiple capabilities share machinery, optimize:

```
minimum |shared substrate| + sum(|capability-specific residual_i|)
```

rather than the sum of independently minimized packages.

Brain's existing atomic causal intelligence map and dependency-compression work already support this interpretation: family labels are evaluation surfaces, while the internal unit is the smallest causally meaningful transformation.

## Minimum mechanism cover

Represent each candidate mechanism as:

```
m_j = {
  atomic_behaviors_covered,
  dependency_closure,
  unique_bytes,
  latency,
  memory,
  reliability,
  verification_status
}
```

Then solve a minimum-weight mechanism-cover / hypergraph problem over the currently discovered mechanism library, subject to compatibility and capability constraints.

This can yield an exact optimum **over the finite known candidate library** even though the universal information-theoretic optimum is uncomputable.

## Counterexample-guided byte minimization

Use a CEGIS-like loop:

1. start with the smallest candidate representation;
2. test protected/adversarial capability contracts;
3. obtain the smallest counterexample;
4. add only the mechanism required to close that witness;
5. reminimize the entire dependency closure;
6. repeat until the qualification/coverage criterion closes.

Do not preserve donor bulk pre-emptively.

## Four-way causal proof

Every retained learned or harvested mechanism should satisfy:

1. **Necessity**: ablation materially degrades the target behavior.
2. **Sufficiency**: restoration/transplant restores the target behavior.
3. **Specificity**: unrelated important behavior does not regress beyond tolerance.
4. **Donor independence**: donor and undeclared dependencies can be deleted.

A minimization certificate should additionally attempt removal/compression of every retained component and record the result.

## White-box donor interpretation

A model, library, framework, prompt pack, skill repository, and software package are all donors.

Historical packaging has zero authority over the final Brain footprint.

The general transformation is:

```
donor
 -> behavioral contract
 -> causal dependency closure
 -> delete everything else
 -> repair incidental coupling without widening the contract
 -> held-out verification
 -> donor deletion
 -> promote only exact surviving route
```

## Current canonical repository byte census

Measured on base commit `10b69a7eff33780d6d6677144c6eca8af6151888` / tree `a5a868fc987098b2adc756e5c53d774c42971fc3`:

- repository: 10,904 blobs, 122,169,704 logical bytes;
- `canonical/capabilities/internalized/`: 209 files, 1,293,871 logical bytes;
- unique Git blob bytes in that subtree: 1,248,496;
- duplicate path overcount: 45,375 bytes.

Internalized package logical bytes:
- professional_work: 608,669;
- software_engineering: 572,272;
- causal_falsification: 78,705;
- artifact_creation: 34,225.

This proves repository size is not capability size.

## Current ownership context

At the base commit the ownership matrix reports seven `VERIFIED_OWNED_EQUAL_OR_BETTER` families:

- EXACT_SYMBOLIC_COMPUTATION
- LONG_HORIZON_MEMORY_AND_CONTINUITY
- SELF_VERIFICATION_DEBUGGING_AND_RECOVERY
- SUBAGENT_DELEGATION_AND_COORDINATION
- TOOL_DISCOVERY_SELECTION_AND_LEARNING
- INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT
- COMPLEX_MULTI_TOOL_AGENCY

Bytes work must distinguish these from larger candidate/verification-pending packages. Candidate warehouse bytes do not automatically count as terminal capability bytes.

## Important discovered sharing

`canonical/runtime/tool_discovery_information_safe_candidate.py` is both the Tool Discovery operative mechanism and part of the Instruction Following operative closure.

Therefore acquisition-order marginal bytes differ from the order-independent terminal union.

This is direct evidence for joint dependency factoring.

## Scope of experimental exact-symbolic work

The session attacked the currently verified bounded `EXACT_SYMBOLIC_COMPUTATION` route because its SymPy dependency appears much larger than the directly named runtime code of several other owned families.

The canonical exact-symbolic contract remains exactly the bounded 12-operation suite already in Brain. No broader mathematics claim is implied.

Detailed experimental status is recorded in:
`canonical/reasoning/2026-10-09_BYTES_RESEARCH_EXPERIMENTAL_CHECKPOINT_V1.json`.

## External research references recorded during the session

These are literature leads supporting the research direction, not Brain capability evidence:

- Donoway et al., 2026, work on excess description length / latent-vs-taught capability information:
  https://proceedings.mlr.press/v306/donoway26a.html
- He et al., 2026, low-rank/shared task structure work:
  https://proceedings.mlr.press/v306/he26h.html
  https://proceedings.mlr.press/v306/he26f.html
- Shao et al., 2026, shared causal decoding subspace:
  https://proceedings.mlr.press/v306/shao26j.html
- Lyu et al., 2026, student-centered / earliest-error distillation:
  https://proceedings.mlr.press/v306/lyu26j.html
- Python dynamic debloating lead:
  https://arxiv.org/abs/2609.14040

Re-fetch and independently validate any literature claim before using it as consequential promotion evidence.

## Terminal research question

The Bytes frontier is:

> What is the minimum unique, compressed, resource-feasible dependency closure that implements the entire verified capability envelope, conditional on the already-owned Brain substrate, while preserving donor deletion and the exact acceptance bars?

No capability credit is granted by this document.
