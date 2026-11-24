import os
B="static/images/"
def w(path, s): open(B+path,"w").write(s)
MARK='''<rect width="64" height="64" rx="16" fill="url(#g)"/>
<polygon points="32,11 51,21.5 32,32 13,21.5" fill="#fff" fill-opacity=".30"/>
<path d="M32 11 51 21.5v21L32 53 13 42.5v-21Z" fill="none" stroke="#fff" stroke-width="3.4" stroke-linejoin="round"/>
<rect x="29.4" y="26" width="5.2" height="17" rx="2.6" fill="#fff"/>'''
DEF='<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3B82F6"/><stop offset="1" stop-color="#1D4ED8"/></linearGradient></defs>'
w("logo/logo-mark.svg", f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64" role="img" aria-label="INDPNS Market">{DEF}{MARK}</svg>')
w("logo/favicon.svg", f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">{DEF}{MARK}</svg>')
for name,col,sub in (("logo-full.svg","#111827","#6B7280"),("logo-full-light.svg","#F3F4F6","#9CA3AF")):
    w("logo/"+name, f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 64" width="280" height="64" role="img" aria-label="INDPNS Market">{DEF}{MARK}<text x="76" y="40" font-family="Inter,system-ui,Segoe UI,Arial,sans-serif" font-size="27" font-weight="800" letter-spacing="-0.5" fill="{col}">INDPNS<tspan font-weight="500" fill="{sub}"> Market</tspan></text></svg>')
G={
"code":'<path d="m16 18 6-6-6-6"/><path d="m8 6-6 6 6 6"/>',
"layout":'<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/>',
"plug":'<path d="M12 22v-5"/><path d="M9 8V2"/><path d="M15 8V2"/><path d="M18 8v5a4 4 0 0 1-4 4h-4a4 4 0 0 1-4-4V8Z"/>',
"layers":'<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
"spark":'<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>',
"box":'<path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
}
def cat(name,c1,c2,glyph):
    w(f"cats/{name}.svg", f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 300" preserveAspectRatio="xMidYMid slice"><defs><linearGradient id="a" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs>
<rect width="480" height="300" fill="url(#a)"/><circle cx="410" cy="40" r="120" fill="#fff" fill-opacity=".08"/><circle cx="40" cy="290" r="140" fill="#fff" fill-opacity=".08"/>
<g fill="none" stroke="#fff" stroke-opacity=".18" stroke-width="2"><rect x="70" y="50" width="90" height="60" rx="10"/><rect x="330" y="190" width="100" height="56" rx="10"/><path d="M60 230h70M60 246h44"/></g>
<rect x="180" y="75" width="120" height="120" rx="26" fill="#fff" fill-opacity=".96"/>
<g transform="translate(204 99) scale(3)" fill="none" stroke="{c2}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{G[glyph]}</g></svg>''')
cat("source-code","#2563EB","#1E3A8A","code"); cat("templates-themes","#7C3AED","#4C1D95","layout")
cat("plugins-extensions","#0891B2","#134E4A","plug"); cat("ui-components","#DB2777","#831843","layers")
cat("ai-tools-agents","#F59E0B","#B45309","spark"); cat("sdks-libraries","#059669","#064E3B","box")
cat("default","#475569","#1E293B","box"); cat("placeholder-cover","#E2E8F0","#94A3B8","box")
BL,LB,SO,IN,GR,AM,ST="#2563EB","#60A5FA","#DBEAFE","#4F46E5","#10B981","#F59E0B","#CBD5E1"
def svg(vb,body,extra=""): return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" {extra}>{body}</svg>'
def win(x,y,w,h,inner="",r=14): return (f'<g><rect x="{x+4}" y="{y+8}" width="{w}" height="{h}" rx="{r}" fill="#0F172A" fill-opacity=".08"/><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="#fff" stroke="#E2E8F0"/><rect x="{x}" y="{y}" width="{w}" height="26" rx="{r}" fill="#F1F5F9"/><rect x="{x}" y="{y+14}" width="{w}" height="12" fill="#F1F5F9"/><circle cx="{x+16}" cy="{y+13}" r="4" fill="#F87171"/><circle cx="{x+30}" cy="{y+13}" r="4" fill="#FBBF24"/><circle cx="{x+44}" cy="{y+13}" r="4" fill="#34D399"/>{inner}</g>')
def line(x,y,w,c=ST,h=7): return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" fill="{c}"/>'
def pcard(x,y,w,h,c1,c2,price=True):
    i=f"p{x}{y}"
    s=f'<g><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#fff" stroke="#E2E8F0"/><defs><linearGradient id="{i}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/><stop offset="1" stop-color="{c2}"/></linearGradient></defs><rect x="{x+6}" y="{y+6}" width="{w-12}" height="{h*0.5}" rx="7" fill="url(#{i})"/>'
    s+=line(x+8,y+h*0.5+16,w*0.6,"#CBD5E1")+line(x+8,y+h*0.5+30,w*0.35,"#E2E8F0")
    if price: s+=f'<rect x="{x+w-46}" y="{y+h-26}" width="38" height="16" rx="8" fill="{SO}"/>'
    return s+'</g>'
def check(cx,cy,r=14,c=GR): return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{c}"/><path d="M{cx-r*0.4} {cy+r*0.05} l{r*0.28} {r*0.3} l{r*0.55} {-r*0.6}" fill="none" stroke="#fff" stroke-width="{r*0.22}" stroke-linecap="round" stroke-linejoin="round"/>'
def shield(cx,cy,s=1,c=BL): return (f'<g transform="translate({cx} {cy}) scale({s})"><path d="M0 -44 38 -30V4C38 26 20 40 0 48 -20 40 -38 26 -38 4V-30Z" fill="{c}"/><path d="M0 -44 38 -30V4C38 26 20 40 0 48Z" fill="#fff" fill-opacity=".12"/><path d="m-14 2 10 10 20-22" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/></g>')
def stars(x,y,n=5): return "".join(f'<polygon transform="translate({x+i*16} {y}) scale(.6)" points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" fill="{AM}"/>' for i in range(n))
def spark(x,y,s=1,c=LB): return f'<path transform="translate({x} {y}) scale({s})" d="M0 -12 3 -3 12 0 3 3 0 12 -3 3 -12 0 -3 -3Z" fill="{c}"/>'
bg=lambda c="#EFF6FF": f'<circle cx="260" cy="190" r="170" fill="{c}"/>'
w("hero/hero.svg", svg("0 0 720 560", f'''<defs><linearGradient id="h2" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#A78BFA"/><stop offset="1" stop-color="#6D28D9"/></linearGradient></defs>
<circle cx="380" cy="290" r="230" fill="#3B82F6" fill-opacity=".10"/><circle cx="560" cy="130" r="70" fill="#8B5CF6" fill-opacity=".12"/>
{win(70,80,500,350, line(94,122,120,"#CBD5E1",9)+line(94,142,70,"#E2E8F0")+f'<rect x="440" y="116" width="106" height="30" rx="8" fill="{BL}"/>'+pcard(94,170,140,130,"#3B82F6","#1D4ED8")+pcard(250,170,140,130,"#A78BFA","#6D28D9")+pcard(406,170,140,130,"#34D399","#047857")+line(94,330,300,"#E2E8F0")+line(94,348,220,"#F1F5F9")+line(94,372,180,"#E2E8F0"),18)}
<g><rect x="30" y="360" width="236" height="132" rx="14" fill="#0F172A"/><circle cx="52" cy="380" r="4" fill="#F87171"/><circle cx="66" cy="380" r="4" fill="#FBBF24"/><circle cx="80" cy="380" r="4" fill="#34D399"/>{line(52,402,70,"#60A5FA")}{line(130,402,90,"#A78BFA")}{line(66,422,110,"#34D399")}{line(52,442,150,"#94A3B8")}{line(66,462,80,"#F59E0B")}{line(156,462,60,"#60A5FA")}</g>
<g><rect x="470" y="340" width="212" height="112" rx="14" fill="#fff" stroke="#E2E8F0"/><circle cx="504" cy="376" r="18" fill="url(#h2)"/>{line(534,366,90,"#CBD5E1",9)}{line(534,384,60,"#E2E8F0")}{stars(494,410)}{line(494,424,150,"#E2E8F0")}<rect x="598" y="352" width="72" height="18" rx="9" fill="#ECFDF5"/><path d="m608 361 4 4 8-8" fill="none" stroke="{GR}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></g>
{shield(620,150,.8)}{spark(100,60,1.1)}{spark(660,300,.9,"#A78BFA")}{spark(330,470,.8,"#34D399")}''', 'preserveAspectRatio="xMidYMid meet"'))
w("illustrations/empty.svg", svg("0 0 240 180", f'''<ellipse cx="120" cy="156" rx="78" ry="10" fill="#94A3B8" fill-opacity=".25"/><path d="M62 78 120 58l58 20-58 20Z" fill="#BFDBFE"/><path d="M62 78v50l58 20V98Z" fill="#93C5FD"/><path d="M178 78v50l-58 20V98Z" fill="#60A5FA"/><path d="M62 78 38 62l50-18 32 14Z" fill="#DBEAFE"/><path d="M178 78l24-16-50-18-32 14Z" fill="#DBEAFE"/>{spark(52,34,1,LB)}{spark(196,30,.8,"#A78BFA")}{spark(204,110,.6,"#34D399")}'''))
w("illustrations/auth.svg", svg("0 0 520 460", f'''<circle cx="260" cy="230" r="200" fill="#fff" fill-opacity=".10"/>{win(110,90,300,250, line(140,140,100,"#CBD5E1",9)+f'<rect x="140" y="170" width="240" height="32" rx="8" fill="#F1F5F9" stroke="#E2E8F0"/><rect x="140" y="214" width="240" height="32" rx="8" fill="#F1F5F9" stroke="#E2E8F0"/><rect x="140" y="262" width="240" height="34" rx="9" fill="{BL}"/>'+line(160,181,70,"#CBD5E1")+line(160,225,90,"#CBD5E1"),16)}
{shield(400,120,1.0)}<g transform="translate(86 300)"><circle r="34" fill="#fff"/><path d="M-10 6v-8a10 10 0 0 1 20 0v8" fill="none" stroke="{BL}" stroke-width="5" stroke-linecap="round"/><rect x="-16" y="4" width="32" height="24" rx="6" fill="{BL}"/><circle cx="0" cy="15" r="3.5" fill="#fff"/></g>{spark(60,100,1.2,"#BFDBFE")}{spark(450,330,1,"#BFDBFE")}{spark(250,400,.8,"#BFDBFE")}'''))
w("illustrations/seller.svg", svg("0 0 520 380", f'''{bg()}<rect x="90" y="120" width="340" height="190" rx="14" fill="#fff" stroke="#E2E8F0"/><path d="M80 120h360l-18-56H98Z" fill="{BL}"/>{"".join(f'<path d="M{98+i*60} 64h30l-6 56h-18Z" fill="#fff" fill-opacity="{0.25 if i%2 else 0.9}"/>' for i in range(6))}
<path d="M80 120h360v18a30 30 0 0 1-60 0 30 30 0 0 1-60 0 30 30 0 0 1-60 0 30 30 0 0 1-60 0 30 30 0 0 1-60 0 30 30 0 0 1-60 0Z" fill="#1D4ED8"/>{pcard(112,170,100,110,"#3B82F6","#1D4ED8")}{pcard(228,170,100,110,"#A78BFA","#6D28D9")}{pcard(344,170,70,110,"#34D399","#047857",False)}
<g transform="translate(400 250)"><rect width="110" height="80" rx="12" fill="#fff" stroke="#E2E8F0"/><path d="M14 58 38 38l18 12 22-26 18 14" fill="none" stroke="{GR}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>{line(14,14,50,"#CBD5E1")}</g>{spark(60,90,1.2)}{spark(470,100,1,"#A78BFA")}'''))
w("illustrations/secure.svg", svg("0 0 420 320", f'''{bg("#ECFDF5")}<g transform="translate(-50 0)">{win(110,70,230,180, line(134,114,120,"#CBD5E1",9)+line(134,136,170,"#E2E8F0")+line(134,154,140,"#E2E8F0")+f'<rect x="134" y="184" width="100" height="30" rx="8" fill="{BL}"/>',14)}</g>{shield(300,170,1.5,GR)}{spark(70,70,1.1,"#6EE7B7")}{spark(360,60,.9,"#93C5FD")}'''))
w("illustrations/license.svg", svg("0 0 420 320", f'''{bg()}<g transform="rotate(-6 200 170)"><rect x="115" y="58" width="190" height="240" rx="12" fill="#0F172A" fill-opacity=".08"/><rect x="110" y="50" width="190" height="240" rx="12" fill="#fff" stroke="#E2E8F0"/>{line(134,82,100,"#CBD5E1",10)}{line(134,106,140,"#E2E8F0")}{line(134,124,128,"#E2E8F0")}{line(134,142,150,"#E2E8F0")}{line(134,160,90,"#E2E8F0")}{check(148,198,9)}{line(166,194,90,"#E2E8F0")}{check(148,224,9)}{line(166,220,70,"#E2E8F0")}{check(148,250,9)}{line(166,246,100,"#E2E8F0")}</g>
<g transform="translate(300 230)"><path d="M-18 20l-10 40 28-14 28 14-10-40Z" fill="{AM}"/><circle r="34" fill="{AM}"/><circle r="26" fill="none" stroke="#fff" stroke-width="3" stroke-opacity=".7"/><path d="M-12 0 -4 8 12 -8" fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/></g>{spark(80,80,1.1)}{spark(350,90,.9,"#A78BFA")}'''))
w("illustrations/download.svg", svg("0 0 420 380", f'''{bg()}<rect x="150" y="30" width="130" height="270" rx="22" fill="#0F172A"/><rect x="158" y="44" width="114" height="242" rx="14" fill="#fff"/><rect x="190" y="36" width="50" height="6" rx="3" fill="#334155"/>{"".join(f'<rect x="{170+(i%3)*34}" y="{66+(i//3)*42}" width="26" height="26" rx="7" fill="{c}"/>' for i,c in enumerate([BL,IN,GR,AM,LB,"#F472B6"]))}{line(172,160,80,"#E2E8F0")}{line(172,178,56,"#F1F5F9")}<rect x="172" y="212" width="86" height="30" rx="9" fill="{BL}"/><path d="M215 220v10m-5-4 5 5 5-5" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
<g transform="translate(300 90)"><rect width="84" height="84" rx="12" fill="#fff" stroke="#E2E8F0"/>{"".join(f'<rect x="{10+(i%5)*13}" y="{10+(i//5)*13}" width="9" height="9" rx="1.5" fill="#0F172A" fill-opacity="{1 if (i*7)%3 else .15}"/>' for i in range(25))}</g>{spark(90,70,1.2)}{spark(120,250,.9,"#A78BFA")}'''))
w("illustrations/help.svg", svg("0 0 420 320", f'''{bg()}<rect x="70" y="70" width="200" height="90" rx="18" fill="{BL}"/><path d="M110 160v30l30-30Z" fill="{BL}"/>{line(94,98,120,"#fff",9)}{line(94,118,150,"#BFDBFE")}{line(94,134,90,"#BFDBFE")}
<rect x="170" y="170" width="190" height="84" rx="18" fill="#fff" stroke="#E2E8F0"/>{line(194,196,110,"#CBD5E1",9)}{line(194,216,140,"#E2E8F0")}<g transform="translate(330 90)"><circle r="30" fill="{AM}"/><text y="14" text-anchor="middle" font-family="Inter,system-ui,Arial" font-size="40" font-weight="800" fill="#fff">?</text></g>{spark(70,230,1,"#A78BFA")}'''))
w("illustrations/404.svg", svg("0 0 420 260", f'''<text x="210" y="165" text-anchor="middle" font-family="Inter,system-ui,Arial,sans-serif" font-size="150" font-weight="800" fill="#2563EB" fill-opacity=".14">404</text>
<g transform="translate(210 110)"><path d="M-46 -20 0 -44 46 -20V30L0 54 -46 30Z" fill="#BFDBFE"/><path d="M-46 -20 0 4V54L-46 30Z" fill="#93C5FD"/><path d="M46 -20 0 4V54L46 30Z" fill="#60A5FA"/><path d="M-46 -20 0 -44 46 -20 0 4Z" fill="#DBEAFE"/></g>{spark(90,60,1.2)}{spark(340,70,1,"#A78BFA")}{spark(320,200,.8,"#34D399")}<ellipse cx="210" cy="226" rx="70" ry="8" fill="#94A3B8" fill-opacity=".25"/>'''))
w("illustrations/banner.svg", svg("0 0 1200 240", '''<defs><linearGradient id="b" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#2563EB"/><stop offset="1" stop-color="#4F46E5"/></linearGradient></defs><rect width="1200" height="240" fill="url(#b)"/><g fill="#fff" fill-opacity=".10"><circle cx="1050" cy="30" r="170"/><circle cx="120" cy="250" r="150"/><circle cx="640" cy="260" r="100"/></g><g fill="none" stroke="#fff" stroke-opacity=".22" stroke-width="2"><rect x="760" y="60" width="140" height="90" rx="14"/><rect x="920" y="110" width="120" height="80" rx="14"/><rect x="300" y="40" width="110" height="70" rx="12"/></g>''', 'preserveAspectRatio="xMidYMid slice"'))
for n,(c,gl) in {"step-search":(BL,G["layout"]),"step-license":(IN,G["code"]),"step-download":(GR,G["box"])}.items():
    w(f"illustrations/{n}.svg", svg("0 0 96 96", f'<rect width="96" height="96" rx="24" fill="{c}" fill-opacity=".12"/><g transform="translate(24 24) scale(2)" fill="none" stroke="{c}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{gl}</g>'))

# PNG icons / OG
from PIL import Image, ImageDraw, ImageFont
def mark(size, maskable=False):
    S=size*4; im=Image.new("RGBA",(S,S),(0,0,0,0))
    g=Image.new("RGBA",(S,S)); px=g.load()
    for y in range(S):
        for x in range(S):
            t=(x+y)/(2*S); px[x,y]=(int(59+(29-59)*t),int(130+(78-130)*t),int(246+(216-246)*t),255)
    mask=Image.new("L",(S,S),0); md=ImageDraw.Draw(mask)
    if maskable: md.rectangle((0,0,S,S),fill=255)
    else: md.rounded_rectangle((0,0,S,S),radius=int(S*0.25),fill=255)
    im.paste(g,(0,0),mask); k=S/64.0; sc=0.78 if maskable else 1.0
    P=lambda x,y:(S/2+(x-32)*k*sc,S/2+(y-32)*k*sc)
    ov=Image.new("RGBA",(S,S),(0,0,0,0)); ImageDraw.Draw(ov).polygon([P(32,11),P(51,21.5),P(32,32),P(13,21.5)],fill=(255,255,255,77))
    im=Image.alpha_composite(im,ov); d=ImageDraw.Draw(im)
    pts=[P(32,11),P(51,21.5),P(51,42.5),P(32,53),P(13,42.5),P(13,21.5),P(32,11)]
    d.line(pts,fill="white",width=int(3.4*k*sc),joint="curve")
    for p in pts: d.ellipse((p[0]-1.7*k*sc,p[1]-1.7*k*sc,p[0]+1.7*k*sc,p[1]+1.7*k*sc),fill="white")
    d.rounded_rectangle((*P(29.4,26),*P(34.6,43)),radius=int(2.6*k*sc),fill="white")
    return im.resize((size,size),Image.LANCZOS)
ic="static/icons/"
mark(192).save(ic+"icon-192.png"); mark(512).save(ic+"icon-512.png"); mark(512,True).save(ic+"icon-maskable-512.png"); mark(180).save(ic+"apple-touch-icon.png"); mark(64).save(B+"logo/logo-mark.png")
W,H=1200,630; og=Image.new("RGB",(W,H)); d=ImageDraw.Draw(og)
for y in range(H):
    t=y/H; d.line((0,y,W,y),fill=(int(37+(79-37)*t),int(99+(70-99)*t),int(235+(229-235)*t)))
d=ImageDraw.Draw(og,"RGBA"); d.ellipse((760,-140,1320,420),fill=(255,255,255,26)); d.ellipse((-120,380,420,860),fill=(255,255,255,26))
m=mark(150); og.paste(m,(90,90),m)
def font(sz,b=True):
    try: return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf"%("-Bold" if b else ""),sz)
    except Exception: return ImageFont.load_default()
d.text((270,110),"INDPNS Market",font=font(64),fill="white")
d.text((90,300),"Professional digital products",font=font(58),fill="white")
d.text((90,380),"Source code, templates, plugins, SDKs and AI tools",font=font(32,False),fill=(255,255,255,220))
d.text((90,540),"market.indpns.com",font=font(30),fill=(255,255,255,230))
og.save(B+"og-image.png")
