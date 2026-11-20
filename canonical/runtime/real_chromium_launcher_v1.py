"""Launch real Chromium with a CDP debugging endpoint for browser automation.

Downloads the @sparticuz/chromium headless server binary (built for Linux
servers, no GPU required), inflates its bundled SwiftShader and AL2023
shared libraries (Brotli decompression via Node.js), and launches Chromium
with --remote-debugging-port so Playwright can connect via connect_over_cdp.

Zero model calls, zero network calls at runtime (the npm download happens
once at setup; the binary is then reused). The GPU/Vulkan/EGL crash in this
sandbox only kills the GPU process, not the browser process: CDP, page
navigation, clicking, typing and AX tree access all work through the browser
process.

Usage:
    from canonical.runtime.real_chromium_launcher_v1 import launch_chromium
    endpoint = launch_chromium(port=9222)
    # endpoint == "http://localhost:9222" — pass to BrowserCDP or to
    # playwright p.chromium.connect_over_cdp(endpoint)
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import time
import urllib.error
import urllib.request

PACKAGE_NAME = "@sparticuz/chromium"
# The npm scoped package directory keeps the @ prefix: node_modules/@sparticuz/chromium
NODE_MODULES = pathlib.Path("node_modules")
PACKAGE_DIR = NODE_MODULES / PACKAGE_NAME
BIN_DIR = PACKAGE_DIR / "bin"
NSS_STUB_DIR = pathlib.Path("canonical/runtime/nss_stubs")

CHROMIUM_ARGS = [
    "--headless=new",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--disable-software-rasterizer",
    "--disable-vulkan",
    "--use-gl=disabled",
    "--disable-gpu-vsync",
    "--disable-frame-rate-limit",
    "--no-first-run",
    "--no-default-browser-check",
    "--mute-audio",
    "--font-render-hinting=none",
    "--force-device-scale-factor=1",
    "--disable-features=Translate,BackForwardCache,VizDisplayCompositor",
]

_INFLATE_JS = r"""
const fs = require('fs');
const zlib = require('zlib');
const br = process.argv[2];
const out = process.argv[3];
fs.writeFileSync(out, zlib.brotliDecompressSync(fs.readFileSync(br)));
"""


def _ensure_package() -> None:
    """Download @sparticuz/chromium via npm if not already present."""
    if PACKAGE_DIR.is_dir():
        return
    NODE_MODULES.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["npm", "install", PACKAGE_NAME, "--no-save"],
        check=True,
        capture_output=True,
        timeout=180,
    )


def _inflate_br(br_path: pathlib.Path, out_path: pathlib.Path) -> None:
    """Brotli-decompress a .br file using Node.js zlib (Python zlib lacks Brotli)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    js_path = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "brain_inflate.js"
    js_path.write_text(_INFLATE_JS)
    subprocess.run(
        ["node", str(js_path), str(br_path), str(out_path)],
        check=True,
        capture_output=True,
        timeout=60,
    )


def _extract_tar(tar_path: pathlib.Path, dest_dir: pathlib.Path) -> None:
    """Extract a tar archive using the system tar."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["tar", "-xf", str(tar_path), "-C", str(dest_dir)], check=True)


def _prepare_runtime() -> dict[str, pathlib.Path]:
    """Inflate Chromium binary and bundled libraries. Returns paths."""
    _ensure_package()

    tmp = pathlib.Path(os.environ.get("TMPDIR", "/tmp"))
    chromium_exe = tmp / "brain_chromium"
    if not chromium_exe.exists():
        _inflate_br(BIN_DIR / "chromium.br", chromium_exe)
        chromium_exe.chmod(0o755)

    swift_dir = tmp / "brain_swiftshader"
    if not (swift_dir / "libvk_swiftshader.so").exists():
        swift_tar = swift_dir / "swiftshader.tar"
        _inflate_br(BIN_DIR / "swiftshader.tar.br", swift_tar)
        _extract_tar(swift_tar, swift_dir)

    al2023_dir = tmp / "brain_al2023"
    if not (al2023_dir / "lib").exists():
        al_tar = al2023_dir / "al2023.tar"
        _inflate_br(BIN_DIR / "al2023.tar.br", al_tar)
        _extract_tar(al_tar, al2023_dir)

    fonts_dir = tmp / "brain_fonts"
    if not fonts_dir.exists():
        fonts_tar = fonts_dir / "fonts.tar"
        _inflate_br(BIN_DIR / "fonts.tar.br", fonts_tar)
        _extract_tar(fonts_tar, fonts_dir)

    return {
        "chromium": chromium_exe,
        "swift": swift_dir,
        "al2023": al2023_dir,
        "fonts": fonts_dir,
    }


def _collect_so_dirs(root: pathlib.Path) -> list[str]:
    """Collect directories containing .so files under root."""
    dirs: set[str] = set()
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(".so"):
                dirs.add(dirpath)
                break
    return sorted(dirs)


def launch_chromium(
    port: int = 9222,
    user_data_dir: str | pathlib.Path | None = None,
    timeout_s: int = 30,
) -> str:
    """Launch real Chromium with a CDP debugging endpoint.

    Returns the CDP endpoint URL (e.g. "http://localhost:9222") suitable for
    BrowserCDP.bind_environment or Playwright connect_over_cdp.

    Raises RuntimeError if Chromium fails to start or the CDP port does not
    become available within timeout_s.
    """
    paths = _prepare_runtime()

    if user_data_dir is None:
        user_data_dir = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "brain_chromium_profile"
    user_data_dir = pathlib.Path(user_data_dir)
    user_data_dir.mkdir(parents=True, exist_ok=True)

    so_dirs: list[str] = []
    for d in (paths["swift"], paths["al2023"]):
        so_dirs.extend(_collect_so_dirs(d))

    nss_stub = NSS_STUB_DIR if NSS_STUB_DIR.is_dir() else None
    ld_parts = so_dirs + [str(pathlib.Path(os.environ.get("TMPDIR", "/tmp")))]
    if nss_stub:
        ld_parts.append(str(nss_stub))
    if os.environ.get("LD_LIBRARY_PATH"):
        ld_parts.append(os.environ["LD_LIBRARY_PATH"])

    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = ":".join(ld_parts)
    env["FONTCONFIG_PATH"] = str(paths["fonts"] / "fonts")

    args = [
        str(paths["chromium"]),
        *CHROMIUM_ARGS,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "about:blank",
    ]

    proc = subprocess.Popen(args, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"Chromium exited early with code {proc.returncode}")
        try:
            urllib.request.urlopen(f"http://localhost:{port}/json/version", timeout=1)
            return f"http://localhost:{port}"
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            time.sleep(0.25)

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    raise RuntimeError(f"Chromium CDP port {port} did not become available within {timeout_s}s")


def stop_chromium(port: int = 9222) -> None:
    """Best-effort stop of a Chromium launched on the given CDP port."""
    try:
        urllib.request.urlopen(f"http://localhost:{port}/json/close", timeout=2)
    except Exception:
        pass
