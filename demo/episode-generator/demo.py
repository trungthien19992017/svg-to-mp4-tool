"""Build illustrative assets only; never reads or writes the live Studio store."""
from pathlib import Path
import copy
import json
import zipfile
from generator import HERE, compile_episode


def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2).encode()


def fixture():
    files = {}
    for name, color in [('male', '#68d9e8'), ('female', '#ffb3cc')]:
        files['characters/robot-' + name + '.svg'] = ('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 1280">
<rect width="720" height="1280" fill="#142639"/>
<circle cx="575" cy="250" r="100" fill="#243f55"/>
<ellipse cx="360" cy="1030" rx="185" ry="28" fill="#0b1828"/>
<g id="body"><rect x="265" y="530" width="190" height="270" rx="45" fill="COLOR"/>
<rect x="280" y="800" width="60" height="210" rx="25" fill="#8ca9c2"/>
<rect x="380" y="800" width="60" height="210" rx="25" fill="#8ca9c2"/>
<g id="arm-left"><rect x="205" y="560" width="55" height="245" rx="25" fill="COLOR"/></g>
<g id="arm-right"><rect x="460" y="560" width="55" height="245" rx="25" fill="COLOR"/></g>
<g id="head"><rect x="220" y="260" width="280" height="245" rx="65" fill="COLOR"/>
<rect x="248" y="310" width="224" height="145" rx="35" fill="#142639"/>
<g id="face-neutral"><circle cx="300" cy="360" r="15" fill="#fff3ce"/><circle cx="420" cy="360" r="15" fill="#fff3ce"/><path d="M325 405 L395 405" stroke="#fff3ce" stroke-width="9"/></g>
<!--EXTRA_EXPRESSION-->
</g></g></svg>'''.replace('COLOR', color)).encode()
    files['characters/character-rig.json'] = encoded({'version': 'robot-demo-v1', 'joints': {
        'body': {'nodeId': 'body', 'pivot': [360, 800]},
        'head': {'nodeId': 'head', 'pivot': [360, 490]},
        'leftArm': {'nodeId': 'arm-left', 'pivot': [232, 570]},
        'rightArm': {'nodeId': 'arm-right', 'pivot': [487, 570]}},
        'anchors': {'leftSole': [310, 1010], 'rightSole': [410, 1010]}})
    manifest = {'schemaVersion': 'demo-1', 'kitId': 'robot-series-demo', 'version': '1.0.0',
                'rigVersion': 'robot-demo-v1', 'rig': 'characters/character-rig.json',
                'catalogs': {'characters': 'characters/character-catalog.json',
                             'poses': 'characters/pose-catalog.json', 'expressions': 'characters/expression-catalog.json',
                             'motions': 'motions/motion-catalog.json'},
                'notice': 'Illustrative geometry, not approved production artwork. Supported applies to this tested demo only.'}
    files['production-manifest.json'] = encoded(manifest)
    files['characters/character-catalog.json'] = encoded([
        {'id': name, 'artwork': 'characters/robot-' + name + '.svg', 'status': 'Supported'} for name in ('male', 'female')])
    files['characters/pose-catalog.json'] = encoded([
        {'id': 'idle', 'rigVersion': 'robot-demo-v1', 'status': 'Supported', 'rotations': {}}])
    files['characters/expression-catalog.json'] = encoded([
        {'id': 'neutral', 'rigVersion': 'robot-demo-v1', 'status': 'Supported', 'nodeId': 'face-neutral'}])
    files['motions/motion-library.js'] = b'export function evaluate(t,d) {return {head: Math.sin(Math.PI*t/d)*8};}\n'
    files['motions/motion-catalog.json'] = encoded([motion('nod', 'motions/motion-library.js')])
    files['motions/interaction-catalog.json'] = encoded([])
    files['environments/rainy-room/environment-config.json'] = encoded({'status': 'Unavailable', 'note': 'Reserved; not rendered in this demo'})
    files['audio/audio-catalog.json'] = encoded([])
    files['storytelling/series-bible.md'] = b'Demo only. Storytelling rules are not executed.\n'
    for name in ('story-patterns', 'scene-templates', 'character-personalities', 'episode-rules'):
        files['storytelling/' + name + '.json'] = encoded({})
    root = HERE.parents[1]
    for name in ('story.schema.json', 'animation-code-contract.md'):
        files['contracts/' + name] = (root / 'docs' / name).read_bytes()
    return files


def motion(name, module, pose='idle'):
    return {'id': name, 'module': module, 'rigVersion': 'robot-demo-v1', 'status': 'Supported',
            'startPose': pose, 'endPose': pose, 'duration': 4,
            'requiredJoints': ['head', 'leftArm', 'rightArm'], 'anchors': ['leftSole', 'rightSole'],
            'qaScope': 'Synthetic demo fixture; requires browser regression, not production approval'}


def add_expression(files):
    files = dict(files)
    face = '<g id="face-happy"><path d="M282 365 Q300 337 318 365 M402 365 Q420 337 438 365 M325 393 Q360 440 395 393" fill="none" stroke="#fff3ce" stroke-width="10" stroke-linecap="round"/></g>'
    for name in ('male', 'female'):
        path = 'characters/robot-' + name + '.svg'
        files[path] = files[path].replace(b'<!--EXTRA_EXPRESSION-->', face.encode())
    records = json.loads(files['characters/expression-catalog.json'])
    records.append({'id': 'happy', 'nodeId': 'face-happy', 'rigVersion': 'robot-demo-v1', 'status': 'Supported'})
    files['characters/expression-catalog.json'] = encoded(records)
    return version(files, '1.1.0')


def add_pose(files):
    files = dict(files)
    records = json.loads(files['characters/pose-catalog.json'])
    records.append({'id': 'arms-open', 'rigVersion': 'robot-demo-v1', 'status': 'Supported',
                    'rotations': {'leftArm': 32, 'rightArm': -32}})
    files['characters/pose-catalog.json'] = encoded(records)
    records = json.loads(files['motions/motion-catalog.json'])
    records.append(motion('nod-open', 'motions/motion-library.js', 'arms-open'))
    files['motions/motion-catalog.json'] = encoded(records)
    return version(files, '1.2.0')


def add_motion(files):
    files = dict(files)
    files['motions/wave.js'] = b'export function evaluate(t,d) {return {rightArm: -55*Math.sin(Math.PI*t/d)**2, head: 4*Math.sin(4*Math.PI*t/d)};}\n'
    records = json.loads(files['motions/motion-catalog.json'])
    records.append(motion('wave', 'motions/wave.js'))
    files['motions/motion-catalog.json'] = encoded(records)
    return version(files, '1.3.0')


def version(files, value):
    manifest = json.loads(files['production-manifest.json'])
    manifest['version'] = value
    files['production-manifest.json'] = encoded(manifest)
    return files


def write_kit(files, path):
    with zipfile.ZipFile(path, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr('robot-series-production-kit/' + name, data)


def episode(**changes):
    return dict({'id': 'robot-demo', 'title': 'Robot Production Kit Demo', 'character': 'male',
                 'pose': 'idle', 'expression': 'neutral', 'motion': 'nod'}, **changes)


def main():
    output = HERE / 'generated'
    output.mkdir(exist_ok=False)
    files = fixture()
    variants = [('base', files, episode()),
                ('A-expression', add_expression(files), episode(expression='happy')),
                ('B-pose', add_pose(files), episode(pose='arms-open', motion='nod-open')),
                ('C-motion', add_motion(files), episode(motion='wave', character='female'))]
    for name, pack, spec in variants:
        folder = output / name
        folder.mkdir()
        kit = folder / 'production-kit.zip'
        write_kit(pack, kit)
        (folder / 'episode.json').write_bytes(encoded(spec))
        compiled = compile_episode(kit, spec, folder / 'episode.zip')
        for path, data in compiled.items():
            target = folder / 'story' / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    (output / 'index.html').write_bytes((HERE / 'preview.html').read_bytes())
    print('Created', output)
    print('Preview: python -m http.server 5198 --bind 127.0.0.1 --directory "' + str(output) + '"')


if __name__ == '__main__':
    main()
