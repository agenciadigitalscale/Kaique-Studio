"""Ponte de fluxo com o DS HUB (o painel web da agência).

Duas direções: (1) PUXAR a fila de edição — os cards que estão em produção,
para o editor não precisar abrir o painel para saber o que editar; (2) ENTREGAR
o export — avisar o painel que o vídeo ficou pronto.

A rede é INJETADA (parâmetro `fetch`/`deliver`), exatamente como no `updates.py`:
a lógica de "o que fazer com a resposta" roda em teste sem o painel no ar. A
camada de rede real fica isolada no fim. Nada de segredo no código — a URL do
painel é configurável e a autenticação (quando existir) vem de fora.
"""
import json
from urllib.parse import urljoin

# Onde o painel vive. Mesmo host do canal de atualização (studio-catalog).
DEFAULT_BASE = 'https://social-media-painel.pages.dev'


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


def fetch_queue(base=DEFAULT_BASE, fetch=None):
    """Puxa e normaliza a fila. `fetch(url) -> bytes` injetável para teste."""
    fetch = fetch or live_fetch
    return parse_queue(fetch(urljoin(base + '/', 'api/studio-queue')))


def deliver(task, link, base=DEFAULT_BASE, post=None):
    """Entrega o export ao painel. `post(url, body_bytes) -> bytes` injetável."""
    post = post or live_post
    body = json.dumps(delivery_payload(task, link)).encode('utf-8')
    return post(urljoin(base + '/', 'api/studio-deliver'), body)


# ── Rede real (isolada, para o resto ser testável offline) ──────────────────
def live_fetch(url, timeout=20):
    import urllib.request
    req = urllib.request.Request(url, headers={'User-Agent': 'KaiqueStudio'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def live_post(url, body, timeout=20):
    import urllib.request
    req = urllib.request.Request(url, data=body, method='POST',
                                 headers={'User-Agent': 'KaiqueStudio', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()
