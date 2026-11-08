"""Create a versioned experimental front-view kit without touching the source archive."""
from pathlib import Path
import hashlib
import io
import json
import re
import wave
import zipfile
import xml.etree.ElementTree as ET
import argparse

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/robot-series-production-kit-structured.zip'
OUT = ROOT / 'outputs/robot-series-front-test-v0.1.0'
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)


def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8')


def main():
    global SOURCE, OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=SOURCE)
    parser.add_argument('--output',type=Path,default=OUT)
    parser.add_argument('--kit-id',default='robot-series-front-test')
    parser.add_argument('--version',default='0.1.0')
    args=parser.parse_args()
    SOURCE=args.source.resolve(); OUT=args.output.resolve()
    OUT.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(SOURCE) as archive:
        source = {n.split('/', 1)[1]: archive.read(n) for n in archive.namelist() if not n.endswith('/')}
    files = {}
    source_rig = json.loads(source['characters/character-rig.json'])
    male_rig = next(r for r in source_rig['rigs'] if r['id'] == 'robot-men-front')
    rig_version = 'robot-front-trial-v1'
    joints = {n['id']: dict(nodeId='front--' + n['id'], pivot=n['pivot'], **({'parent': n['parent']} if n['parent'] else {})) for n in male_rig['nodes']}
    # Joint-local pivots/IDs are shared; original per-character mounts remain in each SVG.
    # Anchors vary by character and are not flattened or used for contact in this trial.
    files['characters/character-rig.json'] = encoded({'version':rig_version, 'joints':joints, 'anchors':{},
        'scope':'Front-view local rotations only. Per-character mounts preserved in immutable SVGs. No contact solver.'})
    for sex in ('male', 'female'):
        path = 'characters/robot-' + sex + '.svg'
        files[path] = source[path]
    files['characters/character-catalog.json'] = encoded([
        {'id':'robot-' + sex, 'label':'Robot ' + ('nam' if sex == 'male' else 'nữ') + ' · front · thử nghiệm',
         'status':'Partial', 'artwork':'characters/robot-' + sex + '.svg'} for sex in ('male','female')])
    expression_source = json.loads(source['characters/expression-catalog.json'])
    expressions = []
    for expression in expression_source['characters'][0]['expressions']:
        name = expression['id']
        statuses = {c['id']:next(e for e in c['expressions'] if e['id']==name)['views']['front']['status'] for c in expression_source['characters']}
        expressions.append({'id':name, 'label':name+' · thử nghiệm', 'status':'Partial', 'rigVersion':rig_version,
            'bindings':{'robot-male':'front--facial-men-front-expression-'+name, 'robot-female':'front--facial-women-front-expression-'+name},
            'sourceStatuses':statuses, 'qa':'Awaiting user visual testing; original status records preserved in provenance.'})
    files['characters/expression-catalog.json'] = encoded(expressions)
    files['characters/pose-catalog.json'] = encoded([
        {'id':'idle-front','label':'Đứng nghỉ · thử nghiệm','status':'Partial','rigVersion':rig_version,'rotations':{},'sourceStatus':'Partial'},
        {'id':'head-tilt-test','label':'Nghiêng đầu 3° · bản thử mới','status':'Partial','rigVersion':rig_version,'rotations':{'head':3},'sourceStatus':'New trial, not approved artwork'}])
    files['motions/head-gentle.js'] = b'export function evaluate(t,duration) {return {head:3*Math.sin(Math.PI*t/duration)};}\n'
    files['motions/arm-review.js'] = b'export function evaluate(t,duration) {return {"upper-arm-R":-6*Math.sin(Math.PI*t/duration),"forearm-R":-4*Math.sin(Math.PI*t/duration)};}\n'
    files['motions/motion-catalog.json'] = encoded([
        {'id':name, 'label':label, 'status':'Partial', 'rigVersion':rig_version, 'module':'motions/'+name+'.js',
         'startPose':'idle-front','endPose':'idle-front','duration':6,'requiredJoints':joints,'anchors':[],
         'qa':'New diagnostic adapter for user testing; not a port or approval of the Phase03 action library.'}
        for name,label,joints in [('head-gentle','Nghiêng đầu nhẹ 3° · thử nghiệm',['head']),('arm-review','Kiểm tra khớp tay 6° · thử nghiệm',['upper-arm-R','forearm-R'])]])
    # Preserve source episode layer ordering, with foreground above actors.
    def compose(names):
        root = ET.Element('{'+NS+'}svg', {'viewBox':'0 0 1080 1920'})
        for name in names:
            layer = ET.fromstring(source['environments/rainy-room/'+name+'.svg'])
            prefix = name+'--'
            for node in layer.iter():
                if node.get('id'):node.set('id',prefix+node.get('id'))
                for key,value in list(node.attrib.items()):
                    value=re.sub(r'url\(#([^)]*)\)',lambda m:'url(#'+prefix+m.group(1)+')',value)
                    if key.endswith('href') and value.startswith('#'):value='#'+prefix+value[1:]
                    node.set(key,value)
            group=ET.SubElement(root,'{'+NS+'}g',{'data-layer':name})
            for child in list(layer):group.append(child)
        return ET.tostring(root,encoding='utf-8')
    files['environments/rainy-room/back.svg']=compose(['background-far','rain-back','walls','rain-glass','window-reflections','floor','furniture'])
    files['environments/rainy-room/front.svg']=compose(['foreground','lighting'])
    files['environments/environment-catalog.json']=encoded([{'id':'rainy-room','label':'Phòng mưa · hình nền tĩnh cho bản thử','status':'Partial',
        'artwork':'environments/rainy-room/back.svg','foregroundArtwork':'environments/rainy-room/front.svg','note':'Rain geometry static in this trial; original compositing order preserved.'}])
    audio=[]
    for entry in json.loads(source['audio/audio-catalog.json'])['generatedAssets']:
        path=entry['path']
        if path not in source:continue
        files[path]=source[path]
        with wave.open(io.BytesIO(source[path])) as stream:duration=stream.getnframes()/stream.getframerate()
        audio.append({**entry,'id':entry['assetId'],'label':entry['assetId'],'status':'Partial','duration':duration,'qa':'Audio source preserved; playback acceptance pending.'})
    files['audio/audio-catalog.json']=encoded(audio)
    def actor(sex, expression='default', motion='', x=50):
        return {'id':sex,'character':'robot-'+sex,'pose':'idle-front','expression':expression,'motion':motion,'x':x,'y':760,'scale':1}
    scenes=[]
    for index,(title,expression,motion) in enumerate([('Artwork gốc · đứng nghỉ','default',''),('Biểu cảm · nghiêng đầu nhẹ','pleased','head-gentle'),('Kiểm tra khớp tay','cheerful','arm-review')],1):
        scenes.append({'id':'scene-00'+str(index),'name':title,'duration':6,'environment':'rainy-room','audio':'rain','volume':.18,
            'caption':'BẢN THỬ · '+title,'actors':[actor('male',expression,motion,30),actor('female',expression,motion,535)],'transition':{'type':'cut','duration':0}})
    files['storytelling/scene-templates.json']=encoded([{'id':'front-trial-three-scenes','title':'Kiểm tra front · 3 cảnh / 18 giây','scenes':scenes}])
    files['storytelling/series-bible.md']=('Bản thử front của hai robot dùng artwork thật. Không có tương tác tiếp xúc, đi bộ hoặc góc nhìn khác. Các chuyển động mới chỉ để kiểm tra khớp; không phải motion đã được duyệt.\n').encode('utf-8')
    for path in ['production-manifest.json','characters/character-rig.json','characters/expression-catalog.json','characters/pose-catalog.json','motions/motion-catalog.json']:
        files['provenance/source-'+path.replace('/','-')]=source[path]
    for name in ['story.schema.json','animation-code-contract.md']:
        files['contracts/'+name]=(ROOT/'docs'/name).read_bytes()
    for path,data in source.items():
        if path.startswith('storytelling/') and path.endswith(('.json','.md')):
            files['provenance/source-'+path.replace('/','-')]=data
    manifest={'schemaVersion':'production-1','kitId':args.kit_id,'title':'Robot thật · front · BẢN THỬ', 'version':args.version,'rigVersion':rig_version,
        'testOnly':True,'sourceKitSha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'rig':'characters/character-rig.json',
        'video':{'width':1080,'height':1920,'fps':24,'format':'mp4'},'defaultTemplate':'front-trial-three-scenes',
        'catalogs':{'characters':'characters/character-catalog.json','poses':'characters/pose-catalog.json','expressions':'characters/expression-catalog.json',
                    'motions':'motions/motion-catalog.json','environments':'environments/environment-catalog.json','audio':'audio/audio-catalog.json','templates':'storytelling/scene-templates.json'}}
    files['production-manifest.json']=encoded(manifest)
    files['asset-registry.json']=encoded({'hashAlgorithm':'SHA-256','assets':[{'path':p,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for p,b in sorted(files.items())]})
    kit=OUT/(args.kit_id+'-v'+args.version+'.zip')
    with zipfile.ZipFile(kit,'x',zipfile.ZIP_DEFLATED) as archive:
        for path,data in sorted(files.items()):archive.writestr('robot-series-front-test/'+path,data)
    spec={'schemaVersion':'episode-1','kitId':manifest['kitId'],'kitVersion':manifest['version'],'allowExperimental':True,
        'id':'robot-front-trial-01','title':'Robot thật · Kiểm tra front 18 giây','video':manifest['video'],'scenes':scenes}
    (OUT/'episode.json').write_bytes(encoded(spec))
    (OUT/'README.txt').write_text('BẢN THỬ, chưa nghiệm thu production. Import episode.zip vào Story Studio để xem ngay; nhập Kit ZIP sau khi cập nhật/restart ứng dụng. Artwork robot giữ nguyên bytes; môi trường mưa tĩnh; motion mới để kiểm tra khớp; không tự nâng status Partial.\n',encoding='utf-8')
    print('Created trial kit:',kit)


if __name__=='__main__':main()
