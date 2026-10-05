from __future__ import annotations

import os
import platform
from pathlib import Path

import pytest

from canonical.runtime.root3_linux_userns_effect_carrier_v1 import (
    CarrierError,
    build_unshare_command,
    probe,
    run_isolated,
)


def test_path_escape_is_rejected(tmp_path):
    repo=tmp_path/"repo"; repo.mkdir()
    root=tmp_path/"root"; root.mkdir()
    with pytest.raises(CarrierError):
        build_unshare_command(
            repo_root=repo,
            sandbox_root=root,
            writable_repo_prefixes=["../escape"],
            argv=["/usr/bin/true"],
        )


def test_repo_root_cannot_be_writable_prefix(tmp_path):
    repo=tmp_path/"repo"; repo.mkdir()
    root=tmp_path/"root"; root.mkdir()
    with pytest.raises(CarrierError,match="WRITABLE_PREFIX_REPO_ROOT_FORBIDDEN"):
        build_unshare_command(
            repo_root=repo,
            sandbox_root=root,
            writable_repo_prefixes=["."],
            argv=["/usr/bin/true"],
        )


def test_overlapping_writable_prefixes_fail_closed(tmp_path):
    repo=tmp_path/"repo"; repo.mkdir()
    (repo/"out").mkdir(); (repo/"out"/"nested").mkdir()
    root=tmp_path/"root"; root.mkdir()
    with pytest.raises(CarrierError,match="WRITABLE_PREFIX_OVERLAP"):
        build_unshare_command(
            repo_root=repo,
            sandbox_root=root,
            writable_repo_prefixes=["out","out/nested"],
            argv=["/usr/bin/true"],
        )


def test_preexisting_hardlink_alias_in_writable_prefix_fails_closed(tmp_path):
    repo=tmp_path/"repo"; repo.mkdir()
    (repo/"input").mkdir(); (repo/"out").mkdir()
    source=repo/"input"/"a.txt"
    source.write_text("original",encoding="utf-8")
    os.link(source,repo/"out"/"alias")
    root=tmp_path/"root"; root.mkdir()
    with pytest.raises(CarrierError,match="WRITABLE_PREFIX_HARDLINK_FORBIDDEN"):
        build_unshare_command(
            repo_root=repo,
            sandbox_root=root,
            writable_repo_prefixes=["out"],
            argv=["/usr/bin/true"],
        )


@pytest.mark.skipif(not hasattr(os,"mkfifo"),reason="FIFO unsupported")
def test_special_file_in_repo_fails_closed(tmp_path):
    repo=tmp_path/"repo"; repo.mkdir()
    (repo/"out").mkdir()
    os.mkfifo(repo/"out"/"pipe")
    root=tmp_path/"root"; root.mkdir()
    with pytest.raises(CarrierError,match="SPECIAL_FILE_FORBIDDEN"):
        build_unshare_command(
            repo_root=repo,
            sandbox_root=root,
            writable_repo_prefixes=["out"],
            argv=["/usr/bin/true"],
        )


def test_command_declares_all_required_namespaces_and_capability_drop(tmp_path):
    repo=tmp_path/"repo"; repo.mkdir()
    (repo/"out").mkdir()
    root=tmp_path/"root"; root.mkdir()
    cmd=build_unshare_command(
        repo_root=repo,
        sandbox_root=root,
        writable_repo_prefixes=["out"],
        argv=["/usr/bin/true"],
    )
    joined=" ".join(cmd)
    for token in ("--user","--map-root-user","--mount","--net","--pid","--fork","--kill-child"):
        assert token in cmd
    assert "--bounding-set=-all" in joined
    assert "--inh-caps=-all" in joined
    assert "--ambient-caps=-all" in joined
    assert "--nnp" in joined
    assert 'mount -o remount,bind,ro "$root/workspace"' in joined


@pytest.mark.skipif(platform.system().lower()!="linux",reason="Linux-only carrier")
def test_live_carrier_when_explicitly_enabled(tmp_path):
    if os.environ.get("PROJECT_BRAIN_RUN_USERNS_CARRIER_INTEGRATION")!="1":
        pytest.skip("explicit integration probe disabled")
    p=probe()
    if not p["static_prerequisites_present"]:
        pytest.skip("carrier tools unavailable")
    repo=tmp_path/"repo"; repo.mkdir()
    (repo/"input").mkdir(); (repo/"out").mkdir()
    (repo/"input"/"a.txt").write_text("input",encoding="utf-8")
    script=(
        "from pathlib import Path; import socket,subprocess,os; "
        "assert Path('/workspace/input/a.txt').read_text()=='input'; "
        "\ntry: Path('/workspace/input/bad').write_text('x'); raise SystemExit(91)\n"
        "except OSError: pass\n"
        "Path('/workspace/out/ok.txt').write_text('persist'); "
        "\ntry: os.link('/workspace/input/a.txt','/workspace/out/hard'); raise SystemExit(93)\n"
        "except OSError: pass\n"
        "os.symlink('/workspace/input/a.txt','/workspace/out/sym'); "
        "\ntry: Path('/workspace/out/sym').write_text('x'); raise SystemExit(94)\n"
        "except OSError: pass\n"
        "s=socket.socket(); s.settimeout(.1); "
        "\ntry: s.connect(('1.1.1.1',53)); raise SystemExit(92)\n"
        "except OSError: pass\n"
        "p=subprocess.run(['/usr/bin/mount','-t','tmpfs','tmpfs','/tmp'],capture_output=True); "
        "assert p.returncode!=0"
    )
    out=run_isolated(
        repo_root=repo,
        writable_repo_prefixes=["out"],
        argv=["/usr/bin/python3","-c",script],
        timeout_s=30,
    )
    assert out.returncode==0,(out.stdout,out.stderr)
    assert not (repo/"input"/"bad").exists()
    assert (repo/"input"/"a.txt").read_text()=="input"
    assert (repo/"out"/"ok.txt").read_text()=="persist"
