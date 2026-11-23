# The web is the source; word overlap fails; and my 44% was mostly leakage

**Authority:** NONE · `truth.achieved` stays `false` · **$0**, 0 model calls · zero model calls at runtime

---

## 1. The verdict on §3, in one table

| claim | verdict | evidence |
|---|---|---|
| Web acquisition was blocked by a constraint | **FALSE — it was never a constraint, just unbuilt** | `github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org` all return 200 from the sandbox |
| The artifact's docs are the supervision | **TRUE** | 1,064 of 2,046 definitions documented across 4 unseen libraries |
| Runnable doc examples are the acquisition channel | **FALSE** | 27 of 2,046 documented defs carry a doctest — **1.3%**. Killed in 29 s, before building it |
| Word overlap is enough to find the right name | **FALSE** | **8/94 = 8.5%**. `inspect` was the top hit for *every* rich goal |
| The artifact's layout is a better index | **TRUE but small** | **4/34 = 11.8%** genuinely — see §3 |
| Instant learning is solved for unseen libraries | **UNPROVEN, and weaker than I first reported** | see §3 |

---

## 2. The one component that was new

Everything else existed. `scan_retrieve_fetch_v1` already did scan → retrieve → fetch, but its
"fetch" was a local `--help` page. The web half had been recorded as "out of scope by
constraint" in earlier receipts. **It was not a constraint.** `documentation_is_the_source_v1`
adds a source channel — GitHub contents API (JSON + base64) and a pypi sdist tarball — and
reuses the existing ranker with its weights untouched.

---

## 3. I reported 43.6% and had to walk it back

The organic corpus (`which_rule_on_a_real_corpus_v1`) is **94 rows** where the truth is set by
the projects' own test imports — no answer key written by me.

Five word-overlap rules: **all 8/94 (8.5%)**. Five rules landing on one number is the signature
of a pinned answer, not of a good rule.

The structural rule — *match the goal word to a module name, then take that module's units* —
scored **41/94 = 43.6%**, a 5.12× ratio. I nearly wrote that down.

**The leakage check cut it by 3.7×:**

```
goal word IS  a module name    37/60 = 61.7%   <- near-tautology
goal word is NOT a module name  4/34 = 11.8%   <- the genuine number
```

`test_align.py` importing from `rich/align.py` makes "match the goal to the module" almost
vacuous. **The honest capability is 11.8%, not 43.6%.** It beats the 8.5% baseline on the same
rows and it is nowhere near solved.

Per library, unchanged: `rich` 58.1%, `attrs` 33.3%, `click` 0%, `tabulate` 0% **FLAT**.
A one-module library has no layout to read — the rule degrades to nothing exactly where the
artifact is flat. That is a boundary of the mechanism, not noise.

---

## 4. Why word overlap fails — the first-principles answer

`doc_overlap = |goal ∩ doc| / |goal|`: a **bag of words with no structure**. Measured
consequences:

* `Tenacity.retry` — goal contains the literal word "retry"; `retry`'s own docstring is
  *"Wrap a function with a new Retrying object"* and shares **zero** words with the goal.
* `rich.Table` — docstring *"A table"*, while `rich.print`'s says it prints tables. The
  goal "print a table" therefore selects `print`.
* `click.option` — docstring *"Attaches an option to the command"*; the goal's words
  ("parameter", "default", "help") appear nowhere.

**The name is not the statement, and the docstring is not the meaning.** Word overlap matches
patterns. What the artifact states about itself *structurally* — its layout, its declared
surface, its examples — carries information that word overlap cannot see.

---

## 5. What this means for the user's algorithm

The algorithm is **sound and now half-built**:

> scan → know what you don't know → fetch instantly from the guide → use it

* **scan**: works (216 programs, 48 ms)
* **know what you don't know**: works (`is_the_store_sufficient_v1`, 0 probes)
* **fetch instantly**: **works** — 4 libraries, 1.4 MB, ~35 s, no model call
* **use it**: **this is the bottleneck, at 11.8%**

Goal-directed vs learn-everything is settled at **3.0×** in favour of goal-directed. What is
*not* settled is whether 11.8% is a floor that better structure-reading beats, or the ceiling of
this family of methods.

---

## 6. Next bottleneck, named

Not fetching, not the store, not persistence. **Grounding a goal expressed in a person's words
onto the artifact's own vocabulary.** 11.8% of the time the layout gets you there; 88.2% of the
time nothing in the artifact's structure matches the user's phrasing, and a bag of words will
not close that gap.

`truth.achieved` = **`false`**.
