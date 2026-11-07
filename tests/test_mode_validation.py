"""Regression: ordinary SVG selected as doodle must fail before queuing work."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'engine/.packages'),str(ROOT/'engine')]
from playwright.sync_api import sync_playwright
from render import browser_executable

BASE='http://127.0.0.1:5188'

def wait_until(check,timeout=20):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if check():return
        time.sleep(.1)
    raise AssertionError('Timed out waiting for UI')

with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=browser_executable(),headless=True,chromium_sandbox=True,timeout=20000)
    try:
        page=browser.new_page(viewport={'width':1440,'height':1100})
        errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(BASE+'/whiteboard',wait_until='networkidle')
        wait_until(lambda:page.evaluate("typeof token==='string'&&token.length>0"))
        page.locator('#fileInput').set_input_files(str(ROOT/'samples/01-ngoi-nha-mau.svg'))
        wait_until(lambda:page.locator('#projectName').input_value()=='01-ngoi-nha-mau')
        assert page.locator('#effect').input_value()=='whiteboard'
        page.locator('#hand').select_option('white')
        page.locator('#effect').select_option('doodle')
        wait_until(lambda:page.locator('#modeNotice').is_visible())
        posted=[]
        page.on('request',lambda r:posted.append(r.url) if r.method=='POST' and r.url.endswith('/api/renders') else None)
        for button in ['previewButton','exportButton']:
            page.locator('#'+button).click()
            assert 'Nét trước, màu sau' in page.locator('#message').inner_text()
        assert not posted,'Invalid mode unexpectedly queued a job'
        # Reload the saved mismatched draft: show recovery, never silently switch.
        wait_until(lambda:page.evaluate("JSON.parse(localStorage.getItem('net-studio-draft-v1')).settings.effect==='doodle'"))
        page.reload(wait_until='networkidle')
        assert page.locator('#effect').input_value()=='doodle'
        assert page.locator('#modeNotice').is_visible()
        page.locator('#useWhiteboard').click()
        assert page.locator('#effect').input_value()=='whiteboard'
        assert page.locator('#hand').input_value()=='white'
        assert page.locator('#modeNotice').is_hidden()
        # The API must independently prevent malformed or mismatched requests.
        source=(ROOT/'samples/01-ngoi-nha-mau.svg').read_text(encoding='utf-8')
        headers={'X-CSRF-TOKEN':page.evaluate('token')}
        request=page.request
        baseline=len(request.get(BASE+'/api/renders').json())
        settings={'duration':3,'hold':.5,'aspect':'portrait','hand':'none','handScale':.65,'effect':'doodle'}
        inputs=[source,'<svg><g id="doodles"/><rect width="20" height="20"/></svg>','<svg><g><g id="doodles"/></g></svg>','<svg><g id="doodles"/><g id="doodles"/></svg>','<svg>','<!DOCTYPE svg><svg/>']
        for bad in inputs:
            response=request.post(BASE+'/api/renders',headers=headers,data={'svg':bad,'name':'Mode regression','mode':'preview','settings':settings})
            assert response.status==400,response.text()
            assert 'error' in response.json() and '\n' not in response.json()['error']
        assert len(request.get(BASE+'/api/renders').json())==baseline
        # Valid doodle source still has no mismatch warning after import.
        page.locator('#fileInput').set_input_files(str(ROOT/'samples/03-doodle-anh-nen.svg'))
        wait_until(lambda:page.locator('#effect').input_value()=='doodle')
        assert page.locator('#modeNotice').is_hidden()
        # Editing the source without importing must also detect the mismatch.
        page.locator('#svgSource').fill(source)
        wait_until(lambda:page.locator('#modeNotice').is_visible())
        page.locator('#useWhiteboard').click()
        page.locator('#duration').fill('3');page.locator('#hold').fill('0.5')
        page.locator('#previewButton').click()
        wait_until(lambda:page.evaluate('activeId!==null'))
        job_id=page.evaluate('activeId')
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            job=request.get(f'{BASE}/api/renders/{job_id}').json()
            if job['state'] in ('Succeeded','Failed'):break
            time.sleep(.3)
        assert job['state']=='Succeeded',job
        assert job['framesDone']==45 and job['settings']['effect']=='whiteboard'
        assert not errors,errors
        print('PASS: mismatch blocked in UI/API, saved draft recovery, explicit mode switch, valid preview.',flush=True)
    finally:browser.close()

# Dynamic SVG errors keep details in a local log, not the user-facing JSON.
with tempfile.TemporaryDirectory(dir=ROOT/'work') as tmp:
    directory=Path(tmp)
    (directory/'input.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><g id="doodles"><path fill="red" d="M10 10L80 80"/></g></svg>')
    (directory/'request.json').write_text(json.dumps({'schemaVersion':1,'width':320,'height':180,'fps':15,'settings':settings}))
    result=subprocess.run([sys.executable,str(ROOT/'engine/render.py'),'--job',str(directory/'request.json')],capture_output=True,text=True)
    assert result.returncode==1
    events=[json.loads(line) for line in result.stdout.splitlines()]
    error=next(e['message'] for e in events if e['type']=='error')
    assert 'fill=' in error and 'Page.evaluate' not in error and '\n' not in error,error
    assert 'Traceback' in (directory/'renderer.log').read_text(encoding='utf-8')
    print('PASS: actionable error without traceback; diagnostics retained in renderer.log.',flush=True)
