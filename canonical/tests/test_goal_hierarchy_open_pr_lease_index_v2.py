from __future__ import annotations

import json
import unittest

from canonical.runtime import enforce_goal_hierarchy as guard


def _node(number, *, intent=False, deleted=False, has_more_files=False):
    files=[]
    if intent:
        files.append({
            "path":f"canonical/action_intents/{number}.json",
            "changeType":"DELETED" if deleted else "ADDED",
        })
    return {
        "number":number,
        "headRefOid":f"{number:040x}"[-40:],
        "files":{
            "pageInfo":{
                "hasNextPage":has_more_files,
                "endCursor":"files-next" if has_more_files else None,
            },
            "nodes":files,
        },
    }


class FakeApis:
    def __init__(self,pages,intents,rest_files=None):
        self.pages=list(pages)
        self.intents=dict(intents)
        self.rest_files=dict(rest_files or {})
        self.page_calls=0
        self.blob_calls=0
        self.rest_calls=0

    def graphql(self,query,variables):
        if "pullRequests(" in query:
            page=self.pages[self.page_calls]
            self.page_calls+=1
            return {"repository":{"pullRequests":page}}
        self.blob_calls+=1
        repo={}
        i=0
        while f"i{i}: object(" in query:
            marker=f"i{i}: object(expression:"
            start=query.index(marker)+len(marker)
            expr,_=json.JSONDecoder().raw_decode(query[start:])
            head,path=expr.split(":",1)
            number=int(head,16)
            repo[f"i{i}"]={
                "text":json.dumps(self.intents[(number,path)]),
                "isBinary":False,
            }
            i+=1
        return {"repository":repo}

    def rest(self,path):
        self.rest_calls+=1
        number=int(path.split("/pulls/")[1].split("/")[0])
        page=int(path.rsplit("page=",1)[1])
        return self.rest_files.get((number,page),[])


class CompleteOpenPRLeaseIndexTests(unittest.TestCase):
    def test_second_page_intent_is_visible(self):
        first=[_node(i) for i in range(1,101)]
        second=[_node(101,intent=True)]
        pages=[
            {"pageInfo":{"hasNextPage":True,"endCursor":"c1"},"nodes":first},
            {"pageInfo":{"hasNextPage":False,"endCursor":None},"nodes":second},
        ]
        path="canonical/action_intents/101.json"
        fake=FakeApis(pages,{(101,path):{"blocker_lease_key":"SECOND_PAGE"}})
        out=guard._open_pr_intents_from_apis(
            fake.graphql,fake.rest,"moxnixmdj/brain",999
        )
        self.assertEqual(len(out),1)
        self.assertEqual(out[0]["pr"],101)
        self.assertEqual(out[0]["intent"]["blocker_lease_key"],"SECOND_PAGE")
        self.assertEqual(fake.page_calls,2)

    def test_current_pr_and_deleted_intent_are_excluded(self):
        pages=[{
            "pageInfo":{"hasNextPage":False,"endCursor":None},
            "nodes":[
                _node(5,intent=True),
                _node(6,intent=True,deleted=True),
                _node(7,intent=True),
            ],
        }]
        fake=FakeApis(
            pages,
            {
                (5,"canonical/action_intents/5.json"):{"x":5},
                (7,"canonical/action_intents/7.json"):{"x":7},
            },
        )
        out=guard._open_pr_intents_from_apis(
            fake.graphql,fake.rest,"moxnixmdj/brain",5
        )
        self.assertEqual([x["pr"] for x in out],[7])

    def test_large_pr_uses_paginated_rest_file_fallback(self):
        pages=[{
            "pageInfo":{"hasNextPage":False,"endCursor":None},
            "nodes":[_node(8,has_more_files=True)],
        }]
        path="canonical/action_intents/8.json"
        first=[
            {"filename":f"other/{i}.txt","status":"modified"}
            for i in range(100)
        ]
        second=[{"filename":path,"status":"added"}]
        fake=FakeApis(
            pages,
            {(8,path):{"blocker_lease_key":"LARGE"}},
            {(8,1):first,(8,2):second},
        )
        out=guard._open_pr_intents_from_apis(
            fake.graphql,fake.rest,"moxnixmdj/brain",99
        )
        self.assertEqual(out[0]["intent"]["blocker_lease_key"],"LARGE")
        self.assertEqual(fake.rest_calls,2)

    def test_invalid_blob_fails_closed(self):
        pages=[{
            "pageInfo":{"hasNextPage":False,"endCursor":None},
            "nodes":[_node(10,intent=True)],
        }]

        def graphql(query,variables):
            if "pullRequests(" in query:
                return {"repository":{"pullRequests":pages[0]}}
            return {"repository":{"i0":{"text":"{","isBinary":False}}}

        with self.assertRaises(RuntimeError):
            guard._open_pr_intents_from_apis(
                graphql,lambda path:[],"moxnixmdj/brain",99
            )


if __name__=="__main__":
    unittest.main(verbosity=2)
