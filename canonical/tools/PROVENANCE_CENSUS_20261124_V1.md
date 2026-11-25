# The repair site is on the executed path 73.5% of the time

**Status:** localisation measured; the bottleneck moves from localisation to the repair operator.
**Authority:** NONE (producer-run sandbox). **Model calls at decision time:** 0.
**Corpus:** `real_fix_pairs_20261119_V1.json`, 68 well-formed of 87, judged by each repo's own tests.

---

## §1 Why this measurement

Every repair mechanism measured on this corpus succeeds exactly when the test names the site and
fails when it does not:

| mechanism | solved | what named the site |
|---|---|---|
| local arm (traceback) | 1/56 | the raise line — but 77% of tracebacks never reach repo code |
| witness inversion (return site) | 0/79 | the site was right, the target value was junk |
| guard synthesis | 0/27 | the frame was never entered from the failing test |
| literal repair in a guard | 1/6 | the exception named the guard, the guard named the literal |

So localisation looked like the wall. But that inference has a hole: "the traceback does not name
the site" is not "the site is not on the path". Those are different claims, and only the first
had been measured.

`real_fix_provenance_census_v1.py` measures the second, and it is **judge-side by construction**:
it computes which functions the upstream fix changed (using `after`), traces the single failing
node, and asks whether a changed function actually ran. **It is a measurement of whether a signal
exists. It is not a solver and it produces no repair.** Any repair number derived from it would be
a forgery.

---

## §2 The census

| localisation class | n | share |
|---|---|---|
| **one function modified, and it is on the path** | **26** | **38.2%** |
| several functions modified, at least one on the path | 24 | 35.3% |
| **pure constant** — no function changed at all | 7 | 10.3% |
| pure addition — the fix only adds functions | 4 | 5.9% |
| modified but off the executed path | 4 | 5.9% |
| no calls recorded (import-time failure) | 3 | 4.4% |

**The modified function is on the executed path for 50/68 = 73.5% of tasks.**
Only 5.9% are genuinely unreachable by tracing, and 4.4% record no calls at all.

Two structural facts fall out that change the plan:

1. **38.2% of tasks are a single function on the path.** Not "a hunk", not "a file" — one named
   function that the failing test demonstrably executes. That is a far smaller target than any
   previous census suggested.
2. **10.3% are pure constants** — no function body changes at all. That is exactly the class the
   regex-boundary repair hit (`_validate_regex` is a module-level `re.compile`). It is a real,
   separate class, not a rounding error.

### The path is short

Mean **21.5 distinct functions** on the path. So the localisation problem is not "find the site in
a repository of 18,000 files" — it is "pick 1 of about 21".

### And ranking by anything cheap fails

| heuristic | top-1 accuracy |
|---|---|
| deepest call on the path | **0/65 (0.0%)** |
| last call before the assert | **0/65 (0.0%)** |
| first call into repo code | **0/65 (0.0%)** |

The repair function sits at **median rank 6 of ~21** when ranked by depth. Top-k coverage:

| k | coverage |
|---|---|
| 1 | 0% |
| 2 | 18.0% |
| 3 | 32.0% |
| 5 | 50.0% |

**Conclusion: localisation does not need to be solved, it needs to be enumerated.** At k=5 the
path enumeration already contains the repair site for half the corpus, and at k≈10 for most of it.
No heuristic is required; the real test is the selector.

---

## §3 The arm that tests this, and its result

`--arm path`: trace the failing node, take the functions it actually entered, mutate the literals
inside each (deepest first, top 6, ≤24 per function), hand every variant to the harness to judge
against the recorded nodes and then the whole test file as a failure-subset test. It never sees
`after`.

| | |
|---|---|
| tasks attempted | 11 well-formed |
| candidates tried | 4–12 per task |
| **solved** | **0** |

**0/11.** Honest, and informative: the path enumeration is cheap and reaches 73.5% of the corpus,
but the only literal operator that has ever worked here is the regex-boundary family, and that
fires on roughly 1 task in 68. **The bottleneck has moved from localisation to the repair
operator.** Enumerating 21 functions does not help if the operator cannot express the edit inside
any of them.

---

## §4 What this establishes, and what it does not

**Established, by execution:**
- The repair site is on the executed path for **73.5%** of tasks, and confined to **one** function
  on the path for **38.2%**.
- The path is short (mean 21.5 functions), and cheap ranking heuristics are worthless (0% top-1),
  while top-5 enumeration covers 50%.
- Literal repair over the enumerated path solves **0/11** — so the operator, not the localiser, is
  now the constraint.

**Not established:**
- That any operator can repair the 26 single-function-on-path tasks. That is the open problem and
  it is now precisely posed: *given one function that the test executes and a real oracle, produce
  the edit inside it.* Nothing here solves it.
- Anything about benchmark performance. The honest measured baseline remains
  SWE-bench Pro V2 **0/3** on `arena/b81b2217-brain`, with nop 0/3, oracle 3/3, both gates PASS —
  and that document's own verdict is *"§6 met: NO. Not close."*

**§6 is not met.**

---

## §5 Method and integrity

- `changed_functions` compares each function's unparsed source between `before` and `after`, and
  splits `modified` / `added` / `removed`. **Only `modified` can appear on the path of a before
  run** — a function the fix *adds* is unreachable by definition, so folding it into one "changed"
  set made every task that adds a helper look off-path when it was not.
- The tracer records `(module, function, depth)` for every call into repository source, bounded by
  **uniqueness** rather than by call count. An earlier 64-call cap was binding on nearly every task
  and silently hid every call after the 64th, which made the path look far shorter than it is.
- Qualified names are not observable at runtime, so matching is on leaf names. That is a real
  over-approximation and is stated rather than hidden.
- 3 tasks record no calls because they fail at import time; they are reported as their own class,
  not dropped.
