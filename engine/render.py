"""Local SVG adapter. No model, TTS, cloud API, or arbitrary user code execution."""
from __future__ import annotations

import argparse
import base64
import binascii
from contextlib import contextmanager, ExitStack
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback

ENGINE = Path(__file__).resolve().parent
sys.path[:0] = [str(ENGINE / '.packages'), str(ENGINE / 'vendor')]

from defusedxml import ElementTree as ET
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright
from whiteboard_skill import whiteboard as wb
from whiteboard_skill.preprocess import Stroke

VERSION = 'svg-adapter-2'
UPSTREAM = '86848ea27077c1902950bf4e7e37e02d4bfbd1a3'
SVG_NS = 'http://www.w3.org/2000/svg'
TAGS = {'svg', 'g', 'image', 'path', 'line', 'polyline', 'polygon', 'rect', 'circle', 'ellipse',
        'title', 'desc', 'defs', 'linearGradient', 'radialGradient', 'stop', 'text', 'tspan'}
PROPS = {'fill', 'fill-opacity', 'fill-rule', 'stroke', 'stroke-width', 'stroke-opacity',
         'stroke-linecap', 'stroke-linejoin', 'stroke-miterlimit', 'stroke-dasharray', 'stroke-dashoffset',
         'opacity', 'display', 'visibility', 'color', 'font-family', 'font-size', 'font-weight',
         'font-style', 'text-anchor', 'dominant-baseline', 'letter-spacing', 'word-spacing', 'paint-order'}
ATTRS = PROPS | {'id', 'class', 'style', 'version', 'viewBox', 'preserveAspectRatio', 'width', 'height',
                  'x', 'y', 'x1', 'x2', 'y1', 'y2', 'cx', 'cy', 'r', 'rx', 'ry', 'd', 'points', 'transform',
                  'dx', 'dy', 'rotate', 'textLength', 'lengthAdjust', 'gradientUnits', 'gradientTransform',
                  'spreadMethod', 'fx', 'fy', 'fr', 'offset', 'stop-color', 'stop-opacity', 'href'}

MAX_SVG_BYTES = 20_000_000


def validate_image(value: str):
    match = re.fullmatch(r'data:image/(png|jpeg);base64,([A-Za-z0-9+/=]+)', value)
    if not match:
        raise ValueError('Ảnh nền phải là PNG/JPEG nhúng base64, không dùng link hoặc file ngoài.')
    try:
        data = base64.b64decode(match[2], validate=True)
        with Image.open(io.BytesIO(data)) as image:
            if image.format != {'png': 'PNG', 'jpeg': 'JPEG'}[match[1]] or image.width * image.height > 25_000_000:
                raise ValueError('Ảnh nền không đúng định dạng hoặc vượt quá 25 triệu pixel.')
            image.verify()
    except (binascii.Error, OSError, Image.DecompressionBombError) as error:
        raise ValueError('Dữ liệu ảnh nền không hợp lệ.') from error


def emit(kind: str, **data):
    print(json.dumps({'type': kind, **data}, ensure_ascii=True), flush=True)


def progress(state, stage, **data):
    emit('progress', state=state, stage=stage, **data)


def user_error(error: Exception) -> str:
    message = str(error).splitlines()[0] if str(error) else 'Không thể xử lý SVG này.'
    return re.sub(r'^Page\.evaluate:\s*(?:Error:\s*)?', '', message)


def validate_svg(source: str) -> str:
    if len(source.encode('utf-8')) > MAX_SVG_BYTES:
        raise ValueError('SVG vượt quá giới hạn 20 MB.')
    if '<!DOCTYPE' in source.upper() or '<!ENTITY' in source.upper() or '<?' in re.sub(r'^\s*<\?xml[^?]*\?>', '', source):
        raise ValueError('SVG không được chứa DTD, entity hoặc processing instruction.')
    root = ET.fromstring(source, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    count = 0
    for element in root.iter():
        count += 1
        if count > 5000:
            raise ValueError('SVG vượt quá 5.000 phần tử.')
        namespace, _, tag = element.tag[1:].partition('}') if element.tag.startswith('{') else ('', '', element.tag)
        if namespace not in ('', SVG_NS) or tag not in TAGS:
            raise ValueError(f'Chưa hỗ trợ phần tử <{tag}>. Hỗ trợ vector, gradient, chữ và PNG/JPEG nhúng; không hỗ trợ script, CSS stylesheet, clip hoặc mask.')
        if element is not root and tag == 'svg':
            raise ValueError('Chưa hỗ trợ SVG lồng nhau. Vui lòng xuất thành một SVG với các group.')
        if len(element.attrib) > 80:
            raise ValueError('Phần tử SVG có quá nhiều thuộc tính.')
        for key, value in element.attrib.items():
            if key in ('href', '{http://www.w3.org/1999/xlink}href') and tag == 'image':
                validate_image(value)
                continue
            if key not in ATTRS:
                raise ValueError(f'Chưa hỗ trợ thuộc tính SVG: {key}.')
            if key == 'href':
                raise ValueError('Chỉ phần tử image được dùng href.')
            if key == 'style':
                for part in value.split(';'):
                    if not part.strip():
                        continue
                    prop, sep, val = part.partition(':')
                    if not sep or prop.strip().lower() not in PROPS:
                        raise ValueError('Style chỉ được chứa thuộc tính màu, nét và chữ được hỗ trợ.')
                    check_value(val)
            else:
                check_value(value)
        if tag == 'image' and not any(key in element.attrib for key in ('href', '{http://www.w3.org/1999/xlink}href')):
            raise ValueError('Ảnh nền cần href chứa PNG/JPEG nhúng.')
    if root.tag.split('}')[-1] != 'svg':
        raise ValueError('File phải có phần tử gốc <svg>.')
    # Reject external/ambiguous resources rather than silently changing the artwork.
    return source


def check_value(value: str):
    if any(c in value for c in ('\\', '<', '>', '@', '{', '}')) or re.search(r'(?:javascript|https?|file|data)\s*:', value, re.I):
        raise ValueError('SVG không được truy cập tài nguyên ngoài hoặc chứa nội dung thực thi.')
    stripped = re.sub(r'url\(\s*#[A-Za-z_][\w.-]*\s*\)', '', value, flags=re.I)
    if re.search(r'url\s*\(|expression\s*\(|var\s*\(', stripped, re.I):
        raise ValueError('SVG chỉ được tham chiếu gradient nội bộ dạng url(#id).')


def browser_executable():
    explicit = os.environ.get('SVG_CHROME')
    if explicit:
        return explicit
    for candidate in [
        Path(os.environ.get('PROGRAMFILES', 'C:/Program Files')) / 'Google/Chrome/Application/chrome.exe',
        Path(os.environ.get('PROGRAMFILES(X86)', 'C:/Program Files (x86)')) / 'Microsoft/Edge/Application/msedge.exe',
    ]:
        if candidate.is_file():
            return str(candidate)
    for name in ('google-chrome', 'chromium', 'chromium-browser', 'microsoft-edge'):
        if shutil.which(name):
            return shutil.which(name)
    raise ValueError('Chưa tìm thấy Chrome/Edge. Cài Chrome hoặc đặt biến SVG_CHROME tới file trình duyệt.')


@contextmanager
def open_scene(source: str, width: int, height: int, effect='whiteboard'):
    """Use browser-native path geometry and the same viewport for final color pixels."""
    validate_svg(source)
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=browser_executable(), headless=True, chromium_sandbox=True, timeout=20000,
                                     args=['--disable-background-networking', '--disable-extensions'])
        try:
            context = browser.new_context(viewport={'width': width, 'height': height}, device_scale_factor=1,
                                          offline=True, service_workers='block', color_scheme='light')
            context.route('**/*', lambda route: route.abort())
            page = context.new_page()
            page.set_default_timeout(20000)
            page.set_content('<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0;padding:0;background:white;overflow:hidden}body>svg{display:block;background:white}</style></head><body></body></html>')
            geometry = page.evaluate(r'''({source,width,height,effect}) => {
                const doc = new DOMParser().parseFromString(source,'image/svg+xml');
                if(doc.querySelector('parsererror')) throw Error('SVG không hợp lệ.');
                const svg = document.importNode(doc.documentElement,true);
                if(!svg.getAttribute('viewBox')) {
                    const w=parseFloat(svg.getAttribute('width')), h=parseFloat(svg.getAttribute('height'));
                    if(!(w>0&&h>0)) throw Error('SVG cần viewBox hoặc width/height hợp lệ.');
                    svg.setAttribute('viewBox',`0 0 ${w} ${h}`);
                }
                svg.setAttribute('width',width);svg.setAttribute('height',height);
                document.body.append(svg);
                const doodles = svg.querySelector('g[id="doodles"]');
                if(effect==='doodle' && (!doodles || doodles.parentElement!==svg || doodles.nextElementSibling))
                    throw Error('Chế độ doodle cần group <g id="doodles"> ở cuối SVG, chứa các nét cần vẽ.');
                if(effect==='doodle' && doodles.querySelector('image,text,tspan'))
                    throw Error('Group doodles chỉ chứa nét vector. Đặt ảnh và chữ tĩnh bên ngoài group này.');
                const result=[];let pointCount=0;
                const shapes = (effect==='doodle'?doodles:svg).querySelectorAll('path,line,polyline,polygon,rect,circle,ellipse');
                for(const [shapeIndex,shape] of [...shapes].entries()) {
                    if(shape.closest('defs')) continue;
                    let visible=true;
                    for(let node=shape;node&&node!==document.body;node=node.parentElement){
                        const s=getComputedStyle(node);
                        if(s.display==='none'||s.visibility==='hidden'||s.visibility==='collapse'||Number(s.opacity)===0) visible=false;
                    }
                    const style=getComputedStyle(shape);
                    if(!visible || (style.fill==='none'&&style.stroke==='none')) continue;
                    if(effect==='doodle' && (style.fill!=='none'||style.stroke==='none'||Number(style.strokeWidth.replace('px',''))<=0))
                        throw Error('Các nét trong group doodles cần fill="none", stroke và stroke-width lớn hơn 0.');
                    const m=shape.getScreenCTM();
                    if(!m||![m.a,m.b,m.c,m.d,m.e,m.f].every(Number.isFinite)) throw Error('Transform SVG không hợp lệ.');
                    const scale=Math.max(Math.hypot(m.a,m.b),Math.hypot(m.c,m.d));
                    let paths=[shape];
                    if(shape.tagName.toLowerCase()==='path' && effect!=='doodle') {
                        const d=shape.getAttribute('d')||'';
                        if(d.length>200000) throw Error('Path quá dài.');
                        if(/[^MmLlHhVvCcSsQqTtAaZz0-9eE+.,\s-]/.test(d)) throw Error('Lệnh path không hợp lệ.');
                        const parts=d.match(/[Mm][^Mm]*/g)||[];
                        if(!parts.length && d.trim()) throw Error('Path cần bắt đầu bằng moveto.');
                        let last={x:0,y:0};paths=[];
                        for(const part of parts){
                            const p=document.createElementNS('http://www.w3.org/2000/svg','path');
                            let isolated=part;
                            if(part[0]==='m') {
                                const first=part.match(/^m\s*([-+]?(?:\d*\.?\d+)(?:[eE][-+]?\d+)?)[\s,]*([-+]?(?:\d*\.?\d+)(?:[eE][-+]?\d+)?)/);
                                if(!first) throw Error('Relative moveto không hợp lệ.');
                                const remainder=part.slice(first[0].length).replace(/^[\s,]+/,'');
                                isolated=`M ${last.x+Number(first[1])} ${last.y+Number(first[2])} `+(/^[+\-.\d]/.test(remainder)?'l ':'')+remainder;
                            }
                            p.setAttribute('d',isolated);
                            const length=p.getTotalLength();
                            last=p.getPointAtLength(length);
                            if(length>0) paths.push(p);
                        }
                    }
                    for(const path of paths){
                        const length=path.getTotalLength();
                        if(!Number.isFinite(length)||length*scale>200000) throw Error('Đường vẽ quá lớn.');
                        if(length<=0) continue;
                        const steps=Math.max(2,Math.ceil(length*scale/1.5));
                        pointCount+=steps+1;
                        if(pointCount>250000||result.length>=4000) throw Error('SVG quá phức tạp cho bản đầu.');
                        const points=[];
                        for(let i=0;i<=steps;i++){
                            const p=path.getPointAtLength(length*i/steps);
                            const x=p.x*m.a+p.y*m.c+m.e, y=p.x*m.b+p.y*m.d+m.f;
                            if(!Number.isFinite(x)||!Number.isFinite(y)||Math.abs(x)>100000||Math.abs(y)>100000) throw Error('Tọa độ SVG vượt giới hạn.');
                            points.push([x,y]);
                        }
                        result.push({points,shapeIndex,length});
                    }
                }
                return {paths:result,hasText:!!svg.querySelector('text'),browser:navigator.userAgent};
            }''', {'source': source, 'width': width, 'height': height, 'effect':effect})
            page.evaluate('document.fonts.ready')
            page.evaluate('async () => { await Promise.all([...document.querySelectorAll("image")].map(el => new Promise((resolve,reject) => { const img=new Image(); img.onload=resolve; img.onerror=()=>reject(Error("Không đọc được ảnh nền.")); img.src=el.href.baseVal; }))); }')
            png = page.screenshot(type='png', animations='disabled')
            final = Image.open(io.BytesIO(png)).convert('RGB')
            if not geometry['paths']:
                raise ValueError('SVG chưa có đường vector có thể vẽ. Chữ sẽ hiện trong giai đoạn màu, nhưng cần ít nhất một shape/path.')
            if effect == 'doodle':
                # A separate solid mask reveals each original stroke. The source stroke
                # keeps its own color, dashes, opacity and transforms unchanged.
                page.evaluate(r'''paths => {
                    const ns='http://www.w3.org/2000/svg',svg=document.querySelector('svg');
                    const defs=document.createElementNS(ns,'defs');svg.prepend(defs);
                    const shapes=svg.querySelector('g[id="doodles"]').querySelectorAll('path,line,polyline,polygon,rect,circle,ellipse');
                    window.reveals=paths.map((p,i)=>{
                        const shape=shapes[p.shapeIndex], mask=document.createElementNS(ns,'mask');
                        let id='__reveal_'+i;while(document.getElementById(id)) id+='_';
                        for(const [k,v] of Object.entries({id,maskUnits:'userSpaceOnUse',maskContentUnits:'userSpaceOnUse',x:-100000,y:-100000,width:200000,height:200000})) mask.setAttribute(k,v);
                        const reveal=shape.cloneNode(false),style=getComputedStyle(shape);
                        for(const key of [...reveal.attributes].map(a=>a.name))
                            if(!['d','points','x','y','x1','x2','y1','y2','cx','cy','r','rx','ry','width','height'].includes(key)) reveal.removeAttribute(key);
                        reveal.setAttribute('fill','none');reveal.setAttribute('stroke','white');
                        reveal.setAttribute('stroke-width',parseFloat(style.strokeWidth)+2);
                        reveal.setAttribute('stroke-linecap','round');reveal.setAttribute('stroke-linejoin','round');
                        reveal.setAttribute('stroke-dasharray',`${p.length} ${p.length+1}`);
                        reveal.setAttribute('stroke-dashoffset',p.length+1);
                        mask.append(reveal);defs.append(mask);shape.setAttribute('mask',`url(#${id})`);
                        return {shape,reveal,length:p.length,mask:`url(#${id})`};
                    });
                }''', geometry['paths'])
            yield geometry, final, page
        finally:
            browser.close()


def prepare_scene(source: str, width: int, height: int):
    with open_scene(source, width, height) as (geometry, final, _):
        return geometry, final


def overlay_frame(page, timeline, progress):
    target = timeline[-1].pause_end_unit * min(1., max(0., progress))
    amounts = [min(1., max(0., (target-item.start_unit)/item.length)) for item in timeline]
    page.evaluate('''amounts => window.reveals.forEach((r,i)=>{
        const a=amounts[i];r.shape.style.visibility=a<=0?'hidden':'visible';
        if(a>=1) r.shape.removeAttribute('mask');
        else {r.shape.setAttribute('mask',r.mask);r.reveal.setAttribute('stroke-dashoffset',r.length*(1-a));}
    })''', amounts)
    return Image.open(io.BytesIO(page.screenshot(type='png', animations='disabled'))).convert('RGB')


def evaluate_strokes(timeline, progress):
    """Absolute evaluator: repeat/seek calls do not depend on frame history."""
    if not timeline or progress <= 0:
        return [], None
    total = timeline[-1].pause_end_unit
    target = total * min(1., max(0., progress))
    visible = []
    tip = None
    for item in timeline:
        if target <= item.start_unit:
            break
        amount = min(item.length, max(0., target - item.start_unit))
        pts = wb._stroke_segment_between(item.stroke.points, item.cumulative, 0., amount)
        if len(pts) > 1:
            visible.append(pts)
        if item.start_unit < target < item.end_unit:
            tip = wb._point_at_distance(item.stroke.points, item.cumulative, amount)
    # Pen is lifted/hidden during pauses and at transitions; no connector ink.
    return visible, tip


def render(job_file: Path):
    with ExitStack() as resources:
        return render_job(job_file, resources)


def render_job(job_file: Path, resources):
    started = time.monotonic()
    job_file = job_file.resolve()
    directory = job_file.parent
    request = json.loads(job_file.read_text(encoding='utf-8-sig'))
    if request.get('schemaVersion') != 1:
        raise ValueError('Phiên bản tác vụ không được hỗ trợ.')
    width, height, fps = request['width'], request['height'], request['fps']
    if (width,height,fps) not in {(540,960,15),(960,540,15),(1080,1920,30),(1920,1080,30),(320,180,15)}:
        raise ValueError('Kích thước hoặc FPS không được hỗ trợ.')
    settings = request['settings']
    effect = settings.get('effect', 'whiteboard')
    if effect not in ('whiteboard', 'doodle'):
        raise ValueError('Hiệu ứng không hợp lệ.')
    duration, hold = float(settings['duration']), float(settings['hold'])
    scale = float(settings['handScale'])
    hand = settings['hand']
    if not all(map(math.isfinite, (duration,hold,scale))) or not 3<=duration<=120 or not .5<=hold<=duration-1.5 or not .2<=scale<=1.5 or hand not in (*wb.BUILTIN_HANDS,'none'):
        raise ValueError('Thiết lập render không hợp lệ.')
    source = (directory / 'input.svg').read_text(encoding='utf-8-sig')
    progress('Preparing', 'Đang đọc SVG và chuẩn bị hình màu')
    if effect == 'doodle':
        geometry, final, overlay_page = resources.enter_context(open_scene(source, width, height, effect))
    else:
        geometry, final = prepare_scene(source, width, height)
    final.save(directory / 'original.png')
    total_frames = round(duration*fps)
    hold_frames = round(hold*fps)
    available = total_frames - hold_frames
    color_frames = 0 if effect == 'doodle' else min(round(2*fps), max(1, available//3))
    draw_frames = available - color_frames
    strokes = [Stroke([tuple(p) for p in path['points']], source='svg') for path in geometry['paths']]
    timeline = wb._prepare_timeline(strokes, draw_frames)
    cursor = wb._load_hand_cursor(hand, (width,height), scale) if hand != 'none' else None
    warning = ('Chữ ngoài lớp doodle hiển thị sẵn trên nền.' if effect == 'doodle' else 'Chữ sẽ xuất hiện cùng phần màu; bản đầu chưa mô phỏng viết từng nét chữ.') if geometry['hasText'] else None
    progress('Rendering', 'Đang vẽ nét', done=0, total=total_frames, warning=warning)
    binary = shutil.which('ffmpeg')
    if not binary or not shutil.which('ffprobe'):
        raise ValueError('Không tìm thấy ffmpeg/ffprobe trong PATH.')
    partial = directory / 'output.partial.mp4'
    command = [binary,'-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24',
               '-s',f'{width}x{height}','-framerate',str(fps),'-i','pipe:0','-an','-c:v','libx264',
               '-threads','2','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(partial)]
    line_width = max(2, round(min(width,height)/350))
    outline = None
    with (directory/'encoder.log').open('wb') as log:
        encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log)
        try:
            for index in range(total_frames):
                if index < draw_frames:
                    amount = index/max(1,draw_frames-1)
                    visible, tip = evaluate_strokes(timeline, amount)
                    if effect == 'doodle':
                        frame = overlay_frame(overlay_page, timeline, amount)
                    else:
                        frame = Image.new('RGB',(width,height),'white')
                        pen = ImageDraw.Draw(frame)
                        for points in visible:
                            pen.line(points,fill=wb.SKETCH_INK_COLOR,width=line_width,joint='curve')
                    if index == draw_frames-1:
                        outline = frame.copy()
                    if cursor is not None and tip is not None:
                        frame = wb._paste_hand_cursor(frame,tip[0],tip[1],cursor)
                    stage = 'Đang vẽ doodle trên nền' if effect == 'doodle' else 'Đang vẽ nét'
                elif index < available:
                    value = (index-draw_frames+1)/color_frames
                    frame, _, _ = wb._color_fill_frame(outline,final,value,mode='fade')
                    stage = 'Đang hiện màu gốc'
                else:
                    frame = final
                    stage = 'Đang giữ hình cuối'
                wb._write_ffmpeg_frame(encoder,frame)
                if index%max(1,fps//3)==0 or index==total_frames-1:
                    progress('Rendering',stage,done=index+1,total=total_frames)
            encoder.stdin.close()
            if encoder.wait(timeout=90) != 0:
                raise ValueError('FFmpeg không encode được video. Xem encoder.log của tác vụ.')
        finally:
            if encoder.poll() is None:
                encoder.kill()
                encoder.wait()
    progress('Validating','Đang kiểm tra MP4',done=total_frames,total=total_frames)
    probe = subprocess.run([shutil.which('ffprobe'),'-v','error','-select_streams','v:0','-count_frames',
                            '-show_streams','-show_format','-of','json',str(partial)],capture_output=True,check=True,timeout=60)
    metadata = json.loads(probe.stdout)
    stream = metadata['streams'][0]
    if stream['codec_name']!='h264' or stream['pix_fmt']!='yuv420p' or stream['width']!=width or stream['height']!=height or int(stream['nb_read_frames'])!=total_frames:
        raise ValueError('Video không đạt kiểm tra codec, kích thước hoặc số frame.')
    if abs(float(metadata['format']['duration'])-total_frames/fps)>1/fps:
        raise ValueError('Thời lượng video không khớp thiết lập.')
    rate = stream['avg_frame_rate'].split('/')
    if abs(int(rate[0])/int(rate[1])-fps)>1e-6:
        raise ValueError('FPS video không khớp thiết lập.')
    result = {'adapterVersion':VERSION,'effect':effect,'upstreamCommit':UPSTREAM,'frames':total_frames,'width':width,'height':height,
              'fps':fps,'duration':total_frames/fps,'strokeCount':len(strokes),'browser':geometry['browser'],
              'elapsedSeconds':round(time.monotonic()-started,2),'ffprobe':metadata}
    (directory/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    partial.replace(directory/'output.mp4')
    emit('complete',**{k:v for k,v in result.items() if k!='ffprobe'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--job',type=Path,required=True)
    args = parser.parse_args()
    try:
        render(args.job)
    except Exception as error:
        (args.job.resolve().parent/'renderer.log').write_text(traceback.format_exc(),encoding='utf-8')
        emit('error',message=user_error(error))
        sys.exit(1)
