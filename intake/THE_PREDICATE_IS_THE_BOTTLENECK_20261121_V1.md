# The predicate is the bottleneck, and it is not language-shaped

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls
**Companion to:** `intake/EFFECT_PREDICATE_BINDER_20261121_V1.md` (13 tests, committed `82167e75`)

---

## 0. What was already proven, and what was not

`effect_predicate_binder_v1` binds an unseen artifact's callable to a goal *when the goal is
already a predicate on observables*. On sorted containers that works, and it resists its
lookalikes by executing a battery that separates them:

```
sorted and unique        -> SortedSet.add   (SortedList.add rejected: keeps the duplicate)
sorted keeping duplicates -> SortedKeyList.add (SortedSet.add rejected: drops it)
PSet  refused: passes [3,1,2], fails [8,3,100] and ['b','a','c']  (hash-ordered, not sorted)
```

But in that family the predicate was **hand-written** (`GOALS` in the instrument). The
honest question was whether the same idea survives a second effect family whose observable
is not a collection. It was tested on **text transliteration**, and the answer is *no, not
as constructed* — for a reason that has nothing to do with the battery.

---

## 1. The test that killed it

Artifact: `text-unidecode` 1.3, digest-verified, never seen by this repo. Its entire
implementation is **21 lines** that index an opaque `data.bin`:

```python
_replaces = pkgutil.get_data(__name__, 'data.bin').decode('utf8').split('\x00')
def unidecode(txt):
    for ch in txt:
        chars.append(_replaces[ord(ch)-1])
```

The behaviour is **not in the readable surface**. `Æsir→AEsir`, `Ж→Zh`, `日本語→Ri Ben Yu`
exist only inside the binary table and in prose documentation. So no amount of AST reading,
signature probing, or docstring parsing yields the effect. This is the good case for
"execute, don't read" — and also the case that exposes the flaw.

A goal-derived predicate was written from the goal alone, using only the standard library:

| predicate | statement | holds on 13 probes? | discriminates the artifact from a naive ASCII stripper? |
|---|---|---|---|
| **P1 exact** | output is ASCII **and** equals the base letter of the input | **no** (9/13) | — |
| **P2 loose** | output is ASCII and alphanumerically equals the base, ignoring case and spacers | yes (13/13) | **no** — the impostor also scores 13/13 |

P1 is falsified by the artifact itself: `Ж→Zh` is not the base letter, so exactness fails.
Loosening it to P2 to admit `Zh` and `Ri Ben Yu` makes P2 **satisfied by the naive stripper on
every probe**. The loosening that was required to fit reality is exactly the loosening that
destroys discriminating power. There is no setting of that dial that both fits and separates.

### The precise reason

| char | artifact | naive stripper | differ? |
|---|---|---|---|
| `Å` | `A` | `A` | no |
| `ö` | `o` | `o` | no |
| `ñ` | `n` | `n` | no |
| `Ж` | `Zh` | `` | **yes** |
| `日本語` | `Ri Ben Yu ` | `` | **yes** |
| `—` | `--` | `` | **yes** |

The artifact and the impostor are **identical on every Latin probe**, and differ only on
Cyrillic, CJK, and punctuation — exactly the inputs where the goal language ("give me plain
ASCII") **cannot say which output is correct**, because both are ASCII and neither is
implied by the goal.

> **The information needed to discriminate the effect does not exist in the goal, and does
> not exist in the readable surface. It exists only in the artifact's data.**

---

## 2. Why "learn the table from probes" also fails here

A partial transcription table was learned from single-character probes and applied to
held-out inputs. It is *sound* (it abstains instead of guessing) but it is **not
discriminating**: on every held-out Latin word the artifact and the naive stripper both
satisfy it, so it cannot tell them apart. Accuracy on decidable inputs was 3/4, and the
discrimination column is `False` on all four.

The table approach is not wrong — it is simply unable to separate two effects that agree on
the entire region of input space the goal can describe.

---

## 3. What this establishes

1. **The binder is real but narrow.** Effect-as-predicate binding is verified to work where
   the observable domain is structured and a separating input exists (`sorted_unique` and
   its inverse). It is **not** yet a general mechanism.
2. **The bottleneck has moved, and it moved to the predicate.** It is no longer acquisition
   (0.709 s, digest-verified, no pip), nor execution, nor storage, nor replay — all four are
   measured and working. It is: *given a goal and an artifact, produce a predicate that the
   artifact satisfies and its lookalikes do not.*
3. **That is not a language-understanding problem.** More text would not have helped here;
   the artifact's own docs describe `unidecode` as "ASCII transliteration", which both the
   artifact and the impostor satisfy. The missing information is the artifact's **data**, and
   the only way to obtain it is execution on inputs chosen to separate — which requires
   knowing *which* inputs separate, which is what the goal failed to supply.
4. **The failure is honest and it is falsifiable.** Every number above is a subprocess
   result, reproducible from the committed instrument. Nothing was inferred from prose.

---

## 4. The open problem, stated so it can be attacked

> For an artifact whose effect is a **data-driven map** rather than a structural invariant,
> derive a predicate that (a) the artifact satisfies and (b) its cheap lookalikes do not,
> using only the goal, the artifact's surface, and executions the goal chose.

Candidate directions, none yet tested, listed as problem statements rather than claims:

- **Separate by disagreement, not by description.** Use the goal to name *the class of
  inputs the goal is silent about* (here: non-Latin script) and require the predicate only
  on that region, admitting that the goal does not determine it. The effect then becomes
  "preserves meaning where the goal speaks, and is *stable and total* where it does not" —
  testable, but it admits any total map.
- **Treat the artifact's own data as inspectable.** `data.bin` is part of the artifact. A
  method that indexes it and then *verifies by execution on held-out characters* would
  separate artifact from impostor without a natural-language predicate. This is a promise,
  not a result.
- **Accept refusal as the correct outcome** when the goal does not determine the effect.
  The binder already refuses 9 of 11 packages; refusal here is principled, not a failure —
  but it means such artifacts cannot be learned by this mechanism at all.

---

## 5. Status

`truth.achieved` remains `false`. Two verified records, one effect family that passes and one
that decisively fails. The instrument is committed and its limits are measured rather than
described. The next unit of work is §4's open problem, not more features on the binder.
