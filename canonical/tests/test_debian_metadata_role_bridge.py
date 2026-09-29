import importlib.util
import pathlib

ROOT=pathlib.Path(__file__).resolve().parents[2]
MOD=ROOT/"canonical"/"runtime"/"capability_discovery.py"

def load_module():
    spec=importlib.util.spec_from_file_location("capability_discovery_role_test",MOD)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod._APT_PACKAGE_METADATA_CACHE=None
    mod._APT_EXECUTABLE_PATHS_CACHE={}
    return mod

class Result:
    def __init__(self,stdout="",stderr="",returncode=0):
        self.stdout=stdout
        self.stderr=stderr
        self.returncode=returncode

DUMP="""Package: opaque-converter
Description: general purpose command line utility
Tag: role::program, interface::commandline, use::converting, works-with::image:raster, works-with-format::svg

Package: opaque-sync
Description: general purpose network utility
Tag: role::program, interface::commandline, use::synchronizing, network::client, works-with::file

Package: opaque-speech
Description: general purpose accessibility utility
Tag: role::program, interface::commandline, sound::speech, works-with::audio

Package: misleading-lib
Description: raster conversion helper library
Tag: role::shared-lib, works-with::image:raster, use::converting
"""

def fake_which(name):
    return "/usr/bin/"+name if name in {"apt-cache","apt-file"} else None

def fake_run(argv,**kwargs):
    if argv[:2]==["apt-cache","dumpavail"]:
        return Result(DUMP)
    if argv[:2]==["apt-file","list"]:
        package=argv[2]
        files={
            "opaque-converter":"opaque-converter: /usr/bin/zz-convert\n",
            "opaque-sync":"opaque-sync: /usr/bin/zz-sync\n",
            "opaque-speech":"opaque-speech: /usr/bin/zz-say\n",
            "misleading-lib":"",
        }
        return Result(files.get(package,""))
    if argv[:2]==["apt-cache","policy"]:
        return Result("  Candidate: 1.0\n")
    raise AssertionError("unexpected subprocess: "+repr(argv))

def test_debian_use_and_format_tags_bridge_opaque_names(monkeypatch):
    d=load_module()
    monkeypatch.setattr(d.shutil,"which",fake_which)
    monkeypatch.setattr(d.subprocess,"run",fake_run)
    result=d.search_apt_packages(
        "Convert a raster picture into scalable vector graphics.",
        limit=10,
    )
    assert result["candidates"][0]["name"]=="opaque-converter"
    assert result["candidates"][0]["evidence_tier"]=="SEMANTIC_PACKAGE_EXECUTABLE_OWNERSHIP"

def test_synchronizing_role_tag_bridges_morphology(monkeypatch):
    d=load_module()
    monkeypatch.setattr(d.shutil,"which",fake_which)
    monkeypatch.setattr(d.subprocess,"run",fake_run)
    result=d.search_apt_packages(
        "Synchronize files to a remote machine efficiently.",
        limit=10,
    )
    assert result["candidates"][0]["name"]=="opaque-sync"

def test_shared_library_role_does_not_outrank_verified_program(monkeypatch):
    d=load_module()
    monkeypatch.setattr(d.shutil,"which",fake_which)
    monkeypatch.setattr(d.subprocess,"run",fake_run)
    result=d.search_apt_packages(
        "Convert a raster image into SVG.",
        limit=10,
    )
    names=[x["name"] for x in result["candidates"]]
    assert names[0]=="opaque-converter"
    assert "misleading-lib" not in names or names.index("misleading-lib")>0

def test_speech_tag_is_semantic_evidence(monkeypatch):
    d=load_module()
    monkeypatch.setattr(d.shutil,"which",fake_which)
    monkeypatch.setattr(d.subprocess,"run",fake_run)
    result=d.search_apt_packages(
        "Speak text aloud using synthesized speech.",
        limit=10,
    )
    assert result["candidates"][0]["name"]=="opaque-speech"
