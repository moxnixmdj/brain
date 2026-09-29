import importlib.util
import pathlib

ROOT=pathlib.Path(__file__).resolve().parents[2]
MOD=ROOT/"canonical"/"runtime"/"capability_discovery.py"

def load_module():
    spec=importlib.util.spec_from_file_location("capability_discovery_debtags_test",MOD)
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

DUMP="""Package: opaque-beta
Description: general purpose command line utility
Tag: role::program, interface::commandline, use::converting, works-with::audio

Package: opaque-gamma
Description: generic document utility
Tag: role::program, use::{converting,viewing}, works-with-format::pdf

Package: name-overlap-helper
Description: audio helper library
Tag: role::shared-lib

Package: unrelated
Description: terminal calendar and clock
Tag: role::program, use::timekeeping
"""

def fake_which(name):
    return "/usr/bin/"+name if name in {"apt-cache","apt-file"} else None

def fake_run(argv,**kwargs):
    if argv[:2]==["apt-cache","dumpavail"]:
        return Result(DUMP)
    if argv[:2]==["apt-file","list"]:
        package=argv[2]
        files={
            "opaque-beta":"opaque-beta: /usr/bin/zzx\n",
            "opaque-gamma":"opaque-gamma: /usr/bin/qqx\n",
            "name-overlap-helper":"",
            "unrelated":"unrelated: /usr/bin/clocky\n",
        }
        return Result(files.get(package,""),returncode=0)
    if argv[:2]==["apt-cache","policy"]:
        return Result("  Candidate: 1.0\n")
    raise AssertionError("unexpected subprocess: "+repr(argv))

def test_debian_tag_semantics_admit_opaque_executable(monkeypatch):
    d=load_module()
    monkeypatch.setattr(d.shutil,"which",fake_which)
    monkeypatch.setattr(d.subprocess,"run",fake_run)
    result=d.search_apt_packages("Convert an audio recording to another audio format.",limit=10)
    assert result["candidates"][0]["name"]=="opaque-beta"
    assert result["candidates"][0]["evidence_tier"]=="SEMANTIC_PACKAGE_EXECUTABLE_OWNERSHIP"
    assert "convert" in result["candidates"][0]["matched_tag_terms"] or "audio" in result["candidates"][0]["matched_tag_terms"]

def test_compressed_debtags_braces_are_semantically_searchable(monkeypatch):
    d=load_module()
    monkeypatch.setattr(d.shutil,"which",fake_which)
    monkeypatch.setattr(d.subprocess,"run",fake_run)
    result=d.search_apt_packages("Convert and view a PDF document.",limit=10)
    assert result["candidates"][0]["name"]=="opaque-gamma"
    assert result["candidates"][0]["executable_semantic_evidence"]["command_paths"]==["/usr/bin/qqx"]

def test_name_overlap_without_executable_ownership_does_not_win(monkeypatch):
    d=load_module()
    monkeypatch.setattr(d.shutil,"which",fake_which)
    monkeypatch.setattr(d.subprocess,"run",fake_run)
    result=d.search_apt_packages("Convert an audio recording to another audio format.",limit=10)
    names=[x["name"] for x in result["candidates"]]
    assert names.index("opaque-beta") < names.index("name-overlap-helper")

def test_tag_metadata_index_is_cached(monkeypatch):
    d=load_module()
    monkeypatch.setattr(d.shutil,"which",fake_which)
    calls={"dump":0}
    def counted(argv,**kwargs):
        if argv[:2]==["apt-cache","dumpavail"]:
            calls["dump"]+=1
        return fake_run(argv,**kwargs)
    monkeypatch.setattr(d.subprocess,"run",counted)
    d.search_apt_packages("Convert audio.",limit=5)
    d.search_apt_packages("View PDF.",limit=5)
    assert calls["dump"]==1
