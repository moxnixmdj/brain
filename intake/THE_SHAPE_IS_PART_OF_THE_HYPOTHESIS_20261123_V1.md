# The shape is part of the hypothesis

**Date:** 2026-11-23 · **Branch:** `arena/eac85348-brain` · **Round:** 2 of the interrogation line
**Authority:** NONE__PRODUCER_RUN_SANDBOX · **Model calls:** 0 · **Network:** 0 · **Parameters:** 0
**Instrument:** `canonical/runtime/interrogation_v1.py` · **Tests:** `canonical/tests/test_interrogation_v1.py` (**37 passed, 8.7 s**)
**Receipt:** `intake/RECEIPT_INTERROGATION_20261123_V2.json` (supersedes V1, and says why)
**Superseded:** `intake/RECEIPT_INTERROGATION_20261123_V1.json`

---

## 1. Requirements I am bound by, restated

Own model, own runtime, **zero model calls**, **no parametric warehouse of world facts**, every
parameter derived and justified, instant knowledge from an external and deletable store,
learning from a single experience, hardest honest tests, no borrowed output, no hand-solving,
research project-then-web before building, kill a design before implementing it, "the best
part is no part", verified / unverified / failed kept apart, one branch, merge once,
`truth.achieved` stays `false`.

**§2 resolved, unchanged.** Forbidden: parameters as a lookup of memorized facts, and any
runtime model dependency. Allowed: an external store the system computes with, written from
single experience. Test: knowledge removable without retraining. Everything written this round
is either derived in a fraction of a second or disposable.

---

## 2. What the project already had — and the two numbers that decided this round

Searched exhaustively before building: `function_the_task_text_points_at_v1`,
`file_the_task_text_points_at_v1`, `quoted_in_the_task_text_v1`, `fix_shape_v1`,
`tests_as_the_judge_v1`, `bounded_imperative_directive_semantics_v2`,
`objective_relevance_bm25`, plus everything in the previous round's list.

The project had already **executed real benchmark tasks**, which is the thing that matters most:

| record | what it is | the number that decided this round |
|---|---|---|
| `CANDIDATE_UNDER_THE_TASKS_TESTS_SWEBENCH_VERIFIED_DJANGO_20261113_V1.json` | 231 Django tasks of SWE-bench Verified, **2 422 candidates actually run under the tasks' own tests**, no model call, 2 cores, no Docker | **1 submission resolves 5**; first 20 hold a resolving candidate for 7; as high as 20 for 10 tasks; **another task's text: 0**; **96 tasks make no candidate at all** |
| `RESOLVING_CANDIDATE_UNDER_THE_WHOLE_SUITE_…_20261113_V1.json` | the same candidates under each project's *whole* suite | 6 of 7 keep the whole suite; 1 breaks 8 tests elsewhere |
| `FUNCTION_FOUND_FROM_TASK_TEXT_…_20261112_V1.json` | file and function localisation from task text, 500 tasks | file named in **68%** of tasks; reached with the file given: **10 of 500**; 141 empty candidate lists in that corpus, **67 because the issue text contains no call**; I measure **141/158** declarations naming nothing in the algebra below — the same distribution in a different guise |

Its own verdict, written before this round: *"work on WRITING the change, counted by the tests
and not by the text of somebody's patch."* That is the real limiter, and it is not
identification in general.

So I did not attempt a benchmark that cannot be run here. The Chinese wall is real: this
sandbox has **no Docker and no network at measurement time**, and the benchmark repos are
not on disk. What I did instead was attack the mechanism whose defect the last round's own
receipt recorded as a failure.

---

## 3. The frontier, as input only

- **OSWorld 2.1**: 108 long-horizon workflows; best published binary 48.7, partial 81.8.
  The gap is constraint tracking and verification, not GUI control.
- **Terminal-Bench 4.0**: leader 64.8.
- **Agent-Diff** (arXiv 2602.11224): docs help pass rate but not partial score; no-docs agents
  discover by probing. Probing over reading.
- **"Sampling Is Not Curiosity"** (arXiv 2611.10501, 19 Nov 2026): nearly all agents merely
  sample; a genuine investigate loop needs prediction → selection → hypothesis tracking.
- **GNU `fold`, `sort -g`, `sort -V`**: measured on the host. The documentation is thin and,
  for `sort -V`, explicitly says the comparator is not transitive.

Nothing above became a runtime dependency.

---

## 4. Verdict on §3, and the bottleneck this round actually fixed

**The message's idea is right and the measurements keep confirming it in a sharper form each
round.** Not "scan everything and fetch the unknowns" — that is a cache with no bound. The
part that works is: *make the question computable from the competing readings.* And this
round found the *second-order* version of that law, which is the real content of the round:

> **The shape set is part of the hypothesis, not the evidence.**

Last round I wrote that sentence and then did not act on it. This round two facts forced it:

1. `fold -b` was certified `identity`, survived the whole design space, and was **falsified**
   the moment the world handed it a line longer than 80 bytes. Cause: every shape was shorter
   than the width the declaration names.
2. `sort -g` was certified as `sort_num` in the last receipt and **survived held-out**, yet it
   differs from `sort -n` on **383 of 400** random numeric inputs, because `-n` reads `1e3` as
   1 and `-g` as 1000. Cause: no shape contained an exponent.

Both are one defect: **a parameter a declaration names, that no shape exercises.** The fix is
not more shapes — it is a *computable* test.

---

## 5. The build

`canonical/runtime/interrogation_v1.py`. Nothing branches on a tool's name.

**5.1 The adequacy gate — the law, made mechanical.**
`PARAMETER_WITNESS` records, per primitive, the two settings of each parameter and the shape
that separates them. `parameter_exercised(name)` returns whether some shape in the space
actually prints different bytes under those two settings. A declaration naming an unexercised
parameter returns `REFUSED__PARAMETER_NOT_EXERCISED_BY_ANY_SHAPE` — refused **by name**, never
certified on faith. This is "the best part is no part" applied to a certificate: the gate is
twelve lines and removes a whole class of false confidence.

**5.2 The primitives had to become exact, and four measurement rounds were needed.**

| primitive | first attempt | after measuring | final |
|---|---|---|---|
| `fold_columns` | byte count as column | 107/2800 wrong | **0/2100**, every byte 1–255 |
| `fold_bytes` | column math | 51/800 wrong | **0/2100** — a plain byte count: a tab and a backspace are one byte each and neither moves a column |
| tab | width only | — | advances to the next multiple of 8 |
| backspace / CR | ignored | — | steps back one column / returns to column 0 |
| boundary | cut *at* the crossing byte | off by one | cut **after** the byte that brings the column to the width |
| `sort_general` | float compare | wrong on overflow, nan, hex, non-numbers | **0/700** on the numeric domain; 0 on hex and signed nan are named as outside its claim |

Each rule was found by **shrinking a failing input**, not by reading documentation. That is
the only method here that has ever worked: my model of a program is wrong far more often than
the program is.

**5.3 A primitive I could not specify is removed, by the law already in the module.**
`fold -s`: five separately measured break rules each still left hundreds of inputs wrong (539
of 2100 at the last). Recorded in `_FOLD_SPACES_RECORD` and refused by name, exactly as
`sort -V` was removed for an intransitive comparator. A transform that cannot be specified
exactly does not enter the hypothesis space, because its presence manufactures false
certificates.

**5.4 The search got an exact quotient and a real speedup.**
`goal_quotient()` groups readings by what the goal can ever observe; the exact minimax search
runs over those classes. `optimal_move()` is keyed on classes with a precomputed outcome
table. Measured: **52 s → 2.2 s** for the root move; the whole 158-surface sweep **61.8 s →
5.2 s**. The tree search now reports `UPPER_BOUND_ONLY__NODE_BUDGET_EXHAUSTED` when its cap is
hit, and a test pins that the cap-free search plateaus at the same number, so a budget-limited
`None` can never be read as a proof.

**5.5 Greedy is now measurably worse than exact.** Greedy 6, exact 5. Last round they tied at
4. The first round in which the exact policy actually buys something.

**5.6 The declaration vocabulary now reaches the folding primitives**, so the gate can fire on
a fold declaration instead of the surface being refused for the wrong reason ("names nothing
in the algebra").

---

## 6. Measurements, including the failures

**Final sweep — 158 declared surfaces across 20 GNU text filters, `LC_ALL=C`, 5.2 s:**

| outcome | v1 (last round) | **v2 (this round)** |
|---|---|---|
| CERTIFIED and survived held-out | 10 | **11** |
| CERTIFIED and **falsified** | **1** (`fold -b`) | **0** |
| NOT_IDENTIFIABLE / OPEN, named | 6 | 6 |
| REFUSED by name | 141 | 141 |
| witnesses spent (vs naive) | 25 (132) | **37 (176)** |
| total wall clock | 61.8 s | **5.2 s** |

Certified, with cost and class:

| surface | witnesses | bound | greedy | class | held-out |
|---|---|---|---|---|---|
| `sort -d` | 5 | 5 | 6 | `sort_dict` | survived |
| `sort -g` | 4 | 5 | 6 | **`sort_general`** (was wrongly `sort_num`) | survived |
| `sort -M` | 4 | 5 | 6 | `sort_month` | survived |
| `sort -n` | 4 | 5 | 6 | `sort_num` | survived |
| `sort -r` | 5 | 5 | 6 | `sort_lex_desc` | survived |
| `uniq -c` | 3 | 5 | 6 | `count_runs` | survived |
| `wc -c` / `-m` | 2 | 5 | 6 | `count_bytes` / `count_chars` | survived |
| `wc -l` | 2 | 5 | 6 | `count` | survived |
| `wc -w` | 2 | 5 | 6 | `count_words` | survived |
| `fold -b` | 4 | 5 | 6 | **`fold_bytes`** (was wrongly `identity`) | survived |

**Design space:** 16 shapes, 63 behaviours, exact optimum **5**, greedy **6**, naive 16.
Independently confirmed by a cap-free checker: **4 is impossible, 5 is achievable.**

**Failures, stated as failures**

- The v1 receipt is **wrong on two counts** and is superseded. `fold -b` was certified
  `identity` and `sort -g` was graded `sort_num`. Both are recorded in the v2 receipt's
  `why_a_v2` rather than quietly overwritten.
- My `_fold` was wrong **four times** before it was right, and my `_general_key` **five times**.
  Every version passed a small hand-picked test set; every one failed shrinking.
- A brute-force checker I wrote to validate the exact search was **itself wrong** (it re-split
  a branch on an already-answered shape). The module was right and my "independent" check was
  not — a reminder that an oracle needs the same scrutiny as the thing it judges.
- `fold -s` is removed, not approximated.
- `sort_general` is exact on the domain it claims and **not** on hexadecimal literals or signed
  nan; the docstring says so and the receipt repeats it.

**Unverified:** anything about GUIs, browsers or images; any frontier benchmark score. This
sandbox has no display, no Docker at measurement time, and no benchmark corpora on disk. **No
OSWorld, Terminal-Bench or SWE-bench number is claimed.**

---

## 7. The one plan, with the ideas that were rejected

The loop, unchanged in shape and now with the gate in it:

1. **Read the declaration** of the surface. Refuse by name if it names nothing in the algebra,
   demands an argument, or **names a parameter no shape exercises**.
2. **Scan** the default form once per shape, as a control that attributes outcomes.
3. **Enumerate** readings over a closed algebra whose primitives declare their input domains.
4. **Ask the exact-minimax witness** over unasked shapes; stop when every survivor agrees on
   every shape the goal can produce.
5. **Falsify out of space** on adversarial inputs; a disagreement blocks storage.
6. **Store** keyed by `(bytes, name, surface, goal)`; re-run the evidence on every reuse.

| rejected this round | the measurement that killed it |
|---|---|
| Add a shape only when a certificate fails | this is what produced both v1 failures — the shape arrives *after* the false certificate has been stored and believed |
| Approximate `fold -s` with the best of five rules | 539 of 2100 still wrong; an approximation inside the hypothesis space manufactures certificates |
| Compare `sort -g` in floats | `1e999` sorts below `inf`, so the arithmetic must be exact (`Decimal`) |
| Keep the class-agnostic search and just raise the node cap | 52 s and 200 000 nodes for a 2.2 s question; the quotient is the fix, not the budget |
| Report the node-capped optimum as the optimum | the cap can return `None`; it now says `UPPER_BOUND_ONLY` and a test pins agreement with the cap-free search |
| Trust the project's existing localisation numbers | I re-derived the same distribution independently (141/158 declarations naming nothing) instead of quoting them |

**Expansion rule, applied honestly.** *GUI/browser*: ① no storage-boundary change; ② the same
skeleton with the accessibility tree as the declaration; ③ the visual primitives are a real
addition and are **not claimed**; ④ refuse by name what is not declared; ⑤ no constraint
broken; ⑥ **not verified — no display in this sandbox.** *Web as knowledge source*: unchanged,
and still bounded — the machine-readable tier answers existence, version and digests, prose
answers nothing a zero-model-call system can check.

---

## 8. Honest state and the next bottleneck

- **Verified:** the adequacy gate; two primitives now exact on measured domains
  (0/2100 and 0/700 mismatches); 11 surfaces certified and held-out-survived with **zero
  falsifications**, where the same sweep falsified one last round; the exact optimum (5)
  confirmed by a cap-free search; a 12× speedup with the same answers.
- **Unverified:** GUI, browser, image, network; every frontier benchmark; whether 16 shapes are
  *sufficient* rather than merely adequate for the 63 readings they now separate.
- **Failed:** two false grades in the previous receipt; `_fold` wrong four times;
  `_general_key` wrong five times; my own "independent" oracle wrong once; `fold -s` removed.
- `truth.achieved` remains **false**.

**The next bottleneck, named.** The gate now catches an unexercised parameter *inside* the
algebra. It cannot catch a primitive **missing from the algebra altogether** — which is what
`fold` was for a whole round: no shape could reveal it, because no reading in the universe
performed it. Closing that requires generating candidate primitives from the declaration's own
verbs rather than from a hand-written table, and falsifying them against the program. The
measurable test for it is concrete: *on the 88 declarations currently refused as "names nothing
in the algebra", does verb-derived primitive generation produce a candidate that survives
held-out on at least some of them?* If yes, the algebra stops being the ceiling. If no, the
honest conclusion is that most declared surfaces are not parameterised transforms at all, and
the refusal was already correct.


---

## 9. Round 3 — the refusal class was the next bottleneck, and it was not what I assumed

The gate catches an unexercised parameter *inside* the algebra. It cannot catch a primitive
**missing from the algebra**. So I read the 85 declarations still refused as "names nothing in
the algebra" instead of quoting the number.

**What they actually are.** Fourteen examined. Four named a transform the algebra genuinely
lacked. The rest named parameters I could not construct an input for, and I wrote that down as
"invisible at the default width" — naming `sort -b` and `sort -i` as examples.

**CORRECTION (V4).** That sentence was false. Both parameters are visible; I had not looked
hard enough. A searched witness finds `b" ab\nAB\n"` for `sort -b` and `b"\tab\nAB\n"` for
`sort -i`, and both are now certified in 4 witnesses each and survive held-out. The error is
the one this document is about: I reported a failure of my search as a property of the
program. "No witness was found" is the only claim a failed search supports.

**Added, each verified exactly against the host before it entered:**

| primitive | behaviour | exactness |
|---|---|---|
| `uniq -i` → `uniq_fold_case` | a case-folded run keeps its **first** member | 0 / 700 |
| `uniq -d` → `dedupe_repeated` | one line per repeated run | 0 / 700 |
| `uniq -D` → `dedupe_all_repeated` | every member of a repeated run | 0 / 700 |

**Refused by name, with the measurement recorded: `sort -f`.** This one cost me eight
candidate keys, each falsified against the host:

1. `bytes.lower()` as the key — wrong on `_` and `[`;
2. a hand-built rank table over printable ASCII — wrong on `"aA"` vs `"AB"`;
3. the same with a low-cased tie-break — still wrong on that pair;
4. five variants between them.

Its *ranking* over printable ASCII is measurable and I measured it exactly
(` !"#$...@AaBbCc...Zz[\]^_`{|}~`). The ranking turns out not to be the behaviour: two lines
that fold equal are ordered by something no folded key reproduced. That is the **same
structural finding as `sort -V`**, so the same rule applies and the record says why:

> A comparator that is not a key function cannot be a member of a hypothesis space whose
> members are key functions.

**A bug in my own reporting, found by a test I wrote for something else.** `optimal_move`
scored unsplittable shapes with a `1 << 30` sentinel, and that sentinel leaked out as a
*reported worst-case bound* — `1073741825` printed next to eleven certificates. Fixed in two
places; a test now asserts no score in the ranking can be a sentinel. This is the second time
in two rounds that a number I printed described something other than what its name claimed.

**Measured, final:**

| | v1 | v2 | **v3** |
|---|---|---|---|
| certified **and** held-out survived | 10 | 11 | **14** |
| certified and falsified | **1** | 0 | **0** |
| shapes / behaviours / primitives | 12 / 36 / 17 | 16 / 63 / 21 | **18 / 86 / 24** |
| optimum vs greedy | 4 vs 4 | 5 vs 6 | **5 vs 6** |
| witnesses spent (naive) | 25 (132) | 37 (176) | **60 (252)** |
| sweep wall clock | 61.8 s | 5.2 s | **11.1 s** |
| tests | 25 | 37 | **40, in 14.5 s** |

**Honest state.** 85 declarations remain refused; some are genuinely outside a text-filter
algebra (`jq`'s slurp and raw verbs), some are invisible at default width, and I have not
classified all 85. Shapes are still hand-chosen — two were added this round because a refused
declaration *named* the missing witness, which is better than guessing but is not a proof of
adequacy. `truth.achieved` remains **false**. No GUI, browser, image or frontier benchmark is
measured or claimed.

**Next bottleneck, sharper than last time.** The law "a parameter is exercised only if two
settings of it disagree on some shape" is computable *because I supply the two settings*.
That is the residual weakness, and it was real: `sort -b` was invisible not because it does
nothing but because I constructed no input where leading blanks change the order.

**DONE IN V4, and it cost me two false certificates to learn why it was not enough.** Searching
for a witness input does find them — `sort -b` and `sort -i` are primitives after all. But the
search also found a third case nobody had asked about: a witness can EXIST and still not be in
the design space, which is `fold -b`'s failure mode one level down. The gate now refuses in
that case and attaches the witness. And then the reverse: a shape can split the design space
while the declaration that named it describes something else entirely, so `sort -V` ("natural
sort of version numbers") and `sort -c` ("check for sorted input; do not sort") were certified
as transforms they are not. A positive vocabulary alone cannot refuse; the refusal has to be
keyed to the surface's own words.
