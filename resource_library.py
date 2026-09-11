"""Local, categorized asset collection. Remote search opens the source website."""
import json, shutil, uuid
from pathlib import Path
from urllib.parse import urlencode
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog,QVBoxLayout,QHBoxLayout,QLineEdit,QComboBox,
    QListWidget,QListWidgetItem,QPushButton,QLabel,QFileDialog,QMessageBox,QInputDialog,QCheckBox)
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
import core

KINDS=['Todos','Memes','Efeitos sonoros','Músicas','LUTs','Transições','Filtros']
CATEGORIES=['Todas','Humor','Reações','Suspense','Impacto','Movimento','Interface','Ambiente',
            'Gastronomia','Natureza','Institucional','Cinemático','Outros']
EXTENSIONS={'Memes':{'.mp3','.wav','.m4a','.aac','.flac'},
            'Efeitos sonoros':{'.mp3','.wav','.m4a','.aac','.flac'},
            'Músicas':{'.mp3','.wav','.m4a','.aac','.flac'},'LUTs':{'.cube'}}

class Catalog:
    def __init__(self,root,bundled):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.file=self.root/'catalogo.json'
        self.data={'items':[],'favorites':[]}
        if self.file.exists():self.data=json.loads(self.file.read_text(encoding='utf-8'))
        self.bundled=Path(bundled)
        self.defaults=json.loads((self.bundled/'catalog.json').read_text(encoding='utf-8'))
    def items(self):
        defaults=[]
        for entry in self.defaults:
            e=dict(entry)
            if e.get('path'):e['path']=str((self.bundled/e['path']).resolve())
            defaults.append(e)
        return defaults+self.data['items']
    def save(self):core.atomic_json(self.file,self.data)
    def add(self,paths,kind,category):
        allowed=EXTENSIONS[kind]
        paths=[Path(p) for p in paths]
        if any(p.suffix.lower() not in allowed or not p.is_file() for p in paths):
            raise ValueError('Selecione arquivos compatíveis com o tipo escolhido.')
        new=[];created=[]
        try:
            for path in paths:
                identifier=uuid.uuid4().hex;target=self.root/(identifier+path.suffix.lower())
                shutil.copyfile(path,target);created.append(target)
                new.append(dict(id=identifier,title=path.stem,kind=kind,category=category,path=str(target.resolve())))
            self.data['items'].extend(new);self.save()
        except Exception:
            self.data['items']=[e for e in self.data['items'] if e not in new]
            for path in created:path.unlink(missing_ok=True)
            raise
        return new
    def favorite(self,identifier):
        favorites=self.data['favorites']
        if identifier in favorites:favorites.remove(identifier)
        else:favorites.append(identifier)
        self.save()

def myinstants_url(query):
    return 'https://www.myinstants.com/pt/search/?'+urlencode({'name':query.strip() or 'mentira'})

class LibraryDialog(QDialog):
    def __init__(self,studio,state,base):
        super().__init__(studio);self.studio=studio
        self.catalog=Catalog(Path(state)/'biblioteca',Path(base)/'assets')
        self.setWindowTitle('Biblioteca • Kaique Studio');self.resize(880,650)
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel('BIBLIOTECA / sons, memes, LUTs e presets'))
        filters=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('Buscar no acervo ou digitar uma busca para o Myinstants…')
        self.kind=QComboBox();self.kind.addItems(KINDS);self.category=QComboBox();self.category.addItems(CATEGORIES)
        filters.addWidget(self.search,1);filters.addWidget(self.kind);filters.addWidget(self.category);layout.addLayout(filters)
        self.only_favorites=QCheckBox('Somente favoritos');layout.addWidget(self.only_favorites)
        self.list=QListWidget();layout.addWidget(self.list,1)
        self.details=QLabel('');self.details.setWordWrap(True);layout.addWidget(self.details)
        controls=QHBoxLayout()
        for title,fn in [('Ouvir / parar',self.listen),('★ Favoritar',self.favorite),('Usar no projeto',self.apply),('Importar arquivos',self.import_files)]:
            b=QPushButton(title);b.clicked.connect(fn);controls.addWidget(b)
        layout.addLayout(controls)
        online=QPushButton('Buscar no Myinstants ↗');online.clicked.connect(self.online);layout.addWidget(online)
        note=QLabel('Myinstants abre no navegador. Baixe o áudio desejado no site e importe em Memes. O catálogo online não é espelhado no aplicativo. Memes aqui são áudios; vídeos de memes ainda não entram como sobreposição.')
        note.setWordWrap(True);layout.addWidget(note)
        self.player=QMediaPlayer(self);self.audio=QAudioOutput(self);self.audio.setVolume(.5);self.player.setAudioOutput(self.audio)
        self.player.errorOccurred.connect(lambda *_:self.details.setText('Não foi possível ouvir: '+self.player.errorString()))
        self.search.textChanged.connect(self.refresh);self.kind.currentTextChanged.connect(self.refresh);self.category.currentTextChanged.connect(self.refresh);self.only_favorites.toggled.connect(self.refresh)
        self.list.currentItemChanged.connect(self.describe);self.refresh()
    def refresh(self,*_):
        self.list.clear();query=core.normalized(self.search.text());favorites=self.catalog.data['favorites']
        for e in self.catalog.items():
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
        if e['kind'] not in EXTENSIONS or e['kind']=='LUTs':return self.details.setText('Aplique este recurso e gere a prévia com efeitos no editor.')
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
        query=self.search.text().strip()
        if not query:
            query,ok=QInputDialog.getText(self,'Myinstants','Qual som procurar?',text='mentira')
            if not ok:return
        QDesktopServices.openUrl(QUrl(myinstants_url(query)))
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
            core.validate(candidate);s.checkpoint();s.p=candidate;s.restore_ui()
            self.player.stop();self.details.setText('Aplicado. Feche a biblioteca e clique em Ver prévia com efeitos.')
        except Exception as exc:QMessageBox.warning(self,'Confira',str(exc))
    def closeEvent(self,event):self.player.stop();super().closeEvent(event)
    def reject(self):self.player.stop();super().reject()
