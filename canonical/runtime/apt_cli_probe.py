#!/usr/bin/env python3
"""Read-only probe for a discovered APT CLI supplier.

Verifies exact package metadata, installs the requested pinned package, enumerates
installed executables, and captures bounded help text. It does not infer or run
a task-specific command.
"""
from __future__ import annotations
import json,pathlib,re,stat,subprocess,sys

class ProbeFailure(RuntimeError): pass

PKG_RE=re.compile(r"^[A-Za-z0-9][A-Za-z0-9+._-]{0,127}$")

def _run(argv,timeout=30):
    return subprocess.run(argv,text=True,capture_output=True,timeout=timeout)

def probe(package,version,sha256,root):
    if not sys.platform.startswith("linux"):
        raise ProbeFailure("APT_PLATFORM_REQUIRED")
    if not PKG_RE.fullmatch(package or ""):
        raise ProbeFailure("APT_PACKAGE_INVALID")
    if not version or not re.fullmatch(r"[0-9a-f]{64}",sha256 or ""):
        raise ProbeFailure("APT_METADATA_INCOMPLETE")
    show=_run(["apt-cache","show",f"{package}={version}"])
    if show.returncode!=0:
        raise ProbeFailure("APT_METADATA_NOT_FOUND")
    found=None
    for line in show.stdout.splitlines():
        if line.startswith("SHA256:"):
            found=line.split(":",1)[1].strip().lower(); break
    if found!=sha256.lower():
        raise ProbeFailure("APT_HASH_MISMATCH")
    install=_run(["sudo","apt-get","install","-y","--no-install-recommends",f"{package}={version}"],timeout=240)
    if install.returncode!=0:
        raise ProbeFailure("APT_INSTALL_FAILED:"+install.stderr[-1000:])
    listed=_run(["dpkg","-L",package])
    if listed.returncode!=0:
        raise ProbeFailure("APT_FILE_LIST_FAILED")
    executables=[]
    for raw in listed.stdout.splitlines():
        p=pathlib.Path(raw.strip())
        if not p.is_file():
            continue
        try:
            mode=p.stat().st_mode
        except OSError:
            continue
        if mode & (stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH) and str(p).startswith(("/usr/bin/","/bin/","/usr/sbin/","/sbin/")):
            executables.append(str(p))
    evidence=[]
    for exe in sorted(set(executables))[:16]:
        attempts=[]
        for flag in ("--help","-h"):
            p=_run([exe,flag],timeout=10)
            text=(p.stdout+"\n"+p.stderr).strip()[:10000]
            attempts.append({"flag":flag,"returncode":p.returncode,"text":text})
            if text:
                break
        evidence.append({"executable":exe,"help_attempts":attempts})
    return {
      "schema":"PROJECT_BRAIN_APT_CLI_PROBE_V1",
      "package":package,"version":version,"archive_sha256":sha256.lower(),
      "executables":evidence
    }

def main():
    if len(sys.argv)!=5:
        raise SystemExit("usage: apt_cli_probe.py PACKAGE VERSION SHA256 OUTPUT_JSON")
    package,version,sha,out=sys.argv[1:]
    result=probe(package,version,sha,pathlib.Path.cwd())
    p=pathlib.Path(out); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__": main()
