"""Small streaming reader for explicitly stated slot values and conditionals.

Consumes conversation *text*, not an entity graph. Deliberately leaves
paraphrases, multi-value questions and unstated dependencies unresolved. Neither
a transcript search nor a synthetic graph benchmark. All facts/rules on disk.
"""
from __future__ import annotations

import re
from canonical.swe_kernel.witnessed_revision_store_v1 import RevisionStore

_OWNER = r'(?:my|our|the)\s+'
_KEY = r'([\w-]+(?:\s+[\w-]+){0,5}?)'
_ASSIGN = re.compile(r'(?:^|,\s*)'+_OWNER+_KEY+r'\s+(?:is|was changed to|changed to|has become)\s+(?:now\s+)?(.+)$', re.I)
_REMOVE = re.compile(r'(?:^|\bplease\s+)(?:forget|delete|remove)\s+'+_OWNER+_KEY+r'$',re.I)
_COND = re.compile('^if '+_OWNER+_KEY+r'\s+(?:is|changes to|becomes)\s+(.+?),\s*(?:then\s+)?'+_OWNER+_KEY+r'\s+(?:is|will be|becomes)\s+(.+)$', re.I)
_STOP = set('what when where which is are was were the my our your me i have of a an now current currently can you tell latest about to for in at as it be do does did and would should'.split())


def _key(s):
    return ' '.join(s.casefold().split())


def _value(s):
    return s.strip().strip('"\'“”')


def _tokens(s):
    return set(re.findall(r'[\w-]+',s.casefold()))-_STOP


class DialogueReader:
    def __init__(self,path):
        self.store=RevisionStore(path)

    def ingest(self, role, text, *, turn, source):
        if role != 'user': return 0  # an assistant suggestion is not a user's assertion
        count=0
        for sentence in re.split(r'(?<=[.?!;])\s+|\n+',text):
            s=sentence.strip().rstrip('.;!').strip()
            if not s or len(s)>400 or s.endswith('?'): continue
            kw=dict(valid_from=turn,source=source,witness=sentence.strip())
            if m:=_COND.fullmatch(s):
                key, trigger, head, value=m.groups()
                rule=[_key(key),_value(trigger),_key(head),_value(value)]
                self.store.append('set','rule:'+repr(rule),value=rule,**kw); count+=1
            elif m:=_REMOVE.fullmatch(s):
                self.store.append('delete','fact:'+_key(m[1]),**kw);count+=1
            elif m:=_ASSIGN.search(s):
                key,value=_key(m[1]),_value(m[2]); root='fact:'+key
                fact=self.store.append('set',root,value=value,**kw);count+=1
                # Only fire rules actually uttered before this update. An old
                # conclusion depends on that exact version; never infer its replacement.
                pending=[(key,value,fact['id'])]; fired=set()
                while pending:
                    slot,val,parent=pending.pop()
                    for rk in self.store.keys('rule:'):
                        if rk in fired: continue
                        row=self.store.query(rk,valid_at=turn)
                        if row['status']!='SUPPORTED':continue
                        dep,trigger,head,replacement=row['value']
                        if dep!=slot or _key(trigger)!=_key(val):continue
                        fired.add(rk)
                        self.store.append('delete','fact:'+head,**kw)
                        entry=self.store.append('derive','fact:'+head,value=replacement,
                                 parents=[parent,row['support'][0]['id']],**kw)
                        pending.append((head,replacement,entry['id']));count+=1
        return count

    def answer(self, question):
        q=_tokens(question);ranked=[]
        for name in self.store.keys('fact:'):
            t=_tokens(name[5:]); hits=len(t&q)
            if hits and hits==len(t):ranked.append((hits,name))
        ranked.sort(reverse=True)
        if not ranked or (len(ranked)>1 and ranked[0][0]==ranked[1][0]):
            return {'answer':'Uncertain','status':'NO_UNIQUE_SLOT'}
        row=self.store.query(ranked[0][1]);status=row['status']
        return {'answer':str(row['value']) if status=='SUPPORTED' else 'Uncertain',
                'status':status,'key':ranked[0][1],'evidence_ids':[r['id'] for r in row['support']]}
