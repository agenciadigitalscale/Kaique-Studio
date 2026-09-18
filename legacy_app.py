from __future__ import annotations
import copy, json, os, sys, traceback
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QThread, Signal, QRectF, QTimer
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QDesktopServices, QAction, QKeySequence
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,
    QPushButton,QFrame,QSplitter,QTabWidget,QListWidget,QPlainTextEdit,QLineEdit,QComboBox,
    QSpinBox,QDoubleSpinBox,QCheckBox,QTableWidget,QTableWidgetItem,QHeaderView,QFileDialog,
    QMessageBox,QSlider,QColorDialog,QInputDialog,QProgressBar,QScrollArea)
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
import core

BASE=Path(__file__).resolve().parent
STATE=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'KaiqueStudio'
STATE.mkdir(parents=True,exist_ok=True)
STYLE='''
QWidget {background:#0e0b16;color:#ece9f5;font-family:"Segoe UI";font-size:12px;}
QMainWindow {background:#0e0b16;}
QFrame#panel {background:#181322;border:1px solid #2a2340;border-radius:14px;}
QLabel {background:transparent;}
QLabel#muted {color:#9a90b5;font-size:11px;}
QLabel#brand {font-size:21px;font-weight:800;letter-spacing:2px;color:#c084fc;}
QLabel#title {font-size:14px;font-weight:700;color:#e6def7;}
QPushButton {background:#221a33;border:1px solid #362b4f;border-radius:9px;padding:9px 13px;color:#ece9f5;}
QPushButton:hover {background:#2c2242;border-color:#5b4a82;}
QPushButton:pressed {background:#1a1428;}
QPushButton:disabled {color:#6b6285;background:#171122;border-color:#2a2138;}
QPushButton#primary {background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #8b5cf6,stop:1 #ec4899);color:#ffffff;font-weight:700;border:0;padding:10px 14px;border-radius:9px;}
QPushButton#primary:hover {background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #9d72f7,stop:1 #f45aa6);}
QPushButton#primary:pressed {background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7c4fe0,stop:1 #d83f8a);}
QLineEdit,QPlainTextEdit,QSpinBox,QDoubleSpinBox,QComboBox {background:#140f1f;border:1px solid #302743;border-radius:9px;padding:8px;selection-background-color:#5b3a82;color:#ece9f5;}
QLineEdit:focus,QPlainTextEdit:focus,QSpinBox:focus,QDoubleSpinBox:focus,QComboBox:focus {border:1px solid #a78bfa;}
QComboBox::drop-down {border:0;width:22px;}
QComboBox QAbstractItemView {background:#181322;border:1px solid #302743;selection-background-color:#33244d;color:#ece9f5;outline:0;}
QTabWidget::pane {border:0;}
QTabBar::tab {background:transparent;color:#9a90b5;padding:8px 9px;font-size:11px;font-weight:600;border-bottom:2px solid transparent;margin-right:2px;}
QTabBar::tab:hover {color:#e6def7;}
QTabBar::tab:selected {color:#c084fc;border-bottom:2px solid #c084fc;}
QTableWidget,QListWidget {background:#140f1f;border:1px solid #2a2340;border-radius:11px;outline:0;}
QListWidget::item {padding:8px;border-radius:9px;margin:2px;}
QListWidget::item:hover {background:#221a33;}
QListWidget::item:selected {background:#3a2560;color:#f0e7ff;}
QTableWidget::item {padding:6px;}
QTableWidget::item:selected {background:#33244d;color:#f0e7ff;}
QHeaderView::section {background:#1c1530;color:#9a90b5;border:0;padding:7px;}
QSlider::groove:horizontal {height:5px;background:#302743;border-radius:3px;}
QSlider::sub-page:horizontal {background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #8b5cf6,stop:1 #ec4899);border-radius:3px;}
QSlider::handle:horizontal {background:#f0e7ff;width:14px;height:14px;margin:-5px 0;border-radius:7px;border:2px solid #c084fc;}
QProgressBar {background:#241b33;border:0;border-radius:3px;text-align:center;height:6px;}
QProgressBar::chunk {background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #8b5cf6,stop:1 #ec4899);border-radius:3px;}
QCheckBox {spacing:8px;}
QCheckBox::indicator,QRadioButton::indicator {width:16px;height:16px;border:1px solid #4a3a63;background:#140f1f;}
QCheckBox::indicator {border-radius:5px;}
QRadioButton::indicator {border-radius:8px;}
QCheckBox::indicator:hover,QRadioButton::indicator:hover {border-color:#a78bfa;}
QCheckBox::indicator:checked {border:0;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #8b5cf6,stop:1 #ec4899);}
QRadioButton::indicator:checked {border:0;background:#c084fc;}
QMenu {background:#181322;border:1px solid #302743;border-radius:10px;padding:6px;}
QMenu::item {padding:7px 22px 7px 14px;border-radius:7px;color:#ece9f5;}
QMenu::item:selected {background:#33244d;color:#f0e7ff;}
QMenu::separator {height:1px;background:#2a2340;margin:5px 8px;}
QMenu::icon {padding-left:6px;}
QSplitter::handle {background:#241b33;}
QSplitter::handle:hover {background:#c084fc;}
QSplitter::handle:horizontal {width:6px;}
QSplitter::handle:vertical {height:6px;}
QScrollArea {border:0;}
QScrollBar:vertical {background:transparent;width:10px;margin:2px;}
QScrollBar::handle:vertical {background:#3d3357;border-radius:5px;min-height:30px;}
QScrollBar::handle:vertical:hover {background:#5b4a82;}
QScrollBar:horizontal {background:transparent;height:10px;margin:2px;}
QScrollBar::handle:horizontal {background:#3d3357;border-radius:5px;min-width:30px;}
QScrollBar::handle:horizontal:hover {background:#5b4a82;}
QScrollBar::add-line,QScrollBar::sub-line {height:0;width:0;}
QScrollBar::add-page,QScrollBar::sub-page {background:transparent;}
QToolTip {background:#1c1530;color:#ece9f5;border:1px solid #3d3357;border-radius:6px;padding:6px;}
'''

def button(text,fn,primary=False):
    b=QPushButton(text);b.setMinimumHeight(32);b.clicked.connect(fn)
    if primary:b.setObjectName('primary')
    return b

def label(text,kind='muted'):
    w=QLabel(text);w.setObjectName(kind);w.setWordWrap(True);return w

def panel():
    w=QFrame();w.setObjectName('panel');v=QVBoxLayout(w);v.setContentsMargins(14,14,14,14);v.setSpacing(10);return w,v

def row(*items):
    w=QWidget();h=QHBoxLayout(w);h.setContentsMargins(0,0,0,0);h.setSpacing(8)
    for item in items:h.addWidget(item)
    return w

class Job(QThread):
    progress=Signal(str)
    result=Signal(object)
    failed=Signal(str)
    def __init__(self,fn):super().__init__();self.fn=fn
    def run(self):
        try:self.result.emit(self.fn(self.progress.emit))
        except Exception as exc:
            (STATE/'last-error.log').write_text(traceback.format_exc(),encoding='utf-8')
            self.failed.emit(str(exc))

class Timeline(QWidget):
    seek=Signal(float)
    def __init__(self):
        super().__init__();self.data=core.project();self.position=0;self.setMinimumHeight(150)
        self.setToolTip('Clique para navegar no vídeo original. Os blocos mostram os trechos que serão mantidos.')
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(),QColor('#13171d'))
        start=92;width=max(20,self.width()-start-16);total=max(1,self.data['duration'])
        p.setFont(QFont('Segoe UI',9))
        for i in range(9):
            x=start+width*i/8
            p.setPen(QColor('#29303c'));p.drawLine(int(x),18,int(x),self.height()-8)
            p.setPen(QColor('#788595'));p.drawText(int(x)+3,15,f'{total*i/8:.1f}s')
        for name,y in [('VÍDEO',40),('LEGENDAS',86),('ÁUDIO',123)]:
            p.setPen(QColor('#9ba7b6'));p.drawText(8,y+8,name)
        for i,r in enumerate(self.data['ranges']):
            x=start+width*r['start']/total;w=width*(r['end']-r['start'])/total
            p.setPen(Qt.NoPen);p.setBrush(QColor('#667f44' if r['enabled'] else '#363c47'))
            p.drawRoundedRect(QRectF(x,28,max(2,w),33),4,4)
            p.setPen(QColor('#ebf4e3'));p.drawText(QRectF(x+5,30,max(0,w-8),26),Qt.AlignVCenter,f'Trecho {i+1}')
        for i,take in enumerate(self.data.get('takes',[])):
            x=start+width*take['start']/total
            p.setPen(QPen(QColor('#a9c985'),1,Qt.DashLine));p.drawLine(int(x),24,int(x),68)
            p.drawText(int(x)+3,73,f'T{i+1}')
        for word in self.data['words']:
            x=start+width*word['start']/total;w=width*(word['end']-word['start'])/total
            p.fillRect(QRectF(x,76,max(1,w),21),QColor('#65548c'))
        if self.data['music']:
            p.setPen(QColor('#80d1c4'));p.drawText(start+4,131,'♪ Música importada • mixagem na prévia renderizada')
        else:
            p.setPen(QColor('#65717e'));p.drawText(start+4,131,'Áudio original do vídeo')
        x=start+width*self.position/total
        p.setPen(QPen(QColor('#ec4899'),2));p.drawLine(int(x),19,int(x),self.height()-6)
        p.end()
    def mousePressEvent(self,event):
        t=(event.position().x()-92)/max(20,self.width()-108)*self.data['duration']
        self.seek.emit(max(0,min(self.data['duration'],t)))

class Studio(QMainWindow):
    def __init__(self):
        super().__init__();self.p=core.project();self.history=[];self.job=None;self.project_path=None;self.preview_mode=False
        self.setWindowTitle('Kaique Studio • 0.4 / Alpha');self.resize(1480,930);self.setMinimumSize(1100,740)
        self.player=QMediaPlayer(self);self.audio=QAudioOutput(self);self.player.setAudioOutput(self.audio);self.audio.setVolume(.7)
        self.build();self.player.positionChanged.connect(self.position_changed)
        self.player.mediaStatusChanged.connect(self.media_status)
        self.player.durationChanged.connect(lambda d:self.seekbar.setMaximum(d))
        self.player.errorOccurred.connect(lambda *_:self.status.setText('Player: '+self.player.errorString()+' — tente a prévia renderizada.'))
        self.restore_ui()
        self.timer=QTimer(self);self.timer.timeout.connect(self.autosave);self.timer.start(30000)
    def build(self):
        center=QWidget();main=QVBoxLayout(center);main.setContentsMargins(18,14,18,10);main.setSpacing(12);self.setCentralWidget(center)
        top=QHBoxLayout();brand=label('KAIQUE / STUDIO','brand');top.addWidget(brand);top.addWidget(label('0.4 ALPHA • EDIÇÃO LOCAL'));top.addStretch()
        top.addWidget(button('Abrir projeto',self.load));top.addWidget(button('Salvar',self.save));top.addWidget(button('Ajuda',self.help));self.export_button=button('Exportar MP4  ↗',lambda:self.export(False),True);top.addWidget(self.export_button);main.addLayout(top)
        self.workspace=QSplitter(Qt.Horizontal);main.addWidget(self.workspace,1)
        left,left_layout=panel();left.setMinimumWidth(240);left_layout.addWidget(label('Seu projeto','title'))
        self.client=QLineEdit();self.client.setPlaceholderText('Cliente / nome do projeto');left_layout.addWidget(self.client)
        left_layout.addWidget(button('+ Importar takes (vários)',self.import_video,True));self.media_list=QListWidget();self.media_list.setMaximumHeight(130);left_layout.addWidget(self.media_list)
        self.media_list.itemDoubleClicked.connect(self.jump_take)
        left_layout.addWidget(row(button('↑',lambda:self.move_take(-1)),button('↓',lambda:self.move_take(1)),button('Remover',self.remove_take)))
        left_layout.addWidget(label('Ctrl ou Shift para selecionar vários arquivos. Duplo clique no take para assistir. ↑ ↓ alteram a sequência.'))
        self.left_tabs=QTabWidget();left_layout.addWidget(self.left_tabs,1)
        assets=QWidget();a=QVBoxLayout(assets);a.setContentsMargins(0,12,0,0)
        a.addWidget(button('Abrir biblioteca de recursos',self.open_library,True))
        a.addWidget(label('Recursos aplicados ao projeto','title'))
        a.addWidget(button('♪ Importar música',self.import_music));self.music_label=label('Nenhuma música');a.addWidget(self.music_label)
        self.volume=QSlider(Qt.Horizontal);self.volume.setRange(0,100);self.volume.setValue(15);a.addWidget(label('Volume da música'));a.addWidget(self.volume)
        a.addWidget(button('Remover música',lambda:self.set_asset('music','')))
        a.addWidget(button('+ Efeito sonoro',self.add_sfx));self.sfx_list=QListWidget();self.sfx_list.setMaximumHeight(90);a.addWidget(self.sfx_list)
        a.addWidget(button('Remover efeito selecionado',self.remove_sfx))
        a.addWidget(button('+ Sticker PNG',self.import_sticker));self.sticker_label=label('Sem sticker');a.addWidget(self.sticker_label)
        a.addWidget(button('Remover sticker',lambda:self.set_asset('sticker','')))
        a.addWidget(label('Músicas, efeitos e stickers são arquivos locais. Ainda não há catálogo online.'));a.addStretch()
        asset_scroll=QScrollArea();asset_scroll.setWidgetResizable(True);asset_scroll.setWidget(assets)
        self.left_tabs.addTab(asset_scroll,'Biblioteca')
        script=QWidget();s=QVBoxLayout(script);s.setContentsMargins(0,12,0,0);s.addWidget(label('Roteiro de referência','title'))
        s.addWidget(button('Importar TXT',self.import_script));self.script=QPlainTextEdit();self.script.setPlaceholderText('Cole o roteiro aqui.\n\nNesta versão ele fica disponível para consulta; a seleção automática de takes por roteiro ainda não está conectada.');s.addWidget(self.script)
        self.left_tabs.addTab(script,'Roteiro');self.workspace.addWidget(left)
        mid,m=panel();mid.setMinimumWidth(390)
        self.player_badge=label('PLAYER / ORIGINAL','title');m.addWidget(row(self.player_badge,button('Voltar ao original',self.original)))
        self.video_widget=QVideoWidget();self.video_widget.setMinimumHeight(200);self.player.setVideoOutput(self.video_widget);m.addWidget(self.video_widget,1)
        self.live_caption=label('Importe um vídeo para começar.','title');self.live_caption.setAlignment(Qt.AlignCenter);self.live_caption.setMinimumHeight(45);m.addWidget(self.live_caption)
        self.seekbar=QSlider(Qt.Horizontal);self.seekbar.sliderMoved.connect(self.player.setPosition);m.addWidget(self.seekbar)
        self.clock=label('00:00 / 00:00');m.addWidget(row(button('▶ / Ⅱ',self.toggle),self.clock,button('Ver prévia com efeitos',lambda:self.export(True))))
        m.addWidget(label('O player original mostra os takes. A prévia renderizada aplica cortes, legendas, filtros, áudio e sticker.'))
        self.workspace.addWidget(mid)
        right,r=panel();right.setMinimumWidth(320)
        self.right_tabs=QTabWidget();r.addWidget(self.right_tabs);self.workspace.addWidget(right)
        self.workspace.setSizes([270,650,380])
        command=QWidget();c=QVBoxLayout(command);c.setContentsMargins(0,12,0,0)
        c.addWidget(label('Descreva. Revise. Aplique.','title'));c.addWidget(label('Comandos locais • vocabulário limitado nesta alpha'))
        self.prompt=QPlainTextEdit();self.prompt.setPlaceholderText('cortes e legenda; \nfiltro quente;\nvolume música 15%;\ncortar pausas');self.prompt.setMaximumHeight(145);c.addWidget(self.prompt)
        c.addWidget(button('Cortes + legenda',self.quick_edit,True))
        c.addWidget(button('Interpretar comando',self.interpret));self.plan_text=QPlainTextEdit();self.plan_text.setReadOnly(True);self.plan_text.setPlaceholderText('O plano de edição aparece aqui antes de alterar o projeto.');c.addWidget(self.plan_text)
        c.addWidget(button('Aplicar plano',self.apply_commands));c.addWidget(button('Desfazer última alteração',self.undo))
        c.addWidget(label('IA generativa por prompt livre ainda não conectada. Pedidos não reconhecidos serão informados.'));self.right_tabs.addTab(command,'Comandos')
        caption=QWidget();cp=QVBoxLayout(caption);cp.setContentsMargins(0,12,0,0)
        cp.addWidget(button('Transcrever em português',self.transcribe,True));self.caption_enabled=QCheckBox('Legendas na exportação');self.caption_enabled.setChecked(True);cp.addWidget(self.caption_enabled)
        self.mode=QComboBox();self.mode.addItems(['Palavra ativa','Palavras-chave','Frase']);cp.addWidget(label('Estilo de legenda'));cp.addWidget(self.mode)
        self.color_button=button('Cor do destaque',self.pick_color);self.font_size=QSpinBox();self.font_size.setRange(10,50);cp.addWidget(row(self.color_button,self.font_size))
        self.keywords=QLineEdit();self.keywords.setPlaceholderText('Ex.: almoço, promoção, Atibaia');cp.addWidget(label('Palavras-chave para destacar'));cp.addWidget(self.keywords)
        self.word_table=self.table(['Início','Fim','Palavra']);cp.addWidget(self.word_table,1)
        cp.addWidget(row(button('+ Palavra',self.add_word),button('Remover',self.remove_word)))
        cp.addWidget(button('Aplicar ajustes de legenda',self.apply_ui));self.right_tabs.addTab(caption,'Legendas')
        look=QWidget();lk=QVBoxLayout(look);lk.setContentsMargins(0,12,0,0);lk.addWidget(label('Imagem e identidade','title'))
        self.look=QComboBox();self.look.addItems(list(core.FILTERS));lk.addWidget(label('Filtro'));lk.addWidget(self.look)
        self.zoom=QDoubleSpinBox();self.zoom.setRange(1,1.3);self.zoom.setSingleStep(.01);self.zoom.setSuffix('×');lk.addWidget(label('Zoom fixo central'));lk.addWidget(self.zoom)
        lk.addWidget(button('Importar LUT .cube',self.import_lut));self.lut_label=label('Sem LUT');lk.addWidget(self.lut_label);lk.addWidget(button('Remover LUT',lambda:self.set_asset('lut','')))
        self.transition=QComboBox();self.transition.addItems(['Nenhuma','Preto','Branco']);lk.addWidget(label('Transição nas junções dos trechos'));lk.addWidget(self.transition)
        lk.addWidget(button('Aplicar ajustes de imagem',self.apply_ui));lk.addWidget(label('Confira o resultado em “Ver prévia com efeitos”. O zoom é fixo; animações de câmera ainda não estão incluídas.'));lk.addStretch();self.right_tabs.addTab(look,'Imagem')
        lower,lo=panel();self.lower=lower;lower.setMaximumHeight(285);lo.setContentsMargins(12,8,12,8);main.addWidget(lower)
        self.summary=label('TIMELINE / TEMPO DO ORIGINAL','title')
        lo.addWidget(row(self.summary,button('Sugerir cortes de pausas',self.suggest),button('Dividir no cursor',self.split),button('Restaurar vídeo inteiro',self.reset_ranges)))
        bottom=QSplitter(Qt.Horizontal);self.timeline=Timeline();self.timeline.seek.connect(self.seek_source);bottom.addWidget(self.timeline)
        self.range_table=self.table(['Manter','Início','Fim']);self.range_table.setMaximumHeight(150);self.range_table.setMinimumWidth(260);bottom.addWidget(self.range_table);bottom.setSizes([900,300]);lo.addWidget(bottom)
        lo.addWidget(row(label('Cortes baseados em intervalos entre palavras. Revise para preservar o ritmo da fala.'),button('Aplicar trechos',self.apply_ui)))
        self.status=label('Pronto • Seus arquivos originais são preservados.');self.progress=QProgressBar();self.progress.setMaximumWidth(160);self.progress.setRange(0,1);self.progress.setValue(0);main.addWidget(row(self.status,self.progress))
        for keys,fn in [('Ctrl+S',self.save),('Ctrl+O',self.load),('Ctrl+Z',self.undo)]:
            action=QAction(self);action.setShortcut(QKeySequence(keys));action.triggered.connect(fn);self.addAction(action)
    def table(self,headers):
        t=QTableWidget(0,len(headers));t.setHorizontalHeaderLabels(headers);t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch);t.verticalHeader().hide();t.setAlternatingRowColors(True);return t
    def info(self,text):QMessageBox.information(self,'Kaique Studio',text)
    def error(self,text):QMessageBox.warning(self,'Confira este ponto',text)
    def busy(self):return self.job is not None
    def checkpoint(self):
        self.history.append(copy.deepcopy(self.p));self.history=self.history[-20:]
    def sync(self):
        p=copy.deepcopy(self.p)
        p.update(client=self.client.text(),script=self.script.toPlainText(),music_volume=self.volume.value()/100,
                 caption_mode=self.mode.currentText(),captions_enabled=self.caption_enabled.isChecked(),
                 font_size=self.font_size.value(),keywords=self.keywords.text(),filter=self.look.currentText(),transition=self.transition.currentText(),zoom=self.zoom.value())
        p['words']=[]
        for i in range(self.word_table.rowCount()):
            p['words'].append(dict(start=float(self.word_table.item(i,0).text().replace(',','.')),end=float(self.word_table.item(i,1).text().replace(',','.')),text=self.word_table.item(i,2).text()))
        p['ranges']=[]
        for i in range(self.range_table.rowCount()):
            p['ranges'].append(dict(enabled=self.range_table.item(i,0).checkState()==Qt.Checked,
                                   start=float(self.range_table.item(i,1).text().replace(',','.')),end=float(self.range_table.item(i,2).text().replace(',','.'))))
        if p['source']:core.validate(p,files=False)
        if p!=self.p:self.checkpoint();self.p=p
    def restore_ui(self):
        p=self.p;self.client.setText(p['client']);self.script.setPlainText(p['script']);self.volume.setValue(round(p['music_volume']*100))
        self.mode.setCurrentText(p['caption_mode']);self.caption_enabled.setChecked(p['captions_enabled']);self.font_size.setValue(p['font_size']);self.keywords.setText(p['keywords']);self.look.setCurrentText(p['filter']);self.zoom.setValue(p['zoom']);self.transition.setCurrentText(p.get('transition','Nenhuma'))
        self.color_button.setStyleSheet('border: 2px solid '+p['color']+';')
        self.media_list.clear()
        for i,take in enumerate(p.get('takes',[])):
            self.media_list.addItem(f"{i+1:02} • {Path(take['path']).name} • {take['end']-take['start']:.1f}s")
        if p['source'] and not p.get('takes'):self.media_list.addItem('▸ '+Path(p['source']).name)
        self.music_label.setText(Path(p['music']).name if p['music'] else 'Nenhuma música')
        self.lut_label.setText(Path(p['lut']).name if p['lut'] else 'Sem LUT')
        self.sticker_label.setText(f"{Path(p['sticker']).name} • {p['sticker_start']:.1f}–{p['sticker_end']:.1f}s" if p['sticker'] else 'Sem sticker')
        self.sfx_list.clear()
        for s in p['sfx']:self.sfx_list.addItem(f"{s['time']:.1f}s • {Path(s['path']).name}")
        self.word_table.setRowCount(len(p['words']))
        for i,w in enumerate(p['words']):
            for j,v in enumerate([f"{w['start']:.3f}",f"{w['end']:.3f}",w['text']]):self.word_table.setItem(i,j,QTableWidgetItem(v))
        self.range_table.setRowCount(len(p['ranges']))
        for i,r in enumerate(p['ranges']):
            item=QTableWidgetItem(str(i+1));item.setFlags(Qt.ItemIsEnabled|Qt.ItemIsUserCheckable|Qt.ItemIsSelectable);item.setCheckState(Qt.Checked if r['enabled'] else Qt.Unchecked);self.range_table.setItem(i,0,item)
            self.range_table.setItem(i,1,QTableWidgetItem(f"{r['start']:.3f}"));self.range_table.setItem(i,2,QTableWidgetItem(f"{r['end']:.3f}"))
        self.timeline.data=p;self.timeline.update();self.summary.setText(f"TIMELINE • {core.duration(p):.1f}s finais / {p['duration']:.1f}s originais")
    def apply_ui(self):
        if self.busy():return
        try:self.sync();self.restore_ui();self.status.setText('Ajustes aplicados. Gere uma prévia para conferir o resultado completo.')
        except Exception as e:self.error(str(e))
    def task(self,fn,done):
        if self.busy():return
        self.task_error=False;self.lower.setEnabled(False);self.workspace.setEnabled(False);self.export_button.setEnabled(False);self.progress.setRange(0,0)
        self.job=Job(fn);self.job.progress.connect(self.status.setText);self.job.result.connect(done);self.job.failed.connect(self.task_failed);self.job.finished.connect(self.task_finished);self.job.start()
    def task_failed(self,message):
        self.task_error=True;self.error(message)
    def task_finished(self):
        self.lower.setEnabled(True);self.workspace.setEnabled(True);self.export_button.setEnabled(True);self.progress.setRange(0,1);self.progress.setValue(0 if self.task_error else 1);self.status.setText('Não foi possível concluir. Confira o erro informado.' if self.task_error else 'Tarefa concluída. Revise o resultado.');self.job.deleteLater();self.job=None
    def take_paths(self):
        return [t['path'] for t in self.p.get('takes',[])] or ([self.p['source']] if self.p['source'] else [])
    def import_video(self):
        if self.busy():return
        paths,_=QFileDialog.getOpenFileNames(self,'Selecionar takes — Ctrl ou Shift','','Vídeos (*.mp4 *.mov *.mkv *.avi *.webm)')
        if paths:self.build_sequence(self.take_paths()+paths)
    def move_take(self,step):
        if self.busy():return
        i=self.media_list.currentRow();paths=self.take_paths();j=i+step
        if i<0 or not 0<=j<len(paths):return
        paths[i],paths[j]=paths[j],paths[i];self.build_sequence(paths)
    def remove_take(self):
        if self.busy():return
        i=self.media_list.currentRow();paths=self.take_paths()
        if i<0:return
        if len(paths)<2:return self.info('Mantenha pelo menos um take na sequência.')
        paths.pop(i);self.build_sequence(paths)
    def jump_take(self,item):
        i=self.media_list.row(item);takes=self.p.get('takes',[])
        if i<len(takes):self.seek_source(takes[i]['start']);self.player.play()
    def build_sequence(self,paths):
        try:self.sync()
        except Exception as e:return self.error(str(e))
        if self.p['source']:
            answer=QMessageBox.question(self,'Atualizar sequência',
                'A sequência será reconstruída nessa ordem. Cortes, transcrição, efeitos sonoros e sticker serão reiniciados. Música, roteiro e estilo serão mantidos. Você poderá desfazer. Continuar?')
            if answer!=QMessageBox.Yes:return
        import uuid
        cache=STATE/'sequencias';cache.mkdir(exist_ok=True)
        destination=str(cache/f'{uuid.uuid4().hex}.mp4')
        old=copy.deepcopy(self.p)
        def done(result):
            self.checkpoint();self.p=old
            self.p.update({key:result[key] for key in ['source','duration','width','height','takes']})
            self.p.update(words=[],sfx=[],sticker='')
            self.p['ranges']=[dict(start=t['start'],end=t['end'],enabled=True) for t in result['takes']]
            self.restore_ui();self.original()
        self.player.pause();self.task(lambda progress:core.assemble(paths,destination,progress),done)
    def media_status(self,status):
        if status==QMediaPlayer.EndOfMedia:
            self.status.setText('Fim do vídeo. Clique em ▶ para assistir novamente.')
    def quick_edit(self):
        self.prompt.setPlainText('cortes e legenda');self.apply_commands()
    def original(self):
        if not self.p['source']:return
        self.preview_mode=False;self.player.setSource(QUrl.fromLocalFile(self.p['source']));self.player_badge.setText('PLAYER / SEQUÊNCIA');self.live_caption.show();self.player.setPosition(0)
    def toggle(self):
        if self.player.playbackState()==QMediaPlayer.PlayingState:self.player.pause()
        else:
            if self.player.mediaStatus()==QMediaPlayer.EndOfMedia:self.player.setPosition(0)
            self.player.play()
    def seek_source(self,t):
        if self.preview_mode:self.original()
        self.player.setPosition(round(t*1000))
    def position_changed(self,pos):
        self.seekbar.setValue(pos);self.clock.setText(f'{pos/1000:.1f}s / {self.player.duration()/1000:.1f}s')
        if not self.preview_mode:
            self.timeline.position=pos/1000;self.timeline.update()
            word=next((w['text'] for w in self.p['words'] if w['start']<=pos/1000<w['end']), '')
            self.live_caption.setText(word or '');self.live_caption.setStyleSheet('color:'+self.p['color'])
    def transcribe(self):
        if self.busy():return
        if not self.p['source']:return self.info('Importe um vídeo primeiro.')
        if self.p['words'] and QMessageBox.question(self,'Transcrever novamente','Substituir as palavras atuais pela nova transcrição?')!=QMessageBox.Yes:return
        try:self.sync()
        except Exception as e:return self.error(str(e))
        source=self.p['source']
        def done(words):self.checkpoint();self.p['words']=words;self.restore_ui()
        self.task(lambda progress:core.transcribe(source,progress),done)
    def suggest(self):
        if self.busy():return
        try:
            self.sync();ranges=core.suggest_ranges(self.p['words'],self.p['duration'])
            removed=self.p['duration']-sum(r['end']-r['start'] for r in ranges)
            if QMessageBox.question(self,'Revisar cortes',f'Sugestão: {len(ranges)} trechos; remover aproximadamente {removed:.1f}s sem palavras reconhecidas.\n\nNão identifica respirações nem avalia a qualidade dos takes. Aplicar à tabela para revisar?')==QMessageBox.Yes:
                self.checkpoint();self.p['ranges']=ranges;self.restore_ui()
        except Exception as e:self.error(str(e))
    def split(self):
        if self.busy():return
        if self.preview_mode:return self.info('Volte ao original para dividir um trecho.')
        try:self.sync()
        except Exception as e:return self.error(str(e))
        t=self.player.position()/1000
        for i,r in enumerate(self.p['ranges']):
            if r['start']+.03<t<r['end']-.03:
                self.checkpoint();self.p['ranges'][i:i+1]=[dict(start=r['start'],end=t,enabled=r['enabled']),dict(start=t,end=r['end'],enabled=r['enabled'])];self.restore_ui();return
        self.info('Posicione o cursor no meio de um trecho.')
    def reset_ranges(self):
        if self.busy() or not self.p['source']:return
        self.checkpoint();self.p['ranges']=[dict(start=0,end=self.p['duration'],enabled=True)];self.restore_ui()
    def undo(self):
        if self.busy() or not self.history:return
        source=self.p['source'];self.p=self.history.pop();self.restore_ui()
        if source!=self.p['source']:self.original()
    def interpret(self):
        actions,unknown=core.commands(self.prompt.toPlainText())
        text='\n'.join('• '+x[2] for x in actions) or 'Nenhum comando reconhecido.'
        if unknown:text+='\n\nAinda não suportado:\n'+'\n'.join('• '+x for x in unknown)
        self.plan_text.setPlainText(text)
    def apply_commands(self):
        if self.busy():return
        actions,unknown=core.commands(self.prompt.toPlainText());self.interpret()
        if unknown:return self.info('Remova ou ajuste os pedidos não reconhecidos antes de aplicar. Veja os exemplos em Ajuda.')
        if not actions:return
        try:
            self.sync()
            if not self.p['source']:return self.info('Importe os takes primeiro.')
            candidate=copy.deepcopy(self.p)
            needs_words=any(k=='cuts' or k=='caption_mode' or (k=='captions_enabled' and v) for k,v,_ in actions)
            def finish(words=None):
                if words is not None:candidate['words']=words
                try:
                    for key,value,_ in actions:
                        if key=='cuts':candidate['ranges']=core.suggest_ranges(candidate['words'],candidate['duration'])
                        else:candidate[key]=value
                    core.validate(candidate,files=False)
                    self.checkpoint();self.p=candidate;self.restore_ui()
                    self.plan_text.setPlainText('Plano aplicado. Revise os cortes e as palavras; depois gere a prévia com efeitos.')
                except Exception as e:self.error(str(e))
            if needs_words and not candidate['words']:
                if QMessageBox.question(self,'Transcrever e preparar edição',
                    'Vou transcrever a sequência e aplicar o plano para revisão. Na primeira vez, o modelo é baixado pela internet. Os cortes podem remover takes sem fala; revise antes de exportar. Continuar?')!=QMessageBox.Yes:return
                self.task(lambda progress:core.transcribe(candidate['source'],progress),finish)
            else:finish()
        except Exception as e:self.error(str(e))
    def pick_color(self):
        color=QColorDialog.getColor(QColor(self.p['color']),self)
        if color.isValid():
            try:self.sync()
            except Exception as e:return self.error(str(e))
            self.checkpoint();self.p['color']=color.name();self.restore_ui()
    def add_word(self):
        i=self.word_table.rowCount();self.word_table.insertRow(i)
        start=float(self.word_table.item(i-1,1).text()) if i else 0
        for j,value in enumerate([str(round(start,3)),str(round(start+.3,3)),'palavra']):self.word_table.setItem(i,j,QTableWidgetItem(value))
    def remove_word(self):
        i=self.word_table.currentRow()
        if i>=0:self.word_table.removeRow(i)
    def set_asset(self,key,path):
        if self.busy():return
        try:self.sync()
        except Exception as e:return self.error(str(e))
        self.checkpoint();self.p[key]=path;self.restore_ui()
    def open_library(self):
        if self.busy():return
        try:
            from resource_library import LibraryDialog
            self.sync();LibraryDialog(self,STATE,BASE).exec()
        except Exception as exc:self.error(str(exc))
    def import_music(self):
        path,_=QFileDialog.getOpenFileName(self,'Importar música','','Áudio (*.mp3 *.wav *.m4a *.aac *.flac)')
        if path:self.set_asset('music',path)
    def import_lut(self):
        path,_=QFileDialog.getOpenFileName(self,'Importar LUT','','LUT (*.cube)')
        if path:self.set_asset('lut',path)
    def add_sfx(self):
        if not self.p['source']:return self.info('Importe um vídeo primeiro.')
        path,_=QFileDialog.getOpenFileName(self,'Efeito sonoro local','','Áudio (*.mp3 *.wav *.m4a *.aac *.flac)')
        if not path:return
        t,ok=QInputDialog.getDouble(self,'Posição do efeito','Segundo na edição FINAL:',0,0,max(0,core.duration(self.p)-.01),2)
        if ok:
            try:self.sync()
            except Exception as e:return self.error(str(e))
            self.checkpoint();self.p['sfx'].append(dict(path=path,time=t,volume=.7));self.restore_ui()
    def remove_sfx(self):
        i=self.sfx_list.currentRow()
        if i>=0:self.checkpoint();self.p['sfx'].pop(i);self.restore_ui()
    def import_sticker(self):
        if not self.p['source']:return self.info('Importe um vídeo primeiro.')
        path,_=QFileDialog.getOpenFileName(self,'Sticker transparente','','Imagem PNG (*.png)')
        if not path:return
        length=core.duration(self.p)
        start,ok=QInputDialog.getDouble(self,'Sticker','Início na edição final:',0,0,max(0,length-.1),2)
        if not ok:return
        end,ok=QInputDialog.getDouble(self,'Sticker','Fim na edição final:',min(length,start+3),start+.01,length,2)
        if ok:
            try:self.sync()
            except Exception as e:return self.error(str(e))
            self.checkpoint();self.p.update(sticker=path,sticker_start=start,sticker_end=end);self.restore_ui()
    def import_script(self):
        path,_=QFileDialog.getOpenFileName(self,'Roteiro','','Texto (*.txt *.md)')
        if path:
            try:self.script.setPlainText(Path(path).read_text(encoding='utf-8-sig'))
            except Exception as e:self.error(str(e))
    def save(self):
        if self.busy():return
        try:self.sync()
        except Exception as e:return self.error(str(e))
        path,_=QFileDialog.getSaveFileName(self,'Salvar projeto',self.project_path or 'meu-projeto.kaique.json','Projeto (*.json)')
        if path:
            try:core.atomic_json(path,self.p);self.project_path=path;self.status.setText('Projeto salvo: '+Path(path).name)
            except Exception as e:self.error(str(e))
    def load(self):
        if self.busy():return
        path,_=QFileDialog.getOpenFileName(self,'Abrir projeto','','Projeto (*.json)')
        if not path:return
        if self.p['source'] and QMessageBox.question(self,'Trocar projeto','Abrir outro projeto descarta alterações não salvas. Continuar?')!=QMessageBox.Yes:return
        try:
            data=json.loads(Path(path).read_text(encoding='utf-8'));core.validate(data)
            self.checkpoint();self.p=data;self.project_path=path;self.restore_ui();self.original()
        except Exception as e:self.error(str(e))
    def autosave(self):
        if self.busy() or not self.p['source']:return
        try:self.sync();core.atomic_json(STATE/'recuperacao.json',self.p)
        except Exception:pass
    def export(self,preview=False):
        if self.busy():return
        try:self.sync();core.validate(self.p)
        except Exception as e:return self.error(str(e))
        if not self.p['words'] and self.p['captions_enabled']:
            if QMessageBox.question(self,'Sem transcrição','Ainda não há palavras. Exportar sem legendas?')!=QMessageBox.Yes:return
        if preview:
            import time
            path=str(STATE/f'previa-{time.time_ns()}.mp4')
        else:
            path,_=QFileDialog.getSaveFileName(self,'Exportar MP4','video-final.mp4','Vídeo (*.mp4)')
            if not path:return
        if Path(path).exists():return self.info('Escolha um nome novo para preservar o arquivo existente.')
        snapshot=copy.deepcopy(self.p)
        def done(output):
            if preview:
                self.preview_mode=True;self.player_badge.setText('PRÉVIA RENDERIZADA / ATÉ 10s');self.live_caption.hide();self.player.setSource(QUrl.fromLocalFile(output));self.player.play()
            else:self.info('MP4 exportado:\n'+output)
        self.player.pause();self.task(lambda progress:core.render(snapshot,path,progress,preview),done)
    def help(self):
        message=QMessageBox(self);message.setWindowTitle('Ajuda • Kaique Studio');message.setText('Comece: importar vídeo → Legendas → Transcrever → revisar cortes → Ver prévia com efeitos.\n\nComandos aceitos (separe por ponto e vírgula):\nlegendas dinâmicas; filtro quente; volume música 15%; cortar pausas\nTambém: filtro contraste; filtro preto e branco; legendas brancas; zoom 1.10; sem legendas\n\nA prévia renderizada mostra a edição completa. O player original não aplica filtros.\n\nInstalar FFmpeg completo, se solicitado: abra o Terminal do Windows e execute:\nwinget install --id Gyan.FFmpeg -e\nDepois feche e abra o Studio.\n\nRecuperação automática e logs:\n'+str(STATE))
        manual=message.addButton('Abrir manual',QMessageBox.ActionRole);folder=message.addButton('Abrir recuperação',QMessageBox.ActionRole);message.addButton(QMessageBox.Close);message.exec()
        if message.clickedButton()==manual:QDesktopServices.openUrl(QUrl.fromLocalFile(str(BASE/'COMECE-AQUI.txt')))
        if message.clickedButton()==folder:QDesktopServices.openUrl(QUrl.fromLocalFile(str(STATE)))
    def closeEvent(self,event):
        if self.busy():self.info('Uma tarefa está em andamento. Aguarde terminar antes de fechar.');event.ignore();return
        if self.p['source']:
            answer=QMessageBox.question(self,'Fechar Studio','Salvar o projeto antes de sair?',QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel)
            if answer==QMessageBox.Cancel:event.ignore();return
            if answer==QMessageBox.Save:
                self.save()
                # Always let the user explicitly close again after saving, so cancel/failure never loses work.
                event.ignore();return
        self.player.stop();event.accept()

if __name__=='__main__':
    app=QApplication(sys.argv);app.setStyle('Fusion');app.setStyleSheet(STYLE)
    window=Studio();window.show();sys.exit(app.exec())
