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


_TASKS = {"two-fields": _two_fields, "three-boxes": _three_boxes, "named-decoy": _named_decoy,
          "named-button": _named_button, "type-and-submit": _type_and_submit, "shout-and-submit": _shout_and_submit,
          "numbered-section": _numbered_section, "nth-box": _nth_box, "always-the-same": _always_the_same,
          "hidden-answer": _hidden_answer, "one-or-two": _one_or_two, "unsolvable": _unsolvable,
          "hidden-latch": _hidden_latch, "shout-or-whisper": _shout_or_whisper, "chatty-section": _chatty_section,
          "shifting-section": _shifting_section, "mail-rows": _mail_rows, "widget-kind": _widget_kind}


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
        supports, against = max((vs.evidence(skill, page["utterance"]) for skill in self.kept["three-boxes"].skills),
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

    def test_a_substrate_nobody_named_is_refused(self):
        with self.assertRaises(ValueError):
            tool.Bridge(os.environ["MINIWOB_HTML_DIR"], "", substrate="a real person")


if __name__ == "__main__":
    unittest.main()
