"""Build the explicitly illustrative production-profile sample, not a live registry entry."""
from pathlib import Path
import json
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'demo' / 'episode-generator'))
from demo import fixture, add_expression, add_pose, add_motion, encoded

files = add_motion(add_pose(add_expression(fixture())))
manifest = json.loads(files['production-manifest.json'])
manifest.update(schemaVersion='production-1', kitId='robot-series-example', version='1.0.0',
                title='Robot Series — Kit minh họa', demo=True,
                video={'width':720, 'height':1280, 'fps':24, 'format':'mp4'})
manifest['catalogs'].update(environments='environments/environment-catalog.json',
                             audio='audio/audio-catalog.json', templates='storytelling/scene-templates.json')
files['production-manifest.json'] = encoded(manifest)
ET.register_namespace('', 'http://www.w3.org/2000/svg')
for name in ('male','female'):
    path = 'characters/robot-' + name + '.svg'
    svg = ET.fromstring(files[path])
    for node in list(svg):
        if node.tag.rsplit('}',1)[-1] != 'g':
            svg.remove(node)
    files[path] = ET.tostring(svg, encoding='utf-8')
files['environments/rainy-room/room.svg'] = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 1280"><rect width="720" height="1280" fill="#142639"/><rect x="60" y="100" width="600" height="500" rx="30" fill="#26445b"/><circle cx="560" cy="210" r="60" fill="#587c96"/><path d="M180 150v390M360 150v390M540 150v390M100 330h520" stroke="#3b6078" stroke-width="12"/><rect y="1030" width="720" height="250" fill="#1c3245"/></svg>'
files['environments/environment-catalog.json'] = encoded([{'id':'room', 'label':'Căn phòng minh họa', 'status':'Supported', 'artwork':'environments/rainy-room/room.svg'}])
rig = json.loads(files['characters/character-rig.json'])
rig['joints']['head']['parent'] = 'body'
rig['joints']['leftArm']['parent'] = 'body'
rig['joints']['rightArm']['parent'] = 'body'
files['characters/character-rig.json'] = encoded(rig)
def actor(character='male', pose='idle', motion='nod', expression='neutral'):
    return {'id':'hero', 'character':character, 'pose':pose, 'expression':expression, 'motion':motion, 'x':0, 'y':0, 'scale':1}
scenes = [
    {'id':'scene-001','name':'Một lời chào','duration':4,'caption':'Một ngày mới, một lời chào.','environment':'room','actors':[actor(expression='happy')],'transition':{'type':'cut','duration':0}},
    {'id':'scene-002','name':'Đón niềm vui','duration':4,'caption':'Mở lòng với những điều nhỏ bé.','environment':'room','actors':[actor('female','arms-open','nod-open','happy')],'transition':{'type':'cut','duration':0}},
    {'id':'scene-003','name':'Hẹn gặp lại','duration':4,'caption':'Hẹn bạn ở tập tiếp theo!','environment':'room','actors':[actor(motion='wave',expression='happy')],'transition':{'type':'cut','duration':0}}]
files['storytelling/scene-templates.json'] = encoded([{'id':'greeting-three-scenes','title':'Lời chào · 3 cảnh / 12 giây','scenes':scenes}])
files['storytelling/series-bible.md'] = 'Robot minh họa kể các câu chuyện ngắn, ấm áp. Chỉ sử dụng capability thực sự có trong catalog. Không có thoại hoặc TTS tự động.\n'.encode()
spec = {'schemaVersion':'episode-1','kitId':manifest['kitId'],'kitVersion':manifest['version'],
        'id':'robot-episode-01','title':'Một lời chào nhỏ','video':manifest['video'],'scenes':scenes}
target = ROOT / 'src/SvgToMp4.Web/wwwroot/episodes/production-kit-demo.zip'
target.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
    for path,data in sorted(files.items()):archive.writestr('robot-series-production-kit/'+path,data)
(ROOT / 'samples/production-episode.json').write_bytes(encoded(spec))
print('Created illustrative kit:', target)
