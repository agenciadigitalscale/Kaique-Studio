# Kaique Studio

Editor de vídeo **desktop** para a Digital Scale — corte por transcrição, legendas
dinâmicas, biblioteca de recursos (sons, memes, LUTs, presets) e exportação para
Reels/Shorts. Feito em Python + Qt, roda na máquina do editor (não é web).

> Este README é para **quem desenvolve** (humanos e agentes de IA). Para o usuário
> final, veja `COMECE-AQUI.txt` e `PRODUTO.md`.

---

## Stack

- **Python 3.11** — nesta máquina o 3.11 responde por `py -3.11` (o `python` do PATH é alias inútil da Windows Store).
- **PySide6** (Qt) — interface desktop.
- **FFmpeg** via `imageio-ffmpeg` — corte, filtros, overlays, exportação.
- **faster-whisper** — transcrição (gera as palavras das legendas).
- **PyAV** (`av`) — leitura de mídia.

Dependências fixas em `requirements.txt`; extras de teste em `requirements-dev.txt`.

---

## Rodar

```bat
INSTALAR.bat   :: cria a .venv e instala as dependências (uma vez)
INICIAR.bat    :: abre o editor (app.py)
```

`DIAGNOSTICO.bat` checa o ambiente se algo não abrir.

> ⚠️ A janela Qt só pode ser julgada **abrindo o app** — nenhum teste "vê" a tela.
> Agentes: verifiquem por testes + exportações reais; o julgamento visual é humano.

---

## Testar

Rode **sempre pela python da .venv** (as deps pesadas — av/PySide6/ffmpeg — estão lá):

```bash
QT_QPA_PLATFORM=offscreen ./.venv/Scripts/python.exe -m unittest discover -p "test_*.py"
```

- `QT_QPA_PLATFORM=offscreen` deixa rodar sem display.
- **67 testes** hoje, incluindo **exportações reais de vídeo** (o teste que pega erro
  de FFmpeg de verdade — filter_complex, ASS animado).
- Lógica pura fica separada da UI de propósito: `library.py`, `core.py`, `native.py`,
  `updates.py` são testáveis sem Qt.
- **Não instancie a janela `Studio()` inteira em modo headless — trava.** Para conferir
  fiação de UI, importe o módulo + cheque atributos, ou instancie só um painel
  (ex.: `LibraryPanel`) com um `studio` falso.

---

## Arquitetura (mapa dos módulos)

| Arquivo | Papel |
|---|---|
| `core.py` | Motor **não-destrutivo**: projeto JSON plano, `validate`, `transcribe`, `render` (FFmpeg), `FILTERS`, `CAPTION_STYLES`, `CORNERS`, geração de ASS (`make_ass`). |
| `native.py` | Modelo **v5** de clipes independentes: cada take guarda tempos do arquivo original; `reorder`/`split`/trim/words preservam a fonte. `legacy(doc)` expõe o projeto no formato plano do `core`; `from_legacy` importa projetos 0.2–0.4. |
| `app.py` | Janela principal (`Studio`, um `QMainWindow`): lista de takes, player, timeline (arraste/drop), abas (Comandos/Cortes/Legendas/Imagem-áudio/Projeto). |
| `library.py` | **Núcleo da biblioteca, sem Qt**: `Catalog`, tipos/categorias, busca online livre (`SOURCES`/`search_url`), `Presets`, `CAPTION_TEMPLATES`, `apply_entry`, agrupamento com emojis (`group_for_display`). |
| `resource_library.py` | UI da biblioteca (`LibraryPanel`, encaixável): lista arrastável, botão direito, tocar no 1º clique. Só interface — a lógica vem de `library.py`. |
| `updates.py` | **Canal de atualização**: lê um manifesto remoto e baixa efeitos/presets/ícones novos sem reinstalar. Download injetável (testável offline). |
| `legacy_app.py` | Tema (QSS, cores, helpers `button`/`label`/`row`/`panel`) e classes reaproveitadas das versões antigas. |

### Conceitos que não são óbvios

- **Ponte `Studio.p`** — `app.py` guarda o projeto no modelo *native* (`self.doc`, com
  `clips` + `style`). A propriedade `self.p` expõe isso como projeto **plano** (via
  `native.legacy`) e o *setter* copia `STYLE_KEYS` de volta. É por essa ponte que a
  biblioteca aplica sons/LUTs/overlays/presets sem conhecer o modelo native.
- **`apply_entry` é a lógica ÚNICA** de "aplicar um recurso ao projeto" — usada pelo
  clique ("Usar no projeto") e pelo arraste-para-a-timeline. Não duplicar.
- **Legendas em ASS** — `core.make_ass` monta tags por estilo (`Realce`/`Pop`/`Contorno`).
  Editar essas strings com barras invertidas: **escreva um `.py` com raw strings**, nunca
  cole via heredoc de shell (a dupla camada de escaping quebra o match).
- **Canal ↔ DS HUB** — o manifesto do `updates.py` é servido pelo DS HUB em
  `GET /api/studio-catalog`. Publicar novidade = gravar a chave `sm_studio_catalog` lá,
  sem redeploy nem reinstalar o Studio.

---

## Convenções

- Lógica pura fora da UI — se dá pra testar sem Qt, mora em `core`/`native`/`library`/`updates`.
- Todo comportamento novo entra com **teste** (`test_*.py`); render real quando toca FFmpeg.
- Compatibilidade: projeto antigo tem de continuar abrindo (`from_legacy`, catálogo sem
  a chave `presets`, sticker legado virando overlay).
- Mensagens ao usuário em **português**, claras; erro de verdade aparece, nunca é maquiado.

---

## Trabalho colaborativo (vários agentes)

Repo **privado**. Codex e outros agentes trabalham através do **GitHub** (não conversam
direto — o ponto de encontro são os commits).

```bash
git pull        # SEMPRE antes de começar
# ... trabalhe, rode os testes ...
git push        # ao terminar
```

Se der conflito, resolva antes de seguir. Branch default: `master`.

---

## Estado atual e próximos passos

Feito: corte não-destrutivo, transcrição, legendas dinâmicas (3 estilos) + modelos
prontos, 12 filtros, múltiplos overlays, biblioteca agrupada com busca livre, presets,
**canal de atualização**, **arrastar recurso para a timeline**, menus de botão direito.

Próximos (ver `NOVIDADES.txt`): memes de **vídeo** como overlay (hoje overlay é imagem
estática), reprodução contínua sem "pulos" ao trocar de clipe, **ferramentas de IA**
(cortes/legenda inteligentes), e a **ponte com o DS HUB** (puxar fila de edição + entregar
o export na pasta Publicar).
