from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from PIL import Image, ImageDraw
from canonical.runtime.chartography_series_intersection_v1 import solve

C=(0,190,190)

def w(text,cx,cy,line,word,width=24):
    return {"text":str(text),"confidence":99.0,"left":cx-width/2,"top":cy-6,
            "width":width,"height":12,"cx":cx,"cy":cy,
            "block_num":1,"par_num":1,"line_num":line,"word_num":word}

def make(tmp,slope):
    im=Image.new("RGB",(650,400),"white"); d=ImageDraw.Draw(im)
    L,R,T,B=70,430,40,310
    d.line((L,B,R,B),fill="black",width=2); d.line((L,T,L,B),fill="black",width=2)
    words=[]
    for i,v in enumerate([0,20,40,60,80,100]):
        words.append(w(v,L+(R-L)*v/100,335,10,i+1))
    for i,v in enumerate([0,1,2,3,4,5,6]):
        words.append(w(v,50,B-(B-T)*v/6,20+i,1))
    def xy(x,y): return L+(R-L)*x/100,B-(B-T)*y/6
    def series(m,on,off):
        x=0
        while x<100:
            e=min(100,x+on); d.line((*xy(x,m*x),*xy(e,m*e)),fill=C,width=2); x=e+off
    series(.044,100,0); series(.048,8,5); series(slope,2,8)
    for j,(a,on,off) in enumerate([("700",100,0),("900",8,5),("1100",2,8)]):
        cy=80+j*35; x=440
        while x<500:
            e=min(500,x+on); d.line((x,cy,e,cy),fill=C,width=2); x=e+off
        for q,(text,cx) in enumerate([(a,530),("0.03",580)],1): words.append(w(text,cx,cy,30+j,q))
    p=tmp/"c.png"; im.save(p); return p,words

class T(unittest.TestCase):
    def check(self,slope):
        with tempfile.TemporaryDirectory() as td:
            p,words=make(Path(td),slope)
            out=solve(p,"How long for selector 1100 / 0.03 to reach 4? Answer with 1 decimal place.",words=words)
            self.assertAlmostEqual(out["raw_value"],4/slope,delta=1.7)
    def test_base(self): self.check(.052)
    def test_metamorphic(self): self.check(.058)

if __name__=="__main__": unittest.main()
