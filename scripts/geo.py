#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "pillow"]
# ///
"""坐标系换算 + 方位/距离 + 相机几何。其余脚本都 import 这个文件。"""
from __future__ import annotations
import argparse, json, math, os, re, sys, time
from pathlib import Path

_A = 6378245.0
_EE = 0.00669342162296594323

def _out_of_china(lat, lon): return not (73.66 < lon < 135.05 and 3.86 < lat < 53.55)
def _t_lat(x,y):
    r=-100+2*x+3*y+0.2*y*y+0.1*x*y+0.2*math.sqrt(abs(x))
    r+=(20*math.sin(6*x*math.pi)+20*math.sin(2*x*math.pi))*2/3
    r+=(20*math.sin(y*math.pi)+40*math.sin(y/3*math.pi))*2/3
    r+=(160*math.sin(y/12*math.pi)+320*math.sin(y*math.pi/30))*2/3
    return r
def _t_lon(x,y):
    r=300+x+2*y+0.1*x*x+0.1*x*y+0.1*math.sqrt(abs(x))
    r+=(20*math.sin(6*x*math.pi)+20*math.sin(2*x*math.pi))*2/3
    r+=(20*math.sin(x*math.pi)+40*math.sin(x/3*math.pi))*2/3
    r+=(150*math.sin(x/12*math.pi)+300*math.sin(x/30*math.pi))*2/3
    return r
def _gcj_delta(lat,lon):
    dlat=_t_lat(lon-105,lat-35); dlon=_t_lon(lon-105,lat-35)
    rad=lat/180*math.pi; m=1-_EE*math.sin(rad)**2; sm=math.sqrt(m)
    dlat=dlat*180/((_A*(1-_EE))/(m*sm)*math.pi)
    dlon=dlon*180/(_A/sm*math.cos(rad)*math.pi)
    return dlat,dlon
def wgs2gcj(lat,lon):
    if _out_of_china(lat,lon): return lat,lon
    dlat,dlon=_gcj_delta(lat,lon); return lat+dlat,lon+dlon
def gcj2wgs(lat,lon):
    if _out_of_china(lat,lon): return lat,lon
    wlat,wlon=lat,lon
    for _ in range(5):
        glat,glon=wgs2gcj(wlat,wlon); wlat+=lat-glat; wlon+=lon-glon
    return wlat,wlon
_XPI=math.pi*3000/180
def gcj2bd(lat,lon):
    z=math.hypot(lon,lat)+0.00002*math.sin(lat*_XPI)
    th=math.atan2(lat,lon)+0.000003*math.cos(lon*_XPI)
    return z*math.sin(th)+0.006,z*math.cos(th)+0.0065
def bd2gcj(lat,lon):
    x,y=lon-0.0065,lat-0.006
    z=math.hypot(x,y)-0.00002*math.sin(y*_XPI)
    th=math.atan2(y,x)-0.000003*math.cos(x*_XPI)
    return z*math.sin(th),z*math.cos(th)
_MCBAND=[12890594.86,8362377.87,5591021,3481989.83,1678043.12,0]
_MC2LL=[
[1.410526172116255e-8,0.00000898305509648872,-1.9939833816331,200.9824383106796,-187.2403703815547,91.6087516669843,-23.38765649603339,2.57121317296198,-0.03801003308653,17337981.2],
[-7.435856389565537e-9,0.000008983055097726239,-0.78625201886289,96.32687599759846,-1.85204757529826,-59.36935905485877,47.40033549296737,-16.50741931063887,2.28786674699375,10260144.86],
[-3.030883460898826e-8,0.00000898305509983578,0.30071316287616,59.74293618442277,7.357984074871,-25.38371002664745,13.45380521110908,-3.29883767235584,0.32710905363475,6856817.37],
[-1.981981304930552e-8,0.000008983055099779535,0.03278182852591,40.31678527705744,0.65659298677277,-4.44255534477492,0.85341911805263,0.12923347998204,-0.04625736007561,4482777.06],
[3.09191371068437e-9,0.000008983055096812155,0.00006995724062,23.10934304144901,-0.00023663490511,-0.6321817810242,-0.00663494467273,0.03430082397953,-0.00466043876332,2555164.4],
[2.890871144776878e-9,0.000008983055095805407,-3.068298e-8,7.47137025468032,-0.00000353937994,-0.02145144861037,-0.00001234426596,0.00010322952773,-0.00000323890364,826088.5]]
_LLBAND=[75,60,45,30,15,0]
_LL2MC=[
[-0.0015702102444,111320.7020616939,1704480524535203,-10338987376042340,26112667856603880,-35149669176653700,26595700718403920,-10725012454188240,1800819912950474,82.5],
[0.0008277824516172526,111320.7020463578,647795574.6671607,-4082003173.641316,10774905663.51142,-15171875531.51559,12053065338.62167,-5124939663.577472,913311935.9512032,67.5],
[0.00337398766765,111320.7020202162,4481351.045890365,-23393751.19931662,79682215.47186455,-115964993.2797253,97236711.15602145,-43661946.33752821,8477230.501135234,52.5],
[0.00220636496208,111320.7020209128,51751.86112841131,3796837.749470245,992013.7397791013,-1221952.21711287,1340652.697009075,-620943.6990984312,144416.9293806241,37.5],
[-0.0003441963504368392,111320.7020576856,278.2353980772752,2485758.690035394,6070.750963243378,54821.18345352118,9540.606633304236,-2710.55326746645,1405.483844121726,22.5],
[-0.0003218135878613132,111320.7020701615,0.00369383431289,823725.6402795718,0.46104986909093,2351.343141331292,1.58060784298199,8.77738589078284,0.37238884252424,7.45]]
def _poly(x,y,c):
    fx=c[0]+c[1]*abs(x); t=abs(y)/c[9]
    fy=c[2]+c[3]*t+c[4]*t**2+c[5]*t**3+c[6]*t**4+c[7]*t**5+c[8]*t**6
    return (-fx if x<0 else fx),(-fy if y<0 else fy)
def bdmc2bd(x,y):
    c=next(_MC2LL[i] for i,b in enumerate(_MCBAND) if abs(y)>=b)
    lon,lat=_poly(x,y,c); return lat,lon
def bd2bdmc(lat,lon):
    lat=max(min(lat,74),-74)
    c=next(_LL2MC[i] for i,b in enumerate(_LLBAND) if abs(lat)>=b)
    return _poly(lon,lat,c)
def convert(a,b,src,dst):
    if src==dst: return a,b
    if src=="wgs": lat,lon=a,b
    elif src=="gcj": lat,lon=gcj2wgs(a,b)
    elif src=="bd": lat,lon=gcj2wgs(*bd2gcj(a,b))
    elif src=="bdmc": lat,lon=gcj2wgs(*bd2gcj(*bdmc2bd(a,b)))
    else: raise ValueError(src)
    if dst=="wgs": return lat,lon
    g=wgs2gcj(lat,lon)
    if dst=="gcj": return g
    bd=gcj2bd(*g)
    if dst=="bd": return bd
    if dst=="bdmc": return bd2bdmc(*bd)
    raise ValueError(dst)

_R=6371008.8
def distance(p,q):
    la1,lo1,la2,lo2=map(math.radians,(*p,*q))
    h=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*_R*math.asin(math.sqrt(h))
def bearing(p,q):
    la1,lo1,la2,lo2=map(math.radians,(*p,*q))
    y=math.sin(lo2-lo1)*math.cos(la2)
    x=math.cos(la1)*math.sin(la2)-math.sin(la1)*math.cos(la2)*math.cos(lo2-lo1)
    return (math.degrees(math.atan2(y,x))+360)%360
def dest(p,brg,dist_m):
    la1,lo1=map(math.radians,p); b=math.radians(brg); d=dist_m/_R
    la2=math.asin(math.sin(la1)*math.cos(d)+math.cos(la1)*math.sin(d)*math.cos(b))
    lo2=lo1+math.atan2(math.sin(b)*math.sin(d)*math.cos(la1),math.cos(d)-math.sin(la1)*math.sin(la2))
    return math.degrees(la2),math.degrees(lo2)

def ll2px(zoom,lat,lon):
    n=256*2**zoom; x=(lon+180)/360*n
    y=(1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n; return x,y
def px2ll(zoom,x,y):
    n=256*2**zoom; lon=x/n*360-180
    lat=math.degrees(math.atan(math.sinh(math.pi*(1-2*y/n)))); return lat,lon
def meters_per_px(zoom,lat): return 156543.03392*math.cos(math.radians(lat))/2**zoom

def focal_px(iw,hfov): return (iw/2)/math.tan(math.radians(hfov)/2)
def range_from_size(real,px,iw,hfov): return real*focal_px(iw,hfov)/px
def fov_from_equiv_focal(focal_mm,aspect=(4,3)):
    diag=43.2666; w,h=aspect; k=diag/math.hypot(w,h)
    long_s,short_s=w*k,h*k
    return (math.degrees(2*math.atan(long_s/2/focal_mm)),math.degrees(2*math.atan(short_s/2/focal_mm)))

# 简化版 CLI（完整版本见原始 geo-sleuth 项目）
def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="cmd",required=True)
    c=sub.add_parser("convert")
    c.add_argument("--from",dest="src",required=True)
    c.add_argument("--to",dest="dst",required=True)
    c.add_argument("a",type=float); c.add_argument("b",type=float)
    b=sub.add_parser("bearing"); b.add_argument("p"); b.add_argument("q")
    d=sub.add_parser("dest"); d.add_argument("p"); d.add_argument("--bearing",type=float,required=True); d.add_argument("--dist",type=float,required=True)
    args=ap.parse_args()
    if args.cmd=="convert":
        x,y=convert(args.a,args.b,args.src,args.dst); print(f"{x:.7f},{y:.7f}")
    elif args.cmd=="bearing":
        p=tuple(float(v) for v in args.p.split(",")); q=tuple(float(v) for v in args.q.split(","))
        print(f"bearing={bearing(p,q):.1f}deg distance={distance(p,q):.1f}m")
    elif args.cmd=="dest":
        p=tuple(float(v) for v in args.p.split(","))
        la,lo=dest(p,args.bearing,args.dist); print(f"{la:.7f},{lo:.7f}")

if __name__=="__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
