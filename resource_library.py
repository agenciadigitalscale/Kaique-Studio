"""Interface Qt da biblioteca. A lógica do acervo vive em `library.py` (sem Qt)."""
import json
from pathlib import Path
from PySide6.QtCore import Qt, QUrl, QSize, QMimeData
from PySide6.QtGui import QDesktopServices, QGuiApplication, QColor, QBrush, QFont
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLineEdit,QComboBox,
    QListWidget,QListWidgetItem,QPushButton,QLabel,QFileDialog,QMessageBox,QInputDialog,QCheckBox,
    QAbstractItemView)
from PySide6.QtMultimedia import QMediaPlayer,QAudioOutput
import core, updates
# Reexporta o núcleo para quem já importava daqui (app.py, testes antigos).
from library import (Catalog, KINDS, CATEGORIES, EXTENSIONS, myinstants_url, apply_preset,
    all_sources, search_url, group_for_display, kind_emoji, category_emoji, apply_entry, RESOURCE_MIME)


class DragList(QListWidget):
    """Lista da biblioteca com itens ARRASTÁVEIS para a timeline.

    O recurso viaja como JSON num tipo MIME próprio (`RESOURCE_MIME`); a timeline
    decodifica e aplica no tempo onde foi solto. Cabeçalhos de seção têm
    `NoItemFlags`, então não arrastam — só recurso de verdade sai daqui.
    """
    def __init__(self):
        super().__init__()
        self.setDragEnabled(True);self.setDragDropMode(QAbstractItemView.DragOnly)
    def mimeData(self, items):
        md = QMimeData()
        for it in items:
            e = it.data(Qt.UserRole)
            if e:
                md.setData(RESOURCE_MIME, json.dumps(e).encode('utf-8'));break
        return md

# Estilo próprio da Biblioteca — herda o tema do app e refina a lista: linhas
# altas e arejadas, cabeçalho de seção com o verde da marca, seleção destacada.
LIBRARY_QSS = '''
QDialog {background:#0e0b16;}
QListWidget {background:#140f1f;border:1px solid #2a2340;border-radius:10px;padding:4px;outline:0;}
QListWidget::item {padding:9px 10px;border-radius:8px;margin:1px 2px;}
QListWidget::item:hover {background:#221a33;}
QListWidget::item:selected {background:#3a2560;color:#f0e7ff;}
QLabel#libtitle {font-size:15px;font-weight:800;letter-spacing:1px;color:#c084fc;}
QLabel#libhint {color:#9a90b5;font-size:11px;}
'''
_AUDIO_KINDS = {'Memes', 'Efeitos sonoros', 'Músicas'}
_HEADER_ROLE = Qt.UserRole + 1  # marca a linha como cabeçalho de seção (não selecionável)

class LibraryPanel(QWidget):
    def __init__(self,studio,state,base):
        super().__init__(studio);self.studio=studio
        self.catalog=Catalog(Path(state)/'biblioteca',Path(base)/'assets')
        self.setStyleSheet(LIBRARY_QSS)
        layout=QVBoxLayout(self)
        head=QLabel('🎬  BIBLIOTECA');head.setObjectName('libtitle');layout.addWidget(head)
        sub=QLabel('Clique num som para ouvir na hora · arraste qualquer recurso para a timeline · botão direito e “Usar no projeto” também aplicam.');sub.setObjectName('libhint');sub.setWordWrap(True);layout.addWidget(sub)
        filters=QHBoxLayout();self.search=QLineEdit();self.search.setPlaceholderText('🔎  Buscar no acervo, ou digitar um termo e buscar online…')
        self.kind=QComboBox();self.kind.addItems(KINDS);self.category=QComboBox();self.category.addItems(CATEGORIES)
        filters.addWidget(self.search,1);filters.addWidget(self.kind);filters.addWidget(self.category);layout.addLayout(filters)
        self.only_favorites=QCheckBox('Somente favoritos');layout.addWidget(self.only_favorites)
        self.list=DragList();self.list.setSpacing(0);self.list.setUniformItemSizes(False);layout.addWidget(self.list,1)
        self.details=QLabel('');self.details.setObjectName('libhint');self.details.setWordWrap(True);layout.addWidget(self.details)
        controls=QHBoxLayout()
        for title,fn in [('Ouvir / parar',self.listen),('★ Favoritar',self.favorite),('Usar no projeto',self.apply),('🔊 Efeitos embutidos',self.add_builtin_sfx),('Importar arquivos',self.import_files)]:
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
        self.list.currentItemChanged.connect(self.on_select)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu);self.list.customContextMenuRequested.connect(self.context_menu)
        self.refresh()
    def _visible_entries(self):
        query=core.normalized(self.search.text());favorites=self.catalog.data['favorites'];out=[]
        for e in self.catalog.items()+self.catalog.presets():
            if self.kind.currentText()!='Todos' and e['kind']!=self.kind.currentText():continue
            if self.category.currentText()!='Todas' and e['category']!=self.category.currentText():continue
            if self.only_favorites.isChecked() and e['id'] not in favorites:continue
            if query not in core.normalized(' '.join([e['title'],e['kind'],e['category']])):continue
            out.append(e)
        return out
    def refresh(self,*_):
        self.list.clear();favorites=self.catalog.data['favorites'];total=0
        for r in group_for_display(self._visible_entries()):
            if r[0]=='header':
                _,kind,count=r
                h=QListWidgetItem(f'{kind_emoji(kind)}  {kind.upper()}   ·   {count}')
                h.setData(_HEADER_ROLE,True);h.setFlags(Qt.NoItemFlags)  # não selecionável, não clicável
                f=QFont();f.setBold(True);f.setPointSize(9);h.setFont(f);h.setForeground(QBrush(QColor('#c084fc')))
                h.setSizeHint(QSize(0,30));self.list.addItem(h)
            else:
                e=r[1];star='⭐ ' if e['id'] in favorites else ''
                item=QListWidgetItem(f"{star}{category_emoji(e['category'])}  {e['title']}     {e['category']}")
                item.setData(Qt.UserRole,e);item.setSizeHint(QSize(0,38));self.list.addItem(item);total+=1
        self.details.setText(f'{total} recursos no acervo. Clique num som para ouvir na hora; use os botões abaixo para favoritar ou aplicar.')
    def selected(self):
        item=self.list.currentItem()
        return item.data(Qt.UserRole) if item and not item.data(_HEADER_ROLE) else None
    def on_select(self,*_):
        """Um clique já toca: seleção de um som dispara a prévia na hora (pedido do
        dono). Tipo visual (LUT/ícone/imagem/preset) não toca — descreve."""
        e=self.selected()
        if not e:return
        self.describe()
        if e['kind'] in _AUDIO_KINDS and e.get('path'):
            self.studio.player.pause();self.player.stop()
            self.player.setSource(QUrl.fromLocalFile(e['path']));self.player.play()
    def describe(self,*_):
        e=self.selected()
        if e:self.details.setText(e.get('description','Arquivo local: '+e['title']))
    def listen(self):
        e=self.selected()
        if not e:return
        if e['kind'] not in _AUDIO_KINDS:return self.details.setText('Aplique este recurso e gere a prévia com efeitos no editor.')
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
    def add_builtin_sfx(self):
        """Gera o kit de efeitos sonoros embutidos e mostra no acervo."""
        self.setCursor(Qt.WaitCursor)
        try:novos=self.catalog.ensure_builtin_sfx()
        except Exception as exc:
            self.unsetCursor();QMessageBox.warning(self,'Efeitos embutidos',f'Não deu para gerar os efeitos: {exc}');return
        self.unsetCursor()
        self.search.clear();self.kind.setCurrentText('Efeitos sonoros');self.category.setCurrentText('Todas');self.only_favorites.setChecked(False);self.refresh()
        if novos:QMessageBox.information(self,'Efeitos embutidos',f'{len(novos)} efeitos sonoros gerados e adicionados ao acervo. Clique num para ouvir.')
        else:QMessageBox.information(self,'Efeitos embutidos','Os efeitos embutidos já estão no seu acervo.')
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
            s.sync();total=core.duration(s.p);at=0.0;corner=None
            if e['kind'] in ('Memes','Efeitos sonoros'):
                at,ok=QInputDialog.getDouble(self,'Posição','Segundo na edição FINAL:',0,0,max(0,total-.01),2)
                if not ok:return
            elif e['kind'] in ('Ícones','Imagens'):
                corner,ok=QInputDialog.getItem(self,'Sobreposição','Posição na tela:',list(core.CORNERS),0,False)
                if not ok:return
                at,ok=QInputDialog.getDouble(self,'Sobreposição','Aparece a partir de (segundo):',0,0,max(0,total-.01),2)
                if not ok:return
            candidate=apply_entry(s.p,e,at_time=at,corner=corner)
            core.validate(candidate);s.checkpoint();s.p=candidate;s.restore_ui()
            self.player.stop();self.details.setText('Aplicado. Clique em “Prévia com efeitos” para ver.')
        except Exception as exc:QMessageBox.warning(self,'Confira',str(exc))
    def context_menu(self,pos):
        """Botão direito num recurso: ouvir, aplicar, favoritar — o pedido de
        'opção pra tudo com botão direito'."""
        e=self.selected()
        if not e:return
        from PySide6.QtWidgets import QMenu
        menu=QMenu(self)
        if e['kind'] in _AUDIO_KINDS:menu.addAction('🔊  Ouvir / parar',self.listen)
        menu.addAction('➕  Usar no projeto',self.apply)
        star='☆  Desfavoritar' if e['id'] in self.catalog.data['favorites'] else '⭐  Favoritar'
        menu.addAction(star,self.favorite)
        menu.exec(self.list.mapToGlobal(pos))
    def closeEvent(self,event):self.player.stop();super().closeEvent(event)


# Compat: código/testes antigos importavam LibraryDialog. Hoje é um painel
# encaixável (não-modal) para permitir arrastar recursos para a timeline.
LibraryDialog = LibraryPanel
