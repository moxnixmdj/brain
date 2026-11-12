# The capability was there. The substrate wasn't.

**2026-11-12.** Authority **NONE**. `truth.achieved` = `false`.

Last pass I ranked the next move as *"take one failing cross-language transfer test, find the
smallest reason it fails, and fix the mechanism until it goes green."* I did that. The
mechanism needed no fixing. It was never running.

---

## 1. The claim under test

One lesson taught once, in Python:

```python
before: def under_cap(xs, cap): return len(xs) <= cap
after:  def under_cap(xs, cap): return len(xs) <  cap
```

then offered to six other languages. Before:

```
rust hit: None
```

`test_phase3_one_python_lesson_transfers_across_all_six_other_languages` — the test that *is*
your claim — was failing, and had been failing across the last three passes.

## 2. The reason, found by following it down

Not the learner. `tree_sitter` was not installed.

```
python3 -c "import tree_sitter"  ->  ModuleNotFoundError
```

and the tree **already knows this exact incident**:

> `scripts/restore_substrate_v1.py`: *"pip installs outside /home/user evaporate between turns.
> The repository recorded that twice ('tree_sitter generation mismatch broke 3 tree-sitter
> capabilities') and then left the restore step as a comment. A comment cannot run, so the
> matrix silently measured a smaller machine than the one the registry describes."*

The restore script exists. The pinned manifest exists
(`requirements/software_engineering_kernel_v1.txt`: `tree_sitter==0.20.4`,
`tree_sitter_languages==1.10.2`). The census workflow restores it. **The unit-test lane does
not**, and the mastery test runs in no workflow at all.

## 3. Same lesson, substrate restored

```
  rust        HIT CROSS_LANGUAGE_CST_SKELETON
  go          HIT CROSS_LANGUAGE_CST_SKELETON
  typescript  HIT CROSS_LANGUAGE_CST_SKELETON
  javascript  HIT CROSS_LANGUAGE_CST_SKELETON
  java        HIT CROSS_LANGUAGE_CST_SKELETON
  cpp         HIT CROSS_LANGUAGE_CST_SKELETON
```

**6 of 6, from one Python demonstration.** `test_phase3_one_python_lesson_transfers_across_all_six_other_languages`
now passes. Two other failures in that file remain and are a different mechanism
(`FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT` — a fail-closed confinement
gate, unrelated to language transfer and untouched here).

So the honest headline is: **the one-shot → new-language link was never broken. It was
unmeasured, and reported as broken.** That is worse than either, because a false negative about
a capability you have is indistinguishable from a true negative about one you don't.

## 4. The second defect this exposed: silence

The transfer path could not distinguish "no rule applied" from "no parser exists":

```python
try:
    tree = tsk.parse_bytes(lang, raw)
except Exception:
    return            # <-- yields zero candidates: identical to "the rule does not fit"
```

and, one layer up, a Python-shaped skeleton was produced by the **stdlib AST fallback** when the
Tree-Sitter parse failed, then unified against a Rust target it could never match. Two silent
degradations, both presenting as a capability failure.

Fixed:

| situation | before | after |
|---|---|---|
| substrate present, rule applies | candidate | candidate |
| substrate present, rule doesn't fit | no candidates | no candidates |
| **substrate absent** | **no candidates** | **`CstSubstrateUnavailable`** |
| recall with substrate absent | `None` | `{"measured": False, "substrate_unavailable": True, "remedy": "python3 scripts/restore_substrate_v1.py"}` |

The refusal is shaped so a caller doing `if hit:` cannot mistake it for an application — there is
no `patched_source` and no `scope_tier` in it.

## 5. The tests are honest in both worlds

```
with substrate     : 11 passed
simulated bare image: 7 skipped, 4 passed
```

The four that still run on a bare image are the ones that check the *refusal* and the
*declaration*. Nothing fails for an uninstalled dependency; nothing silently passes either.

---

## What this changes about the answer

The link table from last pass one line amended:

| link | before | now |
|---|---|---|
| transfer one lesson across six languages | *FALSE* | **TRUE when the substrate is present — 6/6 measured** |
| substrate declared and restorable | true | true, and the capability now names it when absent |

**You are right about this specific thing, more than I gave you last pass:** a single
demonstration in Python did carry enough structure to be re-expressed in six other languages,
and that is a real, re-runnable, non-hand-wavy result. It was already built here.

**The limit that survives is the one I have been pointing at, and this pass sharpens it:** the
*mechanism* was right and the *measurement* was wrong, for three passes, in a repository whose
own docstring predicted it. A system that reports a capability as absent when its dependency is
missing cannot tell you what it can do — and "what it can do" is the entire question. The
interesting failure is never a wrong answer; it is a confident answer about something that was
never measured.

## What is genuinely load-bearing from here

1. **The measurement substrate is part of the claim.** A capability number printed from an image
   without its declared dependencies is not a smaller number, it is a wrong one. Route the unit
   lane through `restore_substrate_v1.py --check`.
2. **Run the capability tests in CI.** The mastery file — the most capability-dense file in the
   tree — is executed by no workflow, which is why a three-pass-old regression was invisible.
3. **Cross-language transfer is real and narrow.** 6/6 on a structural idiom (`len(x)` ↔
   `x.len()`). It is not "any environment": the literature still measures <9% / <3% unseen-site
   reuse for UI agents. The transfer here is over *syntax*, and syntax is the easy axis.
