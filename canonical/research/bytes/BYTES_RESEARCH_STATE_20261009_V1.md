# BYTES RESEARCH — CANONICAL RESEARCH STATE V1

Status: RESEARCH EVIDENCE / ZERO CAPABILITY CREDIT / ZERO FAMILY CREDIT

Date: 2026-10-09
Branch base: `461c30bde072db63b946b4671e61eafaaa3c8276`
Scope: Bytes research after parameter obsolescence. This is NOT the older Sub-Agent causal Bits scheduler branch.

## Mission lock

After knowledge/parameter warehouse reconstruction was rejected in favor of JIT knowledge, the remaining question is:

> What is the minimum persistent information Brain must permanently own to realize the complete required capability envelope, subject to correctness, donor independence, latency, memory, reliability, verification, legal/provenance and zero-incremental-spend constraints?

The target is not "compress a model." A frontier/open model or software package is a temporary white-box donor. Brain should retain only the smallest sufficient causal mechanism, in whatever representation wins.

Existing canonical authority remains:
- `canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V7.md`
- `canonical/laws/WHITE_BOX_CAPABILITY_HARVESTING_LAW_V1.md`
- `canonical/governance/WHITE_BOX_CAPABILITY_CAPSULE_SCHEMA_V1.json`
- `canonical/capabilities/opus55/ATOMIC_CAUSAL_INTELLIGENCE_MAP_V1.json`

This research does not modify their authority or increase capability credit.

## Core formalization

For a fixed already-owned Brain substrate S and required capability set C, the correct object is a resource-bounded conditional executable description:

```
B*_R(C | S) =
  minimum unique persistent representation size
  subject to:
    every required capability contract passes,
    exact Brain route >= required frontier bar,
    donor deletion,
    held-out generalization,
    non-interference,
    legal/provenance constraints,
    runtime latency <= bound,
    memory/compute <= bound,
    reliability >= bound.
```

Raw Kolmogorov-smallest description is not the terminal objective because an absurdly small program may regenerate a gigantic system using unacceptable compute. The search is resource-bounded.

For multiple capabilities, optimize the joint dependency closure rather than independently minimizing each capsule:

```
B_terminal(C | S) = | unique content-addressed closure(S + selected mechanisms) | - | unique closure(S) |
```

This naturally counts shared mechanisms once.

Two quantities must remain separate:
- marginal bytes for capability i: ΔB_i = B(C_1..C_i) - B(C_1..C_{i-1})
- terminal bytes: B(C_1..C_n)

Acquisition order can change marginal bytes. It cannot change the terminal union.

## Byte accounting

Do NOT use:
- parameter count alone;
- adapter-local size with hidden base model omitted;
- repository size;
- logical path size with duplicate blobs double-counted;
- pretty-printed source bytes as if syntax redundancy were capability information.

Count:
- all unavoidable capability-bearing learned and deterministic artifacts;
- masks/indices/routing tables/decoder information;
- unavoidable shared base/substrate dependencies that actually carry target capability;
- configuration required to reproduce the behavior;
- executable decompressor/loader cost when not already fixed substrate.

Track separately:
- B_exec: persistent execution bytes;
- B_verify: online verifier bytes required for autonomous correctness;
- B_proof: provenance/receipts/history, not cognition;
- B_JIT: transient task knowledge, not persistent capability storage.

Lossless compression is allowed as a physical representation optimization, but decompression time/memory remain resource constraints.

## Capability-bearing dependency test

A dependency is not free merely because it is called a library, runtime, base model, framework or substrate.

Ask:
> If the dependency were replaced by a generic implementation that preserves ordinary computation but removes the target behavior, would the capability disappear?

If yes, the dependency is capability-bearing and belongs in the byte closure unless its mechanism is harvested/replaced.

## Elicit-before-teach

Before adding learned bytes:
1. test zero-byte composition of already-owned mechanisms;
2. test tiny configuration/routing/activation keys;
3. test sparse or low-rank residuals;
4. only then teach/harvest a larger residual.

Recent EDL-style results are useful as a search signal for "latent/elicited versus genuinely taught" capability. EDL is NOT a proof of deployed minimum bytes.

## Global minimum mechanism cover

Represent each verified mechanism as:
- atomic behaviors covered;
- dependencies;
- persistent bytes;
- latency;
- RAM/compute;
- reliability;
- legal/provenance constraints.

Then solve a minimum-weight dependency-aware hypergraph/set-cover problem over the known mechanism library.

This can provide an exact optimum over the finite set of mechanisms Brain has actually discovered, without pretending to prove the universal Kolmogorov minimum.

## Counterexample-guided byte minimization

Preferred loop:
1. start from the smallest candidate representation;
2. run held-out/adversarial verifier;
3. obtain the first counterexample;
4. add only the missing causal mechanism;
5. re-minimize all bytes;
6. independently falsify again.

For taught agentic behavior, prefer correcting the earliest irreducible failure rather than distilling entire donor trajectories.

## Joint factoring

Do not assume one generic cognition kernel. Brain already falsified that simplistic hypothesis in adjacent work.

Instead, after multiple capsules exist, empirically factor common substrate S plus residuals r_i:

```
min |S| + Σ|r_i|
```

subject to every capability remaining re-executable and verified.

Heterogeneous shared primitives are allowed. Reality, not architecture aesthetics, decides.

## Canonical Brain observations made during this research

At the live canonical state inspected during this session:
- white-box harvesting remained mandatory;
- whole-model adoption default remained forbidden;
- neural parameter retention required residual necessity;
- donor deletion remained required for promotion;
- the atomic causal map already treated family labels as evaluation surfaces, not internal modules;
- several capability families had already been dependency-compressed into shared S0/G0-style dependencies rather than independent learned modules.

A repository census was performed at historical tree `5ea2095f25a42f03544f782798577f4fe74054fa`:
- repository logical blobs: 10,249 files / 115,819,722 bytes;
- `canonical/capabilities/internalized/`: 209 files / 1,293,871 path-bytes;
- unique content-addressed bytes under that directory: 1,248,496;
- duplicate path overcount: 45,375 bytes;
- professional_work: 608,669 bytes;
- software_engineering: 572,272 bytes;
- causal_falsification: 78,705 bytes;
- artifact_creation: 34,225 bytes.

This demonstrated why repository bytes, internalized-candidate bytes and verified capability bytes are different quantities.

## Existing-package observations

### mini-SWE

The minimal mini-SWE internalization package was measured at 54,910 stored path-bytes.

Its manifest named only a much smaller operative root set. A first directly reachable source/config slice measured about 30,116 bytes, but external Python dependencies and dynamically referenced model adapters mean this is not a full executable dependency closure.

Conclusion:
- do not count the package size as irreducible capability;
- do not count the 30,116-byte local slice as complete dependency cost;
- source/package dependencies must pass the capability-bearing dependency test.

### Verified-owned route sharing

The Instruction Following ownership proof named a 21-file operative closure totaling 180,309 bytes at the inspected revision.

`canonical/runtime/tool_discovery_information_safe_candidate.py` was both:
- the owned Tool Discovery mechanism; and
- part of the Instruction Following closure.

This is direct evidence that joint factoring is real, not hypothetical.

## Exact-symbolic donor slicing experiment

Target donor:
- SymPy 1.14.0
- mpmath dependency
- Brain's bounded exact-symbolic capability represented by the existing exact-symbolic suite plus generated class-level variants.

Critical doctrine:
- no homemade CAS is promoted;
- underlying-capability invention remains forbidden;
- only donor-derived specialization/deletion/repackaging is a candidate route.

### Early experiment

The unmodified donor source footprint was roughly 28.1 MB of SymPy+mpmath Python source.

Initial normal execution of the frozen 12-task suite loaded about 10.42 MB of source.

Major false dependencies discovered included broad package facades and type-support branches for:
- plotting;
- geometry;
- physics/units;
- tensor algebra;
- combinatorics/permutation groups;
- generic printing/codegen;
- generic solver families;
- generic integration;
- matrix-expression algebra;
- test/development files;
- public API exports unrelated to the target contract.

### Accepted deletion/specialization progression

Observed checkpoints in this session included:

1. Whole-domain deletion wave:
   - ~4.65 MB installed bytes removed;
   - frozen 12/12 retained;
   - 409/409 generated class-level variants retained.

2. Test/development source removal:
   - SymPy Python source reduced from ~26.17 MB to ~12.36 MB;
   - frozen 12/12 + 409/409 retained.

3. Joint SymPy+mpmath calibration closure:
   - about 11.14 MB source;
   - frozen + generated verification retained.

4. Narrow printing facade:
   - removed roughly 547 KB of loaded source.

5. Narrow solver facade:
   - solver load reduced from about 1.04 MB to ~0.394 MB.

6. Tensor/combinatorics cut:
   - scalar algebra no longer eagerly imported tensor/permutation-group machinery;
   - resulting physical capsule around 7.69 MB Python source;
   - fresh qualification retained.

7. Quintic constants:
   - ~96 KB constants module made lazy/removed because qualified root scope was <=4;
   - source reduced further.

8. Specialized integration:
   - qualified even-power sin integral branch routed through donor-derived specialized algorithm instead of generic integration engine;
   - generic solver dependency disappeared from that route;
   - physical capsule reached 7,044,219 Python-source bytes;
   - xz persistent representation at that checkpoint: 1,207,652 bytes.

9. Further donor-derived minification and dependency removal continued after the visible 1.21 MB checkpoint.

### Current strongest saved candidate: MINSRC2

The strongest reproducible donor-derived checkpoint found in the preserved workspace is `bytes_capsule_minsrc2`.

Measured:
- physical directory bytes: 3,756,874;
- files: 251;
- lossless xz capsule bytes: 220,640;
- xz SHA-256: `7f2442cb8b5545aac1a580eabbe3b936740bdeba066c6b590145c7be31d2848d`.

Frozen-suite recheck on 2026-10-09:
- DONE 12;
- loaded Python modules: 125;
- loaded source bytes: 1,420,386;
- loaded `sympy/polys/` bytes: 233,851;
- `sympy/polys/polytools.py` not loaded;
- trace SHA-256: `e9bea826a5f9b6d5c81acebb37d718b5a1b4171e16697824bd4ba3efbdf60e23`.

Fresh deterministic qualification:
- generator seed: 20261009175531;
- generated cases: 2,228;
- verifier recheck: PASS 2228 / 2228;
- case generator SHA-256: `7f25bc14e8704911c82fd71e5cbfb83c2d41f6f4620bfe1d7ee11c778f5efed7`;
- generated case corpus SHA-256: `4166f8333955a0cc92f43b573b2773ce3f27f0bdb9f3537379f184530251109f`;
- execution output SHA-256: `6a1af9ec627e229d75281be7de3fff2699e7a5c39a17c5841a8dd9d3b771f0ce`;
- verifier SHA-256: `98b31c50509de2d0827db02f76677a475e4808c38bf656d4cbdf8ffc7a14d2b8`.

The 2,228-case corpus covers:
- 120 rational sums;
- 220 linear-factor polynomial cases;
- 110 mixed quadratic/linear factor cases;
- x^n ± 1 factor cases for n=2..20;
- 300 coefficient cases;
- 300 rational-root degree <=4 cases;
- 170 nonsquare positive-discriminant quadratics;
- x^x, powers, exp-linear and sin-linear derivatives;
- 40 even-power sin integrals;
- random exact determinants up to 6x6 plus Hilbert n<=7;
- binomial-square identities;
- 100 sin(a*x)/x zero limits;
- 180 exact nonsingular 2x2 systems;
- 280 exp(a*x)sin(b*x) series-coefficient cases.

Important limitation:
This is strong research evidence, NOT a promoted replacement for the existing SymPy-owned exact-symbolic route. It has not yet passed the full independent canonical promotion protocol, license/provenance packaging, untouched final qualification and donor-deletion proof required by `WHITE_BOX_CAPABILITY_HARVESTING_LAW_V1`.

### Later exploratory variants

Post-MINSRC2 variants named `mulscalar1` and `scalarassoc1` were explored.

- `mulscalar1` replays the same 2,228-case fresh corpus successfully.
- `scalarassoc1` was slower during an immediate recheck and did not establish a smaller persistent representation before this save.
- Neither is promoted as a frontier improvement over MINSRC2 here.

Preserve them as evidence that further core scalar-operation surgery was being explored, but do not supersede MINSRC2 without an explicit byte/runtime win plus fresh qualification.

## Rejected or non-promotable experiments

### Standalone ~13 KB exact-symbolic kernel

A newly constructed standard-library kernel reached roughly 13.3 KB and passed 981 generated checks.

It is useful evidence that the behavioral description may be dramatically smaller than donor packaging.

It is NOT promotable under current Brain law because:
- it is underlying capability invention rather than clean donor harvesting/reuse;
- its larger untouched qualification did not complete within the execution window;
- it therefore cannot replace the donor-derived path.

### Generic-limit replacement

A narrow `as_leading_term`-style limit route was tested.

Result:
- no meaningful dependency-byte reduction;
- slower execution;
- rejected by the resource-bounded objective.

### Lazy simplify specialization

Lazy imports for exotic Bessel/gamma/tensor/matrix/integral branches preserved tests but did not reduce the actual loaded closure because other modules still imported the same tree.

Rejected as zero-byte-gain surgery.

### Verifier bug

One fresh-qualification script accidentally hard-coded the prior capsule path and therefore appeared to qualify a successor while actually retesting its parent.

That result was explicitly invalidated.

The correct successor was rerun against its actual bytes before any later claim was accepted.

This is a permanent regression lesson:
> every qualification receipt must bind the exact candidate content hash/path, not merely a test script name.

## Current Bytes frontier

MINSRC2 is the strongest saved donor-derived checkpoint in this research save:
- 220,640-byte xz physical payload;
- exact frozen 12-task execution retained;
- 2,228/2,228 fresh generated qualification pass;
- no promotion or family-credit change.

The next research target is the residual polynomial/core closure, especially:
- factor;
- coefficient;
- exact roots degree <=4;
- associated domain/core machinery.

Continue only with donor-derived specialization/deletion, preserving fail-closed rejection outside the contracted operation classes.

## Required promotion work before canonical capability replacement

Before replacing the existing full SymPy 1.14 route:

1. bind exact capsule payload hash;
2. preserve donor provenance and applicable licenses;
3. prove full dependency closure and absence of undeclared external target-capability providers;
4. freeze untouched final qualification tasks before any further tuning;
5. run independent verification;
6. prove donor deletion in a clean environment;
7. compare latency/memory/reliability against incumbent;
8. verify exact Brain route >= incumbent/frontier bar for the claimed scope;
9. only then update ownership routing.

Until then:
- research progress: YES;
- white-box candidate: YES;
- current exact-symbolic ownership replacement: NO;
- Opus/family credit delta: 0.

## Next action

Resume from MINSRC2, not from the old 1.21 MB checkpoint.

Highest-leverage target:
> minimize the remaining `polys` and core dependency closure for factor/coefficient/roots<=4 using donor-derived algorithms, while holding the 2,228-case corpus fixed as spent calibration and creating a new untouched qualification corpus for every subsequent candidate.

Do not reopen the old causal Bits scheduler branch.
