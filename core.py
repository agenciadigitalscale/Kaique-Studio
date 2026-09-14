"""Local editing model. Source timestamps are never destructively modified."""
from __future__ import annotations
import copy, json, math, os, re, shutil, subprocess, tempfile, unicodedata, uuid
from pathlib import Path

VERSION = 2
FILTERS = {
    'Original': '',
    'Quente': 'eq=saturation=1.08:gamma_r=1.04:gamma_b=0.97',
    'Frio': 'eq=saturation=1.03:gamma_b=1.06:gamma_r=0.95',
    'Vívido': 'eq=saturation=1.25:contrast=1.06',
    'Desbotado': 'eq=saturation=0.8:contrast=0.93:brightness=0.02',
    'Contraste': 'eq=contrast=1.12:saturation=1.06',
    'Nítido': 'unsharp=5:5:0.8:5:5:0.0',
    'Suave': 'gblur=sigma=0.8',
    'Vinheta': 'vignette=PI/4',
    'Sépia': 'colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131:0',
    'Cinema': 'curves=preset=medium_contrast,eq=saturation=1.05',
    'Preto e branco': 'hue=s=0',
}
CAPTION_STYLES = ['Realce', 'Pop', 'Contorno']
CORNERS = {'Superior direito': 'W-w-24:24', 'Superior esquerdo': '24:24',
           'Inferior direito': 'W-w-24:H-h-24', 'Inferior esquerdo': '24:H-h-24'}


def overlays_of(p):
    """Lista efetiva de sobreposições: as novas `overlays` mais o `sticker`
    único legado dobrado como uma — projeto antigo (um sticker) segue valendo
    com uma linha, sem migração de dado."""
    items = [dict(o) for o in p.get('overlays', [])]
    if p.get('sticker') and not items:
        items = [dict(path=p['sticker'], start=float(p.get('sticker_start', 0)),
                      end=float(p.get('sticker_end', 5)), corner='Superior direito', width=180)]
    return items


def project():
    return dict(version=VERSION, id=str(uuid.uuid4()), client='', source='', duration=0,
                width=0, height=0, takes=[], words=[], ranges=[], script='', music='', music_volume=0.15, music_fade=1.0,
                sfx=[], sticker='', sticker_start=0, sticker_end=5, overlays=[], lut='',
                color='#C9FF63', font_size=22, caption_mode='Palavra ativa', caption_style='Realce', keywords='',
                filter='Original', transition='Nenhuma', zoom=1.0, captions_enabled=True,
                aspect='Original', quality='Alta (1080p)', titles=[])


# Textos/títulos na tela (hooks, chamadas) — independentes da legenda da fala.
# O valor é o código de alinhamento do ASS: 8=topo, 5=centro, 2=rodapé (centralizados).
TITLE_POSITIONS = {'Topo': 8, 'Centro': 5, 'Rodapé': 2}

# Extensões de VÍDEO — uma sobreposição com essas toca como b-roll (sem -loop 1).
VIDEO_EXT = {'.mp4', '.mov', '.webm', '.mkv', '.avi', '.m4v'}


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
    if p.get('caption_style', 'Realce') not in CAPTION_STYLES:
        raise ValueError('Animação de legenda inválida.')
    if p.get('aspect', 'Original') not in ASPECT_CHOICES:
        raise ValueError('Proporção de saída inválida.')
    if p.get('quality', 'Alta (1080p)') not in QUALITY_CHOICES:
        raise ValueError('Resolução de saída inválida.')
    for t in p.get('titles', []):
        if not str(t.get('text', '')).strip():
            raise ValueError('Um texto na tela está sem conteúdo.')
        s, e = float(t['start']), float(t['end'])
        if not math.isfinite(s + e) or not 0 <= s < e:
            raise ValueError('Tempo do texto na tela inválido.')
        if t.get('position', 'Centro') not in TITLE_POSITIONS:
            raise ValueError('Posição do texto na tela inválida.')
        if not 12 <= int(t.get('size', 40)) <= 120:
            raise ValueError('Tamanho do texto na tela fora da faixa (12–120).')
    if not 0 <= float(p.get('music_fade', 1.0)) <= 10:
        raise ValueError('Fade da música fora da faixa (0–10s).')
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
    for o in overlays_of(p):
        if files and not Path(o['path']).is_file():
            raise ValueError('Imagem de sobreposição não encontrada: ' + o['path'])
        if not 0 <= float(o['start']) < float(o['end']) <= length + 0.05:
            raise ValueError('Ajuste o início/fim de uma sobreposição para a duração final.')
        if o.get('corner', 'Superior direito') not in CORNERS:
            raise ValueError('Posição de sobreposição inválida.')
        if not 20 <= int(o.get('width', 180)) <= 600:
            raise ValueError('Largura de sobreposição fora da faixa (20–600).')
    if len(overlays_of(p)) > 8:
        raise ValueError('Limite desta versão: 8 sobreposições por projeto.')


def duration(p):
    return sum(r['end']-r['start'] for r in p['ranges'] if r['enabled'])


# Intensidade do corte automático de silêncios: quão longa uma pausa entre falas
# precisa ser para virar corte. Menor = corta mais (mais agressivo). São os
# valores por trás do controle Leve/Médio/Agressivo no editor.
SILENCE_LEVELS = {'Leve': 1.0, 'Médio': 0.65, 'Agressivo': 0.35}


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


# Fim de frase: ponto/exclamação/interrogação/reticências, com aspas ou parêntese
# de fechamento depois. Quebrar a legenda aqui deixa cada frase inteira na tela.
_SENTENCE_END = re.compile(r'[.!?…]+["\')\]]*$')


def _capitalize_first(text):
    """Deixa maiúscula a primeira LETRA (pulando aspas/parênteses iniciais)."""
    for i, ch in enumerate(text):
        if ch.isalpha():
            return text[:i] + ch.upper() + text[i+1:]
    return text


def polish_words(words):
    """Capitaliza o começo de cada frase — a parte segura da 'pontuação automática'.

    Deixa maiúscula a primeira palavra e a que vem depois de fim de frase (. ! ?).
    De propósito NÃO inventa vírgulas nem pontos: restaurar pontuação de forma
    confiável exigiria um modelo, e chutar pontuação erraria mais do que ajudaria.
    O Whisper já emite parte da pontuação em pt; aqui só arrumamos as maiúsculas.
    Devolve uma lista NOVA (não muta a original).
    """
    out, start_sentence = [], True
    for w in words:
        text = _capitalize_first(w['text']) if start_sentence and w['text'] else w['text']
        out.append(dict(w, text=text))
        start_sentence = bool(_SENTENCE_END.search(text))
    return out


# Palavras "vazias" (stopwords) do português — artigos, preposições, pronomes,
# conjunções e verbos de apoio. Não são o que se quer destacar numa legenda; o
# destaque automático guarda o resto (substantivos, verbos plenos, adjetivos).
_STOPWORDS_PT = {
    'a','o','as','os','um','uma','uns','umas','de','do','da','dos','das','em','no','na','nos','nas',
    'ao','aos','pra','para','por','pelo','pela','pelos','pelas','com','sem','sob','sobre','entre','ate','ate',
    'e','ou','mas','que','se','como','quando','onde','porque','pois','entao','tambem','nem','ja','la','ali','aqui',
    'eu','tu','ele','ela','nos','vos','eles','elas','voce','voces','me','te','lhe','nos','vos','meu','minha','teu',
    'seu','sua','seus','suas','dele','dela','deles','delas','este','esta','estes','estas','esse','essa','esses',
    'essas','isso','isto','aquilo','aquele','aquela','ser','sou','somos','sao','foi','era','sera','ter','tem','tinha',
    'estar','esta','estao','muito','muita','mais','menos','todo','toda','todos','todas','cada','bem','ainda','so',
    'nao','sim','vai','vou','ir','fazer','faz','ficar','fica','coisa','ai',
}


def content_keywords(texts):
    """Escolhe automaticamente as palavras 'de conteúdo' de uma fala.

    Descarta stopwords e palavras muito curtas — o que sobra (substantivos,
    verbos plenos, adjetivos) é o que merece destaque na legenda. Devolve as
    chaves NORMALIZADAS (minúsculas, sem acento, sem pontuação), no mesmo formato
    que `make_ass` usa para casar palavra por palavra.
    """
    out = set()
    for text in texts:
        key = normalized(text).strip('.,!?;:"\'()[]')
        if len(key) >= 4 and key not in _STOPWORDS_PT:
            out.add(key)
    return out


def group_words(words, max_words=5, max_chars=30, gap=0.45):
    """Agrupa as palavras em frases curtas e legíveis — a 'legenda inteligente'.

    Em vez de palavra-a-palavra ou de um bloco fixo de N, quebra onde a leitura
    pede: fim de frase (. ! ?), pausa longa (`gap`), estouro de palavras
    (`max_words`) ou de largura (`max_chars`, para a linha não transbordar a tela).
    Função pura: recebe as palavras já mapeadas para o tempo final e devolve
    listas de palavras. `make_ass` desenha; a decisão de quebra fica aqui, testável.
    """
    groups = []
    for word in words:
        cur = groups[-1] if groups else None
        if cur is None:
            groups.append([word]); continue
        cur_chars = sum(len(w['text']) for w in cur) + (len(cur) - 1)  # com os espaços
        would_be = cur_chars + 1 + len(word['text'])
        if (_SENTENCE_END.search(cur[-1]['text'])
                or len(cur) >= max_words
                or would_be > max_chars
                or (word['start'] - cur[-1]['end']) > gap):
            groups.append([word])
        else:
            cur.append(word)
    return groups


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
    # Textos na tela primeiro: valem mesmo com a legenda da fala desligada.
    for t in p.get('titles', []):
        if float(t['end']) - float(t['start']) < 0.005:
            continue
        an = TITLE_POSITIONS.get(t.get('position', 'Centro'), 5)
        size = round(int(t.get('size', 40)) * 2.5)
        col = ass_color(t.get('color', p['color']))
        tag = '{\\an' + str(an) + '\\fs' + str(size) + '\\c' + col + '\\bord3\\3c&H101010&}'
        head += f'Dialogue: 0,{ass_time(float(t["start"]))},{ass_time(float(t["end"]))},Main,,0,0,0,,{tag}{safe_text(t["text"])}\n'
    if not p['captions_enabled']:
        return head
    words = mapped_words(p)
    groups = group_words(words)
    keywords = set(re.findall(r'\w+',normalized(p['keywords'])))
    # Sem palavras-chave digitadas? O modo 'Palavras-chave' escolhe sozinho as
    # palavras de conteúdo — o destaque automático, sem o editor ter que pensar.
    if not keywords and p['caption_mode']=='Palavras-chave':
        keywords = content_keywords(w['text'] for w in words)
    accent=ass_color(p['color'])
    # A decoração da palavra ativa muda com caption_style. Vale no modo
    # 'Palavra ativa', o único que anima palavra a palavra — os outros mostram
    # o grupo inteiro de uma vez, onde animar por palavra não faz sentido.
    style=p.get('caption_style','Realce')
    if style=='Pop':
        active_tag='{\c'+accent+r'\fscx82\fscy82\t(0,110,\fscx112\fscy112)\t(110,200,\fscx100\fscy100)}'
    elif style=='Contorno':
        active_tag=r'{\c&HFFFFFF&\bord5\3c'+accent+'}'
    else:
        active_tag='{\c'+accent+'}'
    def line(a,b,text):
        if b-a<0.005:
            return ''
        return f'Dialogue: 0,{ass_time(a)},{ass_time(b)},Main,,0,0,0,,{text}\n'
    for group in groups:
        if p['caption_mode']=='Palavra ativa':
            for i,w in enumerate(group):
                tokens=[]
                for j,x in enumerate(group):
                    tag=active_tag if i==j else r'{\c&HFFFFFF&}'
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
    return polish_words(words)  # capitaliza o início de cada frase


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
        overlay_inputs=[]
        for o in overlays_of(p):
            overlay_inputs.append((input_index,o));input_index+=1
            # Vídeo sobreposto (b-roll/meme) toca normal; imagem estática entra em loop.
            if Path(o['path']).suffix.lower() in VIDEO_EXT:
                args+=['-i',o['path']]
            else:
                args+=['-loop','1','-i',o['path']]
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
        if overlay_inputs:
            current='[basev]'
            for n,(idx,o) in enumerate(overlay_inputs):
                width=int(o.get('width',180));corner=CORNERS[o.get('corner','Superior direito')]
                filters.append(f'[{idx}:v]scale={width}:-1[ov{n}]')
                out='[outv]' if n==len(overlay_inputs)-1 else f'[ovbase{n}]'
                # imagem em loop precisa de shortest=1 (senão fica infinita); vídeo
                # NÃO — com shortest=1 ele cortaria a base ao acabar. -t já limita a saída.
                short=0 if Path(o['path']).suffix.lower() in VIDEO_EXT else 1
                filters.append(f"{current}[ov{n}]overlay={corner}:enable='between(t,{o['start']},{o['end']})':shortest={short}{out}")
                current=out
        else:
            filters.append('[basev]null[outv]')
        labels=['[voice]'];filters.append('[0:a]anull[voice]')
        if music_index is not None:
            total=min(duration(p),10) if preview else duration(p)
            fade=max(0.0,float(p.get('music_fade',1.0)))
            mf=f'volume={p["music_volume"]}'
            if fade>0.01:  # entrada e saída suaves — trilha não estoura nem corta seco
                mf+=f',afade=t=in:st=0:d={fade},afade=t=out:st={max(0,total-fade)}:d={fade}'
            filters.append(f'[{music_index}:a]{mf}[music]');labels.append('[music]')
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


# Proporção e resolução de SAÍDA. 'Original' mantém a do take. Os demais reenquadram
# a sequência na moldura escolhida (com letterbox), sem tocar nos arquivos originais.
ASPECTS = {'9:16': (9, 16), '1:1': (1, 1), '16:9': (16, 9), '4:5': (4, 5), '5:4': (5, 4), '4:3': (4, 3)}
QUALITIES = {'Máxima (4K)': 2160, 'Alta (1080p)': 1080, 'Média (720p)': 720, 'Leve (480p)': 480}
ASPECT_CHOICES = ['Original'] + list(ASPECTS)
QUALITY_CHOICES = list(QUALITIES)


def target_dims(aspect, quality='Alta (1080p)'):
    """Dimensões (par, largura×altura) da moldura de saída para a proporção e
    resolução escolhidas. 'Original' devolve None (o pipeline usa a do take).

    `quality` é o LADO MENOR (1080/720/480): num 9:16 é a largura (1080×1920),
    num 16:9 é a altura (1920×1080) — é assim que 'resolução' é lida em vídeo.
    """
    if aspect not in ASPECTS:
        return None
    aw, ah = ASPECTS[aspect]
    short = QUALITIES.get(quality, 1080)
    if aw <= ah:
        w, h = short, round(short * ah / aw)
    else:
        h, w = short, round(short * aw / ah)
    return (max(2, w // 2 * 2), max(2, h // 2 * 2))


def assemble(paths, destination, progress=lambda message: None, canvas=None):
    """Normalize takes into a persistent editing source; never modify originals.

    `canvas=(w,h)` força a moldura de saída (proporção/resolução escolhidas);
    None mantém a dimensão do primeiro take (comportamento antigo)."""
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
    if canvas:  # proporção/resolução escolhidas vencem a dimensão do take
        width, height = int(canvas[0])//2*2, int(canvas[1])//2*2
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
