# The convention is the missing information

**Date:** 2026-11-21 · **Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls
**Instrument:** `canonical/tools/data_map_convention_v1.py` · **Tests:** `canonical/tests/test_data_map_convention_v1.py`
**Closes:** the open problem in `intake/THE_PREDICATE_IS_THE_BOTTLENECK_20261121_V1.md`

---

## 0. The problem that was left open

The previous receipt proved that for a **data-driven** effect, the goal cannot supply a
discriminating predicate. `unidecode` and a naive ASCII stripper agree on every Latin probe
(`Å→A`, `ö→o`, `ñ→n`) and differ only where the goal is silent (Cyrillic, CJK, punctuation).
A goal-derived predicate therefore either fails on the artifact (exact: 9/13) or accepts the
impostor (loose: 13/13). The stated open problem was:

> Derive a predicate that (a) the artifact satisfies and (b) its cheap lookalikes do not,
> using only the goal, the artifact's surface, and executions the goal chose.

The candidate direction that was listed but untested: *treat the artifact's own data as
inspectable.*

---

## 1. What was found

The artifact's **behaviour** is not in its readable surface, and the **goal** does not
determine it. But the artifact ships its **data** and the **convention** that indexes it, and
both are facts about the artifact that can be read without knowing anything about the world.

Three conventions had to be discovered, and each one is per-artifact:

| convention | question | `unidecode` 1.4.0 | `text-unidecode` 1.3 |
|---|---|---|---|
| **which file** | where is the table? | 190 modules `xNNN.py`, one per 256-codepoint block | one `data.bin`, NUL-joined, 65,535 pieces |
| **which name** | what does an entry index? | `block = int(filename[1:], 16)`, `base = block*256` | `piece[k]` is codepoint `k+1` |
| **which hole** | what does "no entry" mean? | ASCII is an `''` placeholder; `# Code points u+007f and below are equivalent to ASCII` | uncovered codepoints are dropped |

All three were read off the artifacts. The ASCII rule in particular is *stated by the
artifact about itself* (`unidecode/x000.py`), and preferring that statement over the table's
placeholder is the difference between reproducing the effect and deleting every ASCII
character.

## 2. The result

Predict the behaviour from the discovered convention, then **execute** the artifact on
inputs the convention was not fitted to:

| artifact | tables | codepoints mapped | fallback derived | agreement on 15 held-out inputs |
|---|---|---|---|---|
| `unidecode` 1.4.0 | 190 | 43,120 | `identity_below_ascii` | **15/15** |
| `text-unidecode` 1.3 | 1 | 65,535 | `keep` | **15/15** |

Two entirely different layouts, two different fallback policies, both discovered, both
exactly right on held-out inputs including `Ελλάδα→Ellada`, `Ж→Zh`, `日本語→Ri Ben Yu`,
`Æsir→AEsir`, `—→--`, `İstanbul→Istanbul`, `þorn→thorn`.

### The comparison that matters

| method | artifact satisfied | impostor rejected |
|---|---|---|
| goal-derived predicate, exact (P1) | **no** (9/13) | — |
| goal-derived predicate, loose (P2) | yes (13/13) | **no** (impostor 13/13) |
| **artifact-convention predictor** | **yes** (15/15) | **yes** — separates the artifact from a naive stripper on **8 of 15** held-out inputs |

The open problem is closed for these two artifacts: the missing information was never in the
goal, and never in the artifact's prose. It was in the artifact's **data** and the
**convention** that indexes it, and both are discoverable without world knowledge.

---

## 3. Four measurement bugs, and why they are recorded

The first attempt at this scored 4/10 and 0/10. Every one of those numbers was the
instrument's fault, and each produced a failure that looked exactly like an artifact
limitation. They are pinned by tests because the same four mistakes will be made again:

1. **requiring a `.py` filename** made the binary payload invisible → `blob_tables`
2. **requiring exactly 256 entries** dropped a 255-entry block, which was the entire
   Cyrillic block → width tolerance `(256, 255)`
3. **treating an empty-string placeholder as a mapping** deleted every ASCII character →
   the artifact's stated boundary outranks the table
4. **assuming a fallback** instead of reading the one the artifact states →
   `discover_fallback`, with the cited signal recorded

Two further bugs were in the *test fixtures*, not the instrument: a fixture that wrote the
two-character string `''` instead of an empty string, and one that placed `Ж` at `0x15`
instead of `0x16`. Both are noted because a fixture that silently cannot express the case it
tests is worse than no fixture.

---

## 4. What this does not prove

- **Two artifacts, one effect family.** Transliteration. Nothing here shows transfer to file
  formats, protocols, processes, or GUIs.
- **The convention search is not general.** It recognises blob-with-BMP-width and
  block-indexed-literals. A third layout would need a third recogniser; when none matches,
  the instrument refuses (`NO_CONVENTION`) rather than guessing.
- **Discovery was guided by having seen these two layouts.** The recognisers were written
  after inspecting them. What is shown is that the *conventions* are discoverable and that
  the resulting predictor is verified by execution — not that a blind search would find them.
- **The goal still does not choose.** In this family the goal ("plain ASCII") is unchanged
  across both artifacts; what the convention supplies is the *mapping*, not the preference.
- **`truth.achieved` remains `false`.** §6 is not met.

---

## 5. Where the bottleneck now sits

Not acquisition (0.709 s, digest-verified, no pip), not execution, not storage, not replay,
not the predicate for structural effects, and — on these two artifacts — not the predicate
for data-driven effects either.

It is now: **recognising which convention an unseen artifact uses**, from its bytes and
source, without a recogniser having been written for that layout. That is a search problem
over conventions, and it is the next thing to attack.
