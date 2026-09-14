"""Independent source clips; all source times survive reorder and trim."""
import copy, json, math, subprocess, tempfile, uuid
from pathlib import Path
import core

STYLE_KEYS=['music','music_volume','music_fade','sfx','sticker','sticker_start','sticker_end','overlays','lut','color','font_size','caption_mode','caption_style','keywords','filter','transition','zoom','captions_enabled','aspect','quality','titles']
def project():
    defaults=core.project()
    return dict(version=5,client='',script='',clips=[],style={k:defaults[k] for k in STYLE_KEYS})
def length(p):return sum(c['out']-c['in'] for c in p['clips'])
def words(p):
    result=[];offset=0
    for c in p['clips']:
        for w in c['words']:
            a=max(w['start'],c['in']);b=min(w['end'],c['out'])
            if b-a>.005:result.append(dict(start=offset+a-c['in'],end=offset+b-c['in'],text=w['text']))
        offset+=c['out']-c['in']
    return result

def validate(p):
    if p.get('version')!=5:raise ValueError('Abra um projeto nativo 0.5. Para projetos antigos, use a versão anterior.')
    if not p['clips']:raise ValueError('Importe takes primeiro.')
    ids=set()
    for c in p['clips']:
        if c['id'] in ids:raise ValueError('ID de clipe duplicado.')
        ids.add(c['id'])
        if not Path(c['source']).is_file():raise ValueError('Take não encontrado: '+c['source'])
        if not all(math.isfinite(float(c[k])) for k in ['in','out','duration']) or not 0<=c['in']<c['out']<=c['duration']+.001:raise ValueError('Corte fora dos limites do take.')
        if not 0.5<=float(c.get('speed',1.0))<=2.0:raise ValueError('Velocidade do take fora da faixa (0.5–2.0).')
        end=0
        for w in c['words']:
            a,b=float(w['start']),float(w['end'])
            if not math.isfinite(a+b) or not 0<=a<b<=c['duration']+.1 or a<end-.001 or not w['text'].strip():raise ValueError('Revise as palavras e tempos do take.')
            end=b

def legacy(p):
    """Projection for existing effect library; source duration is virtual here."""
    q=core.project();q.update(copy.deepcopy(p['style']));q.update(client=p['client'],script=p['script'])
    if p['clips']:
        first=p['clips'][0];d=length(p)
        q.update(source=first['source'],duration=d,width=first['width'],height=first['height'],ranges=[dict(start=0,end=d,enabled=True)],words=words(p))
    return q

def split(p,index,source_time):
    c=p['clips'][index]
    if not c['in']+.04<source_time<c['out']-.04:raise ValueError('Posicione o cursor dentro do clipe, longe das bordas.')
    a=copy.deepcopy(c);b=copy.deepcopy(c);a['out']=source_time;b['in']=source_time;b['id']=uuid.uuid4().hex
    p['clips'][index:index+1]=[a,b]

def reorder(p,index,target):
    if not 0<=index<len(p['clips']) or not 0<=target<len(p['clips']):raise ValueError('Posição inválida.')
    p['clips'].insert(target,p['clips'].pop(index))

def trim(p,index,start,end):
    c=p['clips'][index]
    if not math.isfinite(start+end) or not 0<=start<end<=c['duration']:raise ValueError('Limites inválidos.')
    c.update({'in':start,'out':end})

def inspect(source,cache,progress=lambda _:None):
    import array
    source=str(Path(source).resolve());info=core.probe(source);folder=Path(cache)/uuid.uuid4().hex;folder.mkdir(parents=True)
    thumbs=[];exe=core.ffmpeg()
    for i,fraction in enumerate([.05,.45,.8]):
        target=folder/f'{i}.jpg'
        core.run([exe,'-v','error','-nostdin','-ss',str(info['duration']*fraction),'-i',source,'-frames:v','1','-vf','scale=160:90:force_original_aspect_ratio=decrease,pad=160:90:(ow-iw)/2:(oh-ih)/2','-threads','2',str(target)])
        thumbs.append(str(target))
    peaks=[]
    if info['audio']:
        progress('Lendo onda de áudio: '+Path(source).name)
        result=subprocess.run([exe,'-v','error','-nostdin','-i',source,'-vn','-ac','1','-ar','8000','-f','s16le','-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=0x08000000 if __import__('os').name=='nt' else 0)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-1000:])
        samples=array.array('h');samples.frombytes(result.stdout)
        size=max(1,math.ceil(len(samples)/700))
        peaks=[max(abs(v) for v in samples[i:i+size])/32768 for i in range(0,len(samples),size)]
    return dict(id=uuid.uuid4().hex,source=source,duration=info['duration'],width=info['width'],height=info['height'],**{'in':0,'out':info['duration']},words=[],thumbs=thumbs,peaks=peaks,proxy='')

def proxy(c,cache,progress=lambda _:None):
    target=Path(cache)/(uuid.uuid4().hex+'.mp4');progress('Criando cópia leve do take…')
    core.run([core.ffmpeg(),'-v','error','-nostdin','-i',c['source'],'-vf',"scale=640:640:force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1",'-c:v','libx264','-preset','veryfast','-crf','26','-threads','4','-c:a','aac','-movflags','+faststart',str(target)])
    return str(target)

def render(p,destination,progress=lambda _:None,preview=False):
    validate(p);q=legacy(p);core.validate(q)
    target=Path(destination).resolve()
    if target.exists():raise ValueError('Escolha um nome novo para preservar arquivos existentes.')
    exe=core.ffmpeg()
    # Normalize only on export; timeline never combines source files.
    with tempfile.TemporaryDirectory(dir=target.parent,prefix='native_') as tmp:
        work=Path(tmp);paths=[];remain=10 if preview else length(p)
        for i,c in enumerate(p['clips']):
            if remain<=0:break
            count=min(remain,c['out']-c['in']);remain-=count
            progress(f'Exportando take {i+1}/{len(p["clips"])}…')
            part=work/f'clip{i}.mp4'
            speed=float(c.get('speed',1.0));extra=[]
            if abs(speed-1.0)>1e-3:  # câmera lenta (<1) ou acelerar (>1)
                extra=['-filter:v',f'setpts=PTS/{speed}']
                if core.probe(c['source'])['audio']:extra+=['-filter:a',f'atempo={speed}']
            # -ss/-t como opções de ENTRADA (antes do -i): limitam o que é LIDO da
            # fonte. Se -t ficasse na saída, a câmera lenta (mais longa) seria cortada.
            core.run([exe,'-v','error','-nostdin','-ss',str(c['in']),'-t',str(count),'-i',c['source']]+extra+['-map','0:v:0','-map','0:a?','-c:v','libx264','-preset','veryfast','-crf','18','-threads','4','-c:a','aac',str(part)])
            paths.append(str(part))
        assembled=core.assemble(paths,work/'sequence.mp4',progress,canvas=core.target_dims(q.get('aspect','Original'),q.get('quality','Alta (1080p)')))
        # Frame-rate conversion can shift boundaries by a fraction of a frame.
        captions=[];ranges=[];offset=0
        for c,t in zip(p['clips'],assembled['takes']):
            # A velocidade comprime/estica o tempo: uma palavra em `a` (tempo do
            # arquivo) aparece em (a-in)/speed na sequência. Sem dividir por speed
            # a legenda dessincroniza. Para speed=1 isto é idêntico ao de antes.
            s=float(c.get('speed',1.0));rendered=t['end']-t['start'];limit=min(c['out'],c['in']+rendered*s)
            for w in c['words']:
                a,b=max(w['start'],c['in']),min(w['end'],limit)
                if b-a>.005:captions.append(dict(start=offset+(a-c['in'])/s,end=offset+(b-c['in'])/s,text=w['text']))
            ranges.append(dict(start=t['start'],end=t['end'],enabled=True));offset=t['end']
        q.update(source=assembled['source'],duration=assembled['duration'],width=assembled['width'],height=assembled['height'],words=captions,ranges=ranges)
        # Preview can exclude sound effects and clamp sticker at its endpoint.
        if preview:
            q['sfx']=[s for s in q['sfx'] if s['time']<q['duration']]
            if q['sticker']:
                if q['sticker_start']>=q['duration']:q['sticker']=''
                else:q['sticker_end']=min(q['sticker_end'],q['duration'])
        return core.render(q,str(target),progress,False)

def suggest_cuts(p,threshold=0.65):
    if not any(c['words'] for c in p['clips']):raise ValueError('Transcreva os takes com fala antes de sugerir cortes.')
    result=[]
    for c in p['clips']:
        visible=[w for w in c['words'] if w['end']>c['in'] and w['start']<c['out']]
        if not visible:result.append(c);continue
        for r in core.suggest_ranges(visible,c['duration'],threshold=threshold):
            start=max(c['in'],r['start']);end=min(c['out'],r['end'])
            if end-start>.04:
                part=copy.deepcopy(c);part.update(id=uuid.uuid4().hex,**{'in':start,'out':end});result.append(part)
    p['clips']=result

def from_legacy(old,cache,progress=lambda _:None):
    core.validate(old)
    p=project();p.update(client=old['client'],script=old['script'])
    for key in STYLE_KEYS:
        if key in old:p['style'][key]=copy.deepcopy(old[key])
    base=inspect(old['source'],cache,progress);base['words']=copy.deepcopy(old['words'])
    for r in old['ranges']:
        if r['enabled']:
            c=copy.deepcopy(base);c.update(id=uuid.uuid4().hex,**{'in':r['start'],'out':min(r['end'],base['duration'])});p['clips'].append(c)
    validate(p)
    return p
