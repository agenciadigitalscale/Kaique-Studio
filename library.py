"""Núcleo da biblioteca de recursos — sem Qt, para poder ser testado sem interface.

A parte visual (LibraryDialog) fica em `resource_library.py`, que reexporta daqui.
Antes tudo morava junto e importava PySide6 no topo: a lógica do acervo não podia
rodar em teste sem a interface gráfica, e a biblioteca é o coração do produto.
"""
import json, shutil, uuid
from pathlib import Path
from urllib.parse import urlencode
import core

# Tipos de recurso e categorias — a espinha de organização do acervo.
KINDS = ['Todos', 'Memes', 'Efeitos sonoros', 'Músicas', 'Ícones', 'Imagens', 'LUTs', 'Transições', 'Filtros', 'Presets']
CATEGORIES = ['Todas', 'Humor', 'Reações', 'Suspense', 'Impacto', 'Movimento', 'Interface',
              'Ambiente', 'Gastronomia', 'Natureza', 'Institucional', 'Cinemático', 'Outros']
AUDIO_EXT = {'.mp3', '.wav', '.m4a', '.aac', '.flac'}
IMG_EXT = {'.png', '.jpg', '.jpeg', '.webp'}
EXTENSIONS = {'Memes': AUDIO_EXT, 'Efeitos sonoros': AUDIO_EXT, 'Músicas': AUDIO_EXT,
              'Ícones': IMG_EXT, 'Imagens': IMG_EXT, 'LUTs': {'.cube'}}


def myinstants_url(query):
    return 'https://www.myinstants.com/pt/search/?' + urlencode({'name': query.strip() or 'mentira'})


# ── Busca online por tipo, em fontes de uso livre ──────────────────────────
# Cada fonte é um site que abre no NAVEGADOR com a busca pronta. O usuário
# baixa lá e importa aqui — nada é raspado nem baixado sem ele ver a licença.
# São fontes com conteúdo livre/CC de propósito: o material vai para vídeo de
# cliente, e usar áudio/imagem com direitos seria criar problema, não recurso.
from urllib.parse import quote as _quote

SOURCES = {
    'Efeitos sonoros': [
        ('Myinstants', 'https://www.myinstants.com/pt/search/?name={q}'),
        ('Pixabay (livre)', 'https://pixabay.com/sound-effects/search/{q}/'),
        ('Freesound (CC)', 'https://freesound.org/search/?q={q}'),
    ],
    'Memes': [
        ('Myinstants', 'https://www.myinstants.com/pt/search/?name={q}'),
        ('Pixabay (livre)', 'https://pixabay.com/sound-effects/search/{q}/'),
    ],
    'Músicas': [
        ('Pixabay Music (livre)', 'https://pixabay.com/music/search/{q}/'),
        ('Free Music Archive', 'https://freemusicarchive.org/search?quicksearch={q}'),
    ],
    'Ícones': [
        ('Flaticon', 'https://www.flaticon.com/search?word={q}'),
        ('Google Imagens (uso livre)', 'https://www.google.com/search?tbm=isch&tbs=sur:fmc&q={q}'),
        ('Openverse (CC)', 'https://openverse.org/search/?q={q}'),
    ],
    'Imagens': [
        ('Google Imagens (uso livre)', 'https://www.google.com/search?tbm=isch&tbs=sur:fmc&q={q}'),
        ('Openverse (CC)', 'https://openverse.org/search/?q={q}'),
        ('Pixabay (livre)', 'https://pixabay.com/images/search/{q}/'),
    ],
}


def sources_for(kind):
    """As fontes de busca de um tipo — [] quando o tipo não tem busca online
    (LUTs, Filtros, Transições, Presets são internos, não se baixam da web)."""
    return [name for name, _ in SOURCES.get(kind, [])]


def all_sources():
    """Todas as fontes numa lista, para um seletor de busca próprio — a busca
    online não depende do filtro do acervo local. Deduplica por URL: Pixabay
    aparece em tipos diferentes com destinos diferentes (sons × imagens), e cada
    destino distinto vira uma opção, rotulada pelo tipo."""
    seen = set()
    out = []
    for kind, lst in SOURCES.items():
        for name, template in lst:
            if template in seen:
                continue
            seen.add(template)
            out.append((kind, name))
    return out


def search_url(kind, query, source):
    """Monta a URL de busca de uma fonte para um termo.

    `%20` (via quote) em vez de `+`: serve tanto em caminho quanto em query, e
    todas as fontes aceitam — evita o `+` que só vale depois do `?`.
    """
    options = dict(SOURCES.get(kind, []))
    if source not in options:
        raise ValueError('Fonte de busca indisponível para este tipo.')
    term = query.strip()
    if not term:
        raise ValueError('Digite o que procurar.')
    return options[source].replace('{q}', _quote(term, safe=''))


# ── Presets ────────────────────────────────────────────────────────────────
# Um preset é um COMBO de estilo pronto — o "aplicar com um clique" do produto.
# Só mexe em valores simples (sem arquivo): filtro, transição, legenda, zoom.
# LUT e música continuam vindo como assets normais, porque são arquivos e o
# caminho depende da máquina.
PRESET_KEYS = ['filter', 'transition', 'color', 'font_size', 'caption_mode', 'caption_style',
               'zoom', 'music_volume', 'captions_enabled']

_FILTERS = set(core.FILTERS)
_TRANSITIONS = {'Nenhuma', 'Preto', 'Branco'}
_CAPTION_MODES = {'Palavra ativa', 'Palavras-chave', 'Frase'}
_CAPTION_STYLES = set(core.CAPTION_STYLES)


def validate_preset(preset):
    """Um preset só pode carregar chaves conhecidas e valores que o core aceita.

    Vem de JSON (bundled ou salvo pelo usuário): validar aqui evita que um preset
    torto só estoure lá no `core.validate`, na hora de exportar, sem explicar por quê.
    """
    if not preset.get('name', '').strip():
        raise ValueError('O preset precisa de um nome.')
    style = preset.get('style', {})
    if not isinstance(style, dict) or not style:
        raise ValueError('O preset não define nenhum ajuste.')
    for key, value in style.items():
        if key not in PRESET_KEYS:
            raise ValueError(f'O preset usa um ajuste desconhecido: {key}.')
        if key == 'filter' and value not in _FILTERS:
            raise ValueError('Filtro do preset inválido.')
        if key == 'transition' and value not in _TRANSITIONS:
            raise ValueError('Transição do preset inválida.')
        if key == 'caption_mode' and value not in _CAPTION_MODES:
            raise ValueError('Modo de legenda do preset inválido.')
        if key == 'caption_style' and value not in _CAPTION_STYLES:
            raise ValueError('Animação de legenda do preset inválida.')
        if key == 'font_size' and not 10 <= int(value) <= 50:
            raise ValueError('Tamanho de fonte do preset fora da faixa (10–50).')
        if key == 'zoom' and not 1 <= float(value) <= 1.3:
            raise ValueError('Zoom do preset fora da faixa (1–1.3).')
        if key == 'music_volume' and not 0 <= float(value) <= 1:
            raise ValueError('Volume de música do preset fora da faixa (0–1).')
        if key == 'color' and not __import__('re').fullmatch(r'#[0-9A-Fa-f]{6}', str(value)):
            raise ValueError('Cor do preset inválida.')


def apply_preset(style, preset):
    """Devolve uma CÓPIA de `style` com os ajustes do preset por cima.

    Não muda o `style` recebido: aplicar um preset é uma ação com desfazer no
    editor, e mutar o original tiraria o ponto de retorno.
    """
    validate_preset(preset)
    result = dict(style)
    result.update(preset['style'])
    return result


class Catalog:
    """Acervo local do usuário + os recursos que já vêm no aplicativo.

    Os itens que vêm no app (`assets/catalog.json`) têm caminho relativo à pasta
    do programa; os do usuário ficam em `%LOCALAPPDATA%\\KaiqueStudio\\biblioteca`
    com caminho absoluto. `items()` funde os dois já com caminho resolvido.
    """

    def __init__(self, root, bundled):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.file = self.root / 'catalogo.json'
        self.data = {'items': [], 'favorites': [], 'presets': []}
        if self.file.exists():
            stored = json.loads(self.file.read_text(encoding='utf-8'))
            # 'presets' nasceu depois; um catálogo antigo não o tem. Preencher em
            # vez de exigir migração deixa o acervo do usuário intacto.
            self.data = {'items': stored.get('items', []),
                         'favorites': stored.get('favorites', []),
                         'presets': stored.get('presets', [])}
        self.bundled = Path(bundled)
        self.defaults = json.loads((self.bundled / 'catalog.json').read_text(encoding='utf-8'))
        presets_file = self.bundled / 'presets.json'
        self.default_presets = json.loads(presets_file.read_text(encoding='utf-8')) if presets_file.exists() else []

    def items(self):
        defaults = []
        for entry in self.defaults:
            e = dict(entry)
            if e.get('path'):
                e['path'] = str((self.bundled / e['path']).resolve())
            defaults.append(e)
        return defaults + self.data['items']

    def presets(self):
        """Presets prontos do app + os que o usuário salvou. Cada um vira um item
        de biblioteca (kind='Presets') para caber na mesma lista e busca."""
        out = []
        for p in self.default_presets + self.data['presets']:
            out.append(dict(id=p['id'], title=p['name'], kind='Presets',
                            category=p.get('category', 'Outros'),
                            description=p.get('description', ''), preset=p))
        return out

    def save(self):
        core.atomic_json(self.file, self.data)

    def add(self, paths, kind, category):
        allowed = EXTENSIONS[kind]
        paths = [Path(p) for p in paths]
        if any(p.suffix.lower() not in allowed or not p.is_file() for p in paths):
            raise ValueError('Selecione arquivos compatíveis com o tipo escolhido.')
        new = []
        created = []
        try:
            for path in paths:
                identifier = uuid.uuid4().hex
                target = self.root / (identifier + path.suffix.lower())
                shutil.copyfile(path, target)
                created.append(target)
                new.append(dict(id=identifier, title=path.stem, kind=kind, category=category,
                                path=str(target.resolve())))
            self.data['items'].extend(new)
            self.save()
        except Exception:
            self.data['items'] = [e for e in self.data['items'] if e not in new]
            for path in created:
                path.unlink(missing_ok=True)
            raise
        return new

    def save_preset(self, name, style, category='Outros', description=''):
        """Guarda um combo de estilo como preset do usuário. Valida antes de gravar."""
        chosen = {k: style[k] for k in PRESET_KEYS if k in style}
        preset = dict(id=uuid.uuid4().hex, name=name.strip(), category=category,
                      description=description, style=chosen)
        validate_preset(preset)
        self.data['presets'].append(preset)
        self.save()
        return preset

    def remove_preset(self, identifier):
        """Remove um preset do USUÁRIO. Os que vêm no app não são apagáveis."""
        before = len(self.data['presets'])
        self.data['presets'] = [p for p in self.data['presets'] if p['id'] != identifier]
        if len(self.data['presets']) == before:
            raise ValueError('Este preset vem no aplicativo e não pode ser removido.')
        self.save()

    def favorite(self, identifier):
        favorites = self.data['favorites']
        if identifier in favorites:
            favorites.remove(identifier)
        else:
            favorites.append(identifier)
        self.save()

    # ── Recebimento de pacotes do canal de atualização ─────────────────────
    # O `updates.py` decide O QUE baixar; o Catalog é quem GRAVA. Os ids dos
    # pacotes convivem no mesmo espaço dos itens/presets: um pacote com id já
    # presente é considerado "já instalado" e não entra de novo.
    def installed_ids(self):
        """Todo id que o acervo já conhece — bundled, do usuário e de atualização.
        É a base do incremental: o que já está aqui não se rebaixa."""
        ids = set()
        for e in self.defaults + self.data['items']:
            ids.add(e.get('id'))
        for p in self.default_presets + self.data['presets']:
            ids.add(p.get('id'))
        return ids

    def add_update_asset(self, pack, data):
        """Grava o arquivo de um pacote (som, ícone, LUT…) no acervo do usuário.

        Igual ao `add`, mas a origem é o download e não um arquivo da máquina —
        por isso guarda `source='update'`: dá para distinguir na tela o que veio
        do canal do que o usuário importou à mão.
        """
        target = self.root / (pack['id'] + str(pack['ext']).lower())
        target.write_bytes(data)
        try:
            entry = dict(id=pack['id'], title=pack['title'], kind=pack['kind'],
                         category=pack.get('category', 'Outros'),
                         path=str(target.resolve()), source='update')
            self.data['items'].append(entry)
            self.save()
        except Exception:
            self.data['items'] = [e for e in self.data['items'] if e is not entry]
            target.unlink(missing_ok=True)
            raise
        return entry

    def add_update_preset(self, pack):
        """Instala um preset vindo do canal. O combo já veio embutido e validado
        no manifesto (`updates.parse_manifest`); aqui ele só entra no acervo."""
        preset = dict(pack['preset'])
        preset.setdefault('id', pack['id'])
        preset['source'] = 'update'
        self.data['presets'].append(preset)
        self.save()
        return preset
