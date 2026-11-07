"""Real application import/export, browser preview and worker MP4 acceptance.

Requires the current app on loopback 5188/5189. Creates two demo projects and a
render job in the application's local store. Does not read private module state.
"""
from pathlib import Path
import hashlib, http.cookiejar, io, json, shutil, sys, time, urllib.request, zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'engine/.packages'),str(ROOT/'engine')]
from playwright.sync_api import sync_playwright, expect
from render import browser_executable
from PIL import Image, ImageChops

BASE='http://127.0.0.1:5188'
OUT=ROOT/'outputs/may-bong-episode-01'
OUT.mkdir(parents=True,exist_ok=True)
report={'checks':[]}
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def request(path,body=None,method=None,content_type='application/json'):
    headers={'X-CSRF-TOKEN':csrf} if 'csrf' in globals() else {}
    if body is not None:headers['Content-Type']=content_type
    req=urllib.request.Request(BASE+path,data=body,method=method,headers=headers)
    try:
        with opener.open(req,timeout=40) as response:return response.read()
    except urllib.error.HTTPError as e:raise AssertionError(f'{path}: HTTP {e.code}: {e.read().decode()}') from e


def import_zip(data):
    boundary='MayBongStoryBoundary811'
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="may-bong-episode-01.zip"\r\nContent-Type: application/zip\r\n\r\n').encode()+data+f'\r\n--{boundary}--\r\n'.encode()
    return json.loads(request('/api/stories/import',body,'POST','multipart/form-data; boundary='+boundary))


def unpack(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.testzip() is None
        names=archive.namelist();assert len(names)==len(set(names))
        assert 'story.json' in names
        assert all(not n.startswith('/') and '..' not in n.split('/') and '\\' not in n and ':' not in n for n in names)
        return {n:archive.read(n) for n in names}


def check(label):report['checks'].append(label);print('PASS',label,flush=True)


def wait_for(checker,seconds=45):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        result=checker()
        if result:return result
        time.sleep(.25)
    raise AssertionError('Timed out waiting for browser/job')


def main():
    global csrf
    csrf=json.loads(request('/api/session'))['token']
    source=ROOT/'samples/may-bong-episode-01'
    seed=io.BytesIO()
    with zipfile.ZipFile(seed,'w',zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(source.rglob('*')):
            if file.is_file():archive.write(file,file.relative_to(source).as_posix())
    project=import_zip(seed.getvalue());check('Official API imported authored v1 project')
    final=request(f'/api/stories/{project["id"]}/export')
    zip_path=OUT/'may-bong-episode-01.zip';zip_path.write_bytes(final)
    exported=unpack(final);manifest=json.loads(exported['story.json'])
    assert manifest['schemaVersion']=='1.0' and manifest['duration']==14
    for asset in manifest['assets']:assert asset['path'] in exported
    for scene in manifest['scenes']:assert scene['source'] in exported
    assert len(manifest['characters'])==2 and len(manifest['scenes'])==3
    assert 'modules/cozy-engine.js' in exported
    for file in source.rglob('*'):
        if file.is_file() and file.name!='story.json':assert exported[file.relative_to(source).as_posix()]==file.read_bytes()
    check('Application export ZIP: CRC, safe paths, manifest, all asset/source bytes and helper module')
    again=import_zip(final)
    roundtrip=unpack(request(f'/api/stories/{again["id"]}/export'))
    assert exported==roundtrip
    report.update(projectId=again['id'],revision=again['revision'],zipSha256=hashlib.sha256(final).hexdigest(),files=len(exported))
    check('Re-import and second official export preserve every file byte-for-byte')
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=browser_executable(),headless=True,chromium_sandbox=True,timeout=20000)
        try:
            page=browser.new_page(viewport={'width':1440,'height':1080},device_scale_factor=1)
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto(BASE,wait_until='networkidle')
            page.locator('#projectList').select_option(again['id'])
            expect(page.locator('#status')).to_contain_text('Preview sẵn sàng',timeout=30000)
            frame=page.locator('#storyFrame').element_handle().content_frame()
            frame.wait_for_url('**/story/runtime.html?**')
            frame.evaluate('async()=>{await window.storyReady;}')
            assert frame.evaluate('window.storyRenderer.instances.length')==3
            assert frame.evaluate('window.storyRenderer.timeline.duration')==14
            assert frame.evaluate('(()=>{try{return !!parent.document.body}catch{return false}})()') is False
            check('All three scenes initialized in official opaque-origin preview')
            def snap(t):
                frame.evaluate('async t=>window.storyRenderer.readyFrame(t)',t)
                return frame.locator('#stage').screenshot(animations='allow')
            for t in [0,1.75,4.75,6.25,9.25,12.25,13.95]:
                expected=snap(t)
                visible_dom=lambda:frame.evaluate("window.storyRenderer.instances.filter(i=>i.root.style.visibility==='visible').map(i=>i.root.outerHTML)")
                expected_dom=visible_dom()
                for other in [13.5,.15,8,0]:snap(other)
                actual=snap(t)
                if actual!=expected:
                    # The studio scales its iframe to fractional CSS pixels. Chromium
                    # can round translucent rain edges by one 8-bit value after repaint.
                    # Require exact active DOM and a tightly bounded raster difference;
                    # the production exporter still enforces exact full-size PNG hashes.
                    difference=ImageChops.difference(Image.open(io.BytesIO(expected)).convert('RGB'),Image.open(io.BytesIO(actual)).convert('RGB'))
                    max_error=max(v[1] for v in difference.getextrema())
                    changed=sum(pixel!=(0,0,0) for pixel in difference.get_flattened_data())
                    assert visible_dom()==expected_dom and max_error<=1 and changed/(difference.width*difference.height)<.001,f'Non-deterministic frame at {t}'
                    report.setdefault('scaledPreviewRounding',[]).append({'time':t,'maxChannelError':max_error,'changedPixels':changed})
            check('Deterministic seek at seven timestamps and both overlaps; scaled preview tolerance <=1/255 on <0.1% pixels')
            assert snap(1.5)!=snap(2.5),'Animation does not change over time'
            page.locator('#playStory').click();time.sleep(.8)
            assert 'Dừng' in page.locator('#playStory').inner_text()
            page.locator('#playStory').click()
            snap(2.5)
            frame.locator('#stage').screenshot(path=str(OUT/'preview.png'))
            page.screenshot(path=str(OUT/'studio-preview.png'),full_page=True)
            assert not errors,errors
            report['browser']=browser.version
            check('Studio playback, animated preview, screenshots and no page errors')
        finally:browser.close()
    options={'width':720,'height':1280,'fps':24,'crf':18,'preset':'veryfast'}
    job=json.loads(request(f'/api/stories/{again["id"]}/render',json.dumps(options).encode(),'POST'))
    report['jobId']=job['id'];print('RENDER JOB',job['id'],flush=True)
    last=None;deadline=time.monotonic()+900
    while time.monotonic()<deadline:
        state=json.loads(request('/api/renders/'+job['id']))
        progress=(state['state'],state['framesDone']//24)
        if progress!=last:print(state['state'],state['framesDone'],'/',state['framesTotal'],flush=True);last=progress
        if state['state']=='Failed':raise AssertionError('Render failed: '+str(state['error']))
        if state['state']=='Completed':break
        time.sleep(1)
    else:raise AssertionError('Render acceptance deadline exceeded')
    assert state['framesDone']==336
    result=json.loads((ROOT/'data/jobs'/job['id']/'result.json').read_text())
    assert result['deterministicCheck'] and result['frames']==336 and result['duration']==14
    streams=result['ffprobe']['streams']
    assert any(s['codec_type']=='audio' and s['codec_name']=='aac' for s in streams)
    video=next(s for s in streams if s['codec_type']=='video')
    assert video['width']==720 and video['height']==1280 and video['codec_name']=='h264'
    (OUT/'may-bong-episode-01.mp4').write_bytes(request(f'/api/renders/{job["id"]}/video?download=true'))
    shutil.copyfile(ROOT/'data/jobs'/job['id']/'result.json',OUT/'render-result.json')
    report['render']=result
    check('Official queued worker MP4: 336 frames / 14s / 720x1280 / 24 FPS / H.264 + AAC')
    report['status']='PASS'


if __name__=='__main__':
    try:main()
    except Exception as error:
        report['status']='FAIL';report['error']=str(error);raise
    finally:(OUT/'acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
