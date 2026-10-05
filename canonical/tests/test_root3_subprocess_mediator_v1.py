from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

from canonical.runtime import root3_subprocess_mediator_v1 as m


@pytest.fixture(autouse=True)
def restore_subprocess():
    try:
        m.uninstall()
    except Exception:
        subprocess.run = m._ORIGINAL_RUN
        subprocess.Popen = m._ORIGINAL_POPEN
        m._INSTALLED = False
        m._AUTHORIZER = None
        m._AUTHORITY_ID = None
    yield
    try:
        m.uninstall()
    except Exception:
        subprocess.run = m._ORIGINAL_RUN
        subprocess.Popen = m._ORIGINAL_POPEN
        m._INSTALLED = False
        m._AUTHORIZER = None
        m._AUTHORITY_ID = None


def _allow(verdicts):
    def authorizer(request):
        verdicts.append(dict(request))
        return {
            "allowed": True,
            "authorization_sha256": "a" * 64,
        }
    return authorizer


def test_denial_occurs_before_child_creation(tmp_path: pathlib.Path):
    marker = tmp_path / "must_not_exist.txt"

    def deny(request):
        return {"allowed": False, "reason": "TEST_DENY"}

    m.install(deny, authority_id="TEST")
    with pytest.raises(m.ProcessEffectDenied, match="SUBPROCESS_EFFECT_DENIED:TEST_DENY"):
        subprocess.run(
            [
                sys.executable,
                "-c",
                f"from pathlib import Path; Path({str(marker)!r}).write_text('bad')",
            ],
            check=True,
        )
    assert not marker.exists()


def test_authorized_run_preserves_completed_process_and_authorizes_once():
    verdicts = []
    m.install(_allow(verdicts), authority_id="TEST")
    result = subprocess.run(
        [sys.executable, "-c", "print('ok')"],
        text=True,
        capture_output=True,
        check=True,
    )
    assert isinstance(result, subprocess.CompletedProcess)
    assert result.stdout.strip() == "ok"
    assert len(verdicts) == 1
    assert verdicts[0]["api"] == "subprocess.run"
    assert verdicts[0]["request_sha256"]


def test_direct_popen_authorizes_once_and_preserves_live_process_semantics():
    verdicts = []
    m.install(_allow(verdicts), authority_id="TEST")
    proc = subprocess.Popen(
        [sys.executable, "-c", "print('popen-ok')"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = proc.communicate(timeout=10)
    assert proc.returncode == 0
    assert stdout.strip() == "popen-ok"
    assert stderr == ""
    assert len(verdicts) == 1
    assert verdicts[0]["api"] == "subprocess.Popen"


def test_authorizer_cannot_spawn_a_child_reentrantly():
    def recursive_authorizer(request):
        subprocess.run([sys.executable, "-c", "pass"], check=True)
        return {"allowed": True, "authorization_sha256": "b" * 64}

    m.install(recursive_authorizer, authority_id="TEST")
    with pytest.raises(
        m.ProcessEffectDenied,
        match="SUBPROCESS_EFFECT_DURING_AUTHORIZATION_FORBIDDEN",
    ):
        subprocess.run([sys.executable, "-c", "pass"], check=True)


def test_unsupported_process_creation_knob_fails_closed_before_child():
    verdicts = []
    m.install(_allow(verdicts), authority_id="TEST")
    with pytest.raises(
        m.ProcessEffectDenied,
        match="SUBPROCESS_KWARG_NOT_YET_MEDIATED:start_new_session",
    ):
        subprocess.run(
            [sys.executable, "-c", "pass"],
            start_new_session=True,
        )
    assert verdicts == []


def test_uninstall_restores_exact_original_function_objects():
    verdicts = []
    m.install(_allow(verdicts), authority_id="TEST")
    assert subprocess.run is not m._ORIGINAL_RUN
    assert subprocess.Popen is not m._ORIGINAL_POPEN
    state = m.uninstall()
    assert state["installed"] is False
    assert subprocess.run is m._ORIGINAL_RUN
    assert subprocess.Popen is m._ORIGINAL_POPEN

def test_executable_override_is_rejected_from_strict_request():
    with pytest.raises(
        m.ProcessEffectDenied,
        match="SUBPROCESS_KWARG_NOT_YET_MEDIATED:executable",
    ):
        m._request(
            "subprocess.run",
            ([sys.executable, "-c", "pass"],),
            {"executable": sys.executable, "check": True},
        )


def test_unclassified_future_kwarg_fails_closed():
    with pytest.raises(
        m.ProcessEffectDenied,
        match="SUBPROCESS_KWARG_UNCLASSIFIED:future_process_knob",
    ):
        m._request(
            "subprocess.run",
            ([sys.executable, "-c", "pass"],),
            {"future_process_knob": "surprise"},
        )


def test_neutral_forbidden_kwarg_does_not_change_request_digest():
    base = m._request(
        "subprocess.run",
        ([sys.executable, "-c", "pass"],),
        {"check": True},
    )
    neutral = m._request(
        "subprocess.run",
        ([sys.executable, "-c", "pass"],),
        {"check": True, "executable": None},
    )
    assert neutral == base

