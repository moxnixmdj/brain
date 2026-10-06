from canonical.runtime import h100_reference_machine_u1_v1 as u

H=12
W=20
ROW=list(range(H))
COL=list(range(32,32+W))
PREV=100
COUNT=101
COLRUN=102
ROWRUN=103

class A:
    def __init__(self):
        self.p=[]; self.labels={}; self.fix=[]
    def e(self,op,imm=None):
        self.p.append((op,) if imm is None else (op,imm))
    def mark(self,name):
        self.labels[name]=len(self.p)
    def j(self,op,label):
        self.fix.append((len(self.p),op,label)); self.e(op,0)
    def done(self):
        p=list(self.p)
        for i,op,label in self.fix:
            p[i]=(op,self.labels[label])
        return p

def build_program():
    a=A()
    for y in range(H):
        for x in range(W):
            a.e("READ"); a.e("DUP")
            a.e("LOAD",ROW[y]); a.e("ADD"); a.e("STORE",ROW[y])
            a.e("LOAD",COL[x]); a.e("ADD"); a.e("STORE",COL[x])

    def count_runs(addrs,prefix,dest):
        a.e("PUSH",0); a.e("STORE",PREV)
        a.e("PUSH",0); a.e("STORE",COUNT)
        for i,addr in enumerate(addrs):
            no=f"{prefix}_no_{i}"; start=f"{prefix}_start_{i}"; done=f"{prefix}_done_{i}"
            a.e("PUSH",0); a.e("LOAD",addr); a.e("LT"); a.j("JZ",no)
            a.e("LOAD",PREV); a.j("JZ",start); a.j("JMP",done)
            a.mark(start)
            a.e("LOAD",COUNT); a.e("PUSH",1); a.e("ADD"); a.e("STORE",COUNT)
            a.e("PUSH",1); a.e("STORE",PREV); a.j("JMP",done)
            a.mark(no)
            a.e("PUSH",0); a.e("STORE",PREV)
            a.mark(done)
        a.e("LOAD",COUNT); a.e("STORE",dest)

    count_runs(COL,"c",COLRUN)
    count_runs(ROW,"r",ROWRUN)

    a.e("LOAD",ROWRUN); a.e("LOAD",COLRUN); a.e("LT"); a.j("JZ","horizontal")
    a.e("PUSH",0); a.e("WRITE"); a.e("LOAD",COLRUN); a.e("WRITE"); a.j("JMP","out_cols")
    a.mark("horizontal")
    a.e("PUSH",1); a.e("WRITE"); a.e("LOAD",ROWRUN); a.e("WRITE"); a.j("JMP","out_rows")

    def output_runs(addrs,prefix,end):
        a.e("PUSH",0); a.e("STORE",PREV)
        for i,addr in enumerate(addrs):
            no=f"{prefix}_no_{i}"; start=f"{prefix}_start_{i}"; done=f"{prefix}_done_{i}"
            a.e("PUSH",0); a.e("LOAD",addr); a.e("LT"); a.j("JZ",no)
            a.e("LOAD",PREV); a.j("JZ",start); a.j("JMP",done)
            a.mark(start)
            a.e("LOAD",addr); a.e("WRITE")
            a.e("PUSH",1); a.e("STORE",PREV); a.j("JMP",done)
            a.mark(no)
            a.e("PUSH",0); a.e("STORE",PREV)
            a.mark(done)
        a.j("JMP",end)

    a.mark("out_cols"); output_runs(COL,"oc","end")
    a.mark("out_rows"); output_runs(ROW,"or","end")
    a.mark("end"); a.e("HALT")
    return a.done()

PROGRAM=build_program()
PROGRAM_BYTES=u.encode(PROGRAM)
assert len(PROGRAM_BYTES)==5263
