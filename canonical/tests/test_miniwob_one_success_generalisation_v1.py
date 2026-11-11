"""One success, then unseen instances: what the measurement and the learner guarantee.

The pages below are written by this file, in Python, with the same commands and the same
observation shape as the node bridge. Each page knows its own right answer, so every expected
value here comes from the page's DEFINITION and never from what an arm says about itself.

What these tests do NOT show: anything about MiniWoB++ or about a real screen. They show that
the instrument counts what it claims to count and that the learner does what its docstring
says. The numbers about real pages live in `canonical/verification/`.
"""
from __future__ import annotations

import os
import random
import shutil
import tempfile
import unittest

from canonical.runtime import demonstration_version_space_v1 as vs
from canonical.runtime import systematic_exploration_v1 as sx
from canonical.tools import miniwob_one_success_generalisation_measure_v1 as tool

WORDS = ["Alba", "Bram", "Cleo", "Dion", "Enya", "Finn", "Gwen", "Hugo", "Ines", "Jude", "Kira", "Lars"]


def _element(index, parent, tag, text="", *, click=False, type_=False, **extra):
    record = {"index": index, "parent": parent, "tag": tag, "text": text,
              "can_click": bool(click), "can_type": bool(type_)}
    record.update(extra)
    return record


class _Page:
    """One instance of one stub task. `rows` are (tag, text, extra) under a single container."""

    def __init__(self, utterance, rows, judge, *, steps_allowed=10):
        self.utterance = utterance
        self.rows = [dict(tag=tag, text=text, extra=dict(extra)) for tag, text, extra in rows]
        self.judge = judge          # (page, row_index) -> None | +1 | -1, called on every click
        self.done, self.reward, self.clicked = False, 0.0, []
        self.left = steps_allowed

    def observe(self):
        elements = [_element(0, -1, "body"), _element(1, 0, "div", id="area")]
        for row in self.rows:
            extra = dict(row["extra"])
            inside = extra.pop("inside", None)       # the row (by position) that contains this one, if any
            is_input = row["tag"] == "input" and extra.get("type", "text") == "text"
            elements.append(_element(len(elements), 1 if inside is None else inside + 2, row["tag"], row["text"],
                                     click=True, type_=is_input, **extra))
        return {"utterance": self.utterance, "done": self.done, "raw_reward": self.reward, "reason": None,
                "virtual_ms": 500 * (10 - self.left), "elements": elements, "js_errors": []}

    def act(self, action):
        if self.done:
            return self.observe()
        row = action["index"] - 2
        if 0 <= row < len(self.rows):
            if action["type"] == "type":
                self.rows[row]["extra"]["value"] = action["text"]
            else:
                self.clicked.append(row)
                verdict = self.judge(self, row)
                if verdict is not None:
                    self.done, self.reward = True, float(verdict)
        self.left -= 1
        if self.left <= 0 and not self.done:
            self.done, self.reward = True, -1.0
        return self.observe()


def _named_button(seed):
    """`Click on the "X" button.` among shuffled buttons, behind a varying number of decoys."""
    rng = random.Random(f"named:{seed}")
    labels = rng.sample(WORDS, 4)
    target = rng.choice(labels)
    rows = [("div", w.lower() + " note", {}) for w in rng.sample(WORDS, rng.randint(0, 3))]
    rows += [("button", label, {}) for label in labels]
    return _Page(f'Click on the "{target}" button.', rows,
                 lambda page, r: (1 if page.rows[r]["text"] == target else -1) if page.rows[r]["tag"] == "button" else None)


def _type_and_submit(seed):
    rng = random.Random(f"type:{seed}")
    word = rng.choice(WORDS) + str(rng.randint(10, 99))
    rows = [("input", "", {"type": "text", "id": "tt", "value": ""}), ("button", "Submit", {"id": "subbtn"})]
    return _Page(f'Enter "{word}" into the text field and press Submit.', rows,
                 lambda page, r: (1 if page.rows[0]["extra"]["value"] == word else -1) if r == 1 else None)


def _shout_and_submit(seed):
    """The page wants the quoted word in capitals: the typed text is not a substring of the instruction."""
    rng = random.Random(f"shout:{seed}")
    word = rng.choice(WORDS).lower()
    rows = [("input", "", {"type": "text", "id": "tt", "value": ""}), ("button", "Submit", {"id": "subbtn"})]
    return _Page(f'Type "{word}" in capital letters and press Submit.', rows,
                 lambda page, r: (1 if page.rows[0]["extra"]["value"] == word.upper() else -1) if r == 1 else None)


def _shout_or_whisper(seed):
    """Two ways of asking: capitals on some instances, small letters on the others."""
    rng = random.Random(f"case:{seed}")
    word = rng.choice(WORDS)
    loud = rng.random() < 0.5
    wanted = word.upper() if loud else word.lower()
    rows = [("input", "", {"type": "text", "id": "tt", "value": ""}), ("button", "Submit", {"id": "subbtn"})]
    return _Page(f'Type "{word}" in all {"upper" if loud else "lower"} case letters and press Submit.', rows,
                 lambda page, r: (1 if page.rows[0]["extra"]["value"] == wanted else -1) if r == 1 else None)


def _numbered_section(seed, *, shows_that_it_opened=True, decoys=False):
    """Open the section (its title changes every time), then press Submit. The instruction never changes."""
    rng = random.Random(f"section:{seed}")
    title = f"Section #{rng.randint(1, 60)}"
    rows = [("div", w.lower() + " note", {}) for w in rng.sample(WORDS, rng.randint(0, 3))] if decoys else []
    header = len(rows)
    rows += [("h3", title, {"role": "tab"}), ("button", "Submit", {"id": "subbtn"})]

    def judge(page, r):
        if r == header + 1:
            return 1 if header in page.clicked[:-1] else -1
        if r == header and shows_that_it_opened and len(page.rows) == header + 2:
            page.rows.append(dict(tag="div", text="lorem ipsum", extra={}))
        return None
    return _Page("Expand the section below and click submit.", rows, judge)


def _shifting_section(seed):
    """The numbered section behind a varying number of unrelated rows: positions move, the instruction does not."""
    return _numbered_section(seed, decoys=True)


def _chatty_section(seed):
    """The shifting section with an instruction that changes every time and says nothing new."""
    page = _shifting_section(seed)
    page.utterance = f"Expand the section below and click submit, {random.Random(f'chat:{seed}').choice(WORDS)}."
    return page


def _mail_rows(seed):
    """A list of rows, each with a sender and the same two icons. The instruction names a sender;
    the right click is the trash icon IN THAT ROW. Nothing about the icon itself says whose it is."""
    rng = random.Random(f"mail:{seed}")
    senders = rng.sample(WORDS, rng.randint(3, 5))
    wanted = rng.choice(senders)
    rows = []
    for sender in senders:
        base = len(rows)
        rows.append(("div", "", {"classes": "email-thread"}))
        rows.append(("span", sender, {"classes": "email-sender", "inside": base}))
        rows.append(("span", rng.choice(WORDS).lower() + " news", {"classes": "email-subject", "inside": base}))
        rows.append(("span", "", {"classes": "star", "inside": base}))
        rows.append(("span", "", {"classes": "trash", "inside": base}))

    def judge(page, r):
        if page.rows[r]["extra"].get("classes") != "trash":
            return None if page.rows[r]["extra"].get("classes") != "star" else -1
        owner = page.rows[page.rows[r]["extra"]["inside"] + 1]["text"]
        return 1 if owner == wanted else -1
    return _Page(f"Find the email by {wanted} and click the trash icon to delete it.", rows, judge)


def _widget_kind(seed):
    """`Click on a "textarea" widget.`: the instruction names the KIND of element, not its label."""
    rng = random.Random(f"widget:{seed}")
    kinds = ["button", "textarea", "select", "h3", "label"]
    rng.shuffle(kinds)
    wanted = rng.choice(kinds)
    rows = [("div", w.lower() + " note", {}) for w in rng.sample(WORDS, rng.randint(0, 2))]
    rows += [(kind, "", {}) for kind in kinds]
    return _Page(f'Click on a "{wanted}" widget.', rows,
                 lambda page, r: (1 if page.rows[r]["tag"] == wanted else -1) if page.rows[r]["tag"] != "div" else None)


def _hidden_latch(seed):
    """The same task, but opening the section changes nothing the observation shows."""
    return _numbered_section(seed, shows_that_it_opened=False)


def _nth_box(seed):
    rng = random.Random(f"nth:{seed}")
    count = rng.randint(3, 5)
    wanted = rng.randint(1, count)
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(wanted, "th")
    rows = [("input", "", {"type": "text", "value": ""}) for _ in range(count)]
    return _Page(f"Focus into the {wanted}{suffix} input textbox.", rows,
                 lambda page, r: 1 if r == wanted - 1 else -1)


def _always_the_same(seed):
    rows = [("button", "Open", {}), ("button", "Confirm", {})]

    def judge(page, r):
        if r == 1:
            return 1 if 0 in page.clicked[:-1] else -1
        page.rows[0]["text"] = "Opened"
        return None
    return _Page("Open it and confirm.", rows, judge)


def _hidden_answer(seed):
    """Every instance looks the same; which button is right depends on something not shown."""
    rows = [("button", "A", {}), ("button", "B", {}), ("button", "C", {})]
    return _Page("Press the right button.", rows, lambda page, r: 1 if r == seed % 3 else -1)


def _one_or_two(seed):
    """Even instances need one click, odd ones need two: successes of different shapes."""
    rows = [("button", "Go", {}), ("button", "Arm", {})]

    def judge(page, r):
        if r == 0:
            return 1 if (seed % 2 == 0 or 1 in page.clicked[:-1]) else -1
        page.rows[1]["text"] = "Armed"
        return None
    return _Page("Go.", rows, judge)


def _unsolvable(seed):
    return _Page("Nothing here works.", [("button", "No", {}), ("button", "Never", {})], lambda page, r: -1)


def _two_fields(seed):
    """Two values, each named in the instruction, each into its own field, then the right button.
    A third field and a second button are there to be wrong with."""
    rng = random.Random(f"fields:{seed}")
    user, secret = rng.choice(WORDS).lower(), rng.choice(WORDS)[:2].upper() + str(rng.randint(2, 9))
    rows = [("label", "Username", {}), ("input", "", {"type": "text", "id": "username", "value": ""}),
            ("label", "Password", {}), ("input", "", {"type": "text", "id": "password", "value": ""}),
            ("label", "Notes", {}), ("input", "", {"type": "text", "id": "notes", "value": ""}),
            ("button", "Cancel", {"id": "cancel"}), ("button", "Login", {"id": "subbtn"})]

    def judge(page, r):
        if page.rows[r]["tag"] != "button":
            return None
        if r == 6:
            return -1
        return 1 if (page.rows[1]["extra"]["value"] == user and page.rows[3]["extra"]["value"] == secret) else -1
    return _Page(f'Enter the username "{user}" and the password "{secret}" into the text fields and press login.',
                 rows, judge, steps_allowed=12)


def _three_boxes(seed):
    """Tick every named box, then Submit. The page pays PART of the reward for part of the boxes."""
    rng = random.Random(f"boxes:{seed}")
    names = rng.sample(WORDS, 5)
    wanted = sorted(rng.sample(names, 3), key=names.index)
    rows = [("label", name, {"checked": False}) for name in names] + [("button", "Submit", {"id": "subbtn"})]

    def judge(page, r):
        if r < len(names):
            page.rows[r]["extra"]["checked"] = not page.rows[r]["extra"]["checked"]
            return None
        ticked = [row["text"] for row in page.rows[:len(names)] if row["extra"]["checked"]]
        if any(name not in wanted for name in ticked):
            return -1
        return len(ticked) / len(wanted) if ticked else -1
    return _Page(f"Select {', '.join(wanted)} and click Submit.", rows, judge, steps_allowed=12)


def _named_decoy(seed):
    """The instruction mentions a note nobody has to open. Opening it changes the page and decides nothing."""
    rows = [("div", "Help", {}), ("button", "Go", {})]

    def judge(page, r):
        if r == 1:
            return 1
        page.rows[0]["text"] = "Help was opened"
        return None
    return _Page("The Help note is optional. Press Go.", rows, judge)


def _any_boxes(seed, *, in_order=False, always=None):
    """Tick every box the instruction names -- none, one or up to five of them -- then Submit. The names
    come in no particular order. With `in_order` the page only pays when they were ticked in the order
    they are named in."""
    rng = random.Random(f"anyboxes:{seed}")
    names = rng.sample(WORDS, 6)
    count = always if always is not None else (3 if seed == 0 else rng.randint(0, 5))
    wanted = rng.sample(names, count)
    if seed == 0:
        wanted.sort(key=names.index, reverse=True)       # where a first success is found, they are named last to first
    rows = [("label", name, {"checked": False}) for name in names] + [("button", "Submit", {"id": "subbtn"})]

    def judge(page, r):
        if r < len(names):
            page.rows[r]["extra"]["checked"] = not page.rows[r]["extra"]["checked"]
            return None
        ticked = [row["text"] for row in page.rows[:len(names)] if row["extra"]["checked"]]
        pressed = [names[k] for k in page.clicked[:-1]]
        return 1 if sorted(ticked) == sorted(wanted) and (not in_order or pressed == wanted) else -1
    return _Page(f"Select {', '.join(wanted) if wanted else 'nothing'} and click Submit.", rows, judge, steps_allowed=14)


def _boxes_in_the_order_named(seed):
    return _any_boxes(seed, in_order=True)


def _one_box(seed):
    """The boxes page, but the instruction of the demonstration names exactly one box."""
    return _any_boxes(seed, always=1 if seed == 0 else None)


def _drawers(seed, *, one_open=False):
    """Three drawers. Pulling one shows its two things and hides whatever was shown. The instruction names
    one thing. A Close button, which is no drawer, ends everything badly. With `one_open` some drawer
    stands open at the start, so the thing named is sometimes simply there."""
    rng = random.Random(f"drawers:{seed}")
    things = rng.sample(WORDS, 6)
    target = rng.choice(things)

    def inside(k):
        return [dict(tag="span", text=thing, extra={"classes": "thing"}) for thing in things[2 * k: 2 * k + 2]]

    def judge(page, r):
        row = page.rows[r]
        if row["extra"].get("classes") == "drawer":
            page.pulled.append(row["text"])
            page.rows[4:] = inside(r)
            return None
        if row["extra"].get("classes") == "shut":
            return -1
        return 1 if row["text"] == target else -1
    rows = [("h4", f"Drawer {k + 1}", {"classes": "drawer"}) for k in range(3)] + [("button", "Close", {"classes": "shut"})]
    page = _Page(f'Find "{target}" in the drawers and take it.', rows, judge, steps_allowed=12)
    page.pulled = []
    if one_open:
        # on the instance a first success is found on, the open drawer is the one with the thing in it
        page.rows[4:] = inside(things.index(target) // 2 if seed == 0 else rng.randrange(3))
    return page


def _drawers_one_open(seed):
    return _drawers(seed, one_open=True)


def _starts_and_ends(seed):
    """Nine items, every beginning with every ending. `Take the item that starts with "Al" and ends with "on".`"""
    rng = random.Random(f"ends:{seed}")
    heads, tails = rng.sample(["Al", "Br", "Cl", "Di", "En"], 3), rng.sample(["ba", "am", "eo", "on", "ya"], 3)
    items = [head + "x" + tail for head in heads for tail in tails]
    rng.shuffle(items)
    head, tail = rng.choice(heads), rng.choice(tails)
    return _Page(f'Take the item that starts with "{head}" and ends with "{tail}".',
                 [("li", item, {"classes": "pick"}) for item in items],
                 lambda page, r: 1 if page.rows[r]["text"] == head + "x" + tail else -1)


def _ledger(seed):
    """A ledger of names and values side by side. `Enter the value of Town into the text field and press Submit.`
    The value is on the page and not in the instruction."""
    rng = random.Random(f"ledger:{seed}")
    keys = rng.sample(["Colour", "Size", "Owner", "Town", "Year", "Shape"], 4)
    values = rng.sample(WORDS, 4)
    rows = []
    for key, value in zip(keys, values):
        rows += [("td", key, {}), ("td", value, {})]
    rows += [("input", "", {"type": "text", "id": "tt", "value": ""}), ("button", "Submit", {"id": "subbtn"})]
    asked = rng.randrange(4)

    def judge(page, r):
        if page.rows[r]["tag"] != "button":
            return None
        return 1 if page.rows[8]["extra"]["value"] == values[asked] else -1
    return _Page(f"Enter the value of {keys[asked]} into the text field and press Submit.", rows, judge, steps_allowed=12)


_TASKS = {"two-fields": _two_fields, "three-boxes": _three_boxes, "named-decoy": _named_decoy,
          "named-button": _named_button, "type-and-submit": _type_and_submit, "shout-and-submit": _shout_and_submit,
          "numbered-section": _numbered_section, "nth-box": _nth_box, "always-the-same": _always_the_same,
          "hidden-answer": _hidden_answer, "one-or-two": _one_or_two, "unsolvable": _unsolvable,
          "hidden-latch": _hidden_latch, "shout-or-whisper": _shout_or_whisper, "chatty-section": _chatty_section,
          "shifting-section": _shifting_section, "mail-rows": _mail_rows, "widget-kind": _widget_kind,
          "any-boxes": _any_boxes, "boxes-in-the-order-named": _boxes_in_the_order_named, "one-box": _one_box,
          "drawers": _drawers, "drawers-one-open": _drawers_one_open, "starts-and-ends": _starts_and_ends,
          "ledger": _ledger}


class StubBridge:
    """Same surface as `tool.Bridge`, pages from `_TASKS`. Counts what is done to it."""

    def __init__(self, *, drifting=(), forgetful=(), loads_allowed=None):
        self.task, self.page = None, None
        self.resets, self.acts, self.loads = [], 0, 0
        self._drifting, self._forgetful = set(drifting), set(forgetful)
        self._loads_allowed = loads_allowed
        self._visits = 0
        self._fresh = True

    def versions(self):
        return {"node": "stub", "jsdom": "stub", "fake_timers": "stub", "step_ms": 500, "epoch_ms": 0}

    def load(self, task):
        self.loads += 1
        if self._loads_allowed is not None and self.loads > self._loads_allowed:
            self.task = None
            return {"ok": False, "js_errors": []}
        self.task = task if task in _TASKS else None
        self._fresh = True
        return {"ok": self.task is not None, "js_errors": []}

    def reset(self, seed, *, time_limit_ms=None):
        self.resets.append(seed)
        self._visits += 1
        effective = seed + self._visits if self.task in self._drifting else seed
        self.page = _TASKS[self.task](effective)
        if self.task in self._forgetful and self._fresh:
            # a page that only rewards once it has some history: a success found late does not replay fresh
            self.page.judge = lambda page, r: -1
        self._fresh = False
        return self.page.observe()

    def act(self, action):
        self.acts += 1
        return self.page.act(action)

    def restart(self):
        pass

    def close(self):
        pass


def _demonstrate(bridge, task, seed=0, budget=300):
    shown = tool.demonstrate(bridge, task, seed, action_budget=budget)
    assert shown["stage"] == tool.STAGE_DEMONSTRATED, (task, shown["stage"])
    return shown["trace"], shown["acquisition"]


TEST_SEEDS = list(range(1000, 1030))


class SlotTests(unittest.TestCase):
    def test_a_slot_cuts_the_same_role_out_of_a_different_instruction(self):
        first = 'Enter "Tora" into the text field and press Submit.'
        rules = vs.slots_returning(first, "Tora")
        self.assertIn(("quoted", 0), rules)
        second = 'Enter "Mable" into the text field and press Submit.'
        for rule in rules:
            self.assertEqual(vs.extract(rule, second), "Mable", rule)

    def test_an_unquoted_word_is_found_by_its_neighbours(self):
        rules = vs.slots_returning("Select Brazil from the list and click Submit.", "Brazil")
        self.assertEqual(rules, [("between", "Select", "from")])
        self.assertEqual(vs.extract(rules[0], "Select New Zealand from the list and click Submit."), "New Zealand")

    def test_a_rule_that_finds_nothing_says_so(self):
        self.assertIsNone(vs.extract(("quoted", 1), 'Only "one" here.'))
        self.assertIsNone(vs.extract(("between", "Select", "from"), "Pick Brazil in the list."))
        self.assertIsNone(vs.extract(("number", 0), "No digits."))

    def test_text_that_is_not_in_the_instruction_has_no_slot(self):
        self.assertEqual(vs.slots_returning('Enter "Tora" and press Submit.', "Section #40"), [])
        self.assertEqual(vs.slots_returning('Enter "Tora" and press Submit.', "ora"), [])   # not on word boundaries


class DescriptionTests(unittest.TestCase):
    def _page(self, seed=0, task="named-button"):
        return _TASKS[task](seed).observe()

    def test_every_description_generated_for_an_element_selects_that_element_first(self):
        observation = self._page(3)
        page = vs.Page(observation)
        for index, element in enumerate(observation["elements"]):
            if element["tag"] != "button":
                continue
            found = vs.descriptions_of(page, index)
            self.assertTrue(found)
            for description in found:
                self.assertEqual(vs.pick(description, page), index, description)

    def test_a_tie_to_the_instruction_is_preferred_to_position_and_to_quoted_content(self):
        observation = self._page(5)
        target = observation["utterance"].split('"')[1]
        index = next(e["index"] for e in observation["elements"] if e["text"] == target)
        page = vs.Page(observation)
        ranked = sorted(vs.descriptions_of(page, index), key=lambda d: vs.preference(d, [page]))
        first_tests, first_position = ranked[0]
        self.assertTrue(any(t[0] == "slot" for t in first_tests))
        self.assertIsNone(first_position)
        kinds = [vs.preference(d, [page])[0] for d in ranked]
        self.assertEqual(kinds, sorted(kinds))
        self.assertIn(3, kinds)      # positional readings exist; they are simply last

    def test_a_description_selects_nothing_on_a_page_where_it_has_no_referent(self):
        page = vs.Page(self._page(0, "numbered-section"))
        title = page.elements[2]["text"]
        description = ((("equals", "self", "text", title),), None)
        self.assertEqual(vs.pick(description, page), 2)
        other = next(vs.Page(self._page(s, "numbered-section")) for s in range(1, 50)
                     if _TASKS["numbered-section"](s).rows[0]["text"] != title)
        self.assertIsNone(vs.pick(description, other))


class SkillFromOneSuccessTests(unittest.TestCase):
    def _score(self, task, arm, bridge=None):
        bridge = bridge or StubBridge()
        return tool.score_arm(bridge, task, arm, TEST_SEEDS)

    def _skills(self, task):
        bridge = StubBridge()
        trace, _ = _demonstrate(bridge, task)
        skills = vs.SkillSet()
        self.assertEqual(skills.add_success(trace), "new_way")
        return skills, trace

    def test_the_named_button_is_found_on_pages_never_seen(self):
        skills, trace = self._skills("named-button")
        arm = vs.VersionSpaceArm(skills, {})
        self.assertEqual(self._score("named-button", arm)["successes"], len(TEST_SEEDS))
        # ... and position alone does not do it: the same clicks replayed mostly miss
        self.assertLess(self._score("named-button", tool.VerbatimArm(trace))["successes"], len(TEST_SEEDS) // 2)

    def test_typed_text_follows_the_instruction(self):
        skills, trace = self._skills("type-and-submit")
        self.assertEqual(self._score("type-and-submit", vs.VersionSpaceArm(skills, {}))["successes"], len(TEST_SEEDS))
        self.assertEqual(self._score("type-and-submit", tool.VerbatimArm(trace))["successes"], 0)

    def test_text_the_page_wants_transformed_is_transformed(self):
        skills, _ = self._skills("shout-and-submit")
        self.assertEqual(self._score("shout-and-submit", vs.VersionSpaceArm(skills, {}))["successes"], len(TEST_SEEDS))

    def test_content_that_changes_every_time_is_not_what_the_skill_holds_on_to(self):
        skills, _ = self._skills("numbered-section")
        self.assertEqual(self._score("numbered-section", vs.VersionSpaceArm(skills, {}))["successes"], len(TEST_SEEDS))

    def test_a_position_named_in_the_instruction_is_read_from_the_instruction(self):
        skills, _ = self._skills("nth-box")
        self.assertEqual(self._score("nth-box", vs.VersionSpaceArm(skills, {}))["successes"], len(TEST_SEEDS))

    def test_what_cannot_be_seen_cannot_be_learned(self):
        skills, trace = self._skills("hidden-answer")
        learned = self._score("hidden-answer", vs.VersionSpaceArm(skills, {}))["successes"]
        replayed = self._score("hidden-answer", tool.VerbatimArm(trace))["successes"]
        self.assertEqual(learned, replayed)                       # the skill is exactly the replay
        self.assertEqual(learned, sum(1 for s in TEST_SEEDS if s % 3 == 0))   # right only where the hidden answer repeats

    def test_one_way_of_asking_learned_is_one_way_of_asking_solved(self):
        skills, trace = self._skills("shout-or-whisper")
        loud = "upper" in trace[0][0]["utterance"]
        scored = self._score("shout-or-whisper", vs.VersionSpaceArm(skills, {}))
        same_way = sum(1 for s in TEST_SEEDS if ("upper" in _TASKS["shout-or-whisper"](s).utterance) == loud)
        self.assertEqual(scored["successes"], same_way)
        self.assertTrue(0 < same_way < len(TEST_SEEDS))

    def test_the_skill_never_acts_on_an_element_that_cannot_take_the_action(self):
        skills, _ = self._skills("type-and-submit")
        observation = _TASKS["type-and-submit"](77).observe()
        for element in observation["elements"]:
            element["can_type"] = False
        self.assertIsNone(skills.skills[0].act(0, observation))

    def test_past_the_last_step_there_is_no_action(self):
        skills, trace = self._skills("named-button")
        self.assertIsNone(skills.skills[0].act(len(trace), _TASKS["named-button"](9).observe()))


class NamedByTheInstructionTests(unittest.TestCase):
    """Two things an instruction can do besides quoting a label: name the element's neighbourhood, or its kind."""

    def _one_success(self, task):
        bridge = StubBridge()
        trace, _ = _demonstrate(bridge, task)
        skills = vs.SkillSet()
        skills.add_success(trace)
        return bridge, trace, skills

    def test_nearest_is_the_candidate_sharing_the_deepest_container_with_the_named_element(self):
        observation = _TASKS["mail-rows"](4).observe()
        page = vs.Page(observation)
        wanted = observation["utterance"].split(" by ")[1].split(" and ")[0]
        rule = vs.slots_returning(observation["utterance"], wanted)[0]
        trash = ((("equals", "self", "classes", "trash"),), ("nearest", "text", rule, "exact"))
        picked = vs.pick(trash, page)
        row = observation["elements"][picked]["parent"]
        names = [e["text"] for e in observation["elements"] if e["parent"] == row and e.get("classes") == "email-sender"]
        self.assertEqual(names, [wanted])                       # the icon picked sits in the named sender's row
        self.assertEqual(observation["elements"][picked]["classes"], "trash")
        # the row itself is "nearest" to its own sender too: a container of the named element counts as close
        thread = ((("equals", "self", "classes", "email-thread"),), ("nearest", "text", rule, "exact"))
        self.assertEqual(vs.pick(thread, page), row)
        # no element named by the instruction on the page: the description selects nothing, it does not guess
        nobody = ((("equals", "self", "classes", "trash"),), ("nearest", "text", ("quoted", 0), "exact"))
        self.assertIsNone(vs.pick(nobody, page))

    def test_two_candidates_equally_near_the_first_in_the_page_is_taken(self):
        elements = [_element(0, -1, "body"), _element(1, 0, "div"),
                    _element(2, 1, "div", classes="row"), _element(3, 2, "span", "Alba"),
                    _element(4, 2, "span", classes="icon", click=True), _element(5, 2, "span", classes="icon", click=True),
                    _element(6, 1, "div", classes="row"), _element(7, 6, "span", "Bram"),
                    _element(8, 6, "span", classes="icon", click=True), _element(9, 6, "span", classes="icon", click=True)]
        for wanted, expected in (("Alba", 4), ("Bram", 8)):
            page = vs.Page({"utterance": f"Open the item of {wanted} now.", "elements": elements})
            rule = vs.slots_returning(page.instruction, wanted)[0]
            icon = ((("equals", "self", "classes", "icon"),), ("nearest", "text", rule, "exact"))
            self.assertEqual(vs.matches(icon, page), [expected])
        self.assertEqual(page.closeness(8, 7), 3)      # body, outer div, the row
        self.assertEqual(page.closeness(4, 7), 2)      # body, outer div
        self.assertEqual(page.closeness(7, 7), 4)      # an element is closest to itself

    def test_the_named_row_wins_over_the_first_row_even_when_the_demonstration_was_in_the_first_row(self):
        # the hardest single example: the named sender happened to be first, so "the first trash
        # icon on the page" explains the click just as well as "the trash icon in that sender's row"
        seed = next(s for s in range(300) if _TASKS["mail-rows"](s).rows[1]["text"] in _TASKS["mail-rows"](s).utterance)
        bridge = StubBridge()
        trace, _ = _demonstrate(bridge, "mail-rows", seed=seed)
        self.assertEqual(trace[0][0]["elements"][tool.parse_action(trace[0][1])["index"]]["parent"], 2)   # first row
        skills = vs.SkillSet()
        skills.add_success(trace)
        scored = tool.score_arm(bridge, "mail-rows", vs.VersionSpaceArm(skills, {}), TEST_SEEDS)
        self.assertEqual(scored["successes"], len(TEST_SEEDS))

    def test_the_icon_in_the_row_of_the_named_sender_is_learned_from_one_success(self):
        bridge, trace, skills = self._one_success("mail-rows")
        scored = tool.score_arm(bridge, "mail-rows", vs.VersionSpaceArm(skills, {}), TEST_SEEDS)
        self.assertEqual(scored["successes"], len(TEST_SEEDS))
        # neither position nor the existing compiler can do it: every icon looks the same
        self.assertLess(tool.score_arm(bridge, "mail-rows", tool.VerbatimArm(trace), TEST_SEEDS)["successes"],
                        len(TEST_SEEDS) // 2)
        self.assertLess(tool.score_arm(bridge, "mail-rows", tool.ExistingCompilerArm(trace), TEST_SEEDS)["successes"],
                        len(TEST_SEEDS) // 2)
        # and it is the instruction that carries it: with the old sender's name it goes to the old sender's row
        blind = tool.InstructionBlindArm(vs.VersionSpaceArm(skills, {}), trace[0][0]["utterance"])
        self.assertLess(tool.score_arm(bridge, "mail-rows", blind, TEST_SEEDS)["successes"], len(TEST_SEEDS) // 2)

    def test_an_element_named_by_its_kind_is_found(self):
        bridge, trace, skills = self._one_success("widget-kind")
        scored = tool.score_arm(bridge, "widget-kind", vs.VersionSpaceArm(skills, {}), TEST_SEEDS)
        self.assertEqual(scored["successes"], len(TEST_SEEDS))
        self.assertLess(tool.score_arm(bridge, "widget-kind", tool.VerbatimArm(trace), TEST_SEEDS)["successes"],
                        len(TEST_SEEDS) // 2)

    def test_the_sender_name_is_treated_as_a_slot_when_choosing_between_programs(self):
        bridge, trace, skills = self._one_success("mail-rows")
        other = _TASKS["mail-rows"](77).utterance
        self.assertNotEqual(other, trace[0][0]["utterance"])
        self.assertEqual(vs.mismatch(skills.skills[0], other), 0)


class MoreSuccessesTests(unittest.TestCase):
    def test_a_second_success_strikes_out_what_would_have_done_something_else(self):
        bridge = StubBridge()
        trace, _ = _demonstrate(bridge, "named-button", seed=0)
        skill = vs.VersionSpaceSkill()
        skill.add_success(trace)
        before = skill.describe()["steps"][0]["descriptions_left"]
        other, _ = _demonstrate(bridge, "named-button", seed=1)
        self.assertNotEqual(trace[0][0]["utterance"], other[0][0]["utterance"])
        self.assertTrue(skill.add_success(other))
        after = skill.describe()["steps"][0]["descriptions_left"]
        self.assertLess(after, before)
        self.assertGreater(after, 0)
        # everything that survives selects the acted-on element in BOTH successes
        for observation, action in (trace[0], other[0]):
            page = vs.Page(observation)
            wanted = tool.parse_action(action)["index"]
            for description in skill._targets[0]:
                self.assertEqual(vs.pick(description, page), wanted)

    def test_a_success_no_single_program_explains_is_refused_by_that_program_and_changes_nothing(self):
        bridge = StubBridge()
        even, _ = _demonstrate(bridge, "one-or-two", seed=0)
        odd, _ = _demonstrate(bridge, "one-or-two", seed=1)
        self.assertNotEqual(len(even), len(odd))                         # another shape
        skill = vs.VersionSpaceSkill()
        self.assertTrue(skill.add_success(even))
        held = skill.describe()
        self.assertFalse(skill.add_success(odd))
        self.assertEqual(skill.describe()["steps"], held["steps"])
        self.assertEqual(skill.examples, 1)
        # same shape, same-looking page, a different element rewarded: also not one program
        first, _ = _demonstrate(bridge, "hidden-answer", seed=0)
        second, _ = _demonstrate(bridge, "hidden-answer", seed=1)
        self.assertEqual(len(first), len(second))
        clash = vs.VersionSpaceSkill()
        self.assertTrue(clash.add_success(first))
        self.assertFalse(clash.add_success(second))
        self.assertGreater(clash.describe()["steps"][0]["descriptions_left"], 0)

    def test_a_second_way_of_asking_becomes_a_second_program_and_both_are_then_solved(self):
        bridge = StubBridge()
        seeds = iter(range(0, 200))
        loud = next(s for s in seeds if "upper" in _TASKS["shout-or-whisper"](s).utterance)
        quiet = next(s for s in range(0, 200) if "lower" in _TASKS["shout-or-whisper"](s).utterance)
        skills = vs.SkillSet()
        self.assertEqual(skills.add_success(_demonstrate(bridge, "shout-or-whisper", seed=loud)[0]), "new_way")
        self.assertEqual(skills.add_success(_demonstrate(bridge, "shout-or-whisper", seed=quiet)[0]), "new_way")
        self.assertEqual(len(skills.skills), 2)
        scored = tool.score_arm(bridge, "shout-or-whisper", vs.VersionSpaceArm(skills, {}), TEST_SEEDS)
        self.assertEqual(scored["successes"], len(TEST_SEEDS))
        # a third success in a way already known refines that program instead of adding one
        again = next(s for s in range(quiet + 1, 200) if "lower" in _TASKS["shout-or-whisper"](s).utterance)
        self.assertEqual(skills.add_success(_demonstrate(bridge, "shout-or-whisper", seed=again)[0]), "refined")
        self.assertEqual(len(skills.skills), 2)

    def test_practice_from_one_way_of_asking_reaches_the_other(self):
        bridge = StubBridge()
        trace, _ = _demonstrate(bridge, "shout-or-whisper", seed=0)
        practice = list(range(500, 506))
        ways = {("upper" in _TASKS["shout-or-whisper"](s).utterance) for s in practice + [0]}
        self.assertEqual(ways, {True, False})                            # the practice set holds both ways
        arm = vs.build_arm(bridge=bridge, task="shout-or-whisper", trace=trace, practice_seeds=practice,
                           action_budget=300, tier=0, tool=tool)
        self.assertEqual(arm.learning["skills"]["programs"], 2)
        self.assertEqual(arm.learning["new_ways"], 1)
        self.assertGreaterEqual(arm.learning["found_by_search"], 1)       # the other way had to be found
        self.assertGreater(arm.learning["search_actions"], 0)            # and finding it was paid for
        self.assertEqual(tool.score_arm(bridge, "shout-or-whisper", arm, TEST_SEEDS)["successes"], len(TEST_SEEDS))

    def test_practice_only_ever_adds_what_the_page_rewarded(self):
        bridge = StubBridge()
        trace, _ = _demonstrate(bridge, "hidden-answer", seed=0)
        practice = [501, 502, 503, 504, 505, 506]
        arm = vs.build_arm(bridge=bridge, task="hidden-answer", trace=trace, practice_seeds=practice,
                           action_budget=200, tier=0, tool=tool)
        log = arm.learning
        # every practice instance ends in exactly one of three ways
        self.assertEqual(log["own_success"] + log["found_by_search"] + log["no_success"], len(practice))
        # the page definition says which instances the held answer is right on; a try that the
        # page did not reward is never kept, so the examples are the rewarded traces and no more
        self.assertEqual(log["own_success"], sum(1 for s in practice if s % 3 == 0))
        self.assertEqual(arm.skills.examples, 1 + log["own_success"] + log["found_by_search"])
        # The page looks identical every time, so nothing can tell the three answers apart:
        # they become three programs with the same instruction, the one with most successes
        # behind it acts, and the result is exactly the base rate of that answer.
        self.assertEqual(log["skills"]["programs"], 3)
        scored = tool.score_arm(bridge, "hidden-answer", arm, TEST_SEEDS)
        self.assertEqual(scored["successes"], sum(1 for s in TEST_SEEDS if s % 3 == 0))


class InstrumentTests(unittest.TestCase):
    def test_success_means_the_page_ended_the_episode_with_a_positive_reward(self):
        self.assertTrue(tool.succeeded({"done": True, "raw_reward": 1}))
        self.assertFalse(tool.succeeded({"done": True, "raw_reward": -1}))
        self.assertFalse(tool.succeeded({"done": True, "raw_reward": 0}))
        self.assertFalse(tool.succeeded({"done": False, "raw_reward": 1}))
        self.assertTrue(tool.failed({"done": True, "raw_reward": 0}))

    def test_the_clock_is_not_part_of_where_you_are(self):
        observation = _TASKS["named-button"](2).observe()
        later = dict(observation, virtual_ms=9000, js_errors=["x"])
        self.assertEqual(tool.state_key(observation), tool.state_key(later))
        moved = dict(observation, utterance=observation["utterance"] + " ")
        self.assertNotEqual(tool.state_key(observation), tool.state_key(moved))

    def test_one_try_per_unseen_instance_and_none_of_them_is_the_demonstration(self):
        bridge = StubBridge()
        trace, _ = _demonstrate(bridge, "named-button")
        bridge.resets.clear()
        scored = tool.score_arm(bridge, "named-button", tool.VerbatimArm(trace), TEST_SEEDS)
        self.assertEqual(bridge.resets, TEST_SEEDS)
        self.assertEqual(scored["episodes"], len(TEST_SEEDS))
        self.assertEqual(len(scored["per_seed"]), len(TEST_SEEDS))
        self.assertNotIn(tool.DEMO_SEED, TEST_SEEDS)

    def test_the_score_is_the_page_definition_not_the_arm_opinion(self):
        bridge = StubBridge()
        trace, _ = _demonstrate(bridge, "named-button")
        scored = tool.score_arm(bridge, "named-button", tool.VerbatimArm(trace), TEST_SEEDS)
        position = tool.parse_action(trace[0][1])["index"] - 2
        expected = 0
        for seed in TEST_SEEDS:
            page = _TASKS["named-button"](seed)
            target = page.utterance.split('"')[1]
            if position < len(page.rows) and page.rows[position]["tag"] == "button" and page.rows[position]["text"] == target:
                expected += 1
        self.assertEqual(scored["successes"], expected)

    def test_a_success_that_does_not_happen_again_on_a_fresh_page_is_not_a_demonstration(self):
        bridge = StubBridge(forgetful={"named-button"})
        row = tool.measure_task(bridge, "named-button", test_seeds=TEST_SEEDS[:5], action_budget=300,
                                arm_names=["verbatim"])
        self.assertEqual(row["stage"], tool.STAGE_NOT_REPRODUCED)
        self.assertNotIn("arms", row)

    def test_state_the_observation_does_not_show_makes_the_map_wrong_and_the_walked_route_is_used(self):
        bridge = StubBridge()
        bridge.load("hidden-latch")
        acquired = tool.acquire_first_success(bridge, 0, action_budget=300)
        self.assertTrue(acquired["found"])
        self.assertEqual(len(acquired["plan"]), 1)            # the map says one click is enough ...
        self.assertFalse(tool.replay_on_fresh_page(bridge, "hidden-latch", 0, acquired["plan"])["reproduced"])
        self.assertEqual(len(acquired["plan_walked"]), 2)     # ... what was actually done was two
        shown = tool.demonstrate(bridge, "hidden-latch", 0, action_budget=300)
        self.assertEqual(shown["stage"], tool.STAGE_DEMONSTRATED)
        self.assertEqual(shown["acquisition"]["route_used"], "as_walked")
        self.assertEqual([a for _, a in shown["trace"]], acquired["plan_walked"])

    def test_a_page_that_changes_under_the_same_seed_is_left_out_before_anything_is_measured(self):
        bridge = StubBridge(drifting={"named-button"})
        row = tool.measure_task(bridge, "named-button", test_seeds=TEST_SEEDS[:5], action_budget=300,
                                arm_names=["verbatim"])
        self.assertEqual(row["stage"], tool.STAGE_NOT_REPEATABLE)

    def test_no_success_within_the_budget_is_reported_as_that(self):
        bridge = StubBridge()
        row = tool.measure_task(bridge, "unsolvable", test_seeds=TEST_SEEDS[:5], action_budget=100,
                                arm_names=["verbatim"])
        self.assertEqual(row["stage"], tool.STAGE_NO_SUCCESS)
        self.assertFalse(row["acquisition"]["found"])

    def test_the_random_arm_is_the_same_run_twice_and_is_not_good(self):
        bridge = StubBridge()
        trace, acquired = _demonstrate(bridge, "named-button")
        a = tool.score_arm(bridge, "named-button", tool.RandomArm(trace, tier=0, salt="t"), TEST_SEEDS)
        b = tool.score_arm(bridge, "named-button", tool.RandomArm(trace, tier=0, salt="t"), TEST_SEEDS)
        self.assertEqual(a["per_seed"], b["per_seed"])
        self.assertLess(a["successes"], len(TEST_SEEDS) // 2)
        # what it does on an instance depends on that instance, not on what came before it
        backwards = tool.score_arm(bridge, "named-button", tool.RandomArm(trace, tier=0, salt="t"),
                                   list(reversed(TEST_SEEDS)))
        self.assertEqual(backwards["per_seed"][::-1], a["per_seed"])
        self.assertIn("1", a["per_seed"])            # otherwise the line above would prove nothing

    def test_scored_instances_are_never_the_demonstration_or_the_practice_instances(self):
        for scored, practised in ((1, 0), (20, 3), (50, 10), (200, 400)):
            test_seeds, practice = tool.seed_plan(scored, practised)
            self.assertEqual((len(test_seeds), len(practice)), (scored, practised))
            self.assertNotIn(tool.DEMO_SEED, test_seeds)
            self.assertNotIn(tool.DEMO_SEED, practice)
            self.assertFalse(set(test_seeds) & set(practice))
        with self.assertRaises(ValueError):
            tool.seed_plan(20, tool.FIRST_TEST_SEED - tool.FIRST_PRACTICE_SEED + 1)   # practice would run into the scored ones

    def test_replaying_positions_solves_a_page_that_never_changes_and_only_that(self):
        bridge = StubBridge()
        same, _ = _demonstrate(bridge, "always-the-same")
        self.assertEqual(tool.score_arm(bridge, "always-the-same", tool.VerbatimArm(same), TEST_SEEDS)["successes"],
                         len(TEST_SEEDS))
        typed, _ = _demonstrate(bridge, "type-and-submit")
        self.assertEqual(tool.score_arm(bridge, "type-and-submit", tool.VerbatimArm(typed), TEST_SEEDS)["successes"], 0)


class InstructionBlindControlTests(unittest.TestCase):
    """The control arm: the same skill, shown the demonstration's instruction on every instance."""

    def _arms(self, task):
        bridge = StubBridge()
        trace, _ = _demonstrate(bridge, task)
        skills = vs.SkillSet()
        skills.add_success(trace)
        sighted = vs.VersionSpaceArm(skills, {})
        blind = tool.InstructionBlindArm(vs.VersionSpaceArm(skills, {}), trace[0][0]["utterance"])
        return bridge, trace, sighted, blind

    def test_a_skill_that_types_what_the_instruction_says_types_the_old_word_when_denied_it(self):
        bridge, trace, sighted, blind = self._arms("type-and-submit")
        self.assertEqual(tool.score_arm(bridge, "type-and-submit", sighted, TEST_SEEDS)["successes"], len(TEST_SEEDS))
        old_word = trace[0][0]["utterance"].split('"')[1]
        same_word = sum(1 for s in TEST_SEEDS if _TASKS["type-and-submit"](s).utterance.split('"')[1] == old_word)
        self.assertEqual(tool.score_arm(bridge, "type-and-submit", blind, TEST_SEEDS)["successes"], same_word)
        self.assertLess(same_word, len(TEST_SEEDS) // 2)

    def test_a_skill_that_finds_the_named_button_mostly_misses_when_denied_the_name(self):
        bridge, trace, sighted, blind = self._arms("named-button")
        old_name = trace[0][0]["utterance"].split('"')[1]
        same_name = sum(1 for s in TEST_SEEDS if _TASKS["named-button"](s).utterance.split('"')[1] == old_name)
        got = tool.score_arm(bridge, "named-button", blind, TEST_SEEDS)["successes"]
        self.assertGreaterEqual(got, same_name)          # where the old name is still the right one it cannot miss
        self.assertLess(got, 0.9 * len(TEST_SEEDS))     # everywhere else it is guessing

    def test_a_skill_that_never_needed_the_instruction_does_not_notice(self):
        for task in ("numbered-section", "shifting-section", "chatty-section"):
            bridge, trace, sighted, blind = self._arms(task)
            self.assertEqual(tool.score_arm(bridge, task, blind, TEST_SEEDS)["successes"], len(TEST_SEEDS), task)

    def test_the_page_itself_is_never_altered_for_the_control(self):
        bridge, trace, sighted, blind = self._arms("named-button")
        observation = _TASKS["named-button"](1234).observe()
        before = dict(observation)
        blind.begin(observation, 1234)
        blind.next_action(observation)
        self.assertEqual(observation, before)


class ExistingCompilerArmTests(unittest.TestCase):
    """The repository's own generaliser, driven through the adapter, on pages with known answers."""

    def test_a_quoted_literal_shared_with_the_instruction_becomes_a_parameter(self):
        bridge = StubBridge()
        trace, _ = _demonstrate(bridge, "type-and-submit")
        arm = tool.ExistingCompilerArm(trace)
        self.assertEqual(arm.parameters, ["?str0"])
        scored = tool.score_arm(bridge, "type-and-submit", arm, TEST_SEEDS)
        self.assertEqual(scored["successes"], len(TEST_SEEDS))
        self.assertEqual(scored["refused"], 0)

    def test_page_content_it_cannot_tie_to_the_instruction_stays_a_constant_and_then_misses(self):
        bridge = StubBridge()
        trace, _ = _demonstrate(bridge, "numbered-section")
        arm = tool.ExistingCompilerArm(trace)
        self.assertEqual(arm.parameters, [])
        scored = tool.score_arm(bridge, "numbered-section", arm, TEST_SEEDS)
        title = trace[0][0]["elements"][2]["text"]
        same_title = sum(1 for s in TEST_SEEDS if _TASKS["numbered-section"](s).rows[0]["text"] == title)
        self.assertEqual(scored["successes"], same_title)
        self.assertEqual(scored["refused"], 0)

    def test_an_instruction_it_cannot_parse_is_refused_rather_than_guessed(self):
        bridge = StubBridge()
        trace, _ = _demonstrate(bridge, "nth-box")
        arm = tool.ExistingCompilerArm(trace)
        scored = tool.score_arm(bridge, "nth-box", arm, TEST_SEEDS)
        same_instruction = sum(1 for s in TEST_SEEDS
                               if _TASKS["nth-box"](s).utterance == trace[0][0]["utterance"])
        self.assertEqual(scored["refused"], len(TEST_SEEDS) - same_instruction)
        self.assertLessEqual(scored["successes"], same_instruction)


class WholeRunTests(unittest.TestCase):
    def _rows(self, arm_names, tasks):
        bridge = StubBridge()
        return [tool.measure_task(bridge, t, test_seeds=TEST_SEEDS[:10], action_budget=300, arm_names=arm_names,
                                  practice=[500, 501]) for t in tasks]

    def test_tasks_without_a_demonstration_stay_in_the_denominator(self):
        arms = ["random", "verbatim", "existing_compiler", "version_space", "version_space_practice"]
        rows = self._rows(arms, ["named-button", "type-and-submit", "unsolvable", "always-the-same"])
        summary = tool.summarise(rows, arms)["all"]
        self.assertEqual(summary["tasks"], 4)
        self.assertEqual(summary["demonstrated"], 3)
        self.assertEqual(summary["stages"][tool.STAGE_NO_SUCCESS], 1)
        learned = summary["arms"]["version_space"]
        self.assertEqual(learned["tasks_at_100_percent"], 3)
        self.assertEqual(learned["share_of_all_tasks_at_or_above_90_percent"], 0.75)
        self.assertEqual(summary["arms"]["verbatim"]["tasks_at_100_percent"], 1)
        # the page that never changes is solved by replay and is set aside when asking who generalised
        self.assertEqual(summary["tasks_a_fixed_replay_already_solves"], 1)
        self.assertEqual(summary["tasks_that_need_generalisation"], 2)
        self.assertEqual(learned["tasks_at_or_above_90_percent_where_replay_is_not_enough"], 2)
        self.assertEqual(summary["arms"]["verbatim"]["tasks_at_or_above_90_percent_where_replay_is_not_enough"], 0)
        # both remaining tasks quote, in the instruction, the very literal a step uses: the one
        # case the existing compiler turns into a parameter
        self.assertEqual(summary["arms"]["existing_compiler"]["tasks_at_or_above_90_percent_where_replay_is_not_enough"], 2)
        self.assertEqual(summary["arms"]["random"]["tasks_at_or_above_90_percent_where_replay_is_not_enough"], 0)

    def test_the_summary_says_which_one_success_skills_rest_on_reading_the_instruction(self):
        arms = ["verbatim", "version_space", "version_space_blind"]
        tasks = ["named-button", "type-and-submit", "numbered-section", "shifting-section", "chatty-section",
                 "always-the-same", "unsolvable"]
        rows = self._rows(arms, tasks)
        by_task = {r["task"]: r for r in rows}
        self.assertEqual(by_task["shifting-section"]["distinct_test_instructions"], 1)
        self.assertGreater(by_task["chatty-section"]["distinct_test_instructions"], 1)
        summary = tool.summarise(rows, arms)["all"]
        # replay is enough where nothing moves (always-the-same, numbered-section); nothing solves unsolvable
        self.assertEqual(summary["tasks_a_fixed_replay_already_solves"], 2)
        block = summary["one_success_skills_where_replay_is_not_enough"]
        self.assertEqual(block["tasks_at_or_above_90_percent"], 4)
        self.assertEqual(block["of_which_fail_when_denied_the_instruction"], 2)           # the two that read it
        self.assertEqual(block["of_which_still_succeed_when_denied_the_instruction"], 2)  # the two moving sections
        # only one of those has an instruction that changes: that is the one a reader should look at twice
        self.assertEqual(block["of_which_still_succeed_although_the_instruction_changes"], 1)
        self.assertEqual(block["tasks_that_succeed_without_an_instruction_that_changes"], ["chatty-section"])

    def test_a_page_that_breaks_while_an_arm_runs_keeps_what_was_already_measured(self):
        whole = tool.measure_task(StubBridge(), "named-button", test_seeds=TEST_SEEDS[:10], action_budget=300,
                                  arm_names=["verbatim", "version_space"])
        counter = StubBridge()
        tool.measure_task(counter, "named-button", test_seeds=TEST_SEEDS[:10], action_budget=300,
                          arm_names=["verbatim"])
        broken = StubBridge(loads_allowed=counter.loads)        # enough loads for everything up to the first arm
        row = tool.measure_task(broken, "named-button", test_seeds=TEST_SEEDS[:10], action_budget=300,
                                arm_names=["verbatim", "version_space"])
        self.assertEqual(row["stage"], tool.STAGE_DEMONSTRATED)
        self.assertTrue(row["arms_incomplete"])
        self.assertEqual(list(row["arms"]), ["verbatim"])
        self.assertEqual(row["arms"]["verbatim"]["per_seed"], whole["arms"]["verbatim"]["per_seed"])
        summary = tool.summarise([row], ["verbatim", "version_space"])["all"]
        self.assertEqual(summary["arms"]["verbatim"]["tasks_scored"], 1)
        self.assertEqual(summary["arms"]["version_space"]["tasks_scored"], 0)

    def test_a_result_names_the_bytes_it_came_from(self):
        hashes = tool.code_sha256()
        self.assertEqual(set(hashes), {"tool", "bridge", "bridge_chromium", "version_space_learner", "explorer",
                                       "existing_compiler"})
        for name, value in hashes.items():
            self.assertRegex(value, r"^[0-9a-f]{64}$", name)
        self.assertEqual(len(set(hashes.values())), len(hashes))

    def test_the_split_is_a_fixed_function_of_the_task_name(self):
        self.assertEqual(tool.split_of("click-button"), tool.split_of("click-button"))
        names = [f"task-{i}" for i in range(400)]
        development = sum(1 for n in names if tool.split_of(n) == "development")
        self.assertTrue(60 < development < 140)          # about a quarter

    def test_a_digest_keeps_the_counts_and_refuses_a_foreign_file(self):
        arms = ["verbatim", "version_space"]
        rows = self._rows(arms, ["named-button", "unsolvable"])
        result = {"schema": tool.SCHEMA, "authority": tool.AUTHORITY, "generated_utc": "t", "environment": {},
                  "parameters": {}, "tasks": rows, "summary": tool.summarise(rows, arms)}
        digest = tool.digest(result)
        self.assertEqual(digest["schema"], tool.DIGEST_SCHEMA)
        by_task = {t["task"]: t for t in digest["tasks"]}
        self.assertEqual(by_task["named-button"]["arms"]["version_space"]["successes"], 10)
        self.assertEqual(by_task["unsolvable"]["stage"], tool.STAGE_NO_SUCCESS)
        self.assertEqual(digest["producer_cognition_model_dependency_count"], 0)
        with self.assertRaises(ValueError):
            tool.digest({"schema": "SOMETHING_ELSE"})


class ReplayIsDoneStepByStepTests(unittest.TestCase):
    def test_a_plan_that_names_an_element_that_is_not_there_is_not_a_success(self):
        # two-button page: "Go" alone succeeds. A plan with a step on a 99th element would also end
        # in success on a page that ignores what it cannot do -- and would record an impossible action.
        bridge = StubBridge()
        honest = tool.replay_on_fresh_page(bridge, "named-decoy", 0, ["click@3"])
        self.assertTrue(honest["reproduced"])
        bridge = StubBridge()
        padded = tool.replay_on_fresh_page(bridge, "named-decoy", 0, ["click@99", "click@3"])
        self.assertFalse(padded["reproduced"])
        self.assertEqual(padded["reason"], "PLAN_NAMES_AN_ELEMENT_THAT_IS_NOT_ON_THE_PAGE")
        self.assertEqual(bridge.acts, 0)
        self.assertEqual(padded["trace"], [])

    def test_a_plan_that_acts_on_something_that_cannot_take_the_action_is_not_a_success(self):
        bridge = StubBridge()
        typed = tool.replay_on_fresh_page(bridge, "named-decoy", 0, ["type@3=x", "click@3"])     # a button takes no text
        self.assertFalse(typed["reproduced"])
        self.assertEqual(typed["reason"], "PLAN_ACTS_ON_AN_ELEMENT_THAT_CANNOT_TAKE_THE_ACTION")
        self.assertEqual(bridge.acts, 0)
        pressed = tool.replay_on_fresh_page(StubBridge(), "named-decoy", 0, ["click@0", "click@3"])   # the page body
        self.assertFalse(pressed["reproduced"])

    def test_every_step_of_a_demonstration_is_on_the_page_it_was_recorded_with(self):
        for task in sorted(_TASKS):
            for search in tool.SEARCHES:
                shown = tool.demonstrate(StubBridge(), task, 0, action_budget=3000, search=search)
                for observation, action in shown["trace"] or []:
                    wanted = tool.parse_action(action)
                    element = observation["elements"][wanted["index"]]
                    self.assertTrue(element.get("can_click" if wanted["type"] == "click" else "can_type"), (task, action))


class OneTaskCannotSinkTheRunTests(unittest.TestCase):
    class Breaks(StubBridge):
        """A page that throws something nobody planned for, from its n-th action on."""

        def __init__(self, at):
            super().__init__()
            self._at = at

        def act(self, action):
            if self.acts >= self._at:
                raise RuntimeError("something nobody planned for")
            return super().act(action)

    def test_an_unexpected_error_is_recorded_against_the_task_and_what_was_measured_is_kept(self):
        arms = ["verbatim", "version_space"]
        whole = StubBridge()
        clean = tool.measure_task(whole, "named-button", test_seeds=TEST_SEEDS[:10], action_budget=300, arm_names=arms)
        early = tool.measure_task(self.Breaks(0), "named-button", test_seeds=TEST_SEEDS[:10], action_budget=300,
                                  arm_names=arms)
        self.assertEqual(early["stage"], tool.STAGE_NOT_RUNNING)
        self.assertEqual(early["reason"], "TOOL_OR_LEARNER_ERROR")
        self.assertEqual(early["error_type"], "RuntimeError")
        self.assertNotIn("arms", early)
        late = tool.measure_task(self.Breaks(whole.acts - 5), "named-button", test_seeds=TEST_SEEDS[:10],
                                 action_budget=300, arm_names=arms)
        self.assertEqual(late["stage"], tool.STAGE_DEMONSTRATED)
        self.assertTrue(late["arms_incomplete"])
        self.assertEqual(late["reason"], "TOOL_OR_LEARNER_ERROR")
        self.assertEqual(late["arms"]["verbatim"]["per_seed"], clean["arms"]["verbatim"]["per_seed"])
        self.assertNotIn("version_space", late["arms"])
        summary = tool.summarise([early, late], arms)["all"]
        self.assertEqual(summary["tasks"], 2)                                  # both stay in the denominator
        self.assertEqual(summary["arms"]["version_space"]["tasks_scored"], 0)

    def test_an_arm_nobody_defined_is_refused_before_anything_is_measured(self):
        bridge = StubBridge()
        with self.assertRaises(ValueError):
            tool.measure_task(bridge, "named-button", test_seeds=TEST_SEEDS[:5], action_budget=300,
                              arm_names=["verbatim", "telepathy"])
        self.assertEqual(bridge.loads, 0)


class KeptSkillTests(unittest.TestCase):
    def test_a_kept_skill_does_on_unseen_pages_exactly_what_the_scored_one_did(self):
        folder = tempfile.mkdtemp()
        try:
            arms = ["verbatim", "version_space", "version_space_practice"]
            rows = {}
            for task in ("named-button", "shout-or-whisper", "unsolvable"):
                rows[task] = tool.measure_task(StubBridge(), task, test_seeds=TEST_SEEDS[:10], action_budget=600,
                                               arm_names=arms, practice=[500, 501, 502, 503], skills_dir=folder)
            kept = tool.kept_skills(folder)
            self.assertEqual(set(kept), {"version_space", "version_space_practice"})       # only arms that learn
            self.assertEqual(set(kept["version_space"]), {"named-button", "shout-or-whisper"})   # nothing for no success
            for arm_name in kept:
                for task, skills in kept[arm_name].items():
                    again = tool.score_arm(StubBridge(), task, vs.VersionSpaceArm(skills, {}), TEST_SEEDS[:10])
                    self.assertEqual(again["per_seed"], rows[task]["arms"][arm_name]["per_seed"], (task, arm_name))
            # practice changed what is held for the task with two ways of doing it, and only there
            self.assertGreater(len(kept["version_space_practice"]["shout-or-whisper"].skills),
                               len(kept["version_space"]["shout-or-whisper"].skills))
        finally:
            shutil.rmtree(folder)

    def test_nothing_is_written_unless_asked(self):
        folder = tempfile.mkdtemp()
        try:
            tool.measure_task(StubBridge(), "named-button", test_seeds=TEST_SEEDS[:5], action_budget=300,
                              arm_names=["version_space"])
            self.assertEqual(os.listdir(folder), [])
            self.assertEqual(tool.kept_skills(folder), {})
        finally:
            shutil.rmtree(folder)


class OneMemoryTests(unittest.TestCase):
    """One agent holding everything learned, given pages and never the name of a task."""
    TASKS = ["named-button", "type-and-submit", "shout-and-submit", "numbered-section", "shifting-section",
             "chatty-section", "mail-rows", "widget-kind", "two-fields", "three-boxes", "nth-box", "always-the-same",
             "one-or-two", "shout-or-whisper", "hidden-answer"]
    SEEDS = TEST_SEEDS[:10]

    @classmethod
    def setUpClass(cls):
        cls.kept, cls.told = {}, {}
        for task in cls.TASKS:
            bridge = StubBridge()
            shown = tool.demonstrate(bridge, task, 0, action_budget=3000, search="guided")
            arm = tool.build_version_space_arm(bridge, task, shown["trace"], practice=[500, 501, 502],
                                               action_budget=3000, tier=2, search="guided")
            cls.kept[task] = arm.skills
            cls.told[task] = tool.score_arm(StubBridge(), task, arm, cls.SEEDS)
        cls.library = tool.library_of(cls.kept)
        cls.rows = {r["task"]: r for r in tool.measure_library(
            StubBridge(), cls.TASKS + ["hidden-latch", "unsolvable", "no-such-page"], cls.library, test_seeds=cls.SEEDS)}

    def test_not_being_told_the_task_costs_nothing_on_any_task_that_was_learned(self):
        for task in self.TASKS:
            self.assertEqual(self.rows[task]["all_skills"]["per_seed"], self.told[task]["per_seed"], task)
        # and it mostly knows where it learned what it is using
        own = sum(1 for task in self.TASKS if next(iter(self.rows[task]["all_skills"]["chosen_from"])) == task)
        self.assertGreaterEqual(own, len(self.TASKS) - 2)

    def test_a_program_whose_slot_swallows_its_whole_instruction_does_not_answer_for_every_page(self):
        # "Go." was learned as "<the button's name>.": no fixed word is left, so nothing can ever differ
        swallow = self.kept["one-or-two"].skills[0]
        page = _TASKS["three-boxes"](1003).observe()
        self.assertEqual(vs.mismatch(swallow, page["utterance"]), 0)             # distance alone says: a perfect fit
        self.assertEqual(vs.evidence(swallow, page["utterance"]), (0, 0))        # evidence says: nothing either way
        # (the names in the list are read off the page: a program that presses every box named reads them as values)
        supports, against = max((vs.evidence(skill, page["utterance"], vs.Page(page))
                                 for skill in self.kept["three-boxes"].skills),
                                key=lambda pair: pair[0] - pair[1])
        self.assertGreater(supports - against, 0)
        origin, _ = self.library.choose(page)
        self.assertEqual(origin, "three-boxes")
        self.assertEqual(self.rows["three-boxes"]["all_skills"]["chosen_from"], {"three-boxes": len(self.SEEDS)})

    def test_nothing_stands_against_an_instruction_a_program_was_learned_from(self):
        # a program learned from several sentences is judged by the one that fits best, not the one that fits worst
        program = max(self.kept["chatty-section"].skills, key=lambda skill: len(set(skill.instructions())))
        known = sorted(set(program.instructions()))
        self.assertGreater(len(known), 1)
        for instruction in known:
            supports, against = vs.evidence(program, instruction)
            self.assertEqual(against, 0, instruction)
            self.assertGreater(supports, 0, instruction)

    def test_first_sight_of_a_task_is_done_with_what_a_twin_taught_and_the_twin_is_named(self):
        for task, twin in (("numbered-section", "shifting-section"), ("shifting-section", "numbered-section"),
                           ("hidden-latch", "numbered-section")):
            row = self.rows[task]["without_this_task"]
            self.assertEqual(row["successes"], len(self.SEEDS), task)
            self.assertEqual(row["chosen_from"], {twin: len(self.SEEDS)}, task)
        self.assertFalse(self.rows["hidden-latch"]["has_own_skill"])
        summary = tool.summarise_library(list(self.rows.values()))
        block = summary["without_this_task"]
        self.assertEqual(block["done_with_a_skill_learned_on"]["hidden-latch"], "numbered-section")
        self.assertEqual(block["of_which_had_no_skill_of_their_own"], ["hidden-latch"])

    def test_first_sight_without_anything_like_it_is_not_pretended(self):
        for task in ("mail-rows", "two-fields", "always-the-same"):
            row = self.rows[task]["without_this_task"]
            self.assertEqual(row["successes"], 0, task)
            self.assertNotIn(task, row["chosen_from"])
        self.assertEqual(self.rows["unsolvable"]["all_skills"]["successes"], 0)

    def test_what_is_left_out_is_really_left_out(self):
        page = _TASKS["mail-rows"](1001).observe()
        self.assertEqual(self.library.choose(page)[0], "mail-rows")
        origins = [origin for _, origin, _ in self.library.ranked(page["utterance"], without=("mail-rows",))]
        self.assertNotIn("mail-rows", origins)
        self.assertEqual(len(origins), len(self.library.entries) - len(self.kept["mail-rows"].skills))

    def test_a_better_supported_program_that_cannot_begin_on_the_page_is_passed_over(self):
        page = _TASKS["named-button"](1002).observe()
        page["utterance"] = 'Click on the "Zzyzx" button.'                        # reads like the task; names nothing here
        ranked = self.library.ranked(page["utterance"])
        first_origin, first = ranked[0][1], ranked[0][2]
        self.assertEqual(first_origin, "named-button")
        self.assertIsNone(first.act(0, page))
        origin, skill = self.library.choose(page)
        self.assertIsNotNone(skill)
        self.assertNotEqual(origin, "named-button")
        self.assertIsNotNone(skill.act(0, page))
        self.assertEqual(self.library.choose(page, look=1), (None, None))        # told to look no further: it does nothing
        arm = vs.LibraryArm(self.library)
        arm.library = vs.SkillLibrary()                                           # an empty memory refuses, and says so
        arm.begin(page, 0)
        self.assertIsNone(arm.next_action(page))
        self.assertTrue(arm.refused)
        self.assertEqual(arm.chosen_from, {"NOTHING_HELD_BEGINS_HERE": 1})

    def test_tasks_that_did_not_run_stay_in_the_count(self):
        self.assertEqual(self.rows["no-such-page"]["stage"], tool.STAGE_NOT_RUNNING)
        self.assertNotIn("all_skills", self.rows["no-such-page"])
        summary = tool.summarise_library(list(self.rows.values()))
        self.assertEqual(summary["tasks"], len(self.TASKS) + 3)
        self.assertEqual(summary["tasks_with_a_skill_of_their_own"], len(self.TASKS))
        self.assertEqual(summary["all_skills"]["tasks_scored"], len(self.TASKS) + 2)
        done = summary["all_skills"]["tasks_at_or_above_90_percent"]
        self.assertEqual(done, sum(1 for r in self.rows.values() if "all_skills" in r and r["all_skills"]["successes"] >= 9))
        self.assertEqual(summary["all_skills"]["share_of_all_tasks_at_or_above_90_percent"],
                         round(done / (len(self.TASKS) + 3), 4))

    def test_one_place_is_held_once(self):
        with self.assertRaises(ValueError):
            self.library.add("mail-rows", self.kept["mail-rows"])

    def test_library_results_join_only_when_they_are_one_run(self):
        def result(tasks, seeds=3):
            rows = tool.measure_library(StubBridge(), tasks, self.library, test_seeds=self.SEEDS[:seeds])
            return {"schema": tool.LIBRARY_SCHEMA, "authority": tool.AUTHORITY, "environment": {"pages": "x"},
                    "parameters": {"test_seeds": self.SEEDS[:seeds]}, "tasks": rows,
                    "summary": tool.summarise_library(rows)}
        whole = result(["mail-rows", "nth-box", "two-fields"])
        joined = tool.merge_library([result(["two-fields"]), result(["nth-box", "mail-rows"])])
        self.assertEqual(joined["summary"], whole["summary"])
        self.assertEqual([r["task"] for r in joined["tasks"]], ["mail-rows", "nth-box", "two-fields"])
        with self.assertRaises(ValueError):
            tool.merge_library([result(["two-fields"]), result(["nth-box"], seeds=2)])
        with self.assertRaises(ValueError):
            tool.merge_library([result(["two-fields"]), result(["two-fields"])])
        with self.assertRaises(ValueError):
            tool.merge_library([result(["two-fields"]), {"schema": "SOMETHING_ELSE", "tasks": []}])


class MergeTests(unittest.TestCase):
    ARMS = ["verbatim", "version_space"]

    def _result(self, tasks, *, tree="aa", budget=300):
        bridge = StubBridge()
        rows = [tool.measure_task(bridge, t, test_seeds=TEST_SEEDS[:10], action_budget=budget, arm_names=self.ARMS)
                for t in tasks]
        return {"schema": tool.SCHEMA, "authority": tool.AUTHORITY, "generated_utc": "t",
                "environment": {"html_tree_sha256": tree}, "parameters": {"arms": self.ARMS, "budget": budget},
                "tasks": rows, "summary": tool.summarise(rows, self.ARMS)}

    def test_two_runs_over_different_tasks_join_into_what_one_run_would_have_said(self):
        whole = self._result(["named-button", "type-and-submit", "unsolvable", "always-the-same"])
        joined = tool.merge([self._result(["unsolvable", "named-button"]),
                             self._result(["always-the-same", "type-and-submit"])])
        strip = lambda rows: [{k: v for k, v in r.items() if k != "seconds"} for r in rows]
        self.assertEqual(strip(joined["tasks"]), strip(sorted(whole["tasks"], key=lambda r: r["task"])))
        self.assertEqual(joined["summary"], whole["summary"])
        self.assertEqual(joined["summary"]["all"]["tasks"], 4)

    def test_runs_that_must_not_be_added_up_are_not(self):
        base = self._result(["named-button"])
        with self.assertRaises(ValueError):
            tool.merge([base, self._result(["type-and-submit"], tree="bb")])       # other pages
        with self.assertRaises(ValueError):
            tool.merge([base, self._result(["type-and-submit"], budget=100)])      # other parameters
        with self.assertRaises(ValueError):
            tool.merge([base, self._result(["named-button"])])                     # the same task twice
        with self.assertRaises(ValueError):
            tool.merge([base, {"schema": "SOMETHING_ELSE"}])
        with self.assertRaises(ValueError):
            tool.merge([])


class FullRewardTests(unittest.TestCase):
    """A page that pays part of the reward for part of the task has not been told the task was done."""

    def _ended(self, reward):
        return {"done": True, "raw_reward": reward, "elements": []}

    def test_only_the_full_reward_is_a_success(self):
        self.assertTrue(tool.succeeded(self._ended(1)))
        self.assertTrue(tool.succeeded(self._ended(1.0)))
        for reward in (0.999, 0.5, 1 / 3, 0.1, 0, -0.5, -1):
            self.assertFalse(tool.succeeded(self._ended(reward)), reward)
        self.assertFalse(tool.succeeded({"done": False, "raw_reward": 1}))

    def test_part_of_the_reward_is_counted_and_is_a_failure(self):
        self.assertTrue(tool.partly_rewarded(self._ended(1 / 3)))
        self.assertTrue(tool.failed(self._ended(1 / 3)))
        self.assertFalse(tool.partly_rewarded(self._ended(1)))
        self.assertFalse(tool.partly_rewarded(self._ended(-1)))
        self.assertFalse(tool.partly_rewarded({"done": False, "raw_reward": 0.5}))

    class OneBoxThenSubmit:
        """Ticks the first box the instruction names and submits: a third of the task, every time."""

        def begin(self, observation, seed):
            self.wanted = observation["utterance"].split()[1].strip(",")
            self.step = 0

        def next_action(self, observation):
            self.step += 1
            wanted = self.wanted if self.step == 1 else "Submit"
            return "click@%d" % next(e["index"] for e in observation["elements"] if e["text"] == wanted)

    def test_an_arm_that_does_a_third_of_the_task_scores_nothing_and_is_seen_doing_it(self):
        scored = tool.score_arm(StubBridge(), "three-boxes", self.OneBoxThenSubmit(), TEST_SEEDS[:10])
        self.assertEqual(scored["successes"], 0)
        self.assertEqual(scored["partial_credit"], 10)
        self.assertEqual(scored["per_seed"], "0" * 10)

    def test_a_search_does_not_stop_at_part_of_the_reward(self):
        for search in tool.SEARCHES:
            bridge = StubBridge()
            shown = tool.demonstrate(bridge, "three-boxes", 0, action_budget=3000, search=search)
            self.assertEqual(shown["stage"], tool.STAGE_DEMONSTRATED, search)
            page = _TASKS["three-boxes"](0)
            for _, action in shown["trace"]:
                page.act(tool.parse_action(action))
            self.assertEqual(page.reward, 1.0, search)           # the page's definition, not the tool's word

    def test_the_digest_carries_the_partial_count(self):
        scored = tool.score_arm(StubBridge(), "three-boxes", self.OneBoxThenSubmit(), TEST_SEEDS[:10])
        rows = [{"task": "three-boxes", "split": "held_out", "stage": tool.STAGE_DEMONSTRATED, "arms": {"a_third": scored}}]
        result = {"schema": tool.SCHEMA, "authority": tool.AUTHORITY, "generated_utc": "t", "environment": {},
                  "parameters": {}, "tasks": rows, "summary": {}}
        kept = tool.digest(result)["tasks"][0]["arms"]["a_third"]
        self.assertEqual(kept["partial_credit"], 10)
        self.assertEqual(kept["successes"], 0)


class GuidedPriceTests(unittest.TestCase):
    """What the instruction makes cheap. Every expectation is read off the instruction and the page by hand."""

    def _page(self):
        elements = [
            _element(0, -1, "body"),
            _element(1, 0, "label", "Username", click=True, **{"for": "user"}),
            _element(2, 0, "input", type_=True, click=True, id="user", type="text", value=""),
            _element(3, 0, "input", type_=True, click=True, id="note", type="text", value="old"),
            _element(4, 0, "label", "Remember", click=True, **{"for": "keep"}),
            _element(5, 0, "input", click=True, id="keep", type="checkbox", checked=True),
            _element(6, 0, "span", "Alba", click=True),
            _element(7, 0, "span", "", click=True, classes="star"),
            _element(8, 0, "span", "", click=True, classes="email-thread"),
            _element(9, 0, "div", "unrelated", click=True),
            _element(10, 0, "button", "Login", click=True),
            _element(11, 0, "button", "Cancel", click=True),
            _element(12, 0, "input", click=True, type="submit", value="Remember"),
        ]
        return {"utterance": 'Enter "kira" for Alba on 10/20/2017, click the star, tick Remember and press login. Then wait.',
                "done": False, "elements": elements}

    def test_typing(self):
        price, page = tool.GuidedPrices(), self._page()
        self.assertEqual(price(page, "type@2=kira"), (0, 0))            # quoted
        self.assertEqual(price(page, "type@2=10/20/2017"), (0, 0))      # spelled like a value
        self.assertEqual(price(page, "type@2=Alba"), (0, 0))            # a capital inside a sentence
        self.assertEqual(price(page, "type@2=KIRA"), (1, 0))            # a value, in the other letter case
        self.assertEqual(price(page, "type@2=star"), (3, 0))            # prose: dearer than pressing anything
        self.assertEqual(price(page, "type@2=Then"), (3, 0))            # a capital that only starts a sentence
        self.assertEqual(price(page, "type@2=unrelated"), (3, 0))       # found on the page, not in the instruction
        self.assertEqual(price(page, "type@3=kira"), (2, 0))            # the field already holds something
        self.assertEqual(price(page, "type@3=unrelated"), (5, 0))

    def test_a_value_that_already_sits_in_a_field_is_no_longer_free_for_another(self):
        page = self._page()
        page["elements"][3]["value"] = "kira"
        price = tool.GuidedPrices()
        self.assertEqual(price(page, "type@2=kira"), (1, 0))            # field 3 holds it: try the other values first
        self.assertEqual(price(page, "type@2=Alba"), (0, 0))
        self.assertEqual(price(page, "type@3=kira"), (2, 0))            # its own content does not count against it

    def test_one_price_list_serves_many_pages(self):
        price, first, second = tool.GuidedPrices(), self._page(), self._page()
        second["utterance"] = 'Enter "zed" and press Cancel.'
        self.assertEqual(price(first, "type@2=kira"), (0, 0))
        self.assertEqual(price(second, "type@2=kira"), (3, 0))          # not this page's instruction
        self.assertEqual(price(second, "click@11"), (0, 2))
        self.assertEqual(price(first, "click@11"), (1, 2))

    def test_pressing(self):
        price, page = tool.GuidedPrices(), self._page()
        self.assertEqual(price(page, "click@6"), (0, 1))                # its text is a run of the instruction's words
        self.assertEqual(price(page, "click@7"), (0, 1))                # its class is a word of the instruction
        self.assertEqual(price(page, "click@8"), (1, 1))                # `email-thread` is not named; an icon all the same
        self.assertEqual(price(page, "click@9"), (2, 1))                # nothing names it
        self.assertEqual(price(page, "click@10"), (0, 2))               # a named button: free, and last in its state
        self.assertEqual(price(page, "click@11"), (1, 2))               # a button nobody named
        self.assertEqual(price(page, "click@12"), (0, 2))               # a button is named by what it shows
        self.assertEqual(price(page, "click@4"), (1, 1))                # named, but its box is already ticked
        self.assertEqual(price(page, "click@2"), (2, 1))                # pressing a text field only moves the cursor
        self.assertEqual(price(page, "click@1"), (2, 1))                # and so does pressing its label

    def test_pressing_a_text_field_or_its_label_is_never_cheap_however_it_is_named(self):
        elements = [_element(0, -1, "body"),
                    _element(1, 0, "label", "Username", click=True, **{"for": "username"}),
                    _element(2, 0, "input", type_=True, click=True, id="username", type="text", value=""),
                    _element(3, 0, "span", "Username", click=True)]
        page = {"utterance": 'Enter "kira" into the Username field.', "done": False, "elements": elements}
        price = tool.GuidedPrices()
        self.assertEqual(price(page, "click@1"), (2, 1))       # named, and all it does is move the cursor
        self.assertEqual(price(page, "click@2"), (2, 1))
        self.assertEqual(price(page, "click@3"), (0, 1))       # the same word on something that is not a field's label
        self.assertEqual(price(page, "type@2=kira"), (0, 0))

    def test_values_are_recognised_by_spelling_alone(self):
        self.assertEqual(tool.literal_words("Enter 10/20/2017 as the date and hit submit."), ["10/20/2017"])
        self.assertEqual(tool.literal_words("Find the email by Celestyn and forward that email to Theresita."),
                         ["Celestyn", "Theresita"])
        self.assertEqual(tool.literal_words("Select Brazil. Then click Submit! Now."), ["Brazil", "Submit"])
        self.assertEqual(tool.literal_words("press the button"), [])

    def test_a_name_in_the_markup_counts_only_whole(self):
        phrases = tool.instruction_phrases("Find the email and click the star icon.")
        self.assertTrue(tool.named_by_instruction({"index": 0, "tag": "span", "text": "", "classes": "star"}, phrases))
        self.assertTrue(tool.named_by_instruction({"index": 0, "tag": "span", "text": "", "classes": "big star"}, phrases))
        self.assertFalse(tool.named_by_instruction({"index": 0, "tag": "div", "text": "", "classes": "email-thread"}, phrases))
        self.assertTrue(tool.named_by_instruction({"index": 0, "tag": "div", "text": "", "id": "star-icon"}, phrases))
        self.assertFalse(tool.named_by_instruction({"index": 0, "tag": "div", "text": "the starfish"}, phrases))


class GuidedSearchTests(unittest.TestCase):
    def test_what_the_instruction_names_is_found_for_a_fraction_of_the_blind_price(self):
        blind = tool.demonstrate(StubBridge(), "two-fields", 0, action_budget=5000, search="blind")
        guided = tool.demonstrate(StubBridge(), "two-fields", 0, action_budget=5000, search="guided")
        self.assertEqual(blind["stage"], tool.STAGE_DEMONSTRATED)
        self.assertEqual(guided["stage"], tool.STAGE_DEMONSTRATED)
        cheap, dear = guided["acquisition"]["budget_spent"], blind["acquisition"]["budget_spent"]
        self.assertLessEqual(cheap * 5, dear)
        # and with a budget the guided search fits in three times over, the blind one finds nothing
        self.assertEqual(tool.demonstrate(StubBridge(), "two-fields", 0, action_budget=cheap * 3,
                                          search="blind")["stage"], tool.STAGE_NO_SUCCESS)
        page = _TASKS["two-fields"](0)
        for _, action in guided["trace"]:
            page.act(tool.parse_action(action))
        self.assertEqual(page.reward, 1.0)

    def test_what_the_instruction_does_not_name_is_still_tried(self):
        # nothing in "Press the right button." says which; the guided search has to get there by trying
        for seed in range(6):
            shown = tool.demonstrate(StubBridge(), "hidden-answer", seed, action_budget=50, search="guided")
            self.assertEqual(shown["stage"], tool.STAGE_DEMONSTRATED, seed)
            self.assertEqual(tool.parse_action(shown["trace"][0][1])["index"], 2 + seed % 3, seed)

    def test_a_page_with_no_success_is_tried_out_completely(self):
        bridge = StubBridge()
        shown = tool.demonstrate(bridge, "unsolvable", 0, action_budget=500, search="guided")
        self.assertEqual(shown["stage"], tool.STAGE_NO_SUCCESS)
        self.assertEqual(shown["acquisition"]["runs"][0]["status"], sx.FAIL_EXHAUSTED)
        self.assertEqual(bridge.acts, 2)                           # both buttons, once each

    def test_the_same_search_twice_is_the_same_search(self):
        first = tool.demonstrate(StubBridge(), "two-fields", 3, action_budget=5000, search="guided")
        second = tool.demonstrate(StubBridge(), "two-fields", 3, action_budget=5000, search="guided")
        self.assertEqual([a for _, a in first["trace"]], [a for _, a in second["trace"]])
        self.assertEqual(first["acquisition"], second["acquisition"])

    def test_an_unknown_search_is_refused(self):
        with self.assertRaises(ValueError):
            tool.acquire_first_success(StubBridge(), 0, action_budget=10, search="lucky")

    def test_practice_searches_the_way_it_was_told_to(self):
        spent = {}
        for search in tool.SEARCHES:
            bridge = StubBridge()
            shown = tool.demonstrate(bridge, "shout-or-whisper", 0, action_budget=600, search=search)
            arm = tool.build_version_space_arm(bridge, "shout-or-whisper", shown["trace"], practice=[500, 501, 502, 503],
                                               action_budget=600, tier=2, search=search)
            self.assertEqual(arm.learning["found_by_search"], 1, search)     # one practice page needed a search
            spent[search] = arm.learning["search_actions"]
        self.assertLess(spent["guided"] * 3, spent["blind"])

    def test_a_skill_learned_from_a_guided_success_holds_on_unseen_instances(self):
        bridge = StubBridge()
        row = tool.measure_task(bridge, "two-fields", test_seeds=TEST_SEEDS[:10], action_budget=5000,
                                arm_names=["verbatim", "version_space"], search="guided")
        self.assertEqual(row["stage"], tool.STAGE_DEMONSTRATED)
        self.assertEqual(row["arms"]["version_space"]["successes"], 10)
        self.assertEqual(row["arms"]["verbatim"]["successes"], 0)


class NeededStepsTests(unittest.TestCase):
    def test_a_step_the_success_did_not_need_is_dropped_and_the_shorter_route_is_replayed(self):
        bridge = StubBridge()
        shown = tool.demonstrate(bridge, "named-decoy", 0, action_budget=50, search="guided")
        self.assertEqual(shown["stage"], tool.STAGE_DEMONSTRATED)
        acquisition = shown["acquisition"]
        self.assertEqual(acquisition["steps_found"], 2)            # the search opened the note it was told about
        self.assertEqual(acquisition["steps_not_needed"], 1)
        self.assertGreater(acquisition["necessity_check_actions"], 0)
        self.assertEqual([a for _, a in shown["trace"]], ["click@3"])
        self.assertEqual(shown["trace"][0][0]["elements"][2]["text"], "Help")     # seen on a page where the note is shut

    def test_what_is_kept_pays_in_full_and_nothing_kept_can_be_left_out(self):
        # judged by each page's own definition: the kept route earns the full reward, and the same
        # route with any one step removed does not
        for task, length in (("always-the-same", 2), ("two-fields", 3), ("three-boxes", 4), ("named-decoy", 1)):
            shown = tool.demonstrate(StubBridge(), task, 0, action_budget=5000, search="guided")
            self.assertEqual(shown["stage"], tool.STAGE_DEMONSTRATED, task)
            actions = [tool.parse_action(a) for _, a in shown["trace"]]
            self.assertEqual(len(actions), length, task)

            def reward_of(steps):
                page = _TASKS[task](0)
                for step in steps:
                    page.act(step)
                return page.reward if page.done else 0.0
            self.assertEqual(reward_of(actions), 1.0, task)
            for left_out in range(len(actions)):
                self.assertLess(reward_of(actions[:left_out] + actions[left_out + 1:]), 1.0, (task, left_out))

    def test_only_a_route_that_pays_in_full_replaces_the_one_found(self):
        # leaving out one box of three still ends the episode with a reward: a third less. It must stay in.
        bridge = StubBridge()
        plan = [a for _, a in tool.demonstrate(bridge, "three-boxes", 0, action_budget=5000, search="guided")["trace"]]
        replay = tool.replay_on_fresh_page(bridge, "three-boxes", 0, plan)
        needed = tool.needed_steps(bridge, "three-boxes", 0, plan, replay["trace"])
        self.assertEqual(needed["plan"], plan)
        self.assertEqual(needed["dropped"], 0)
        self.assertEqual(needed["actions"], sum(len(plan) - 1 + 1 for _ in plan))   # each shorter plan, plus its reset

    def test_a_blind_search_is_left_as_it_was(self):
        shown = tool.demonstrate(StubBridge(), "named-button", 0, action_budget=300, search="blind")
        self.assertNotIn("steps_not_needed", shown["acquisition"])


def _one_success_arm(task, *, practice=(), budget=3000):
    bridge = StubBridge()
    shown = tool.demonstrate(bridge, task, 0, action_budget=budget, search="guided")
    assert shown["stage"] == tool.STAGE_DEMONSTRATED, (task, shown["stage"])
    arm = tool.build_version_space_arm(bridge, task, shown["trace"], practice=list(practice),
                                       action_budget=budget, tier=2, search="guided")
    return arm, shown["trace"]


class EveryOneTheInstructionMentionsTests(unittest.TestCase):
    """"Press every box it names" is one step, however many it names."""

    def test_being_mentioned_is_asked_of_the_instruction_itself_and_only_on_whole_words(self):
        said = "Select Alba, Bram, Cleo, Dion and click Submit."
        for name in ("Alba", "Bram", "Cleo", "Dion", "Submit"):
            self.assertTrue(vs.mentioned_in(said, name), name)
        # the third and fourth items are mentioned although no "between this word and that" cuts them out
        self.assertEqual(vs.slots_returning(said, "Cleo"), [])
        for absent in ("Sub", "Alb", "lba", "Enya", ""):
            self.assertFalse(vs.mentioned_in(said, absent), absent)

    def test_one_success_with_three_boxes_does_none_one_or_five(self):
        arm, trace = _one_success_arm("any-boxes")
        program = arm.skills.skills[0]
        self.assertEqual(program.kinds, [vs.SET_STEP, "click"])
        scored = tool.score_arm(StubBridge(), "any-boxes", arm, TEST_SEEDS)
        self.assertEqual(scored["successes"], len(TEST_SEEDS))
        counts = {_TASKS["any-boxes"](seed).utterance.count(",") for seed in TEST_SEEDS}
        self.assertGreaterEqual(len(counts), 4)                                # the pages really differ in how many
        self.assertTrue(any("nothing" in _TASKS["any-boxes"](seed).utterance for seed in TEST_SEEDS))
        # the same presses replayed by position, or by a program of fixed length, do not do this
        self.assertLess(tool.score_arm(StubBridge(), "any-boxes", tool.VerbatimArm(trace), TEST_SEEDS)["successes"], 5)

    def test_the_step_selects_exactly_the_boxes_named_and_nothing_else(self):
        page = vs.Page(_TASKS["any-boxes"](0).observe())
        named = [i for i, e in enumerate(page.elements) if e["tag"] == "label" and vs.mentioned_in(page.instruction, e["text"])]
        self.assertEqual(len(named), 3)
        found = vs.set_descriptions(page, named)
        self.assertTrue(found)
        for description in found:
            self.assertEqual(vs.matches(description, page), named)
        self.assertEqual(vs.set_descriptions(page, named[:2]), [])              # two of the three named: not "all of them"
        other = next(i for i, e in enumerate(page.elements) if e["tag"] == "label" and i not in named)
        self.assertEqual(vs.set_descriptions(page, named + [other]), [])        # one that is not named: not "the named ones"
        submit = next(i for i, e in enumerate(page.elements) if e["tag"] == "button")
        self.assertEqual(vs.set_descriptions(page, named + [submit]), [])       # Submit is mentioned too, and is no box

    def test_a_single_press_is_not_read_as_all_of_them(self):
        arm, _ = _one_success_arm("one-box")
        self.assertEqual(arm.skills.skills[0].kinds, ["click", "click"])
        # ... and with practice on pages that name several, the second way is learned and then serves them all
        practised, _ = _one_success_arm("one-box", practice=[500, 501, 502, 503])
        self.assertIn([vs.SET_STEP, "click"], [program.kinds for program in practised.skills.skills])
        some = [seed for seed in TEST_SEEDS if _TASKS["one-box"](seed).utterance.count(",") >= 1]
        self.assertEqual(tool.score_arm(StubBridge(), "one-box", practised, some)["successes"], len(some))

    def _last_to_first(self, task):
        """A success on the first instance that went through the named boxes from the last on the page to the first."""
        page = _TASKS[task](0)
        named = page.utterance[len("Select "):page.utterance.index(" and click")].split(", ")
        rows = [row["text"] for row in page.rows]
        self.assertEqual(named, sorted(named, key=rows.index, reverse=True))    # that is also the order they are named in
        plan = [f"click@{rows.index(name) + 2}" for name in named] + [f"click@{len(rows) + 1}"]
        bridge = StubBridge()
        replay = tool.replay_on_fresh_page(bridge, task, 0, plan)
        self.assertTrue(replay["reproduced"])
        return bridge, replay["trace"]

    def test_whether_the_order_matters_is_asked_of_the_page_and_its_answer_is_kept(self):
        # a page that does not care in which order its boxes are ticked: asked, it pays again, and "all of them" is read off
        bridge, trace = self._last_to_first("any-boxes")
        free = tool.build_version_space_arm(bridge, "any-boxes", trace, practice=[], action_budget=3000, tier=2, search="guided")
        self.assertEqual((free.learning["order_questions"], free.learning["order_questions_answered_yes"]), (1, 1))
        self.assertEqual(free.learning["order_question_actions"], len(trace) + 1)
        self.assertEqual(free.skills.skills[0].kinds, [vs.SET_STEP, "click"])
        self.assertEqual(tool.score_arm(StubBridge(), "any-boxes", free, TEST_SEEDS)["successes"], len(TEST_SEEDS))
        # a page that pays only for the order named: asked, it does not pay, and the success is kept as it was
        bridge, trace = self._last_to_first("boxes-in-the-order-named")
        strict = tool.build_version_space_arm(bridge, "boxes-in-the-order-named", trace, practice=[], action_budget=3000,
                                              tier=2, search="guided")
        self.assertEqual((strict.learning["order_questions"], strict.learning["order_questions_answered_yes"]), (1, 0))
        self.assertNotIn(vs.SET_STEP, strict.skills.skills[0].kinds)
        self.assertEqual(len(strict.skills.skills[0].kinds), len(trace))
        # and a success that already went in the order of the page is not asked about
        arm, found = _one_success_arm("any-boxes")
        if [a for _, a in found][:-1] == sorted([a for _, a in found][:-1], key=lambda a: int(a.split("@")[1])):
            self.assertEqual(arm.learning["order_questions"], 0)

    def test_a_record_that_left_a_named_box_out_or_took_another_in_is_not_this_program(self):
        arm, trace = _one_success_arm("any-boxes")
        program = arm.skills.skills[0]
        self.assertEqual(program.kinds, [vs.SET_STEP, "click"])
        ordered = sorted(trace[:-1], key=lambda step: int(step[1].split("@")[1]))
        page = vs.Page(trace[0][0])
        other = next(i for i, e in enumerate(page.elements) if e["tag"] == "label" and not vs.mentioned_in(page.instruction, e["text"]))
        for wrong in (ordered[:-1] + [trace[-1]],                                           # one named box left out
                      ordered + [(trace[0][0], f"click@{other}")] + [trace[-1]],            # one box nobody named
                      ordered + [trace[-1], trace[-1]],                                     # something more after the end
                      list(reversed(ordered)) + [trace[-1]]):                               # the named ones, last to first
            self.assertFalse(program.add_success(wrong))
        self.assertEqual(program.examples, 1)
        self.assertTrue(program.add_success(ordered + [trace[-1]]))
        self.assertEqual(program.examples, 2)

    def test_reordering_is_only_ever_a_question(self):
        trace = [(o, a) for o, a in _one_success_arm("any-boxes")[1]]
        presses = [a for _, a in trace[:-1]]
        backwards = [(o, a) for (o, _), a in zip(trace[:-1], reversed(presses))] + [trace[-1]]
        asked = vs.page_order(backwards)
        self.assertEqual(asked, sorted(presses, key=lambda a: int(a.split("@")[1])) + [trace[-1][1]])
        self.assertIsNone(vs.page_order([(o, a) for (o, _), a in zip(trace[:-1], asked[:-1])] + [trace[-1]]))

    def test_a_success_with_another_number_of_presses_is_the_same_program(self):
        arm, _ = _one_success_arm("any-boxes", practice=[500, 501, 502, 503])
        self.assertEqual(len(arm.skills.skills), 1)
        self.assertEqual(arm.skills.skills[0].examples, 5)
        self.assertEqual(arm.learning["own_success"], 4)
        self.assertEqual(arm.learning["found_by_search"], 0)

    def test_the_names_in_the_list_do_not_count_as_a_different_way_of_asking(self):
        arm, _ = _one_success_arm("any-boxes")
        program = arm.skills.skills[0]
        for seed in TEST_SEEDS[:10]:
            observation = _TASKS["any-boxes"](seed).observe()
            if "nothing" in observation["utterance"]:
                continue
            page = vs.Page(observation)
            self.assertLessEqual(vs.mismatch(program, page.instruction, page), 1, page.instruction)   # at most the comma
            if page.instruction.count(",") != 2:
                self.assertGreater(vs.mismatch(program, page.instruction), 1, page.instruction)       # without the page: unread


class BroughtOutByThePressBeforeTests(unittest.TestCase):
    """A press that was made to bring the next target out is remembered with that purpose."""

    def test_one_success_in_one_drawer_finds_the_thing_in_any_drawer(self):
        arm, trace = _one_success_arm("drawers")
        program = arm.skills.skills[0]
        self.assertEqual(program.kinds, ["click", "click"])
        self.assertIsNone(program._reveal[0])
        self.assertIsNotNone(program._reveal[1])
        scored = tool.score_arm(StubBridge(), "drawers", arm, TEST_SEEDS)
        self.assertEqual(scored["successes"], len(TEST_SEEDS))
        self.assertGreater(arm.searched, 0)                                    # it did have to look
        # without the purpose the same program only succeeds where the thing is in the drawer of the demonstration
        program._reveal = [None] * len(program.kinds)
        blind = tool.score_arm(StubBridge(), "drawers", vs.VersionSpaceArm(arm.skills, {}), TEST_SEEDS)
        self.assertLess(blind["successes"], len(TEST_SEEDS) * 2 // 3)

    def test_looking_presses_each_drawer_at_most_once_and_nothing_that_is_no_drawer(self):
        arm, _ = _one_success_arm("drawers")
        for seed in TEST_SEEDS:
            bridge = StubBridge()
            bridge.load("drawers")
            outcome = tool.run_episode(bridge, seed, arm)
            self.assertTrue(outcome["success"], seed)
            self.assertEqual(len(bridge.page.pulled), len(set(bridge.page.pulled)), seed)
            self.assertLessEqual(outcome["steps"], 4, seed)                     # three drawers and the thing: never more

    def test_presses_made_only_to_look_are_counted_as_that_and_once(self):
        arm, _ = _one_success_arm("drawers")
        looking, steps = 0, 0
        for seed in TEST_SEEDS:                                                # from the pages: drawers pulled, less the program's own pull
            bridge = StubBridge()
            bridge.load("drawers")
            steps += tool.run_episode(bridge, seed, arm)["steps"]
            looking += len(bridge.page.pulled) - 1
        self.assertGreater(looking, 0)
        for _ in range(2):                                                     # the same arm scored twice says the same twice
            scored = tool.score_arm(StubBridge(), "drawers", arm, TEST_SEEDS)
            self.assertEqual(scored["actions_spent_looking"], looking)
            self.assertEqual(scored["actions"], steps)
        self.assertNotIn("actions_spent_looking", tool.score_arm(StubBridge(), "drawers", tool.VerbatimArm([]), TEST_SEEDS[:2]))
        # the one memory counts its looking the same way
        library = vs.SkillLibrary()
        library.add("drawers", arm.skills)
        self.assertEqual(tool.score_arm(StubBridge(), "drawers", vs.LibraryArm(library), TEST_SEEDS)["actions_spent_looking"], looking)

    def test_a_target_that_was_there_all_along_is_not_given_a_purpose_it_did_not_have(self):
        arm, _ = _one_success_arm("two-fields")
        for program in arm.skills.skills:
            self.assertEqual(program._reveal, [None] * len(program.kinds))
        arm, _ = _one_success_arm("any-boxes")
        self.assertEqual(arm.skills.skills[0]._reveal, [None, None])
        # two presses, the first on one of several elements of a kind, the second on a button that never was hidden
        page = {"utterance": "Pick a side, then go.", "elements": [
            _element(0, -1, "body"), _element(1, 0, "a", "Left", click=True, classes="side"),
            _element(2, 0, "a", "Right", click=True, classes="side"), _element(3, 0, "button", "Go", click=True, id="go")]}
        program = vs.VersionSpaceSkill()
        self.assertTrue(program.add_success([(page, "click@1"), (page, "click@3")]))
        self.assertIsNotNone(vs.family_of(vs.Page(page), 1))                    # there IS a kind to look through ...
        self.assertEqual(program._reveal, [None, None])                        # ... and no reason to

    def test_looking_stops(self):
        arm, _ = _one_success_arm("drawers")
        program = arm.skills.skills[0]
        observation = _TASKS["drawers"](1001).observe()
        drawers = {f"click@{e['index']}" for e in observation["elements"] if e.get("classes") == "drawer"}
        run = vs.Execution(program)
        pressed = []
        for _ in range(40):                                                    # a page on which nothing ever comes out
            action = run.next_action(observation)
            if action is None:
                break
            pressed.append(action)
        pulls = [action for action in pressed if action in drawers]
        self.assertEqual(sorted(pulls), sorted(drawers))                       # every drawer once ...
        self.assertEqual(run.searched, len(drawers) - 1)                       # ... one as the program's own step, the others looking
        self.assertLessEqual(len(pressed), len(drawers) + 1)                   # and then at most one last guess
        # a wall of thirty drawers and nothing behind any of them: the looking has an end of its own
        wall = {"utterance": observation["utterance"], "elements": [_element(0, -1, "body")] + [
            _element(k + 1, 0, "h4", f"Drawer {k + 1}", click=True, classes="drawer") for k in range(30)]}
        run = vs.Execution(program)
        pressed = []
        for _ in range(60):
            action = run.next_action(wall)
            if action is None:
                break
            pressed.append(action)
        self.assertEqual(run.searched, vs.MAX_REVEAL_PRESSES)
        self.assertEqual(len(pressed), len(set(pressed)))

    def test_a_program_that_cannot_begin_gives_way_to_one_that_can(self):
        alone, _ = _one_success_arm("drawers-one-open")
        self.assertEqual([program.kinds for program in alone.skills.skills], [["click"]])   # the thing was simply there
        # where the thing is not in the open drawer, the program's own description finds nothing; a weaker one still points somewhere
        hidden = [seed for seed in TEST_SEEDS if alone.skills.skills[0].begins(vs.Page(_TASKS["drawers-one-open"](seed).observe())) < 2]
        self.assertGreater(len(hidden), 5)
        self.assertLess(len(hidden), len(TEST_SEEDS))
        self.assertEqual(tool.score_arm(StubBridge(), "drawers-one-open", alone, hidden)["successes"], 0)
        arm, _ = _one_success_arm("drawers-one-open", practice=[500, 501, 502, 503, 504, 505])
        shapes = sorted(program.kinds for program in arm.skills.skills)
        self.assertEqual(shapes, [["click"], ["click", "click"]])               # ... and where it was not, a drawer was pulled first
        self.assertEqual(arm.skills.skills[0].kinds, ["click"])                # the first one held is the one that cannot begin there
        scored = tool.score_arm(StubBridge(), "drawers-one-open", arm, TEST_SEEDS)
        self.assertEqual(scored["successes"], len(TEST_SEEDS))
        # the choice itself, with one success behind each: the page decides, and without the page the first held is taken
        pair = vs.SkillSet()
        pair.add_success(tool.demonstrate(StubBridge(), "drawers-one-open", 0, action_budget=3000, search="guided")["trace"])
        practice_hidden = next(seed for seed in range(500, 540)
                               if pair.skills[0].begins(vs.Page(_TASKS["drawers-one-open"](seed).observe())) < 2)
        shown = tool.demonstrate(StubBridge(), "drawers-one-open", practice_hidden, action_budget=3000, search="guided")
        self.assertEqual(pair.add_success(shown["trace"]), "new_way")
        self.assertEqual([program.examples for program in pair.skills], [1, 1])
        for seed in hidden:
            observation = _TASKS["drawers-one-open"](seed).observe()
            self.assertEqual(pair.choose(observation["utterance"], observation).kinds, ["click", "click"], seed)
            self.assertEqual(pair.choose(observation["utterance"]).kinds, ["click"], seed)

    def test_a_press_that_was_not_needed_once_does_not_take_the_purpose_away(self):
        arm, _ = _one_success_arm("drawers-one-open", practice=[500, 501, 502, 503, 504, 505])
        two = next(program for program in arm.skills.skills if program.kinds == ["click", "click"])
        there_all_along = [example for example in two._examples
                           if vs.pick(two._targets[1][0], example[0][0]) is not None]
        self.assertTrue(there_all_along)                                       # it did pull a drawer it need not have pulled
        self.assertIsNotNone(two._reveal[1])

    def test_a_success_reached_by_looking_is_not_kept_as_a_new_way(self):
        arm, _ = _one_success_arm("drawers", practice=[500, 501, 502, 503])
        self.assertEqual(arm.learning["own_success"], 4)
        self.assertGreater(arm.learning["own_success_with_looking"], 0)
        self.assertEqual(arm.learning["new_ways"], 0)
        for program in arm.skills.skills:
            self.assertEqual(program.kinds, ["click", "click"])


def _flat_page(said, rows):
    return {"utterance": said, "elements": [_element(0, -1, "body")] + [
        _element(k + 1, 0, tag, text, click=True, **extra) for k, (tag, text, extra) in enumerate(rows)]}


class ShapeOfARecordTests(unittest.TestCase):
    """What a recorded success is read as, before anything is generalised."""
    BOXES = [("label", "Alba", {"classes": "box"}), ("label", "Bram", {"classes": "box"}),
             ("label", "Cleo", {"classes": "box"}), ("button", "Go", {})]

    def test_a_record_that_typed_where_the_program_presses_is_another_program(self):
        page = {"utterance": "Use the box, then go.", "elements": [
            _element(0, -1, "body"), _element(1, 0, "input", "", click=True, type_=True, id="box", value=""),
            _element(2, 0, "button", "Go", click=True, id="go")]}
        program = vs.VersionSpaceSkill()
        self.assertTrue(program.add_success([(page, "click@1"), (page, "click@2")]))
        self.assertFalse(program.add_success([(page, "type@1=hello"), (page, "click@2")]))
        self.assertEqual((program.examples, program.kinds, program.rejected_examples), (1, ["click", "click"], 1))

    def test_presses_between_which_the_page_changed_are_not_read_as_one_step(self):
        before = _flat_page("Select Alba, Cleo and click Go.", self.BOXES)
        same = vs.VersionSpaceSkill()
        self.assertTrue(same.add_success([(before, "click@1"), (before, "click@3"), (before, "click@4")]))
        self.assertEqual(same.kinds, [vs.SET_STEP, "click"])
        after = _flat_page("Select Alba, Cleo and click Go.", self.BOXES + [("div", "a note appeared", {})])
        changed = vs.VersionSpaceSkill()
        self.assertTrue(changed.add_success([(before, "click@1"), (after, "click@3"), (after, "click@4")]))
        self.assertEqual(changed.kinds, ["click", "click", "click"])
        self.assertIsNone(vs.page_order([(before, "click@3"), (after, "click@1"), (after, "click@4")]))

    def test_a_success_only_the_narrower_reading_explains_is_taken_and_strikes_the_wider_one_out(self):
        first = _flat_page("Select Alba, Cleo and click Go.", self.BOXES)
        program = vs.VersionSpaceSkill()
        self.assertTrue(program.add_success([(first, "click@1"), (first, "click@3"), (first, "click@4")]))
        narrow = ("equals", "self", "classes", "box")
        wide = [d for d in program._targets[0] if narrow not in d[0]]            # "every label it names"
        self.assertTrue(wide)
        self.assertLess(len(wide), len(program._targets[0]))                    # and "every label of class box it names"
        # a page on which a label of ANOTHER class is named too, and the success left that one alone
        second = _flat_page("Select Dion, Enya, Finn and click Go.", [
            ("label", "Dion", {"classes": "note"}), ("label", "Enya", {"classes": "box"}),
            ("label", "Finn", {"classes": "box"}), ("button", "Go", {})])
        self.assertTrue(program.add_success([(second, "click@2"), (second, "click@3"), (second, "click@4")]))
        self.assertEqual(program.examples, 2)
        self.assertTrue(program._targets[0])
        for description in program._targets[0]:
            self.assertIn(narrow, description[0])
        run = vs.Execution(program)
        self.assertEqual([run.next_action(second) for _ in range(4)], ["click@2", "click@3", "click@4", None])

    def test_an_element_alone_of_its_kind_still_has_a_kind(self):
        page = vs.Page(_flat_page("Open it.", [("h4", "Drawer 1", {"classes": "drawer"}), ("button", "Go", {})]))
        self.assertEqual(vs.matches(vs.family_of(page, 1), page), [1])
        self.assertIsNone(vs.family_of(page, 2))                     # nothing to tell its kind by


class StartsOrEndsWithTests(unittest.TestCase):
    def test_an_item_is_found_by_how_it_starts_and_how_it_ends(self):
        arm, trace = _one_success_arm("starts-and-ends")
        scored = tool.score_arm(StubBridge(), "starts-and-ends", arm, TEST_SEEDS)
        self.assertEqual(scored["successes"], len(TEST_SEEDS))
        first = arm.skills.skills[0]._targets[0][0]
        self.assertEqual(sorted(test[4] for test in first[0] if test[0] == "slot"), ["prefix", "suffix"])
        self.assertLess(tool.score_arm(StubBridge(), "starts-and-ends", tool.VerbatimArm(trace), TEST_SEEDS)["successes"], 10)

    def test_being_the_piece_goes_before_beginning_with_the_piece(self):
        page = vs.Page({"utterance": 'Press the "Block" button.', "elements": [
            _element(0, -1, "body"), _element(1, 0, "li", "Block @ann", click=True), _element(2, 0, "li", "Block", click=True)]})
        whole = ((("slot", "self", "text", ("quoted", 0), "exact"),), None)
        part = ((("slot", "self", "text", ("quoted", 0), "prefix"),), None)
        self.assertEqual(vs.matches(whole, page), [2])
        self.assertEqual(vs.matches(part, page), [1, 2])
        self.assertLess(vs.preference(whole, [page]), vs.preference(part, [page]))
        self.assertIn(part[0][0], vs.tests_true_of(page, 1))
        self.assertNotIn(part[0][0], vs.tests_true_of(page, 2))                 # the whole text is not "a beginning"

    def test_only_what_the_instruction_quotes_can_be_a_beginning_or_an_end(self):
        page = vs.Page({"utterance": 'Press the Block button, or "B".', "elements": [
            _element(0, -1, "body"), _element(1, 0, "li", "Block @ann", click=True)]})
        self.assertFalse([t for t in vs.tests_true_of(page, 1) if t[0] == "slot" and t[4] in ("prefix", "suffix")])


class CopiedFromWhereTheInstructionPointsTests(unittest.TestCase):
    def test_the_value_next_to_the_name_the_instruction_gives_is_what_gets_typed(self):
        arm, trace = _one_success_arm("ledger")
        scored = tool.score_arm(StubBridge(), "ledger", arm, TEST_SEEDS)
        self.assertEqual(scored["successes"], len(TEST_SEEDS))
        typed = arm.skills.skills[0]._texts[0][0]
        self.assertEqual(typed[0], "copy")
        self.assertTrue(any(test[0] == "slot" for test in typed[1][0]))
        # the word typed in the demonstration is on almost no other page
        self.assertLess(tool.score_arm(StubBridge(), "ledger", tool.VerbatimArm(trace), TEST_SEEDS)["successes"], 10)

    def test_a_program_that_copies_through_the_instruction_reads_that_word_as_a_value(self):
        arm, _ = _one_success_arm("ledger")
        program = arm.skills.skills[0]
        for seed in TEST_SEEDS[:8]:
            self.assertEqual(vs.mismatch(program, _TASKS["ledger"](seed).utterance), 0)


@unittest.skipUnless(os.environ.get("MINIWOB_HTML_DIR") and shutil.which("node"),
                     "set MINIWOB_HTML_DIR (and MINIWOB_BRIDGE_NODE_MODULES) to run against the real pages")
class RealPageTests(unittest.TestCase):
    """Against MiniWoB++ itself. Skipped unless the pages and node are present."""

    def setUp(self):
        self.bridge = tool.Bridge(os.environ["MINIWOB_HTML_DIR"], os.environ.get("MINIWOB_BRIDGE_NODE_MODULES", ""))

    def tearDown(self):
        self.bridge.close()

    def test_a_seed_is_one_page_whatever_happened_before(self):
        self.assertTrue(self.bridge.load("click-button")["ok"])
        first = tool.state_key(self.bridge.reset(7))
        observation = self.bridge.reset(3)
        clickable = [e["index"] for e in observation["elements"] if e["can_click"]]
        self.bridge.act({"type": "click", "index": clickable[0]})
        self.assertEqual(tool.state_key(self.bridge.reset(7)), first)

    def test_the_page_timer_runs_on_the_virtual_clock(self):
        self.bridge.load("click-button")
        observation = self.bridge.reset(1)
        limit = observation["page_time_limit_ms"]
        steps = 0
        while not observation["done"] and steps < 100:
            observation = self.bridge.act({"type": "click", "index": 0})
            steps += 1
        self.assertTrue(observation["done"])
        self.assertEqual(observation["reason"], "timed out")
        self.assertEqual(observation["virtual_ms"], limit)
        self.assertLess(observation["raw_reward"], 0)

    def test_the_right_button_is_rewarded_and_a_wrong_one_is_not(self):
        self.bridge.load("click-button")
        observation = self.bridge.reset(0)
        wanted = observation["utterance"].split('"')[1]
        right = [e["index"] for e in observation["elements"] if e["tag"] == "button" and e["text"] == wanted]
        wrong = [e["index"] for e in observation["elements"] if e["tag"] == "button" and e["text"] != wanted]
        self.assertTrue(tool.succeeded(self.bridge.act({"type": "click", "index": right[0]})))
        self.bridge.reset(0)
        self.assertTrue(tool.failed(self.bridge.act({"type": "click", "index": wrong[0]})))


@unittest.skipUnless(os.environ.get("MINIWOB_HTML_DIR") and os.environ.get("MINIWOB_CHROMIUM_NODE_MODULES")
                     and shutil.which("node"),
                     "set MINIWOB_HTML_DIR and MINIWOB_CHROMIUM_NODE_MODULES to run against the real pages in Chromium")
class RealBrowserTests(RealPageTests):
    """The same pages in headless Chromium: everything asked of the headless DOM, and what only a browser does."""

    def setUp(self):
        self.bridge = tool.Bridge(os.environ["MINIWOB_HTML_DIR"], os.environ["MINIWOB_CHROMIUM_NODE_MODULES"],
                                  substrate="chromium")

    def test_it_says_which_browser_it_is(self):
        versions = self.bridge.versions()
        self.assertIn("Chrome", versions["browser"])
        self.assertEqual(len(versions["viewport"]), 2)

    def test_every_shown_element_reports_a_box_and_a_button_has_a_real_one(self):
        self.bridge.load("click-button")
        observation = self.bridge.reset(0)
        for element in observation["elements"]:
            self.assertEqual(len(element["box"]), 4)
        buttons = [e for e in observation["elements"] if e["tag"] == "button"]
        self.assertTrue(buttons)
        for button in buttons:
            self.assertGreater(button["box"][2], 5)
            self.assertGreater(button["box"][3], 5)
        tops = [b["box"][1] for b in buttons]
        self.assertEqual(tops, sorted(tops))            # laid out down the page, in document order

    def test_typing_goes_through_the_keyboard(self):
        # A date field takes keystrokes part by part and reports ISO; only a browser does that.
        self.bridge.load("enter-date")
        observation = self.bridge.reset(0)
        wanted = [t for t in tool.utterance_tokens(observation["utterance"]) if t.count("/") == 2][0]
        month, day, year = wanted.split("/")
        field = [e["index"] for e in observation["elements"] if e["can_type"]][0]
        observation = self.bridge.act({"type": "type", "index": field, "text": wanted})
        self.assertEqual(observation["elements"][field]["value"], f"{year}-{month}-{day}")
        self.assertTrue(observation["elements"][field].get("focused"))

    def test_typing_replaces_what_was_there(self):
        self.bridge.load("enter-text")
        observation = self.bridge.reset(0)
        field = [e["index"] for e in observation["elements"] if e["can_type"]][0]
        self.bridge.act({"type": "type", "index": field, "text": "first try"})
        observation = self.bridge.act({"type": "type", "index": field, "text": "Second"})
        self.assertEqual(observation["elements"][field]["value"], "Second")
        observation = self.bridge.act({"type": "type", "index": field, "text": ""})
        self.assertEqual(observation["elements"][field]["value"], "")

    def test_the_first_look_at_a_page_is_already_drawn(self):
        # The search icon is a picture named by the stylesheet. Before it arrives its box is empty.
        # The very first look of a new browser must not be that look.
        self.bridge.load("email-inbox")
        first = self.bridge.reset(0)
        icon = [e for e in first["elements"] if e.get("id") == "open-search"][0]
        self.assertGreater(icon["box"][2], 0)
        self.assertTrue(icon["can_click"])
        self.assertNotIn("files_still_arriving", first)
        self.assertEqual(tool.state_key(self.bridge.reset(0)), tool.state_key(first))

    def test_an_element_below_the_fold_is_scrolled_to_and_then_pressed(self):
        self.bridge.load("email-inbox")
        observation = self.bridge.reset(0)
        rows = [e for e in observation["elements"] if e.get("classes") == "email-thread"]
        self.assertGreater(len(rows), 1)
        last = rows[-1]
        self.assertGreater(last["box"][1], rows[0]["box"][1])
        opened = self.bridge.act({"type": "click", "index": last["index"]})
        self.assertNotIn("action_error", opened)
        self.assertNotEqual(tool.state_key(opened), tool.state_key(observation))
        self.assertFalse([e for e in opened["elements"] if e.get("classes") == "email-thread"])   # the list gave way to the message

    def _success_by_hand(self, task, seed, plan):
        """A plan read off the page by this test, kept only because the page itself pays for it on a fresh copy."""
        replay = tool.replay_on_fresh_page(self.bridge, task, seed, plan)
        self.assertTrue(replay["reproduced"], (task, seed, plan, replay["reason"]))
        return replay["trace"]

    def test_the_boxes_the_real_page_names_are_one_step_whatever_their_number(self):
        self.bridge.load("click-checkboxes")
        plan, shown_on = None, None
        for seed in range(40):
            observation = self.bridge.reset(seed)
            named = [e["index"] for e in observation["elements"]
                     if e["tag"] == "label" and vs.mentioned_in(observation["utterance"], e["text"])]
            if len(named) >= 3:
                submit = [e["index"] for e in observation["elements"] if e.get("id") == "subbtn"]
                plan, shown_on = [f"click@{index}" for index in named + submit], seed
                break
        self.assertIsNotNone(plan)
        skills = vs.SkillSet()
        skills.add_success(self._success_by_hand("click-checkboxes", shown_on, plan))
        self.assertEqual(skills.skills[0].kinds, [vs.SET_STEP, "click"])
        seeds = list(range(1000, 1012))
        self.bridge.load("click-checkboxes")
        asked = {self.bridge.reset(seed)["utterance"].count(",") for seed in seeds}
        self.assertGreaterEqual(len(asked), 3)                                  # the unseen pages name different numbers of boxes
        scored = tool.score_arm(self.bridge, "click-checkboxes", vs.VersionSpaceArm(skills, {}), seeds)
        self.assertEqual(scored["successes"], len(seeds))                       # the page's verdict, twelve times
        self.assertEqual(scored["actions_spent_looking"], 0)

    def test_a_link_behind_another_tab_of_the_real_page_is_looked_for_and_found(self):
        self.bridge.load("click-tab-2")
        trace = None
        for seed in range(40):
            observation = self.bridge.reset(seed)
            wanted = tool.quoted_spans(observation["utterance"])[0]
            if any(e.get("classes") == "alink" and e["text"] == wanted for e in observation["elements"]):
                continue                                                        # the link is on the tab already open: nothing to learn from
            tabs = [e["index"] for e in observation["elements"] if e.get("classes") == "ui-tabs-anchor"]
            for tab in tabs:
                self.bridge.reset(seed)
                opened = self.bridge.act({"type": "click", "index": tab})
                link = [e["index"] for e in opened["elements"] if e.get("classes") == "alink" and e["text"] == wanted]
                if link:
                    trace = self._success_by_hand("click-tab-2", seed, [f"click@{tab}", f"click@{link[0]}"])
                    break
            if trace:
                break
        self.assertIsNotNone(trace)
        skills = vs.SkillSet()
        skills.add_success(trace)
        program = skills.skills[0]
        self.assertEqual(program.kinds, ["click", "click"])
        self.assertIsNotNone(program._reveal[1])                                # the tab was pressed to bring the link out
        seeds = list(range(1000, 1012))
        scored = tool.score_arm(self.bridge, "click-tab-2", vs.VersionSpaceArm(skills, {}), seeds)
        self.assertEqual(scored["successes"], len(seeds))
        self.assertGreater(scored["actions_spent_looking"], 0)                  # on some pages it was behind yet another tab
        program._reveal = [None, None]                                          # the same program without the purpose
        without = tool.score_arm(self.bridge, "click-tab-2", vs.VersionSpaceArm(skills, {}), seeds)
        self.assertLess(without["successes"], len(seeds))

    def test_a_substrate_nobody_named_is_refused(self):
        with self.assertRaises(ValueError):
            tool.Bridge(os.environ["MINIWOB_HTML_DIR"], "", substrate="a real person")


if __name__ == "__main__":
    unittest.main()
