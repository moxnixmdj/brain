#!/usr/bin/env python3
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "canonical" / "runtime" / "enforce_goal_hierarchy.py"

spec = importlib.util.spec_from_file_location("goal_guard_sensitivity_test", PATH)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

def test_action_intent_is_frontier_sensitive():
    assert guard.is_sensitive(
        "canonical/action_intents/2026-09-29_EXAMPLE.json"
    ) is True

def test_unrelated_document_is_not_frontier_sensitive():
    assert guard.is_sensitive("README.md") is False
