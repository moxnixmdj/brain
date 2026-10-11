from __future__ import annotations
import hashlib,struct,tempfile
from pathlib import Path
from canonical.runtime.chartography_deterministic_geometry_v1 import (
    read_bmp_rgb,tallest_bar_color,bar_height_ratio,line_left_to_right_trend,
    line_right_higher_color,vertical_divider_x,count_components_left_of_x,
    grouped_bar_winner_group
)

W,H=256,192
WHITE=(255,255,255); BLACK=(0,0,0); RED=(255,0,0); GREEN=(0,180,0); BLUE=(0,80,255)
CYAN=(0,190,190); YELLOW=(240,190,0); PURPLE=(145,70,200); ORANGE=(240,120,20)

def canvas(): return [[WHITE for _ in range(W)] for __ in range(H)]
def rect(im,x0,y0,x1,y1,c):
    for y in range(max(0,y0),min(H,y1)):
        for x in range(max(0,x0),min(W,x1)): im[y][x]=c
def line(im,x0,y0,x1,y1,c,t=3):
    dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        rect(im,x0-t//2,y0-t//2,x0+t//2+1,y0+t//2+1,c)
        if x0==x1 and y0==y1: return
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
def dot(im,x,y,c,r=5):
    for yy in range(y-r,y+r+1):
        for xx in range(x-r,x+r+1):
            if (xx-x)**2+(yy-y)**2<=r*r and 0<=xx<W and 0<=yy<H: im[yy][xx]=c
def axes(im): line(im,28,160,232,160,BLACK,2); line(im,28,20,28,160,BLACK,2)
def bmp(im):
    stride=((W*3+3)//4)*4; pix=bytearray()
    for y in range(H-1,-1,-1):
        raw=bytearray()
        for x in range(W):
            r,g,b=im[y][x]; raw+=bytes((b,g,r))
        raw+=bytes(stride-len(raw)); pix+=raw
    size=54+len(pix)
    return b"BM"+struct.pack("<IHHI",size,0,0,54)+struct.pack("<IIIHHIIIIII",40,W,H,1,24,0,len(pix),2835,2835,0,0)+pix
def roundtrip(im,tmp,name):
    p=tmp/f"{name}.bmp"; p.write_bytes(bmp(im)); return read_bmp_rgb(p)



def test_frozen_six_and_metamorphic_six():
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td)
        # Frozen case 1 + mutation with RED tallest.
        im=canvas(); axes(im); rect(im,55,120,90,160,RED); rect(im,110,80,145,160,GREEN); rect(im,165,40,200,160,BLUE)
        a=roundtrip(im,tmp,"bar_order"); assert tallest_bar_color(a,{"RED":RED,"GREEN":GREEN,"BLUE":BLUE})=="BLUE"
        im2=canvas(); axes(im2); rect(im2,55,30,90,160,RED); rect(im2,110,80,145,160,GREEN); rect(im2,165,100,200,160,BLUE)
        assert tallest_bar_color(roundtrip(im2,tmp,"bar_order_mut"),{"RED":RED,"GREEN":GREEN,"BLUE":BLUE})=="RED"
    
        # Frozen case 2 + mutation ratio 3.
        im=canvas(); axes(im); rect(im,75,64,115,160,CYAN); rect(im,150,112,190,160,YELLOW)
        assert abs(bar_height_ratio(roundtrip(im,tmp,"ratio"),CYAN,YELLOW)-2)<1e-9
        im2=canvas(); axes(im2); rect(im2,75,40,115,160,CYAN); rect(im2,150,120,190,160,YELLOW)
        assert abs(bar_height_ratio(roundtrip(im2,tmp,"ratio_mut"),CYAN,YELLOW)-3)<1e-9
    
        # Frozen line trend + reversed mutation.
        im=canvas(); axes(im); pts=[(48,140),(85,120),(122,96),(159,70),(205,46)]
        for a,b in zip(pts,pts[1:]): line(im,*a,*b,RED,4)
        assert line_left_to_right_trend(roundtrip(im,tmp,"trend"),RED)=="INCREASE"
        im2=canvas(); axes(im2); pts2=[(48,46),(85,70),(122,96),(159,120),(205,140)]
        for a,b in zip(pts2,pts2[1:]): line(im2,*a,*b,RED,4)
        assert line_left_to_right_trend(roundtrip(im2,tmp,"trend_mut"),RED)=="DECREASE"
    
        # Frozen crossing + color-swap mutation.
        im=canvas(); axes(im); line(im,48,50,210,135,RED,4); line(im,48,135,210,50,BLUE,4)
        assert line_right_higher_color(roundtrip(im,tmp,"cross"),{"RED":RED,"BLUE":BLUE})=="BLUE"
        im2=canvas(); axes(im2); line(im2,48,135,210,50,RED,4); line(im2,48,50,210,135,BLUE,4)
        assert line_right_higher_color(roundtrip(im2,tmp,"cross_mut"),{"RED":RED,"BLUE":BLUE})=="RED"
    
        # Frozen scatter + mutation adding one green point.
        im=canvas(); axes(im); line(im,130,25,130,160,BLACK,1)
        for p in [(50,55),(70,80),(88,108),(105,65),(116,130)]: dot(im,*p,GREEN,6)
        for p in [(155,75),(183,112),(214,52)]: dot(im,*p,RED,6)
        a=roundtrip(im,tmp,"scatter"); xd=vertical_divider_x(a); assert count_components_left_of_x(a,GREEN,xd)==5
        dot(im,60,145,GREEN,6); a2=roundtrip(im,tmp,"scatter_mut"); assert count_components_left_of_x(a2,GREEN,vertical_divider_x(a2))==6
    
        # Frozen grouped comparison + inverse mutation.
        im=canvas(); axes(im); rect(im,60,100,85,160,PURPLE); rect(im,88,75,113,160,ORANGE); rect(im,155,55,180,160,PURPLE); rect(im,183,95,208,160,ORANGE)
        assert grouped_bar_winner_group(roundtrip(im,tmp,"grouped"),PURPLE,ORANGE)=="RIGHT"
        im2=canvas(); axes(im2); rect(im2,60,55,85,160,PURPLE); rect(im2,88,95,113,160,ORANGE); rect(im2,155,100,180,160,PURPLE); rect(im2,183,75,208,160,ORANGE)
        assert grouped_bar_winner_group(roundtrip(im2,tmp,"grouped_mut"),PURPLE,ORANGE)=="LEFT"
    
    
    
