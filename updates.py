"""Canal de atualização — o que faz o app receber conteúdo novo sem reinstalar.

O app lê um MANIFESTO remoto (JSON) que lista pacotes — efeitos sonoros,
presets, ícones, LUTs, estilos — e baixa os que ainda não tem. É o motor de
"app sempre atualizado". O manifesto e os arquivos vão ser hospedados no
DS HUB (Cloudflare), então este mesmo canal é a ponte com o painel.

O download é INJETADO (parâmetro `fetch`/`download`): assim a lógica de
"o que é novo" e "instalar" roda em teste sem rede. A camada de rede real
(`live_fetch`) fica isolada no fim.
"""
import json
from urllib.parse import urlparse
import library

# Onde o manifesto vai morar. Placeholder até o DS HUB publicar o catálogo —
# enquanto for isto, "Buscar novidades" avisa que ainda não há canal, sem erro.
MANIFEST_URL = 'https://social-media-painel.pages.dev/studio/catalogo.json'

# Só http(s): um manifesto não pode mandar o app abrir file:// nem outro esquema.
_ALLOWED_SCHEMES = {'http', 'https'}


def parse_manifest(data):
    """Valida a forma do manifesto e devolve a lista de pacotes.

    Rejeitar aqui o que está torto evita que um manifesto mal publicado quebre
    o app do editor — a atualização falha com aviso, não com tela de erro.
    """
    if isinstance(data, (bytes, str)):
        data = json.loads(data)
    if not isinstance(data, dict) or not isinstance(data.get('packs'), list):
        raise ValueError('Manifesto inválido: falta a lista de pacotes.')
    packs = []
    for p in data['packs']:
        if not isinstance(p, dict) or not p.get('id') or not p.get('kind') or not p.get('title'):
            raise ValueError('Pacote sem id, tipo ou título.')
        if p['kind'] == 'Presets':
            library.validate_preset(p.get('preset', {}))  # preset embutido tem de ser válido
        else:
            if p['kind'] not in library.EXTENSIONS:
                raise ValueError(f"Tipo de pacote desconhecido: {p['kind']}.")
            ext = str(p.get('ext', '')).lower()
            if ext not in library.EXTENSIONS[p['kind']]:
                raise ValueError(f"Extensão inválida para {p['kind']}: {ext or 'ausente'}.")
            scheme = urlparse(str(p.get('url', ''))).scheme
            if scheme not in _ALLOWED_SCHEMES:
                raise ValueError('Pacote de arquivo sem URL http(s) válida.')
        packs.append(p)
    return packs


def new_packs(catalog, packs):
    """Só os pacotes que o acervo ainda não tem — a atualização é incremental,
    e reinstalar o que já existe seria baixar à toa e duplicar."""
    have = catalog.installed_ids()
    return [p for p in packs if p['id'] not in have]


def install(catalog, pack, download):
    """Instala um pacote. `download(url) -> bytes` é injetado para testar sem rede.

    Preset não baixa nada (vem embutido no manifesto). Arquivo é baixado e
    guardado no acervo local, marcado como vindo de atualização.
    """
    if pack['kind'] == 'Presets':
        return catalog.add_update_preset(pack)
    data = download(pack['url'])
    if not data:
        raise ValueError('Download vazio: ' + pack['title'])
    return catalog.add_update_asset(pack, data)


def sync(catalog, fetch=None, download=None):
    """Aplica todas as novidades. Devolve quantos entraram e eventuais falhas.

    Falha de um pacote não derruba os outros: um arquivo fora do ar não pode
    impedir os demais de chegar. Cada erro é reportado, não engolido.
    """
    fetch = fetch or live_fetch
    download = download or live_fetch
    packs = parse_manifest(fetch(MANIFEST_URL))
    pending = new_packs(catalog, packs)
    added, errors = [], []
    for p in pending:
        try:
            added.append(install(catalog, p, download))
        except Exception as exc:  # noqa: BLE001 — cada pacote é independente
            errors.append((p.get('title', p.get('id', '?')), str(exc)))
    return dict(added=len(added), total=len(packs), errors=errors)


# ── Camada de rede real (isolada, para o resto ser testável offline) ────────
def live_fetch(url, timeout=20):
    import urllib.request
    req = urllib.request.Request(url, headers={'User-Agent': 'KaiqueStudio'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()
