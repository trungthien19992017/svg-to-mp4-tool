"""Story rendering shares the browser runtime with the editor; no scene JS runs in Python."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import mimetypes
import os
from pathlib import Path
import shutil
import subprocess
import time
import traceback
from urllib.parse import unquote,urlparse

from render import ENGINE, browser_executable, emit, progress, user_error
from playwright.sync_api import sync_playwright

ROOT=ENGINE.parent
RUNTIME=ROOT/'src/SvgToMp4.Web/wwwroot/story'

def layout(manifest):
    start=0.;result=[]
    for index,scene in enumerate(manifest['scenes']):
        duration=float(scene['duration']);transition=scene.get('transition',{})
        overlap=0. if transition.get('type','cut')=='cut' else float(transition.get('duration',.5))
        if not math.isfinite(duration) or duration<=0 or overlap<0 or overlap>duration/2 or (index==len(manifest['scenes'])-1 and overlap):
            raise ValueError('Story timeline không hợp lệ.')
        if index+1<len(manifest['scenes']) and overlap>float(manifest['scenes'][index+1]['duration'])/2:
            raise ValueError('Transition overlap vượt giới hạn.')
        result.append({**scene,'start':start,'end':start+duration})
        start+=duration-overlap
    return result,start

def mix_arguments(manifest,snapshot,silent,output,duration):
    scenes,_=layout(manifest);starts={s['id']:s['start'] for s in scenes}
    assets={a['id']:a for a in manifest.get('assets',[])}
    tracks=manifest.get('audio',[])
    command=[shutil.which('ffmpeg'),'-hide_banner','-loglevel','error','-y','-i',str(silent)]
    filters=[];labels=[]
    for i,track in enumerate(tracks,1):
        relative=assets[track['assetId']]['path'];path=(snapshot/relative).resolve()
        if not path.is_relative_to(snapshot):raise ValueError('Audio nằm ngoài snapshot.')
        fmt={'.wav':'wav','.mp3':'mp3','.m4a':'mov','.ogg':'ogg'}[path.suffix.lower()]
        command+=['-protocol_whitelist','file,pipe','-f',fmt,'-i',str(path)]
        start=starts.get(track.get('sceneId'),0)+float(track.get('start',0));length=float(track['duration'])
        offset=float(track.get('offset',0));gain=float(track.get('volume',1));fade_in=float(track.get('fadeIn',0));fade_out=float(track.get('fadeOut',0))
        parts=[f'[{i}:a]aresample=48000',f'atrim=start_sample={round(offset*48000)}:end_sample={round((offset+length)*48000)}','asettb=1/48000','asetpts=N/48000/TB',f'volume={gain}']
        if fade_in:parts.append(f'afade=t=in:ss=0:ns={max(1,round(fade_in*48000))}')
        if fade_out:parts.append(f'afade=t=out:ss={round(max(0,length-fade_out)*48000)}:ns={max(1,round(fade_out*48000))}')
        parts.append(f'adelay={round(start*48000)}S:all=1')
        filters.append(','.join(parts)+f'[a{i}]');labels.append(f'[a{i}]')
    filters.append(''.join(labels)+f'amix=inputs={len(labels)}:normalize=0:duration=longest,apad=whole_len={round(duration*48000)},atrim=end_sample={round(duration*48000)},asettb=1/48000,asetpts=N/48000/TB[audio]')
    command+=['-filter_complex',';'.join(filters),'-map','0:v:0','-map','[audio]','-c:v','copy','-c:a','aac','-ar','48000','-b:a','192k','-t',str(duration),'-movflags','+faststart',str(output)]
    return command

def render_story(job_file):
    if os.environ.get('STORY_RESOURCE_GUARD')!='windows-job-v1':
        raise ValueError('Story code phải render qua background job có giới hạn tài nguyên. Hãy dùng nút Render trong studio.')
    started=time.monotonic();directory=job_file.resolve().parent;request=json.loads(job_file.read_text(encoding='utf-8-sig'))
    snapshot=Path(request['snapshot']).resolve()
    if not snapshot.is_relative_to((ROOT/'data/stories').resolve()):raise ValueError('Snapshot nằm ngoài kho project.')
    manifest=json.loads((snapshot/'story.json').read_text(encoding='utf-8-sig'))
    scenes,duration=layout(manifest);width,height,fps=int(request['width']),int(request['height']),int(request['fps'])
    if not 64<=width<=3840 or not 64<=height<=3840 or width%2 or height%2 or width*height>8294400 or fps not in (24,30,60):raise ValueError('Thiết lập video không hợp lệ.')
    crf=int(request.get('crf',18));preset=request.get('preset','veryfast')
    if not 10<=crf<=35 or preset not in ('ultrafast','veryfast','medium'):raise ValueError('CRF hoặc preset không hợp lệ.')
    if not (RUNTIME/'vendor/gsap.min.js').is_file():raise ValueError('Chưa cài GSAP. Dừng tool và chạy setup.ps1 trước khi render Story.')
    for tool in ('ffmpeg','ffprobe'):
        if not shutil.which(tool):raise ValueError(f'Thiếu {tool} trong PATH.')
    total=math.ceil(duration*fps);effective=total/fps;silent=directory/'silent.partial.mp4';partial=directory/'output.partial.mp4'
    progress('Preparing','Đang nạp câu chuyện',total=total)
    allowed_runtime={'runtime.html','runtime.css','runtime.js','timeline.mjs','vendor/gsap.min.js','vendor/MotionPathPlugin.min.js','vendor/MorphSVGPlugin.min.js'}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=browser_executable(),headless=True,chromium_sandbox=True,timeout=20000,args=['--disable-background-networking','--disable-extensions','--site-per-process','--force-webrtc-ip-handling-policy=disable_non_proxied_udp'])
        try:
            context=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1,offline=True,service_workers='block',accept_downloads=False)
            def route_request(route):
                url=urlparse(route.request.url);path=unquote(url.path)
                if url.scheme!='https' or url.netloc!='story.invalid':return route.abort()
                if path.startswith('/bundle/'):
                    file=(snapshot/path[len('/bundle/'):]).resolve()
                    if not file.is_relative_to(snapshot):return route.abort()
                elif path.startswith('/story/') and path[len('/story/'):] in allowed_runtime:
                    file=RUNTIME/path[len('/story/'):]
                else:return route.abort()
                if not file.is_file():return route.abort()
                mime={'.js':'text/javascript','.mjs':'text/javascript','.svg':'image/svg+xml'}.get(file.suffix,mimetypes.guess_type(file.name)[0] or 'application/octet-stream')
                return route.fulfill(body=file.read_bytes(),content_type=mime,headers={'Content-Security-Policy':"default-src 'none'; script-src 'self' blob:; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; font-src 'self' blob: data:; frame-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"})
            context.route('**/*',route_request)
            context.route_web_socket('**/*',lambda socket:socket.close())
            page=context.new_page();page.set_default_timeout(30000)
            page.goto('https://story.invalid/story/runtime.html?bundle=/bundle/',wait_until='load')
            page.evaluate('async()=>{await window.storyReady;}')
            # Observable, nonsequential determinism check before committing video frames.
            check=min(5.,duration/2)
            digests=[]
            for t in (check,min(1.,duration),min(8.,duration),0.,check):
                page.evaluate('async t=>{await window.storyReady;return window.storyRenderer.readyFrame(t)}',t)
                digests.append(hashlib.sha256(page.screenshot(type='png')).hexdigest())
            if digests[0]!=digests[-1]:raise ValueError('Scene không deterministic: cùng thời điểm cho hình khác nhau sau khi seek ngược. Kiểm tra callback, random và state tích lũy.')
            command=[shutil.which('ffmpeg'),'-hide_banner','-loglevel','error','-y','-f','image2pipe','-vcodec','png','-framerate',str(fps),'-i','pipe:0','-an','-c:v','libx264','-threads','2','-preset',preset,'-crf',str(crf),'-pix_fmt','yuv420p','-movflags','+faststart',str(silent)]
            with (directory/'encoder.log').open('wb') as log:
                encoder=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log)
                try:
                    for frame in range(total):
                        info=page.evaluate('async t=>window.storyRenderer.readyFrame(t)',frame/fps)
                        encoder.stdin.write(page.screenshot(type='png',animations='allow'))
                        if frame%max(1,fps//3)==0 or frame==total-1:progress('Rendering',f'Đang render: {", ".join(info["scenes"])}',done=frame+1,total=total)
                    encoder.stdin.close();progress('Encoding','Đang hoàn tất video',done=total,total=total)
                    if encoder.wait(timeout=120)!=0:raise ValueError('FFmpeg encode lỗi. Xem encoder.log.')
                finally:
                    if encoder.poll() is None:encoder.kill();encoder.wait()
        finally:browser.close()
    if manifest.get('audio'):
        progress('Encoding','Đang ghép âm thanh',done=total,total=total)
        with (directory/'audio.log').open('wb') as log:subprocess.run(mix_arguments(manifest,snapshot,silent,partial,effective),stdout=subprocess.DEVNULL,stderr=log,check=True,timeout=300)
    else:silent.replace(partial)
    progress('Validating','Đang kiểm tra video',done=total,total=total)
    probe=subprocess.run([shutil.which('ffprobe'),'-v','error','-count_frames','-show_streams','-show_format','-of','json',str(partial)],capture_output=True,check=True,timeout=120)
    metadata=json.loads(probe.stdout);video=next(s for s in metadata['streams'] if s['codec_type']=='video')
    if int(video['nb_read_frames'])!=total or video['width']!=width or video['height']!=height or video['codec_name']!='h264' or video['pix_fmt']!='yuv420p':raise ValueError('MP4 không đạt kiểm tra số frame/kích thước/codec.')
    numerator,denominator=map(int,video['avg_frame_rate'].split('/'))
    if numerator/denominator!=fps or abs(float(video['duration'])-effective)>1/fps:raise ValueError('MP4 sai FPS hoặc thời lượng.')
    if manifest.get('audio') and not any(s['codec_type']=='audio' for s in metadata['streams']):raise ValueError('Video thiếu audio track.')
    result={'kind':'story','duration':effective,'frames':total,'width':width,'height':height,'fps':fps,'elapsedSeconds':round(time.monotonic()-started,2),'deterministicCheck':True,'ffprobe':metadata}
    (directory/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');partial.replace(directory/'output.mp4')
    silent.unlink(missing_ok=True);emit('complete',frames=total)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--job',type=Path,required=True);args=parser.parse_args()
    try:render_story(args.job)
    except Exception as error:
        (args.job.resolve().parent/'renderer.log').write_text(traceback.format_exc(),encoding='utf-8')
        emit('error',message=user_error(error));raise SystemExit(1)
