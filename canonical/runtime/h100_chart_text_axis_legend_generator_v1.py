from __future__ import annotations
import random

H,W=32,48
FONT={
"0":["111","101","101","101","111"],
"1":["010","110","010","010","111"],
"2":["110","001","010","100","111"],
"3":["110","001","010","001","110"],
"5":["111","100","110","001","110"],
"A":["010","101","111","101","101"],
"B":["110","101","110","101","110"],
"C":["011","100","100","100","011"],
"P":["110","101","110","100","100"],
"Q":["010","101","101","011","001"],
"R":["110","101","110","101","101"],
"S":["011","100","010","001","110"],
}
TICK_ROWS=[24,19,14,9]
GROUP_X=[16,25,34]

def _text(g,text,y,x,code=1):
    cx=x
    for ch in text:
        pat=FONT[ch]
        for dy,row in enumerate(pat):
            for dx,v in enumerate(row):
                if v=="1": g[y+dy][cx+dx]=code
        cx+=4

def generate(seed:int):
    rng=random.Random(int(seed))
    g=[[0]*W for _ in range(H)]
    # Axes.
    for y in range(8,25): g[y][9]=1
    for x in range(9,40): g[24][x]=1
    scale=rng.choice([1,2])
    ticks=[0,5,10,15] if scale==1 else [0,10,20,30]
    for row,val in zip(TICK_ROWS,ticks):
        for x in (8,9,10): g[row][x]=1
        s=str(val); width=len(s)*3+(len(s)-1)
        _text(g,s,row-2,7-width,1)
    categories=list("ABC"); rng.shuffle(categories)
    for cx,label in zip(GROUP_X,categories): _text(g,label,26,cx-1,1)
    labels=rng.sample(list("PQRS"),2)
    if rng.randrange(2): labels.reverse()
    # legend: color 2 left, color 3 right
    for y in range(2,5):
        for x in range(29,31): g[y][x]=2
        for x in range(38,40): g[y][x]=3
    _text(g,labels[0],1,32,1); _text(g,labels[1],1,41,1)
    heights2=[]; heights3=[]
    for cx in GROUP_X:
        h2=rng.randint(1,15); h3=rng.randint(1,15)
        heights2.append(h2); heights3.append(h3)
        for y in range(24-h2,24):
            for x in (cx-3,cx-2): g[y][x]=2
        for y in range(24-h3,24):
            for x in (cx+1,cx+2): g[y][x]=3
    values={
        labels[0]:[scale*h for h in heights2],
        labels[1]:[scale*h for h in heights3],
    }
    gold={
        "axis_ticks":[[v,r] for v,r in zip(ticks,TICK_ROWS)],
        "categories":categories,
        "legend":[[labels[0],2],[labels[1],3]],
        "values":values,
    }
    return {"rows":g,"gold":gold}
