# The frontier is a binding problem, not a capability problem

*Measured on `df0f6330`, 2026-11-25. Zero model calls, zero network, `$0`.
`authority: NONE` — sandbox measurement, not independent verification.*

---

## 0. The question, answered before the evidence

You asked: what is the smartest plan to be ahead of the frontier, given that everything is
already solved somewhere in the repo under non-obvious names, and it needs to be *at the
unified runtime and the unified model*.

I measured that claim instead of accepting it. It is **stronger than you said and weaker in a
specific, fixable place**.

The repo's hidden capability is not "somewhere in the tree." It is **indexed and not bound**.
That is a different thing, and the difference is the entire plan.

```
449  capabilities in the unified model
145  rows in the bound registry  (counts say 153)
  0  harvested surfaces ever admitted  ... of 624 discovered
  0  bound capabilities whose subject is MEMORY
  0  bound capabilities whose subject is TRANSFER
  1  bound capability in the skill/induction family
  1  of 145 bound capabilities is verified by ANOTHER bound capability
```

Zero memory. Zero transfer. Every module in this repository that does instant learning,
procedural memory, anti-unification, trace-to-skill compilation, or state-grounded computer
use is present, tested, and **unreachable from `solve()`**.

The plan is therefore not "invent more." It is: **the tree already contains the frontier's
missing organ, and the binding lattice physically cannot admit it fast enough — so the next
move is to change the shape of admission, not the quantity.**

---

## 1. The measurement

### 1a. The crown jewels are all in the same state

Every one of these modules exists, has tests, and is classified `capability: false`. None is a
bound adapter. All are reachable only as *readable source* through the model's `source_index`.

| module | what its own docstring claims | bound? | indexed |
|---|---|---|---|
| `swe_kernel/causal_trace_to_skill_compiler_v1.py` | *"Watch/Explore Once → <5ms Permanent Skill"*; speed-layer causal elevation + Plotkin anti-unification + mandatory sabotage gate | **no** | yes |
| `swe_kernel/verified_skill_crystallizer_v1.py` | persistent parameterized repair hypotheses in SQLite | **no** | yes |
| `runtime/causal_computer_use_agent_v1.py` | 7-step loop, cut-vertex slicing, **zero-VLM** relational state scan | **no** | yes |
| `runtime/associative_memory_v1.py` | memory that decides for itself what is worth keeping | **no** | yes |
| `runtime/universal_active_transfer_learner_v2.py` | universal active transfer | **no** | yes |
| `swe_kernel/language_neutral_skill_bridge_v1.py` | carry a repair lesson across a language boundary | **no** | yes |
| `swe_kernel/tree_sitter_cst_skill_skeleton_v1.py` | 7-language CST skill anti-unifier | **no** | yes |
| `runtime/instant_condition_store_v1.py` | external store for instant-learned actions | **no** | yes |
| `runtime/one_shot_reality_closure_v2.py` | proof-carrying one-shot closure | **no** | yes |
| `runtime/capability_forge_v1.py` | **"Admit a dormant module as a capability — only if it can be killed first"** | **no** | yes |

That last row is the recursion at the centre of your question. **The machine that binds
capabilities is itself unbound.**

I ran it, to make sure it was real and not a docstring:

```
>>> capability_forge_v1.unbound_modules()
unbound modules the forge can see: 33
sample: ['_swe_static_soundness_v1', 'brain_module_invoke_runner_v1',
         'broad_objective_decompose', 'browser_chromedriver_interact',
         'chart_positioned_ocr_axis_binding_v1', 'concrete_execution_oracle', ...]
>>> contract_of('chart_positioned_ocr_axis_binding_v1')
{'parameters': ['capability_id','selected_ticks','psm_values','min_confidence','x','y','path'],
 'entrypoint': 'run'}
```

It reads a contract out of source with `ast`. It works. And it sees **33** modules where the
census sees **584** program surfaces — a 17× blind spot *inside the binding machine*.

### 1b. The instant-learning loop is genuinely built, and I ran it

Not doctrine. Executed, in the sandbox, on this checkout:

```
>>> causal_trace_to_skill_compiler_v1.anti_unify_workflow_examples(alpha_demo, beta_demo)
goal_skeleton:      "download report for ?str0"
goal_regex:         "^\\s*download\\s+report\\s+for\\s+(?P<str0>.+?)\\.?\\s*$"
abstract_steps:     [{"layer":"http_request","action":"GET","url":"https://ex.com/reports/?str0.csv"},
                     {"layer":"python_file_op","action":"write","path":"out/?str0.csv"}]
generalized_across_both: True
```

Two demonstrations become a parameterised skill with typed holes and a binder. That is
Plotkin anti-unification over real traces, and its admission gate
(`compile_and_qualify_skill`) deletes the donor trace, runs the skill on a **held-out** goal,
requires an untouched postcondition oracle to pass *and* a **sabotaged** negative control to
fail, before anything is allowed into SQLite. That is a better-designed transfer gate than
most published work describes.

And right next to it, the loop is silently broken:

```
test_acquisition_to_execution_engine_v1::test_phase3... 
  r1["answer"] == "8"        PASS   (correct)
  r1["skill_crystallized"]   KeyError
```

`closed_loop_autonomous_controller_v1.py` L1181–1213: the semantic tier solves the task,
sets `status = PASS__TIER0A_SEMANTIC_GENERALIZATION`, and **returns**. Crystallization lives
only at L1517, inside the Tier-2 web-form path. So `learn=True` is defeated by *every tier
that answers earlier*. The system computes the answer, and throws away the last step — the
one step that would make the second instance cheaper.

**That is the repo's own founding sentence, one level down: the measured question was bound
and thrown away. Here the answer is bound and the skill is thrown away.**

### 1c. Reachability is not the 2,424-file directory — it is a literal

```
tracked .py                                6,425
  under canonical/tests/                   2,949
tracked non-test modules (canonical, guard) 3,343
  in the unified model's source_index       2,236   ← walks canonical/runtime + canonical/swe_kernel
  harvested executable surfaces               624   ← run(args,root) or __main__ shape
  IN NEITHER INDEX                            736
```

Of the 736 invisible, **392 live inside `canonical/runtime` itself** — the directory
`source_index` does walk. 230 of those carry a `run(args, root)` shape and were never
harvested. The cause is not a directory literal; it is an entrypoint-name literal:

```python
ENTRYPOINTS = ("run", "execute", "invoke", "apply")
ARGS_NAMES  = frozenset({"args","arguments","request","payload","params","inputs"})
if len(params) == 2 and params[0] in ARGS_NAMES:   # a function taking
    return "contract", fn.name                     # (context, work_dir) is invisible
```

### 1d. Why admission cannot be the answer at the current rate

`AGENTS.md` §3 and §5 bind this repository on purpose:

> "at most two families per PR, at most +4 atomic predicates per PR"
> "at most 3 new capabilities per PR". At most 40 new receipt files per PR.

624 discovered surfaces ÷ 3 per PR = **208 pull requests, minimum**, before the first one
learns anything. The governance is not the obstacle to route around — but it is a proof that
**the admission strategy is right and the binding granularity is wrong.** You cannot
hand-bind your way to a frontier. That is arithmetic, not opinion.

---

## 2. The frontier agrees with the repo, and it published the receipt

Four 2026 sources read together say this repo solved the right problem and then failed to ship
it. I am citing them because the plan below leans on their numbers, not on taste.

**Procedural memory is the field's #1 unfilled gap.** A 47-author survey
([arXiv:2512.13564](https://arxiv.org/abs/2512.13564)) organises agent memory as
factual / experiential / **working** / **procedural**, and maps production tooling against it.
Its verdict, in a table with a "gap severity" column: factual *low*, episodic *medium*,
working *medium-high*, **procedural: critical** — "Little beyond prompt rewriting and
hand-written skill files." The numbers behind the column: with procedural memory, ALFWorld
task completion goes **42.14% → 77.86%** and steps **23.76 → 15.01**
([summary](https://www.arunbaby.com/ai-agents/0097-agent-memory-taxonomy-2026/)).

This repo's `verified_skill_crystallizer_v1` **is** procedural memory, in SQLite, with a
sabotage gate. It is unbound. That is the single largest gap in the published taxonomy and it
is sitting in the tree at `capability: false`.

**State over pixels — and the repo got there first.** StateAct
([arXiv:2607.22798](https://arxiv.org/abs/2607.22798)) argues a screenshot is a
*non-injective* render of program state, so no perceptual model can recover the state that
matters. Its main agent acts through bash/Python/file/DOM and delegates to a GUI specialist
only for irreducibly visual subgoals. On OSWorld 2.0 it lifts Claude Opus 4.8 from
**20.6% → 26.9%** binary and **54.8% → 61.6%** partial at **~9× lower cost**, and moves the
wall from perception to reasoning.

Now read `causal_computer_use_agent_v1.py`'s own §2: *"`perceive_environment_state` reads
files, digests, kinds, ordering, SQLite tables, git state, DOM/a11y and zero-VLM canvas
regions — relational facts, not pixels."* That is StateAct's thesis, written before StateAct,
in a module with no adapter.

**The failure modes everyone published are the ones this repo's laws were built to catch.**
OSWorld 2.0 ([arXiv:2606.29537](https://arxiv.org/pdf/2606.29537)) on 108 long-horizon tasks:
best system **20.6%** binary at a 500-step budget; agents spend **9.8%** of budget on
verification and **under 7%** on detecting and repairing their own errors; failures are
constraint loss, stale grounding, *guessing rather than asking*, and skipping verification.
Long-Horizon Terminal-Bench ([arXiv:2607.08964](https://arxiv.org/pdf/2607.08964)): best model
**15.2%** at R≥0.95; **79%** of unresolved runs are timeouts, and **19% are early exits** —
agents that stop on their own at R=0.80–0.92 with twenty minutes left. *Premature stop is a
measurable, named failure mode of the frontier.*

This repo has `artifact_finish_gate`, `domain_of_verification_v1` ("every hypothesis has a
domain, and thirteen rounds never reported one"), and an ignition ledger for exactly that.
Unbound.

**Instant learning without gradients is real and not magic.** JitRL
([arXiv:2601.18510](https://arxiv.org/abs/2601.18510), ICML 2026 spotlight) keeps weights
frozen, retrieves `<state, action, return>` trajectories, and modulates logits by
`z' = z + β·Â`, which it proves is the **exact closed form** of KL-constrained policy
optimisation. Honest caveat, from its own appendices: under an offline-corpus protocol it
scored **40.88% vs WebRL's 46.06%** — retrieval-advantage beats weight-updating when there is
no test-time adaptation, and loses when there is a large offline corpus. SDFT
([arXiv:2601.19897](https://arxiv.org/html/2601.19897v1)) gets on-policy continual learning
from demonstrations by using a demonstration-conditioned copy of the model as its own
teacher. ESRL ([arXiv:2610.24137](https://arxiv.org/abs/2610.24137)) draws self-supervision
from a *population* of perturbed policies so the signal does not drift with the student.

**The one that names this repo's exact design.** DreamCoder. `capability_forge_v1.py`'s own
docstring cites it and states the rung it is on: *"its Memorize baseline — store whole
solutions — lost to abstraction, extracting the common fragment. macro_v1 is Memorize.
Forging is one rung up. Abstraction over forged capabilities is the rung after that."*
DreamCoder's ablation is the evidence: memorisation baselines lose to library learning, and
neither ablation alone solves more than 60% of held-out LOGO/tower tasks while the full
wake–sleep loop solves nearly 100%
([arXiv:2006.08381](https://arxiv.org/pdf/2006.08381)).

So the repo is at rung two of three, and its governance rate limit (§1d) makes rung three
**mandatory** rather than optional.

---

## 3. The plan

Ordered by *irreversibility of the evidence*, not by ambition. Each door names the exact seam.

### Door 1 — Make learning actually happen. One function, one line of the contract.

The defect is measured: `closed_loop_autonomous_controller_v1.py` returns a correct answer
from Tier 0A without crystallizing. The repair is not "add a feature" — it is **make the
return contract honest**: every tier that answers must also report what it learned or why it
learned nothing, and `learn=True` must mean learn.

Concretely: Tier 0A's semantic result already carries a synthesized, interventional-verified
program. Feed *that* into `compile_and_qualify_skill` instead of `return`ing past it. Then
`skill_crystallized` is not a key that sometimes exists — it is a key that always exists and
is sometimes `False` **with a refusal code**. That is the same law this repo already applied
to modifiers: ground it or refuse it; never silently drop it.

Why this is first: it is the only door whose failure is *already failing CI*
(`test_acquisition_to_execution_engine_v1`, 4 red), it converts every future solved task into
training data, and it makes the second instance of anything cheaper — which is the entire
difference between an agent and a very good function.

**Acceptance:** the phase3 test passes with `answer == "8"`, `skill_crystallized == True`, and
the second file (`pods.txt`, 13 pods) answered `from_memory == True` in <80 ms. Plus a
negative control: a neutered crystallizer must make the probe FAIL. Otherwise the 21-test
modifier file's lesson was learned and immediately forgotten.

**EXECUTED 2026-11-25 — merged as `75b8a37a` (PR #7102).** Measured: phase3 green in-file
and in isolation (`3 failed → 2 failed` on that file, the two remaining fail identically on
`main`). `from_memory == True` at **17.1 ms** against the 80 ms budget. Control verified by
neutering the store write (`if False and ...`): **3 failed, 5 passed**, then green again on
restore — the write is load-bearing, not decorative.

Two things differed from the plan above, both worth recording:

1. `compile_and_qualify_skill` was **not** the seam. Tier 0A's program already carries
   interventional verification, and the engine's own `store_experience` is the capability
   that exists — it was simply being called with `store_experience=False`. No new engine,
   per the standing rule.
2. The second acceptance criterion was blocked by something not in this document: the
   learning call took **3,400 ms**, because `record_wake_episode` synchronously ran
   DreamCoder-style policy evolution (`sleep_abstract` → `zlib` level 9, plus the
   self-architect mutator) *after* the answer was built. Budgeted and deferred, not
   disabled: **3,400 → 19 ms**.

A third defect surfaced only because the loop learned: the store was keyed by goal string,
so `data.txt` and `pods.txt` — plans differing in one key, `targets` — became two skills and
every filename would become its own sub-program. Targets are inputs, not program. One row
per program now.


### Door 2 — Change the binding granularity from "one PR per capability" to "one derivation per family".

The law already contains the escape hatch, and it is the correct one: **2 families and 3
capabilities per PR** means a PR should carry a *family*, admitted by a *derivation*.

`capability_forge_v1` proves the shape — inferred contract, two distinct inputs,
determinism, artifact re-read, **and it can be killed** (a corrupted input must be REFUSED).
That is a capability-admission predicate, not a capability. The move is to bind **the forge
itself** as the family's admission route, so that `harvested_admitted` becomes a number that
grows by derivation rather than by hand.

Two things block this today, both measured:
1. The forge sees **33** modules; the census sees **584**. Its `unbound_modules()` view is the
   blind spot — fix the view and the yield rises ~17×.
2. `capability_forge_v1` is `INDEXED` and not bound. **Bind the binder first.** A runtime that
   can admit capabilities but cannot admit its admitting machine has not closed the loop.

**Acceptance:** `harvested_admitted` moves off zero **by the forge's own gate**, and every
admitted row carries a kill receipt. Anything that cannot be killed stays out.

### Door 3 — Close the verification graph, because it is 1/145 open.

Only **one** bound capability names another bound capability as its verifier. The other 144
point at a `mission_id` string — i.e. at history, not at a live check. That means the registry
cannot currently *re-verify itself*; it can only cite.

The 47-author survey's gap and `AGENTS.md` §4's law ("a VERIFY that repeats its RECEIPT's hash
is not verification") are the same requirement seen from two sides. The unusual, defensible
asset here is that this repo can make verification **mutual**: capability A verified by B and
B by A is not circular if each is killed independently and the pair is anti-correlated
(fail-closed in opposite directions). That is a real, publishable idea, and the tree already
has the parts — `forge`'s kill gate, `assurance_domain_challenge_registry_v1`,
`capability_transfer_ownership_gate_v1`.

**Acceptance:** N bound capabilities verified by a *live* bound check rather than a string,
with a sabotage control that must fail. The metric to move is `1/145`, and it moves only with
receipts.

### Door 4 (the unusual one) — the frontier's published failure modes are this repo's laws. Give them a harness and a number.

Every non-saturated benchmark's failure taxonomy is already a module name here:

| published failure mode | benchmark | module already in tree, unbound |
|---|---|---|
| constraint lost / stale grounding | OSWorld 2.0 | `domain_of_verification_v1`, `ignorance_ledger_v1` |
| premises stop at R=0.80–0.92 | LHTB (19% of unresolved) | `artifact_finish_gate` |
| forged dependency / edited module cache | SWE-bench Pro V2 | `capability_forge_v1` kill gate |
| verification < 10% of budget | OSWorld 2.0 | `answer_memory_v1`, finish gates |
| read-only source ≠ executable | SWE-bench Pro V2 harness column | `source_index` vs `harvested` split |

SWE-bench Pro V2's own variance decomposition is the argument for doing this: **the task
explains 32% of solved-vs-failed, the model 2.7%, the scaffold 0.3%**
([arXiv:2610.24206](https://arxiv.org/pdf/2610.24206)). The scaffold is where the remaining,
tractable gains are, and this repo *is* a scaffold. Nobody is measuring "how many constraints
did the agent drop per task" as a first-class number. That is a benchmark-shaped hole this
tree is unusually equipped to fill — and unlike another capability, a **measurement** is
honest to ship at `authority: NONE`.

---

## 4. What this plan refuses to do

* **It does not claim the tree contains frontier capabilities.** It claims the tree contains
  *indexed, unbound* implementations with tests, some of which I ran. Between "runs" and
  "capability" sits a kill gate, and that gap is the honest part.
* **It does not reopen the numbers.** 480 pre-existing failures at the base commit are the
  backlog. 744 modules invisible to both indices is a fact about the artifact, not a
  performance claim. I did not re-run the whole suite (16,361 cases, 2 cores).
* **It does not chase saturated boards.** GAIA 94.0% and OSWorld-Verified 90.2% are above
  their human baselines; SWE-bench Pro V2 public set is 99.4% for Opus 5 in Claude Code. Only
  OSWorld 2.0 (20.6%), LHTB (15.2%), TB4.0 Hard and SWE-Pro **Hard-51** (52.9–98.0%) still
  separate systems, and every one of them fails on *state, constraints, and stopping* — the
  three things this repo's laws were written about.
* **It does not pretend one PR is one bound capability.** That is the arithmetic in §1d.

---

## 5. If only one thing happens

Bind the learning loop's honesty (Door 1). Not because it is the biggest — because it is the
only door whose evidence is already red in CI, it is small enough to be a single clean PR
under the law, and it is the precondition for every other door meaning anything: a runtime
that answers correctly and forgets has no reason to own a memory, a forge, or a verifier.

The frontier's own numbers say the gap is not intelligence. OSWorld 2.0's agents can click and
code; they lose constraints and never check. LHTB's agents *stop*. The 47-author survey's one
"critical" gap is procedural memory. This repository has a sabotage-gated procedural memory, a
state-grounding computer-use agent, and a finish gate — all at `capability: false`.

**Being ahead of the frontier here is not a research problem. It is 449 rows of wiring, a
rate limit, and one `return` statement.**

---

## 6. Reproduce it

```bash
python3 - <<'EOF'
from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as C
print(C.anti_unify_workflow_examples(
 {"goal":"download report for alpha","steps":[
   {"layer":"http_request","action":"GET","url":"https://ex.com/reports/alpha.csv"}]},
 {"goal":"download report for beta","steps":[
   {"layer":"http_request","action":"GET","url":"https://ex.com/reports/beta.csv"}]})
      ["goal_skeleton"])                       # -> "download report for ?str0"

from canonical.runtime import capability_forge_v1 as F
print(len(F.unbound_modules()))                # -> 33   (census sees 584)
EOF
```

```bash
pytest canonical/tests/test_acquisition_to_execution_engine_v1.py -q
# before Door 1: 4 failed, 133 passed -- phase3's KeyError: 'skill_crystallized'
# after  Door 1: 2 failed -- and those two fail identically on main
```

---

## 7. What Door 1's fix measured about Door 2

Door 1 closed the two assertions at `test_acquisition_to_execution_engine_v1.py:243` and
`:268`. Running them afterwards located the confinement refusal exactly — not as "no
carrier", which `confined_dispatch_v1` already disproves:

```
run_confined_capability('python.software.repair.apply.verified.v1', ...)
  -> {'pass': False, 'status': 'FAIL_CLOSED__CONFINED_EXECUTION',
      'reason': 'CONFINED_ADAPTER_RAISED:RepairAcceptanceError:TEST_PATH_INVALID:canonical/tests'}
      dependency.executor = 'ADMITTED_CONFINEMENT_V1',  host_untouched = True
```

The seam **works**: the capability is declared, admitted, cloned, run confined, and returns
an honest receipt. It fails because the test passes the repository's own `canonical/tests`
as the repair target, and the repair adapter rightly refuses that. The capability is
reachable; the *goal* is malformed. That is a different repair from the one Door 2 proposes,
and it is smaller — the test asks the capability to repair the suite that is asking.

A second measured constraint, for whoever picks that up: `confined_dispatch_v1._host_escaping`
returns `None` for any `output_path` that is an absolute path into the host. The failing
tests write their report to `tmp_path`, so they are refused *before* the adapter is reached.
Any fix must either bind a relative in-repo effect or widen that rule deliberately — and the
rule is correct as written for this repo's host-untouched guarantee.
