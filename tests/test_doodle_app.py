"""Run against the local app; creates real doodle preview/export jobs."""
import base64
import json
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'engine/.packages'),str(ROOT/'engine')]
from playwright.sync_api import sync_playwright
from render import browser_executable

BASE='http://127.0.0.1:5188'

def wait_until(predicate,timeout=30):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if predicate():return
        time.sleep(.2)
    raise AssertionError('Timed out waiting for browser state')


def wait_job(request,job_id):
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        job=request.get(f'{BASE}/api/renders/{job_id}').json()
        if job['state'] in ('Succeeded','Failed','Cancelled'):
            assert job['state']=='Succeeded',job
            return job
        time.sleep(.5)
    raise AssertionError('Render timed out')


with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=browser_executable(),headless=True,chromium_sandbox=True)
    try:
        context=browser.new_context(viewport={'width':1440,'height':1100},accept_downloads=True)
        page=context.new_page();errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('dialog',lambda dialog:dialog.accept())
        page.goto(BASE+'/whiteboard',wait_until='networkidle')
        wait_until(lambda:page.evaluate("typeof token==='string' && token.length>0"))
        page.locator('#loadDoodleSample').click()
        wait_until(lambda:page.locator('#effect').input_value()=='doodle')
        wait_until(lambda:page.locator('#originalImage').evaluate('(image)=>image.complete && image.naturalWidth>0'))
        source=page.locator('#svgSource').input_value()
        assert 'data:image/png;base64,' in source
        assert page.locator('#recipeTitle').inner_text()=='Doodle trên ảnh nền'
        page.locator('#duration').fill('3');page.locator('#hold').fill('0.5')
        page.locator('#previewButton').click()
        wait_until(lambda:page.evaluate('activeId!==null'))
        preview_id=page.evaluate('activeId')
        preview=wait_job(context.request,preview_id)
        assert preview['framesDone']==45 and preview['settings']['effect']=='doodle'
        wait_until(lambda:page.evaluate('selectedId')==preview_id)
        wait_until(lambda:page.locator('#video').evaluate('(video)=>video.videoWidth===540'))
        headers={'X-CSRF-TOKEN':page.evaluate('token')}
        payload={'svg':source,'name':'Doodle · kiểm tra 1080p','mode':'export','settings':{'duration':3,'hold':.5,'aspect':'portrait','hand':'asian','handScale':.65,'effect':'doodle'}}
        response=context.request.post(BASE+'/api/renders',data=payload,headers=headers)
        assert response.status==202,response.text()
        exported=wait_job(context.request,response.json()['id'])
        assert exported['width']==1080 and exported['framesDone']==90
        media=context.request.get(f'{BASE}/api/renders/{exported["id"]}/video',headers={'Range':'bytes=0-1023'})
        assert media.status==206
        page.locator('#showOriginal').click()
        with page.expect_download() as download:
            page.locator('#downloadSvg').click()
        downloaded=Path(download.value.path()).read_text(encoding='utf-8')
        assert downloaded==source
        image=ET.fromstring(source).find('{http://www.w3.org/2000/svg}image')
        png=base64.b64decode(image.attrib['href'].split(',',1)[1])
        page.locator('#backgroundInput').set_input_files({'name':'new-background.png','mimeType':'image/png','buffer':png})
        wait_until(lambda:page.locator('#projectName').input_value()=='new-background')
        assert page.locator('#effect').input_value()=='doodle'
        assert 'id="doodles"' in page.locator('#svgSource').input_value()
        with page.expect_download() as download:
            page.locator('#downloadSvg').click()
        assert 'data:image/png;base64,' in Path(download.value.path()).read_text(encoding='utf-8')
        page.reload(wait_until='networkidle')
        assert page.locator('#effect').input_value()=='doodle'
        assert page.locator('#projectName').input_value()=='new-background'
        for width in [1440,390]:
            page.set_viewport_size({'width':width,'height':1100})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        (ROOT/'work/qa').mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(ROOT/'work/qa/doodle-mobile.png'),full_page=True)
        assert not errors,errors
        report={'preview':preview_id,'export':exported['id'],'checks':['sample','UI preview','1080p export with hand','range playback','SVG download','background upload','draft restore','mobile layout','no JS errors']}
        (ROOT/'work/qa/doodle-integration.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report),flush=True)
    finally:
        browser.close()
