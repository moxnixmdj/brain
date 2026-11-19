# The demand is a relation: 2 verified repairs in 75, both on the one row per corpus where the relation is one site wide

*2026-11-25. The question, asked again without the abbreviation: if a demonstration can be transferred
into a system in one exposure, why can we not hand our system the most advanced coding actions, let it
experience each one once, and thereby own the best coding agent there is? Which parts of that are real,
which parts are wrong, and what is the smartest thing to do next?*

## What the previous round left standing

The round before this one changed the site and nothing else: it took the demand implied by a failing
assertion and asked the identical demand at 37 other statement-level productions in the same function.
Zero of the 37 verified. It then read the seven human fixes it could reach and found that the smallest
of them — `attrs 13105a64f2`, one line — was

```python
-        if a.converter and not isinstance(a.converter, Converter):
+        if a.converter is not None and not isinstance(a.converter, Converter):
```

That is not a value moved from one place to another. It is the same name, at the same site, in the same
statement, with the *question it is asked* changed. The code asked `a.converter` for a truth value; the
object it received was a converter whose `__bool__` is `False`. The demand was never "produce this value
elsewhere". It was "this guard is asking the wrong question about the value it already holds".

So this round built the instrument for that sentence and measured it.

## The mechanism, in the order it earned its parts

1. **Ask the running code, not the text.** Parse the file, find every `If` test, and take the maximal
   `Name`/`Attribute` spans *the test asks a yes/no question of* — the test itself, `and`/`or` operands,
   the operand of `not`. Wrap each in `__brain_probe__(line, col, value)` and run *one* failing test
   file. Behaviour is unchanged: the probe returns its argument.
2. **Keep the sites where the value and the question disagree.** A site is a candidate only if the value
   that arrived was **falsey**, was **not `None`**, and was **not a `bool`**. That is the exact shape of
   the attrs defect: a real object that answers "no" to a question about existence or content. A `bool`
   is excluded because a `bool` answering a truth question is not a disagreement; it is the answer.
3. **Project at the site.** `(a.converter) is not None` — the two-option closed set for this defect.
4. **Judge by the project's own suite, against the human edit's footprint.** A candidate must (a) flip
   at least one test that failed on the parent, (b) break nothing that passed, and (c) flip *all* of the
   tests that the human's own edit flips. The human's edit is run on every row as a **control**; if the
   control does not verify under the same judge, the row is refused as `CONTROL_BROKEN` and is not
   counted either way.

## The measurement

Both corpora, judged by the project's own test file, zero parameters stored, zero model calls.

| corpus | rows | wall | falsey guard sites | projections judged | control accepted | verified |
|---|---|---|---|---|---|---|
| 30 commits from the previous receipt (click, jinja, attrs) | 30 | 499 s | 165 | 164 | 28/30 | **1** |
| the 45 one-line-fix commits this engine had never run | 45 | 1649 s | 201 | 200 | 42/45 | **1** |

Stages across the 75: `NO_PROJECTION_REPAIRS` 51, `NO_FALSEY_GUARD` 17, `REFUSED__CONTROL_BROKEN` 3,
`NO_FAILING_TEST` 2, `VERIFIED` 2.

The two verified repairs are, in full:

| repo | commit | the human's line | the engine's edit | value seen | attempt (of candidate sites in that file) | tests flipped |
|---|---|---|---|---|---|---|
| attrs | `13105a64f2` | `if a.converter and not isinstance(...)` | `if ((a.converter) is not None) and not ...` | `MyConv` | 7th of 8 | `test_falsey_converter` |
| packaging | `b80e6eb0a6` | `if self.environments:` | `if (self.environments) is not None:` | `list` | 1st of 2 | `test_lock_no_matching_env[environments0]` |

Both are the human's own line. Both are the *same relation*: a guard asking a container or an object for
a truth value when the question it means is existence. Neither was derived from a failure message — the
site was *selected by the run*: the probe saw the value, and the value did not match the question.

## Three times the instrument was wrong and the world was blamed

Each of these produced a number that read like a fact, and each was a defect:

- **The criterion rejected the answer key.** Demanding that *every* test failing on the parent pass
  reports "not repaired" for the human's own fix wherever the parent carries an unrelated red. On the
  first row it did exactly that. Hence the control, and hence the footprint rule.
- **"At least one test flips" accepted a nonsense edit.** At `click 4fd2fea0db` a projection in a
  different class flipped 2 of the 5 tests the human's edit flips; the footprint rule refuses it.
- **A call argument was treated as a question.** At `more-itertools cca32949f1` the test is
  `hasattr(iterable, '__reversed__')`. Projecting the *argument* gives `hasattr(True, '__reversed__')`,
  which is `False`, which skips the branch exactly as the human's `getattr(..., None)` does — so it
  flipped the human's own fail-to-pass test and "verified". **The judge accepted it because the nonsense
  coincided with the fix.** The first run of the 45 reported 2 verified; one of them was this. Restricting
  candidate sites to boolean positions removed it, and the sweep was re-run in full: 45 rows, 1 verified.

The last one is the most important line in this document, because it is the failure mode that a
demonstration-based system has and a verifier-based system does not: an edit that is *wrong* can pass a
test that is *right*. Only reading the site's position in the AST — "is this expression the value the
test asks about, or an argument to something else?" — distinguished them.

## What the numbers mean together

The mechanism recovers **2 of 75**, and both are the same form: `if x:` → `if x is not None:` at a guard
that already holds the right object. It recovers them at the human's line, on the 7th and 1st attempt
out of the 8 and 2 candidate sites those two files contained, with the control accepted on 70 of 75 rows. 366 falsey guard sites produce 2
correct repairs: a precision of 0.55%.

That is the boundary, and the corpus states it in the rows the mechanism cannot reach. `click
4fd2fea0db`'s human edit is:

```python
+        if is_flag and flag_value is None:
+            flag_value = not self.default
+
         self.type: types.ParamType
         if is_flag and type is None:
-            if flag_value is None:
-                flag_value = not self.default
             self.type = types.convert_type(None, flag_value)
```

The demand there is not a different question at a site. It is: **the same question must be asked
regardless of the enclosing condition** — the relation spans two frames, the inner branch and its
parent. A projection that rewrites one guard cannot express it, and the engine's nearest attempt is
refused as a partial flip, which is the correct verdict.

That is the round's answer in one line: **the difference between 0 and 1 is the arity of the relation.**
The instrument can express "this value at this site is asked the wrong question" — one frame, one value,
one relation. The corpus's remaining demands are relations over frames: a call must return bytes, a
branch must be taken because the object is not `None` though falsey, two sites must agree, a condition
must be lifted out of its enclosing branch. Each form buys roughly one row in thirty-five when it is
built by hand.

## Falsified this round, with the cost written down

- **Enumerating the projection at every guard.** 308 guard sites, 616 candidates, 111 s for the first
  row, correct site past attempt 80. The site must be *selected by the run*, not searched. This also
  puts the tree's "enumerate more edits" instinct in its place: a targeted sweep of all single-edit
  mutations is a published 2026 baseline (arXiv 2609.01775, 14/23 with an 18× speedup), so matching it
  would not be progress even if it worked.
- **Counting a `bool` as a falsey disagreement.** 84 "candidate sites" collapsed to 15 once `bool` was
  excluded — the filter is the difference between a signal and a census.
- **Counting every name inside an `If` test as a question.** 498 candidate sites on the 30 corpus
  collapsed to 165 once only boolean positions counted — and the difference contained a false
  verification.
- **Two silent instrumentation failures** (an import above `from __future__`, a probe module written
  without `.py`) that both produced *zero verdicts*, which is indistinguishable from "the guard was never
  reached". Both are now pinned as tests.

## The answer to the question

**Real.** A demonstration transfers something in one exposure. That part is not in doubt, and this tree
has measured its shape three rounds running: what transfers is what the demonstration *separates*
(r19), and a demonstration given without a world to try it in brings no measurable benefit at all
(arXiv 2611.12885: 69.0% → 78.5% with rehearsal, p=0.003). Instant learning is real in the same sense
that a key is real: it opens the lock it was cut for.

**Not real.** The step from "the model saw the action" to "the model can take the action" — because an
action is two things, and a demonstration only ever shows one of them. It shows the **form**: the edit's
text, where it goes, what syntax carries it. It never shows the **demand**: which relation the failing
run violated, and therefore which of the exponentially many edits with that form is the one. This round
is the smallest possible demonstration of the gap: the human fix is 19 characters, the form is
`<expr> is not None`, and the engine can generate that form at 366 sites. It is right at 2.

**The single bottleneck, unchanged in name and sharpened in content: the demand language.** Not the
store (zero parameters). Not the search cost (~50 µs per candidate). Not the oracle (fixed and audited
last round). Not the site finder (it found the right line, by running). The instrument can only say
*"this value at this site"*, and the demands the corpus contains are relations over frames. Every round
of this program has now priced one form of that language: a value demand, a site shift, a truthiness
relation, a caller's variable, a statement, a verb, a new production. Each costs a round and buys one or
two rows in seventy-five.

**The ultimate move, therefore, is not the eighth form.** Hand-building forms is the incremental path,
and this round is the arithmetic that says so: at ~1 row per form per 35, the corpus needs ~35 forms to
be covered, and the 36th real fix will need a form nobody wrote. The only move that is not incremental
is to make the demand language a **function learned from the run**, with the witness judge as its
signal. The raw material is already being produced by the probe: for every guard the run reports a pair —
*the question the code asked* and *the value that arrived* — and the disagreement between them is the
demand's seed. A space of relations over (question, value, frame) pairs, scored by whether an edit that
satisfies it turns the witness's tests green, is a thing that can be learned from our own arithmetic:
no stored knowledge, no borrowed weights, and the same verifier that just refused a partial flip and a
coincidence.

The law this round establishes is the sentence the previous one could only suspect, now with a number
on both sides of it:

> A demand is a relation, not a value. Its producer may be in another frame. An instrument that can
> only name a value at one site will find the site — and still miss the demand. 2 of 75 real fixes are
> of that form; the other 73 are not, and no amount of repeating the demonstration changes which is which.

## Cost

75 real commits across 12 repositories, 2148 s of test execution, 366 guard sites instrumented across
two full sweeps, 364 projections judged against the projects' own suites, 70 controls accepted, 0
parameters stored, 0 model calls, 0 borrowed weights. Three instrument defects were found and fixed
mid-round (control criterion, footprint criterion, boolean-position criterion) and both corpora were
re-run in full after each — the numbers above are from the final run, not the run that agreed with the
hypothesis.
