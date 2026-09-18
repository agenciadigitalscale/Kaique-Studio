"""Favoritos das galerias (filtros, transições, legendas) — a estrelinha do CapCut.

Puro e sem Qt: guarda por TIPO de galeria uma lista de nomes preferidos, num JSON
em %LOCALAPPDATA%/KaiqueStudio/favorites.json (fora do repo). O caminho é
injetável para os testes. Falha de leitura nunca derruba a galeria — favoritos
são conveniência, não dado crítico.
"""
import json
import os
from pathlib import Path


def store_path():
    base = Path(os.environ.get('LOCALAPPDATA') or os.environ.get('TMPDIR') or Path.home())
    return base / 'KaiqueStudio' / 'favorites.json'


def load(path=None):
    """Devolve {tipo: [nomes]} — {} quando não há arquivo ou está corrompido."""
    p = Path(path) if path else store_path()
    try:
        data = json.loads(p.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            return {k: [n for n in v if isinstance(n, str)]
                    for k, v in data.items() if isinstance(v, list)}
    except Exception:
        pass
    return {}


def save(data, path=None):
    p = Path(path) if path else store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')


def is_favorite(data, kind, name):
    return name in data.get(kind, [])


def toggle(data, kind, name):
    """Liga/desliga um favorito. Devolve (novo_dict, agora_é_favorito).

    Não muta o dict recebido — a galeria guarda o resultado.
    """
    favs = list(data.get(kind, []))
    if name in favs:
        favs.remove(name)
        on = False
    else:
        favs.append(name)
        on = True
    new = dict(data)
    new[kind] = favs
    return new, on


def ordered(names, favs):
    """Os `names` com os favoritos primeiro (preservando a ordem de `names`)."""
    fset = set(favs)
    return [n for n in names if n in fset] + [n for n in names if n not in fset]
