"""Ponte de fluxo com o DS HUB (o painel web da agência).

Duas direções: (1) PUXAR a fila de edição — os cards que estão em produção,
para o editor não precisar abrir o painel para saber o que editar; (2) ENTREGAR
o export — avisar o painel que o vídeo ficou pronto.

A rede é INJETADA (parâmetro `fetch`/`deliver`), exatamente como no `updates.py`:
a lógica de "o que fazer com a resposta" roda em teste sem o painel no ar. A
camada de rede real fica isolada no fim. Nada de segredo no código — a URL do
painel é configurável e a autenticação (quando existir) vem de fora.
"""
import json, unicodedata
from pathlib import Path
from urllib.parse import urljoin


def _sortkey(s):
    """Chave de ordenação A–Z que ignora maiúsculas e acentos (coração ~ coracao)."""
    return ''.join(c for c in unicodedata.normalize('NFD', (s or '').lower())
                   if unicodedata.category(c) != 'Mn')


def group_queue(tasks, by='cliente'):
    """Organiza a fila para exibição. Devolve linhas prontas para a UI desenhar:
    `('header', rótulo, contagem)` e `('item', tarefa)`.

    - 'cliente': agrupa por cliente (A–Z), com os cards de cada um em ordem de
      título. É o que transforma 180 itens soltos em algo navegável.
    - 'titulo': lista única, todos os cards em ordem de título (sem cabeçalhos).
    A decisão de ordem/agrupamento fica aqui, testável sem Qt.
    """
    if by == 'titulo':
        return [('item', t) for t in sorted(tasks, key=lambda t: (_sortkey(t['titulo']), _sortkey(t['cliente'])))]
    groups = {}
    for t in tasks:
        groups.setdefault(t['cliente'] or 'Sem cliente', []).append(t)
    rows = []
    for cliente in sorted(groups, key=_sortkey):
        items = sorted(groups[cliente], key=lambda t: _sortkey(t['titulo']))
        rows.append(('header', cliente, len(items)))
        for t in items:
            rows.append(('item', t))
    return rows

# Onde o painel vive. Mesmo host do canal de atualização (studio-catalog).
DEFAULT_BASE = 'https://social-media-painel.pages.dev'


def config_path(state):
    return Path(state) / 'dshub.json'


def load_config(state):
    """URL do painel e chave do Studio, guardadas na máquina do editor (nunca no
    código nem no repositório). Arquivo ausente/corrompido cai nos padrões."""
    p = config_path(state)
    if p.exists():
        try:
            d = json.loads(p.read_text(encoding='utf-8'))
            return dict(base=(d.get('base') or DEFAULT_BASE), key=str(d.get('key', '')))
        except Exception:  # noqa: BLE001 — config ruim não pode travar o app
            pass
    return dict(base=DEFAULT_BASE, key='')


def save_config(state, base, key):
    config_path(state).write_text(
        json.dumps(dict(base=(base or DEFAULT_BASE).strip(), key=(key or '').strip())),
        encoding='utf-8')
    return load_config(state)


def parse_queue(data):
    """Normaliza a resposta de GET /api/studio-queue numa lista de tarefas
    `{card_id, cliente, titulo, selo}`.

    Item torto é DESCARTADO (não derruba a fila inteira) — um card mal formado no
    painel não pode impedir o editor de ver os outros. Forma totalmente inválida
    levanta erro, para a UI avisar "não consegui ler a fila".
    """
    if isinstance(data, (bytes, str)):
        data = json.loads(data)
    if not isinstance(data, dict) or not isinstance(data.get('queue'), list):
        raise ValueError('Resposta de fila inválida do DS HUB.')
    out = []
    for it in data['queue']:
        if not isinstance(it, dict) or not it.get('card_id') or not it.get('titulo'):
            continue
        out.append(dict(card_id=str(it['card_id']), cliente=str(it.get('cliente', '')),
                        titulo=str(it['titulo']), selo=str(it.get('selo', ''))))
    return out


def export_name(task):
    """Nome de export que a esteira do DS HUB reconhece: `Cliente - Título [SELO]`.

    Vai SEM extensão de propósito — o campo de nome do CapCut põe a dele, e colar
    '.mp4' aqui geraria 'arquivo.mp4.mp4'. O selo é o que deixa a esteira casar o
    arquivo com o card automaticamente.
    """
    base = f"{task.get('cliente', '')} - {task['titulo']}".strip(' -')
    selo = task.get('selo', '')
    return f"{base} [{selo}]" if selo else base


def delivery_payload(task, link):
    """Corpo do POST /api/studio-deliver: qual card foi entregue e onde está o vídeo."""
    if not link:
        raise ValueError('Informe o link ou caminho do vídeo exportado.')
    return dict(card_id=task['card_id'], link=link, source='kaique-studio')


def fetch_queue(base=DEFAULT_BASE, fetch=None, key=None):
    """Puxa e normaliza a fila. `fetch(url, key) -> bytes` injetável para teste."""
    fetch = fetch or live_fetch
    return parse_queue(fetch(urljoin(base + '/', 'api/studio-queue'), key))


def deliver(task, link, base=DEFAULT_BASE, post=None, key=None):
    """Entrega o export ao painel. `post(url, body_bytes, key) -> bytes` injetável."""
    post = post or live_post
    body = json.dumps(delivery_payload(task, link)).encode('utf-8')
    return post(urljoin(base + '/', 'api/studio-deliver'), body, key)


def _headers(key):
    # O Studio se identifica pela chave (X-Studio-Key), configurada na máquina do
    # editor — nunca no código. Sem chave, o painel responde 401 (guarda ligada).
    h = {'User-Agent': 'KaiqueStudio'}
    if key:
        h['X-Studio-Key'] = key
    return h


# ── Rede real (isolada, para o resto ser testável offline) ──────────────────
def live_fetch(url, key=None, timeout=20):
    import urllib.request
    req = urllib.request.Request(url, headers=_headers(key))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def live_post(url, body, key=None, timeout=20):
    import urllib.request
    h = _headers(key); h['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=body, method='POST', headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()
