# Flying magpies (까치) in the folk-painting manner: black head and back, white belly and wing patches,
# long blue-green tail. Three birds flying left, toward the tiger. viewBox 0 0 120 60.
BLACK="#1B1E23"; WHITE="#F4F1EA"; SHEEN="#3E6E78"; FAR="#2E333B"
def bird(x,y,s,flap=0):
    T=lambda d: d  # paths are written at unit scale and placed with a transform
    parts=[
     ("M19,22 C21,28 24,33 30,36 C29,33 29,30.5 30,29 C28,28.5 27,26 27,23 Z",FAR),             # far wing, down
     ("M23.5,27.5 C25,30.5 27,33 29.6,34.8 C29,32.6 29,30.8 29.8,29.4 C27.8,29.2 25.6,28.6 23.5,27.5 Z",WHITE),
     ("M29,20 C38,21 48,23.5 58,27.5 C57,29.5 55,30 53,29.6 C45,28 37,26 29,24 Z",BLACK),       # long graduated tail
     ("M38,23.2 C44,24.4 50,26 55.6,28.2",SHEEN),
     ("M6.5,19.5 C7,15.8 10.5,14 14,14.6 C20,14.6 27,17 31,21 C28,25 21,26.5 15,25 C10.5,24 7,22.5 6.5,19.5 Z",BLACK),
     ("M15,22.2 C19,25.6 25,25.6 30,22.8 C27,21 20,20.6 15,22.2 Z",WHITE),                       # white belly
     ("M6.8,18.8 L2.4,19.6 L6.9,20.4 Z",BLACK),                                                  # beak
     ("M16,17 C16,10 20,3 29,0.5 C31,2 31.5,4 30.5,5.5 C33,6 33.5,8 32,9.5 C33.5,11 33,13 31,13.5 C30,16 28,18 26,19 Z",BLACK),  # near wing, raised
     ("M22.5,7 C24.5,4 27,2.2 29.5,1.4 C31,3 31,4.6 30.2,5.8 C32.4,6.4 32.8,8.2 31.6,9.4 C28.5,9.6 25,8.8 22.5,7 Z",WHITE),     # white primaries
     ("M18.6,12.5 C20.5,8.8 23.5,5.8 27,3.8",SHEEN),
    ]
    return [(d,f,x,y,s) for d,f in parts]
BIRDS=bird(56,2,0.95)+bird(22,20,0.62)+bird(88,34,0.45)
def svg(w,x,y):
    k=w/120; o=[f'<g transform="translate({x},{y}) scale({k})">']
    for d,f,bx,by,s in BIRDS:
        if d.startswith(("M38,23.2","M18.6,12.5")):
            o.append(f'<path transform="translate({bx},{by}) scale({s})" d="{d}" fill="none" stroke="{f}" stroke-width="0.9" stroke-linecap="round"/>')
        else:
            rim=f' stroke="#F6F0E1" stroke-opacity="0.35" stroke-width="0.6"' if f in (BLACK,FAR) else ''
            o.append(f'<path transform="translate({bx},{by}) scale({s})" d="{d}" fill="{f}"{rim}/>')
    return ''.join(o)+'</g>'
def vector():
    r=['<vector xmlns:android="http://schemas.android.com/apk/res/android"','    android:width="120dp" android:height="60dp" android:viewportWidth="120" android:viewportHeight="60">']
    for d,f,bx,by,s in BIRDS:
        r.append(f'    <group android:translateX="{bx}" android:translateY="{by}" android:scaleX="{s}" android:scaleY="{s}">')
        if d.startswith(("M38,23.2","M18.6,12.5")):
            r.append(f'        <path android:pathData="{d}" android:strokeColor="{f}" android:strokeWidth="0.9" android:strokeLineCap="round" />')
        else:
            rim=' android:strokeColor="#F6F0E1" android:strokeAlpha="0.35" android:strokeWidth="0.6"' if f in (BLACK,FAR) else ''
            r.append(f'        <path android:pathData="{d}" android:fillColor="{f}"{rim} />')
        r.append('    </group>')
    return '\n'.join(r+['</vector>'])
