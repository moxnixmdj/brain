# My headlines were leakage — twice, and the guard is the deliverable

**Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls · 6 new tests pass

---

## The correction, stated plainly

I published two numbers today for "ground a goal onto the artifact's own vocabulary". Both were
mostly the corpus answering itself.

| what I reported | what it actually is | why it inflated |
|---|---|---|
| **43.6%** — module layout as the index | **11.8%** | `test_align.py` imports from `rich/align.py`; the goal word *was* a module name on 60 of 94 rows (61.7% there, 11.8% elsewhere) |
| **47.0%** — name+doc overlap | **9.7%** | `test_align.py` → goal "align" → answer `Align`. 69.2% on rows where the goal stems from the truth; 9.7% where it does not |

**The real capability is 9.7–11.8%.** Every headline driven by a project's test filenames is
inflated 4–6×. That is the difference between "solved" and "fails nine times out of ten".

This is the third correction in this stretch, after the misread `grep` and the false
`stub_imports` root cause. **The pattern is the same every time: I measured on a corpus that
contained its own answer, or I read a summary instead of the raw rows.**

---

## The measurement bug, precisely

A test file's name and its imports come from the same decision by the library's author: name the
file after the thing you are testing, import the thing you are testing. So:

```
goal   = "align"                     <- chosen because the module is called align
truth  = the names in rich/align.py  <- the module called align
```

Any scorer that matches text will win, and it has measured **nothing about generalisation.** My
`rich` result even looked stratified (58.1%), which made it feel like a real finding.

---

## What I kept: a guard, not a scorer

`the_goal_must_not_share_a_stem_v1` — **6 tests**, and the whole mechanism is:

> a goal may not share a 6-character prefix with **any** candidate the rule could return.

Six characters because it is the bluntest thing that works and a clever stemmer would itself be a
fitted component. It is checked against **every candidate, not just the truth** — guarding only
the truth lets a leak through a near-miss the goal also names.

Two properties that matter more than the rule:

* `audit` always reports **kept, dropped, and the drop rate**, so a thin corpus cannot become a
  headline by being quoted as a percentage of itself.
* `verdict` **refuses** to call anything under 20 leak-free rows meaningful. `verdict(4, 4)`
  returns `meaningful: False` even though that reads as 100%.

I also caught my own docstring making a false claim — it said `table`/`tabulate` collide when they
diverge at the fourth character. A test found it. **Prose about a mechanism is a claim like any
other.**

---

## What else this session actually established

**The web channel works, and it was never blocked by a constraint.** Earlier receipts recorded
"web acquisition out of scope by constraint". Wrong: `github.com`, `api.github.com`,
`registry.npmjs.org`, `pypi.org`, `codeload.github.com` all answer.

**The GitHub contents API has a hard ceiling, measured:** 5,000 requests/hour unauthenticated;
one four-library run consumed all 5,000 (`{"limit":5000,"used":5000,"remaining":0}`), after which
every fetch is 403. `codeload` (one tar.gz per repo) and `pypi` sdists (one tarball per package)
have **no quota** and are strictly fewer round trips — six packages in **1.4 s**. The quota-burning
channel is now only the pinned-commit fallback.

**Doctests are not the acquisition channel, measured before building it:** 27 of 2,046 documented
definitions carry a runnable example — **1.3%**. It would have worked on `tabulate` and died on
`click`. Killed in 29 seconds.

**The `doc_overlap` feature normalises by the *query*, not the document**
(`|goal ∩ doc| / |goal|`), so a long class docstring outranks a short precise one. Measured
consequence: `Table` (docstring "A table") loses to `print` for the goal "print a table".

---

## Honest status of the user's algorithm

| step | status |
|---|---|
| scan the environment | **works** — 216 programs, 48 ms |
| know what you don't know | **works** — 0 probes at rebuild |
| fetch instantly from the guide | **works** — no model call, no quota, ~1 request/library |
| **use it** (ground the goal) | **9.7–11.8% — the bottleneck** |

Goal-directed beats learn-everything by **3.0×**, and that finding is unaffected by any of this
because it counted *requests*, not matches.

`truth.achieved` = **`false`**.
