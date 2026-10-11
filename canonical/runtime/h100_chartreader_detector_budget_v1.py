from __future__ import annotations
from dataclasses import dataclass

BUDGET=100_000_000

@dataclass(frozen=True)
class S:
    matrix:int=0
    vector:int=0
    buffers:int=0
    qchannels:int=0
    convs:int=0
    def __add__(self,o):
        return S(self.matrix+o.matrix,self.vector+o.vector,self.buffers+o.buffers,self.qchannels+o.qchannels,self.convs+o.convs)
    def mul(self,n:int):
        return S(self.matrix*n,self.vector*n,self.buffers*n,self.qchannels*n,self.convs*n)

def conv(inp,out,k,bn=True):
    # weight matrix; bias only when BN absent. BN carries gamma,beta plus running mean/var and int64 num_batches.
    return S(inp*out*k*k, 2*out if bn else out, (2*out*4+8) if bn else 0, out, 1)

def rawconv(inp,out,k,bias=True):
    return S(inp*out*k*k, out if bias else 0, 0, out, 1)

def residual(inp,out,stride=1):
    s=rawconv(inp,out,3,False)+S(0,2*out,2*out*4+8,0,0)
    s=s+rawconv(out,out,3,False)+S(0,2*out,2*out*4+8,0,0)
    if stride!=1 or inp!=out:
        s=s+rawconv(inp,out,1,False)+S(0,2*out,2*out*4+8,0,0)
    return s

def layer(inp,out,modules):
    s=residual(inp,out)
    for _ in range(1,modules): s=s+residual(out,out)
    return s

def hg_down(inp,out,modules):
    s=residual(inp,out,2)
    for _ in range(modules-1): s=s+residual(out,out)
    return s

def layer_revr(inp,out,modules):
    s=S()
    for _ in range(modules-1): s=s+residual(inp,inp)
    return s+residual(inp,out)

D=[256,256,384,384,384,512]
M=[2,2,2,2,2,4]
def hourglass(n,dims=D,mods=M):
    cur,nxt=dims[0],dims[1]; cm,nm=mods[0],mods[1]
    s=layer(cur,cur,cm)+hg_down(cur,nxt,cm)
    s=s+(hourglass(n-1,dims[1:],mods[1:]) if n>1 else layer(nxt,nxt,nm))
    return s+layer_revr(nxt,cur,cm)

def head(outdim):
    return conv(256,256,3,False)+rawconv(256,outdim,1,True)

def detector(nstack):
    s=conv(3,128,7,True)+residual(128,256,2)
    s=s+hourglass(5).mul(nstack)
    s=s+conv(256,256,3,True).mul(nstack)
    s=s+conv(256,256,3,True).mul(2*nstack)
    s=s+head(3).mul(2*nstack)+head(2).mul(2*nstack)
    if nstack>1:
        s=s+residual(256,256).mul(nstack-1)
        bridge=(rawconv(256,256,1,False)+S(0,2*256,2*256*4+8,0,0)).mul(2*(nstack-1))
        s=s+bridge
    return s

def grouping_tail():
    d=260; ff=1024; layers=6
    # qkv, attention output, FF1, FF2 matrices
    matrix=(3*d*d+d*d+ff*d+d*ff)*layers + d*64 + 64*2
    # qkv/out/FF biases + two LayerNorm affine pairs; classifier biases
    vector=(3*d+d+ff+d+4*d)*layers + 64+2
    qchannels=(3*d+d+ff+d)*layers + 64+2
    return S(matrix,vector,0,qchannels,0)

def storage(s,bits):
    packed=(s.matrix*bits+7)//8
    return packed+s.vector*4+s.buffers+s.qchannels*4+s.qchannels*4

FIRST=detector(1)
FULL=detector(2)
GROUP=FULL+grouping_tail()

RESULT={
 "first":FIRST.__dict__,
 "full":FULL.__dict__,
 "group":GROUP.__dict__,
 "first_q4_bytes":storage(FIRST,4),
 "first_int8_bytes":storage(FIRST,8),
 "full_q4_bytes":storage(FULL,4),
 "group_q4_bytes":storage(GROUP,4),
 "first_q4_headroom":BUDGET-storage(FIRST,4),
 "first_int8_headroom":BUDGET-storage(FIRST,8),
 "full_q4_headroom":BUDGET-storage(FULL,4),
 "group_q4_over":storage(GROUP,4)-BUDGET,
}
if __name__=="__main__":
 import json; print(json.dumps(RESULT,indent=2,sort_keys=True))
