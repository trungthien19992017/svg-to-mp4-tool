"""Run against the local app after start.ps1; creates real preview/export demo jobs."""
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'engine/.packages'),str(ROOT/'engine')]
from playwright.sync_api import sync_playwright
from render import browser_executable

BASE='http://127.0.0.1:5188'
report={'checks':[],'jobs':[]}

def wait_until(predicate,timeout=30):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if predicate():return
        time.sleep(.2)
    raise AssertionError('Timed out waiting for browser state')


def wait_job(request,job_id,timeout=180):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        job=request.get(f'{BASE}/api/renders/{job_id}').json()
        if job['state'] in ('Succeeded','Failed','Cancelled'): return job
        time.sleep(.5)
    raise AssertionError(f'Timed out waiting for {job_id}')


with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=browser_executable(),headless=True,chromium_sandbox=True,timeout=20000)
    try:
        context=browser.new_context(viewport={'width':1440,'height':1100},device_scale_factor=1)
        page=context.new_page()
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(BASE+'/whiteboard',wait_until='networkidle')
        wait_until(lambda:page.evaluate("typeof token==='string' && token.length>0"))
        assert page.locator('h1').inner_text().startswith('Cho bản vẽ')
        assert page.locator('#originalImage').evaluate('(i)=>i.complete&&i.naturalWidth>0')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        (ROOT/'work/qa').mkdir(exist_ok=True,parents=True)
        page.screenshot(path=str(ROOT/'work/qa/studio-desktop.png'),full_page=True)
        csrf=page.evaluate('token')
        request=context.request
        headers={'X-CSRF-TOKEN':csrf}
        blocked=request.post(f'{BASE}/api/renders',data={'svg':'<svg/>','name':'CSRF test','mode':'preview','settings':{}})
        assert blocked.status==400,blocked.status
        report['checks'].append('Missing CSRF rejected')
        page.locator('#previewButton').click()
        wait_until(lambda:page.evaluate('activeId!==null'))
        preview_id=page.evaluate('activeId')
        preview=wait_job(request,preview_id)
        assert preview['state']=='Succeeded',preview
        assert preview['framesDone']==150 and preview['width']==540
        wait_until(lambda:page.evaluate('selectedId!==null'))
        wait_until(lambda:page.locator('#video').evaluate('(v)=>v.videoWidth===540'))
        report['checks'].append('UI -> preview -> playable video, 150 frames')
        source=page.locator('#svgSource').input_value()
        for aspect in ['portrait','landscape']:
            payload={'svg':source,'name':f'Ngôi nhà nhỏ · {aspect}','mode':'export','settings':{'duration':10,'hold':1,'aspect':aspect,'hand':'asian','handScale':.65}}
            response=request.post(f'{BASE}/api/renders',data=payload,headers=headers)
            assert response.status==202,response.text()
            job=wait_job(request,response.json()['id'])
            assert job['state']=='Succeeded',job
            assert job['framesDone']==300
            directory=ROOT/'data/jobs'/job['id']
            result=json.loads((directory/'result.json').read_text(encoding='utf-8'))
            assert result['frames']==300 and result['fps']==30
            assert (result['width'],result['height'])==((1080,1920) if aspect=='portrait' else (1920,1080))
            media=request.get(f'{BASE}/api/renders/{job["id"]}/video',headers={'Range':'bytes=0-1023'})
            assert media.status==206 and len(media.body())==1024
            attachment=request.get(f'{BASE}/api/renders/{job["id"]}/video?download=true')
            assert attachment.status==200 and 'attachment' in attachment.headers['content-disposition']
            report['jobs'].append({k:result[k] for k in ['width','height','fps','frames','elapsedSeconds','strokeCount']})
            report['checks'].append(f'1080p {aspect}, 300 frames, range playback/download')
            print(f'PASS export {aspect}',flush=True)
        # Check unsupported active content at the actual worker boundary.
        payload={'svg':(ROOT/'tests/fixtures/unsafe.svg').read_text(),'name':'Security fixture','mode':'preview','settings':{'duration':3,'hold':.5,'aspect':'portrait','hand':'none','handScale':.65}}
        unsafe=request.post(f'{BASE}/api/renders',data=payload,headers=headers).json()
        failed=wait_job(request,unsafe['id'])
        assert failed['state']=='Failed' and 'script' in failed['error']
        assert request.get(f'{BASE}/api/renders/{unsafe["id"]}/video').status==404
        report['checks'].append('Active SVG rejected, failed output inaccessible')
        # Active cancel and queued cancel; use the known-good sample.
        payload.update(svg=source,name='Cancel fixture',settings={'duration':120,'hold':1,'aspect':'portrait','hand':'asian','handScale':.65})
        running=request.post(f'{BASE}/api/renders',data=payload,headers=headers).json()
        queued=request.post(f'{BASE}/api/renders',data=payload,headers=headers).json()
        cancelled=request.post(f'{BASE}/api/renders/{queued["id"]}/cancel',headers=headers).json()
        assert cancelled['state']=='Cancelled'
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            state=request.get(f'{BASE}/api/renders/{running["id"]}').json()['state']
            if state=='Rendering':break
            if state in ('Failed','Succeeded'):raise AssertionError(state)
            time.sleep(.3)
        assert state=='Rendering'
        assert request.post(f'{BASE}/api/renders/{running["id"]}/cancel',headers=headers).json()['state']=='Cancelled'
        time.sleep(2)
        assert request.get(f'{BASE}/api/renders/{running["id"]}/video').status==404
        assert not (ROOT/'data/jobs'/running['id']/'output.partial.mp4').exists()
        report['checks'].append('Queued and active cancellation; partial output removed')
        page.reload(wait_until='networkidle')
        wait_until(lambda:page.evaluate('jobs.length>=6'))
        assert page.locator('#jobs .job').count()>=6
        page.set_viewport_size({'width':390,'height':844})
        page.wait_for_timeout(300)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(ROOT/'work/qa/studio-mobile.png'),full_page=True)
        assert not errors,errors
        report['checks'].append('History persists on reload; mobile fits viewport; no JS errors')
        (ROOT/'work/qa/integration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'PASS {len(report["checks"])} integration checks',flush=True)
    finally:
        browser.close()
