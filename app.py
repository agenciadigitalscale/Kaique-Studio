from __future__ import annotations
import copy,json,sys,time
from pathlib import Path
from PySide6.QtCore import Qt,QUrl,QTimer,Signal,QRectF
from PySide6.QtGui import QPainter,QColor,QPen,QPixmap,QAction,QKeySequence
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QSplitter,
 QLabel,QPushButton,QListWidget,QListWidgetItem,QAbstractItemView,QTabWidget,QLineEdit,QPlainTextEdit,
 QTableWidget,QTableWidgetItem,QHeaderView,QDoubleSpinBox,QComboBox,QSpinBox,QCheckBox,QScrollArea,
 QSlider,QFileDialog,QMessageBox,QProgressBar)
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
import core,native
from legacy_app import STYLE,STATE,BASE,Job,button,label,row,panel

class ClipList(QListWidget):
    moved=Signal(int,int)
    def __init__(self):
        super().__init__();self.setDragDropMode(QAbstractItemView.InternalMove)
    def dropEvent(self,event):
        old=self.currentRow();target=self.indexAt(event.position().toPoint()).row()
        if target<0:target=self.count()-1
        self.moved.emit(old,target);event.accept()

class Timeline(QWidget):
    selected=Signal(int,float);moved=Signal(int,int);trimmed=Signal(int,float,float)
    def __init__(self):
        super().__init__();self.data=native.project();self.active=-1;self.cursor=0;self.drag=None;self.pixmaps={}
        self.setMinimumHeight(235);self.setMouseTracking(True)
        self.setToolTip('Clique para navegar. Arraste o centro para reordenar; arraste as bordas para aparar. Ctrl+Z desfaz.')
    def geometry_data(self):
        total=max(.01,native.length(self.data));scale=max(100,self.width()-110)/total;offset=0;rects=[]
        for c in self.data['clips']:
            width=(c['out']-c['in'])*scale;rects.append((95+offset*scale,width,offset));offset+=c['out']-c['in']
        return scale,rects
    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor('#12161b'));scale,rects=self.geometry_data()
        for text,y in [('TAKES',60),('VOZ',139),('LEGENDAS',178),('MÚSICA',206),('EFEITOS',231)]:p.setPen(QColor('#9ca9bb'));p.drawText(4,y,text)
        total=native.length(self.data)
        for i in range(11):
            x=95+total*scale*i/10;p.setPen(QColor('#586576'));p.drawText(int(x),15,f'{total*i/10:.1f}s')
        for i,(c,(x,w,offset)) in enumerate(zip(self.data['clips'],rects)):
            p.setPen(QPen(QColor('#c9ff63' if i==self.active else '#526d43'),2));p.setBrush(QColor('#243020'));p.drawRect(QRectF(x,24,w,86))
            p.save();p.setClipRect(QRectF(x+2,26,max(0,w-4),82))
            thumbs=c.get('thumbs',[])
            if thumbs:
                for j in range(max(1,int(w/90)+1)):
                    path=thumbs[min(len(thumbs)-1,int(j*90/max(1,w)*len(thumbs)))]
                    if path not in self.pixmaps:self.pixmaps[path]=QPixmap(path)
                    p.drawPixmap(QRectF(x+j*90,27,90,51),self.pixmaps[path],QRectF(self.pixmaps[path].rect()))
            p.setPen(QColor('white'));p.drawText(int(x)+5,99,Path(c['source']).name);p.restore()
            # source-indexed peaks follow trim and reorder, not virtual source time.
            peaks=c.get('peaks',[])
            if peaks:
                p.setPen(QPen(QColor('#70b7b0'),1))
                for px in range(0,max(1,int(w)),2):
                    t=c['in']+(px/max(1,w))*(c['out']-c['in']);index=min(len(peaks)-1,int(t/c['duration']*len(peaks)))
                    h=peaks[index]*20;p.drawLine(int(x+px),int(139-h),int(x+px),int(139+h))
            for word in c['words']:
                a=max(c['in'],word['start']);b=min(c['out'],word['end'])
                if b>a:p.fillRect(QRectF(x+(a-c['in'])*scale,165,max(1,(b-a)*scale),16),QColor('#9b80d0'))
        if self.data['style']['music']:p.fillRect(QRectF(95,195,total*scale,17),QColor('#315b66'))
        for s in self.data['style']['sfx']:
            x=95+s['time']*scale;p.fillRect(QRectF(x,219,8,15),QColor('#edb05b'))
        p.setPen(QPen(QColor('#c9ff63'),2));x=95+self.cursor*scale;p.drawLine(int(x),20,int(x),self.height())
        if self.drag:
            p.setPen(QColor('#ffffff'));p.drawText(98,self.height()-4,'Solte para aplicar • Ctrl+Z para desfazer')
        p.end()
    def mousePressEvent(self,e):
        scale,rects=self.geometry_data();x=e.position().x()
        for i,(left,width,offset) in enumerate(rects):
            if left<=x<=left+width:
                c=self.data['clips'][i];local=c['in']+(x-left)/scale
                mode='left' if abs(x-left)<9 else 'right' if abs(x-left-width)<9 else 'move'
                self.selected.emit(i,local);self.drag=(i,mode,x,c['in'],c['out']);return
    def mouseMoveEvent(self,e):
        if self.drag:self.setCursor(Qt.SizeHorCursor if self.drag[1]!='move' else Qt.ClosedHandCursor)
    def mouseReleaseEvent(self,e):
        if not self.drag:return
        i,mode,start,a,b=self.drag;self.drag=None;self.unsetCursor();delta=e.position().x()-start
        if abs(delta)<5:return
        scale,rects=self.geometry_data();c=self.data['clips'][i]
        if mode=='left':self.trimmed.emit(i,max(0,min(b-.05,a+delta/scale)),b)
        elif mode=='right':self.trimmed.emit(i,a,min(c['duration'],max(a+.05,b+delta/scale)))
        else:
            target=len(rects)-1
            for j,(x,w,_) in enumerate(rects):
                if e.position().x()<x+w:target=j;break
            self.moved.emit(i,target)
        self.update()

class Studio(QMainWindow):
    def __init__(self):
        super().__init__();self.doc=native.project();self.history=[];self.active=-1;self.job=None;self.path=None;self.loading=False;self.preview_mode=False;self.pending_seek=None
        self.setWindowTitle('Kaique Studio 0.5 • Timeline nativa');self.resize(1480,960)
        self.player=QMediaPlayer(self);self.audio=QAudioOutput(self);self.audio.setVolume(.7);self.player.setAudioOutput(self.audio)
        self.build();self.player.positionChanged.connect(self.position);self.player.mediaStatusChanged.connect(self.media_status)
        self.player.errorOccurred.connect(lambda *_:self.status.setText('Player: '+self.player.errorString()+'. Tente Criar prévia leve.'))
        self.timer=QTimer(self);self.timer.timeout.connect(self.autosave);self.timer.start(30000);self.restore_ui()
    @property
    def p(self):return native.legacy(self.doc)
    @p.setter
    def p(self,value):self.doc['style']={k:copy.deepcopy(value[k]) for k in native.STYLE_KEYS}
    def build(self):
        center=QWidget();self.setCentralWidget(center);main=QVBoxLayout(center)
        main.addWidget(row(label('KAIQUE / STUDIO','brand'),label('0.6 • BIBLIOTECA VIVA'),button('Novo',self.new),button('Abrir',self.load),button('Salvar',self.save),button('Ajuda',self.help),button('Exportar MP4',lambda:self.export(False),True)))
        self.workspace=QWidget();layout=QVBoxLayout(self.workspace);main.addWidget(self.workspace,1)
        split=QSplitter(Qt.Horizontal);layout.addWidget(split,1)
        left,l=panel();l.addWidget(button('+ Importar vários takes',self.import_takes,True));self.clips=ClipList();self.clips.currentRowChanged.connect(self.select);self.clips.moved.connect(self.move);l.addWidget(self.clips,1)
        l.addWidget(row(button('↑',lambda:self.move(self.active,self.active-1)),button('↓',lambda:self.move(self.active,self.active+1)),button('Remover',self.remove)))
        l.addWidget(button('Biblioteca de recursos',self.open_library));l.addWidget(label('Arraste para reordenar. Cortes e palavras acompanham cada take.'));split.addWidget(left)
        middle,m=panel();self.badge=label('PLAYER / TAKE','title');m.addWidget(self.badge);self.video=QVideoWidget();self.video.setMinimumSize(320,220);self.player.setVideoOutput(self.video);m.addWidget(self.video,1)
        self.caption=label('Importe os takes para começar.','title');m.addWidget(self.caption)
        self.seek=QSlider(Qt.Horizontal);self.seek.setRange(0,10000);self.seek.sliderMoved.connect(self.scrub);m.addWidget(self.seek)
        self.clock=label('0.0s');m.addWidget(row(button('▶ / Ⅱ',self.toggle),self.clock,button('Voltar ao take',lambda:self.play_clip(self.active))))
        m.addWidget(row(button('Criar prévia leve',self.make_proxy),button('Prévia com efeitos',lambda:self.export(True))));m.addWidget(label('Player de takes segue a sequência; efeitos aparecem na prévia renderizada.'));split.addWidget(middle)
        right,r=panel();tabs=QTabWidget();r.addWidget(tabs);split.addWidget(right);split.setSizes([260,730,370])
        command=QWidget();cm=QVBoxLayout(command);self.prompt=QPlainTextEdit();self.prompt.setPlaceholderText('cortes e legenda; filtro quente');cm.addWidget(self.prompt);cm.addWidget(button('Aplicar comandos',self.commands));cm.addWidget(label('Comandos predefinidos. Transcreva antes de solicitar cortes. Takes sem palavras são preservados; revise imagens de apoio.'));tabs.addTab(command,'Comandos')
        edit=QWidget();e=QVBoxLayout(edit);e.addWidget(label('Clipe selecionado','title'));self.ins=QDoubleSpinBox();self.outs=QDoubleSpinBox()
        for w in [self.ins,self.outs]:w.setDecimals(3);w.setRange(0,100000);w.setSuffix(' s')
        e.addWidget(label('Entrada no arquivo original'));e.addWidget(self.ins);e.addWidget(label('Saída no arquivo original'));e.addWidget(self.outs)
        e.addWidget(button('Aplicar corte',self.trim_fields));e.addWidget(button('Dividir no cursor',self.split_clip));e.addWidget(button('Restaurar take inteiro',self.reset_clip));e.addWidget(button('Desfazer • Ctrl+Z',self.undo));e.addStretch();tabs.addTab(edit,'Cortes')
        caption=QWidget();c=QVBoxLayout(caption);c.addWidget(button('Transcrever take',self.transcribe));c.addWidget(button('Transcrever todos os pendentes',lambda:self.transcribe(True),True))
        self.words=QTableWidget(0,3);self.words.setHorizontalHeaderLabels(['Início','Fim','Palavra']);self.words.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);c.addWidget(self.words)
        c.addWidget(button('Salvar palavras',self.sync_message));self.mode=QComboBox();self.mode.addItems(['Palavra ativa','Palavras-chave','Frase']);c.addWidget(self.mode)
        self.caption_style=QComboBox();self.caption_style.addItems(core.CAPTION_STYLES);c.addWidget(label('Animação da legenda (no modo Palavra ativa)'));c.addWidget(self.caption_style)
        self.keywords=QLineEdit();self.keywords.setPlaceholderText('Palavras-chave separadas por vírgula');c.addWidget(self.keywords)
        self.font=QSpinBox();self.font.setRange(10,50);c.addWidget(label('Tamanho da legenda'));c.addWidget(self.font)
        self.enabled=QCheckBox('Legendas na exportação');c.addWidget(self.enabled);tabs.addTab(caption,'Legendas')
        image=QWidget();im=QVBoxLayout(image);self.look=QComboBox();self.look.addItems(core.FILTERS);im.addWidget(label('Filtro'));im.addWidget(self.look)
        self.transition=QComboBox();self.transition.addItems(['Nenhuma','Preto','Branco']);im.addWidget(label('Transição entre clipes'));im.addWidget(self.transition)
        self.volume=QSlider(Qt.Horizontal);self.volume.setRange(0,100);im.addWidget(label('Volume da música'));im.addWidget(self.volume)
        im.addWidget(button('Remover música',lambda:self.clear_asset('music')));im.addWidget(button('Remover LUT',lambda:self.clear_asset('lut')));im.addWidget(button('Remover efeitos sonoros',lambda:self.clear_asset('sfx')));im.addWidget(button('Remover imagens/ícones',lambda:self.clear_asset('overlays')))
        self.effects=label('');im.addWidget(self.effects);im.addStretch();tabs.addTab(image,'Imagem/áudio')
        script=QWidget();sc=QVBoxLayout(script);self.client=QLineEdit();self.client.setPlaceholderText('Cliente / projeto');sc.addWidget(self.client);self.script=QPlainTextEdit();self.script.setPlaceholderText('Roteiro de referência');sc.addWidget(self.script);tabs.addTab(script,'Projeto')
        layout.addWidget(label('TIMELINE • arraste o centro para reordenar / bordas para aparar','title'))
        zoom=QSlider(Qt.Horizontal);zoom.setRange(1,8);zoom.setValue(1);zoom.valueChanged.connect(self.zoom_timeline);layout.addWidget(row(label('Zoom da timeline'),zoom))
        self.timeline=Timeline();self.timeline.selected.connect(self.seek_clip);self.timeline.moved.connect(self.move);self.timeline.trimmed.connect(self.trim)
        self.scroll=QScrollArea();self.scroll.setWidgetResizable(True);self.scroll.setWidget(self.timeline);self.scroll.setMinimumHeight(265);self.scroll.setMaximumHeight(295);layout.addWidget(self.scroll)
        self.status=label('Pronto');self.progress=QProgressBar();self.progress.setRange(0,1);main.addWidget(row(self.status,self.progress))
        for key,fn in [('Ctrl+S',self.save),('Ctrl+Z',self.undo),('Ctrl+B',self.split_clip)]:
            action=QAction(self);action.setShortcut(QKeySequence(key));action.triggered.connect(fn);self.addAction(action)
    def zoom_timeline(self,value):self.timeline.setMinimumWidth(max(900,self.scroll.viewport().width())*value)
    def error(self,message):QMessageBox.warning(self,'Confira',str(message))
    def info(self,message):QMessageBox.information(self,'Kaique Studio',message)
    def checkpoint(self):self.history.append(copy.deepcopy(self.doc));self.history=self.history[-30:]
    def sync(self):
        if self.loading:return
        candidate=copy.deepcopy(self.doc)
        candidate.update(client=self.client.text(),script=self.script.toPlainText())
        candidate['style'].update(caption_mode=self.mode.currentText(),caption_style=self.caption_style.currentText(),keywords=self.keywords.text(),font_size=self.font.value(),captions_enabled=self.enabled.isChecked(),filter=self.look.currentText(),transition=self.transition.currentText(),music_volume=self.volume.value()/100)
        if 0<=self.active<len(candidate['clips']):
            words=[]
            for i in range(self.words.rowCount()):words.append(dict(start=float(self.words.item(i,0).text().replace(',','.')),end=float(self.words.item(i,1).text().replace(',','.')),text=self.words.item(i,2).text()))
            candidate['clips'][self.active]['words']=words
        if candidate['clips']:native.validate(candidate)
        if candidate!=self.doc:self.checkpoint();self.doc=candidate
    def sync_message(self):
        try:self.sync();self.restore_ui();self.status.setText('Palavras e ajustes salvos no projeto em memória. Ctrl+S para gravar o arquivo.')
        except Exception as exc:self.error(exc)
    def restore_ui(self):
        self.loading=True;self.clips.blockSignals(True);self.clips.clear()
        for c in self.doc['clips']:
            item=QListWidgetItem(f"{Path(c['source']).name}\n{c['out']-c['in']:.1f}s • {len(c['words'])} palavras")
            if c.get('thumbs'):
                from PySide6.QtGui import QIcon
                item.setIcon(QIcon(c['thumbs'][0]))
            self.clips.addItem(item)
        self.active=min(self.active,len(self.doc['clips'])-1)
        if self.active<0 and self.doc['clips']:self.active=0
        self.clips.setCurrentRow(self.active);self.clips.blockSignals(False)
        s=self.doc['style'];self.mode.setCurrentText(s['caption_mode']);self.caption_style.setCurrentText(s.get('caption_style','Realce'));self.keywords.setText(s['keywords']);self.font.setValue(s['font_size']);self.enabled.setChecked(s['captions_enabled']);self.look.setCurrentText(s['filter']);self.transition.setCurrentText(s['transition']);self.volume.setValue(round(s['music_volume']*100));self.client.setText(self.doc['client']);self.script.setPlainText(self.doc['script'])
        self.effects.setText(f"Música: {Path(s['music']).name if s['music'] else 'nenhuma'}\nEfeitos sonoros: {len(s['sfx'])}\nLUT: {Path(s['lut']).name if s['lut'] else 'nenhuma'}")
        self.words.setRowCount(0)
        if self.active>=0:
            c=self.doc['clips'][self.active];self.ins.setValue(c['in']);self.outs.setValue(c['out']);self.words.setRowCount(len(c['words']))
            for i,w in enumerate(c['words']):
                for j,value in enumerate([f"{w['start']:.3f}",f"{w['end']:.3f}",w['text']]):self.words.setItem(i,j,QTableWidgetItem(value))
        self.timeline.data=self.doc;self.timeline.active=self.active;self.timeline.update();self.loading=False
    def mutate(self,fn):
        if self.job:return
        try:self.sync();candidate=copy.deepcopy(self.doc);fn(candidate);native.validate(candidate);self.checkpoint();self.doc=candidate;self.restore_ui();self.play_clip(self.active)
        except Exception as exc:self.error(exc)
    def select(self,index):
        if self.loading or index<0:return
        try:self.sync()
        except Exception as exc:
            self.error(exc);self.restore_ui();return
        self.active=index;self.restore_ui();self.play_clip(index)
    def play_clip(self,index,source_time=None):
        if not 0<=index<len(self.doc['clips']):return
        c=self.doc['clips'][index];self.caption.setText('');self.preview_mode=False;self.pending_seek=round((c['in'] if source_time is None else source_time)*1000)
        source=c.get('proxy') if c.get('proxy') and Path(c['proxy']).exists() else c['source']
        url=QUrl.fromLocalFile(source);self.badge.setText(('PLAYER / PRÉVIA LEVE • ' if source!=c['source'] else 'PLAYER / TAKE • ')+Path(c['source']).name)
        if self.player.source()==url:self.player.setPosition(self.pending_seek);self.pending_seek=None
        else:self.player.setSource(url)
    def media_status(self,status):
        if status in [QMediaPlayer.LoadedMedia,QMediaPlayer.BufferedMedia] and self.pending_seek is not None:
            value=self.pending_seek;self.pending_seek=None;self.player.setPosition(value)
        if status==QMediaPlayer.EndOfMedia and not self.preview_mode:self.next_clip()
    def next_clip(self):
        if self.active+1<len(self.doc['clips']):self.select(self.active+1);self.player.play()
        else:self.player.pause();self.status.setText('Fim da sequência. ▶ recomeça a partir do clipe selecionado.')
    def position(self,pos):
        if self.preview_mode:self.clock.setText(f'Prévia {pos/1000:.1f}s');return
        if not 0<=self.active<len(self.doc['clips']):return
        c=self.doc['clips'][self.active];local=pos/1000;offset=sum(x['out']-x['in'] for x in self.doc['clips'][:self.active]);self.timeline.cursor=offset+max(0,min(local-c['in'],c['out']-c['in']));self.timeline.update()
        self.clock.setText(f'{self.timeline.cursor:.1f}s / {native.length(self.doc):.1f}s');self.seek.setValue(round(max(0,min(1,(local-c['in'])/(c['out']-c['in'])))*10000));self.caption.setText(next((w['text'] for w in c['words'] if w['start']<=local<w['end']),''))
        if local>=c['out']-.02 and self.player.playbackState()==QMediaPlayer.PlayingState:QTimer.singleShot(0,self.advance_if_needed)
    def advance_if_needed(self):
        if self.preview_mode or self.active<0:return
        if self.player.position()/1000>=self.doc['clips'][self.active]['out']-.02:self.next_clip()
    def toggle(self):
        if self.player.playbackState()==QMediaPlayer.PlayingState:self.player.pause();return
        if not self.preview_mode and self.active>=0:
            c=self.doc['clips'][self.active]
            if self.player.position()/1000>=c['out']-.02:self.player.setPosition(round(c['in']*1000))
        self.player.play()
    def scrub(self,value):
        if self.preview_mode:return
        if self.active>=0:
            c=self.doc['clips'][self.active];self.player.setPosition(round((c['in']+(c['out']-c['in'])*value/10000)*1000))
    def seek_clip(self,index,t):self.select(index);self.play_clip(index,t)
    def move(self,index,target):
        if not 0<=index<len(self.doc['clips']) or not 0<=target<len(self.doc['clips']):return
        self.mutate(lambda p:native.reorder(p,index,target));self.active=target;self.restore_ui();self.play_clip(target)
    def trim(self,index,a,b):self.mutate(lambda p:native.trim(p,index,a,b))
    def trim_fields(self):
        if self.active>=0:self.trim(self.active,self.ins.value(),self.outs.value())
    def split_clip(self):
        if self.active<0 or self.preview_mode:return
        t=self.player.position()/1000;self.mutate(lambda p:native.split(p,self.active,t))
    def reset_clip(self):
        if self.active>=0:self.trim(self.active,0,self.doc['clips'][self.active]['duration'])
    def remove(self):
        if self.active<0:return
        if len(self.doc['clips'])==1:return self.info('Use Novo para iniciar um projeto vazio.')
        self.mutate(lambda p:p['clips'].pop(self.active))
    def undo(self):
        if self.job or not self.history:return
        self.doc=self.history.pop();self.restore_ui()
        if self.active>=0:self.play_clip(self.active)
        else:self.player.stop();self.player.setSource(QUrl())
    def task(self,fn,done):
        if self.job:return
        self.failed=False;self.player.pause();self.workspace.setEnabled(False);self.progress.setRange(0,0)
        self.job=Job(fn);self.job.progress.connect(self.status.setText)
        def result(value):
            try:done(value)
            except Exception as exc:self.task_failed(str(exc))
        self.job.result.connect(result);self.job.failed.connect(self.task_failed);self.job.finished.connect(self.task_finished);self.job.start()
    def task_failed(self,text):self.failed=True;self.error(text)
    def task_finished(self):
        self.workspace.setEnabled(True);self.progress.setRange(0,1);self.progress.setValue(0 if self.failed else 1);self.status.setText('Tarefa falhou; confira o aviso.' if self.failed else 'Concluído. Revise o resultado.');self.job.deleteLater();self.job=None
    def import_takes(self):
        if self.job:return
        paths,_=QFileDialog.getOpenFileNames(self,'Selecionar takes','','Vídeos (*.mp4 *.mov *.mkv *.avi *.webm)')
        if not paths:return
        try:self.sync()
        except Exception as exc:return self.error(exc)
        cache=STATE/'timeline';cache.mkdir(exist_ok=True)
        def work(progress):
            clips=[]
            for i,path in enumerate(paths):progress(f'Miniaturas {i+1}/{len(paths)}: {Path(path).name}');clips.append(native.inspect(path,cache,progress))
            return clips
        def done(clips):self.checkpoint();self.doc['clips'].extend(clips);self.restore_ui();self.play_clip(self.active)
        self.task(work,done)
    def transcribe(self,all_pending=False):
        if self.job or self.active<0:return
        try:self.sync()
        except Exception as exc:return self.error(exc)
        ids=[i for i,c in enumerate(self.doc['clips']) if not c['words']] if all_pending else [self.active]
        if not ids:return self.info('Todos os takes já têm palavras.')
        if not all_pending and self.doc['clips'][self.active]['words'] and QMessageBox.question(self,'Transcrever','Substituir as palavras deste take?')!=QMessageBox.Yes:return
        snapshot=copy.deepcopy(self.doc)
        def work(progress):
            cache={};result={}
            for i in ids:
                source=snapshot['clips'][i]['source']
                if source not in cache:cache[source]=core.transcribe(source,progress)
                result[i]=cache[source]
            return result
        def done(result):
            self.checkpoint()
            for i,words in result.items():self.doc['clips'][i]['words']=copy.deepcopy(words)
            self.restore_ui()
        self.task(work,done)
    def make_proxy(self):
        if self.job or self.active<0:return
        index=self.active;c=copy.deepcopy(self.doc['clips'][index]);cache=STATE/'timeline';cache.mkdir(exist_ok=True)
        def done(path):self.doc['clips'][index]['proxy']=path;self.play_clip(index)
        self.task(lambda progress:native.proxy(c,cache,progress),done)
    def open_library(self):
        if self.job:return
        try:
            self.sync()
            from resource_library import LibraryDialog
            LibraryDialog(self,STATE,BASE).exec()
        except Exception as exc:self.error(exc)
    def commands(self):
        actions,unknown=core.commands(self.prompt.toPlainText())
        if unknown:return self.info('Pedidos não reconhecidos: '+', '.join(unknown))
        if not actions:return
        if any(k=='cuts' for k,_,_ in actions):
            if QMessageBox.question(self,'Revisar cortes','Sugerir cortes nos takes transcritos? Takes sem palavras serão mantidos. Revise o resultado antes de exportar.')!=QMessageBox.Yes:return
        def apply(p):
            for key,value,_ in actions:
                if key=='cuts':native.suggest_cuts(p)
                else:p['style'][key]=value
        self.mutate(apply)
    def clear_asset(self,key):
        try:self.sync();self.checkpoint();self.doc['style'][key]=[] if key in ('sfx','overlays') else '';self.restore_ui()
        except Exception as exc:self.error(exc)
    def save(self):
        if self.job:return False
        try:self.sync()
        except Exception as exc:self.error(exc);return False
        path,_=QFileDialog.getSaveFileName(self,'Salvar projeto',self.path or 'projeto.kaique5.json','Projeto (*.json)')
        if not path:return False
        try:core.atomic_json(path,self.doc);self.path=path;return True
        except Exception as exc:self.error(exc);return False
    def discard_ok(self):
        if not self.doc['clips']:return True
        answer=QMessageBox.question(self,'Projeto atual','Salvar o projeto antes de continuar?',QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel)
        return self.save() if answer==QMessageBox.Save else answer==QMessageBox.Discard
    def new(self):
        if self.job or not self.discard_ok():return
        self.doc=native.project();self.history=[];self.path=None;self.active=-1;self.player.stop();self.player.setSource(QUrl());self.restore_ui()
    def load(self):
        if self.job:return
        path,_=QFileDialog.getOpenFileName(self,'Abrir projeto nativo 0.5','','Projeto (*.json)')
        if not path:return
        try:
            data=json.loads(Path(path).read_text(encoding='utf-8'))
            if data.get('version')==core.VERSION:
                core.validate(data)
                if not self.discard_ok():return
                cache=STATE/'timeline';cache.mkdir(exist_ok=True)
                def converted(p):
                    self.doc=p;self.path=None;self.history=[];self.active=0;self.restore_ui();self.play_clip(0);self.status.setText('Projeto antigo importado. Salve como um novo projeto 0.5.')
                self.task(lambda progress:native.from_legacy(data,cache,progress),converted);return
            native.validate(data)
            if not self.discard_ok():return
            self.doc=data;self.path=path;self.history=[];self.active=0;self.restore_ui();self.play_clip(0)
        except Exception as exc:self.error(exc)
    def autosave(self):
        if self.job or not self.doc['clips']:return
        try:self.sync();core.atomic_json(STATE/'recuperacao-v05.json',self.doc)
        except Exception:self.status.setText('Recuperação automática pendente: revise os campos de palavras.')
    def export(self,preview):
        if self.job:return
        try:self.sync();native.validate(self.doc)
        except Exception as exc:return self.error(exc)
        if preview:path=str(STATE/f'previa-v05-{time.time_ns()}.mp4')
        else:
            path,_=QFileDialog.getSaveFileName(self,'Exportar MP4','video-final.mp4','Vídeo (*.mp4)')
            if not path:return
        snapshot=copy.deepcopy(self.doc)
        def done(path):
            if preview:self.preview_mode=True;self.pending_seek=None;self.player.setSource(QUrl.fromLocalFile(path));self.badge.setText('PRÉVIA COM EFEITOS / até 10s');self.player.play()
            else:self.info('Exportado: '+path)
        self.task(lambda progress:native.render(snapshot,path,progress,preview),done)
    def help(self):self.info('Importe takes → organize arrastando → ajuste as bordas → transcreva → revise → exporte.\n\nCtrl+B divide, Ctrl+Z desfaz, Ctrl+S salva.\nAs palavras usam o tempo original de cada take.\nMúsica e efeitos usam o tempo final da sequência: revise após mudar os cortes.\n\nCriar prévia leve gera uma cópia de até 640 px do take selecionado. A exportação usa os originais.\n\nAbrir também importa projetos 0.2–0.4 usando a sequência antiga. Salve como um novo projeto 0.5.\nRecuperação: '+str(STATE/'recuperacao-v05.json'))
    def closeEvent(self,event):
        if self.job:self.info('Aguarde a tarefa terminar.');event.ignore();return
        if not self.discard_ok():event.ignore();return
        self.player.stop();event.accept()

if __name__=='__main__':
    app=QApplication(sys.argv);app.setStyle('Fusion');app.setStyleSheet(STYLE);w=Studio();w.show();sys.exit(app.exec())
