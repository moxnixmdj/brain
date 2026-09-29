import importlib.util
import pathlib
import types

ROOT=pathlib.Path(__file__).resolve().parents[2]
MOD=ROOT/"canonical"/"runtime"/"capability_discovery.py"

def load_module():
    spec=importlib.util.spec_from_file_location("capability_discovery_semantic_test",MOD)
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

DUMP="""Package: opaque-alpha
Description: converts raster pictures into scalable vector graphics while preserving geometry and image structure

Package: vector-helper
Description: small vector file helper

Package: python3-rasterlib
Description: Python library for raster image utilities

Package: unrelated
Description: terminal calendar and clock
"""

def fake_which(name):
    return "/usr/bin/"+name if name in {"apt-cache","apt-file"} else None

def fake_run(argv,**kwargs):
    if argv[:2]==["apt-cache","dumpavail"]:
        return Result(DUMP)
    if argv[:2]==["apt-file","list"]:
        package=argv[2]
        files={
            "opaque-alpha":"opaque-alpha: /usr/bin/zzx\n",
            "vector-helper":"vector-helper: /usr/bin/vector-helper\n",
            "python3-rasterlib":"",
            "unrelated":"unrelated: /usr/bin/clocky\n",
        }
        return Result(files.get(package,""),returncode=0)
    if argv[:2]==["apt-cache","policy"]:
        return Result("  Candidate: 1.0\n")
    raise AssertionError("unexpected subprocess: "+repr(argv))

def test_semantic_package_can_win_with_opaque_package_and_binary_names(monkeypatch):
    d=load_module()
    monkeypatch.setattr(d.shutil,"which",fake_which)
    monkeypatch.setattr(d.subprocess,"run",fake_run)
    result=d.search_apt_packages(
        "Convert a raster image into scalable vector graphics while preserving geometry.",
        limit=10,
    )
    assert result["candidates"][0]["name"]=="opaque-alpha"
    assert result["candidates"][0]["evidence_tier"]=="SEMANTIC_PACKAGE_EXECUTABLE_OWNERSHIP"
    paths=result["candidates"][0]["executable_semantic_evidence"]["command_paths"]
    assert paths==["/usr/bin/zzx"]

def test_executable_name_overlap_is_not_a_hard_ranking_tier(monkeypatch):
    d=load_module()
    monkeypatch.setattr(d.shutil,"which",fake_which)
    monkeypatch.setattr(d.subprocess,"run",fake_run)
    result=d.search_apt_packages(
        "Convert a raster image into scalable vector graphics while preserving geometry.",
        limit=10,
    )
    names=[x["name"] for x in result["candidates"]]
    assert names.index("opaque-alpha") < names.index("vector-helper")

def test_apt_metadata_index_is_cached_across_queries(monkeypatch):
    d=load_module()
    monkeypatch.setattr(d.shutil,"which",fake_which)
    calls={"dump":0}
    def counted(argv,**kwargs):
        if argv[:2]==["apt-cache","dumpavail"]:
            calls["dump"]+=1
        return fake_run(argv,**kwargs)
    monkeypatch.setattr(d.subprocess,"run",counted)
    d.search_apt_packages("Convert raster pictures into vector graphics.",limit=5)
    d.search_apt_packages("Preserve image geometry during conversion.",limit=5)
    assert calls["dump"]==1
