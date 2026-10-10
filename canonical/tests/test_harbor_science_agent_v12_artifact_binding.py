from __future__ import annotations

import asyncio
import hashlib
import json
import os
from unittest.mock import AsyncMock, patch

from canonical.runtime import harbor_science_agent_v12 as s


DIGEST = "sha256:" + "a" * 64
GOAL = "Save results to /tmp/fallback.csv."


def payload(paths, *, digest=DIGEST, goal=GOAL, source="TASK_TOML_ARTIFACTS"):
    return json.dumps({
        "schema": s.BINDING_SCHEMA,
        "task_digest": digest,
        "instruction_sha256": hashlib.sha256(goal.encode("utf-8")).hexdigest(),
        "paths": paths,
        "source": source,
        "task_authority_used": source == "TASK_TOML_ARTIFACTS",
    }, sort_keys=True, separators=(",", ":"))


def env(binding):
    return {
        "BRAIN_TASK_DIGEST": DIGEST,
        s.ENV_KEY: binding,
    }


def test_authoritative_binding_is_validated_and_preserved_first():
    with patch.dict(os.environ, env(payload(["/root/results/output.csv"])), clear=False):
        out = s._runtime_binding(GOAL)
        assert out["paths"] == ["/root/results/output.csv"]
        deliverables = s._deliverables_with_binding(GOAL)
    assert list(deliverables.values())[0] == "/root/results/output.csv"
    assert "/tmp/fallback.csv" in deliverables.values()


def test_digest_mismatch_fails_closed():
    bad = payload(["/root/results/output.csv"], digest="sha256:" + "b" * 64)
    with patch.dict(os.environ, env(bad), clear=False):
        try:
            s._runtime_binding(GOAL)
        except RuntimeError as exc:
            assert str(exc) == "SCIENCE_TASK_ARTIFACT_BINDING_DIGEST_MISMATCH"
        else:
            raise AssertionError("digest mismatch did not fail closed")


def test_instruction_hash_mismatch_fails_closed():
    bad = payload(["/root/results/output.csv"], goal="different")
    with patch.dict(os.environ, env(bad), clear=False):
        try:
            s._runtime_binding(GOAL)
        except RuntimeError as exc:
            assert str(exc) == "SCIENCE_TASK_ARTIFACT_BINDING_INSTRUCTION_MISMATCH"
        else:
            raise AssertionError("instruction mismatch did not fail closed")


def test_unsafe_path_fails_closed():
    bad = payload(["../results/output.csv"])
    with patch.dict(os.environ, env(bad), clear=False):
        try:
            s._runtime_binding(GOAL)
        except RuntimeError as exc:
            assert str(exc) == "SCIENCE_TASK_ARTIFACT_BINDING_PATH_INVALID"
        else:
            raise AssertionError("unsafe path did not fail closed")


def test_v11_run_sees_bound_artifact_and_hook_is_restored():
    original = s.v11._brain_mandated_deliverables

    async def fake_run(goal, environment, *, max_cycles, journal_session):
        current = s.v11._brain_mandated_deliverables(goal)
        assert list(current.values())[0] == "/root/results/output.csv"
        return {
            "schema": "V11",
            "status": "BLOCKED_MAX_CYCLES_NO_BRAIN_AUTHORIZED_FINISH",
            "brain_mandated_deliverables": current,
            "resolved_requirements": [],
        }

    with patch.dict(
        os.environ,
        env(payload(["/root/results/output.csv"])),
        clear=False,
    ), patch.object(s.v11, "run_science_goal", AsyncMock(side_effect=fake_run)):
        result = asyncio.run(s.run_science_goal(GOAL, object(), max_cycles=1))

    assert result["schema"] == s.SCHEMA
    assert result["task_artifact_binding_present"] is True
    assert result["brain_mandated_deliverables"]["BD01"] == "/root/results/output.csv"
    assert s.v11._brain_mandated_deliverables is original


if __name__ == "__main__":
    test_authoritative_binding_is_validated_and_preserved_first()
    test_digest_mismatch_fails_closed()
    test_instruction_hash_mismatch_fails_closed()
    test_unsafe_path_fails_closed()
    test_v11_run_sees_bound_artifact_and_hook_is_restored()
    print("PASS__HARBOR_SCIENCE_AGENT_V12_ARTIFACT_BINDING")
