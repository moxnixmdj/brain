#!/usr/bin/env python3
import importlib.util, pathlib, sys, unittest
from unittest import mock

CANONICAL_ROOT=pathlib.Path(__file__).resolve().parents[1]
PATH=CANONICAL_ROOT/"runtime"/"capability_discovery.py"
spec=importlib.util.spec_from_file_location("semantic_discovery_repair_target",PATH)
discovery=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=discovery
spec.loader.exec_module(discovery)

class R:
    returncode=0
    stderr=""
    stdout=""

def run_for(search_map):
    def fake_run(argv,text=True,capture_output=True,timeout=None):
        r=R()
        if argv[:2]==["apt-cache","search"]:
            r.stdout=search_map.get(argv[2],"")
        elif argv[:2]==["apt-cache","policy"]:
            name=argv[2]
            r.stdout=f"{name}:\n  Candidate: 1.0\n"
        elif argv[:2]==["apt-cache","show"]:
            r.stdout="Package: x\nSHA256: "+"a"*64+"\n"
        return r
    return fake_run

class SemanticExecutableRankingRepairTests(unittest.TestCase):
    def test_query_strips_syntax_noise_and_keeps_domain_noun(self):
        q=discovery.effect_queries(
          "Resize a PNG image to exactly 64 by 64 pixels and save the result "
          "at canonical/astra_runtime/tmp/DIAG_RESIZED.png."
        )
        self.assertIn("resize",q)
        self.assertIn("png",q)
        self.assertIn("image",q)
        self.assertNotIn("at",q)
        self.assertNotIn("exactly",q)
        self.assertNotIn("result",q)

    def test_sqlite_cli_outranks_backends_and_bindings(self):
        lines="\n".join([
          "elpa-emacsql-sqlite - high level SQL database frontend for Emacs (SQLite backend)",
          "kamailio-sqlite-modules - SQLite database connectivity module for the Kamailio SIP server",
          "sqlite3 - Command line interface for SQLite 3",
        ])+"\n"
        with mock.patch.object(discovery.shutil,"which",return_value="/usr/bin/apt-cache"), \
             mock.patch.object(discovery.subprocess,"run",side_effect=run_for({"sqlite":lines,"database":lines,"table":lines,"probe":lines,"rows":lines})), \
             mock.patch.object(discovery.sys,"platform","linux"):
            out=discovery.search_apt_packages("Create a SQLite database containing a table named probe with two rows",limit=20)
        self.assertEqual(out["candidates"][0]["name"],"sqlite3")

    def test_direct_graph_tool_outranks_editor_mode(self):
        lines="\n".join([
          "elpa-graphviz-dot-mode - Emacs mode for the dot-language used by graphviz.",
          "graphviz - rich set of graph drawing tools",
          "codecgraph - Generates graphviz graphs from HDA-Intel codec information",
        ])+"\n"
        search={k:lines for k in ("render","graphviz","dot","graph","png","image")}
        with mock.patch.object(discovery.shutil,"which",return_value="/usr/bin/apt-cache"), \
             mock.patch.object(discovery.subprocess,"run",side_effect=run_for(search)), \
             mock.patch.object(discovery.sys,"platform","linux"):
            out=discovery.search_apt_packages("Render a Graphviz DOT graph into a PNG image",limit=20)
        self.assertEqual(out["candidates"][0]["name"],"graphviz")

    def test_image_domain_noun_surfaces_imagemagick(self):
        lines="\n".join([
          "famfamfam-flag-png - Free collection of countries' flags",
          "hunspell-de-at - Austrian dictionary for hunspell",
          "imagemagick - image manipulation programs -- binaries",
        ])+"\n"
        search={k:lines for k in ("resize","png","pixels","image","save")}
        with mock.patch.object(discovery.shutil,"which",return_value="/usr/bin/apt-cache"), \
             mock.patch.object(discovery.subprocess,"run",side_effect=run_for(search)), \
             mock.patch.object(discovery.sys,"platform","linux"):
            out=discovery.search_apt_packages("Resize a PNG image to 64 by 64 pixels and save it",limit=20)
        names=[x["name"] for x in out["candidates"]]
        self.assertIn("imagemagick",names)
        self.assertLess(names.index("imagemagick"),names.index("famfamfam-flag-png"))

if __name__=="__main__":
    unittest.main(verbosity=2)
