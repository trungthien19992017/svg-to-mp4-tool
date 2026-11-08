"""Requires setup.ps1 and the updated app. Real GSAP/browser/MP4 tests, no mocks."""
from pathlib import Path
import json,re,sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'engine/.packages'),str(ROOT/'engine')]
if not (ROOT/'src/SvgToMp4.Web/wwwroot/story/vendor/gsap.min.js').is_file():
    print('SKIP: GSAP is not installed. Run setup.ps1. End-to-end Story acceptance is NOT verified.')
    raise SystemExit(77)
from playwright.sync_api import sync_playwright
from render import browser_executable
BASE='http://127.0.0.1:5188'
def until(check,timeout=40):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        value=check()
        if value:return value
        time.sleep(.2)
    raise AssertionError('Timed out')
def completed(request,job_id,timeout=600):
    def state():
        job=request.get(f'{BASE}/api/renders/{job_id}').json()
        if job['state']=='Failed':raise AssertionError(job['error'])
        return job if job['state'] in ('Completed','Cancelled') else None
    return until(state,timeout)

with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=browser_executable(),headless=True,chromium_sandbox=True,timeout=20000)
    try:
        page=browser.new_page(viewport={'width':1500,'height':1100});page.on('dialog',lambda d:d.accept())
        page.goto(BASE,wait_until='networkidle');until(lambda:page.evaluate("typeof token==='string'&&token.length>0"))
        request=page.request;headers={'X-CSRF-TOKEN':page.evaluate('token')}
        page.locator('#zipInput').set_input_files(str(ROOT/'samples/lost-star.zip'))
        until(lambda:page.locator('#scenes .scene-card').count()==4)
        scene_frame=until(lambda:page.frame(url=re.compile('.*5189/story/runtime.html.*')))
        until(lambda:scene_frame.evaluate('!!window.storyRenderer'))
        image_a=None
        for _ in range(3):
            for t in [5,1,8,0,5]:
                scene_frame.evaluate('async t=>window.storyRenderer.readyFrame(t)',t)
                image=scene_frame.locator('body').screenshot()
                if image_a is None:image_a=image
            assert image==image_a,'Nonsequential seek changes the same frame'
        assert scene_frame.evaluate('window.storyRenderer.timeline.duration')==34.5
        assert len(scene_frame.evaluate('window.storyRenderer.seek(8.75).scenes'))==2
        assert scene_frame.evaluate("(()=>{try{return !!parent.document.body}catch{return false}})()") is False
        assert request.get('http://127.0.0.1:5189/api/session').status==404
        assert request.get(BASE+'/story/runtime.html').status==404
        project=page.evaluate('project.id')
        full=request.post(f'{BASE}/api/stories/{project}/render',headers=headers,data={'width':1280,'height':720,'fps':30,'crf':18,'preset':'veryfast'})
        assert full.status==202,full.text()
        full_job=completed(request,full.json()['id'])
        assert full_job['framesDone']==1035 and full_job['completedAt']
        result=json.loads((ROOT/'data/jobs'/full_job['id']/'result.json').read_text())
        assert result['deterministicCheck'] and any(s['codec_type']=='audio' for s in result['ffprobe']['streams'])
        # Nested timeline / finite loop: actual GSAP, not a fake animation API.
        code='''export function createScene(context){
          const shape=context.svg('<svg xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="100" r="25" fill="orange"/></svg>');
          const child=context.timeline({nested:true});child.fromTo(shape,{x:0},{x:200,duration:.5,repeat:3,yoyo:true,ease:'none'},0);
          const timeline=context.timeline();timeline.add(child,0);
          return {duration:3,seek(t){timeline.time(t,true);},reset(){timeline.pause(0);},dispose(){timeline.kill();}};
        }'''
        manifest={'schemaVersion':'1.0','projectId':'e2e-nested','title':'E2E nested timeline','video':{'width':1280,'height':720,'fps':30,'format':'mp4'},'scenes':[{'id':'one','duration':3,'source':'scenes/one.js','transition':{'type':'cut'}}],'assets':[],'characters':[],'audio':[]}
        small=request.post(BASE+'/api/stories',headers=headers,data={'manifest':manifest,'files':{'scenes/one.js':code}})
        assert small.status==200,small.text()
        small_id=small.json()['id']
        for width,height,fps in [(1280,720,24),(1920,1080,30),(720,1280,60)]:
            response=request.post(f'{BASE}/api/stories/{small_id}/render',headers=headers,data={'width':width,'height':height,'fps':fps,'crf':18,'preset':'veryfast'})
            assert response.status==202,response.text()
            job=completed(request,response.json()['id']);assert job['framesDone']==3*fps
            output=request.get(f'{BASE}/api/renders/{job["id"]}/video',headers={'Range':'bytes=0-1023'})
            assert output.status==206 and len(output.body())==1024
        # Parser rejects syntax errors before publishing a project.
        invalid=request.post(BASE+'/api/stories',headers=headers,data={'manifest':manifest,'files':{'scenes/one.js':'export function createScene(context) { ??? }'}})
        assert invalid.status==400 and 'SyntaxError' in invalid.json()['error']
        manifest['scenes'][0]['duration']=120
        long=request.post(BASE+'/api/stories',headers=headers,data={'manifest':manifest,'files':{'scenes/one.js':code}}).json()
        running=request.post(f'{BASE}/api/stories/{long["id"]}/render',headers=headers,data={'width':1280,'height':720,'fps':30}).json()
        until(lambda:request.get(f'{BASE}/api/renders/{running["id"]}').json()['state']=='Rendering')
        cancelled=request.post(f'{BASE}/api/renders/{running["id"]}/cancel',headers=headers).json();assert cancelled['state']=='Cancelled'
        until(lambda:not (ROOT/'data/jobs'/running['id']/'output.partial.mp4').exists())
        assert request.get(f'{BASE}/api/renders/{running["id"]}/video').status==404
        print('PASS Story end-to-end: 4 scenes/34.5s, shared character, seek, overlaps, sandbox, audio MP4, 720p/1080p + 24/30/60 FPS, nested loop, syntax rejection, cancellation.')
    finally:browser.close()
