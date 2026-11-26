"""Only the two independently ordered text banks enter. No gold, categories or judge."""
import collections
import hashlib
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from canonical.runtime.brain_unified_model_v1 import open_model
from canonical.runtime.bound_capabilities import objective_relevance_bm25 as ranker


def key(text):return hashlib.sha256(text.encode()).hexdigest()


def capture(bank, queries):
    model=open_model(); op=model.clm_rrf_memory_op
    k=5; limit=5*max(map(len,bank),default=0)+32
    queries=[(key(q),{'query':q,'top_k':k,'char_budget':limit}) for q in queries]
    t0=time.monotonic()
    def answers():
        out={}
        for qid,spec in queries:
            r=op('RETRIEVE_4WAY_RRF_BUDGETED',spec)
            if r.get('tampered_excluded'):raise ValueError('unexpected corrupt measurement')
            out[qid]=[v['record_id'] for v in r['results']]
        return out
    empty=answers();t1=time.monotonic(); writes=collections.Counter()
    ids=[key(text) for text in bank]
    for ident,text in zip(ids,bank):
        r=op('WRITE_SURPRISE_GATED',{'record_id':ident,'key':ident,'verbatim_text':text,
                                     'origin_token':'USER_DIRECT','min_surprise':0,'valid_from':1})
        writes[r['status']]+=1
    t2=time.monotonic();rrf=answers();t3=time.monotonic()
    docs=[ranker._tokens(t) for t in bank];bm25={}
    for qid,spec in queries:
        scores=ranker._bm25_scores(ranker._tokens(spec['query']),docs)
        order=sorted(zip(ids,scores),key=lambda r:(-(r[1][0] if isinstance(r[1],tuple) else r[1]),r[0]))
        bm25[qid]=[i for i,v in order[:k] if (v[0] if isinstance(v,tuple) else v)>0]
    return {'writes':writes,'seconds':{'empty':t1-t0,'write':t2-t1,'rrf':t3-t2,'bm25':time.monotonic()-t3},
            'bank_bytes':sum(len(t.encode()) for t in bank),'char_budget':limit,'empty':empty,'rrf':rrf,'bm25':bm25}


if __name__=='__main__':
    packet=json.load(sys.stdin)
    if set(packet)!={'bank','queries'}:raise ValueError('unexpected content')
    print(json.dumps(capture(**packet),separators=(',',':')))
