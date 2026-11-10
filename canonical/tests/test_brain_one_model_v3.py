#!/usr/bin/env python3
"""ONE MODEL v3 — the door over every proven layer.

Each test pins a property that was measured, not imagined. The failures they exist for
all actually happened during construction:

  * `resolve` refusing a confident route because a *binding* input was missing --
    correct, but the refusal did not say which input (#measured this round)
  * `core.solve()` being called on a UNIFIED_ONLY capability, which cannot bind
  * `acquire` learning nothing because a fully-misspelled goal has no target
  * the carrier being assumed absent when `unshare` was present all along
"""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import pytest

from canonical.runtime import brain_one_model_v3 as v3
from canonical.runtime import admitted_confinement_execution_v1 as carrier
from canonical.runtime import brain_one_model_v2 as core

ROOT = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------- what it is made of
def test_the_model_is_one_door_over_every_proven_layer():
    inv = v3.inventory()
    assert inv["capabilities_indexed"] == 443
    assert inv["bound_capabilities"] == 141
    assert inv["h100_verified_capabilities"] == 21
    assert inv["engines"] == 1, "one model, not a portfolio"
    assert inv["layers"] == ["ROUTE", "BIND", "COMPILE", "H100", "EXECUTE",
                             "ACQUIRE", "REFUSE"]


def test_the_model_has_no_weights_and_says_so_every_answer():
    r = v3.resolve("extract text from a pdf")
    assert r["weights"] == 0
    assert r["persistent_learned_bytes"] == 0
    assert r["incremental_spend_usd"] == 0


def test_h100_learned_bytes_are_zero_as_the_registry_claims():
    inv = v3.inventory()
    assert inv["h100_persistent_learned_bytes"] == 0


# ------------------------------------------------------------------- the seven layers
def test_refusal_names_the_input_it_is_missing():
    """A refusal that names no cause cannot be acted on."""
    r = v3.resolve("extract text from a pdf")
    assert r["pass"] is False
    assert r["status"].startswith("FAIL_CLOSED__INPUT_BINDING_REQUIRED")
    assert r["detail"]["needs"] == ["pdf_path"]
    assert "pdf_path" in r["detail"]["fix"]


def test_a_goal_it_cannot_place_is_refused_with_a_price_not_a_guess():
    r = v3.resolve("order me a pizza")
    assert r["pass"] is False
    assert r["layer"] == "REFUSAL"
    gaps = [g.get("gap") for g in (r["detail"].get("cheapest_gaps") or [])]
    assert gaps, "a refusal must name what is missing"


def test_the_schema_compiler_answers_and_spends_nothing():
    r = v3.resolve("compile this table, target column y",
                   payload="x,y\n0,2\n1,5\n2,8\n3,11\n", target_column="y",
                   inputs={"features": ["x"]})
    assert r["pass"] is True
    assert r["layer"] == "H100_SCHEMA_COMPILER"
    assert r["compiled"]["persistent_learned_bytes"] == 0
    assert r["compiled"]["external_frontier_model_calls"] == 0


def test_routing_never_executes_by_default():
    """The default call must be side-effect free."""
    r = v3.resolve("audit the python source in canonical/runtime", execute=False)
    assert r["pass"] is False


# ------------------------------------------------------------------ the carrier
def test_the_carrier_refuses_a_writer():
    for argv in (["rm", "-rf", "x"], ["tee", "x"], ["sort", "-o", "a", "b"]):
        v = carrier.admission_verdict(argv)
        assert v["admitted"] is False, argv


def test_the_carrier_admits_a_reader():
    v = carrier.admission_verdict(["cut", "-d", " ", "-f", "1", "README.md"])
    assert v["admitted"] is True


def test_the_carrier_executes_a_read_only_command_and_proves_the_tree_untouched():
    """This is the admitted path the boundary's docstring was waiting for."""
    r = carrier.execute_confined(["cut", "-d", " ", "-f", "1", "README.md"], timeout=25)
    assert r["confined"] is True
    assert r["live_workspace_untouched"] is True
    assert r["before_sha256"] == r["after_sha256"]
    assert r["pass"] is True
    assert r["stdout"]
    # and it does not overclaim what the carrier is
    assert r["carrier_qualified"] is False


def test_the_boundary_is_not_weakened_by_the_carrier():
    """The gate still refuses on every unconfined path; this is an alternative, not an edit."""
    from canonical.runtime import computer_execution_boundary_v1 as boundary
    assert boundary.refuses_execution("shell.command.run",
                                      {"adapter_module": "shell_command_run", "source": {}},
                                      None) is True


# ------------------------------------------------------------------ acquisition
def test_a_typo_with_no_clean_signal_learns_nothing_rather_than_guessing():
    v3.core.POLICY_PATH = Path("/tmp") / f"p_{uuid.uuid4().hex}.json"
    assert v3._infer_target("audti pyton soruce structure") is None


def test_bridges_persist_as_rewrite_rules_not_as_guesses(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "POLICY_PATH", tmp_path / "p.json")
    n = core._learn_bridges([{"token": "pyton", "match": "python",
                              "rule": "TYPO_1_INS", "score": 0.95}])
    assert n == 1
    st = core._load_policy()
    assert st["bridges"]["pyton"]["match"] == "python"
    # a weaker later claim must not displace a stronger one
    core._learn_bridges([{"token": "pyton", "match": "perl",
                          "rule": "TRIGRAM_DICE", "score": 0.1}])
    assert core._load_policy()["bridges"]["pyton"]["match"] == "python"


# ---------------------------------------------------------------------- latency
def test_the_free_layers_are_microseconds():
    v3.core._load_index()
    v3.core.route("warm")
    t = time.perf_counter()
    for _ in range(50):
        v3.core.route("extract text from a pdf")
    us = (time.perf_counter() - t) / 50 * 1e6
    assert us < 500, f"route cost {us:.1f} us"
