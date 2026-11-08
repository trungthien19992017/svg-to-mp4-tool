"""Isolated Production Kit -> self-contained Story v1 compiler (stdlib only)."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import io
import json
import math
import re
import stat
import zipfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


def fail(message):
    raise ValueError(message)


def safe_path(name):
    if not isinstance(name, str) or not name or len(name) > 200:
        fail('Invalid path')
    parts = name.split('/')
    if any(p in ('', '.', '..') or p.endswith(('.', ' ')) or
           re.match(r'^(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\.|$)', p, re.I) for p in parts):
        fail('Unsafe path: ' + name)
    if not re.fullmatch(r'[A-Za-z0-9_ ./-]+', name):
        fail('Unsafe path: ' + name)
    return name


class Kit:
    def __init__(self, source):
        source = Path(source)
        if source.stat().st_size > 64_000_000:
            fail('Kit ZIP exceeds 64 MB')
        self.files = {}
        total = 0
        with zipfile.ZipFile(source) as archive:
            entries = archive.infolist()
            if len(entries) > 600:
                fail('Too many ZIP entries')
            manifests = [i.filename for i in entries if PurePosixPath(i.filename).name == 'production-manifest.json']
            if len(manifests) != 1:
                fail('Expected exactly one production-manifest.json')
            prefix = manifests[0][:-len('production-manifest.json')]
            seen = set()
            for entry in entries:
                safe_path(entry.filename.rstrip('/'))
                if not entry.filename.startswith(prefix):
                    fail('Files outside kit root')
                mode = entry.external_attr >> 16
                if stat.S_ISLNK(mode):
                    fail('Symlink forbidden')
                if entry.is_dir():
                    continue
                name = safe_path(entry.filename[len(prefix):])
                if name.casefold() in seen:
                    fail('Duplicate path: ' + name)
                seen.add(name.casefold())
                total += entry.file_size
                if entry.file_size > 16_000_000 or total > 128_000_000 or entry.file_size / max(1, entry.compress_size) > 200:
                    fail('ZIP size/ratio limit exceeded')
                self.files[name] = archive.read(entry)
        self.manifest = self.read('production-manifest.json')
        if self.manifest.get('schemaVersion') != 'demo-1':
            fail('Unsupported kit schema. Map your real catalogs to demo-1 explicitly; no guessing.')
        for field in ('kitId', 'rigVersion'):
            if not ID.fullmatch(self.manifest.get(field, '')):
                fail('Invalid ' + field)
        if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', self.manifest.get('version', '')):
            fail('Expected numeric major.minor.patch version')
        self.rig = self.read(self.manifest['rig'])
        if self.rig['version'] != self.manifest['rigVersion']:
            fail('Breaking rig version: migration required')
        self.characters = self.catalog('characters')
        self.poses = self.catalog('poses')
        self.expressions = self.catalog('expressions')
        self.motions = self.catalog('motions')
        for record in [*self.poses.values(), *self.expressions.values(), *self.motions.values()]:
            if record.get('rigVersion') != self.rig['version']:
                fail('Breaking rig contract: migration required for ' + record['id'])
        self.svg_ids = {}
        for record in self.characters.values():
            path = record['artwork']
            self.svg_ids[path] = self.validate_svg(path)
            for joint, binding in self.rig['joints'].items():
                if binding['nodeId'] not in self.svg_ids[path]:
                    fail('Missing joint ' + joint + ' in ' + path)
                if len(binding['pivot']) != 2 or not all(isinstance(n, (int, float)) and math.isfinite(n) for n in binding['pivot']):
                    fail('Invalid pivot: ' + joint)
        for pose in self.poses.values():
            for joint, angle in pose['rotations'].items():
                if joint not in self.rig['joints'] or not isinstance(angle, (int, float)) or not math.isfinite(angle):
                    fail('Invalid pose joint/angle: ' + pose['id'])
        for expression in self.expressions.values():
            for ids in self.svg_ids.values():
                if expression['nodeId'] not in ids:
                    fail('Missing expression node: ' + expression['id'])
        for motion in self.motions.values():
            self.bytes(motion['module'])
            if not motion['module'].endswith('.js'):
                fail('Adapter must be a local .js module')
            if any(j not in self.rig['joints'] for j in motion['requiredJoints']):
                fail('Missing required joint')
            if any(a not in self.rig.get('anchors', {}) for a in motion['anchors']):
                fail('Missing required anchor')
            if motion['startPose'] not in self.poses or motion['endPose'] not in self.poses:
                fail('Missing start/end pose')
            if not isinstance(motion['duration'], (int, float)) or not math.isfinite(motion['duration']) or not .25 <= motion['duration'] <= 600:
                fail('Invalid motion duration')

    def bytes(self, path):
        safe_path(path)
        if path not in self.files:
            fail('Missing dependency: ' + path)
        return self.files[path]

    def read(self, path):
        return json.loads(self.bytes(path))

    def catalog(self, kind):
        records = self.read(self.manifest['catalogs'][kind])
        result = {}
        for record in records:
            name = record.get('id', '')
            if not ID.fullmatch(name) or name in result:
                fail('Invalid/duplicate catalog ID: ' + name)
            result[name] = record
        return result

    def validate_svg(self, path):
        data = self.bytes(path)
        if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
            fail('SVG DTD/entity forbidden')
        root = ET.fromstring(data)
        if root.tag != '{http://www.w3.org/2000/svg}svg':
            fail('Expected SVG root')
        allowed = {'svg', 'g', 'path', 'rect', 'circle', 'ellipse', 'line', 'polyline', 'polygon', 'defs', 'linearGradient', 'radialGradient', 'stop', 'title', 'desc'}
        ids, refs = set(), []
        for node in root.iter():
            if node.tag.split('}')[-1] not in allowed:
                fail('Unsupported/active SVG element')
            if node.get('id'):
                if not ID.fullmatch(node.get('id')) or node.get('id') in ids:
                    fail('Invalid/duplicate SVG ID')
                ids.add(node.get('id'))
            for key, value in node.attrib.items():
                key = key.split('}')[-1].lower()
                lower = value.lower()
                if key.startswith('on') or any(x in lower for x in ('http:', 'https:', 'file:', 'data:', 'javascript:', '@import', '\\')):
                    fail('Unsafe SVG attribute')
                if key == 'href':
                    if not value.startswith('#'):
                        fail('External SVG reference')
                    refs.append(value[1:])
                if 'url(' in lower:
                    matches = re.findall(r'url\(#([A-Za-z0-9_-]+)\)', value)
                    if value.count('url(') != len(matches):
                        fail('Unsupported SVG URL')
                    refs.extend(matches)
        if any(ref not in ids for ref in refs):
            fail('Unresolved SVG fragment')
        return ids


def supported(catalog, name):
    record = catalog.get(name)
    if not record or record.get('status') != 'Supported':
        fail('Capability is not Supported: ' + str(name))
    return record


def compile_episode(source, episode, output):
    kit = Kit(source)
    if not ID.fullmatch(episode.get('id', '')):
        fail('Invalid episode ID')
    motion = supported(kit.motions, episode['motion'])
    pose = supported(kit.poses, episode['pose'])
    if pose['id'] != motion['startPose'] or pose['id'] != motion['endPose']:
        fail('Demo only supports motions returning to the selected pose')
    expression = supported(kit.expressions, episode['expression'])
    actor = supported(kit.characters, episode['character'])
    artwork = actor['artwork']
    duration = motion['duration']
    payload = {'rig': kit.rig, 'pose': pose, 'expression': expression,
               'expressionNodes': [r['nodeId'] for r in kit.expressions.values()],
               'duration': duration, 'assetId': 'actor-art'}
    module = motion['module']
    # Helper imports must remain relative .js imports supported by the Studio.
    adapter_import = '../' + module
    scene = ('import {createEpisode} from "../modules/episode-runtime.js";\n'
             'import {evaluate} from ' + json.dumps(adapter_import) + ';\n'
             'export function createScene(context) {\n  return createEpisode(context, '
             + json.dumps(payload, ensure_ascii=False) + ', evaluate);\n}\n')
    story = {'schemaVersion': '1.0', 'projectId': episode['id'], 'title': episode.get('title', episode['id']),
             'video': {'width': 720, 'height': 1280, 'fps': 24, 'format': 'mp4'},
             'assets': [{'id': 'actor-art', 'path': artwork}],
             'scenes': [{'id': 'scene-001', 'source': 'scenes/scene-001.js', 'duration': duration,
                         'transition': {'type': 'cut', 'duration': 0}}]}
    lock = {'kitId': kit.manifest['kitId'], 'version': kit.manifest['version'],
            'rigVersion': kit.rig['version'], 'kitSha256': hashlib.sha256(Path(source).read_bytes()).hexdigest(),
            'files': {p: hashlib.sha256(b).hexdigest() for p, b in sorted(kit.files.items())},
            'selected': {k: episode[k] for k in ('character', 'pose', 'expression', 'motion')}}
    files = {'story.json': json.dumps(story, ensure_ascii=False).encode(),
             'scenes/scene-001.js': scene.encode(), artwork: kit.bytes(artwork),
             'modules/episode-runtime.js': (HERE / 'episode-runtime.js').read_bytes(),
             'metadata/production-lock.json': json.dumps(lock, indent=2).encode()}
    # Copy adapter dependencies, not just the entry point. Importer validates them again.
    for path, data in kit.files.items():
        if path.endswith('.js'):
            if path in files:
                fail('Reserved generated file: ' + path)
            files[path] = data
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation: an existing episode artifact is never overwritten.
    with output.open('xb') as stream:
        with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path, data in sorted(files.items()):
                archive.writestr(path, data)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    validate = commands.add_parser('validate')
    validate.add_argument('kit')
    build = commands.add_parser('compile')
    build.add_argument('kit')
    build.add_argument('episode')
    build.add_argument('output')
    args = parser.parse_args()
    try:
        if args.command == 'validate':
            kit = Kit(args.kit)
            print('PASS structural validation:', kit.manifest['kitId'], kit.manifest['version'])
            print('Adapter execution and visual QA are separate checks; import does not certify Supported.')
        else:
            compile_episode(args.kit, json.loads(Path(args.episode).read_text(encoding='utf-8')), args.output)
            print('Created:', args.output)
    except (ValueError, KeyError, OSError, zipfile.BadZipFile, ET.ParseError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
