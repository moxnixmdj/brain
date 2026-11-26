"""Tests for the exact-target scoreboard and the adapter derivation that preceded it.

Two claims are pinned here: that a target is exactly one module (so chance is 1/pool and not a
domain-sized baseline), and that a query repeating the module's own name is excluded from the
clean figures rather than counted as a win.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.tools import ast_adapter_derivation_v1 as A  # noqa: E402
from canonical.tools import exact_target_scoreboard_v1 as S  # noqa: E402

SCOREBOARD = ROOT / "canonical/verification/EXACT_TARGET_SCOREBOARD_20261127_V1.json"
CENSUS = ROOT / "canonical/verification/PLAY_1_LITERAL_CALL_CENSUS_20261127_V1.json"


def test_a_query_that_names_the_module_is_a_leak_not_a_query() -> None:
    module_words = S._norm_set("expire_rule when scope")
    assert module_words & S._norm_set("expire the rule when scope no longer holds")
    assert not (S._norm_set("keep the store current") & S._norm_set("archive"))


def test_only_json_plain_literals_become_arguments() -> None:
    import ast

    ok, value = A._literal(ast.parse("{'a': [1, 2, (3, 4)]}", mode="eval").body)
    assert ok and value == {"a": [1, 2, [3, 4]]}
    ok, _ = A._literal(ast.parse("some_name", mode="eval").body)
    assert not ok, "a name is a guess, not an argument"
    ok, _ = A._literal(ast.parse("{1, 2}", mode="eval").body)
    assert not ok, "a set cannot cross a process boundary"


def test_the_adapter_census_still_says_what_it_said() -> None:
    report = json.loads(CENSUS.read_text())
    assert report["attempted"] == 406
    # The finding: literal-call derivation reaches 3.7 % of the modules it is pointed at,
    # against a kill floor of 40 %, so the variant died before anything was hand-written.
    assert report["survivors"] == 15
    assert report["verdict"] == "KILLED"
    assert report["survival_rate"] < report["kill_floor"]
    assert sum(report["outcomes"].values()) == report["attempted"]


def test_the_scoreboard_pins_one_module_per_query() -> None:
    report = json.loads(SCOREBOARD.read_text())
    assert report["chance_at_1"] == round(1 / report["pool"], 5)
    assert report["targets"] == report["clean_targets"] + report["leaked_targets"]
    assert all(row["module"] for row in report["rows"])
    assert report["model_calls"] == 0 and report["network_calls"] == 0


def test_the_scoreboard_still_says_what_it_said() -> None:
    report = json.loads(SCOREBOARD.read_text())
    # 77 % of this tree's test intents repeat the module's own name, and on the clean quarter
    # no channel clears 18 % at rank five while the ablation beats both structured channels.
    assert report["leak_share"] > 0.75
    summary = report["summary"]
    for channel in ("find_source", "contract_router"):
        assert summary[channel]["clean_at_5"] < 0.20, channel
    assert summary["topic_only_ablation"]["clean_at_5"] >= summary["contract_router"]["clean_at_5"]
