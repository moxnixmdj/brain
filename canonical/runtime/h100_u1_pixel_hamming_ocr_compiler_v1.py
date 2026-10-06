from canonical.runtime.h100_u1_two_counter_compiler_v1 import I,P,L,assemble

BESTD=0; BESTDIG=1; TIE=2; T=3; R=4; BIT=5; CUR=6; A=7; B=8
BASE=7
TEMPLATE_STRIDE=8
TEMPLATE_COUNT=10
ROWS=7
BITS=5

def setc(a,v): return [P(a),P(v),I("STORE")]
def copy(src,dst): return [P(dst),P(src),I("LOAD"),I("STORE")]
def inc(a): return [P(a),P(a),I("LOAD"),P(1),I("ADD"),I("STORE")]

def read_query_row():
    return [P(R),I("LOAD"),I("READ")]

def read_template_row():
    return [P(T),I("LOAD"),P(TEMPLATE_STRIDE),I("MUL"),P(BASE),I("ADD"),P(R),I("LOAD"),I("ADD"),I("READ")]

def read_template_digit():
    return [P(T),I("LOAD"),P(TEMPLATE_STRIDE),I("MUL"),P(BASE+ROWS),I("ADD"),I("READ")]

def program():
    a=[]
    a += [*setc(BESTD,999),*setc(BESTDIG,-1),*setc(TIE,0),*setc(T,0),L("T_LOOP"),
          P(T),I("LOAD"),P(TEMPLATE_COUNT),I("LT"),I("JZ","DONE"),
          *setc(CUR,0),*setc(R,0),L("R_LOOP"),
          P(R),I("LOAD"),P(ROWS),I("LT"),I("JZ","TEMPLATE_DONE"),
          P(A),*read_query_row(),I("STORE"),
          P(B),*read_template_row(),I("STORE"),
          *setc(BIT,0),L("BIT_LOOP"),
          P(BIT),I("LOAD"),P(BITS),I("LT"),I("JZ","ROW_DONE"),
          P(A),I("LOAD"),P(2),I("MOD"),
          P(B),I("LOAD"),P(2),I("MOD"),
          I("EQ"),I("JZ","MISMATCH"),I("JMP","BIT_ADV"),
          L("MISMATCH"),*inc(CUR),
          L("BIT_ADV"),
          P(A),P(A),I("LOAD"),P(2),I("FDIV"),I("STORE"),
          P(B),P(B),I("LOAD"),P(2),I("FDIV"),I("STORE"),
          *inc(BIT),I("JMP","BIT_LOOP"),
          L("ROW_DONE"),*inc(R),I("JMP","R_LOOP"),
          L("TEMPLATE_DONE"),
          P(CUR),I("LOAD"),P(BESTD),I("LOAD"),I("LT"),I("JZ","NOT_BETTER"),
          *copy(CUR,BESTD),P(BESTDIG),*read_template_digit(),I("STORE"),*setc(TIE,0),I("JMP","AFTER_COMPARE"),
          L("NOT_BETTER"),
          P(CUR),I("LOAD"),P(BESTD),I("LOAD"),I("EQ"),I("JZ","AFTER_COMPARE"),
          *setc(TIE,1),
          L("AFTER_COMPARE"),*inc(T),I("JMP","T_LOOP"),
          L("DONE"),
          P(TIE),I("LOAD"),I("JZ","UNIQUE"),
          P(-1),I("WRITE"),I("HALT"),
          L("UNIQUE"),P(BESTDIG),I("LOAD"),I("WRITE"),I("HALT")]
    return assemble(a)

def encode_input(rows,atlas):
    out=[int(x) for x in rows]
    for template,digit in atlas:
        if len(template)!=ROWS: raise ValueError("TEMPLATE_ROWS")
        out.extend(int(x) for x in template)
        out.append(int(digit))
    if len(atlas)!=TEMPLATE_COUNT: raise ValueError("ATLAS_COUNT")
    return out

if __name__=="__main__":
    p=program()
    print(len(p))
    print(p.hex())
