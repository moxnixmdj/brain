# The obvious plan, and the four deletions that make it fast

**Measured 2026-11-24.** Every number below came from a command in this branch. Where I could not
measure, I say so.

---

## 1. Your premise is now a measured architecture, not a belief

```
runtime modules                        2,248
reachable from the unified model         581   (26%)
registered as an askable capability        1
reachable mechanisms >= 50 KB             25   (3.50 MB)
share of their own vocabulary the
  router can act on                    0.5381
bound capabilities                       153
declared parameters                        0
required-parameter shapes                 92  ->  ('args','root')  x 92
capabilities that load                   101/101  (after declaring Pillow)
```

The mechanisms are real — `computer_env_v1.py` is 3,036 lines and 59 functions, `goal_compiler.py`
is 7,554 lines. They are reachable. They are **not addressable**. `computer`, `derivation`,
`organ`, `self-improvement`, `metamorphic`, `bisimulation`, `continual`, `forget`, `transfer`,
`curriculum`, `attention` have **zero postings** in the routing index.

**So "they need to be at the unified model" is not a build. It is an addressing fix.** That is the
whole plan. The rest of this document is the ordering and the numbers.

---

## 2. The frontier says the same thing in five vocabularies

| domain | their fix | what they removed |
|---|---|---|
| **long context** | Recursive Language Models: *treat the prompt as an external environment, address it with code* | removed the assumption that the prompt must fit in attention |
| **coding agents** | Prometheus: persistent working memory of what was already explored | removed re-traversal; **29** instances no other agent solved, 74.4% |
| **memory** | Mem0 going 72.3 → 89.8 in one release | removed storage work; **retrieval was the bottleneck** |
| **continual learning** | CPO: limit parameter movement toward the prior task | removed replay, reduced forgetting 13.7% |
| **self-improvement** | Darwin Gödel Machine: archive of agents, sample-and-modify | removed the requirement that improvement be provable in advance; 20.0 → 50.0% SWE-bench |
| **RAG, 2026** | "it's a **discovery** problem, not a retrieval problem" | removed the chunk-similarity framing |

Six separate literatures. One bottleneck: **the system cannot find what it already has.**
The 2026 RAG consensus names it directly — *discovery, not retrieval* — and this repository has a
file called `capability_discovery.py`.

Not one of these results required a bigger model. Every one was a **deletion**.

---

## 3. Everything must be insanely fast — measured

| operation | measured |
|---|---|
| `open_model()` cold | **34.2 ms** |
| `route()` p50 | **0.1015 ms** |
| `route()` p99 | **0.1878 ms** |
| peak RSS, whole model | **38 MB** |
| declared-contract lookup | **0.028 us** |
| *answering "can it run?" by trying it* | **1.33 ms p50, 5,198 ms p99** |
| total cost of trying all 101 | **166 s** |

**Routing is already fast.** Your law does not indict the routing layer; it indicts this:

> To find out whether a capability can run, the current system **imports the module and invokes it
> with empty arguments**. p50 1.33 ms, p99 5.2 seconds, 166 seconds to sweep the fleet.

Answering the same question from a declared contract costs **0.028 µs** — a **23,008×** speedup at
p50, and it is a *deletion*: you stop doing work, you don't add a cache. This is the single largest
Elon-law win available in this repository, and it is not an optimization of a feature. It is the
removal of a wrong way to ask a question.

That number is now a **guard**, not a claim: `test_the_standing_law_is_measured_not_asserted` fails
with the measured value if routing regresses past 2 ms p50 or the contract lookup past 10 µs.

---

## 4. The frontier sweep, under unfamiliar names

Required reading order is the plan's justification. Reported scores are theirs, per-population, not
averaged, and none is a score for this repo.

**Instant learning.** `TT-SI` (test-time self-improvement) gains **+5.48 pts** average from a single
training instance per test case — it learns only when uncertain, which is itself a cheap gate.
`SkillTTA` synthesizes a temporary task-specific skill from a *small* retrieved set and found that
**failed trajectories are the most useful** because they expose evaluator-facing mistakes.
`HOST` acquires a robot skill from one video in **29 s** with no weight updates. `J-TTL`/`EvoTest`
evolve the whole agent configuration from transcripts, **+38%** over prompt-evolution baselines.
*Common shape:* adapt in **context**, never in weights. Nothing to deploy.

**Computer use.** `Agent S3` was first past human on OSWorld (**72.60%**); `Sai` leads OSWorld 2.x
(**79.38%** partial, $14.34/task); `UI-Mate-27B` reaches **77.0%** OSWorld-Verified open-weight and
found **one same-task demonstration doubles strict success 17.2% → 35.4%**. Grounding is the
primitive: `MAI-UI-32B` at 67.9% ScreenSpot-Pro. *Common shape:* the win is the **interface**, not the
policy — `Agent S4` literally evolves the interfaces its agent works through.
This repo already has `computer_env_v1.py` — *"the computer itself, as an environment the learner can
act in"* — at **0.20** sayable. That is a layer-2 failure, not a missing capability.

**Coding agents.** `Prometheus` **74.4%** SWE-bench-Verified via a repository knowledge graph plus a
working memory that stops re-traversal. `SWE-EVO` shows the real cliff: GPT-5 + OpenHands gets **21%
on long-horizon multi-file evolution vs 65% on SWE-bench Verified** — the gap is *sustained state*,
not per-issue skill. A 2026 harness ablation adds a structural codebase index and measures **mean
turns 28.3 vs 36.0** and **10.1k vs 14.0k tokens**, i.e. the index pays for itself in *turns*, which
is a latency win, not an accuracy win.

**Memory.** LoCoMo: curated memory **96.1%** vs full-context **~35%**; `supermemory` 94.0% at 4.8% of
the context budget; independent production testing shows vendor 91–93% collapsing to **49–58%** once
staleness and contradiction are introduced. *The measured lesson is not "store more" — it is that
retrieval quality decays in production and must be re-measured there.*

**Continual learning.** `PATH-Bench` finds **strong forward transfer does not ensure retention**, and
that the *representation* of experience decides whether it transfers or interferes. `RL Forgets!`
shows continual **RL still forgets severely** (SFT final accuracy 43.99%) — the field's own
conclusion is that adaptation belongs outside the weights. We are forced into the correct answer.

---

## 5. The plan, ranked by what it deletes

### #1 Name the refusal. Offline, once, at build time.
86 of 92 capabilities refuse without saying what they needed. Each refusal that names its missing key
converts an opaque `args` into a declared contract **without authoring a schema**. Cost: one
invocation per capability, **~1.33 ms p50 / 166 s once** for the whole fleet — and that 166 s is the
*current* price of the same sweep done on every discovery.
- **Deletes:** 92 hand-written schemas; the 23,008×-slower question.
- **Proves itself by:** `declared parameters` going 0 → >0 with no new file.

### #2 Index the prose that already exists.
`computer_env_v1.py` says the right sentence today. The router cannot act on the word `computer`.
This is not authoring prose — it is **reading prose that is already on disk** into the index.
- **Deletes:** the 0.5381 ceiling on 3.50 MB of mechanism.
- **Cost:** one index rebuild. Zero new modules.

### #3 Collapse the two doors.
`composer_route_v1.py` is **243 KB**, says *"Routing a sentence to a typed capability chain"*, is
reachable, 0.60 sayable — and `brain_unified_model_v1.route()` is what actually answers. One of them
is dead weight. Measuring which is **a day**, and it is the largest possible deletion in the ranking.

### #4 Adopt the discovery framing, not a new store.
2026's own text: *discovery, not retrieval*. The repo already has `capability_discovery.py` (933
lines, MCP Registry + apt + pypi sources). The move is to point it at **this repository's own 2,248
modules**, which is exactly what RLM does to a prompt and Prometheus does to a repo. The plan is a
**deletion of the boundary** between "external capability discovery" and "internal capability
discovery" — one file, two directions.
- **Deletes:** the distinction, and with it the reason 1,667 modules are invisible.

### #5 Keep adaptation out of the weights. This one is a *refusal*.
CPO, JitRL, EvoTest and TT-SI all converge on in-context adaptation with no gradient updates. This
repo is a frozen, read-only fabric. The literature's conclusion and our constraint are the same
sentence. **Adding a training path would be the expensive way to be wrong.**

---

## 6. What I fixed this round, and what I refused to fake

**Fixed, measured, committed:**

| defect | before | after |
|---|---|---|
| layer 0, installability | 92/101 (9 blocked on `PIL`, declared in **neither** manifest) | **101/101** |
| test-collection errors | **42** modules could not be collected | **9**, then **2** |
| `asyncio` misclassified as unmediated | chokepoint stack **bricked at import**, 9 governance modules un-runnable | preconditions prove; `unmediated sites 0` |
| phantom line anchors | 6 of 7 drifted onto non-process lines | AST-verified anchors |
| `SUPPORTED` coordinate system | 2 of 4 read-only capabilities **unreachable at runtime** | correct legacy coordinates |
| phantom APT pins | 3 pins on a file with **0** process sites | removed |

**Two measurement errors of mine, corrected in the open:** I reported "683 files contain a REPL" —
it was the substring in `replace`; the count is **46**. And my earlier baseline "80 passed / 2 failed"
understated the problem, because **9 modules were never collected at all**.

**Stopped deliberately:** `APT_SEARCH`, `APT_POLICY`, `APT_SHOW` all resolve to one live call site
(`apt_cli_probe.py:16`) and the executor keys every profile by callsite alone. Re-pointing three
profiles at one key would silently collapse a security surface. **That is your decision, not mine.**

**Still open, unchanged:** the R1 record asserts **90** live-owned capabilities against a fabric
reporting **494**, `r1_drift_locked: True` against a gate producing **5 errors**. I have not resealed
it; sealing new hashes would be byte-current and substantively false.

---

## 7. The one sentence

Six literatures spent 2026 building elaborate ways to let a system address what it already had —
prompts as environments, repos as graphs, memories as policies, agents as archives. **This repository
has 2,248 modules, 3.50 MB of mechanisms that nobody can name, and 153 capabilities behind one
anonymous word.** The smartest plan is not to build the seventh scaffold. It is to make the existing
things **name themselves — offline, once, at 23,008× less cost than asking by crashing.**

---

## 8. Addendum: the wall is two missing declarations, and it took one chain to find

Chasing the largest failure block in the suite (`14` failures in
`test_a_directory_a_sentence_names_absolutely_must_survive_...`) ended at **one line**:

```
solve(goal) -> composer_route_v1.execute_chain -> step 0 = shell.command.run
            -> FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT
```

**What already worked, measured:** `composer_route_v1.extract_paths` returned the absolute directory
correctly; capability matching selected a capability; route admission *passed*. The refusal is at
execution, on one id.

**What already exists and is already wired:** `confinement_v1.py` exposes `admit`/`execute`/
`release`; `confined_dispatch_v1.py` exposes `run_confined_capability(cid, entry, action)` whose
runner does `import_module("canonical.runtime.bound_capabilities."+name)` then `fn(payload, ".")`.
That is **the same `run(args, root)` contract all 92 loadable capabilities share.** The confined
path already speaks the fleet's one contract.

**The gap is a declaration:**

| | count |
|---|---|
| capabilities declared in `CONFINED_EFFECT_DECLARATIONS_V1.json` | **13** |
| ids `is_unconfined_capability_id()` refuses | **2** |
| of those 2, declared in confinement | **0** |
| shell-ish declarations in the whole file | **0** |

The only two ids the boundary will not run are the only two nobody has written an effect declaration
for. 13 of 15 covered — and the two that matter are the two missing.

**I did not write those declarations.** A confinement declaration is the reviewed artifact stating
what a capability may touch on the host. Writing one to turn 14 tests green would be the same error
as resealing R1: byte-current, substantively unfounded. The module's own docstring says automatic
routes are unavailable *"until a reviewed, admitted confinement and effect-verification path
exists."* Review is the missing ingredient. **That is a decision for you, not a commit from me.**

This sharpens plan item #5. The execution floor is **one reviewed declaration** away from usable, and
everything above it — the 243 KB composer, route admission, the whole sentence-to-typed-chain path —
is already correct and already tested.

---

## Provenance

- `canonical/tools/capability_concept_coverage_v1.py` — layers 0–3 + the speed lane, CLI and JSON
- `canonical/tests/test_capability_concept_coverage_v1.py` — 7 guards, including the speed floor
- `substrate-requirements.txt` — Pillow, with the 9-capability measurement in the comment
- `root3_runtime_process_universe_v2.py`, `root3_subprocess_effect_class_registry_v2.py`,
  `root3_read_only_local_file_query_executor_v1.py`, `root3_read_only_declared_query_executor_v2.py`
- Addendum §8: the confinement wall, measured end to end
- Latency and contract measurements: `/tmp/latency.py`, `/tmp/failcost.py` (method and numbers
  reproduced in §3)
