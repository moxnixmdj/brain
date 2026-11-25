# WALL TWO IS GENERATION, NOT LOCALISATION

**Round V35 · 2026-11-24 · branch `arena/50c05c04-brain`**

---

## 1. What I set out to fix, and why

V34 solved **1 of 10** and its receipt said seven of the ten refusals produced no usable failure signal at
all. That looked like a localisation defect, so I treated it as one: *if the system cannot find the place, no
operator can help it.* The prediction was that better localisation would unlock generation.

**The prediction was wrong, and the measurement is the point of this round.**

## 2. Part one — localisation, fixed

V34's localiser read traceback frames. On **10 of 10** tasks it found no source file at all. Not because it
failed to find the fix, but because on seven of them there is no frame inside the source tree — only a bare
`assert` inside a test:

```python
assert Infinity <= Infinity
assert tomli.TOMLDecodeError().__module__ == "tomli"
```

Four deterministic resolvers were added, each judged against **the files the real commit changed** (tests,
docs and changelogs removed):

| localiser | top-1 | found any (≤5) | blind |
|---|---|---|---|
| traceback frames (V34) | 0/10 | 0/10 | 10 |
| assertion symbols only | 3/10 | 3/10 | 6 |
| + module-name literal + literal-content | 3/10 | 4/10 | 6 |
| + **reachability from what the test calls** | **8/10** | **10/10** | 0 |

Reachability is the resolver that did the work: a value assertion names no location, but the test must still
*call* something to obtain the value, and the file defining that symbol and whatever it imports is where the
code lives. Only **1 of 8** correct answers still leans on the labelled fallback (largest module), and that
relies on the prior being configured per repository rather than derived — it is a weak component and is
recorded as such.

## 3. Part two — and generation did not move

Feeding those localisations into the generator:

```
                        v34          v35
tasks examined          12           12
not a test failure      2            2
excluded, integrity     0            2
genuine denominator     10           8
solved                  1            3
  of which change behaviour   1      2
  of which only change text   0      1
resolve rate            0.10         0.375
```

Localisation went **0 → 8/10 top-1** and bought **zero** additional solves. The ablation says it plainly:

| condition | solved |
|---|---|
| localisation seed, i.e. the store | 3/8 |
| empty store | 3/8 |

Identical. Both repositories are small enough that the block scan already reaches every source file, so a
seed cannot add what is already there. **Localisation was never the binding constraint. Generation is.**

## 4. The three solves, separated honestly

**`5ab9ec92` — `KEYWORD_APPLY_ALL`, changes behaviour.** Accept `parse_float`, thread it through
`ParseState.__init__`, apply it at all three `float()` sites. Structurally identical to the upstream commit:
same function, same constructor, same call site, same three sites.

**`96dfe2ce` — `ATTRIBUTE_SET`, changes behaviour.** Bind `TOMLDecodeError.__module__ = 'tomli'`. Upstream
writes the same assignment, but in `tomli/__init__.py`; mine lands in `_parser.py`. Same semantic effect,
wrong home. A reviewer would ask for the move.

**`31c85a18` — `MESSAGE_DEQUOTE`, changes only text.** The message becomes
`Found invalid character  'X' ` — with a double space. Its assertion is a containment check, so whitespace
satisfies it. **Nothing the parser computes changed.** This is pattern-matching in disguise, it is counted as
solved because the test genuinely passes, and it is labelled cosmetic because a measure now exists to say so.

## 5. Two tasks are unwinnable under the integrity rule

`9f5249fb` and `e83801f4` both assert `raw["metadata_version"] == "2.6"`, and both real commits reach 2.6 by
editing **`tests/metadata/everything.metadata`** — a test fixture. No source-only edit can make a fixture
declare a different metadata version. They are **excluded by name, with the reason**, rather than counted as
refusals, because honesty about why a task is out of scope is worth more than a bigger denominator.

## 6. Why the remaining five still fail — read from their real diffs

These are not mysteries. Each needs something the current operator set cannot express:

- `959bb79c` — the assertion is about *how many times* a method is called (a `unittest.mock` spy). No value is
  named anywhere.
- `d2fa9238` — control-flow restructuring of `union()` so a pre-release policy propagates through `_build`.
- `f8f16338` — `__le__`/`__ge__` must return identity comparisons where every method currently returns a
  constant. Tried; no single-line form was found that satisfies the test.
- `9af551b5` — add a module docstring *and* an attribute read through `tomli.__doc__`.
- `67ec7d10` — every `raise` must be wrapped in a `suffix_location()` helper **that does not exist yet**.

That last one names the next wall precisely: a fix that requires **inventing a helper**. It is the same shape
as `FOREIGN_IDENT_UNBOUND` recorded in earlier rounds, and it is the honest ceiling of substitution-based
generation.

## 7. Ten defects found by executing, not by reading

1. Frame-only localisation was blind on 7/10 and reported it as "refused" rather than "could not see".
2. A silent line fallback to `1` turned a missed regex into assert-less analysis with no warning.
3. `'tomli' in text` matched `'tomli._parser'` and suppressed the only candidate that worked — the **same
   substring family** as V33's `WRONG_STRING`.
4. A name chain was resolved by picking one end (`tomli.TOMLDecodeError` → took `tomli`) instead of trying
   every name and letting the files decide.
5. An **inverted guard** skipped exactly the files that needed editing, because they already contained the
   expected value.
6. pytest **truncates** expected strings (`'Invalid valu... 1, column 5)'`), so the expected value was being
   read from destroyed text; it survives only in the test source.
7. One-site edits cannot fix a value that must appear in two lists. **Second time this has happened** (V34 was
   the first) — the unit is the shape, not the site.
8. A directory-wide test run returned rc=2 from a **missing optional dependency** (`dateutil`) and was
   counted as a regression, silently turning 3 solves into 0.
9. An f-string containing a `!r` conversion was matched by plain text, so the wrong message was edited.
10. A whitespace-only patch was accepted as a solve **until a measure for cosmetic changes existed**.

## 8. What this establishes, and what it does not

**Established, with execution:** localisation from an assertion is a solved-enough problem on this corpus —
8/10 top-1, 10/10 within five, zero model calls, ~7 s. And, decisively, that it is *not* what limits the
system.

**Not established:** any generalisation. Three of eight single-node bugs in two small pure-Python repositories,
one of the three cosmetic. The ablation shows the store contributes nothing here. **No benchmark row exists or
is claimed. No SWE-bench, Terminal-Bench or OSWorld task has been attempted by this system.**

**Next bottleneck, named by the data:** a fix that must **invent a helper that does not exist yet**
(`67ec7d10`: wrap every `raise` in a `suffix_location()` that has to be written). Every operator built so far
recombines what is already in the file. That is the wall to attack next.
