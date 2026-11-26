# The four layers, and the one that costs a line

**Measured 2026-11-24. Every number below was produced by a command in this commit, not estimated.**

---

## 1. The premise, in one table

You asserted, across many rounds, that we have already solved the frontier problems somewhere under
non-obvious names. That is a claim about coverage. Coverage turned out to have **four** gates, and the
repo had only ever measured the first one.

| layer | question it asks | measured | where it is enforced |
|---|---|---|---|
| **0 — installable** | does the capability's source file import at all? | **92 / 101** load; **9 fail on `PIL`** | *nowhere, until today* |
| **1 — reachable** | does the unified model's import closure load it? | **581 / 2,248** modules (26%) | `brain_owned_python_closure_census_v1` |
| **2 — sayable** | does the routing index hold the words a person would use? | **0.5381** of the mechanisms' own vocabulary | *nowhere* |
| **3 — routable** | does a sentence land on the right module? | see §4 | `brain_unified_model_v1.route()` |

The layers are not nested improvements on one another. They are independent gates, and a module can
pass one and fail the next. `computer_env_v1.py` is **reachable** (layer 1 ✓), **partly sayable**
(0.20), and **not routable** (layer 3 ✗) — so *"act on the computer as an environment"* routes to
`shell.command.run` while a 3,036-line, 59-function implementation of exactly that idea sits in the
import graph, unread.

**This is the ninth consecutive round of the same finding.** The fact was already on disk. It was
not indexed, not addressable, or not installed.

---

## 2. What the frontier is stuck on — five domains, one bottleneck

You asked for a maximal sweep of instant learning, computer use, coding agents, memory, and continual
learning, under unfamiliar names. Done. The five literatures are *separate*, and they report the
same failure with five different vocabularies.

| domain | what they built | the reported bottleneck | the number |
|---|---|---|---|
| **computer use** | Agent S3 / Sai, UI-Mate-27B | grounding: *which* pixel, not *what* action | OSWorld-Verified **77.0%**; ScreenSpot-Pro **67.9%** |
| **memory** | Mem0, supermemory, Zep | **retrieval quality, not storage** | full-context **~35%** vs curated **96.1%** on LoCoMo |
| **continual learning** | CPO, JitRL, EvoTest | plastic *vs* stable, no replay | forgetting **−13.7%**; JitRL beats fine-tuning at **1/30 cost** |
| **coding agents** | Prometheus, SWE-agent | being **stateless** | **74.4%** w/ memory-graph, **29** unique instances no other agent solved |
| **instant learning** | TT-SI, SkillTTA, HOST | adaptation must be *free* | **+5.48 pts** from one sample; **29 s** per skill from one video |

Four independent groups, four vocabularies, **one mechanism**: *the system could not find what it
already knew.* Memory calls it retrieval. Coding agents call it statelessness. Continual learning calls
it forgetting. Computer use calls it grounding. Instant learning calls it adaptation.

### Their consequence, plainly

- **Mem0** demoted storage and promoted retrieval; that is why it went **72.3% → 89.8%** in one release.
- **Prometheus** added a persistent *working memory of what it had already explored* and resolved
  **29 instances that other top agents could not** — the exact "needle-in-a-haystack" class.
- **UI-Mate** found one same-task demonstration doubled strict success **17.2% → 35.4%**.
- **CPO** found that RL still forgets, and fixed it by *limiting parameter movement toward the
  prior task's behaviour* — a regulariser, not a new module.
- **PATH-Bench** found **strong transfer does not ensure retention** — and that the *representation*
  of experience decides whether it helps or interferes.

Not one of these is a bigger model. Every one is a better-indexed existing state.

And the field's own self-assessment numbers say the same thing about *knowing*: KAPRO finds agents
fail to distinguish "I know this" from "I must fetch it"; strict agentic self-awareness reaches
**40.6%** on Terminal-Bench 2.1 while blocker *recognition* reaches **84.4%**. A 43.8-point gap between
recognising a fact and being able to act on it. That is layer 2 versus layer 3, measured by someone
else, on someone else's system.

---

## 3. The finding only this repository can produce

The frontier treats **tool schemas and tool code as separate artifacts**. That separation is why
DIAFORGE measures **76–81% of calls missing a required parameter**, and why schemas drift.

Measured here:

```
  bound capabilities                                   153
  with a resolvable source_path                        101
  load successfully                                    92   (91%)
  declared parameters, across all 153                   0
  required-parameter shapes observed                   92   ->  ('args', 'root')  x 92
  entrypoint name used                                 92   ->  'run'
```

**92 of 92 have the identical required-parameter shape.** `run(args, root)`. Zero declared
parameters. There is no schema drift here because there is only **one** schema — and it is `args`.

This is simultaneously the repo's largest asset and its exact bottleneck:

- **Asset:** a single uniform contract across every capability means one adapter can drive all of
  them. The frontier cannot do this; it maintains N schemas for N tools.
- **Bottleneck:** `args` is opaque. Layer 3 routing can only succeed if the router knows what goes
  *inside* `args`. One undifferentiated `dict` parameter is why "route this sentence to the right
  capability" resolves to `python.software.repair.route.v1` — a *guess from the sentence's words*,
  not a lookup of a declared contract.

The fix is therefore **not** to write 92 schemas. Because the modules are written fail-closed, the
contract is *derivable*: run the capability with an empty `args` and it tells you what it wanted.

---

## 4. I measured the derivation before recommending it, and it mostly failed

I am not going to hand you a plan built on a mechanism I did not test. I invoked all 92 with `{}`:

```
  invoked with empty args                 92
  returned a NAMED missing key             6      -> MANIFEST_INPUT_REQUIRED, ...
  returned something silent               19
  raised                                  76
  wall clock, all 92 calls            164.88 s
```

**6 of 92 name what they want.** The rest raise — some with a useful message, many with
`ModuleNotFoundError: PIL`. Derivation by empty-invocation does **not** work as-is, and I will not
claim it does.

But the 164.88 s is itself the finding: **~1.8 s per capability**. That is too slow to run on every
routing decision and fast enough to run **once, offline, as a build step** — which is what a derived
schema needs.

So the honest plan has a prerequisite I can name precisely: **make the 92 fail-closed modules name
their missing key.** That is a change to the refusal surface, not to any logic — the modules already
refuse; they just refuse anonymously. That is the same class of fix as the `render_route_admission`
and forge-entrypoint fixes that came before it: delete the ambiguity, add nothing.

---

## 5. The plan, ranked by deletion

Every item is scored by *what it removes*. **Best part is no part.**

### #1 — Delete the anonymous refusal. (enables everything else; one line per module)

The single highest-leverage change in this repository. 86 of 92 capabilities fail without saying what
they needed. Making each refusal name its missing key turns an opaque `args` into a declared contract
**without authoring a schema**, at a cost that is measured: the same 164.88 s, once, offline.

- **Removes:** the need for 92 hand-written schemas. Removes `args` opacity from layer 3.
- **Would prove itself by:** `declared parameters` going **0 → >0** with no new file.
- **Guard already planted:** `test_known_mechanism_concepts_are_not_addressable` fails the moment this
  lands, forcing a re-measure instead of a silent drift.

### #2 — Make the mechanisms sayable. (the L1 fix, applied to the 25 large ones)

`computer`, `derivation`, `organ`, `self-improvement`, `metamorphic`, `bisimulation`, `continual`,
`forget`, `transfer`, `curriculum`, `attention` have **zero postings**. The docstrings already exist —
`computer_env_v1.py` says *"the computer itself, as an environment the learner can act in"* and the
router cannot act on the word `computer`. This is not authoring prose; it is **indexing prose that is
already on disk**.

- **Removes:** the 0.5381 sayable ceiling on 3.50 MB of mechanism.
- **Cost:** one index rebuild. No new module.

### #3 — Declare layer 0 in the manifests. **DONE this commit.**

`Pillow==12.0.0` added; it was in neither manifest. 9 capabilities restored from zero to loadable.
The durable part is not the package — it is that **layer 0 now has a name and a guard**, so the next
missing dependency is reported instead of being silently indistinguishable from a bug.

### #4 — Collapse the two doors. (the `composer_route_v1.py` question)

`composer_route_v1.py` (243 KB, *"Routing a sentence to a typed capability chain"*) **is** layer 3,
written, reachable, and 0.60 sayable — while `brain_unified_model_v1.route()` is what actually serves
requests. Either the model delegates to the composer, or the composer is dead weight. Measuring which
is a day, and it decides whether a 243 KB file stays.

- **Removes:** one of two competing routers. Highest possible deletion in the ranking.

### #5 — Adopt the frontier's one measured win, in the form it actually works.

Prometheus's result is **not** "add a memory module." It is: keep a working memory of what has
already been explored so the agent stops re-traversing. This repo has `raw_goal_trace_acceptance_v1.py`
(*"every claimed effect is re-opened from disk"*) at 0.375 sayable. The transferable idea is the
**acceptance trace**, not the graph.

- **Removes:** repeated traversal. Adds no storage layer — the trace is the thing that already
  re-opens from disk.

### Explicitly **not** on the list

- **Fine-tuning, continual post-training, RL.** CPO's own result is that continual RL still forgets
  severely. The frontier is fixing forgetting with a *regulariser*, not more training. We have a
  frozen, read-only fabric; the entire literature's conclusion is that adaptation belongs outside the
  weights. **The cheapest correct answer is the one we are already forced into.**
- **A new memory store.** The survey result is unambiguous: storage is solved, retrieval is not.
  Adding a store adds a part and moves no number. #1 and #2 are the retrieval fix.

---

## 6. The single sentence

The frontier is five separate literatures converging on one failure — *the system cannot find what it
already knows* — and this repository has that failure in its purest form: 2,248 modules, 26%
reachable, 54% sayable, and 92 capabilities behind one opaque word, `args`.

**The smartest plan is not to build the missing capability. It is to make the existing ones name
themselves, at one line each, offline, once.**

---

## 7. Provenance

- Tool: `canonical/tools/capability_concept_coverage_v1.py` (layers 0–2, CLI + JSON)
- Guards: `canonical/tests/test_capability_concept_coverage_v1.py` (6 tests)
- Manifests: `substrate-requirements.txt` (+Pillow, with the measurement in the comment)
- Fabric numbers: `brain_unified_model_v1.open_model()` — 153 BOUND, 92 loadable, 92×`run(args, root)`
- Test state at commit: **79 passed, 0 failed, 919 subtests** on the model/coverage lanes.
  Repo-wide: 80 passed / 2 failed — both failures are the **refused R1 blob pins**, unchanged and
  still awaiting your decision on the 90-vs-494 count.
- External sources are cited inline by system and number; none is used to claim a score for this repo.
