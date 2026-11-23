# §3 verdict, and the one plan

**Authority:** NONE · `truth.achieved` = `false` · **$0**, 0 model calls · 62 tests pass

---

## §2 — confirmed and resolved

I am bound by: own model, **zero model calls at runtime**; **zero knowledge house** (parameters
hold only computed, justified mechanisms); knowledge in the **external store**, addable and
removable without retraining; never stop before §6; research before building; "the best part is
no part"; honesty over encouragement; one branch.

The contradiction (persistence vs. zero knowledge house) is resolved by a boundary that is
**tested, not asserted**:

| | evidence |
|---|---|
| the store holds **4 floats** + provenance | `learned_ranking_store_v1`; a test asserts it contains no names and no facts |
| deletion provably removes the behaviour | `test_deletion_removes_the_behaviour` |
| an empty store ranks **nothing** — it fails closed | `test_empty_store_ranks_nothing` |
| weights are derived by grid search over observed outcomes | `fit()` |

Knowledge outside the weights, removable without retraining, weights holding only a computed
mechanism. The boundary holds.

---

## §3 — the verdict on "instant learning in a new environment is solved"

**It is half solved, and the half that is solved is not the half I previously claimed.**

### What is real, measured

**1. Adaptation by probing is real, and its crossover is measurable.** Atoms can be **opaque** —
named `FS_A1`, carrying no meaning — and what they do is learned by executing once and reading
the machine's own before/after state (`instant_learning_in_a_new_environment_v1`, four real
machines). Adapting once beats learning each request from the **second or third request onward**,
and is **strictly worse for the first request, always**, because measurement is a fixed tax and
a demonstration is not. That is the honest shape of the claim, and it is the opposite of
"solved".

**2. A warm environment visit is 253× cheaper, with identical answers.** Scan → retrieve → ask →
abstain, on a host never seen: 21.0 s cold, **0.083 s warm**, same answer set. The mechanism is
that a **read** page is a fact.

**3. Abstention is a first-class result and it is free.** `/usr/sbin` ships no `gzip`, `bzip2`,
`xz` or `tar`. The system says so for the cost of one 48 ms scan, instead of confidently recalling
a program that is not there. This is the single most under-appreciated result in the whole chain:
**knowing that you do not know is computable, and it costs nothing.**

**4. Knowledge of an artifact's own declarations solves hard unseen problems.**
35/40 on a two-library no-dependency subset, including one item solved by a **different correct
body** than the reference (`diameter(G)`, `list(G.adj)`, `greedy_modularity_communities(G)`).

### What is NOT real, measured

**5. Predicting behaviour from documentation scores 0/45.** 429 learned records reduce to 74 with
any substantive role pattern; the largest class has **consistency 0.33 across 7 patterns**.
Documentation classifies; it does not answer.

**6. Identity does not transfer.** Across two real hosts: **3 of 216 names** overlap (1.4%).
A store keyed on identity is worth almost nothing across environments. The user's own worry —
"his actions will probably never be needed again" — is **correct and worse than intuition**.

**7. The derivation reaches very little on a new host.** Only **4 of 216** programs even mention a
role word in their help output.

### The three statements I must withdraw

> ~~"we already solved instant learning in new arbitrary environments"~~

Not supported. What is supported is a **cost law**: adaptation is O(machines × adaptation) +
O(requests), a change of **currency** from requests to environments, not a solution.

> ~~"188/194 are the meaning→name convention and are not derivable"~~

Wrong. `to_int`, `todok` and `to_list` are members of the **declared type's own `dir()`**. What was
missing was **rank**, not reach. Solved.

> ~~"35/31/32/186/200 are out of scope by construction"~~

Wrong. A truncated expression made `parameters()` return `[]`, so those items were unreachable for
**every** candidate. A parser bug wearing the costume of a capability limit. Solved.

### The real bottlenecks, in order

1. **The vocabulary of questions is chosen, not derived.** 5 English role words for a filesystem
   family. A general environment needs the question derived from the goal and the artifact —
   unsolved.
2. **Documentation classifies but does not answer**, so every new environment still pays the
   adaptation tax per atom.
3. **Nothing here has a display.** Every measurement is CLI, API or filesystem. GUI/browser is
   untested by this system, and the literature's number for unseen UIs is 0–10%.

---

## §4 — the one plan, minimal

The plan is **one loop, three parts**, and every part already has a measured number.

```
1  SCAN      the artifact's own declarations       48 ms / 216 programs; 41,523 API symbols
2  ASK       only what the scan cannot answer      one bounded question per unknown
3  SAVE      the question and the read-set        8,240 bytes, not 190,845
   VERIFY    the environment's own reader, always  hidden test / exit code / file bytes
```

**Why this is the whole plan and not a component of one:** the two strands of this work turned out
to be *the same loop*, and that is the only insight in this document that is new rather than
measured:

| | library environment | filesystem environment |
|---|---|---|
| atoms | API symbols (41,523) | programs (216–635) |
| declarations | docstrings, annotations, signatures | `--help` pages |
| reader | the benchmark's hidden test | the file's own bytes |
| memory | the ranking weights + corpus | the read-set |
| measured | **35/40** | **253× warm** |

Nothing in the loop is a learned world fact. The scan is computed, the question is a closed
vocabulary, the memory is a read-set, and the reader is the artifact's own verdict.

### Rejected, with the reason

| rejected | why |
|---|---|
| Store a fact per program per role | 190,845 bytes for 429 transcriptions; 1.4% survives a host change |
| Predict flags from a verb class | **0/45** on unseen programs; the largest class is 33% self-consistent |
| Trust documentation as the answer | same measurement — docs classify, they do not answer |
| Store negative answers per program | 622 identical negatives; one read-set says the same thing in 8,240 bytes |
| Store the content digest | recomputed by the 48 ms scan; ~17 KB of pure redundancy |
| Use a model for "understanding" the page | forbidden at runtime, and unnecessary — the page is already a declaration |
| Memorise prose descriptions | 21.5 KB of help-page sentences; the definition of a knowledge warehouse |
| Keep 35/40 as the headline | it is 87.5% of a **40-item two-library no-dependency subset**, not a benchmark score |

---

## §6 — where this stands, without softening it

`truth.achieved` = **`false`**.

Met: zero model calls; zero knowledge house with a tested boundary; instant knowledge external,
removable, provably load-bearing; 35/40 on hard unseen library problems; a 253× warm environment
visit with abstention.

**Not met:** a single-experience learning claim verified on unseen environments at scale; any
GUI/browser measurement; the question vocabulary derived rather than chosen; and performance on
the full hardest open benchmarks (SWE-bench Pro, Terminal-Bench, OSWorld-class) with this system
running alone. Until those run, this is progress with its ceiling measured — **not completion**.
