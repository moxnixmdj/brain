# Where the observable was missing — and where our fast oracle lied

**2026-11-16 · branch `arena/5a03fe74-brain` · 9 of the 40 QuixBugs bugs · no model, no weights, no network**

Receipt: `canonical/verification/WHERE_THE_OBSERVABLE_WAS_MISSING_20261116_V1.json`
Tool: `canonical/tools/repair_where_the_suite_is_the_observable_v1.py` (3 tests)

---

## The defect being fixed

Nine of the forty QuixBugs bugs ship **no `json_testcases` file**. Their cases are objects and
assertions inside their own `python_testcases/test_<name>.py`: a `Node("Westminster")`, a graph, an
assertion about a printed sentence. The examples-based repairer therefore reported `NO_EXAMPLES` on
all nine and **never searched them at all** — one appeared in the identification run as
`TOO_FEW_EXAMPLES`, six as `NO_EXAMPLES`.

That is mechanic 2 in the user's own list, and it is worth naming precisely: *the causal observable
was missing from the representation, so repetition could not separate success from failure.* There
was nothing to separate. No budget, no depth and no better learner changes that.

## What was done, and what it bought

For exactly those nine tasks the corpus's own test file became the observable: candidates from the
same five rewrite families are screened against the untouched test file through the tree's existing
confined screen (copy-on-write workers), and any survivor is then judged by the corpus's real
`pytest` on a fresh copy — the same judge every other measurement here uses.

| outcome | tasks |
|---|---|
| repaired | **0 of 9** |
| no candidate survived the screen | 6 (minimum_spanning_tree, reverse_linked_list, shortest_path_length, shortest_path_lengths, shortest_paths, topological_ordering) |
| **the screen accepted, the corpus's pytest refused** | **3 (breadth_first_search, depth_first_search, detect_cycle)** |

So fixing the missing observable made these bugs *searchable* and repaired **none** of them. Six
thousand candidates per task, five families that reach 18 of the other 31 — and on this nine they are
blind. **The observable was necessary and it was not the binding term.** That is the vocabulary wall
again, now measured on the tasks that had the alibi of a missing representation.

## The finding that matters more than the zero

`3` candidates passed the fast in-tree screen and then **failed the corpus's own pytest**.

The screen runs the test file through a stand-in for pytest (`use_correct`, `run_slow`, `mark.parametrize`,
`skip`, `approx`) and a single generated test that runs every case. On these tasks it is **not faithful
to pytest**: it accepts programs the real runner rejects. Any number quoted from the screen alone is
inflated, and no number in this tree should ever be quoted from it alone.

This matters for the previous note's projection. The `26/40` union was computed from a receipt whose
fast arm went through this same screen (`asked_through: the_screen_then_the_benchmarks_runner` — that
tool does re-check, which is why its own numbers are labelled; but the screen is the part that scales,
and it is the part that leaks). **The union projection must be treated as an upper bound until it is
measured as one run with pytest as the only judge.** I am stating that against my own previous note.

## What is real, what is not — the standing answer, updated

**Real.** Permanent storage of a verified experience. One-demonstration generalisation on real code
(60.0% vs 15.0% cache). Admission that refuses a lesson which breaks a correct program. A
vocabulary-free synthesis that builds `(not depth)` from a failure in 0.2 s. Identification that
settles in ~1.31 chosen questions once the space contains the repair.

**Not real.** That one experience is a rule (~10 bits survive it). That more environments buy coverage
(2.5× compute bought 1 page in 37; 0/10 for a new *kind*). That the smartest actions are the missing
piece (an action list repairs 0/20; a learned vocabulary 1–2/20; cross-corpus kinds 20/40). That a
missing observable is the whole story (this receipt: making it present repaired 0 of 9). That any of
this is sentience (the only proxy is measured and small).

**The single bottleneck, unchanged and now bounded on both sides: the hypothesis space.** Not the
learner (it selects inside the space), not the budget (coverage is inelastic), not the oracle (this
receipt shows a *fast* oracle that lies). The space must contain the fix; when it does, one chosen
question finds it; when it does not, every other improvement is wasted motion.

## The smartest next moves, in the order they pay

1. **Make pytest the only judge in the composed run.** No union number, no arm, no screen result may
   be quoted without it. The screen may order candidates; it may never decide.
2. **Compose the arms under that judge** — hand-written families, synthesis-from-the-failure, learned
   kinds — and measure the union once. The projection is an upper bound; the measured number will be lower.
3. **Then grow the space, with the instrument as the router**: the identification tool already says,
   in one question, whether a task is space-broken or observation-broken. Nine of nine here were
   space-broken *after* the observable was fixed, which is where the next mechanism has to land.
4. **Do not add a sixth family by guessing.** The four audits so far all landed on the same conclusion:
   families are found by reading a refusal, never by imagining one.

## Non-claims

- 9 tasks, one corpus, single-function Python. Not general repair, not SWE-bench, not computer use.
- The screen was used to *order* candidates only; every verdict quoted is the corpus's own pytest —
  and the three disagreements are reported rather than dropped.
- Producer-run, one machine, authority **NONE**. No tolerance widened, `truth.achieved` unchanged.
