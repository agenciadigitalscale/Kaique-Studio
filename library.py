"""Núcleo da biblioteca de recursos — sem Qt, para poder ser testado sem interface.

A parte visual (LibraryDialog) fica em `resource_library.py`, que reexporta daqui.
Antes tudo morava junto e importava PySide6 no topo: a lógica do acervo não podia
rodar em teste sem a interface gráfica, e a biblioteca é o coração do produto.
"""
import copy, json, shutil, uuid
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


# ── Identidade visual do acervo: emojis por tipo e categoria ────────────────
# Cada recurso ganha um ícone para ser reconhecido de relance — a lista deixa de
# ser texto puro e vira algo escaneável, que é o pedido do dono do produto.
KIND_EMOJI = {
    'Memes': '😂', 'Efeitos sonoros': '🔊', 'Músicas': '🎵', 'Ícones': '🔷',
    'Imagens': '🖼️', 'LUTs': '🎨', 'Transições': '🎞️', 'Filtros': '✨', 'Presets': '🎯',
}
CATEGORY_EMOJI = {
    'Humor': '😂', 'Reações': '😲', 'Suspense': '😱', 'Impacto': '💥', 'Movimento': '💨',
    'Interface': '🖱️', 'Ambiente': '🌆', 'Gastronomia': '🍕', 'Natureza': '🌿',
    'Institucional': '🏢', 'Cinemático': '🎬', 'Outros': '📦',
}
# Ordem de exibição: Presets primeiro (o "aplicar com um clique"), depois o áudio
# que se ouve, depois o visual. Tipo fora desta lista cai no fim, em ordem alfabética.
KIND_ORDER = ['Presets', 'Efeitos sonoros', 'Memes', 'Músicas', 'LUTs', 'Filtros', 'Transições', 'Ícones', 'Imagens']


def kind_emoji(kind):
    return KIND_EMOJI.get(kind, '•')


def category_emoji(category):
    return CATEGORY_EMOJI.get(category, '•')


def group_for_display(entries):
    """Agrupa os recursos por TIPO para a lista da biblioteca.

    Devolve uma sequência de linhas prontas para a UI, intercalando cabeçalhos
    e itens: `('header', kind, count)` e `('item', entry)`. A UI não decide
    ordem nem contagem — só desenha; assim a regra de organização fica testável
    sem Qt. Dentro de cada tipo, ordena por categoria e depois por título.
    """
    by_kind = {}
    for e in entries:
        by_kind.setdefault(e['kind'], []).append(e)
    ordered = [k for k in KIND_ORDER if k in by_kind]
    ordered += sorted(k for k in by_kind if k not in KIND_ORDER)
    rows = []
    for kind in ordered:
        items = sorted(by_kind[kind], key=lambda e: (e.get('category', ''), e['title'].lower()))
        rows.append(('header', kind, len(items)))
        for e in items:
            rows.append(('item', e))
    return rows


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
        ('Mixkit (livre)', 'https://mixkit.co/free-sound-effects/{q}/'),
        ('Uppbeat (livre)', 'https://uppbeat.io/search?q={q}'),
        ('SoundBible (livre)', 'https://soundbible.com/search.php?q={q}'),
        ('Zapsplat', 'https://www.zapsplat.com/?s={q}'),
    ],
    'Memes': [
        ('Myinstants', 'https://www.myinstants.com/pt/search/?name={q}'),
        ('Pixabay (livre)', 'https://pixabay.com/sound-effects/search/{q}/'),
        ('Tenor (GIF)', 'https://tenor.com/search/{q}-gifs'),
        ('Giphy (GIF)', 'https://giphy.com/search/{q}'),
        ('Imgflip (memes)', 'https://imgflip.com/memesearch?q={q}'),
    ],
    'Músicas': [
        ('Pixabay Music (livre)', 'https://pixabay.com/music/search/{q}/'),
        ('Free Music Archive', 'https://freemusicarchive.org/search?quicksearch={q}'),
        ('Mixkit Music (livre)', 'https://mixkit.co/free-stock-music/{q}/'),
        ('Uppbeat (livre)', 'https://uppbeat.io/search?q={q}'),
        ('Chosic (CC)', 'https://www.chosic.com/free-music/?keyword={q}'),
    ],
    'Ícones': [
        ('Flaticon', 'https://www.flaticon.com/search?word={q}'),
        ('Google Imagens (uso livre)', 'https://www.google.com/search?tbm=isch&tbs=sur:fmc&q={q}'),
        ('Openverse (CC)', 'https://openverse.org/search/?q={q}'),
        ('SVG Repo (livre)', 'https://www.svgrepo.com/vectors/{q}/'),
        ('Iconfinder (grátis)', 'https://www.iconfinder.com/search?q={q}&price=free'),
        ('Icons8', 'https://icons8.com/icons/set/{q}'),
        ('The Noun Project', 'https://thenounproject.com/search/?q={q}'),
    ],
    'Imagens': [
        ('Google Imagens (uso livre)', 'https://www.google.com/search?tbm=isch&tbs=sur:fmc&q={q}'),
        ('Openverse (CC)', 'https://openverse.org/search/?q={q}'),
        ('Pixabay (livre)', 'https://pixabay.com/images/search/{q}/'),
        ('Unsplash (livre)', 'https://unsplash.com/s/photos/{q}'),
        ('Pexels (livre)', 'https://www.pexels.com/search/{q}/'),
        ('Burst (livre)', 'https://burst.shopify.com/photos/search?q={q}'),
    ],
    'LUTs': [
        ('FreshLUTs (grátis)', 'https://freshluts.com/luts?search={q}'),
        ('Lutify.me (grátis)', 'https://lutify.me/?s={q}'),
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
               'zoom', 'music_volume', 'captions_enabled',
               'caption_pos', 'caption_colors', 'caption_emojis']

_FILTERS = set(core.FILTERS)
_TRANSITIONS = set(core.TRANSITIONS)
_CAPTION_MODES = {'Palavra ativa', 'Palavras-chave', 'Frase'}
_CAPTION_STYLES = set(core.CAPTION_STYLES)
_CAPTION_POSITIONS = set(core.CAPTION_POSITIONS)
_CAPTION_COLOR_MODES = set(core.CAPTION_COLOR_MODES)


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
        if key == 'caption_pos' and value not in _CAPTION_POSITIONS:
            raise ValueError('Posição de legenda do preset inválida.')
        if key == 'caption_colors' and value not in _CAPTION_COLOR_MODES:
            raise ValueError('Modo de cor de legenda do preset inválido.')
        if key == 'caption_emojis' and not isinstance(value, bool):
            raise ValueError('O ajuste de emojis do preset deve ser verdadeiro ou falso.')


def apply_preset(style, preset):
    """Devolve uma CÓPIA de `style` com os ajustes do preset por cima.

    Não muda o `style` recebido: aplicar um preset é uma ação com desfazer no
    editor, e mutar o original tiraria o ponto de retorno.
    """
    validate_preset(preset)
    result = dict(style)
    result.update(preset['style'])
    return result


# ── Modelos prontos de LEGENDA ──────────────────────────────────────────────
# Cada modelo é um LOOK completo estilo "legenda dinâmica" do Envato: junta modo +
# animação + cor por palavra + posição + emoji + destaque num clique. O grupo é o
# que faz a legenda parecer editada à mão sem a pessoa acertar 8 controles.
CAPTION_TEMPLATES = [
    # — Virais / redes —
    {'name': '🔥 Viral com emoji', 'style': {'caption_mode': 'Palavra ativa', 'caption_style': 'Pop', 'font_size': 40, 'color': '#FFD24A', 'caption_colors': 'Única', 'caption_emojis': True, 'caption_pos': 'Embaixo', 'captions_enabled': True}},
    {'name': '🌈 Karaokê arco-íris', 'style': {'caption_mode': 'Palavra ativa', 'caption_style': 'Pulsar', 'font_size': 38, 'caption_colors': 'Arco-íris', 'caption_emojis': False, 'caption_pos': 'Embaixo', 'captions_enabled': True}},
    {'name': '⚡ Salto alternado', 'style': {'caption_mode': 'Palavra ativa', 'caption_style': 'Salto', 'font_size': 36, 'caption_colors': 'Alternada', 'color': '#FFD24A', 'caption_emojis': True, 'caption_pos': 'Embaixo', 'captions_enabled': True}},
    {'name': 'TikTok Pop', 'style': {'caption_mode': 'Palavra ativa', 'caption_style': 'Pop', 'font_size': 34, 'color': '#FFFFFF', 'caption_colors': 'Única', 'caption_pos': 'Embaixo', 'captions_enabled': True}},
    {'name': '💜 Neon da balada', 'style': {'caption_mode': 'Palavra ativa', 'caption_style': 'Neon pulsante', 'font_size': 36, 'color': '#29B6F6', 'caption_colors': 'Única', 'caption_pos': 'Meio', 'captions_enabled': True}},
    # — Impacto / título —
    {'name': '📦 Caixa em destaque', 'style': {'caption_mode': 'Palavra ativa', 'caption_style': 'Caixa', 'font_size': 34, 'color': '#FFD24A', 'caption_colors': 'Única', 'caption_pos': 'Embaixo', 'captions_enabled': True}},
    {'name': '🏆 Título gigante', 'style': {'caption_mode': 'Palavra ativa', 'caption_style': 'Contorno grosso', 'font_size': 46, 'color': '#FFFFFF', 'caption_colors': 'Única', 'caption_pos': 'Meio', 'captions_enabled': True}},
    {'name': 'Contorno forte', 'style': {'caption_mode': 'Palavra ativa', 'caption_style': 'Contorno', 'font_size': 32, 'caption_pos': 'Embaixo', 'captions_enabled': True}},
    {'name': 'Realce (destaque na cor)', 'style': {'caption_mode': 'Palavra ativa', 'caption_style': 'Realce', 'font_size': 30, 'caption_pos': 'Embaixo', 'captions_enabled': True}},
    # — Fala / conteúdo —
    {'name': '🎙️ Podcast no meio', 'style': {'caption_mode': 'Palavra ativa', 'caption_style': 'Realce', 'font_size': 28, 'caption_colors': 'Única', 'caption_pos': 'Meio', 'captions_enabled': True}},
    {'name': '⬆️ Emoji no topo', 'style': {'caption_mode': 'Palavra ativa', 'caption_style': 'Surgir', 'font_size': 32, 'caption_emojis': True, 'caption_pos': 'Em cima', 'captions_enabled': True}},
    {'name': '✨ Só palavras-chave', 'style': {'caption_mode': 'Palavras-chave', 'font_size': 34, 'caption_emojis': True, 'caption_pos': 'Meio', 'captions_enabled': True}},
    {'name': 'Frase cheia (legenda de fala)', 'style': {'caption_mode': 'Frase', 'caption_style': 'Sombra', 'font_size': 24, 'caption_pos': 'Embaixo', 'captions_enabled': True}},
    {'name': 'Clean minimalista', 'style': {'caption_mode': 'Frase', 'caption_style': 'Realce', 'font_size': 22, 'caption_colors': 'Única', 'color': '#FFFFFF', 'caption_pos': 'Embaixo', 'captions_enabled': True}},
    {'name': '📰 Notícia (frase pequena)', 'style': {'caption_mode': 'Frase', 'caption_style': 'Caixa', 'font_size': 20, 'caption_pos': 'Embaixo', 'captions_enabled': True}},
    {'name': 'Sem legenda', 'style': {'captions_enabled': False}},
]


# Tipo MIME do arraste de recurso (Biblioteca → timeline). Fica aqui, no núcleo
# sem Qt, para os dois lados (a lista que arrasta e a timeline que recebe) usarem
# a MESMA string — divergir faria o drop nunca casar.
RESOURCE_MIME = 'application/x-kaique-resource'


def apply_entry(project, entry, at_time=0.0, corner=None, width=180, overlay_len=3.0):
    """Aplica um recurso do acervo a um projeto (modelo plano), devolvendo uma CÓPIA.

    Não pergunta nada: quem chama passa tempo/canto. É a mesma lógica para o
    diálogo (que coleta com caixas de diálogo) e para o arraste-para-a-timeline
    (que deriva o tempo do X onde o recurso foi solto). Ter uma função só evita
    que o clique e o arraste apliquem coisas diferentes.
    """
    p = copy.deepcopy(project)
    kind = entry['kind']
    at = max(0.0, float(at_time))
    if kind in ('Memes', 'Efeitos sonoros'):
        p.setdefault('sfx', []).append(dict(path=entry['path'], time=at, volume=.7))
    elif kind == 'Músicas':
        p['music'] = entry['path']
    elif kind == 'LUTs':
        p['lut'] = entry['path']
    elif kind == 'Transições':
        p['transition'] = entry.get('value', p.get('transition', 'Nenhuma'))
    elif kind == 'Filtros':
        p['filter'] = entry.get('value', p.get('filter', 'Original'))
    elif kind == 'Presets':
        p = apply_preset(p, entry['preset'])
    elif kind in ('Ícones', 'Imagens'):
        p.setdefault('overlays', []).append(
            dict(path=entry['path'], start=at, end=at + overlay_len,
                 corner=corner or list(core.CORNERS)[0], width=width))
    else:
        raise ValueError('Este tipo de recurso não pode ser aplicado ao projeto.')
    return p


def caption_template_names():
    return [t['name'] for t in CAPTION_TEMPLATES]


def apply_caption_template(style, name):
    """Aplica um modelo de legenda pelo nome, devolvendo uma CÓPIA do style."""
    for t in CAPTION_TEMPLATES:
        if t['name'] == name:
            return apply_preset(style, t)
    raise ValueError('Modelo de legenda desconhecido.')


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
