from __future__ import annotations
from canonical.runtime.h100_u1_two_counter_compiler_v1 import I,P,L,assemble

W=32; H=20; N=W*H; ATLAS_BASE=N
BG=0; BEST=1; IA=2; JA=3; CAND=4; COUNT=5; Y=6; X=7; BASE=8; AX=9
HEIGHT=10; PREV=11; BARCOUNT=12; IDX=13; PAT=14; BESTDIST=15; BESTDIG=16
TIE=17; PWORK=18; AWORK=19; DIST=20; BIT=21; WY=22; WX=23; CANDDIG=24
TICKDIG=25; LEGDIG=26; VALBASE=100

def setc(a,v): return [P(a),P(v),I("STORE")]
def copy(src,dst): return [P(dst),P(src),I("LOAD"),I("STORE")]
def inc(a): return [P(a),P(a),I("LOAD"),P(1),I("ADD"),I("STORE")]
def dec(a): return [P(a),P(a),I("LOAD"),P(1),I("SUB"),I("STORE")]

def pixel(yaddr,xaddr,dy=0,dx=0):
    a=[P(yaddr),I("LOAD")]
    if dy: a += [P(dy),I("ADD")]
    a += [P(W),I("MUL"),P(xaddr),I("LOAD")]
    if dx: a += [P(dx),I("ADD")]
    a += [I("ADD"),I("READ")]
    return a

def add_fg_to_count(countaddr,yaddr,xaddr,dy=0,dx=0):
    # count += 1 - (pixel == bg)
    return [P(countaddr),P(countaddr),I("LOAD"),*pixel(yaddr,xaddr,dy,dx),
            P(BG),I("LOAD"),I("EQ"),P(1),I("SWAP"),I("SUB"),I("ADD"),I("STORE")]

def build_pattern(prefix):
    a=setc(PAT,0)
    for dy in range(5):
        for dx in range(3):
            a += [P(PAT),P(PAT),I("LOAD"),P(2),I("MUL"),
                  *pixel(WY,WX,dy,dx),P(BG),I("LOAD"),I("EQ"),
                  P(1),I("SWAP"),I("SUB"),I("ADD"),I("STORE")]
    return a

def compare_pattern_to_atlas(prefix):
    a=[
      *copy(PAT,PWORK),
      P(AWORK),P(IDX),I("LOAD"),P(2),I("MUL"),P(ATLAS_BASE),I("ADD"),I("READ"),I("STORE"),
      P(CANDDIG),P(IDX),I("LOAD"),P(2),I("MUL"),P(ATLAS_BASE+1),I("ADD"),I("READ"),I("STORE"),
      *setc(DIST,0),*setc(BIT,0),L(prefix+"_BIT"),
      P(BIT),I("LOAD"),P(15),I("LT"),I("JZ",prefix+"_BIT_DONE"),
      # compare low bits of PWORK and AWORK
      P(PWORK),I("LOAD"),P(2),I("MOD"),
      P(AWORK),I("LOAD"),P(2),I("MOD"),I("EQ"),I("JZ",prefix+"_DIFF"),
      I("JMP",prefix+"_BIT_SAME"),
      L(prefix+"_DIFF"),*inc(DIST),
      L(prefix+"_BIT_SAME"),
      # shift both by integer divide 2
      P(PWORK),P(PWORK),I("LOAD"),P(2),I("FDIV"),I("STORE"),
      P(AWORK),P(AWORK),I("LOAD"),P(2),I("FDIV"),I("STORE"),
      *inc(BIT),I("JMP",prefix+"_BIT"),L(prefix+"_BIT_DONE"),
      # better?
      P(DIST),I("LOAD"),P(BESTDIST),I("LOAD"),I("LT"),I("JZ",prefix+"_NOT_BETTER"),
      *copy(DIST,BESTDIST),*copy(CANDDIG,BESTDIG),*setc(TIE,0),I("JMP",prefix+"_CMP_DONE"),
      L(prefix+"_NOT_BETTER"),
      P(DIST),I("LOAD"),P(BESTDIST),I("LOAD"),I("EQ"),I("JZ",prefix+"_CMP_DONE"),
      P(CANDDIG),I("LOAD"),P(BESTDIG),I("LOAD"),I("EQ"),I("JZ",prefix+"_TIE_OTHER"),
      I("JMP",prefix+"_CMP_DONE"),
      L(prefix+"_TIE_OTHER"),*setc(TIE,1),
      L(prefix+"_CMP_DONE")
    ]
    return a

def ocr_zone(prefix,outaddr,legend=False):
    a=[*setc(BESTDIST,16),*setc(BESTDIG,-1),*setc(TIE,0),*setc(WY,0),L(prefix+"_Y")]
    if legend:
        a += [P(WY),I("LOAD"),P(8),I("LT"),I("JZ",prefix+"_DONE_SCAN"),
              P(WX),P(AX),I("LOAD"),P(1),I("ADD"),I("STORE")]
    else:
        a += [P(WY),I("LOAD"),P(4),I("ADD"),P(BASE),I("LOAD"),I("LT"),I("JZ",prefix+"_DONE_SCAN"),
              *setc(WX,0)]
    a += [L(prefix+"_X")]
    if legend:
        a += [P(WX),I("LOAD"),P(2),I("ADD"),P(W),I("LT"),I("JZ",prefix+"_NEXT_Y")]
    else:
        a += [P(WX),I("LOAD"),P(2),I("ADD"),P(AX),I("LOAD"),I("LT"),I("JZ",prefix+"_NEXT_Y")]
    a += build_pattern(prefix)
    a += [*setc(IDX,0),L(prefix+"_ATLAS"),
          P(IDX),I("LOAD"),P(10),I("LT"),I("JZ",prefix+"_AFTER_ATLAS")]
    a += compare_pattern_to_atlas(prefix+"_A")
    a += [*inc(IDX),I("JMP",prefix+"_ATLAS"),L(prefix+"_AFTER_ATLAS"),
          *inc(WX),I("JMP",prefix+"_X"),
          L(prefix+"_NEXT_Y"),*inc(WY),I("JMP",prefix+"_Y"),
          L(prefix+"_DONE_SCAN"),
          # require bestdist < 3 and no conflicting digit tie
          P(BESTDIST),I("LOAD"),P(3),I("LT"),I("JZ",prefix+"_BAD"),
          P(TIE),I("LOAD"),I("JZ",prefix+"_OK"),
          L(prefix+"_BAD"),*setc(outaddr,-1),I("JMP",prefix+"_END"),
          L(prefix+"_OK"),*copy(BESTDIG,outaddr),L(prefix+"_END")]
    return a

def program():
    a=[]
    # Background mode over arbitrary integer palette values.
    a += [*setc(BEST,-1),*setc(BG,0),*setc(IA,0),L("BG_I"),
          P(IA),I("LOAD"),P(N),I("LT"),I("JZ","BG_DONE"),
          P(CAND),P(IA),I("LOAD"),I("READ"),I("STORE"),
          *setc(COUNT,0),*setc(JA,0),L("BG_J"),
          P(JA),I("LOAD"),P(N),I("LT"),I("JZ","BG_ROW_DONE"),
          P(COUNT),P(COUNT),I("LOAD"),P(JA),I("LOAD"),I("READ"),
          P(CAND),I("LOAD"),I("EQ"),I("ADD"),I("STORE"),
          *inc(JA),I("JMP","BG_J"),L("BG_ROW_DONE"),
          P(BEST),I("LOAD"),P(COUNT),I("LOAD"),I("LT"),I("JZ","BG_NO"),
          *copy(COUNT,BEST),*copy(CAND,BG),L("BG_NO"),
          *inc(IA),I("JMP","BG_I"),L("BG_DONE")]

    # Baseline = row with largest foreground count.
    a += [*setc(BEST,-1),*setc(BASE,0),*setc(Y,0),L("ROW_Y"),
          P(Y),I("LOAD"),P(H),I("LT"),I("JZ","ROW_DONE"),
          *setc(COUNT,0),*setc(X,0),L("ROW_X"),
          P(X),I("LOAD"),P(W),I("LT"),I("JZ","ROW_END")]
    a += add_fg_to_count(COUNT,Y,X)
    a += [*inc(X),I("JMP","ROW_X"),L("ROW_END"),
          P(BEST),I("LOAD"),P(COUNT),I("LOAD"),I("LT"),I("JZ","ROW_NO"),
          *copy(COUNT,BEST),*copy(Y,BASE),L("ROW_NO"),
          *inc(Y),I("JMP","ROW_Y"),L("ROW_DONE")]

    # Axis x = column with largest foreground count.
    a += [*setc(BEST,-1),*setc(AX,0),*setc(X,0),L("COL_X"),
          P(X),I("LOAD"),P(W),I("LT"),I("JZ","COL_DONE"),
          *setc(COUNT,0),*setc(Y,0),L("COL_Y"),
          P(Y),I("LOAD"),P(H),I("LT"),I("JZ","COL_END")]
    a += add_fg_to_count(COUNT,Y,X)
    a += [*inc(Y),I("JMP","COL_Y"),L("COL_END"),
          P(BEST),I("LOAD"),P(COUNT),I("LOAD"),I("LT"),I("JZ","COL_NO"),
          *copy(COUNT,BEST),*copy(X,AX),L("COL_NO"),
          *inc(X),I("JMP","COL_X"),L("COL_DONE")]

    # OCR tick and legend from arbitrary positions within their role zones.
    a += ocr_zone("TICK",TICKDIG,legend=False)
    a += ocr_zone("LEG",LEGDIG,legend=True)

    # Bars = contiguous foreground columns immediately above baseline.
    a += [*setc(BARCOUNT,0),*setc(PREV,0),
          P(X),P(AX),I("LOAD"),P(1),I("ADD"),I("STORE"),L("BAR_X"),
          P(X),I("LOAD"),P(W),I("LT"),I("JZ","BAR_DONE"),
          *setc(HEIGHT,0),
          P(Y),P(BASE),I("LOAD"),P(1),I("SUB"),I("STORE"),L("BAR_UP"),
          P(Y),I("LOAD"),P(0),I("LT"),I("JZ","BAR_CHECK"),I("JMP","BAR_COL_DONE"),
          L("BAR_CHECK"),*pixel(Y,X),P(BG),I("LOAD"),I("EQ"),I("JZ","BAR_FG"),I("JMP","BAR_COL_DONE"),
          L("BAR_FG"),*inc(HEIGHT),*dec(Y),I("JMP","BAR_UP"),L("BAR_COL_DONE"),
          P(HEIGHT),I("LOAD"),P(1),I("LT"),I("JZ","BAR_NONZERO"),
          *setc(PREV,0),I("JMP","BAR_NEXT"),
          L("BAR_NONZERO"),P(PREV),I("LOAD"),I("JZ","BAR_NEW"),I("JMP","BAR_NEXT"),
          L("BAR_NEW"),
          P(BARCOUNT),I("LOAD"),P(VALBASE),I("ADD"),P(HEIGHT),I("LOAD"),I("STORE"),
          *inc(BARCOUNT),*setc(PREV,1),
          L("BAR_NEXT"),*inc(X),I("JMP","BAR_X"),L("BAR_DONE")]

    # Output tick, legend, count, heights.
    a += [P(TICKDIG),I("LOAD"),I("WRITE"),P(LEGDIG),I("LOAD"),I("WRITE"),
          P(BARCOUNT),I("LOAD"),I("WRITE"),*setc(IDX,0),L("OUT"),
          P(IDX),I("LOAD"),P(BARCOUNT),I("LOAD"),I("LT"),I("JZ","OUT_DONE"),
          P(IDX),I("LOAD"),P(VALBASE),I("ADD"),I("LOAD"),I("WRITE"),
          *inc(IDX),I("JMP","OUT"),L("OUT_DONE"),I("HALT")]
    return assemble(a)

def encode_public_input(public_input):
    rows=public_input["rows"]; atlas=public_input["atlas"]
    pixels=[int(ch) for row in rows for ch in row]
    tail=[]
    for p,d in atlas: tail += [int(p),int(d)]
    return pixels+tail

if __name__=="__main__":
    p=program(); print(len(p)); print(p.hex())
