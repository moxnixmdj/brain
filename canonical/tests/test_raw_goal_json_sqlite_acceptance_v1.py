from __future__ import annotations
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import raw_goal_json_sqlite_acceptance_v1 as a


def _goal():
    return (
        "Read canonical/tmp/SOURCE.json. "
        "Create canonical/tmp/OUT.sqlite as a SQLite table named records "
        "with columns capability_id, name, status, and count containing every READY_STATUS."
    )

def _source():
    return {"rows":{
        "b":{"name":"Beta","status":"OTHER","count":2},
        "a":{"name":"Alpha","status":"READY_STATUS","count":1},
        "c":{"name":"Gamma","status":"READY_STATUS","count":3},
    }}

def _make_db(path: Path,pf):
    conn=sqlite3.connect(str(path))
    try:
        cols=", ".join('"'+c+'" TEXT NOT NULL' for c in pf["columns"])
        conn.execute(f'CREATE TABLE "{pf["table_name"]}" ({cols})')
        marks=",".join("?" for _ in pf["columns"])
        conn.executemany(f'INSERT INTO "{pf["table_name"]}" VALUES ({marks})',pf["expected_rows"])
        conn.commit()
    finally:
        conn.close()

def _raw(goal,root):
    pf=a.preflight(goal,root=root)
    contract=a.compile_contract(goal,source_id="user",routing_target_effects=[a.ROUTING_EFFECT])
    return {
        "pass":True,
        "compiler_mode":"DETERMINISTIC_COMPOUND_ACTION_PLAN",
        "raw_goal_sha256":pf["goal_sha256"],
        "raw_task_contract_sha256":contract["task_contract_sha256"],
        "raw_source_coverage_complete":True,
        "raw_acceptance_obligation_count":len(contract["acceptance_contract"]["obligations"]),
        "controller_action_count":3,
        "model_dependency_count":0,
        "cognition_dependency_class":"MODEL_INDEPENDENT",
        "controller_execution":{
            "returncode":0,"controller_mode":"MODEL_INDEPENDENT_ACTION_PLAN",
            "final_summary":"COMPOUND_GOAL_COMPLETE",
            "trace":[
                {"cycle":0,"plan":{"type":"read_file","args":{"path":pf["input_path"]},
                 "expect":{"type":"field_nonempty","field":"content"}},"result":{"content":"source"}},
                {"cycle":1,"plan":{"type":"invoke_capability","args":{
                    "capability_id":a.CAPABILITY,
                    "goal":"Create canonical/tmp/OUT.sqlite as a SQLite table named records containing every READY_STATUS with columns capability_id, name, status, and count",
                    "json_path":pf["input_path"],"output_path":pf["output_path"]},
                    "expect":{"type":"field_equals","field":"output_verified","value":True}},
                 "result":{"output_verified":True,"table_name":pf["table_name"],
                           "columns":pf["columns"],"row_count":len(pf["expected_rows"])}},
                {"cycle":2,"plan":{"type":"finish","args":{"summary":"COMPOUND_GOAL_COMPLETE"}},
                 "result":{"summary":"COMPOUND_GOAL_COMPLETE"}},
            ],
        },
    }


class JsonSqliteAcceptanceTests(unittest.TestCase):
    def _root(self):
        td=tempfile.TemporaryDirectory()
        root=Path(td.name)
        src=root/"canonical/tmp/SOURCE.json"
        src.parent.mkdir(parents=True)
        src.write_text(json.dumps(_source()),encoding="utf-8")
        return td,root,src

    def test_exact_relation_passes(self):
        td,root,src=self._root()
        with td:
            pf=a.preflight(_goal(),root=root)
            self.assertTrue(pf["matched"],pf)
            _make_db(root/pf["output_path"],pf)
            out=a.verify(goal=_goal(),raw_result=_raw(_goal(),root),root=root)
            self.assertTrue(out["pass"],out)
            self.assertTrue(out["relation_exact"])

    def test_tampered_row_fails(self):
        td,root,src=self._root()
        with td:
            pf=a.preflight(_goal(),root=root)
            _make_db(root/pf["output_path"],pf)
            conn=sqlite3.connect(str(root/pf["output_path"]))
            try:
                conn.execute('UPDATE "records" SET "count"="999" WHERE "capability_id"="a"')
                conn.commit()
            finally:
                conn.close()
            out=a.verify(goal=_goal(),raw_result=_raw(_goal(),root),root=root)
            self.assertFalse(out["pass"])
            self.assertFalse(out["relation_exact"])

    def test_extra_table_fails(self):
        td,root,src=self._root()
        with td:
            pf=a.preflight(_goal(),root=root)
            _make_db(root/pf["output_path"],pf)
            conn=sqlite3.connect(str(root/pf["output_path"]))
            try:
                conn.execute('CREATE TABLE "extra" ("x" TEXT NOT NULL)')
                conn.commit()
            finally:
                conn.close()
            out=a.verify(goal=_goal(),raw_result=_raw(_goal(),root),root=root)
            self.assertFalse(out["pass"])
            self.assertIn("TABLE_SET_MISMATCH",out.get("reason",""))

    def test_nested_collection_not_admitted(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=root/"canonical/tmp/SOURCE.json"; src.parent.mkdir(parents=True)
            src.write_text(json.dumps({"rows":{"a":{"status":"READY_STATUS","nested":{"x":1}}}}),encoding="utf-8")
            out=a.preflight(_goal(),root=root)
            self.assertFalse(out["matched"])

    def test_ambiguous_collections_not_admitted(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); src=root/"canonical/tmp/SOURCE.json"; src.parent.mkdir(parents=True)
            src.write_text(json.dumps({
                "left":{"a":{"status":"READY_STATUS","name":"A","count":1}},
                "right":{"b":{"status":"READY_STATUS","name":"B","count":2}},
            }),encoding="utf-8")
            out=a.preflight(_goal(),root=root)
            self.assertFalse(out["matched"])
            self.assertIn("MATCHING_COLLECTION_NOT_UNIQUE",out.get("reason",""))

    def test_source_drift_rejected_by_original_preflight_binding(self):
        td,root,src=self._root()
        with td:
            pf=a.preflight(_goal(),root=root)
            _make_db(root/pf["output_path"],pf)
            raw=_raw(_goal(),root)
            changed=_source(); changed["rows"]["a"]["count"]=99
            src.write_text(json.dumps(changed),encoding="utf-8")
            accepted=a.verify(goal=_goal(),raw_result=raw,root=root)
            self.assertFalse(accepted["pass"])

    def test_extra_instruction_not_matched(self):
        td,root,src=self._root()
        with td:
            out=a.preflight(_goal()+" Then email it.",root=root)
            self.assertFalse(out["matched"])

if __name__=="__main__":
    unittest.main(verbosity=2)
