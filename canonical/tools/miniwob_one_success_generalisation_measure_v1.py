"""Does ONE success become a skill? Measured on web tasks nobody in this repository wrote.

The claim under test
--------------------
"After the machine does a thing once, it has learned it permanently." Recalling the same
solution to the same instance is a cache and is not in dispute. The claim only means
something on the NEXT instance: same task, different page content, different instruction
wording. So this tool measures exactly that step and nothing else:

    1. on ONE instance of a task (the demonstration seed) the machine finds a success by
       itself -- systematic exploration, the page's own reward as the only judge, no model.
       `--search blind` tries every offered action nearest the start first. `--search guided`
       tries the same actions in another ORDER: what the instruction names first (an element
       whose text is a run of the instruction's words; typing text the instruction quotes),
       buttons after everything else that is named. Nothing is removed from what is tried;
    2. the success is replayed on a freshly loaded page under the page's own time limit, or
       it does not count;
    3. each arm turns that one trace into something it can apply to an instance it has not
       seen, and gets ONE try on each of N unseen instances. A wrong click ends the episode.

The environment is MiniWoB++ (Farama-Foundation/miniwob-plusplus, MIT; 130 task pages that
originate in OpenAI's World of Bits), on one of two substrates that take the same commands
and return the same observation:

    chromium   `miniwob_chromium_bridge_v1.mjs`: headless Chromium. Real layout and
               hit-testing; a click is a mouse press at the element's box, typing is key
               events; every episode is a freshly opened page; every element reports its box.
    jsdom      `miniwob_jsdom_bridge_v1.js`: a headless DOM with no layout and no pixels. A
               task that needs geometry does not run faithfully there.

Both run on a virtual clock. The agent can click an element or type into one; it cannot
hover, drag, scroll by itself or press single keys, so a task that needs those is expected
to end with no first success, and is counted as such -- the denominators below always say
which tasks were left out and why.

Arms
----
    random             uniformly random offered action, same number of steps as the demonstration
    verbatim           the demonstration replayed by element position: what a cache does
    existing_compiler  the repository's own demonstration-to-skill generaliser, AS IT IS:
                       `causal_trace_to_skill_compiler_v1` elevates each step to a semantic
                       selector, anti-unifies literals shared with the instruction into holes,
                       and binds a new instruction by regular expression. Its own executor
                       submits HTTP forms and cannot click a live page, so the click itself is
                       done here; elevation, generalisation, binding and instantiation are its
                       code, unmodified.
    version_space      `demonstration_version_space_v1` from the ONE success: every description of
                       each target and every way of cutting the typed text out of the
                       instruction that fits it, in a stated order of preference.
    version_space_blind
                       a control: the one-success skill again, but shown the demonstration's
                       instruction on every instance. What it still solves, it solves without
                       reading; what it loses, it was reading.
    version_space_practice
                       the same learner, after --practice-episodes further instances. On each it tries
                       the skill as it stands; when the page says no it explores that instance
                       for a success. Only page-rewarded traces are ever added, and the
                       exploration it costs is reported.

What a number here is not
-------------------------
Not a MiniWoB++ leaderboard entry (the success found on the demonstration instance comes from
trying actions against the page's own reward, which a leaderboard agent is not given) and
not a capability claim. The author of this tool is a language model that has read about
MiniWoB++; the tasks are split by a hash of their name into a quarter that was looked at
while building the arms and three quarters that were not, and the two are reported apart.
Authority: NONE until someone else reruns it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import pickle
import random
import re
import select
import subprocess
import sys
import time
from typing import Any, Callable, Iterable, Mapping, Sequence

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from canonical.runtime import systematic_exploration_v1 as explorer  # noqa: E402

SCHEMA = "BRAIN_MINIWOB_ONE_SUCCESS_GENERALISATION_MEASUREMENT_V1"
DIGEST_SCHEMA = "BRAIN_MINIWOB_ONE_SUCCESS_GENERALISATION_DIGEST_V1"
AUTHORITY = "NONE__PRODUCER_RUN_SANDBOX_MEASUREMENT"
BRIDGE_JS = pathlib.Path(__file__).with_name("miniwob_jsdom_bridge_v1.js")
CHROMIUM_BRIDGE_JS = pathlib.Path(__file__).with_name("miniwob_chromium_bridge_v1.mjs")
# Where the pages run. Same commands, same observation; what differs is what is underneath.
SUBSTRATES = {
    "jsdom": {
        "script": BRIDGE_JS,
        "description": "jsdom headless DOM, element-level actions, virtual clock; no layout, no pixels",
        "version_keys": ("node", "jsdom", "fake_timers", "step_ms", "epoch_ms"),
        "is_a_browser": False,
    },
    "chromium": {
        "script": CHROMIUM_BRIDGE_JS,
        "description": ("headless Chromium: real layout and hit-testing, a click is a mouse press on a part of "
                        "the element that shows, typing is key events, and the hand can also hover, drag, nudge, "
                        "press three times and wait; virtual clock; one small fixed window"),
        "version_keys": ("node", "browser", "puppeteer_core", "chromium_package", "step_ms", "epoch_ms", "viewport"),
        "is_a_browser": True,
    },
}

DEMO_SEED = 0
FIRST_TEST_SEED = 1000
FIRST_PRACTICE_SEED = 500
EXPLORATION_TIME_LIMIT_MS = 3_600_000   # the page's episode timer is lifted while exploring, never while scoring
MAX_EPISODE_STEPS = 30
DEVELOPMENT_MODULUS = 4

STAGE_NOT_RUNNING = "PAGE_DOES_NOT_RUN_HERE"
STAGE_NOT_REPEATABLE = "SAME_SEED_GIVES_DIFFERENT_PAGE"
STAGE_NO_SUCCESS = "NO_FIRST_SUCCESS_FOUND"
STAGE_NOT_REPRODUCED = "FIRST_SUCCESS_NOT_REPRODUCED_ON_FRESH_PAGE"
STAGE_DEMONSTRATED = "DEMONSTRATED"


# --------------------------------------------------------------------------- #
# the bridge
# --------------------------------------------------------------------------- #
class BridgeHang(RuntimeError):
    """The page ran something that never returned (typically a layout loop without a layout engine)."""


class BridgeError(RuntimeError):
    """The page or the bridge refused a command."""


class Bridge:
    """One `node` process holding one page. Line-delimited JSON, with a watchdog on every reply."""

    def __init__(self, html_dir: str, node_modules_dir: str = "", *, timeout: float = 20.0,
                 node: str = "node", substrate: str = "jsdom") -> None:
        if substrate not in SUBSTRATES:
            raise ValueError("SUBSTRATE_UNKNOWN")
        self.substrate = substrate
        script = SUBSTRATES[substrate]["script"]
        self._argv = [node, str(script), str(html_dir)] + ([str(node_modules_dir)] if node_modules_dir else [])
        self._timeout = float(timeout)
        self._proc: subprocess.Popen[bytes] | None = None
        self._buffer = b""
        self.task: str | None = None
        self._start()

    def _start(self) -> None:
        self._proc = subprocess.Popen(self._argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.DEVNULL, bufsize=0)
        self._buffer = b""
        self.task = None

    def restart(self) -> None:
        self.close()
        self._start()

    def _call(self, **message: Any) -> dict[str, Any]:
        assert self._proc is not None and self._proc.stdin is not None and self._proc.stdout is not None
        self._proc.stdin.write((json.dumps(message) + "\n").encode())
        self._proc.stdin.flush()
        deadline = time.time() + self._timeout
        while b"\n" not in self._buffer:
            left = deadline - time.time()
            if left <= 0:
                self._stop()
                raise BridgeHang(f"NO_REPLY_TO_{str(message.get('cmd')).upper()}_IN_{int(self._timeout)}S")
            ready, _, _ = select.select([self._proc.stdout], [], [], left)
            if ready:
                chunk = os.read(self._proc.stdout.fileno(), 1 << 16)
                if not chunk:
                    raise BridgeError("BRIDGE_PROCESS_ENDED")
                self._buffer += chunk
        line, self._buffer = self._buffer.split(b"\n", 1)
        reply = json.loads(line)
        if isinstance(reply, dict) and reply.get("error"):
            raise BridgeError(str(reply["error"])[:300])
        return reply

    def versions(self) -> dict[str, Any]:
        return self._call(cmd="versions")

    def load(self, task: str) -> dict[str, Any]:
        reply = self._call(cmd="load", task=task)
        self.task = task if reply.get("ok") else None
        return reply

    def reset(self, seed: int, *, time_limit_ms: int | None = None) -> dict[str, Any]:
        if time_limit_ms is None:
            return self._call(cmd="reset", seed=int(seed))
        return self._call(cmd="reset", seed=int(seed), time_limit_ms=int(time_limit_ms))

    def act(self, action: Mapping[str, Any]) -> dict[str, Any]:
        return self._call(cmd="act", action=dict(action))

    def _stop(self) -> None:
        """End the process even when it is stuck. It is asked first (a bridge that holds a browser
        ends the browser when asked), and killed only if it does not go."""
        proc = self._proc
        if proc is None or proc.poll() is not None:
            return
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            pass
        if proc.poll() is None:
            proc.kill()

    def close(self) -> None:
        proc = self._proc
        if proc is None:
            return
        try:
            if proc.poll() is None and proc.stdin is not None:
                proc.stdin.write(b'{"cmd":"close"}\n')
                proc.stdin.flush()
                proc.wait(timeout=3)
        except Exception:
            pass
        self._stop()
        self._proc = None


# --------------------------------------------------------------------------- #
# observations and actions
# --------------------------------------------------------------------------- #
FULL_REWARD = 1.0


def succeeded(observation: Mapping[str, Any]) -> bool:
    """The page ended the episode and gave its FULL reward.

    Some MiniWoB++ pages pay part of the reward for part of the task: one ticked box of three
    pays a third, any colour pays for how close it is, one page pays 0.1 for a wrong card.
    "Any positive reward" is a common way to score these pages, and it is the wrong one for the
    question asked here, which is whether the thing was DONE. Until 2026-11-11 this function
    accepted any positive reward, and the two results written with it (..._V1.json and
    ..._V2.json) are too generous on those pages. Episodes that were paid in part are counted
    separately (`partial_credit`) and never as successes.
    """
    return bool(observation.get("done")) and float(observation.get("raw_reward") or 0) >= FULL_REWARD - 1e-9


def partly_rewarded(observation: Mapping[str, Any]) -> bool:
    """The page ended the episode with some reward, but not all of it. Counted, never as success."""
    return (bool(observation.get("done")) and not succeeded(observation)
            and float(observation.get("raw_reward") or 0) > 0)


def failed(observation: Mapping[str, Any]) -> bool:
    return bool(observation.get("done")) and not succeeded(observation)


def state_key(observation: Mapping[str, Any]) -> str:
    """Identity of a page state. The clock and the error log are left out on purpose: two visits
    to the same page at different times are the same place."""
    body = [observation.get("utterance"), bool(observation.get("done")), succeeded(observation),
            observation.get("elements")]
    # Three things belong to the place and are in no element: what the hand has hold of, the seconds it
    # has just let pass, and the text that shows as selected. With something held, after a wait, or with
    # text selected, the same page is somewhere else. (Left out when there is nothing to say, so a page
    # reached with presses and typing alone has the key it always had.)
    beyond = [observation.get("holding"), observation.get("waited_s"), observation.get("selection") or None]
    if any(value is not None for value in beyond):
        body.append(beyond)
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:20]


_QUOTED = re.compile(r'"([^"]+)"|(?<![A-Za-z0-9])\'([^\']+)\'(?![A-Za-z0-9])')
_EDGE_PUNCTUATION = ".,;:!?\"'()[]{}"


def quoted_spans(utterance: str) -> list[str]:
    out = []
    for match in _QUOTED.finditer(utterance or ""):
        value = match.group(1) if match.group(1) is not None else match.group(2)
        if value and value not in out:
            out.append(value)
    return out


def utterance_tokens(utterance: str) -> list[str]:
    out = []
    for raw in (utterance or "").split():
        token = raw.strip(_EDGE_PUNCTUATION)
        if token and token not in out:
            out.append(token)
    return out


def page_texts(observation: Mapping[str, Any], *, limit: int = 200) -> list[str]:
    out = []
    for element in observation.get("elements") or []:
        for field in ("text", "value"):
            value = str(element.get(field) or "").strip()
            if value and len(value) <= limit and value not in out:
                out.append(value)
    return out


def type_candidates(observation: Mapping[str, Any], tier: int) -> list[str]:
    """What might be typed, cheapest guess first: quoted text; then any word of the
    instruction and the quoted text in the other letter case; then any text already on the page."""
    utterance = str(observation.get("utterance") or "")
    out = list(quoted_spans(utterance))
    if tier >= 1:
        for span in list(out):
            out += [v for v in (span.upper(), span.lower()) if v not in out]
        out += [t for t in utterance_tokens(utterance) if t not in out]
    if tier >= 2:
        out += [t for t in page_texts(observation) if t not in out]
    return out


HAND_TIER = 3                            # everything the hand can do, not only pressing and typing
AT_AN_ELEMENT = ("click", "hover", "grab", "drop", "triple")    # written  kind@index
WITH_A_WORD = ("type", "nudge")                                 # written  kind@index=word
NUDGE_WORDS = ("up", "down", "left", "right")
MAX_WAIT_SECONDS = 60
_WHOLE_NUMBER = re.compile(r"(?<![\w.])\d+(?![\w.])")


def is_hand_action(action: str) -> bool:
    """Anything other than a press and typing."""
    return not str(action).startswith(("click@", "type@"))


def wait_candidates(utterance: str) -> list[int]:
    """How long might be waited: the whole numbers the instruction gives, read as seconds."""
    out: list[int] = []
    for found in _WHOLE_NUMBER.findall(utterance or ""):
        if len(found) <= 3 and 0 < int(found) <= MAX_WAIT_SECONDS and int(found) not in out:
            out.append(int(found))
    return out


def offered_actions(observation: Mapping[str, Any], tier: int) -> list[str]:
    """What can be tried on this page. Tiers 0 to 2: pressing, and typing from a widening
    vocabulary. Tier 3 (HAND_TIER) adds the rest of the hand: moving the pointer onto an element,
    pressing it three times fast, taking hold of it, carrying it a short way up, down, left or
    right, and letting the seconds the instruction speaks of go by. A hand that has hold of
    something can do one thing only: let go of it over something else."""
    if observation.get("done"):
        return []
    elements = observation.get("elements") or []
    reachable = [e["index"] for e in elements if e.get("can_click") and not e.get("disabled")]
    if observation.get("holding") is not None:
        return [f"drop@{index}" for index in reachable if index != observation.get("holding")]
    actions = [f"click@{index}" for index in reachable]
    texts = None
    for element in elements:
        if element.get("can_type"):
            if texts is None:
                texts = type_candidates(observation, tier)
            for text in texts:
                if text != str(element.get("value") or ""):
                    actions.append(f"type@{element['index']}={text}")
    if tier >= HAND_TIER:
        for index in reachable:
            if elements[index].get("tag") == "option":       # an option is picked from its list; that is all
                continue
            actions += [f"hover@{index}", f"triple@{index}", f"grab@{index}"]
            actions += [f"nudge@{index}={word}" for word in NUDGE_WORDS]
        actions += [f"wait={seconds}" for seconds in wait_candidates(str(observation.get("utterance") or ""))]
    return actions


def parse_action(action: str) -> dict[str, Any]:
    text = str(action)
    if text.startswith("wait="):
        seconds = text[5:]
        if not seconds.isdigit() or not 0 < int(seconds) <= MAX_WAIT_SECONDS:
            raise ValueError("ACTION_NOT_UNDERSTOOD")
        return {"type": "wait", "seconds": int(seconds)}
    kind, _, rest = text.partition("@")
    if kind in AT_AN_ELEMENT:
        return {"type": kind, "index": int(rest)}
    if kind in WITH_A_WORD:
        index, _, word = rest.partition("=")
        if kind == "nudge" and word not in NUDGE_WORDS:
            raise ValueError("ACTION_NOT_UNDERSTOOD")
        return {"type": kind, "index": int(index), "text": word}
    raise ValueError("ACTION_NOT_UNDERSTOOD")


def cannot_be_done(observation: Mapping[str, Any], wanted: Mapping[str, Any]) -> str | None:
    """Why this action cannot be taken on the page as it now is, or None when it can."""
    holding = observation.get("holding") is not None
    if holding != (wanted["type"] == "drop"):
        return "PLAN_ASKS_THE_HAND_FOR_WHAT_IT_CANNOT_DO_NOW"       # hold and press at once; let go of nothing
    if wanted["type"] == "wait":
        return None
    elements = observation.get("elements") or []
    if not 0 <= wanted["index"] < len(elements):
        return "PLAN_NAMES_AN_ELEMENT_THAT_IS_NOT_ON_THE_PAGE"
    element = elements[wanted["index"]]
    if wanted["type"] == "type":
        able = element.get("can_type")
    else:
        able = element.get("can_click") and (wanted["type"] == "click" or element.get("tag") != "option")
    return None if able else "PLAN_ACTS_ON_AN_ELEMENT_THAT_CANNOT_TAKE_THE_ACTION"


# --------------------------------------------------------------------------- #
# the order in which a guided search tries things
# --------------------------------------------------------------------------- #
SEARCHES = ("blind", "guided")
PHRASE_WORDS = 6                        # the longest run of instruction words an element can be named by
NAMING_ATTRIBUTES = ("id", "classes", "name", "title", "alt", "aria-label", "placeholder", "data-value", "colour")
BUTTON_INPUT_TYPES = ("submit", "button", "image", "reset")


def plain_words(text: Any) -> list[str]:
    """Lower-case words with the punctuation at their edges dropped; `-` and `_` separate words."""
    out = []
    for raw in str(text or "").replace("-", " ").replace("_", " ").split():
        word = raw.strip(_EDGE_PUNCTUATION).lower()
        if word:
            out.append(word)
    return out


def instruction_phrases(utterance: str) -> frozenset[str]:
    """Every run of up to PHRASE_WORDS neighbouring words of the instruction."""
    words = plain_words(utterance)
    return frozenset(" ".join(words[i:j]) for i in range(len(words))
                     for j in range(i + 1, min(len(words), i + PHRASE_WORDS) + 1))


def is_button(element: Mapping[str, Any]) -> bool:
    return (element.get("tag") == "button" or element.get("role") == "button"
            or (element.get("tag") == "input" and str(element.get("type") or "").lower() in BUTTON_INPUT_TYPES))


def named_by_instruction(element: Mapping[str, Any], phrases: frozenset[str]) -> bool:
    """Does the instruction call this element by name? Its own text is a run of the instruction's
    words; or what a button shows as its value is; or one of its names in the markup is (a whole
    name, so class `star` is named by "click the star" and class `email-thread` is not named by
    "the email")."""
    own = " ".join(plain_words(element.get("text")))
    if own and own in phrases:
        return True
    if is_button(element):
        shown = " ".join(plain_words(element.get("value")))
        if shown and shown in phrases:
            return True
    for attribute in NAMING_ATTRIBUTES:
        value = str(element.get(attribute) or "")
        for name in (value.split() if attribute == "classes" else [value]):
            words = " ".join(plain_words(name))
            if words and words in phrases:
                return True
    return False


def already_chosen(elements: Sequence[Mapping[str, Any]]) -> set[int]:
    """Elements that show as ticked or selected, and the labels that stand for them."""
    chosen = {e["index"] for e in elements if e.get("checked") or e.get("selected")}
    ids = {str(e.get("id")): e["index"] for e in elements if e.get("id")}
    out = set(chosen)
    for e in elements:
        if e.get("tag") != "label":
            continue
        if ids.get(str(e.get("for") or "")) in chosen or any(c.get("parent") == e["index"] and c["index"] in chosen for c in elements):
            out.add(e["index"])
    return out


def focus_only(elements: Sequence[Mapping[str, Any]]) -> set[int]:
    """Elements a press merely puts the text cursor into: text fields, and the labels that stand
    for them. Typing into a field already does that, so pressing one is never what was asked."""
    fields = {e["index"] for e in elements if e.get("can_type")}
    ids = {str(e.get("id")): e["index"] for e in elements if e.get("id")}
    out = set(fields)
    for e in elements:
        if e.get("tag") == "label" and (ids.get(str(e.get("for") or "")) in fields
                                        or any(c.get("parent") == e["index"] and c["index"] in fields for c in elements)):
            out.add(e["index"])
    return out


def is_picture(element: Mapping[str, Any], parents: set[int]) -> bool:
    """Nothing written on it and nothing inside it, yet it takes up room: an icon. Icons are for pressing."""
    box = element.get("box")
    return (not str(element.get("text") or "") and element["index"] not in parents and not element.get("can_type")
            and element.get("tag") not in ("input", "select", "option", "textarea")
            and (box is None or (box[2] > 0 and box[3] > 0)))


_SENTENCE_END = (".", "!", "?")
_LITERAL_MARKS = set("@/:#$%&*+=<>\\_~^|")


def literal_words(utterance: str) -> list[str]:
    """Words of the instruction that look like values rather than like prose, by spelling alone:
    a digit, a symbol, or a capital letter anywhere but at the start of a sentence. No word list."""
    out: list[str] = []
    starts_sentence = True
    for raw in (utterance or "").split():
        word = raw.strip(_EDGE_PUNCTUATION)
        if word and word not in out:
            capital = any(ch.isupper() for ch in word)
            if (any(ch.isdigit() for ch in word) or any(ch in _LITERAL_MARKS for ch in word)
                    or (capital and not starts_sentence)):
                out.append(word)
        starts_sentence = raw.endswith(_SENTENCE_END)
    return out


HAND_PRICE = 1_000_000
POINT_PRICE = HAND_PRICE // 8


class GuidedPrices:
    """The price of trying each action, read off the instruction. An ORDER of trying, not a belief.

    Pressing
        0   something the instruction names, unless it already shows as chosen
        1   a button or an icon the instruction does not name; something named that is chosen
        2   anything else, a text field included (typing into a field already puts the cursor there)
    Typing into an empty field
        0   text the instruction puts in quotes, or a word of it spelled like a value
            (see `literal_words`), that no other field holds yet
        1   the same once another field holds it; such a text in the other letter case
        3   any other word of the instruction; text found on the page
        +2  when the field already holds something

    The rest of the hand (see `offered_actions`, tier 3)
        POINT_PRICE for moving the pointer onto an element the instruction names: it commits to
        nothing, and a menu that opens under the pointer is walked by doing it several times.
        HAND_PRICE more than a press of the same element for anything else: the pointer onto an
        element nobody named, three fast presses, taking hold, a nudge (+2 in a direction the
        instruction does not name); HAND_PRICE for a wait. Letting go of what is held costs what
        a press there would: the drag was paid for when the thing was taken.
    POINT_PRICE is more than any run of presses and typing can add up to within a budget, and
    HAND_PRICE is eight of it. So the order is: everything pressing and typing can reach; then
    that again after pointing at up to seven named things; then after ONE other thing the hand
    can do; then after two. A page that pressing and typing solve is searched exactly as it was
    before the hand could do anything else.

    Typing what the instruction does not mark as a value is dearer than pressing anything,
    because there is so much more of it: every field times every word. In one state, equal
    prices are tried typing first, buttons last (a button is what usually ends an episode).
    All of it is a guess about user interfaces in general, written after reading MiniWoB++
    pages, and all it can cost is actions: every offered action is still tried.
    """

    def __init__(self) -> None:
        self._for: Any = None
        self._context: Any = None

    def _read(self, observation: Mapping[str, Any]) -> Any:
        if self._for is not observation or self._context is None:     # one page is priced action by action
            utterance = str(observation.get("utterance") or "")
            elements = observation.get("elements") or []
            parents = {int(e["parent"]) for e in elements if int(e.get("parent", -1)) >= 0}
            values = set(quoted_spans(utterance)) | set(literal_words(utterance))
            held: dict[str, int] = {}
            for e in elements:
                if e.get("can_type") and str(e.get("value") or ""):
                    held[str(e["value"])] = held.get(str(e["value"]), 0) + 1
            self._for = observation
            self._context = (instruction_phrases(utterance), values, {v.lower() for v in values}, held,
                             already_chosen(elements), focus_only(elements), parents)
        return self._context

    def __call__(self, observation: Mapping[str, Any], action: str) -> tuple[int, int]:
        phrases, values, values_any_case, held, chosen, cursor_only, parents = self._read(observation)
        wanted = parse_action(action)
        if wanted["type"] == "wait":
            return HAND_PRICE, 1
        element = observation["elements"][wanted["index"]]
        if wanted["type"] == "type":
            text, own = wanted["text"], str(element.get("value") or "")
            if text in values:
                price = 1 if held.get(text, 0) > (1 if own == text else 0) else 0
            elif text.lower() in values_any_case:
                price = 1
            else:
                price = 3
            return price + (2 if own else 0), 0
        button = is_button(element)
        turn = 2 if button else 1
        if wanted["index"] in cursor_only:
            press = 2
        elif named_by_instruction(element, phrases):
            press = 1 if wanted["index"] in chosen else 0
        else:
            press = 1 if button or is_picture(element, parents) else 2
        if wanted["type"] in ("click", "drop"):
            return press, turn
        if wanted["type"] == "hover" and press == 0:
            return POINT_PRICE, turn
        if wanted["type"] == "nudge" and wanted["text"] not in phrases:
            press += 2
        return HAND_PRICE + press, turn


class SeedEnv:
    """One instance of one task as reset() / act() / state(), which is what the explorer drives."""

    def __init__(self, bridge: Any, seed: int, *, time_limit_ms: int | None = None) -> None:
        self._bridge = bridge
        self._seed = int(seed)
        self._limit = time_limit_ms
        self._observation: dict[str, Any] = {}
        self.page_errors: list[str] = []

    def reset(self) -> dict[str, Any]:
        self._observation = self._bridge.reset(self._seed, time_limit_ms=self._limit)
        self.page_errors += self._observation.get("js_errors") or []
        return self._observation

    def act(self, action: str) -> dict[str, Any]:
        self._observation = self._bridge.act(parse_action(action))
        self.page_errors += self._observation.get("js_errors") or []
        return self._observation

    def state(self) -> dict[str, Any]:
        return self._observation


# --------------------------------------------------------------------------- #
# stage 1: one success, found by the machine, on one instance
# --------------------------------------------------------------------------- #
GUIDED_TIER = 2      # what a guided search found with presses and typing alone is recorded under this tier


def acquire_first_success_guided(bridge: Any, seed: int, *, action_budget: int) -> dict[str, Any]:
    """Everything the hand can do, tried in the order `GuidedPrices` gives: all that pressing and
    typing reach first (the widest blind tier), the rest of the hand only after that. The tier
    reported for a success is the narrowest that holds every action of it."""
    env = SeedEnv(bridge, seed, time_limit_ms=EXPLORATION_TIME_LIMIT_MS)
    result = explorer.explore_to_goal(
        env, [], is_goal=succeeded, is_dead=failed,
        actions_of=lambda observation: offered_actions(observation, HAND_TIER), key_of=state_key,
        order="cheapest", cost_of=GuidedPrices(), action_budget=int(action_budget), reset_cost=1, include_model=False)
    runs = [{"tier": HAND_TIER, "status": result["status"], "budget_spent": int(result["budget_spent"]),
             "acts": int(result["acts"]), "resets": int(result["resets"]),
             "states": int(result["state_count"]), "surprises": int(result["surprises"])}]
    found = bool(result["pass"])
    with_the_hand = found and any(is_hand_action(a) for a in list(result["plan_cheapest"]) + list(result["plan_walked"]))
    return {"found": found,
            "plan": [str(a) for a in result["plan_cheapest"]] if found else None,
            "plan_walked": [str(a) for a in result["plan_walked"]] if found else None,
            "tier": (HAND_TIER if with_the_hand else GUIDED_TIER) if found else None,
            "budget_spent": int(result["budget_spent"]), "runs": runs,
            "page_errors": sorted(set(env.page_errors))[:3]}


def acquire_first_success(bridge: Any, seed: int, *, action_budget: int,
                          tier_shares: Sequence[float] = (0.4, 0.3, 0.3), search: str = "blind") -> dict[str, Any]:
    """Systematic exploration of ONE instance until the page itself reports success.

    Blind: typed text is tried in tiers (quoted text; any instruction word; any text on the
    page). A later tier keeps the map the earlier one drew, so nothing is paid for twice.
    Guided: see `acquire_first_success_guided`.
    """
    if search not in SEARCHES:
        raise ValueError("SEARCH_UNKNOWN")
    if search == "guided":
        return acquire_first_success_guided(bridge, seed, action_budget=action_budget)
    env = SeedEnv(bridge, seed, time_limit_ms=EXPLORATION_TIME_LIMIT_MS)
    model: dict[str, dict[str, str]] | None = None
    spent = 0
    runs = []
    saw_typable = False

    for tier, share in enumerate(tier_shares):
        remaining = int(action_budget) - spent
        if remaining <= 0:
            break
        is_last = tier == len(tier_shares) - 1
        allowance = remaining if is_last else min(remaining, max(1, int(action_budget * share)))

        def actions_here(observation: Mapping[str, Any], _tier: int = tier) -> list[str]:
            nonlocal saw_typable
            if any(e.get("can_type") for e in observation.get("elements") or []):
                saw_typable = True
            return offered_actions(observation, _tier)

        result = explorer.explore_to_goal(
            env, [], is_goal=succeeded, is_dead=failed, actions_of=actions_here, key_of=state_key,
            order="shallowest", action_budget=allowance, prior=model, reset_cost=1, include_model=True)
        spent += int(result["budget_spent"])
        model = result["model"]
        runs.append({"tier": tier, "status": result["status"], "budget_spent": int(result["budget_spent"]),
                     "acts": int(result["acts"]), "resets": int(result["resets"]),
                     "states": int(result["state_count"]), "surprises": int(result["surprises"])})
        if result["pass"]:
            return {"found": True, "plan": [str(a) for a in result["plan_shortest"]],
                    "plan_walked": [str(a) for a in result["plan_walked"]], "tier": tier,
                    "budget_spent": spent, "runs": runs, "page_errors": sorted(set(env.page_errors))[:3]}
        if not saw_typable:
            # Nothing on any page seen takes text, so a wider vocabulary changes nothing: the
            # tiers are one exploration, and it simply continues on what is left of the budget.
            if result["status"] == explorer.OPEN_BUDGET and int(action_budget) - spent > 0:
                more = explorer.explore_to_goal(
                    env, [], is_goal=succeeded, is_dead=failed, actions_of=actions_here, key_of=state_key,
                    order="shallowest", action_budget=int(action_budget) - spent, prior=model, reset_cost=1,
                    include_model=True)
                spent += int(more["budget_spent"])
                runs.append({"tier": tier, "status": more["status"], "budget_spent": int(more["budget_spent"]),
                             "acts": int(more["acts"]), "resets": int(more["resets"]),
                             "states": int(more["state_count"]), "surprises": int(more["surprises"])})
                if more["pass"]:
                    return {"found": True, "plan": [str(a) for a in more["plan_shortest"]],
                            "plan_walked": [str(a) for a in more["plan_walked"]], "tier": tier,
                            "budget_spent": spent, "runs": runs, "page_errors": sorted(set(env.page_errors))[:3]}
            break
    return {"found": False, "plan": None, "plan_walked": None, "tier": None, "budget_spent": spent, "runs": runs,
            "page_errors": sorted(set(env.page_errors))[:3]}


def replay_on_fresh_page(bridge: Any, task: str, seed: int, plan: Sequence[str]) -> dict[str, Any]:
    """The success must happen again on a page with no history and the page's own timer."""
    loaded = bridge.load(task)
    if not loaded.get("ok"):
        return {"reproduced": False, "trace": [], "reason": "PAGE_DID_NOT_RELOAD"}
    observation = bridge.reset(seed)
    trace = []
    for action in plan:
        if observation.get("done"):
            return {"reproduced": False, "trace": trace, "reason": "EPISODE_ENDED_BEFORE_THE_PLAN_DID"}
        # Every step must be something that can be done on the page as it now is. A plan whose
        # step names an element that is not there is not a shorter plan that happens to work: the
        # page ignores that step, and what would be recorded is an action nobody could have taken.
        wanted = parse_action(action)
        why_not = cannot_be_done(observation, wanted)
        if why_not:
            return {"reproduced": False, "trace": trace, "reason": why_not}
        trace.append((observation, str(action)))
        observation = bridge.act(wanted)
    return {"reproduced": succeeded(observation), "trace": trace,
            "reason": None if succeeded(observation) else "PLAN_DID_NOT_END_IN_SUCCESS"}


def needed_steps(bridge: Any, task: str, seed: int, plan: Sequence[str],
                 trace: Sequence[tuple[Mapping[str, Any], str]]) -> dict[str, Any]:
    """Which steps did the success need? Each step is left out in turn, last first, on a fresh
    page. If the page still pays in full without it, the step was not a cause of the success
    and is dropped. What comes back is again a route that succeeded on a fresh page -- the
    shorter one -- together with what finding that out cost."""
    kept, kept_trace, spent, dropped = [str(a) for a in plan], list(trace), 0, 0
    position = len(kept) - 1
    while position >= 0 and len(kept) > 1:
        shorter = kept[:position] + kept[position + 1:]
        replay = replay_on_fresh_page(bridge, task, seed, shorter)
        spent += len(replay["trace"]) + 1
        if replay["reproduced"]:
            kept, kept_trace, dropped = shorter, replay["trace"], dropped + 1
        position -= 1
    return {"plan": kept, "trace": kept_trace, "actions": spent, "dropped": dropped}


def demonstrate(bridge: Any, task: str, seed: int, *, action_budget: int, search: str = "blind") -> dict[str, Any]:
    """Find a success on one instance and make it happen again on a fresh page.

    The explorer reports the shortest route IN THE MAP IT DREW. When a page keeps state the
    observation does not show, that map merges places that differ and its shortest route can
    be wrong. The route it actually walked since its last reset is then tried as well: that
    one happened. Whichever is used, only a route that succeeds again on a fresh page counts.
    """
    if not bridge.load(task).get("ok"):
        return {"stage": STAGE_NOT_RUNNING, "reason": "PAGE_DID_NOT_RELOAD", "trace": None, "acquisition": None}
    acquired = acquire_first_success(bridge, seed, action_budget=action_budget, search=search)
    summary: dict[str, Any] = {k: acquired[k] for k in ("found", "tier", "budget_spent", "runs", "page_errors")}
    if not acquired["found"]:
        return {"stage": STAGE_NO_SUCCESS, "reason": None, "trace": None, "acquisition": summary}
    reason = None
    for source in ("plan", "plan_walked"):
        plan = acquired[source]
        if source == "plan_walked" and plan == acquired["plan"]:
            break
        replay = replay_on_fresh_page(bridge, task, seed, plan)
        if replay["reproduced"]:
            summary["route_used"] = ("as_walked" if source == "plan_walked"
                                     else "cheapest_in_map" if search == "guided" else "shortest_in_map")
            trace = replay["trace"]
            if search == "guided":
                # a guided search does what the instruction names first, needed or not; keep what was needed
                needed = needed_steps(bridge, task, seed, plan, trace)
                trace = needed["trace"]
                summary["steps_found"] = len(plan)
                summary["steps_not_needed"] = needed["dropped"]
                summary["necessity_check_actions"] = needed["actions"]
            return {"stage": STAGE_DEMONSTRATED, "reason": None, "trace": trace, "acquisition": summary}
        reason = replay["reason"]
    return {"stage": STAGE_NOT_REPRODUCED, "reason": reason, "trace": None, "acquisition": summary}


# --------------------------------------------------------------------------- #
# arms: one trace in, a policy for unseen instances out
# --------------------------------------------------------------------------- #
class RandomArm:
    name = "random"

    def __init__(self, trace: Sequence[tuple[Mapping[str, Any], str]], *, tier: int, salt: str) -> None:
        self._length = len(trace)
        self._tier = int(tier)
        self._salt = salt
        self._rng = random.Random(salt)
        self._done = 0
        self.refused = False

    def begin(self, observation: Mapping[str, Any], seed: int) -> None:
        self._rng = random.Random(f"{self._salt}:{seed}")
        self._done = 0

    def next_action(self, observation: Mapping[str, Any]) -> str | None:
        if self._done >= self._length:
            return None
        offered = offered_actions(observation, self._tier)
        if not offered:
            return None
        self._done += 1
        return self._rng.choice(offered)


class VerbatimArm:
    """The same clicks at the same positions and the same typed text. This is recall."""
    name = "verbatim"

    def __init__(self, trace: Sequence[tuple[Mapping[str, Any], str]]) -> None:
        self._plan = [action for _, action in trace]
        self._at = 0
        self.refused = False

    def begin(self, observation: Mapping[str, Any], seed: int) -> None:
        self._at = 0

    def next_action(self, observation: Mapping[str, Any]) -> str | None:
        if self._at >= len(self._plan):
            return None
        action = self._plan[self._at]
        self._at += 1
        return None if cannot_be_done(observation, parse_action(action)) else action


class InstructionBlindArm:
    """A control, not a contender: the same learned skill, shown every page as it is but always
    the DEMONSTRATION's instruction instead of the instance's own. If a skill still succeeds
    like this, it never needed the instruction -- the page alone decides, or this substrate has
    lost whatever made the instances differ. If it stops succeeding, reading the instruction
    is what the skill is doing."""
    name = "version_space_blind"

    def __init__(self, inner: Any, stale_instruction: str) -> None:
        self._inner = inner
        self._stale = str(stale_instruction)

    def _masked(self, observation: Mapping[str, Any]) -> dict[str, Any]:
        masked = dict(observation)
        masked["utterance"] = self._stale
        return masked

    @property
    def refused(self) -> bool:
        return bool(getattr(self._inner, "refused", False))

    def begin(self, observation: Mapping[str, Any], seed: int) -> None:
        self._inner.begin(self._masked(observation), seed)

    def next_action(self, observation: Mapping[str, Any]) -> str | None:
        return self._inner.next_action(self._masked(observation))


def _organ_dom(observation: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The page as the existing compiler expects to be handed it: one record per element with
    the fields its selector is built from, and a box so that a point picks exactly one."""
    out = []
    for element in observation.get("elements") or []:
        out.append({
            "role": str(element.get("role") or ""),
            "name": str(element.get("name") or ""),
            "aria": str(element.get("aria-label") or ""),
            "placeholder": str(element.get("placeholder") or ""),
            "tag": str(element.get("tag") or ""),
            "type": str(element.get("type") or ""),
            "text": str(element.get("full_text") or element.get("text") or ""),
            "id": str(element.get("id") or ""),
            "bbox": {"x": 10.0 * int(element["index"]), "y": 0.0, "width": 8.0, "height": 8.0},
        })
    return out


class ExistingCompilerArm:
    """`causal_trace_to_skill_compiler_v1` as it is in the tree: elevate, anti-unify, bind, instantiate."""
    name = "existing_compiler"

    def __init__(self, trace: Sequence[tuple[Mapping[str, Any], str]]) -> None:
        from canonical.swe_kernel import causal_trace_to_skill_compiler_v1 as organ
        self._organ = organ
        # The organ keeps instantiation private; there is no public entry that returns the
        # instantiated steps without also executing them over HTTP. Fail loudly if it moves.
        self._instantiate = getattr(organ, "_instantiate_obj")
        # The organ knows two kinds of step, a press and typed text. A success that needed anything else
        # of the hand is outside what it can take in; it then refuses every instance, and says so.
        self.outside_its_actions = any(is_hand_action(action) for _, action in trace)
        self.skill: dict[str, Any] = {}
        self.parameters: list[Any] = []
        self._steps: list[Mapping[str, Any]] = []
        self._at = 0
        self.refused = False
        if self.outside_its_actions:
            return
        steps: list[dict[str, Any]] = []
        for observation, action in trace:
            wanted = parse_action(action)
            point: dict[str, Any] = {"layer": "pixel_ui", "type": wanted["type"],
                                     "x": 10.0 * wanted["index"] + 4.0, "y": 4.0}
            if wanted["type"] == "type":
                point["text"] = wanted["text"]
            elevated = organ.elevate_trace_to_fastest_layer(
                {"steps": [point], "dom_elements": _organ_dom(observation)})
            steps.extend(dict(s) for s in elevated["elevated_steps"])
        self.skill = organ.anti_unify_workflow(str(trace[0][0].get("utterance") or ""), steps, {})
        self.parameters = list(self.skill.get("param_order") or [])
        self._steps: list[Mapping[str, Any]] = []
        self._at = 0
        self.refused = False

    def begin(self, observation: Mapping[str, Any], seed: int) -> None:
        if self.outside_its_actions:
            self.refused, self._steps, self._at = True, [], 0
            return
        bindings = self._organ.bind_goal_parameters(self.skill, str(observation.get("utterance") or ""))
        self.refused = bindings is None
        self._steps = [] if bindings is None else list(self._instantiate(self.skill["abstract_steps"], bindings))
        self._at = 0

    def next_action(self, observation: Mapping[str, Any]) -> str | None:
        if self._at >= len(self._steps):
            return None
        step = self._steps[self._at]
        self._at += 1
        if str(step.get("layer")) != "semantic_dom":
            return None
        selector = step.get("selector") if isinstance(step.get("selector"), Mapping) else {}
        if not selector:
            return None
        for element, record in zip(observation.get("elements") or [], _organ_dom(observation)):
            if all(str(record.get(key) or "").strip() == str(value) for key, value in selector.items()):
                if str(step.get("op")) == "FILL_SEMANTIC":
                    if not element.get("can_type"):
                        return None
                    return f"type@{element['index']}={step.get('value', '')}"
                return f"click@{element['index']}"
        return None


def run_episode(bridge: Any, seed: int, arm: Any) -> dict[str, Any]:
    observation = bridge.reset(seed)
    arm.begin(observation, seed)
    steps = 0
    while not observation.get("done") and steps < MAX_EPISODE_STEPS:
        action = arm.next_action(observation)
        if action is None:
            break
        observation = bridge.act(parse_action(action))
        steps += 1
    return {"success": succeeded(observation), "partial": partly_rewarded(observation), "steps": steps,
            "refused": bool(getattr(arm, "refused", False)), "ended": bool(observation.get("done"))}


def score_arm(bridge: Any, task: str, arm: Any, seeds: Sequence[int]) -> dict[str, Any]:
    """One try per unseen instance, on a page with no history."""
    if not bridge.load(task).get("ok"):
        raise BridgeError("PAGE_DID_NOT_RELOAD")
    bits, steps, refused, partial = [], 0, 0, 0
    looked_before = int(getattr(arm, "searched", 0) or 0)
    for seed in seeds:
        outcome = run_episode(bridge, seed, arm)
        bits.append(1 if outcome["success"] else 0)
        steps += outcome["steps"]
        refused += 1 if outcome["refused"] else 0
        partial += 1 if outcome["partial"] else 0
    scored = {"episodes": len(bits), "successes": sum(bits), "refused": refused, "partial_credit": partial,
              "success_rate": round(sum(bits) / max(1, len(bits)), 4), "actions": steps,
              "per_seed": "".join(str(b) for b in bits)}
    if hasattr(arm, "searched"):
        # of `actions`, the presses a program made only to bring out a target that was not on the page
        scored["actions_spent_looking"] = int(arm.searched) - looked_before
    return scored


# --------------------------------------------------------------------------- #
# one task, start to finish
# --------------------------------------------------------------------------- #
def split_of(task: str) -> str:
    digest = int(hashlib.sha256(task.encode()).hexdigest(), 16)
    return "development" if digest % DEVELOPMENT_MODULUS == 0 else "held_out"


def page_gate(bridge: Any, task: str, seeds: Sequence[int]) -> dict[str, Any]:
    """Does this page run here at all, and does a seed mean one page?"""
    loaded = bridge.load(task)
    if not loaded.get("ok"):
        return {"stage": STAGE_NOT_RUNNING, "reason": "PAGE_DID_NOT_LOAD"}
    first, errors = {}, []
    for seed in seeds:
        observation = bridge.reset(seed)
        errors += observation.get("js_errors") or []
        if not observation.get("utterance"):
            return {"stage": STAGE_NOT_RUNNING, "reason": "NO_INSTRUCTION_TEXT"}
        first[seed] = state_key(observation)
        clickable = [e["index"] for e in observation["elements"] if e.get("can_click")]
        if clickable:   # leave some history behind before asking for the same seed again
            errors += bridge.act({"type": "click", "index": clickable[-1]}).get("js_errors") or []
    if errors:
        return {"stage": STAGE_NOT_RUNNING, "reason": "PAGE_SCRIPT_ERRORS", "errors": sorted(set(errors))[:3]}
    for seed in seeds:
        if state_key(bridge.reset(seed)) != first[seed]:
            return {"stage": STAGE_NOT_REPEATABLE, "reason": "RESET_WITH_THE_SAME_SEED_DIFFERS"}
    return {"stage": None, "distinct_instances_in_gate": len(set(first.values()))}


ARM_NAMES = ("random", "verbatim", "existing_compiler", "version_space", "version_space_blind", "version_space_practice")


def keep_skills(skills_dir: str | None, task: str, arm_name: str, arm: Any) -> None:
    """Put what an arm learned where a later run can pick it up (one file per task and arm).
    What is kept is the learner's own object, byte for byte what was scored here."""
    if not skills_dir or not hasattr(arm, "skills"):
        return
    folder = pathlib.Path(skills_dir)
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / f"{task}__{arm_name}.pickle", "wb") as handle:
        pickle.dump({"task": task, "arm": arm_name, "skills": arm.skills}, handle)


def kept_skills(skills_dir: str) -> dict[str, dict[str, Any]]:
    """{arm: {task: what `keep_skills` put away}}. Only read files this tool wrote itself."""
    out: dict[str, dict[str, Any]] = {}
    for path in sorted(pathlib.Path(skills_dir).glob("*__*.pickle")):
        with open(path, "rb") as handle:
            kept = pickle.load(handle)
        out.setdefault(str(kept["arm"]), {})[str(kept["task"])] = kept["skills"]
    return out


def measure_task(bridge: Any, task: str, *, test_seeds: Sequence[int], action_budget: int,
                 arm_names: Sequence[str], practice: Sequence[int] = (), search: str = "blind",
                 skills_dir: str | None = None) -> dict[str, Any]:
    if any(name not in ARM_NAMES for name in arm_names):
        raise ValueError("ARM_UNKNOWN")
    row: dict[str, Any] = {"task": task, "split": split_of(task)}
    started = time.time()
    try:
        gate = page_gate(bridge, task, [DEMO_SEED] + list(test_seeds[:3]))
        if gate["stage"]:
            row.update(gate)
            return row
        shown = demonstrate(bridge, task, DEMO_SEED, action_budget=action_budget, search=search)
        acquired = shown["acquisition"]
        if acquired is not None:
            row["acquisition"] = acquired
        if shown["stage"] != STAGE_DEMONSTRATED:
            row["stage"] = shown["stage"]
            if shown["reason"]:
                row["reason"] = shown["reason"]
            return row
        trace = shown["trace"]
        row["stage"] = STAGE_DEMONSTRATED
        row["demonstration"] = {"utterance": trace[0][0]["utterance"], "actions": [a for _, a in trace],
                                "length": len(trace)}

        demo_key = state_key(trace[0][0])
        bridge.load(task)
        first_pages = [bridge.reset(seed) for seed in test_seeds]
        row["test_instances_identical_to_demonstration"] = sum(1 for o in first_pages if state_key(o) == demo_key)
        row["distinct_test_instructions"] = len({str(o.get("utterance") or "") for o in first_pages})

        arms: dict[str, Any] = {}
        row["arms"] = arms              # filled as it goes, so a page that breaks later keeps what was measured
        one_success_arm = None
        for name in arm_names:
            if name == "random":
                arm = RandomArm(trace, tier=int(acquired["tier"] or 0), salt=f"{task}:random")
            elif name == "verbatim":
                arm = VerbatimArm(trace)
            elif name == "existing_compiler":
                arm = ExistingCompilerArm(trace)
            elif name in ("version_space", "version_space_blind"):
                if one_success_arm is None:
                    one_success_arm = build_version_space_arm(bridge, task, trace, practice=(),
                                                              action_budget=action_budget,
                                                              tier=int(acquired["tier"] or 0), search=search)
                arm = one_success_arm if name == "version_space" else InstructionBlindArm(
                    one_success_arm, str(trace[0][0].get("utterance") or ""))
            else:
                arm = build_version_space_arm(bridge, task, trace, practice=practice,
                                              action_budget=action_budget, tier=int(acquired["tier"] or 0),
                                              search=search)
            if name in ("version_space", "version_space_practice"):
                keep_skills(skills_dir, task, name, arm)
            scored = score_arm(bridge, task, arm, test_seeds)
            for key in ("parameters", "learning"):
                if hasattr(arm, key):
                    scored[key] = getattr(arm, key)
            arms[name] = scored
    except Exception as error:  # noqa: BLE001 -- one task must not take the others' results with it
        bridge.restart()
        why = ("PAGE_HANGS" if isinstance(error, BridgeHang) else "PAGE_OR_BRIDGE_ERROR"
               if isinstance(error, BridgeError) else "TOOL_OR_LEARNER_ERROR")
        if why == "TOOL_OR_LEARNER_ERROR":
            row["error_type"] = type(error).__name__
        if row.get("stage") == STAGE_DEMONSTRATED:
            # the demonstration stands; whatever arm was running when the page broke is simply absent
            row.update(arms_incomplete=True, reason=why, detail=str(error)[:200])
        else:
            row.update(stage=STAGE_NOT_RUNNING, reason=why, detail=str(error)[:200])
    finally:
        row["seconds"] = round(time.time() - started, 2)
    return row


def build_version_space_arm(bridge: Any, task: str, trace: Sequence[tuple[Mapping[str, Any], str]], *,
                            practice: Sequence[int], action_budget: int, tier: int, search: str = "blind") -> Any:
    from canonical.runtime import demonstration_version_space_v1 as learner
    return learner.build_arm(bridge=bridge, task=task, trace=trace, practice_seeds=list(practice),
                             action_budget=action_budget, tier=tier, tool=sys.modules[__name__], search=search)


# --------------------------------------------------------------------------- #
# one agent, one memory, never told which task it faces
# --------------------------------------------------------------------------- #
LIBRARY_SCHEMA = "BRAIN_MINIWOB_ONE_MEMORY_FOR_ALL_TASKS_V1"
LIBRARY_CONDITIONS = ("all_skills", "without_this_task")


def library_of(kept: Mapping[str, Any]) -> Any:
    """Everything `keep_skills` put away for one arm, as a single memory."""
    from canonical.runtime import demonstration_version_space_v1 as learner
    library = learner.SkillLibrary()
    for task in sorted(kept):
        library.add(task, kept[task])
    return library


def measure_library(bridge: Any, tasks: Sequence[str], library: Any, *, test_seeds: Sequence[int],
                    progress: Callable[[str], None] | None = None) -> list[dict[str, Any]]:
    """Each task's unseen instances, met by ONE agent holding every kept skill.

    all_skills          the agent is not told the task; it holds what was learned everywhere
    without_this_task   the same memory with nothing learned on this task: first sight of it
    One try per instance, the page's full reward the only judge, exactly as for the per-task arms.
    """
    from canonical.runtime import demonstration_version_space_v1 as learner
    held = set(library.origins())
    rows = []
    for task in tasks:
        row: dict[str, Any] = {"task": task, "split": split_of(task), "has_own_skill": task in held}
        started = time.time()
        try:
            gate = page_gate(bridge, task, [DEMO_SEED] + list(test_seeds[:3]))
            if gate["stage"]:
                row.update(gate)
            else:
                for condition in LIBRARY_CONDITIONS:
                    arm = learner.LibraryArm(library, without=(task,) if condition == "without_this_task" else ())
                    scored = score_arm(bridge, task, arm, test_seeds)
                    scored["chosen_from"] = dict(sorted(arm.chosen_from.items(), key=lambda item: (-item[1], item[0])))
                    row[condition] = scored
        except Exception as error:  # noqa: BLE001 -- recorded against the task, like everywhere else here
            bridge.restart()
            row.update(reason="PAGE_HANGS" if isinstance(error, BridgeHang) else "PAGE_OR_BRIDGE_ERROR"
                       if isinstance(error, BridgeError) else "TOOL_OR_LEARNER_ERROR", detail=str(error)[:200])
        row["seconds"] = round(time.time() - started, 2)
        rows.append(row)
        if progress:
            progress(f"{task:<34} " + " ".join(
                f"{c}={row[c]['successes']}/{row[c]['episodes']}<-{next(iter(row[c]['chosen_from']), None)}"
                for c in LIBRARY_CONDITIONS if c in row) + (f" {row.get('stage') or row.get('reason') or ''}"))
    return rows


def summarise_library(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Counts over ALL tasks given. A task that did not run, or where nothing held could begin, counts as not done."""
    out: dict[str, Any] = {"tasks": len(rows), "tasks_with_a_skill_of_their_own": sum(1 for r in rows if r.get("has_own_skill"))}
    for condition in LIBRARY_CONDITIONS:
        scored = [r for r in rows if condition in r]
        done = sorted(r["task"] for r in scored if r[condition]["success_rate"] >= 0.9)
        out[condition] = {
            "tasks_scored": len(scored),
            "tasks_at_or_above_90_percent": len(done),
            "share_of_all_tasks_at_or_above_90_percent": round(len(done) / max(1, len(rows)), 4),
            "mean_success_rate_over_all_tasks": round(sum(r[condition]["success_rate"] for r in scored) / max(1, len(rows)), 4),
            "which": done,
        }
    first_sight = [r for r in rows if "without_this_task" in r and r["without_this_task"]["success_rate"] >= 0.9]
    out["without_this_task"]["done_with_a_skill_learned_on"] = {
        r["task"]: next(iter(r["without_this_task"]["chosen_from"]), None) for r in first_sight}
    out["without_this_task"]["of_which_had_no_skill_of_their_own"] = sorted(
        r["task"] for r in first_sight if not r.get("has_own_skill"))
    return out


def run_library(html_dir: str, node_modules_dir: str, *, skills_dir: str, arm_name: str, tasks: Sequence[str] | None,
                test_episodes: int, substrate: str = "chromium",
                progress: Callable[[str], None] | None = None, first_test_seed: int | None = None) -> dict[str, Any]:
    kept = kept_skills(skills_dir).get(arm_name) or {}
    if not kept:
        raise ValueError("NO_KEPT_SKILLS_FOR_THIS_ARM")
    library = library_of(kept)
    names = list(tasks) if tasks else list_tasks(html_dir)
    test_seeds, _ = seed_plan(test_episodes, 0, first_test_seed)
    bridge = Bridge(html_dir, node_modules_dir, substrate=substrate)
    try:
        versions = bridge.versions()
        rows = measure_library(bridge, names, library, test_seeds=test_seeds, progress=progress)
    finally:
        bridge.close()
    return {
        "schema": LIBRARY_SCHEMA,
        "authority": AUTHORITY,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {
            "source": "github.com/Farama-Foundation/miniwob-plusplus (MIT), miniwob/html",
            "html_tree_sha256": html_tree_sha256(html_dir),
            "substrate_name": substrate,
            **{k: versions.get(k) for k in SUBSTRATES[substrate]["version_keys"]},
            "python": sys.version.split()[0],
            "code_sha256": code_sha256(),
        },
        "parameters": {"skills_from_arm": arm_name, "skills_held_for_tasks": sorted(kept),
                       "programs_held": len(library.entries), "test_seeds": test_seeds,
                       "max_episode_steps": MAX_EPISODE_STEPS, "full_reward": FULL_REWARD},
        "producer_cognition_model_dependency_count": 0,
        "tasks": rows,
        "summary": summarise_library(rows),
    }


def merge_library(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Join library results over disjoint tasks. The same memory, pages and code, or nothing."""
    first = results[0]
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for result in results:
        if result.get("schema") != LIBRARY_SCHEMA:
            raise ValueError("NOT_A_LIBRARY_RESULT_OF_THIS_TOOL")
        if result.get("environment") != first.get("environment") or result.get("parameters") != first.get("parameters"):
            raise ValueError("LIBRARY_RESULTS_FROM_DIFFERENT_RUNS")
        for row in result["tasks"]:
            if row["task"] in seen:
                raise ValueError("TASK_MEASURED_TWICE")
            seen.add(row["task"])
            rows.append(dict(row))
    rows.sort(key=lambda r: r["task"])
    merged = {k: v for k, v in first.items() if k not in ("tasks", "summary")}
    merged["tasks"] = [{k: v for k, v in r.items() if k != "seconds"} for r in rows]
    merged["summary"] = summarise_library(rows)
    return merged


# --------------------------------------------------------------------------- #
# the whole benchmark
# --------------------------------------------------------------------------- #
def html_tree_sha256(html_dir: str) -> str:
    root = pathlib.Path(html_dir)
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def code_sha256() -> dict[str, str]:
    """The bytes that produced a result: this tool, the bridge, the learner, the explorer and
    the existing compiler it measures. A result says which ones it came from."""
    files = {
        "tool": pathlib.Path(__file__),
        "bridge": BRIDGE_JS,
        "bridge_chromium": CHROMIUM_BRIDGE_JS,
        "version_space_learner": REPO / "canonical/runtime/demonstration_version_space_v1.py",
        "explorer": REPO / "canonical/runtime/systematic_exploration_v1.py",
        "existing_compiler": REPO / "canonical/swe_kernel/causal_trace_to_skill_compiler_v1.py",
    }
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in files.items()}


def list_tasks(html_dir: str) -> list[str]:
    return sorted(p.stem for p in (pathlib.Path(html_dir) / "miniwob").glob("*.html"))


def summarise(rows: Sequence[Mapping[str, Any]], arm_names: Sequence[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for split in ("development", "held_out", "all"):
        chosen = [r for r in rows if split == "all" or r.get("split") == split]
        stages: dict[str, int] = {}
        for r in chosen:
            stages[str(r.get("stage"))] = stages.get(str(r.get("stage")), 0) + 1
        demonstrated = [r for r in chosen if r.get("stage") == STAGE_DEMONSTRATED and r.get("arms")]
        block: dict[str, Any] = {"tasks": len(chosen), "stages": stages, "demonstrated": len(demonstrated),
                                 "arms": {}}
        # A task that the replayed demonstration already solves on unseen instances asks for no
        # generalisation at all (the page is the same every time, or this substrate hides what
        # differs). It is counted, and then set aside when asking who generalised.
        replay_enough = {r["task"] for r in demonstrated
                         if "verbatim" in r["arms"] and r["arms"]["verbatim"]["success_rate"] >= 0.9}
        if "verbatim" in arm_names:
            block["tasks_a_fixed_replay_already_solves"] = len(replay_enough)
            block["tasks_that_need_generalisation"] = len(demonstrated) - len(replay_enough)
        if "version_space" in arm_names and "version_space_blind" in arm_names:
            # Of the tasks a one-success skill solves where replay does not: does the skill stop
            # working when it is denied the instance's own instruction? If not, and the
            # instruction does change from instance to instance, the success owes nothing to
            # reading it -- a page that gives the answer away, or a check this substrate lost.
            solved = [r for r in demonstrated if r["task"] not in replay_enough
                      and "version_space" in r["arms"] and "version_space_blind" in r["arms"]
                      and r["arms"]["version_space"]["success_rate"] >= 0.9]
            still = [r for r in solved if r["arms"]["version_space_blind"]["success_rate"] >= 0.9]
            unexplained = sorted(r["task"] for r in still if int(r.get("distinct_test_instructions") or 1) > 1)
            block["one_success_skills_where_replay_is_not_enough"] = {
                "tasks_at_or_above_90_percent": len(solved),
                "of_which_fail_when_denied_the_instruction": len(solved) - len(still),
                "of_which_still_succeed_when_denied_the_instruction": len(still),
                "of_which_still_succeed_although_the_instruction_changes": len(unexplained),
                "tasks_that_succeed_without_an_instruction_that_changes": unexplained,
            }
        for name in arm_names:
            scored = [r["arms"][name] for r in demonstrated if name in r["arms"]]
            beyond = [r["arms"][name] for r in demonstrated if name in r["arms"] and r["task"] not in replay_enough]
            episodes = sum(a["episodes"] for a in scored)
            successes = sum(a["successes"] for a in scored)
            block["arms"][name] = {
                "tasks_at_or_above_90_percent_where_replay_is_not_enough":
                    sum(1 for a in beyond if a["success_rate"] >= 0.9),
                "mean_task_success_rate_where_replay_is_not_enough":
                    round(sum(a["success_rate"] for a in beyond) / max(1, len(beyond)), 4),
                "tasks_scored": len(scored),
                "episodes": episodes,
                "successes": successes,
                "mean_task_success_rate": round(sum(a["success_rate"] for a in scored) / max(1, len(scored)), 4),
                "tasks_at_or_above_90_percent": sum(1 for a in scored if a["success_rate"] >= 0.9),
                "tasks_at_100_percent": sum(1 for a in scored if a["successes"] == a["episodes"]),
                "tasks_at_zero": sum(1 for a in scored if a["successes"] == 0),
                "refused_episodes": sum(a["refused"] for a in scored),
                "share_of_all_tasks_at_or_above_90_percent":
                    round(sum(1 for a in scored if a["success_rate"] >= 0.9) / max(1, len(chosen)), 4),
            }
        out[split] = block
    return out


def seed_plan(test_episodes: int, practice_episodes: int, first_test_seed: int | None = None) -> tuple[list[int], list[int]]:
    """Which instances are scored and which are practised on. The demonstration instance, the
    practice instances and the scored instances must never share a seed; if the requested
    sizes would make them, this refuses instead of measuring recall and calling it transfer.

    `first_test_seed` moves the scored instances. Whoever changes the learner after reading
    how it failed on some instances has made those instances part of what it was fitted to;
    the next score has to come from instances nobody has looked at."""
    first = FIRST_TEST_SEED if first_test_seed is None else int(first_test_seed)
    test_seeds = [first + i for i in range(int(test_episodes))]
    practice = [FIRST_PRACTICE_SEED + i for i in range(int(practice_episodes))]
    if DEMO_SEED in test_seeds or DEMO_SEED in practice or set(test_seeds) & set(practice):
        raise ValueError("SEEN_AND_SCORED_INSTANCES_OVERLAP")
    return test_seeds, practice


def run(html_dir: str, node_modules_dir: str, *, tasks: Sequence[str] | None, test_episodes: int,
        action_budget: int, arm_names: Sequence[str], practice_episodes: int = 0,
        progress: Callable[[str], None] | None = None, substrate: str = "jsdom",
        search: str = "blind", skills_dir: str | None = None, rows_path: str | None = None,
        first_test_seed: int | None = None) -> dict[str, Any]:
    if search not in SEARCHES:
        raise ValueError("SEARCH_UNKNOWN")
    names = list(tasks) if tasks else list_tasks(html_dir)
    test_seeds, practice = seed_plan(test_episodes, practice_episodes, first_test_seed)
    bridge = Bridge(html_dir, node_modules_dir, substrate=substrate)
    try:
        versions = bridge.versions()
        rows = []
        for name in names:
            row = measure_task(bridge, name, test_seeds=test_seeds, action_budget=action_budget,
                               arm_names=arm_names, practice=practice, search=search, skills_dir=skills_dir)
            rows.append(row)
            if rows_path:                       # a run that dies later keeps what it had finished
                with open(rows_path, "a") as handle:
                    handle.write(json.dumps(row, sort_keys=True) + "\n")
            if progress:
                arms = {k: v["success_rate"] for k, v in (row.get("arms") or {}).items()}
                progress(f"{name:<34} {row.get('split'):<11} {row.get('stage')} {arms or row.get('reason') or ''}")
    finally:
        bridge.close()
    return {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {
            "source": "github.com/Farama-Foundation/miniwob-plusplus (MIT), miniwob/html",
            "html_tree_sha256": html_tree_sha256(html_dir),
            "task_pages": len(list_tasks(html_dir)),
            "substrate": SUBSTRATES[substrate]["description"],
            "substrate_name": substrate,
            **{k: versions.get(k) for k in SUBSTRATES[substrate]["version_keys"]},
            "python": sys.version.split()[0],
            "code_sha256": code_sha256(),
        },
        "parameters": {
            "demonstration_seed": DEMO_SEED, "test_seeds": test_seeds, "practice_seeds": practice,
            "acquisition_action_budget": int(action_budget), "first_success_search": search,
            "max_episode_steps": MAX_EPISODE_STEPS,
            "exploration_time_limit_ms": EXPLORATION_TIME_LIMIT_MS,
            "split_rule": f"sha256(task name) mod {DEVELOPMENT_MODULUS} == 0 is development, the rest held out",
            "arms": list(arm_names),
        },
        "producer_cognition_model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "tasks": rows,
        "summary": summarise(rows, arm_names),
    }


def merge(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Join runs over disjoint sets of tasks into one result. Refuses anything that would make
    the joined numbers mean less than each part: other pages, another substrate, other
    parameters, or the same task twice."""
    if not results:
        raise ValueError("NOTHING_TO_MERGE")
    first = results[0]
    seen: set[str] = set()
    rows: list[Any] = []
    for result in results:
        if result.get("schema") != SCHEMA:
            raise ValueError("NOT_A_RESULT_OF_THIS_TOOL")
        if result.get("environment") != first.get("environment"):
            raise ValueError("RESULTS_FROM_DIFFERENT_PAGES_OR_SUBSTRATES")
        if result.get("parameters") != first.get("parameters"):
            raise ValueError("RESULTS_WITH_DIFFERENT_PARAMETERS")
        for row in result["tasks"]:
            if row["task"] in seen:
                raise ValueError("TASK_MEASURED_TWICE")
            seen.add(row["task"])
            rows.append(row)
    rows.sort(key=lambda r: r["task"])
    merged = {k: first[k] for k in ("schema", "authority", "environment", "parameters")}
    merged["generated_utc"] = max(str(r.get("generated_utc")) for r in results)
    merged["producer_cognition_model_dependency_count"] = 0
    merged["incremental_spend_usd"] = 0
    merged["tasks"] = rows
    merged["summary"] = summarise(rows, list(first["parameters"]["arms"]))
    return merged


def digest(result: Mapping[str, Any]) -> dict[str, Any]:
    """What goes into the repository: the numbers and how to get them again, not the raw log."""
    if result.get("schema") != SCHEMA:
        raise ValueError("NOT_A_RESULT_OF_THIS_TOOL")
    rows = []
    for r in result["tasks"]:
        entry: dict[str, Any] = {"task": r["task"], "split": r["split"], "stage": r.get("stage")}
        if r.get("reason"):
            entry["reason"] = r["reason"]
        if r.get("acquisition"):
            entry["first_success_cost_actions"] = r["acquisition"]["budget_spent"]
        if r.get("demonstration"):
            entry["demonstration_length"] = r["demonstration"]["length"]
            entry["test_instances_identical_to_demonstration"] = r.get("test_instances_identical_to_demonstration")
            entry["distinct_test_instructions"] = r.get("distinct_test_instructions")
        if r.get("arms"):
            entry["arms"] = {name: {"successes": a["successes"], "episodes": a["episodes"], "refused": a["refused"],
                                    **({"partial_credit": a["partial_credit"]} if a.get("partial_credit") else {}),
                                    **({"learning": a["learning"]} if "learning" in a else {})}
                             for name, a in r["arms"].items()}
        rows.append(entry)
    body = json.dumps(result, sort_keys=True).encode()
    return {
        "schema": DIGEST_SCHEMA,
        "authority": AUTHORITY,
        "what_this_is": ("One success per task, found by the machine itself, then one try on each unseen instance. "
                         + ("Headless Chromium with real mouse and key input. "
                            if SUBSTRATES.get(str(result["environment"].get("substrate_name")), {}).get("is_a_browser")
                            else "Element-level headless DOM, not a browser. ")
                         + "Producer-run; not a leaderboard entry."),
        "generated_utc": result["generated_utc"],
        "result_sha256": hashlib.sha256(body).hexdigest(),
        "environment": result["environment"],
        "parameters": result["parameters"],
        "producer_cognition_model_dependency_count": 0,
        "incremental_spend_usd": 0,
        "summary": result["summary"],
        "tasks": rows,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--html-dir", help="path to miniwob-plusplus/miniwob/html")
    parser.add_argument("--node-modules-dir", default="", help="directory that contains node_modules: jsdom and @sinonjs/fake-timers for jsdom, puppeteer-core and @sparticuz/chromium for chromium")
    parser.add_argument("--substrate", choices=sorted(SUBSTRATES), default="jsdom", help="where the pages run")
    parser.add_argument("--search", choices=list(SEARCHES), default="blind",
                        help="the order in which actions are tried while looking for the first success")
    parser.add_argument("--tasks", nargs="*", help="task names (default: every page)")
    parser.add_argument("--only-split", choices=["development", "held_out"], help="restrict to one split")
    parser.add_argument("--test-episodes", type=int, default=20)
    parser.add_argument("--first-test-seed", type=int, default=None,
                        help=f"score on instances from this seed on (default {FIRST_TEST_SEED}); use ones nobody has looked at")
    parser.add_argument("--practice-episodes", type=int, default=3, help="extra instances the version_space_practice arm learns from")
    parser.add_argument("--action-budget", type=int, default=1500)
    parser.add_argument("--arms", nargs="*",
                        default=["random", "verbatim", "existing_compiler", "version_space", "version_space_blind",
                                 "version_space_practice"])
    parser.add_argument("--out", help="write the full result here")
    parser.add_argument("--save-skills", help="directory to keep every learned skill in (one file per task and arm)")
    parser.add_argument("--digest-from", nargs="+",
                        help="print the digest of results written earlier (several files over disjoint tasks are joined)")
    parser.add_argument("--library-from", help="directory of kept skills: measure ONE agent holding all of them")
    parser.add_argument("--library-arm", default="version_space_practice", help="which arm's kept skills to hold")
    parser.add_argument("--library-join", nargs="+", help="print library results over disjoint tasks as one")
    args = parser.parse_args(argv)

    if args.library_join:
        loaded = [json.loads(pathlib.Path(path).read_text()) for path in args.library_join]
        print(json.dumps(merge_library(loaded), indent=1, sort_keys=True))
        return 0
    if args.library_from:
        if not args.html_dir:
            parser.error("--html-dir is required")
        result = run_library(args.html_dir, args.node_modules_dir, skills_dir=args.library_from,
                             arm_name=args.library_arm, tasks=args.tasks, test_episodes=args.test_episodes,
                             substrate=args.substrate, progress=lambda line: print(line, flush=True),
                             first_test_seed=args.first_test_seed)
        if args.out:
            pathlib.Path(args.out).write_text(json.dumps(result, indent=1, sort_keys=True))
        print(json.dumps(result["summary"], indent=1, sort_keys=True))
        return 0

    if args.digest_from:
        loaded = [json.loads(pathlib.Path(path).read_text()) for path in args.digest_from]
        print(json.dumps(digest(merge(loaded)), indent=1, sort_keys=True))
        return 0
    if not args.html_dir:
        parser.error("--html-dir is required")
    names = list(args.tasks) if args.tasks else list_tasks(args.html_dir)
    if args.only_split:
        names = [n for n in names if split_of(n) == args.only_split]
    result = run(args.html_dir, args.node_modules_dir, tasks=names, test_episodes=args.test_episodes,
                 action_budget=args.action_budget, arm_names=args.arms, practice_episodes=args.practice_episodes,
                 progress=lambda line: print(line, flush=True), substrate=args.substrate, search=args.search,
                 skills_dir=args.save_skills, rows_path=(args.out + ".rows.jsonl") if args.out else None,
                 first_test_seed=args.first_test_seed)
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(result, indent=1, sort_keys=True))
    print(json.dumps(result["summary"], indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
