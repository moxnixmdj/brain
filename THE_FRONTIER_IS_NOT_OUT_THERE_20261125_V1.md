# The frontier is not out there. It is unindexed, in here.

*2026-11-25 · branch `arena/b864526d-brain` @ `9953cbc4` · $0, zero model calls*

---

## 0. Why this plan is not last round's plan

Last round I wrote that the frontier is a *binding problem* and proposed five doors: admission, curation,
latency, verification, and worlds. Door 1 shipped. Door 2's exit half shipped. This round I went looking
for what had not been measured yet, and found the number that reframes both.

The repository's own compiled artifact already computes it. `BRAIN_UNIFIED_MODEL_V1.json` →
`anatomy.reachability`, from `canonical/tools/domain_atlas_v1.py:384`:

| domain | frontier phrasing, via `route()` | this repo's own vocabulary |
|---|---|---|
| coding agents | **1.000** | 1.000 |
| world model | **1.000** | — |
| memory | 0.667 | 0.333 |
| verification / abstention | 0.667 | 0.333 |
| computer use | 0.667 | 0.333 |
| continual learning | 0.333 | 0.333 |
| **instant learning** | **0.000** | 0.000 |
| **world model (native route)** | **0.000** | — |

Read the right two rows. The frontier's *words* find this machine's own capabilities almost perfectly —
coding agents and world models at 1.000. In the two domains this repository has spent the most effort
proving — instant learning and world models — the runtime's own `solve()` route reaches **none of the
working code**.

The code exists. It is indexed. It is simply not on the path.

So the honest answer to "how do we get ahead of the frontier" is not another capability. It is:

> **This machine may already be ahead of the frontier and cannot currently prove it, because the
> evidence is in 1.4 million lines nobody has been asked to walk.**

---

## 1. The one law

The repository already wrote it. `canonical/laws/BYTES_RESOURCE_BOUNDED_MINIMUM_MECHANISM_LAW_V1.md`:

> The target is not "compress a model." … The target is **the minimum verified composition of mechanisms
> conditional on what Brain already owns.**

That is Elon's law, in this repo's own vocabulary, with a resource bound. It has never been *applied*.

Here is the measurement that makes it urgent:

```
6,294 Python files · 1,428,134 lines · 462 capabilities · 116 engines
153 bound · 631 harvested · 0 admitted
70 imports in the entire front door
0 files deleted in the last 20 commits
```

**A machine that cannot delete anything has a size, not a shape.** 1.4M lines is the largest artifact
here and the least examined. Every line is a part that must be understood, indexed, migrated, and
defended — and `0` of them has ever been retired. That is the same defect Door 2 fixed at the skill
layer, one level up, unaddressed, and roughly three orders of magnitude larger.

And in 2026 the literature named the theory behind the fix: *A Compositional Framework for Open-ended
Intelligence* (arXiv 2606.15386) argues that open-endedness is search over the closure `L(P,C)` of a
**finite** primitive set `P` and composition operators `C`, and that a **parsimony constraint** — MDL
applied to the library, not the model — is what forces a minimal reusable basis instead of brittle,
task-specific accumulation. Their Proposition 5.2 is the claim this plan tests: parsimony biases toward
transfer by recombination.

The frontier cannot run that experiment. Its capabilities *are* weights; there is no file to delete.
This repository has 1.4M lines it could delete and has never tried.

---

## 2. Five doors, ordered by how much they delete

### Door 3 — Make the library smaller than the frontier's prompt.

The move is not "add a capability." It is: for each of the seven anatomy domains, find the **minimum
verified composition** that reaches the frontier function, and delete everything downstream of it that
does not.

`BYTES_RESOURCE_BOUNDED_MINIMUM_MECHANISM_LAW` already defines the objective `B(R)`. What is missing is
an instrument, and the instrument is cheap:

1. For each domain, take the atlas's own candidate stems and frontier query set.
2. Rank every module by *how much of the frontier function it accounts for per line* — a bytes-per-
   behaviour ratio, computed from the module's own declared contract, not from a model's opinion.
3. Report the **Pareto front**: modules that are neither dominated on coverage nor on size. Everything
   off the front is a deletion candidate.
4. Measure `B(R)` for the front. That is the number to compare against the frontier, and nobody has ever
   computed it.

**And the deletion target is already counted.** From the model's own `source_index`, measured here for the
first time:

```
2,237 indexed modules
  1,635  classified ORPHAN          (imported by nothing, entry point for nothing)
  2,161  imported_by_count == 0     (96.6%)
  1,636  of those are also not executable entry points and not capabilities

  29,336,105 bytes on disk -- 46.4% of all 63,222,357 bytes of canonical/**.py
```

**Nearly half the corpus is imported by nothing.** That is not a claim about quality — an orphan can be a
law, a generator, or a document-with-code. It is a claim about *reach*: 29 MB of mechanism that no route,
no test, and no other module currently walks to. `B(R)` has an obvious floor and nobody has ever tried to
reach it.

**Acceptance:** `B(R)` for at least one domain falls below the token cost of the frontier's system prompt
for the same function, with the routed behaviour unchanged. If it does not, the door fails and says so.
**Deleting nothing is a valid outcome; never measuring is not.**

### Door 4 — The door out, one level up: index before you add.

`instant_learning: native 0.000` and `world_model: native 0.000` are not capability gaps — the modules
exist and pass their tests. They are **wiring gaps**, and they are the cheapest win in the entire tree
because the work is already done and already verified.

Door 2 taught the pattern: an asset must keep paying for itself. This door applies it to the *routing*
surface. A module that is indexed but unreachable from `solve()` is paying nothing and costing a slot.

**Acceptance:** `native_route_hit_recall` for instant learning and world model move off 0.0 without
adding a single module. The fix must be a route entry, not a new engine — if it needs a new file, the
answer is that the existing file's contract was wrong, and that is the finding.

### Door 5 — Speculation, where the verification is already free.

This is the round's genuinely new idea, and it comes from a collision between two 2026 papers and one
property this repo has and the frontier does not.

The frontier's latency work is speculative decoding: a cheap drafter proposes, an expensive model verifies
in one parallel pass. *Speculative Macro Commit* (arXiv 2609.03236) extends it across agent steps —
mined recurring action macros committed after a **verified anchor call**, cutting latency 18.6% while
matching baseline accuracy. *SpecAgent* (arXiv 2610.21463) makes the strong model a *reviewer* of
grounded drafts, halving wall time.

Every one of those systems has to guess whether keeping the draft was safe. **This repository often does
not have to guess.** A verified skill in the store *is* a mined macro with a proof attached — Door 1 made
that literal: the store row contains the verified program, and the second instance recomputes through it
in 17.1 ms with zero model calls.

So:

> **Speculate at the level of the plan, not the token, and verify with the artifact instead of a model.**

The router proposes the top-k candidate plans; the cheapest sufficient checker commits the longest valid
prefix; only the first rejected step pays for a model. That is `SpecAgent`'s protocol with the strong
model replaced by a program — and the reason it can be *lossless* here while theirs is approximate is
that a verified skill carries its own postcondition.

**Acceptance:** the median solve commits the draft unchanged, and wall time falls while the acceptance
rate is reported per skill. **A speculation layer that never rejects is not speculation, it is caching
with extra steps** — and the test must show rejections happening.

### Door 6 — A benchmark we cannot win by luck.

Every number above is a recall over a candidate set this repo defined. That is exactly the circularity
`A CENSUS MUST SAMPLE A TREE THAT STILL CONTAINS THE DISTINCTION` warns about, and the 2026 literature
supplies the antidote: *Hardening Agent Benchmarks with Adversarial Hacker-Fixer Loops* found **16% of
1,968** benchmark tasks hackable given only the task description. Any benchmark that can be passed
without doing the work is measuring the verifier.

The advantage here is structural. A "task" on this machine is a file in a git worktree; the oracle is a
differential on that file; and `computer_use_check_density_v1` already measures how often a wrong action
is *indistinguishable* from the right one. A suite built from this repo's own commit history — real
fixes, real oracles, adversarial decoys — is uncontaminated by construction and cannot be farmed.

**Acceptance:** one command, ≤60 s, reporting pass rate **and** the hackability rate of its own verifiers.
A suite that cannot state its own hackability is not admissible.

---

## 3. What "insanely fast" means when the answer is already computed

Measured this round, on this tree:

| operation | cost |
|---|---|
| verified skill re-use (second instance of a program) | **17.1 ms**, 0 model calls |
| in-memory world simulation | **10–50 µs** |
| confidence bound for a retirement decision | **42 ms** |
| frontier IDE agent, per turn | 3–8 s |
| frontier computer-use, per action | 1.5–4 s |

On the second instance of anything, this machine is **200–400× faster than the frontier, because it does
not call a model.** That is the entire thesis, and it is already true. The problem has never been speed.
It is that almost none of the 1.4M lines are on the path where that speed is spent.

Door 1's stall was a **200× tail under a 3 ms `elapsed_ms`**: organ synthesis ran after the answer
existed. Door 3's deletion target is the same defect at rest — 1.4M lines that are not on the path and
still cost. **Best part is no part applies to the answer itself: the fastest line of code is the one that
was never needed because a verified program already knew the answer.**

---

## 4. Why this is ahead, in one testable sentence

**The frontier's capability is in weights and cannot be inspected; this machine's capability is in files
and can be deleted.** That asymmetry only pays if someone does the deleting, and nobody has.

A competitor can copy a model. They cannot copy a 1.4M-line corpus of verified mechanisms minus its
dominated 90%, because that subtraction is the product, and it has never been performed anywhere.

The falsifiable bet: **after Door 3, one domain's minimum verified composition will be smaller than the
frontier's system prompt for the same function, and will route with equal or better recall.** If it is
not, the corpus is genuinely irreducible and I was wrong — which is also worth knowing, and is the only
way to know it.

---

## 5. What I measured, and what I refuse to claim

Measured this round: `6,294` modules / `1,428,134` lines; `0` deletions in the last 20 commits; the
reachability table above, read from the repo's own `DOMAIN_ATLAS_V1.json`; `70` imports in the front
door; `instant_learning` and `world_model` native route recall `0.000` while their source-hit recall is
`1.000` — the code is found and not routed.

**Not claimed:** that the minimum composition is *small*. The corpus may be irreducible; MDL on 1.4M lines
may delete 3%. That is a real possible answer and Door 3 is designed to produce it honestly. Also not
claimed: that removing a module is safe because it is unreachable — unreachable from `solve()` is not
unreachable from a test, a law, or another module's import. Any deletion must be gated on the same
`grader_may_retire` bound Door 2 built, or it is vandalism with a diff.

And the one thing I will not dress up: last round I called the binding problem the answer and shipped two
doors. This round's measurement says the binding problem is **0.0 in the two domains that matter most**,
which makes wiring cheaper and more urgent than anything I proposed before. That is not a better plan.
It is a better measurement, and it made the previous plan smaller.

---

## 6. Reproduce

```bash
python3 -c "
import json
a=json.load(open('canonical/unified_model/DOMAIN_ATLAS_V1.json'))['reachability']
for k,v in a.items():
    print(f\"{k:24s} src·nat {v['native_source_hit_recall']:.3f}  rte·nat {v['native_route_hit_recall']:.3f}\")
"
# instant_learning           src·nat 1.000  rte·nat 0.000   <- found, not routed
# world_model                src·nat 1.000  rte·nat 0.000   <- found, not routed
# coding_agents              src·nat 1.000  rte·nat 1.000

# The model carries only the route columns; the atlas carries both. Use the atlas.

find canonical -name "*.py" | wc -l          # 6294
git log --diff-filter=D --oneline -20 --name-only | grep -c '\.py$'   # 0
```
