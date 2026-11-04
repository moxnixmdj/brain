# Refusing to Guess

**2026-11-04 · branch `arena/e55485af-brain` · authority NONE · `truth.achieved` false · $0 spent**

Sixth time asked, and this time I had no excuse left. Two documents ago I wrote that "the search
itself is the bottleneck and it is unchanged." I had never touched it. So this round does not add
another organ around the search — it changes what the search is allowed to claim.

---

## 1. The defect, read out of the code

```python
if sig == target_sig:
    return expr_src          # first match wins, and the search stops

if sig not in seen_sigs:      # the bank dedupes by OUTPUT SIGNATURE over the supplied inputs
    seen_sigs[sig] = expr_src
```

Two consequences, both fatal to ever knowing whether a choice was forced:

1. The **first** expression that reproduces the examples is returned. Nothing else is considered.
2. The candidate bank is keyed by output signature *over those same examples*. Two different
   programs that agree on the data are stored as one thing. **The bank could not represent "these
   both fit and they are not the same."**

So when the creature answered `x*x` for the examples of `2x`, it was not merely unlucky. It had
chosen, and it had no representation in which choosing was different from knowing.

---

## 2. Making multiplicity observable — and getting it wrong first

My first attempt swept `max_weight` from 1 upward and called the synthesizer once per weight. It
reported **exactly one** admissible body for every problem, and therefore `DETERMINED` for all of
them. That is the same vacuity as the substitution counterfactual two rounds ago: the mechanism could
not produce the other answer, so its agreement was meaningless.

The synthesizer needed a way to *not stop*. It now takes `collect_admissible=True`: every match is
recorded and the search continues. The default path is byte-identical — the first match still returns
immediately — and a test asserts both halves.

Measured on the three teaching examples of `2x`:

> **12 distinct admissible bodies.**

Eleven of them are the correct function written differently; one — `2 // (1 / x)` — gives `-6` where
the others give `-7` at `x = -3`. That is a genuine competing hypothesis, and the creature was
previously blind to all twelve.

## 3. What it does with the ambiguity

| | |
|---|---|
| one admissible body | **DETERMINED** — the data force the choice |
| several | **PROVISIONAL** — a choice was made, and the report says so |
| none | **UNRESOLVED** |

For PROVISIONAL it reports the chosen body, the competing ones, and a **witness**: an input where
two admissible bodies disagree. No expected value is needed to compute a witness — a disagreement is
a fact about the candidate set, not about the world.

**And the cost tie-break did not resolve it.** I introduced a graph-node cost so the cheapest body
would win a tie, and measured: **eleven of twelve tie at cost 6.** Simplicity bought nothing here,
and the report says so explicitly rather than letting a sort order look like a finding:

> `choice_margin: "chosen cost 6 vs next cheapest 6"` ·
> `cost_preference_is_defeasible: "a cheaper body is not a better-supported body"`

Two iterations of that cost function were also wrong before it worked: the first counted operator
and context leaves, so `/ 1` looked as expensive as a real operation and the cheaper correct body was
never reached. Found by printing the costs rather than trusting the chosen answer.

---

## 4. The part that is actually new: asking instead of guessing

A witness is a question. `what_would_settle_it` computes, for the admissible set, which inputs
separate them — and the loop is simply: pick a disagreement, get the value, re-enumerate.

```
step 0: admissible=12  PROVISIONAL  chosen (x/1)+x       asked x=-3, told -6.0
step 1: admissible= 3  PROVISIONAL  chosen (x/1)+x       no discriminating input left
```

**One answer removed nine of twelve explanations.** The loop then stopped, honestly: the three
survivors are *syntactically distinct and semantically identical* — they agree on every value this
module can formulate — so no further question exists. Reporting that as "done" would have been a lie;
the module reports residual ambiguity instead.

This is the capability I have been missing all session. Not a better evaluator — a mechanism that
knows when its data cannot decide, and can say what it would need.

**Pre-registered in `PREREG_EVIDENCE_DEMAND_20261104_V1.md`; 6/6 findings as predicted**, including
the one I got wrong on the first attempt and had to fix to make true.

---

## 5. The honest bound

**The values it asks for were supplied by the benchmark.** The loop shows the *form* of active
learning; the oracle in this run is me. A creature that must be told the value at `x = -3` has
learned to ask well, not to answer for itself.

**Uniqueness is not truth.** `DETERMINED` means the budget contained one admissible body. If the real
function lives outside the grammar, exactly one body may fit and be wrong. The powers-of-two case in
the benchmark makes this concrete and the report says it in words.

**The admissible set is bounded by the grammar.** A larger `max_weight` can always reveal another
explanation, so DETERMINED is a statement about a budget, never about the world.

**Non-claims.** No sentience. Pure Python over small numeric tuples; no I/O, no host execution, no
GUI; nothing here bears on reaching a shell or browser, which remain gated. `truth.achieved` stays
false. $0 spent.

---

## 6. Answering the question with the evidence I now have

Seven rounds, and the shape is finally legible:

| what the creature could not do | what fixed it |
|---|---|
| reuse a named sub-idea | concept invention |
| see two spellings as one idea | semantic unification |
| be wrong about its own parts | lifecycle + priors that fall |
| find which part failed | attribution by search ablation |
| certify only what is defined | totality gate |
| notice its own answer was suspect | structural self-audit |
| **know it was guessing** | **this round** |

Every one of those was a *check on the output of a search*, and the search itself — enumerate
candidates, match the examples, return the first — has not changed since round one. What changed is
that the search is no longer allowed to present its first success as knowledge.

That is why I can now answer "is this the smartest approach?" with something better than an opinion.
The deepest defect was never the grammar or the scoring. It was that **one example set was treated as
sufficient, everywhere, at every level** — the concept library certified on the subdomain that
survived, the synthesizer returned the first match, the audit trusted coverage, and I built six
instruments that each agreed with themselves. This round is the first that treats "how much do these
examples actually pin down?" as a computable question rather than an assumption.

Whether that is *sentient-like* I will not claim. But it is the first mechanism here that can be
surprised by its own ignorance, and that is closer to the thing the user keeps asking for than any
amount of better searching would be.

---

## 7. Ranked next moves

1. **Make the interrogation real, not benchmarked.** Wire `what_would_settle_it` into a caller that
   can actually obtain values — the observation surface the creature already has — so the oracle is
   the world rather than the file.
2. **Cost that reflects invariance, not node count.** Eleven of twelve bodies tie; the ones that tie
   are algebraically the same function. A canonicaliser would collapse them and leave one genuine
   competitor. That is the cheap version of "understand the expression", and it needs no oracle.
3. **Domain tracking instead of rejection** (carried over).
4. Repair rather than discard a refuted concept; composition of invented concepts; the front door.
