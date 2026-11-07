"""Build the self-contained four-scene sample without external services/assets."""
from pathlib import Path
import json,math,random,struct,wave,zipfile,shutil

ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'samples/lost-star'
files={
'assets/characters/may.svg':'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 220">
<g id="body"><ellipse cx="100" cy="150" rx="52" ry="55" fill="#e9b886"/><ellipse cx="100" cy="165" rx="28" ry="35" fill="#fff0cf"/></g>
<g id="left-leg"><ellipse cx="70" cy="203" rx="20" ry="12" fill="#e9b886"/></g><g id="right-leg"><ellipse cx="130" cy="203" rx="20" ry="12" fill="#e9b886"/></g>
<g id="left-arm"><ellipse cx="48" cy="150" rx="12" ry="33" fill="#dd9c70"/></g><g id="right-arm"><ellipse cx="152" cy="150" rx="12" ry="33" fill="#dd9c70"/></g>
<g id="head"><path d="M44 70 L40 10 L82 40 Q100 30 119 40 L160 10 L157 73" fill="#e9b886"/><path d="M50 47 L48 24 L70 43 M132 43 L152 24 L150 47" fill="#e39b9b"/>
<ellipse cx="100" cy="79" rx="61" ry="51" fill="#f4cd99"/><g id="eyes" fill="#342d43"><ellipse cx="77" cy="75" rx="5" ry="8"/><ellipse cx="123" cy="75" rx="5" ry="8"/></g>
<g id="mouth"><path d="M94 88 L106 88 L100 95 Z" fill="#b36c74"/><path d="M100 95 Q91 108 84 98 M100 95 Q109 108 116 98" fill="none" stroke="#704c55" stroke-width="3" stroke-linecap="round"/></g>
<path d="M54 91 L19 84 M54 99 L19 103 M146 91 L181 84 M146 99 L181 103" stroke="#ad7c63" stroke-width="2"/></g>
<path id="tail" d="M149 174 Q212 154 172 120" fill="none" stroke="#e9b886" stroke-width="19" stroke-linecap="round"/>
</svg>''',
'assets/backgrounds/forest.svg':'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><defs><linearGradient id="sky" x2="0" y2="1"><stop stop-color="#18253e"/><stop offset="1" stop-color="#516a81"/></linearGradient></defs><rect width="1280" height="720" fill="url(#sky)"/><circle cx="1050" cy="130" r="55" fill="#fff0bc"/><g fill="#e8ecc9"><circle cx="90" cy="75" r="2"/><circle cx="360" cy="110" r="3"/><circle cx="570" cy="60" r="2"/><circle cx="760" cy="150" r="3"/><circle cx="1180" cy="60" r="2"/></g><path d="M0 550 Q260 380 520 540 Q800 380 1280 530 V720 H0Z" fill="#2c5356"/><path d="M0 615 Q260 470 620 595 Q940 465 1280 570 V720 H0Z" fill="#1e4149"/><g fill="#16343f"><path d="M80 620 V260 L0 390 H40 L0 470 H30 L0 560 H150 L118 470 H155 L118 390 H156Z"/><path d="M1180 620 V240 L1095 380 H1135 L1095 470 H1125 L1090 565 H1270 L1220 470 H1260 L1220 380 H1260Z"/></g><path d="M0 675 Q450 610 1280 655 V720 H0Z" fill="#14343b"/></svg>''',
'assets/objects/star.svg':'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="-60 -60 120 120"><path id="star-body" d="M0 -55 L16 -18 L56 -17 L26 9 L35 49 L0 28 L-35 49 L-26 9 L-56 -17 L-16 -18Z" fill="#ffe29b" stroke="#fff3c9" stroke-width="4"/><circle cx="-12" cy="0" r="3" fill="#7b6548"/><circle cx="12" cy="0" r="3" fill="#7b6548"/><path d="M-8 12 Q0 20 8 12" fill="none" stroke="#7b6548" stroke-width="3"/></svg>'''
}
descriptions=['Mây bắt gặp một ngôi sao rơi trong khu rừng đêm.','Mây đi theo ánh sáng, tìm thấy ngôi sao buồn.','Mây giúp ngôi sao lấy lại ánh sáng và bay lên.','Ngôi sao trở về bầu trời; Mây vẫy tay chào.']
for i in range(1,5):
    setup='''const {gsap}=context;
  context.addSvg(context.assetText('forest'));
  const cat=context.character('may',{id:'hero',x:100,y:450,scale:1});
  const star=context.addSvg(context.assetText('star'),{id:'lost-star',x:760,y:260,scale:.7});
  const caption=context.addSvg('<svg xmlns="http://www.w3.org/2000/svg"><text x="640" y="80" text-anchor="middle" fill="#fff0cf" font-family="Segoe UI, Arial" font-size="28">CAPTION</text></svg>');
  const timeline=context.timeline();
  timeline.fromTo(caption,{opacity:0},{opacity:1,duration:1},0);
  timeline.fromTo(cat.querySelector('#eyes'),{scaleY:1},{scaleY:.1,transformOrigin:'center',duration:.12,yoyo:true,repeat:1},2);
'''.replace('CAPTION',descriptions[i-1])
    motions={
        1:"""timeline.fromTo(cat,{x:80},{x:420,duration:7,ease:'none'},0);
  timeline.fromTo(cat.querySelector('#left-arm'),{rotation:-15},{rotation:15,transformOrigin:'50% 0',duration:.5,yoyo:true,repeat:11},0);
  timeline.fromTo(star,{x:930,y:20,rotation:-30,opacity:0},{x:760,y:360,rotation:25,opacity:1,duration:5,ease:'power2.in'},1);
  timeline.fromTo(context.camera,{scale:1,x:0},{scale:1.07,x:-30,duration:8},0);""",
        2:"""timeline.set(cat,{x:420},0);
  timeline.fromTo(cat,{x:420},{x:660,duration:6,ease:'sine.inOut'},0);
  timeline.fromTo(star,{x:760,y:360},{x:810,y:460,duration:5,ease:'sine.inOut'},0);
  timeline.fromTo(star,{rotation:-10},{rotation:10,duration:1,yoyo:true,repeat:5},0);
  timeline.fromTo(context.camera,{scale:1.07,x:-30},{scale:1.17,x:-100,duration:8},0);""",
        3:"""timeline.set(cat,{x:650},0);
  timeline.fromTo(cat.querySelector('#right-arm'),{rotation:0},{rotation:-100,transformOrigin:'50% 0',duration:2,ease:'sine.inOut'},1);
  timeline.fromTo(star,{scale:.7},{scale:1.15,duration:2,yoyo:true,repeat:1},0);
  timeline.to(star,{duration:5,motionPath:{path:[{x:810,y:460},{x:920,y:300},{x:800,y:100},{x:1040,y:120}],curviness:1.3},ease:'sine.inOut'},3);
  timeline.fromTo(context.camera,{scale:1.17,x:-100},{scale:1.05,x:0,duration:8},0);""",
        4:"""timeline.set(cat,{x:650},0);timeline.set(star,{x:1040,y:120,scale:.55},0);
  timeline.fromTo(cat.querySelector('#right-arm'),{rotation:-90},{rotation:-125,transformOrigin:'50% 0',duration:.4,yoyo:true,repeat:15},0);
  timeline.fromTo(star,{rotation:-8},{rotation:8,duration:1,yoyo:true,repeat:7},0);
  timeline.fromTo(context.camera,{scale:1.05,x:0},{scale:1,x:0,duration:8},0);"""
    }[i]
    files[f'scenes/scene-{i:03}.js']='export function createScene(context) {\n  '+setup+motions+"\n  return {duration:9,seek(time){timeline.time(time,true);},reset(){timeline.pause(0);},dispose(){timeline.kill();}};\n}\n"
manifest={'schemaVersion':'1.0','projectId':'may-and-the-lost-star','title':'Mèo Mây và ngôi sao lạc','description':'Một câu chuyện 4 cảnh về tình bạn, cùng nhân vật SVG xuyên suốt.','seed':42,'video':{'width':1280,'height':720,'fps':30,'format':'mp4'},'render':{'crf':18,'preset':'veryfast'},'assets':[{'id':'cat-art','path':'assets/characters/may.svg','type':'character'},{'id':'forest','path':'assets/backgrounds/forest.svg','type':'background'},{'id':'star','path':'assets/objects/star.svg','type':'object'},{'id':'chime','path':'audio/sfx/chime.wav','type':'audio'}],'characters':[{'id':'may','assetId':'cat-art','parts':['head','body','left-arm','right-arm','left-leg','right-leg','eyes','mouth','tail']}],'scenes':[{'id':f'scene-{i:03}','name':['Ngôi sao rơi','Theo ánh sáng','Cất cánh','Lời chào'][i-1],'duration':9,'source':f'scenes/scene-{i:03}.js','characters':['may'],'background':'forest','transition':{'type':['fade','slide','fade','cut'][i-1],'duration':.5 if i<4 else 0}} for i in range(1,5)],'audio':[{'id':'discovery','assetId':'chime','sceneId':'scene-002','start':2,'offset':0,'duration':3,'volume':.35,'fadeIn':.1,'fadeOut':1},{'id':'return','assetId':'chime','sceneId':'scene-004','start':1,'offset':0,'duration':3,'volume':.25,'fadeIn':.1,'fadeOut':1}]}
manifest['duration']=34.5
files['story.json']=json.dumps(manifest,ensure_ascii=False,indent=2)
files['metadata/storyboard.json']=json.dumps({'story':descriptions,'continuity':'Dùng duy nhất character asset may.svg và background forest.svg trong cả bốn cảnh.'},ensure_ascii=False,indent=2)
for name,text in files.items():
    file=folder/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(text,encoding='utf-8')
audio=folder/'audio/sfx/chime.wav';audio.parent.mkdir(parents=True,exist_ok=True)
rng=random.Random(42);rate=44100
with wave.open(str(audio),'wb') as out:
    out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate)
    samples=[]
    for n in range(rate*4):
        t=n/rate;value=(math.sin(2*math.pi*660*t)+.5*math.sin(2*math.pi*990*t))*math.exp(-1.2*t)*.25+rng.uniform(-.001,.001)
        samples.append(struct.pack('<h',int(max(-1,min(1,value))*32767)))
    out.writeframes(b''.join(samples))
archive=ROOT/'samples/lost-star.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as zip:
    for file in folder.rglob('*'):
        if file.is_file():zip.write(file,file.relative_to(folder).as_posix())
target=ROOT/'src/SvgToMp4.Web/wwwroot/story/samples';target.mkdir(parents=True,exist_ok=True);shutil.copyfile(archive,target/'lost-star.zip')
print(f'Created 4-scene / 34.5s Story ZIP: {archive}')
