"""Run the media host operations against real ffmpeg instead of a canned controller.

`OSWorldHostMediaOps` is the third and last canned family in this repo. Unlike the code and
state ops it was never blocked by a *logic* gap -- it was blocked by two missing binaries. apt
has no `ffmpeg` candidate here and `static-ffmpeg` fetches from `media.githubusercontent.com`,
which this environment cannot reach. The npm registry is reachable, and it ships the same static
builds, so `ffmpeg` and `ffprobe` were installed from `@ffmpeg-installer/linux-x64` and
`@ffprobe-installer/linux-x64`.

Nothing is simulated here. Real ffmpeg, real decoder, real encoded output, real bytes on disk,
and every claim is re-measured with an **independent** `ffprobe` call in the test rather than
read back from the operation's own receipt.

The guest is local: `get_file` reads the path, `download` writes the path. That is what a guest
transport does, minus a network hop.

These tests skip -- loudly, with the reason -- when the binaries or the deployment root are
absent. A skip is not a pass, and the module remains canned elsewhere until the substrate is
there.

The `ffmpeg`/`ffprobe` binaries are **not vendored into this repo**: they are ~100 MB of
third-party executables, and a repository is the wrong place for a codec build. They were
installed into `/usr/local/bin` from the npm registry for this measurement. On a machine
without them these tests skip, and the claim they support must be re-earned there.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime.osworld_v21_host_media_ops_v1 import (  # noqa: E402
    MediaOpsError,
    OSWorldHostMediaOps,
)
import canonical.runtime.osworld_v21_host_media_ops_v1 as media_module  # noqa: E402

SAFE_ROOT = pathlib.Path(media_module.SAFE_ROOT)
MEDIA_DIR = SAFE_ROOT / "share" / "media"

SUBRATE = 10  # frames per second of the synthetic source
SOURCE_SECONDS = 2


def _require_substrate() -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("SUBSTRATE: ffmpeg not on PATH")
    if shutil.which("ffprobe") is None:
        pytest.skip("SUBSTRATE: ffprobe not on PATH")
    if not SAFE_ROOT.is_dir():
        pytest.skip("SUBSTRATE: SAFE_ROOT " + str(SAFE_ROOT) + " missing")
    try:
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pytest.skip("SUBSTRATE: SAFE_ROOT " + str(SAFE_ROOT) + " not writable")


class LocalGuest:
    """A guest whose transport is this filesystem."""

    class _Controller:
        def get_file(self, path):
            return pathlib.Path(path).read_bytes()

    class _Setup:
        def __init__(self, lie=False):
            self.lie = lie

        def download(self, items):
            for item in items:
                payload = pathlib.Path(item["url"]).read_bytes()
                if self.lie:
                    payload = payload[:1]  # corrupt on the way to the guest
                pathlib.Path(item["path"]).write_bytes(payload)

    def __init__(self, *, lie=False) -> None:
        self.controller = self._Controller()
        self.setup_controller = self._Setup(lie=lie)


@pytest.fixture(scope="module")
def source() -> str:
    _require_substrate()
    target = MEDIA_DIR / "source.mp4"
    if not target.exists():
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-f", "lavfi", "-i", f"testsrc=size=320x240:rate={SUBRATE}",
             "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
             "-t", str(SOURCE_SECONDS), "-c:v", "libx264", "-pix_fmt", "yuv420p",
             "-c:a", "aac", str(target)],
            check=True, timeout=180,
        )
    return str(target)


@pytest.fixture()
def ops():
    _require_substrate()
    operations = OSWorldHostMediaOps()
    operations.bind_environment(LocalGuest())
    return operations


def _video_stream(path: str) -> dict:
    """Independent measurement, deliberately not the module's own probe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,duration,nb_frames", "-of", "json", path],
        capture_output=True, text=True, timeout=120, check=True,
    )
    return json.loads(result.stdout)["streams"][0]


def _has_audio(path: str) -> bool:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
         "stream=index", "-of", "json", path],
        capture_output=True, text=True, timeout=120, check=True,
    )
    return bool(json.loads(result.stdout).get("streams"))


def _out(name: str) -> str:
    target = MEDIA_DIR / name
    target.unlink(missing_ok=True)
    return str(target)


# --------------------------------------------------------------------------- real encoding
def test_probe_reads_the_real_source(ops, source):
    out = ops.run({"operation": "PROBE", "args": {"input": source}})
    assert out["ok"] is True
    stream = out["result"]["probe"]["streams"][0]
    assert (stream["width"], stream["height"]) == (320, 240)


def test_resize_produces_the_requested_dimensions(ops, source):
    target = _out("resized.mp4")
    ops.run({"operation": "RESIZE",
             "args": {"input": source, "output": target, "width": 160, "height": 120}})

    measured = _video_stream(target)
    assert (measured["width"], measured["height"]) == (160, 120)


def test_rotate_90_swaps_the_dimensions(ops, source):
    target = _out("rotated.mp4")
    ops.run({"operation": "ROTATE", "args": {"input": source, "output": target, "degrees": 90}})

    measured = _video_stream(target)
    assert (measured["width"], measured["height"]) == (240, 320)


def test_crop_produces_the_requested_window(ops, source):
    target = _out("cropped.mp4")
    ops.run({"operation": "CROP", "args": {"input": source, "output": target,
                                           "width": 200, "height": 150, "x": 10, "y": 10}})

    measured = _video_stream(target)
    assert (measured["width"], measured["height"]) == (200, 150)


def test_trim_shortens_the_clip_to_the_requested_window(ops, source):
    """Tolerance is encoder granularity at 10 fps (one frame = 0.1 s), not slack to pass."""
    target = _out("trimmed.mp4")
    ops.run({"operation": "TRIM", "args": {"input": source, "output": target,
                                           "start_s": 0.5, "end_s": 1.5}})

    duration = float(_video_stream(target)["duration"])
    assert abs(duration - 1.0) <= 0.2
    assert duration < SOURCE_SECONDS


def test_extract_audio_writes_a_real_audio_file(ops, source):
    target = _out("audio.wav")
    ops.run({"operation": "EXTRACT_AUDIO", "args": {"input": source, "output": target}})

    assert pathlib.Path(target).stat().st_size > 1000
    assert _has_audio(target)


def test_set_volume_produces_a_new_playable_file(ops, source):
    target = _out("quiet.mp4")
    ops.run({"operation": "SET_VOLUME",
             "args": {"input": source, "output": target, "factor": 0.25}})

    measured = _video_stream(target)
    assert (measured["width"], measured["height"]) == (320, 240)


# --------------------------------------------------------------------------- the verification
def test_a_guest_that_corrupts_the_upload_is_caught():
    """The module re-reads what landed on the guest and compares sha256. It must not trust
    the transport -- so a guest that damages the bytes has to be refused."""
    _require_substrate()
    source = MEDIA_DIR / "source.mp4"
    if not source.exists():
        pytest.skip("SUBSTRATE: source clip not built")

    lying = OSWorldHostMediaOps()
    lying.bind_environment(LocalGuest(lie=True))

    with pytest.raises(MediaOpsError) as caught:
        lying.run({"operation": "RESIZE",
                   "args": {"input": str(source), "output": _out("lying.mp4"),
                            "width": 64, "height": 48}})
    assert "READBACK_MISMATCH" in str(caught.value)


def test_a_non_media_file_is_not_probed_as_media():
    _require_substrate()
    junk = MEDIA_DIR / "notmedia.mp4"
    junk.write_text("this is not a video\n")
    operations = OSWorldHostMediaOps()
    operations.bind_environment(LocalGuest())

    with pytest.raises(MediaOpsError):
        operations.run({"operation": "PROBE", "args": {"input": str(junk)}})


# --------------------------------------------------------------------------- refusals
def test_trim_with_end_before_start_is_refused(ops, source):
    with pytest.raises(MediaOpsError):
        ops.run({"operation": "TRIM", "args": {"input": source, "output": _out("x.mp4"),
                                               "start_s": 1.5, "end_s": 0.5}})


def test_a_path_outside_the_safe_root_is_refused(ops):
    with pytest.raises(MediaOpsError):
        ops.run({"operation": "PROBE", "args": {"input": "/tmp/some.mp4"}})


def test_a_protected_path_is_refused(ops):
    with pytest.raises(MediaOpsError):
        ops.run({"operation": "PROBE",
                 "args": {"input": str(SAFE_ROOT) + "/share/evaluation_examples/x.mp4"}})


def test_an_unknown_operation_is_refused(ops, source):
    with pytest.raises(MediaOpsError):
        ops.run({"operation": "DEEPFRY", "args": {"input": source}})
