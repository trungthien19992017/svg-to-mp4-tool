"""A/B/C integration and rejection checks. No live Studio requests or data writes."""
import functools
import hashlib
import http.server
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile
from generator import HERE, Kit, compile_episode
from demo import fixture, add_expression, add_pose, add_motion, episode, encoded, write_kit

ROOT = HERE.parents[1]


class Checks(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / 'work' / 'episode-generator-checks'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='run-', dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def pack(self, files, name='kit.zip'):
        target = self.folder / name
        write_kit(files, target)
        return target

    def test_ABC_core_unchanged_and_self_contained(self):
        core = [HERE / 'generator.py', HERE / 'episode-runtime.js']
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in core]
        files = fixture()
        cases = [('A', add_expression(files), episode(expression='happy'), 'face-happy'),
                 ('B', add_pose(files), episode(pose='arms-open', motion='nod-open'), 'arms-open'),
                 ('C', add_motion(files), episode(motion='wave'), 'motions/wave.js')]
        for name, pack, spec, expected in cases:
            with self.subTest(name=name):
                result = compile_episode(self.pack(pack, name + '.zip'), spec, self.folder / (name + '-episode.zip'))
                text = b'\n'.join(result.values()).decode('utf-8')
                self.assertIn(expected, text)
                lock = json.loads(result['metadata/production-lock.json'])
                self.assertEqual(lock['selected']['motion'], spec['motion'])
                for path, source in result.items():
                    if path.endswith('.js'):
                        checked = subprocess.run(['node', '--input-type=module', '--check'], input=source, capture_output=True)
                        self.assertEqual(checked.returncode, 0, checked.stderr.decode())
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in core])

    def test_reject_partial_and_breaking_rig(self):
        files = fixture()
        poses = json.loads(files['characters/pose-catalog.json'])
        poses[0]['status'] = 'Partial'
        files['characters/pose-catalog.json'] = encoded(poses)
        with self.assertRaisesRegex(ValueError, 'not Supported'):
            compile_episode(self.pack(files), episode(), self.folder / 'blocked.zip')
        files = fixture()
        rig = json.loads(files['characters/character-rig.json'])
        rig['version'] = 'robot-v2'
        files['characters/character-rig.json'] = encoded(rig)
        with self.assertRaisesRegex(ValueError, 'migration'):
            Kit(self.pack(files, 'breaking.zip'))

    def test_reject_unsafe_svg_missing_joint_and_traversal(self):
        for name, value in [('script', b'<script/>'), ('remote', b'<image href="https://example.com/a.png"/>')]:
            files = fixture()
            path = 'characters/robot-male.svg'
            files[path] = files[path].replace(b'<!--EXTRA_EXPRESSION-->', value)
            with self.assertRaises(ValueError):
                Kit(self.pack(files, name + '.zip'))
        files = fixture()
        files['characters/robot-male.svg'] = files['characters/robot-male.svg'].replace(b'id="head"', b'id="lost-head"')
        with self.assertRaisesRegex(ValueError, 'Missing joint'):
            Kit(self.pack(files, 'missing.zip'))
        files = fixture()
        files['../escape.json'] = b'{}'
        with self.assertRaisesRegex(ValueError, 'Unsafe path'):
            Kit(self.pack(files, 'traversal.zip'))

    def test_never_overwrite_episode(self):
        kit = self.pack(fixture())
        out = self.folder / 'episode.zip'
        compile_episode(kit, episode(), out)
        before = out.read_bytes()
        with self.assertRaises(FileExistsError):
            compile_episode(kit, episode(), out)
        self.assertEqual(before, out.read_bytes())


def browser_check():
    sys.path[:0] = [str(ROOT / 'engine' / '.packages'), str(ROOT / 'engine')]
    from playwright.sync_api import sync_playwright
    from render import browser_executable

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    handler = functools.partial(QuietHandler, directory=str(HERE / 'generated'))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    report = {'scope': 'Isolated demo context; not Studio import/export or MP4 acceptance', 'cases': []}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=browser_executable(), headless=True)
            try:
                page = browser.new_page(viewport={'width': 1200, 'height': 1000}, device_scale_factor=1)
                errors = []
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.goto('http://127.0.0.1:' + str(server.server_port))
                for name in ('base', 'A-expression', 'B-pose', 'C-motion'):
                    page.select_option('#variant', name)
                    page.wait_for_function("document.querySelector('#status').textContent === 'Sẵn sàng · ' + document.querySelector('#variant').value")
                    snapshots = {}
                    for t in (0, 1, 2, 4, .25, 2, 0, 4):
                        page.evaluate('(t)=>window.demo.seek(t)', t)
                        state = page.locator('#stage').inner_html()
                        if t in snapshots:
                            assert snapshots[t] == state, (name, 'seek differs', t)
                        snapshots[t] = state
                    assert snapshots[0] != snapshots[2], (name, 'motion did not change DOM')
                    # Motion returns to the same pose at both endpoints, within floating precision.
                    angles = page.evaluate('''() => {const s = document.querySelector('#stage');
                      window.demo.seek(0);const a=[...s.querySelectorAll('[transform]')].map(n=>n.getAttribute('transform'));
                      window.demo.seek(4);const b=[...s.querySelectorAll('[transform]')].map(n=>n.getAttribute('transform'));
                      return [a,b];}''')
                    import re
                    numbers = lambda states: [float(n) for state in states for n in re.findall(r'-?\d+(?:\.\d+)?(?:e[-+]?\d+)?', state)]
                    a, b = map(numbers, angles)
                    assert len(a) == len(b) and all(abs(x-y) < 1e-8 for x,y in zip(a,b))
                    page.evaluate('window.demo.scene.reset()')
                    assert page.locator('#stage').inner_html() == snapshots[0]
                    if name == 'A-expression':
                        assert page.locator('#stage [id$="face-happy"]').get_attribute('visibility') == 'visible'
                        assert page.locator('#stage [id$="face-neutral"]').get_attribute('visibility') == 'hidden'
                    if name == 'B-pose':
                        assert 'rotate(32 ' in page.locator('#stage [id$="arm-left"]').get_attribute('transform')
                    if name == 'C-motion':
                        page.evaluate('window.demo.seek(2)')
                        assert 'rotate(-55 ' in page.locator('#stage [id$="arm-right"]').get_attribute('transform')
                        page.screenshot(path=str(HERE / 'generated' / 'preview.png'), full_page=True)
                    page.evaluate('window.demo.scene.dispose();window.demo.scene.dispose()')
                    assert page.locator('#stage > g').count() == 0
                    report['cases'].append({'case': name, 'status': 'PASS', 'checks': ['actual DOM changes', 'arbitrary seek', 'reset', 'endpoint continuity', 'idempotent dispose']})
                assert not errors, errors
                report['status'] = 'PASS'
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
    (HERE / 'generated' / 'verification.json').write_bytes(encoded(report))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    if '--browser' in sys.argv:
        browser_check()
    else:
        unittest.main()
