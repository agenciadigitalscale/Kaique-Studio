"""Interface Qt da biblioteca. A lógica do acervo vive em `library.py` (sem Qt)."""
from pathlib import Path
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLineEdit,QComboBox,
    QListWidget,QListWidgetItem,QPushButton,QLabel,QFileDialog,QMessageBox,QInputDialog,QCheckBox)
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
import core, updates
# Reexporta o núcleo para quem já importava daqui (app.py, testes antigos).
from library import Catalog, KINDS, CATEGORIES, EXTENSIONS, myinstants_url, apply_preset, all_sources, search_url

class LibraryDialog(QDialog):
    def __init__(self,studio,state,base):
        super().__init__(studio);self.studio=studio
        self.catalog=Catalog(Path(state)/'biblioteca',Path(base)/'assets')
        self.setWindowTitle('Biblioteca • Kaique Studio');self.resize(880,650)
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('BIBLIOTECA / sons, memes, LUTs e presets'))
        filters=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Buscar no acervo, ou digitar um termo e buscar online…')
        self.kind=QComboBox();self.kind.addItems(KINDS);self.category=QComboBox();self.category.addItems(CATEGORIES)
        filters.addWidget(self.search,1);filters.addWidget(self.kind);filters.addWidget(self.category);layout.addLayout(filters)
        self.only_favorites=QCheckBox('Somente favoritos');layout.addWidget(self.only_favorites)
        self.list=QListWidget();layout.addWidget(self.list,1)
        self.details=QLabel('');self.details.setWordWrap(True);layout.addWidget(self.details)
        controls=QHBoxLayout()
        for title,fn in [('Ouvir / parar',self.listen),('★ Favoritar',self.favorite),('Usar no projeto',self.apply),('Importar arquivos',self.import_files)]:
            b=QPushButton(title);b.clicked.connect(fn);controls.addWidget(b)
        layout.addLayout(controls)
        online_row=QHBoxLayout()
        online_row.addWidget(QLabel('Buscar online em:'))
        self.source=QComboBox()
        for kind,name in all_sources():self.source.addItem(f'{kind} · {name}',(kind,name))
        online_row.addWidget(self.source,1)
        self.online_btn=QPushButton('Abrir busca ↗');self.online_btn.clicked.connect(self.online);online_row.addWidget(self.online_btn)
        self.update_btn=QPushButton('⟳ Buscar novidades');self.update_btn.setToolTip('Baixa efeitos, presets e ícones novos publicados para o Studio');self.update_btn.clicked.connect(self.fetch_updates);online_row.addWidget(self.update_btn)
        layout.addLayout(online_row)
        note=QLabel('A busca online abre a fonte no navegador. Baixe o arquivo e importe aqui — as fontes listadas oferecem conteúdo de uso livre/CC. Confira sempre a licença na página antes de usar em vídeo de cliente.')
        note.setWordWrap(True);layout.addWidget(note)
        self.player=QMediaPlayer(self);self.audio=QAudioOutput(self);self.audio.setVolume(.5);self.player.setAudioOutput(self.audio)
        self.player.errorOccurred.connect(lambda *_:self.details.setText('Não foi possível ouvir: '+self.player.errorString()))
        self.search.textChanged.connect(self.refresh);self.kind.currentTextChanged.connect(self.refresh);self.category.currentTextChanged.connect(self.refresh);self.only_favorites.toggled.connect(self.refresh)
        self.list.currentItemChanged.connect(self.describe);self.refresh()
    def refresh(self,*_):
        self.list.clear();query=core.normalized(self.search.text());favorites=self.catalog.data['favorites']
        for e in self.catalog.items()+self.catalog.presets():
            if self.kind.currentText()!='Todos' and e['kind']!=self.kind.currentText():continue
            if self.category.currentText()!='Todas' and e['category']!=self.category.currentText():continue
            if self.only_favorites.isChecked() and e['id'] not in favorites:continue
            if query not in core.normalized(' '.join([e['title'],e['kind'],e['category']])):continue
            item=QListWidgetItem(('★ ' if e['id'] in favorites else '')+f"{e['title']}  ·  {e['kind']} / {e['category']}")
            item.setData(Qt.UserRole,e);self.list.addItem(item)
        self.details.setText(f'{self.list.count()} recursos. Selecione um para ouvir ou aplicar.')
    def selected(self):
        item=self.list.currentItem();return item.data(Qt.UserRole) if item else None
    def describe(self,*_):
        e=self.selected()
        if e:self.details.setText(e.get('description','Arquivo local: '+e['title']))
    def listen(self):
        e=self.selected()
        if not e:return
        if e['kind'] not in EXTENSIONS or e['kind'] in ('LUTs','Ícones','Imagens'):return self.details.setText('Aplique este recurso e gere a prévia com efeitos no editor.')
        if self.player.playbackState()==QMediaPlayer.PlayingState:self.player.stop();return
        self.studio.player.pause();self.player.setSource(QUrl.fromLocalFile(e['path']));self.player.play()
    def favorite(self):
        e=self.selected()
        if e:
            try:self.catalog.favorite(e['id']);self.refresh()
            except Exception as exc:QMessageBox.warning(self,'Erro',str(exc))
    def import_files(self):
        kind,ok=QInputDialog.getItem(self,'Tipo de recurso','Importar como:',list(EXTENSIONS),0,False)
        if not ok:return
        category,ok=QInputDialog.getItem(self,'Categoria','Organizar em:',CATEGORIES[1:],0,False)
        if not ok:return
        extensions=' '.join('*'+x for x in sorted(EXTENSIONS[kind]))
        paths,_=QFileDialog.getOpenFileNames(self,'Importar vários recursos','',f'Arquivos ({extensions})')
        if paths:
            try:
                added=self.catalog.add(paths,kind,category);self.search.clear();self.kind.setCurrentText(kind);self.category.setCurrentText(category);self.only_favorites.setChecked(False);self.refresh()
                self.details.setText(f'{len(added)} arquivos copiados para seu acervo permanente.')
            except Exception as exc:QMessageBox.warning(self,'Erro',str(exc))
    def online(self):
        data=self.source.currentData()
        if not data:return
        kind,source=data
        query=self.search.text().strip()
        if not query:
            query,ok=QInputDialog.getText(self,'Buscar online',f'O que procurar em {source}?')
            if not ok or not query.strip():return
        try:QDesktopServices.openUrl(QUrl(search_url(kind,query,source)))
        except Exception as exc:QMessageBox.warning(self,'Busca',str(exc))
    def fetch_updates(self):
        """Consulta o canal e instala os pacotes novos. Roda com cursor de espera;
        falha de rede/canal ausente vira aviso amigável, nunca tela de erro."""
        self.update_btn.setEnabled(False);QGuiApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result=updates.sync(self.catalog)
        except Exception as exc:
            QMessageBox.information(self,'Novidades','Não foi possível buscar novidades agora.\n\n'
                'Verifique sua conexão e tente mais tarde — o canal de conteúdo do Studio ainda '
                'pode não estar publicado.\n\nDetalhe: '+str(exc))
            return
        finally:
            QGuiApplication.restoreOverrideCursor();self.update_btn.setEnabled(True)
        self.refresh()
        if result['added']:
            extra=f"\n\n{len(result['errors'])} não vieram (rede)." if result['errors'] else ''
            QMessageBox.information(self,'Novidades',f"Chegaram {result['added']} novidades ao seu acervo!{extra}")
        else:
            QMessageBox.information(self,'Novidades','Você já está com tudo em dia — nenhuma novidade nova.')
    def apply(self):
        e=self.selected();s=self.studio
        if not e:return
        if not s.p['source']:return QMessageBox.information(self,'Importar takes','Importe os takes antes de aplicar recursos.')
        try:
            s.sync()
            import copy
            candidate=copy.deepcopy(s.p)
            if e['kind'] in ['Memes','Efeitos sonoros']:
                t,ok=QInputDialog.getDouble(self,'Posição','Segundo na edição FINAL:',0,0,max(0,core.duration(s.p)-.01),2)
                if not ok:return
                candidate['sfx'].append(dict(path=e['path'],time=t,volume=.7))
            elif e['kind']=='Músicas':candidate['music']=e['path']
            elif e['kind']=='LUTs':candidate['lut']=e['path']
            elif e['kind']=='Transições':candidate['transition']=e['value']
            elif e['kind']=='Filtros':candidate['filter']=e['value']
            elif e['kind']=='Presets':candidate=apply_preset(candidate,e['preset'])
            elif e['kind'] in ['Ícones','Imagens']:
                corner,ok=QInputDialog.getItem(self,'Sobreposição','Posição na tela:',list(core.CORNERS),0,False)
                if not ok:return
                total=core.duration(s.p)
                start,ok=QInputDialog.getDouble(self,'Sobreposição','Aparece a partir de (segundo):',0,0,max(0,total-.01),2)
                if not ok:return
                end,ok=QInputDialog.getDouble(self,'Sobreposição','Some em (segundo):',min(total,start+3),start+.1,total,2)
                if not ok:return
                candidate.setdefault('overlays',[]).append(dict(path=e['path'],start=start,end=end,corner=corner,width=180))
            core.validate(candidate);s.checkpoint();s.p=candidate;s.restore_ui()
            self.player.stop();self.details.setText('Aplicado. Feche a biblioteca e clique em Ver prévia com efeitos.')
        except Exception as exc:QMessageBox.warning(self,'Confira',str(exc))
    def closeEvent(self,event):self.player.stop();super().closeEvent(event)
    def reject(self):self.player.stop();super().reject()
