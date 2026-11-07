"""Exercise the actual FFmpeg audio mix without executing any imported JavaScript."""
from pathlib import Path
import json,subprocess,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'engine'))
from story_render import mix_arguments
with tempfile.TemporaryDirectory(dir=ROOT/'work') as tmp:
    directory=Path(tmp);silent=directory/'silent.mp4';output=directory/'mixed.mp4'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','color=c=blue:s=320x180:r=24:d=3','-c:v','libx264','-threads','2','-pix_fmt','yuv420p',str(silent)],check=True,capture_output=True,timeout=30)
    manifest=json.loads((ROOT/'samples/lost-star/story.json').read_text(encoding='utf-8'))
    manifest['scenes']=[{'id':'one','duration':3,'transition':{'type':'cut'}}]
    manifest['audio']=[{'assetId':'chime','start':.5,'offset':.1,'duration':1,'volume':.3,'fadeIn':.1,'fadeOut':.2}]
    command=mix_arguments(manifest,ROOT/'samples/lost-star',silent,output,3)
    subprocess.run(command,check=True,capture_output=True,timeout=30)
    probe=json.loads(subprocess.run(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(output)],check=True,capture_output=True).stdout)
    video=next(s for s in probe['streams'] if s['codec_type']=='video');audio=next(s for s in probe['streams'] if s['codec_type']=='audio')
    assert video['nb_read_frames']=='72' and audio['codec_name']=='aac'
    assert abs(float(probe['format']['duration'])-3)<.05
    pcm=subprocess.run(['ffmpeg','-v','error','-i',str(output),'-map','0:a','-f','f32le','-ac','1','-ar','8000','pipe:1'],capture_output=True,check=True).stdout
    import struct
    values=struct.unpack('<'+'f'*(len(pcm)//4),pcm)
    energy=lambda start,end:sum(x*x for x in values[int(start*8000):int(end*8000)])/max(1,int((end-start)*8000))
    assert energy(0,.35)<energy(.7,1.2)*.01
    assert energy(2,2.5)<energy(.7,1.2)*.01
    print('PASS real FFmpeg: 72 video frames, AAC, 3s duration, offset/trim/fade and bounded active audio interval.')
