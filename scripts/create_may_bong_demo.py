"""Author the self-contained v1 demo source. Final ZIP is exported by the app API."""
from pathlib import Path
import json, math, random, struct, wave

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'samples/may-bong-episode-01'


def write(name, text):
    target = PROJECT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding='utf-8')


def svg(body):
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 1280">' + body + '</svg>'


def forest():
    art = '''<defs>
      <linearGradient id="sky" x2="0" y2="1"><stop stop-color="#142f3a"/><stop offset="1" stop-color="#658b88"/></linearGradient>
      <linearGradient id="water" x2="0" y2="1"><stop stop-color="#41696b"/><stop offset="1" stop-color="#102e3b"/></linearGradient>
      <linearGradient id="wood" x2="1" y2="0"><stop stop-color="#513f32"/><stop offset=".5" stop-color="#856044"/><stop offset="1" stop-color="#3d3530"/></linearGradient>
      <radialGradient id="glow"><stop stop-color="#ffdb8b" stop-opacity=".7"/><stop offset="1" stop-color="#ffdb8b" stop-opacity="0"/></radialGradient>
    </defs><rect width="720" height="1280" fill="url(#sky)"/>
    '''
    rng = random.Random(42)
    for layer in range(3):
        for i in range(11):
            x = i * 83 - 60 + rng.randrange(45)
            y = rng.randrange(-170, 160)
            color = ['#638382', '#345c60', '#21494e'][layer]
            art += f'<g opacity="{.35 + layer*.16}" fill="{color}"><path d="M{x} {y}l-82 390h43l-95 210h84l-94 190h210l-94-190h77l-91-210h39z"/><rect x="{x-7}" y="{y+350}" width="16" height="610"/></g>'
    art += '''<path d="M370 720Q660 650 720 835V1280H0V1010Q230 900 370 720" fill="url(#water)"/>
    <path d="M0 820Q200 760 380 825Q460 890 355 970Q240 1090 0 1080Z" fill="#253f3a"/>
    <path d="M0 1020Q180 950 345 1000L285 1090L0 1150Z" fill="#1e3732"/>
    <path d="M-40 160L394 108L510 345L-30 385Z" fill="#263332" stroke="#13292d" stroke-width="12"/>
    <path d="M-30 195L398 150M-25 242L428 202M-15 294L457 254M-20 343L487 307" stroke="#516056" stroke-width="5"/>
    <path d="M0 354L365 323V787H0Z" fill="url(#wood)"/>
    <path d="M0 410L365 384M0 484L365 460M0 560L365 536M0 636L365 612M0 710L365 688" stroke="#392e29" stroke-width="5"/>
    <rect x="24" y="424" width="175" height="248" rx="10" fill="#3b302a"/>
    <rect x="36" y="436" width="150" height="220" fill="#f2b762"/>
    <path d="M110 435V660M35 546H190" stroke="#6b4a30" stroke-width="13"/>
    <path d="M49 444V536M124 444V536M49 563V643M124 563V643" stroke="#ffe1a1" stroke-width="5" opacity=".7"/>
    <path d="M337 331L374 328V826H337Z" fill="url(#wood)"/>
    <path d="M369 353L439 296" stroke="#6d503b" stroke-width="20"/>
    <circle cx="310" cy="447" r="138" fill="url(#glow)"/>
    <path d="M310 356V388" stroke="#211f22" stroke-width="5"/>
    <path d="M282 407L310 383L338 407L331 469H289Z" fill="#392f29" stroke="#241f20" stroke-width="5"/>
    <path d="M291 412L329 412L324 458H296Z" fill="#ffd68a"/>
    <path d="M310 412V458" stroke="#9a713e" stroke-width="4"/>
    <path d="M0 780L428 747L442 800L0 855Z" fill="#4a392f" stroke="#2c2b29" stroke-width="6"/>
    <path d="M0 791L428 759M0 812L433 778M73 783L86 831M222 772L240 815M367 760L381 802" stroke="#b58a5a" stroke-width="3" opacity=".6"/>
    <path d="M44 845V1001M342 811V939" stroke="#4b3c30" stroke-width="30"/>
    '''
    for x, y, s in [(35,1030,1.3),(161,1003,1),(284,1030,.9),(390,932,1),(555,827,.8),(670,907,1.2),(74,1190,1.2)]:
        art += f'<g transform="translate({x} {y}) scale({s})"><ellipse rx="58" ry="35" fill="#354944" stroke="#1b3434" stroke-width="5"/><path d="M-46-8Q-15-45 39-12Q8-24-46-8" fill="#6e8155"/><path d="M-25-19L-14-24M3-26L20-23" stroke="#a5ad6c" stroke-width="3"/></g>'
    for i in range(45):
        x = rng.randrange(720); y = rng.choice([rng.randrange(850,1040),rng.randrange(1110,1280)])
        if 320 < x < 590: continue
        art += f'<path d="M{x} {y}q-35-46-45-20q10 23 45 20q28-52 40-27q-4 22-40 27" fill="{rng.choice(["#64825a","#3c6151","#829063"])}" stroke="#26443e" stroke-width="2"/>'
    for x,y in [(38,974),(98,1104),(168,1068),(644,893),(683,1020)]:
        art += f'<g transform="translate({x} {y})" fill="#dba09a"><circle cx="-9" r="8"/><circle cx="9" r="8"/><circle cy="-10" r="8"/><circle cy="10" r="8"/><circle r="5" fill="#edc875"/></g>'
    return svg(art)


def fox(sleeping=False):
    # Parts are real editable groups; coordinates are local to each character instance.
    eyes = '<path d="M-39-70q12 12 24 0M15-70q12 12 24 0" fill="none" stroke="#44352f" stroke-width="5" stroke-linecap="round"/>' if sleeping else '<ellipse cx="-27" cy="-72" rx="9" ry="13" fill="#382b27"/><ellipse cx="28" cy="-72" rx="9" ry="13" fill="#382b27"/><circle cx="-24" cy="-77" r="3" fill="#fff8e9"/><circle cx="31" cy="-77" r="3" fill="#fff8e9"/>'
    return svg('''<g stroke="#fff0d5" stroke-width="7" stroke-linejoin="round">
    <g id="tail"><path d="M50 41C150 76 178-15 127-86C117-41 63-40 65 10" fill="#daa267"/><path d="M127-86Q163-32 148 0L121-15L117 7L96-7Q111-25 127-86" fill="#ffdfac" stroke="none"/></g>
    <g id="body"><ellipse cy="11" rx="68" ry="72" fill="#efc590"/><ellipse cy="26" rx="43" ry="49" fill="#ffe4b6" stroke="none"/></g>
    <g id="head"><path d="M-73-76L-77-166Q-38-154-22-124Q0-133 25-124Q43-153 78-159L72-78L88-58L65-40Q0-4-66-40L-85-54Z" fill="#f5cf98"/>
    <path d="M-65-139L-60-96L-37-116ZM64-136L35-114L61-97Z" fill="#dc9f85" stroke="none"/>
    <path d="M-67-65Q-41-32 0-40Q40-32 67-65Q49-7 0-18Q-50-7-67-65" fill="#fff0cf" stroke="none"/>
    <g id="eyes">''' + eyes + '''</g><g fill="#eea58a" stroke="none"><ellipse cx="-48" cy="-49" rx="12" ry="7"/><ellipse cx="49" cy="-49" rx="12" ry="7"/></g>
    <path d="M-5-48Q0-53 6-48L0-43Z" fill="#624538" stroke="#624538" stroke-width="3"/>
    <path d="M0-42V-37M-12-37Q-6-30 0-37Q7-30 13-37" fill="none" stroke="#624538" stroke-width="2.5"/>
    </g><g id="paws" fill="#f7d7a3"><ellipse cx="-42" cy="67" rx="26" ry="17"/><ellipse cx="42" cy="67" rx="26" ry="17"/></g>
    <g id="arm" fill="#f6d09a"><ellipse cx="-52" cy="12" rx="17" ry="29" transform="rotate(-25 -52 12)"/></g></g>''')


def main():
    write('assets/backgrounds/rainy-cabin.svg', forest())
    write('assets/characters/may.svg', fox())
    write('assets/characters/bong.svg', fox(True))
    write('assets/objects/book.svg', svg('''<g stroke="#fff0d5" stroke-width="5" stroke-linejoin="round"><path d="M-67-38Q-27-48 0-23Q27-48 67-38L58 40Q22 29 0 47Q-22 29-58 40Z" fill="#eadbbb"/><path d="M-69-29L-58 45Q-25 31 0 51Q25 31 58 45L69-29Q32-36 0-10Q-32-36-69-29Z" fill="#355765"/><path d="M0-10V51" fill="none"/><path d="M12 4L48-8M12 15L43 5M-13 3L-47-8" stroke="#acbaaa" stroke-width="2"/></g>'''))
    write('assets/objects/cup.svg', svg('''<g stroke="#fff0d5" stroke-width="4"><path d="M25-29Q65-32 53 3Q48 14 28 7" fill="none" stroke-width="9"/><path d="M-30-30H31L27 23Q0 38-27 23Z" fill="#ba785d"/><ellipse cy="-30" rx="31" ry="8" fill="#f5d9ad"/><ellipse cy="-30" rx="25" ry="5" fill="#664334"/><path d="M-19-17L-17 16" stroke="#e5ac87"/></g>'''))
    write('assets/objects/doodles.svg', svg('''<g fill="none" stroke="#f8f0da" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M464 515C442 494 452 481 463 492C475 474 490 493 464 515Z"/><path d="M590 699v22m-11-11h22M477 1000v18m-9-9h18M183 582l-8-15m29 6v-18m21 24l8-16"/><path d="M600 1050q35-10 30-40m0 0l-12 8m12-8l7 12" stroke-dasharray="5 7"/></g>'''))
    audio = PROJECT / 'audio/rain.wav'; audio.parent.mkdir(parents=True,exist_ok=True)
    rng=random.Random(811); low=0.; samples=bytearray(); rate=22050
    for i in range(rate*14):
        noise=rng.uniform(-1,1); low=.97*low+.03*noise
        gain=min(1,i/(rate*.7),(rate*14-i)/(rate*.9))
        value=(noise*.11+low*.42)*gain*(.84+.16*math.sin(i/rate*1.3))
        samples.extend(struct.pack('<h',int(value*32767)))
    with wave.open(str(audio),'wb') as out:
        out.setparams((1,2,rate,0,'NONE','not compressed'));out.writeframes(samples)
    assets=[{'id':key,'path':path,'type':kind} for key,path,kind in [
        ('cabin','assets/backgrounds/rainy-cabin.svg','background'),('may-art','assets/characters/may.svg','character'),
        ('bong-art','assets/characters/bong.svg','character'),('book','assets/objects/book.svg','object'),
        ('cup','assets/objects/cup.svg','object'),('doodles','assets/objects/doodles.svg','object'),('rain','audio/rain.wav','audio')]]
    scenes=[]
    for i,(name,mood) in enumerate([('Một hiên nhà, hai người bạn','read'),('Một tách trà ấm','share'),('Bình yên ở ngay đây','rest')],1):
        path=f'scenes/scene-{i:03}.js'
        write(path,"import {createCozyScene} from '../modules/cozy-engine.js';\nexport function createScene(context){return createCozyScene(context,"+json.dumps(mood)+");}\n")
        scenes.append({'id':f'scene-{i:03}','name':name,'duration':5,'source':path,'characters':['may','bong'],'background':'cabin','transition':{'type':'fade' if i<3 else 'cut','duration':.5 if i<3 else 0}})
    manifest={'schemaVersion':'1.0','projectId':'may-bong-episode-01','title':'Mây & Bông · Hiên nhà ngày mưa','description':'Ba khoảnh khắc nhỏ bên hiên rừng: đọc sách, chia hơi ấm và nghỉ ngơi. Original vector artwork inspired by the supplied rainy forest reference.','seed':811,'video':{'width':720,'height':1280,'fps':24,'format':'mp4'},'render':{'width':720,'height':1280,'fps':24,'crf':18,'preset':'veryfast'},'assets':assets,'characters':[{'id':name,'assetId':name+'-art','parts':['body','head','eyes','tail','arm','paws']} for name in ['may','bong']],'scenes':scenes,'audio':[{'id':'rain-bed','assetId':'rain','start':0,'offset':0,'duration':14,'volume':.6,'fadeIn':.4,'fadeOut':.7}]}
    write('story.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('Authored',PROJECT,'(final ZIP must use application export)')


if __name__ == '__main__':main()
