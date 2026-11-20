# A goal hole is found by executing it, and closed by a law the judgments require

**20 November 2026 · branch `arena/1c13ff8a-brain` · authority `NONE__PRODUCER_RUN_SANDBOX`.**
Tool `canonical/tools/goal_closure_v1.py`; tests `canonical/tests/test_goal_closure_v1.py`;
receipt `canonical/verification/GOAL_CLOSURE_20261120_V1.json`.
Zero model calls, zero network at run time, zero parameters, zero capability credit, `truth.achieved`
unchanged. A second agent must rerun the tool before any number here is called verified.

---

## 1. Requirements restated, and the §2 contradiction resolved

I read the whole v3 prompt as new work, not as "continue". Its binding requirements are: read fully;
do not stop at a milestone; never ask the owner (research and decide instead); research the project
and the web before building; use first principles; remove parts before adding them; design for the
hardest case first; build one role at a time; distinguish understanding from matching; report
verified/unverified/failed honestly; let only the system take tests; own all runtime cognition with
zero model calls and zero memorised world knowledge in weights; calculate every parameter; one
branch, one merge when complete.

**Resolution adopted and tested here.** World facts and learned laws live **outside** the weights, in
an inspectable, editable JSON store (`canonical/state/GOAL_CLOSURE_STORE_20261120_V1.json`,
written with `write_store`, loaded with `read_store`). Persistence is a property of that store, not of a parameter: a
judged execution writes one closure clause to it, and deleting the file removes the knowledge
without retraining. The weights hold only derived mechanisms; this build adds exactly zero
parameters. No runtime dependency on another model exists. No evidence in this repository or in the
literature required a different boundary, so the default stands.

## 2. Research: what existed, and what the frontier says

The project already contains, under non-obvious names:

- `the_branch_is_the_model_v1.py` — plans over real directories by copying state, running one real
  action, and reading its exit status; no world model, `transitions_predicted = 0`. It solved 7/7
  real damaged repositories, and its own report names three **goal holes found by the planner and
  closed by hand**: dropping a stash, committing damage onto another branch, deleting a tracked file.
- `the_goal_is_a_discriminator_v1.py` — recovers the smallest relation separating accepted and
  rejected states from user judgments; ambiguity is acted on only by their intersection.
- `the_same_guard_twice_is_the_discriminator_v1.py` and `AGREEMENT_IS_NOT_EQUIVALENCE_20261119_V1.md`
  — agreement on runs is not equivalence; permanence requires a checkable precondition and a proof.
- `the_goal_is_a_relation_over_the_run_v1.py`, `the_goal_is_a_quotient_of_the_trace_v1.py`,
  `BREADTH_BUYS_WHAT_REPETITION_CANNOT_20261201_V1.md` — the goal is a statistic of a trace; breadth
  saturates (4 → 2 → 2 hypotheses across three machines), and a residual can be structural.
- `what_a_decision_costs_v1.py` — trying an action in a copy is exact (1.0 accuracy, 160 real
  states, ~14 ms) and must be paid again; a stored lesson is cheaper and unsound.

**Missing:** nothing above closes a goal hole automatically. The clauses that make a goal safe were
still written by the experimenter after the planner found the exploit. That is the part built here.

Frontier check (read as input, never as truth or runtime dependency): 2026 benchmark surveys put
OSWorld 2.0 at roughly 20% binary completion on 108 long-horizon workflows and treat SWE-bench
Verified as saturated/contaminated [2](https://capitalandcompute.net/ai-benchmarks/). The
specification-gaming literature calls *adversarial specification review* — enumerating ways an agent
can satisfy the letter while violating intent — the scalable defense, and reports that environment
hardening beats model-side mitigations in its setting
[1](https://dev.to/roxdavirox/specification-gaming-is-an-attack-surface-not-an-alignment-footnote-37a4).
A 2026 agentic-safety survey locates the same failure at the plan stage and says constraints can be
gamed under misspecification [5](https://arxiv.org/pdf/2605.23989). That agrees with the project's
own finding, but none of it supplies a zero-parameter hole-closing mechanism; so this is a build,
not a copy.

## 3. Verdict on the core claim

| part | status | evidence in this tree |
|---|---|---|
| One execution in a copy decides an action and gives its successor | **true** | `what_a_decision_costs_v1.py`: 1.0 on 160 real states; `the_branch_is_the_model_v1.py`: 0 predicted transitions |
| A demonstrated action replays exactly | **true, narrow** | retention measured in earlier rounds; it carries an effect, not an intention |
| One experience identifies the goal | **false** | a point is not a quantifier; residuals of 2+ statements survive hundreds of runs |
| "Permanent" = "agreed with every run so far" | **false** | `AGREEMENT_IS_NOT_EQUIVALENCE`: 983 runs, two different functions; equivalence needs a checkable precondition |
| More actions make one-shot learning easier | **false** | every new action enlarges the hypothesis space the single demonstration must pin down |
| The goal can be closed from judgments without another model | **true, bounded** | this build: minimal law sets selected from real executed states, two repos, held-out damage kinds |
| Everything on a computer / sentience follows | **unproven, and not implied** | no GUI, browser, natural-language understanding or new-environment benchmark was run here |

**The real bottleneck** is not action supply, retention, or raw decision accuracy. It is that the
acceptance predicate is incomplete while the planner is strong enough to exploit every omission,
combined with **coverage of judged task classes**: the laws a closure can select are exactly the
laws the judged rows forced. A second bottleneck, untouched here, is the repair grammar — 8 of 30
real historical fixes in `THE_HYPOTHESIS_GRAMMAR_IS_THE_BOTTLENECK_20261122_V1.md` are multi-region
edits, which a single-site expression language cannot express at all.

## 4. The single plan, and what was rejected

**Plan (one player): acceptance closure.** Treat each candidate repair as a relation between the
machine's reading at the origin of the run and its reading at the end. Execute real plans; keep the
states a literal goal accepts and a stronger judge refuses (`HOLE`) and the states both accept
(`LEGITIMATE`). Select the smallest conjunction of preservation laws that accepts every legitimate
state and refuses every hole. Store it externally, evaluate it on unseen damage kinds in a different
repository, and enforce it as an extra conjunct in the planner's verdict. No parameter, no model,
no predicted transition.

**Rejected, with reasons:** a learned transition model (a copy *is* the successor, no prediction
needed); a larger action vocabulary (the repertoire is re-derivable in 47 s, and more actions
enlarge the space a point must identify); statistical pruning on learned conditions (it lost one of
seven real tasks in the prior round — unsound deletion is worse than a slower search); storing more
demonstrations (breadth saturates at two residual statements); asking the owner (the question is
about machine states and can be answered by executing them); weights (would turn an inspectable law
into a memorised fact and violate §2).

**Design killed before acceptance:** the first version compared only the immediate pre-state to the
post-state. The real hole was a *run* — stash dropped one step, cleanup later — so the law saw no
loss and accepted it. The judgment now stores the origin reading. A second defect was a dedup key
that collapsed staged and unstaged changes, hiding the legitimate repair; both are now regression
tests. A third defect evaluated laws on child directories that had been deleted after dedup; the
laws are now pure functions of two readings.

## 5. Build and honest measurements

`goal_closure_v1.py` reads refs, branch head, file bytes (target tree, worktree, stash), index
membership, status codes and ancestry from real git commands. Five generic preservation laws are
written in the algebra; none names a task, a file or a commit. Selection is exhaustive over
subsets by increasing size and keeps all ties.

| measurement | result |
|---|---|
| Training rows (packaging, 3 damage kinds, depth 3) | 5 holes, 10 legitimate states |
| Minimal closure from those rows | 1 law: `ref_preserve` |
| Held-out (different repo, two **new** damage kinds, depth 6) | 20 holes, 13 legitimate states; **0 false accepts, 0 false rejects** |
| Planner with closed goal (held-out task) | solved in 17 edges; literal goal also solved in 17 — the closure cost nothing here |
| Coverage wall: literal goal on rescue tasks | 106 weak-only states, 0 states satisfy both; literal goal is *contradictory*, not merely incomplete |
| Same arm after repairing the literal goal (allow a rescue commit) | 145 judged rows, 6 legitimate; unique minimal closure = 3 laws (`ref_preserve`, `tracking_preserve`, `stash_restore`); 0 false accepts/rejects on training and on 126 held-out hole rows / 13 legitimate rows |
| First closure applied to rescue rows without retraining | **16 of 106 holes accepted** — an honest failure, reported as one |
| Model calls / parameters / predicted transitions | 0 / 0 / 0 |

All seven declared criteria A1–A7 in the receipt are true in this producer run. That is **not**
independent verification and not acceptance credit: the judge was supplied by this project, the
search is bounded, and only two repositories and seven damage kinds were used. The earlier "all
green" claims in this repository were retracted for exactly this kind of overreach.

`python3 -m pytest canonical/tests/test_goal_closure_v1.py -q` → **8 passed** on real local git
repositories, no network. The full measurement reruns in about two minutes:
`python3 canonical/tools/goal_closure_v1.py --receipt <path> --store <path>`.  The store test
deletes the file and shows that knowledge is gone while the mechanism is unchanged.

## 6. What is still missing, and the next loop

1. **Judge coverage.** Arm 1 proves that a closure learned from one task class silently misses the
   stash class. The next bottleneck is a *coverage test*: given the current laws, enumerate the
   classes of states in which a hole could live and report which classes have zero judgments,
   before claiming transfer. That is a falsifier, not another law.
2. **Multi-region repairs.** The five laws decide *whether* a plan is acceptable; they do not
   synthesise a two-region edit. The prior round's 8/30 real fixes remain outside any single-site
   grammar.
3. **Scale and environments.** No GUI, browser or unseen desktop application was touched here.
   The current hardest open benchmarks are OSWorld 2.0 and SWE-bench Pro [2](https://capitalandcompute.net/ai-benchmarks/),
   and nothing in this receipt is a score on them. §6 "done" is therefore **not met**; this is a
   verified-narrow mechanism, not a solution to computer use.

**Honest status:** one bottleneck removed in a bounded domain; the mission remains open.
