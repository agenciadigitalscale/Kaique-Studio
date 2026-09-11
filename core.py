"""Local editing model. Source timestamps are never destructively modified."""
from __future__ import annotations
import copy, json, math, os, re, shutil, subprocess, tempfile, unicodedata, uuid
from pathlib import Path

VERSION = 2
FILTERS = {'Original': '', 'Quente': 'eq=saturation=1.08:gamma_r=1.04:gamma_b=0.97',
           'Contraste': 'eq=contrast=1.12:saturation=1.06', 'Preto e branco': 'hue=s=0'}


def project():
    return dict(version=VERSION, id=str(uuid.uuid4()), client='', source='', duration=0,
                width=0, height=0, takes=[], words=[], ranges=[], script='', music='', music_volume=0.15,
                sfx=[], sticker='', sticker_start=0, sticker_end=5, lut='',
                color='#C9FF63', font_size=22, caption_mode='Palavra ativa', keywords='',
                filter='Original', transition='Nenhuma', zoom=1.0, captions_enabled=True)


def ffmpeg():
    candidate = shutil.which('ffmpeg')
    if candidate:
        return candidate
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def run(args, cwd=None):
    result = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding='utf-8', errors='replace',
                            creationflags=0x08000000 if os.name == 'nt' else 0)
    if result.returncode:
        raise RuntimeError(result.stderr[-2400:] or 'Não foi possível processar o arquivo.')
    return result


def probe(path):
    import av
    with av.open(str(path)) as media:
        videos = list(media.streams.video)
        if not videos:
            raise ValueError('Este arquivo não contém vídeo.')
        stream = videos[0]
        duration = float(media.duration / av.time_base) if media.duration else float((stream.duration or 0) * stream.time_base)
        if duration <= 0:
            raise ValueError('Não foi possível identificar a duração.')
        return dict(duration=duration, width=stream.width, height=stream.height, audio=bool(media.streams.audio))


def validate(p, files=True):
    if p.get('version') != VERSION:
        raise ValueError('Projeto incompatível. Use um projeto criado no Studio 0.2.')
    d = float(p['duration'])
    if not math.isfinite(d) or d <= 0:
        raise ValueError('Importe um vídeo antes de continuar.')
    if files and not Path(p['source']).is_file():
        raise ValueError('Vídeo original não encontrado. Importe-o novamente.')
    previous = 0
    for r in p['ranges']:
        a, b = float(r['start']), float(r['end'])
        if not math.isfinite(a+b) or not 0 <= a < b <= d+0.05 or a < previous-0.001:
            raise ValueError('Revise os trechos: início e fim devem estar dentro do vídeo e sem sobreposição.')
        previous = b
    if not any(r['enabled'] for r in p['ranges']):
        raise ValueError('Mantenha pelo menos um trecho selecionado.')
    previous = 0
    for w in p['words']:
        a, b = float(w['start']), float(w['end'])
        if not math.isfinite(a+b) or not 0 <= a < b <= d+0.1 or a < previous-0.001 or not str(w['text']).strip():
            raise ValueError('Revise o tempo e o texto das palavras: não podem se sobrepor.')
        previous = b
    if not re.fullmatch(r'#[0-9A-Fa-f]{6}', p['color']):
        raise ValueError('Cor de legenda inválida.')
    if not 10 <= int(p['font_size']) <= 50 or p['caption_mode'] not in ['Palavra ativa', 'Palavras-chave', 'Frase']:
        raise ValueError('Estilo de legenda inválido.')
    if p['filter'] not in FILTERS or not 1 <= float(p['zoom']) <= 1.3 or not 0 <= float(p['music_volume']) <= 1:
        raise ValueError('Ajuste de imagem ou áudio inválido.')
    if p.get('transition','Nenhuma') not in ['Nenhuma','Preto','Branco']:
        raise ValueError('Transição inválida.')
    if len(p['sfx']) > 20:
        raise ValueError('Limite desta versão: 20 efeitos sonoros por projeto.')
    for key in ['music','lut','sticker']:
        if files and p[key] and not Path(p[key]).is_file():
            raise ValueError(f'Arquivo não encontrado: {p[key]}')
    length = duration(p)
    for s in p['sfx']:
        if files and not Path(s['path']).is_file():
            raise ValueError('Efeito sonoro não encontrado.')
        if not 0 <= float(s['time']) < length or not 0 <= float(s['volume']) <= 1:
            raise ValueError('Ajuste o tempo do efeito sonoro para a duração final.')
    if p['sticker'] and not 0 <= float(p['sticker_start']) < float(p['sticker_end']) <= length+0.05:
        raise ValueError('Ajuste o início/fim do sticker para a duração final.')


def duration(p):
    return sum(r['end']-r['start'] for r in p['ranges'] if r['enabled'])


def suggest_ranges(words, total, threshold=0.65, padding=0.12):
    """Only remove long gaps between recognized words. Not breath classification."""
    if not words:
        raise ValueError('Transcreva o vídeo antes de sugerir cortes.')
    ranges = []
    start = max(0, words[0]['start']-padding)
    end = min(total, words[0]['end']+padding)
    for word in words[1:]:
        if word['start'] - (end-padding) > threshold:
            if end > start:
                ranges.append(dict(start=round(start,3), end=round(end,3), enabled=True))
            start = max(0, word['start']-padding)
        end = min(total, max(end, word['end']+padding))
    if end > start:
        ranges.append(dict(start=round(start,3), end=round(end,3), enabled=True))
    return ranges


def mapped_words(p):
    result, offset = [], 0
    for r in p['ranges']:
        if not r['enabled']:
            continue
        for word in p['words']:
            a, b = max(word['start'],r['start']), min(word['end'],r['end'])
            if b-a > 0.005:
                result.append(dict(start=offset+a-r['start'], end=offset+b-r['start'], text=word['text']))
        offset += r['end']-r['start']
    return result


def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFD',text.lower()) if unicodedata.category(c) != 'Mn')


def commands(text):
    """Finite command grammar: never pretends to be a generative model."""
    actions, unknown = [], []
    for original in re.split(r'[;\n]+', text):
        t = normalized(original.strip()).rstrip('.')
        if not t:
            continue
        if t in ['cortes e legenda', 'cortes e legendas', 'cortar e legendar', 'cortar pausas e legendar']:
            actions.extend([('captions_enabled',True,'Ativar legendas'),('caption_mode','Palavra ativa','Destacar a palavra ativa'),('cuts',True,'Sugerir cortes entre falas para revisão')])
        elif t in ['legendar','legenda','legendas']:
            actions.extend([('captions_enabled',True,'Ativar legendas'),('caption_mode','Palavra ativa','Destacar a palavra ativa')])
        elif t in ['cortar pausas','remover pausas','sugerir cortes']:
            actions.append(('cuts',True,'Sugerir cortes entre falas para revisão'))
        elif t in ['legendas dinamicas','legendas por palavra','destacar palavra ativa']:
            actions.append(('caption_mode','Palavra ativa','Destacar a palavra ativa'))
        elif t in ['legendas por palavras-chave','destacar palavras-chave']:
            actions.append(('caption_mode','Palavras-chave','Usar as palavras-chave do painel de legendas'))
        elif t in ['sem legendas','remover legendas']:
            actions.append(('captions_enabled',False,'Desativar legendas na exportação'))
        elif t in ['ativar legendas','com legendas']:
            actions.append(('captions_enabled',True,'Ativar legendas'))
        elif t in ['filtro quente','filtro contraste','filtro original','filtro preto e branco']:
            val={'filtro quente':'Quente','filtro contraste':'Contraste','filtro original':'Original','filtro preto e branco':'Preto e branco'}[t]
            actions.append(('filter',val,f'Filtro: {val}'))
        elif re.fullmatch(r'volume (da )?musica \d{1,3}%',t):
            val = int(re.search(r'(\d+)%',t)[1])
            if val <= 100:
                actions.append(('music_volume',val/100,f'Volume da música: {val}%'))
            else:
                unknown.append(original)
        elif t in ['legendas brancas','legendas amarelas','legendas verdes']:
            val={'legendas brancas':'#FFFFFF','legendas amarelas':'#FFD600','legendas verdes':'#C9FF63'}[t]
            actions.append(('color',val,original.strip()))
        elif re.fullmatch(r'zoom 1[.,](0[0-9]|[12][0-9]|30)',t):
            val=float(t.split()[1].replace(',','.'))
            actions.append(('zoom',val,f'Zoom fixo: {val:.2f}x'))
        else:
            unknown.append(original.strip())
    return actions, unknown


def ass_time(t):
    cs = max(0,round(t*100))
    return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'


def ass_color(color):
    return '&H'+color[5:7]+color[3:5]+color[1:3]+'&'


def safe_text(t):
    return t.replace('\\','／').replace('{','(').replace('}',')').replace('\n',' ')


def make_ass(p):
    canvas_width = max(180,round(720*p.get('width',384)/max(1,p.get('height',288))))
    head = f'''[Script Info]
ScriptType: v4.00+
PlayResX: {canvas_width}
PlayResY: 720
WrapStyle: 0
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Arial,{round(p['font_size']*2.5)},&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,24,24,72,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    if not p['captions_enabled']:
        return head
    words = mapped_words(p)
    groups = []
    for word in words:
        if not groups or len(groups[-1])>=4 or word['start']-groups[-1][-1]['end']>0.35:
            groups.append([])
        groups[-1].append(word)
    keywords = set(re.findall(r'\w+',normalized(p['keywords'])))
    accent=ass_color(p['color'])
    def line(a,b,text):
        if b-a<0.005:
            return ''
        return f'Dialogue: 0,{ass_time(a)},{ass_time(b)},Main,,0,0,0,,{text}\n'
    for group in groups:
        if p['caption_mode']=='Palavra ativa':
            for i,w in enumerate(group):
                tokens=[]
                for j,x in enumerate(group):
                    tag='{\\c'+accent+'}' if i==j else r'{\c&HFFFFFF&}'
                    tokens.append(tag+safe_text(x['text']))
                end=group[i+1]['start'] if i+1<len(group) else w['end']
                head+=line(w['start'],end,' '.join(tokens))
        else:
            tokens=[]
            for w in group:
                key=normalized(w['text']).strip('.,!?;:')
                active=p['caption_mode']=='Frase' or key in keywords
                tokens.append(('{\\c'+accent+'}' if active else r'{\c&HFFFFFF&}')+safe_text(w['text']))
            head+=line(group[0]['start'],group[-1]['end'],r'{\fscx94\fscy94\t(0,100,\fscx100\fscy100)}'+' '.join(tokens))
    return head


def transcribe(source, progress):
    from faster_whisper import WhisperModel
    progress('Carregando modelo de fala. A primeira execução precisa de internet…')
    model=WhisperModel('base',device='cpu',compute_type='int8',cpu_threads=4)
    segments, info=model.transcribe(source,language='pt',word_timestamps=True)
    words=[]
    for seg in segments:
        progress(f'Transcrevendo: {seg.end:.0f}s de {info.duration:.0f}s')
        for w in seg.words or []:
            start=max(float(w.start),words[-1]['end'] if words else 0)
            if w.end>start and w.word.strip():
                words.append(dict(start=round(start,3),end=round(float(w.end),3),text=w.word.strip()))
    if not words:
        raise ValueError('Nenhuma fala detectada. Confira o áudio do vídeo.')
    return words


def render(p, destination, progress=lambda s:None, preview=False):
    validate(p)
    target=Path(destination).resolve()
    if target.exists():
        raise ValueError('Escolha um nome novo; arquivos existentes são preservados.')
    exe=ffmpeg()
    if p['captions_enabled'] and p['words']:
        available=run([exe,'-hide_banner','-filters']).stdout
        if 'subtitles' not in available:
            raise ValueError('Este FFmpeg não inclui legendas. Abra Ajuda > Instalar FFmpeg completo.')
    info=probe(p['source'])
    # Every intermediate lives on the output volume, for atomic non-overwriting publication.
    with tempfile.TemporaryDirectory(prefix='kaique_',dir=target.parent) as tmp:
        work=Path(tmp)
        ranges=[r for r in p['ranges'] if r['enabled']]
        if preview:
            remain=10
            limited=[]
            for r in ranges:
                if remain<=0:
                    break
                count=min(remain,r['end']-r['start'])
                limited.append(dict(start=r['start'],end=r['start']+count,enabled=True))
                remain-=count
            ranges=limited
        for index,r in enumerate(ranges):
            progress(f'Montando trecho {index+1}/{len(ranges)}…')
            args=[exe,'-hide_banner','-loglevel','error','-nostdin','-n','-ss',str(r['start']),'-i',p['source']]
            if not info['audio']:
                args+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
            vf='scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1,fps=30'
            transition=p.get('transition','Nenhuma')
            if transition!='Nenhuma':
                length=r['end']-r['start'];fade=min(.16,length/3);color='black' if transition=='Preto' else 'white'
                if index>0:vf+=f',fade=t=in:st=0:d={fade}:color={color}'
                if index<len(ranges)-1:vf+=f',fade=t=out:st={length-fade}:d={fade}:color={color}'
            args+=['-t',str(r['end']-r['start']),'-map','0:v:0','-map','0:a:0' if info['audio'] else '1:a:0',
                   '-vf',vf,'-c:v','libx264',
                   '-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-threads','4','-c:a','pcm_s16le','-ar','48000','-ac','2',
                   str(work/f'part{index:04}.mkv')]
            run(args)
        (work/'parts.txt').write_text(''.join(f"file 'part{i:04}.mkv'\n" for i in range(len(ranges))),encoding='utf-8')
        run([exe,'-hide_banner','-loglevel','error','-nostdin','-n','-f','concat','-safe','1','-i','parts.txt',
             '-c','copy','joined.mkv'],cwd=work)
        progress('Aplicando legendas, imagem e áudio…')
        rendered_info=probe(work/'joined.mkv')
        caption_project=copy.deepcopy(p)
        caption_project.update(width=rendered_info['width'],height=rendered_info['height'])
        (work/'captions.ass').write_text(make_ass(caption_project),encoding='utf-8')
        args=[exe,'-hide_banner','-loglevel','error','-nostdin','-n','-i','joined.mkv']
        input_index=1
        music_index=None
        if p['music']:
            music_index=input_index; input_index+=1
            args+=['-stream_loop','-1','-i',p['music']]
        sfx_inputs=[]
        for s in p['sfx']:
            sfx_inputs.append((input_index,s));input_index+=1
            args+=['-i',s['path']]
        sticker_index=None
        if p['sticker']:
            sticker_index=input_index
            args+=['-loop','1','-i',p['sticker']]
        filters=[]
        vf=[]
        if p['zoom']>1.001:
            z=p['zoom'];vf.append(f'crop=trunc(iw/{z}/2)*2:trunc(ih/{z}/2)*2,scale={rendered_info["width"]}:{rendered_info["height"]}')
        if FILTERS[p['filter']]:
            vf.append(FILTERS[p['filter']])
        if p['lut']:
            shutil.copyfile(p['lut'],work/'look.cube');vf.append('lut3d=look.cube')
        if p['captions_enabled'] and p['words']:
            vf.append('subtitles=captions.ass')
        filters.append('[0:v]'+(','.join(vf) or 'null')+'[basev]')
        if sticker_index is not None:
            filters.append(f'[{sticker_index}:v]scale=180:-1[st]')
            filters.append(f"[basev][st]overlay=W-w-24:24:enable='between(t,{p['sticker_start']},{p['sticker_end']})':shortest=1[outv]")
        else:
            filters.append('[basev]null[outv]')
        labels=['[voice]'];filters.append('[0:a]anull[voice]')
        if music_index is not None:
            filters.append(f'[{music_index}:a]volume={p["music_volume"]}[music]');labels.append('[music]')
        for n,(idx,s) in enumerate(sfx_inputs):
            filters.append(f'[{idx}:a]volume={s["volume"]},adelay={round(s["time"]*1000)}:all=1[sfx{n}]');labels.append(f'[sfx{n}]')
        filters.append(''.join(labels)+f'amix=inputs={len(labels)}:duration=first:normalize=0,alimiter=limit=0.95:level=0[outa]')
        args+=['-filter_complex',';'.join(filters),'-map','[outv]','-map','[outa]',
               '-t',str(min(duration(p),10) if preview else duration(p)),
               '-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-threads','4',
               '-c:a','aac','-movflags','+faststart','finished.mp4']
        run(args,cwd=work)
        # xb also protects against a target created while rendering.
        with target.open('xb') as out, (work/'finished.mp4').open('rb') as src:
            shutil.copyfileobj(src,out)
    return str(target)


def atomic_json(path,data):
    path=Path(path)
    temp=path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(temp,path)


def assemble(paths, destination, progress=lambda message: None):
    """Normalize takes into a persistent editing source; never modify originals."""
    if not paths:
        raise ValueError('Selecione pelo menos um take.')
    target = Path(destination).resolve()
    if target.exists():
        raise ValueError('A sequência já existe. Use um novo destino.')
    infos = []
    for i, path in enumerate(paths):
        progress(f'Analisando arquivo {i+1}/{len(paths)}: {Path(path).name}')
        infos.append(probe(path))
    # Use decoded orientation, including phone rotation metadata.
    import av
    with av.open(str(paths[0])) as media:
        frame = next(media.decode(video=0))
        rotation = abs(round(getattr(frame, 'rotation', 0))) % 180
    width, height = infos[0]['width'], infos[0]['height']
    if rotation == 90:
        width, height = height, width
    factor = min(1, 1920/max(width, height))
    width, height = max(2,int(width*factor)//2*2), max(2,int(height*factor)//2*2)
    exe = ffmpeg()
    takes = []
    offset = 0.0
    with tempfile.TemporaryDirectory(prefix='takes_', dir=target.parent) as tmp:
        work = Path(tmp)
        for i, (path, info) in enumerate(zip(paths, infos)):
            progress(f'Preparando take {i+1}/{len(paths)}: {Path(path).name}')
            args = [exe,'-v','error','-nostdin','-n','-i',str(Path(path).resolve())]
            if not info['audio']:
                args += ['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
            args += ['-map','0:v:0','-map','0:a:0' if info['audio'] else '1:a:0',
                     '-t',str(info['duration']),'-vf',
                     f'scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30',
                     '-af','aresample=48000,apad','-c:v','libx264','-preset','veryfast','-crf','18',
                     '-pix_fmt','yuv420p','-threads','4','-c:a','pcm_s16le','-ar','48000','-ac','2',
                     str(work/f'take{i:04}.mkv')]
            run(args)
            actual = probe(work/f'take{i:04}.mkv')['duration']
            takes.append(dict(path=str(Path(path).resolve()),start=offset,end=offset+actual))
            offset += actual
        (work/'list.txt').write_text(''.join(f"file 'take{i:04}.mkv'\n" for i in range(len(paths))),encoding='utf-8')
        progress('Finalizando sequência…')
        run([exe,'-v','error','-nostdin','-n','-f','concat','-safe','1','-i','list.txt',
             '-c:v','copy','-c:a','aac','-movflags','+faststart','sequence.mp4'],cwd=work)
        with target.open('xb') as out, (work/'sequence.mp4').open('rb') as src:
            shutil.copyfileobj(src,out)
    result = probe(target)
    takes[-1]['end'] = result['duration']
    return dict(source=str(target), takes=takes, **result)
