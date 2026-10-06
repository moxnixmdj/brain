from canonical.runtime.h100_u1_two_counter_compiler_v1 import I,P,L,assemble

W=32; H=20
B=0; BEST=1; Y=2; X=3; COUNT=4; AX=5; BESTCOL=6; SWMAX=7
TICKPAT=8; LEGPAT=9; TICKDIG=10; LEGDIG=11
BARCOUNT=12; PREV=13; HEIGHT=14; IDX=15
VALBASE=100
ATLAS_BASE=W*H

def setc(a,v): return [P(a),P(v),I("STORE")]
def copy(src,dst): return [P(dst),P(src),I("LOAD"),I("STORE")]
def inc(a): return [P(a),P(a),I("LOAD"),P(1),I("ADD"),I("STORE")]
def pixel_dyn(yaddr,xaddr):
    return [P(yaddr),I("LOAD"),P(W),I("MUL"),P(xaddr),I("LOAD"),I("ADD"),I("READ")]

def lookup(pattern_addr,out_addr,prefix):
    return [
      *setc(IDX,0),L(prefix+"_LOOP"),
      P(IDX),I("LOAD"),P(10),I("LT"),I("JZ",prefix+"_NOT_FOUND"),
      P(IDX),I("LOAD"),P(2),I("MUL"),P(ATLAS_BASE),I("ADD"),I("READ"),
      P(pattern_addr),I("LOAD"),I("EQ"),I("JZ",prefix+"_NEXT"),
      P(out_addr),
      P(IDX),I("LOAD"),P(2),I("MUL"),P(ATLAS_BASE+1),I("ADD"),I("READ"),
      I("STORE"),I("JMP",prefix+"_DONE"),
      L(prefix+"_NEXT"),*inc(IDX),I("JMP",prefix+"_LOOP"),
      L(prefix+"_NOT_FOUND"),P(-1),I("WRITE"),I("HALT"),
      L(prefix+"_DONE")
    ]

def program():
    a=[]
    # Find horizontal axis baseline: row with maximum count of axis symbol 1.
    a += [*setc(B,0),*setc(BEST,-1),*setc(Y,0),L("ROW_LOOP"),
          P(Y),I("LOAD"),P(H),I("LT"),I("JZ","ROW_DONE"),
          *setc(COUNT,0),*setc(X,0),L("ROW_COL"),
          P(X),I("LOAD"),P(W),I("LT"),I("JZ","ROW_END"),
          *pixel_dyn(Y,X),P(1),I("EQ"),I("JZ","ROW_SKIP"),
          *inc(COUNT),L("ROW_SKIP"),*inc(X),I("JMP","ROW_COL"),
          L("ROW_END"),
          P(BEST),I("LOAD"),P(COUNT),I("LOAD"),I("LT"),I("JZ","ROW_NO_UPDATE"),
          *copy(COUNT,BEST),*copy(Y,B),
          L("ROW_NO_UPDATE"),*inc(Y),I("JMP","ROW_LOOP"),L("ROW_DONE")]

    # Find vertical axis x: column with maximum count of symbol 1.
    a += [*setc(AX,0),*setc(BESTCOL,-1),*setc(X,0),L("AX_LOOP"),
          P(X),I("LOAD"),P(W),I("LT"),I("JZ","AX_DONE"),
          *setc(COUNT,0),*setc(Y,0),L("AX_Y"),
          P(Y),I("LOAD"),P(H),I("LT"),I("JZ","AX_COL_END"),
          *pixel_dyn(Y,X),P(1),I("EQ"),I("JZ","AX_SKIP"),
          *inc(COUNT),L("AX_SKIP"),*inc(Y),I("JMP","AX_Y"),
          L("AX_COL_END"),
          P(BESTCOL),I("LOAD"),P(COUNT),I("LOAD"),I("LT"),I("JZ","AX_NO_UPDATE"),
          *copy(COUNT,BESTCOL),*copy(X,AX),
          L("AX_NO_UPDATE"),*inc(X),I("JMP","AX_LOOP"),L("AX_DONE")]

    # Find right edge of the sole legend swatch (symbol 4).
    a += [*setc(SWMAX,-1),*setc(Y,0),L("SW_Y"),
          P(Y),I("LOAD"),P(H),I("LT"),I("JZ","SW_DONE"),
          *setc(X,0),L("SW_X"),P(X),I("LOAD"),P(W),I("LT"),I("JZ","SW_ROW_END"),
          *pixel_dyn(Y,X),P(4),I("EQ"),I("JZ","SW_SKIP"),
          P(SWMAX),I("LOAD"),P(X),I("LOAD"),I("LT"),I("JZ","SW_SKIP"),
          *copy(X,SWMAX),
          L("SW_SKIP"),*inc(X),I("JMP","SW_X"),
          L("SW_ROW_END"),*inc(Y),I("JMP","SW_Y"),L("SW_DONE")]

    # Pack tick glyph from 3x5 box: x = AX-4..AX-2, y=1..5.
    a += setc(TICKPAT,0)
    for yy in range(1,6):
      for cc in range(3):
        a += [P(TICKPAT),P(TICKPAT),I("LOAD"),P(2),I("MUL"),
              P(AX),I("LOAD"),P(yy*W-4+cc),I("ADD"),I("READ"),P(3),I("EQ"),
              I("ADD"),I("STORE")]

    # Pack legend glyph: x = SWMAX+3..+5, y=1..5.
    a += setc(LEGPAT,0)
    for yy in range(1,6):
      for cc in range(3):
        a += [P(LEGPAT),P(LEGPAT),I("LOAD"),P(2),I("MUL"),
              P(SWMAX),I("LOAD"),P(yy*W+3+cc),I("ADD"),I("READ"),P(3),I("EQ"),
              I("ADD"),I("STORE")]

    a += lookup(TICKPAT,TICKDIG,"TICK")
    a += lookup(LEGPAT,LEGDIG,"LEG")

    # Scan columns to identify new rectangular bars and capture their heights.
    a += [*setc(BARCOUNT,0),*setc(PREV,0),
          P(X),P(AX),I("LOAD"),P(1),I("ADD"),I("STORE"),
          L("BAR_X"),P(X),I("LOAD"),P(W),I("LT"),I("JZ","BAR_DONE"),
          *setc(HEIGHT,0),*setc(Y,0),L("BAR_Y"),
          P(Y),I("LOAD"),P(B),I("LOAD"),I("LT"),I("JZ","BAR_COL_END"),
          *pixel_dyn(Y,X),P(2),I("EQ"),I("JZ","BAR_SKIP"),
          *inc(HEIGHT),L("BAR_SKIP"),*inc(Y),I("JMP","BAR_Y"),
          L("BAR_COL_END"),
          # zero height? height < 1
          P(HEIGHT),I("LOAD"),P(1),I("LT"),I("JZ","BAR_NONZERO"),
          *setc(PREV,0),I("JMP","BAR_NEXT_X"),
          L("BAR_NONZERO"),
          P(PREV),I("LOAD"),I("JZ","BAR_NEW"),
          I("JMP","BAR_NEXT_X"),
          L("BAR_NEW"),
          # mem[VALBASE+barcount] = height
          P(BARCOUNT),I("LOAD"),P(VALBASE),I("ADD"),P(HEIGHT),I("LOAD"),I("STORE"),
          *inc(BARCOUNT),*setc(PREV,1),
          L("BAR_NEXT_X"),*inc(X),I("JMP","BAR_X"),L("BAR_DONE")]

    # Output [tick, legend, bar_count, values...]
    a += [P(TICKDIG),I("LOAD"),I("WRITE"),P(LEGDIG),I("LOAD"),I("WRITE"),
          P(BARCOUNT),I("LOAD"),I("WRITE"),*setc(IDX,0),L("OUT_LOOP"),
          P(IDX),I("LOAD"),P(BARCOUNT),I("LOAD"),I("LT"),I("JZ","OUT_DONE"),
          P(IDX),I("LOAD"),P(VALBASE),I("ADD"),I("LOAD"),I("WRITE"),
          *inc(IDX),I("JMP","OUT_LOOP"),L("OUT_DONE"),I("HALT")]
    return assemble(a)

def encode_public_input(public_input):
    rows=public_input["rows"]; atlas=public_input["atlas"]
    pixels=[int(ch) for row in rows for ch in row]
    tail=[]
    for p,d in atlas: tail += [int(p),int(d)]
    return pixels+tail

if __name__=="__main__":
    p=program(); print(len(p)); print(p.hex())
