import sys; sys.path.insert(0,'.')
import magpie, cairosvg, base64
def img(path,x,y,w,h):
    b=base64.b64encode(open(path,'rb').read()).decode()
    return f'<image x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid meet" href="data:image/png;base64,{b}"/>'
TIGER='tiger_cut.png'  # 382x465
from PIL import ImageFont
_F=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',100,index=1)
def fit(t,size,maxw):
    if _F.getlength(t)*size/100<=maxw: return t
    while t and _F.getlength(t+'…')*size/100>maxw: t=t[:-1]
    return t.rstrip(' ·')+'…'
S=3  # px per dp (xxhdpi phone)
SANS="Noto Sans CJK KR"; SERIF="Noto Serif CJK KR"
W={'ko':'추석','hj':'秋夕','hun':'가을 추 · 저녁 석','en':'Chuseok, the autumn harvest festival','tag':'오늘의 새 단어'}
STRIPES="M4,2 C12,6 16,16 14,30 C12,19 9,10 4,2 Z M14,4 C21,9 24,18 22,33 C20,21 18,12 14,4 Z M24,8 C30,13 32,21 30,35 C29,24 27,16 24,8 Z M33,14 C37,18 39,24 38,35 C37,27 35.5,21 33,14 Z"
def txt(x,y,s,size,fill,weight=400,family=SANS,anchor='start',op=1):
    sh=f'<text x="{x}" y="{y+size*0.035}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="#000" fill-opacity="{0.3*op}" text-anchor="{anchor}">{s}</text>'
    return sh+f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" fill="{fill}" fill-opacity="{op}" text-anchor="{anchor}">{s}</text>'
def seal(x,y,size=18):
    return (f'<rect x="{x}" y="{y}" width="{size}" height="{size}" rx="3" fill="#B8322A"/>'
            f'<text x="{x+size/2}" y="{y+size*0.78}" font-family="{SERIF}" font-weight="700" font-size="{size*0.74}" fill="#F7E9D2" text-anchor="middle">虎</text>')
def card(x,y,w,h,r=24):
    gid=f"g{int(x)}{int(y)}"
    return (f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#27405F" stop-opacity=".5"/>'
            f'<stop offset="1" stop-color="#3E7466" stop-opacity=".3"/></linearGradient></defs>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="url(#{gid})"/>'
            f'<rect x="{x+.5}" y="{y+.5}" width="{w-1}" height="{h-1}" rx="{r}" fill="none" stroke="#F6F0E1" stroke-opacity="0.18"/>')
def saekdong(x,y,w=26,h=5):
    cols=["#C23B2C","#E2B45A","#8DB85A","#27405F","#E48BA0"]; sw=w/5
    o=f'<clipPath id="sd{int(x)}{int(y)}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}"/></clipPath><g clip-path="url(#sd{int(x)}{int(y)})">'
    for k,c in enumerate(cols): o+=f'<rect x="{x+k*sw}" y="{y}" width="{sw+.2}" height="{h}" fill="{c}"/>'
    return o+'</g>'
def stripes(x,y,w,op=.5):
    s=w/40; return f'<g transform="translate({x},{y}) scale({s})" opacity="{op}"><path d="{STRIPES}" fill="#EDA23C"/></g>'
def title_line(x,y,size):
    return (f'<text x="{x}" y="{y+size*0.035}" font-family="{SANS}" font-size="{size}" font-weight="700" fill="#000" fill-opacity=".3">{W["ko"]}<tspan font-family="{SERIF}" font-weight="400" font-size="{size*.72}" dx="{size*.3}">{W["hj"]}</tspan></text>'
            f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="{size}" font-weight="700" fill="#fff">{W["ko"]}<tspan font-family="{SERIF}" font-weight="400" font-size="{size*.72}" fill="#EBCB8B" dx="{size*.3}">{W["hj"]}</tspan></text>')
# --- the three widget layouts (all units dp, scaled by S) ---
def medium(x,y):   # 4x1 — the default
    w,h=340,76; o=card(x,y,w,h)
    o+=magpie.svg(50,x+w-60,y+5)
    th=70; tw=th*382/465; o+=img(TIGER,x+6,y+h-th-2,tw,th)
    tx=x+6+tw+10
    o+=title_line(tx,y+36,24)
    o+=txt(tx,y+58,fit(f'{W["hun"]}  ·  {W["en"]}',12.5,x+w-16-tx),12.5,'#EFE8D8')
    return o
def large(x,y):    # 4x2
    w,h=340,158; o=card(x,y,w,h)
    o+=magpie.svg(86,x+w-92,y+6)
    th=148; tw=th*382/465; o+=img(TIGER,x+6,y+h-th-4,tw,th)
    tx=x+6+tw+12
    o+=saekdong(tx,y+27)+txt(tx+32,y+33,W['tag'],12.5,'#E2B45A',500)
    o+=title_line(tx,y+84,34)
    o+=txt(tx,y+110,W['hun'],15,'#EFE8D8')
    o+=txt(tx,y+132,fit(W['en'],13.5,x+w-40-tx),13.5,'#D5DEE4')
    o+=seal(x+w-34,y+h-34)
    return o
def small(x,y):    # 2x1
    w,h=160,76; o=card(x,y,w,h)
    th=70; tw=th*382/465; o+=img(TIGER,x+6,y+h-th-2,tw,th)
    o+=txt(x+76,y+36,W['ko'],22,'#F6F0E1',700)
    o+=txt(x+76,y+58,W['hj'],16,'#EBCB8B',400,SERIF)
    return o
def cover(x,y):    # Galaxy Z Flip cover screen — deep indigo, tiger down the left, magpies above
    w,h=250,260
    o=(f'<defs><linearGradient id="cv" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#27405F"/><stop offset="1" stop-color="#1B2A2F"/></linearGradient></defs>'
       f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="34" fill="url(#cv)"/>')
    o+=magpie.svg(104,x+w-112,y+12)
    th=164; tw=th*382/465; o+=img(TIGER,x+10,y+h-th-22,tw,th)
    tx=x+10+tw+10
    o+=saekdong(tx,y+70,24,5)
    o+=f'<text x="{tx}" y="{y+92}" font-family="{SANS}" font-size="11.5" font-weight="500" fill="#E2B45A">오늘의 새 단어</text>'
    o+=f'<text x="{tx}" y="{y+126}" font-family="{SANS}" font-size="28" font-weight="700" fill="#F6F0E1">{W["ko"]}</text>'
    o+=f'<text x="{tx}" y="{y+154}" font-family="{SERIF}" font-size="22" fill="#EBCB8B">{W["hj"]}</text>'
    o+=f'<text x="{tx}" y="{y+176}" font-family="{SANS}" font-size="12" fill="#EFE8D8">가을 추</text>'
    o+=f'<text x="{tx}" y="{y+192}" font-family="{SANS}" font-size="12" fill="#EFE8D8">저녁 석</text>'
    o+=f'<text x="{tx}" y="{y+210}" font-family="{SANS}" font-size="11" fill="#C9D3DA">Chuseok</text>'
    o+=seal(x+w-40,y+h-40,20)
    return o
def wallpaper_dark(x,y,w,h):
    return (f'<defs><linearGradient id="gd" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3B5A5E"/><stop offset=".55" stop-color="#22343F"/><stop offset="1" stop-color="#151B25"/></linearGradient></defs>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="28" fill="url(#gd)"/>'
            f'<path d="M{x},{y+h*.62} C{x+w*.2},{y+h*.48} {x+w*.35},{y+h*.58} {x+w*.5},{y+h*.5} C{x+w*.7},{y+h*.4} {x+w*.85},{y+h*.55} {x+w},{y+h*.47} L{x+w},{y+h} L{x},{y+h} Z" fill="#1B2A31" opacity=".8"/>'
            f'<path d="M{x},{y+h*.78} C{x+w*.25},{y+h*.66} {x+w*.55},{y+h*.8} {x+w},{y+h*.68} L{x+w},{y+h} L{x},{y+h} Z" fill="#101820" opacity=".9"/>')
def wallpaper_light(x,y,w,h):
    return (f'<defs><linearGradient id="gl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#F6C9A8"/><stop offset=".5" stop-color="#E9A9A3"/><stop offset="1" stop-color="#8FA7C4"/></linearGradient></defs>'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="28" fill="url(#gl)"/>'
            f'<circle cx="{x+w*.78}" cy="{y+h*.3}" r="{w*.09}" fill="#FFF1DC" opacity=".9"/>'
            f'<path d="M{x},{y+h*.7} C{x+w*.3},{y+h*.55} {x+w*.6},{y+h*.72} {x+w},{y+h*.6} L{x+w},{y+h} L{x},{y+h} Z" fill="#6E86A8" opacity=".75"/>')
def label(x,y,s): return f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="13" fill="#5A5F66">{s}</text>'
Wd,Hd=800,740
b=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wd*S}" height="{Hd*S}" viewBox="0 0 {Wd} {Hd}"><rect width="{Wd}" height="{Hd}" fill="#F3F1EC"/>']
b.append(label(20,26,'4 × 1 (default) and 2 × 1 — dark wallpaper'))
b.append(wallpaper_dark(20,36,370,300)); b.append(medium(35,70)); b.append(small(35,170))
b.append(label(410,26,'4 × 2 — light wallpaper'))
b.append(wallpaper_light(410,36,370,300).replace('id="gl"','id="gl1"').replace('url(#gl)','url(#gl1)')); b.append(large(425,90))
b.append(label(20,376,'4 × 1 and 2 × 1 — light wallpaper'))
b.append(wallpaper_light(20,386,370,330)); b.append(medium(35,420)); b.append(small(35,520))
b.append(label(410,376,'Galaxy Z Flip cover screen'))
b.append(cover(470,420))
b.append('</svg>')
cairosvg.svg2png(bytestring=''.join(b).encode(),write_to='preview.png')
