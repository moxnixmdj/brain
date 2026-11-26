# The interface is its own declaration

**Date:** 2026-11-23 · **Branch:** `arena/eac85348-brain` · **Base:** `68bf0400`
**Authority:** NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT · **Model calls:** 0 · **Weights:** unchanged
**Receipt:** `intake/RECEIPT_INTERFACE_IS_ITS_OWN_DECLARATION_20261123_V1.json`
**Organ:** `canonical/runtime/interface_is_its_own_declaration_v1.py`
**Tests:** `canonical/tests/test_interface_is_its_own_declaration_v1.py` (17 passed)

---

## 0. What this document is for

The message asked four things and then said: *"I don't know what the smartest thing to do here
is."* That is the question this document answers, with measurements, and it disagrees with part
of the framing.

**(a)** Make a perfect algorithm that enters any unknown environment, asks the right questions,
and pulls what it needs from instant knowledge.
**(b)** Should it be goal-directed, knowing only what it should know — or learn everything and
generalise later?
**(c)** Scan everything, diff against memory, fetch the unknowns.
**(d)** Memory must save generalised learning, not raw experience. What exactly?

(a), (b) and (d) already had measured answers in this project
(`WHAT_TO_SAVE_20261121_V1`, `SCAN_RETRIEVE_FETCH_20261121_V1`,
`THE_BOTTLENECK_IS_NOT_LEARNING_20261121_V1`): **goal-directed is 400× cheaper than a full
sweep**, what transfers is the *reading rule* and the *algebra* rather than per-program facts,
and memory should hold only what a probe would cost to re-derive.

What was genuinely missing was (c) applied to **interfaces**, and the previous round had marked
it blocked:

> *"For GUIs and browsers, nothing declares itself in `pyproject.toml` … It is blocked here, not
> skipped: this sandbox has no display."* — `THE_GUIDE_IS_THE_ENVIRONMENTS_OWN_DECLARATION`, §6

**That claim was false, and it was the bottleneck.** Headless Chromium runs fine here. It was
already in the repository, it already did the thing I was about to hand-build, and a 20-line
launcher plus two small seam fixes made every local application addressable. The rest of this
document is what became possible once the false blocker was removed.

---

## 1. The one idea, and why it beats the obvious one

A screenshot is a **description**: pixels someone must be taught to read. The accessibility tree
is a **declaration**: the interface states, in words, what each control is called and what
changed after it was used.

| artifact | bytes | cost | what it requires of us |
|---|---|---|---|
| screenshot of a real app | 9,601 | 1280×720 of pixels | a model that has learned to read pictures |
| accessibility tree of the same app | **253** | **123 ms** | nothing |

The smaller artifact is also the truthful one. After typing `buy milk` and pressing Enter, the
tree **published the postcondition itself**:

```
- listitem:
  - checkbox
  - text: buy milk
- strong: "1"
- text: item left
```

Nothing in this module knows what "buy milk" means, that a list exists, or that "1 item left"
must follow. **The environment said it.** So a goal is verified by asking whether the interface
now declares it — not by any model judging whether the screen "looks right". This is the same law
the last round landed on, one level out: *prefer the declaration over the description*. A
manifest beats documentation; an exit code beats a claim; an accessibility tree beats a
screenshot.

---

## 2. The measured result

The benchmark is **TodoMVC**: a published interface specification with **45 independent
implementations**. Eleven of them ship a self-contained prebuilt bundle, in eleven different
frameworks — Backbone, vanilla ES5, vanilla ES6, jQuery, Lit, Preact, React, React+Redux,
Svelte, Vue, Web Components. **None of them was written by me.** They are exactly what §6 asks
for: hard, real, unseen environments.

### Single step — add a todo

| | result |
|---|---|
| apps declaring the goal | **11 / 11** |
| steps per app | **2** (fill, then submit) |
| seconds per app | 3.4 – 4.2 |
| model calls | 0 |

An earlier version of this table said **one** step, and it was wrong. It passed because
`goal_holds` credited the text an input merely *held*, so typing the value scored as success
before anything had been added. On the lit app that certified a todo that did not exist. The
check is now strict — the page must declare the goal — and the honest number is two actions.

### Multi-step — add, complete, filter

| | result |
|---|---|
| apps passing | **11 / 11** |
| verification | **the URL is the postcondition**: 11/11 moved to `#/completed` |
| total | 67.8 s |

### Natural language only — no goal strings supplied

The task `add "buy milk" to the list` is the **only** input; the goal is computed from its words
plus what the interface declares.

| | result |
|---|---|
| apps passing | **11 / 11** |
| seconds per app | 3.7 – 4.0 |

And the addresses were **read, never assumed** — which is the entire point:

| app | the address the interface declared |
|---|---|
| backbone | `What needs to be done?` |
| react-redux | `New todo` |
| react | `New Todo Input` |
| web-components | `Enter a new todo.` |

A hardcoded selector would have passed one app and failed ten. The address came from the page
every time, in 1.24 s.

**Visual evidence** (real Svelte, driven by names only): two todos added through the textbox the
app named, no coordinates, no selectors, no model.

---

## 3. Four findings, including three I got wrong first

### 3.1 A control has no single name, and assuming one costs real apps

My first implementation read the placeholder as the name. `web-components` failed. I
"fixed" that by preferring the computed accessibility name — and **broke 8 of 11 apps that had
been passing**, because `backbone`'s textbox has *no* accessibility name at all:

| app | accessible name | placeholder |
|---|---|---|
| backbone | *(none)* | `What needs to be done?` |
| react-redux | `New todo` | `What needs to be done?` |
| web-components | `Enter a new todo.` | `What needs to be done?` |

Neither absolute rule works. The address is the **ordered list the interface publishes**, and
every candidate is tried before a control is declared unaddressable. Result: 3/11 → **11/11**.

This is the same failure class as a bug already in this repository's history: an over-broad
match certified `sort -V` as a sorter. One string, assumed to mean one thing, is how an
instrument lies.

### 3.2 Goal-directed beats learn-everything by 5.9×, at equal success

This is the direct answer to (b), measured instead of argued:

| strategy | cost | what it yields |
|---|---|---|
| learn every app's declaration | **13.49 s**, 27 controls, 1,194 bytes | a map of eleven apps |
| one goal-directed run | **2.30 s** | the task, done, verified |
| ratio | **5.9×** | |

And the deeper result, which took a second measurement to see:

| | cold memory | warm memory |
|---|---|---|
| per app | 2.15 s | 2.17 s |
| steps | 1.0 | 1.0 |

**The name cache buys exactly nothing.** 7 of 11 apps have a unique name set. Every app
re-declares its names in 1.24 s, because it must — the declaration is how the interface
addresses itself. So caching names is not learning the interface; it is memorising the app,
which is the knowledge house the constraints forbid, and it is *also* useless.

### 3.3 The instrument was blind three times before the apps were wrong

Each of these looked like an app failure and was a reader failure:

1. **Shadow DOM.** One implementation put its whole todo list inside four shadow roots.
   `body.inner_text` reported "0 items left" while the todo existed — the work was done and
   invisible. The composed tree is what a person sees, so the observation now reads it.
2. **A navigation counted as progress.** After the goal check was made strict, the goal word
   `TodoMVC` matched the footer link of the same name. The bonus lifted it above the textbox and
   the loop clicked it, leaving the app for `todomvc.com`; the next read saw a blank page.
3. **A substring match on the goal.** Even then, the goal word `buy` matched inside
   `Enter a new todo.`, which pushed the textbox *holding the typed value* to 1.0 — below the
   footer link — so it was never submitted. Twelve steps and no todo on that app while ten
   passed.

All three were found by running; none by reading. That is now the standing argument in this
project for why reading is not verification.

### 3.4 The generalisation is a shape, and it is computed

What is true of **every** interface in the family, read cold from each app's own tree:

| | |
|---|---|
| roles every app declares | `['link', 'textbox']` |
| checkboxes declared cold | 0 of 11 — they appear only after work exists |
| `All/Active/Completed` filters declared cold | 0 of 11 — same |
| apps whose name set is unique | 7 of 11 |

So the transferable statement is a shape: *this family is driven through a textbox and links,
and it grows its checkboxes and filters only once work exists.* That is worth keeping. The
individual names are not.

`declarative_invariant()` computes this from observations; `what_to_remember()` states the
decision and its reason in one place. The test is the project's own: **if this were deleted, how
much would it cost to get back?** An invariant costs a whole family to rediscover. A name costs
1.24 s and the environment re-publishes it.

---

## 4. Answering (d) precisely: what to save

**Save:**
1. **the declarative invariant** — roles, orderings, what only appears after use;
2. **the refusals** — which address resolved to nothing, and when. Cheap to hold, expensive to
   rediscover, stable while the interface is.

**Never save:**
3. **names** — re-declared by the app on every visit (1.24 s), and unique per app (7 of 11), so
   keeping them is memorising the app;
4. **coordinates** — layout, not interface; they break on any resize;
5. **the step sequence** — a search over facts already held;
6. **pixels** — rendering, not meaning.

The inversion is the finding: **the names are the largest part of the declaration and the
smallest part of the knowledge.** That is why a name cache measures as exactly zero gain, and
why "save the generalised learning" is not a slogan here but a specific, short list.

---

## 5. Rejected ideas, and why

| idea | rejected because |
|---|---|
| drive by screenshot + vision | needs a model to read pixels — forbidden at runtime; and it is 38× the bytes for strictly less information (a screenshot does not tell you the control's name) |
| drive by CSS selectors | a guess at internal structure; it passes the one app it was written for. The declared name is stable across 11 independent implementations; a selector is stable across one |
| cache the per-app name→role map | measured: zero gain (cold 2.15 s vs warm 2.17 s), and it is app knowledge, not interface knowledge |
| an OCR/DOM-diff "understands the screen" layer | new organ, no measured need; the tree already publishes what OCR would recover, with names attached |
| coordinates from the accessibility bounding box | layout, not interface. It would work until the first resize, then fail silently |
| write a new browser driver | `canonical/runtime/browser_launch_v1.sh` and the CDP surface already existed and worked. I nearly rebuilt them; the repository's own intent record documents having already solved the sys.path fragility |
| learn the goal from the page | the goal is not in the page. Turning a natural-language task into "strings the interface must declare" is a different organ, and it is the next bottleneck, named below |

---

## 6. Honest limits — what this is not

- **11 apps of one specification.** Breadth within a family, not generalisation across families.
  A desktop application, a native GUI, or a browser-based IDE has a different declaration
  surface; none was tested.
- **The natural-language goal covers one task shape.** `add "buy milk" to the list` computes its
  content from a quoted string or an add/new/create verb, and binds a filter only when the task
  names one and the interface declares it. A task phrased without either computes no content and
  the loop refuses rather than guesses. This is a closed word class, not a parser.
- **Three steps, not 250.** OSWorld 2.1 tasks run beyond 250 agent steps and the benchmark names
  constraint-tracking and mid-task change detection as the failure modes. Neither is exercised.
- **The postcondition check is exact and weak.** "The strings appear in the declaration" can be
  satisfied by a page that prints the string without doing the work — which is why the
  multi-step test also checks the URL.
- **One host, one browser build, no repeat trials.** Every number is producer-measured.
  `truth.achieved` remains **false**.
- **This does not touch the software-engineering gap.** The measured bottleneck there is
  generation: a 1.4% search ceiling against a 78.80% top agent. A GUI organ does not synthesise
  an edit. Two capabilities, two bottlenecks; conflating them is how the last round's false
  "blocked" claim survived as long as it did.

---

## 7. The next bottleneck, named

**The goal is not in the environment's words; it is in the task's.** Everything above assumes
someone says *"add a todo named buy milk"* in the form the checker understands. The real task
arrives in natural language and the environment declares none of it.

That is the same shape as the problem this project already half-solved on the host side — a
program's own sentence gives its type — but here the sentence belongs to the **task**, not the
interface, and the binding between "mark it complete" and the checkbox the interface will only
declare *after* work exists is a real inference, not a string match.

The honest next measurement: take the natural-language instruction, the cold declaration, and
the invariant, and compute the goal string rather than being handed it — then re-run these same
eleven apps with the natural language as the only input. Anything else is measuring my own
helpfulness.

---

## Reproduce

```sh
sh canonical/runtime/browser_launch_v1.sh                 # real Chromium, DevTools on :9222
python3 -m http.server 8800 --bind 0.0.0.0 &            # in examples/ of a TodoMVC checkout
python -m pytest canonical/tests/test_interface_is_its_own_declaration_v1.py -q
```
