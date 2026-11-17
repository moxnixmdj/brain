# One demonstration amortises about a sixth of real work

*Measured on real history from five public repositories, 2026-11-16. Receipt:
`canonical/verification/SYSTEMATIC_EDIT_SUPPLY_20261116_V1.json`. Corpus:
`canonical/tests/fixtures/systematic_edit_corpus_v1.jsonl` (393 commits, sha256 `b47d9c9c…`).
Instrument: `canonical/swe_kernel/systematic_edit_supply_v1.py`. Reproduce in §7.*

## 1. The claim, and what it needs

"Do each advanced coding action once, and it is learned permanently; do that everywhere and advanced
software engineering is solved."

For a single change, that requires three things to hold at once:

1. **supply** — real work contains a *sibling*: another place where the same edit belongs, so the
   demonstration has somewhere to generalise to;
2. **determinacy** — one demonstration *determines* the transformation, so the sibling is produced
   rather than guessed;
3. **permanence** — the induced transformation survives the file moving under it.

Point 3 was measured in the previous change (`action_replay_under_change_v1`: 53.5% of 228 real
compositions stale, 31.1% silently corrupt). Point 1 and 2 had never been measured on real history.
They are now, against ground truth: the text the developer actually committed.

## 2. What was measured

Five real repositories — `pypa/packaging`, `pypa/pyproject-hooks`, `pallets/click`,
`pallets/itsdangerous`, `pallets/markupsafe` — sampled deterministically (every 6th non-merge commit)
into a pinned corpus of 393 commits, of which 268 contain reviewable hunks. For every commit that
touched **sibling sites** (the same edit shape in the same neighbourhood, with different concrete
tokens), one site is the demonstration: its edit is applied to the sibling's tokens, and the result
is compared byte for byte with what the developer wrote.

Every predicted token is marked with where it came from — *bound* from the target, or *copied* from
the demonstration because nothing in the target determined it. That marking is what separates a
prediction the demonstration **forced** from one that merely happened to be right:

* **determined** — matched, and every token was bound from the target;
* **lucky** — matched, but a token had to be copied and happened to be correct;
* **wrong** — did not reproduce the edit, diagnosed as `constant_differs` (a value the demonstration
  had to invent was different), `rebound_wrong` (a token the demonstration did bind was used
  differently), or `mismatch` (not a substitution at all).

## 3. Supply: most real work has no sibling

| rung | commits with a sibling | share of 268 scanned |
|---|---|---|
| same edit shape, no context requirement | 43 | **16.0%** |
| + one shared context line on either side | 42 | 15.7% |
| + one shared context line on both sides | 31 | 11.6% |

**Between 84% and 88% of real commits contain no sibling at all.** For those, "do it once" is exactly
one acquisition per instance: there is nothing for the demonstration to amortise, because the edit
belongs nowhere else in the commit. A perfect one-try mechanism changes nothing for them — this is
the term the claim silently assumes away.

## 4. Determinacy: what the demonstration actually gets

Across 245 sibling pairs (loosest rung):

| outcome | pairs | share |
|---|---|---|
| verbatim repeat — the same edit text belongs there too | 103 | 42.0% |
| induced and **forced** by the demonstration | 31 | 12.7% |
| induced, matched by **luck** | 47 | 19.2% |
| wrong | 64 | 26.1% |

Read the first row carefully, because it is the honest core of "learn once": **42% of what a
demonstration gets right is copy-paste.** The same bytes belong at the sibling too, so memory covers
it and no induction happens. That is real value — it is also not learning, it is retrieval.

On the 142 pairs that genuinely need induction, the demonstration reproduces the developer's edit
**78 times (54.9%)** and is wrong 64 times (45.1%). Against the published ceiling — SyDIT's 70% from
one example with full AST and context machinery — this is the same neighbourhood, and it is nowhere
near permanence.

Determinacy also **falls with size**, in the direction Nguyen et al. measured across 2,841 projects
(70–100% repetitiveness at the smallest sizes, decaying exponentially). The size-3 bucket is small
enough (18 pairs) that no trend should be read into it:

| demonstration size (removed + added lines) | pairs | determined | share |
|---|---|---|---|
| 2 (one changed line) | 197 | 105 | 53% |
| 3 | 18 | 16 | 89% |
| 5 | 14 | 3 | **21%** |

## 5. What is real and what is not

**Real.** A demonstration is a real object with a real domain, and on small systematic edits it
reproduces sibling work about half the time — 55% here, 70% in the best published system. Verbatim
repeats it covers completely. The tree already implements the full pipeline for this
(`causal_trace_to_skill_compiler_v1`: anti-unification plus held-out and sabotage gates), so nothing
here argues for a new mechanism.

**Not real.** That trying once per environment or per action amounts to solving the work. Three
measured reasons, and they compound:

* **supply** — only ~1 in 6 commits has a sibling, so at least 84% of work is untouched by memory;
* **determinacy** — inside that sixth, 45% of the pairs that need induction come out wrong, the
  learner cannot tell a forced prediction from a lucky one without checking, and the part of the
  induction that decides the *value* is right only 21% of the time (§7);
* **permanence** — of what is induced, 53.5% is stale and 31.1% silently corrupt once the file moves.

Multiplying them: a "learn each once" strategy reaches, at best, a minority of the work, errs on
about half of the part that needs induction, and decays on replay. Memory is a **fast path for the
repeated part**, not a solution to the novel part — and advanced engineering is defined by the novel
part, which is why the same edit shows up in a new context rather than the old one.

## 6. The smartest routing this measurement implies

The numbers give a rule that needs no new machinery, only the decision:

1. **Verbatim or substitution sibling present → use memory.** 42% of sibling pairs are verbatim; a
   further slice binds cleanly. Cost: one lookup. Check the postcondition anyway, because §4 cannot
   tell forced from lucky at run time.
2. **Sibling present but the edit introduces values the target does not determine
   (`constant_differs`) → synthesise, don't substitute.** This is the largest wrongness class; the
   demonstration contains the *shape* but not the *value*, and §7 measures the attempt to infer one
   at 21% precision.')
3. **No sibling (84–88% of commits) → there is nothing to learn from, by definition.** The work is
   synthesis plus verification against execution; spending on memory here buys nothing at all.

That is the honest reading of "instant learning as a revolutionary speedup": **it is a speedup on
repetition, and repetition is a measured minority of real engineering.** The revolution is real where
it applies, and the measurement tells you exactly where that is — which is more than the claim
itself does.

## 7. The value layer: one demonstration cannot supply a value; a contrast can test one

The largest single wrongness class was `constant_differs` — 31 of the 64 wrong predictions — where the
demonstration has the edit's *shape* but the target needs a *different* value (`"1.0" -> "1.1"` taught
at `"2.0"` needs `"2.1"`; copying yields `"1.1"`). Two closures were implemented and measured on the
same 245 sibling pairs, same corpus, same rungs.

**Derivation** (`_derive`): carry the demonstration's own arithmetic — the one moved component and its
delta — onto the target's number; or read the value from the same slot of the target's context, which
is SyDIT's constant-replacement move. **Contrast**: accept a derived value only when a second
demonstration's own rule, replayed on the first demonstration's base, reproduces the first
demonstration's value.

| arm (shape_only, 245 pairs) | matched of 142 inductive | wrong | derived-value precision |
|---|---|---|---|
| copy | 78 (54.9%) | 64 | — |
| derive | 84 (59.2%) | 58 | **9/42 = 21.4%** |
| derive + contrast | 82 (57.7%) | 60 | **6/15 = 40.0%** |

Three readings, in order of importance:

1. **Derivation halves the value-class failure and creates new ones.** `constant_differs` falls
   31 -> 12 while `rebound_wrong` rises 20 -> 33: the arithmetic that repairs `"2.1"` also overwrites
   values copying had right. Aggregately it buys about four points — a real effect, not a solution.
2. **When derivation fires it is right one time in five (21.4%); the pairs where it does not fire are
   right 75% (75/100).** The value is not merely noisy, it is the *least* reliable part of the
   induction — and precisely the part a "learn it once" system would store forever.
3. **A second demonstration doubles that precision and makes the system abstain.** Requiring the
   contrast to reproduce the demonstration's value lifts derived-value precision 21.4% -> 40.0% and
   cuts firing from 42 pairs to 15. Agreement between two demonstrations is a usable **veto**, never a
   licence: even two agreeing demonstrations leave the value wrong 60% of the time.

This states the acquisition unit as a measurement. A demonstration identifies a *parameterised
operation*; only a contrast distinguishes which parameter it is tuned by; and even a contrast does not
establish the value. So the value must be closed by execution, and what transfers between environments
is the **policy plus the verifier**, never the stored value. A memory that stores the value stores a
guess — which is exactly the 31.1% silent corruption measured on replay.

## 8. Reproduce

```
python3 canonical/swe_kernel/systematic_edit_supply_v1.py \
  --json canonical/verification/SYSTEMATIC_EDIT_SUPPLY_20261116_V1.json     # ~0.2 s
python3 -m pytest canonical/tests/test_systematic_edit_supply_v1.py -q      # 9 passed, ~0.3 s
```

To rebuild the corpus from history (needs network):

```
python3 canonical/swe_kernel/systematic_edit_supply_v1.py \
  --extract "pypa/packaging=<path>,pallets/click=<path>" --stride 6 --keep 90
```

The value-layer run writes its own receipt and prints all three arms; the copy arm reproduces the
published numbers exactly, which is what makes the derivation delta attributable:

```
python3 canonical/swe_kernel/systematic_edit_supply_v1.py \
  --json canonical/verification/SYSTEMATIC_EDIT_DERIVATION_20261116_V1.json
```

## 9. What this does not claim

No capability credit, no benchmark rank, no terminal credit, no independent verification. The
abstraction is lexical — identifiers, numbers and literals become holes — so "exact" means
"reproduces the bytes", never "means the same thing". The corpus is five Python repositories sampled
every sixth commit; the skip counts for oversized diffs are in the receipt. This measures a
demonstration-determined *substitution* learner; a richer inducer is a different experiment, and the
published ceiling for one with full AST and context machinery is 70%, not 100%.
