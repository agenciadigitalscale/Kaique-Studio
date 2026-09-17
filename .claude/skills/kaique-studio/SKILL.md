---
name: kaique-studio
description: >-
  Como trabalhar no Kaique Studio — o editor de vídeo desktop em Python
  (PySide6 + FFmpeg + faster-whisper) deste repositório. Use SEMPRE que a tarefa
  tocar em core.py / native.py / app.py / library.py / bridge.py, em filtros,
  transições, legendas (ASS), efeitos, galeria de prévias, exportação, o canal de
  novidades ou a ponte com o DS HUB — mesmo que o pedido não cite "Kaique Studio"
  pelo nome. Encapsula o ambiente (venv/py -3.11), como VERIFICAR sem ver a janela
  (app trava headless), as armadilhas de FFmpeg/ASS no Windows, e as receitas de
  "adicionar um efeito com teste de render de verdade".
---

# Kaique Studio — manual de trabalho

Editor de vídeo **desktop** (não é web). O dono é o Kaique (editor/Head da agência);
a visão dele é um app "estilo App Store, sempre inovando, top 1 Brasil". Vários
agentes mexem no repo (inclusive o Codex), então **dê `git pull` antes de começar**
e cuide de conflito.

## Por que este manual existe

Duas coisas tornam este projeto fácil de quebrar sem perceber:

1. **Você NÃO consegue ver a janela.** É um app Qt desktop; instanciar a janela
   inteira **trava** em ambiente headless. Então "funciona" aqui significa *passou
   nos testes + render real*, não *eu olhei e tá bonito*. O julgamento visual é do
   Kaique, abrindo o `INICIAR.bat`.
2. **Um filtro/efeito torto só aparece como erro na hora da exportação**, na cara do
   editor. Por isso **todo efeito novo precisa de um teste que renderize de verdade**
   — é o único jeito de o FFmpeg dizer se a string está certa.

## Ambiente e como rodar

- Python **3.11** — nesta máquina só responde por **`py -3.11`** (o `python`/`python3`
  do PATH são aliases inúteis da Windows Store). Há um **`.venv`** pronto com as deps
  pesadas (PySide6, av, faster-whisper, ffmpeg, pillow).
- FFmpeg vem do `imageio-ffmpeg` (via `core.ffmpeg()`); não depende de PATH.
- Rodar o app (só o Kaique, pra ver): `INICIAR.bat`. Instalar deps: `INSTALAR.bat`.

**Rodar os testes (sempre com `offscreen`, senão o Qt tenta abrir tela):**

```bash
QT_QPA_PLATFORM=offscreen ./.venv/Scripts/python.exe -m unittest discover -p "test_*.py"
```

A suíte é lenta (~2–4 min) porque muitos testes **renderizam vídeo de verdade** —
isso é uma qualidade, não um problema. Para um arquivo só:
`./.venv/Scripts/python.exe -m unittest test_preview -v`.

## Como VERIFICAR sem ver a janela

Em ordem, do mais barato ao mais completo:

1. **Compilar + importar** (pega erro de sintaxe/wiring do módulo inteiro):
   ```bash
   ./.venv/Scripts/python.exe -m py_compile app.py core.py
   QT_QPA_PLATFORM=offscreen ./.venv/Scripts/python.exe -c "import app; print('ok')"
   ```
   `import app` roda o corpo das classes (não o loop do app, que fica sob
   `if __name__=='__main__'`), então acusa `NameError`, import faltando, etc.

2. **Teste de render real** para lógica de FFmpeg/ASS (a única prova que pega
   filtro/transição/legenda torta). Ver as receitas abaixo.

3. **Smoke de QDialog isolado** para UI nova. Ao contrário da janela inteira, um
   `QDialog` isolado **pode** ser construído com `offscreen` + `QApplication([])` num
   script de scratchpad — ele renderiza de verdade e dá pra checar nº de widgets,
   handlers, etc. Exemplo (galeria de prévias):
   ```python
   import sys; sys.path.insert(0, r'<caminho-do-repo>')
   from PySide6.QtWidgets import QApplication, QGridLayout
   import core, app
   QApplication.instance() or QApplication([])
   dlg = app.EffectGalleryDialog(None, 'T', 'hint', list(core.FILTERS),
       lambda n,dest: core.preview_thumbnail('<take>.mp4', dest, vf=core.FILTERS[n], seconds=0.5),
       'filter')
   assert dlg.findChildren(QGridLayout)[0].count() == len(core.FILTERS)
   ```
   Rode com `QT_QPA_PLATFORM=offscreen`. Guarde o script no scratchpad, não no repo.

4. **Nunca** tente instanciar `app.Studio()` (a janela inteira) headless — trava.

## Mapa da arquitetura

| Arquivo | Papel |
|---|---|
| `core.py` | Motor: projeto JSON, `validate`, transcrição, **render FFmpeg** (`assemble`/`render`), `make_ass` (legendas), `preview_thumbnail`/`preview_transition`/`preview_caption` (miniaturas da galeria). `FILTERS`, `XFADE_MAP`/`TRANSITIONS`, `CAPTION_STYLES`, `EXPORT_PROFILES`, `ASPECT_CHOICES`/`QUALITY_CHOICES`. |
| `native.py` | Modelo v5 de **clipes independentes** (reorder/trim/split/words preservam os tempos do arquivo original). `render` monta a partir dos clipes; `legacy(p)` adapta para o formato antigo que o `core` consome. |
| `app.py` | UI Qt (`class Studio`). Combos leem de `core.FILTERS`/`TRANSITIONS`/`CAPTION_STYLES` via `addItems`. Player com auto-avanço entre clipes. `EffectGalleryDialog` (galeria genérica). |
| `library.py` | Núcleo da biblioteca **sem Qt** (presets, busca online, filtros duplicados p/ a UI). `resource_library.py` é só a casca Qt que reexporta. |
| `bridge.py` | Ponte com o DS HUB (puro, rede injetável): puxa a fila de edição, entrega o export. Config em `%LOCALAPPDATA%/KaiqueStudio/dshub.json`. |
| `updates.py` | Canal de novidades (baixa pacotes de um catálogo remoto). Sem Qt, download injetável p/ testar offline. |

## Receitas

### Adicionar um FILTRO
1. Em `core.py`, acrescente ao dict `FILTERS`: `'Nome amigável': 'string_vf_do_ffmpeg'`.
   Use só sintaxe que o FFmpeg empacotado aceita.
2. **Sincronize** a biblioteca: `library.py` mantém cópias (`FILTERS`/`_FILTERS`) —
   se um preset usa um nome de filtro, esse nome PRECISA existir em `FILTERS`.
3. A UI já pega sozinha (`self.look.addItems(core.FILTERS)`) e a **galeria também**.
4. Teste: `test_filters.py` já valida **cada** string no FFmpeg (`test_every_filter_string_is_accepted_by_ffmpeg`) e faz um render ponta a ponta. Rode-o; se
   quiser, some um caso ao `validate`.

### Adicionar uma TRANSIÇÃO (xfade)
1. Em `core.py`, acrescente ao `XFADE_MAP`: `'Nome ◀': 'tipo_real_do_xfade'`
   (`TRANSITIONS` deriva sozinho). **Só** entre tipos confirmados por render.
2. Teste: `test_transitions.py` renderiza cada tipo. A galeria (`preview_transition`)
   e `test_preview.py` cobrem a prévia.

### Adicionar um ESTILO DE LEGENDA
1. Em `core.py`, some o nome a `CAPTION_STYLES` e a tag ASS correspondente em
   `caption_active_tag(style, accent)` (técnicas padrão de animação: escala/rotação/
   contorno/brilho — nada copiado de template de terceiros; `accent` já vem no
   formato ASS `&Hbbggrr&`).
2. Teste: `test_preview.py::PreviewCaptionTests` renderiza **todos** os estilos; e os
   testes de legenda cobrem o `make_ass`.

### Adicionar uma miniatura/galeria nova
- Os motores de prévia vivem em `core.py` (`preview_thumbnail`, `preview_transition`,
  `preview_caption`) — determinísticos e testados por render.
- `app.EffectGalleryDialog` é **genérica**: `(parent, title, hint, names, render, slug, sig='')`.
  `render(name, dest)` desenha uma miniatura; `sig` é a assinatura das entradas para o
  **cache entre sessões** (`%LOCALAPPDATA%/KaiqueStudio/prev_cache`) — inclua no `sig`
  tudo que muda a imagem (take+mtime+tempo p/ filtro; cor p/ legenda; estático p/
  transição), senão o cache serve imagem velha.

## Armadilhas de FFmpeg / ASS / Windows (levam horas se pegarem você)

- **Caminho com `:` em filtro do FFmpeg** (LUT `.cube`, `subtitles=arquivo.ass`)
  quebra no Windows porque `:` separa argumentos de filtro. Solução comprovada:
  **copie o arquivo para um nome simples num diretório temporário e rode o FFmpeg
  com `cwd` nesse diretório**, referenciando só `look.cube` / `p.ass`
  (`core.run(args, cwd=tmp)`). É o que `assemble`, `preview_thumbnail` e
  `preview_caption` já fazem.
- **Editar código com barras invertidas (tags ASS `\c`, `\t`, `\fscx`...):** escreva
  o arquivo `.py` pelo editor com **raw strings** (`r'...'`), **nunca por heredoc de
  bash** — a dupla camada de escaping (bash + Python) corrompe o `\` e o match/tag
  sai errado sem erro aparente.
- **`-ss` como opção de ENTRADA vs SAÍDA importa.** Em câmera lenta (`setpts`), o
  `-t` precisa ser opção de entrada, senão o clipe é cortado antes de desacelerar.
  Ao mexer em tempo/velocidade, confira com render real.
- **A tabela `FILTERS` do `core` e as cópias em `library` têm de ficar em sincronia.**

## Fluxo de git (repo colaborativo)

- **`git pull` antes de trabalhar** (Codex e outros agentes empurram no `master`).
- Antes de commitar: **compile + import offscreen + suíte verde** (e render real do
  que você mexeu).
- Commit direto no `master` e `git push` (é o fluxo estabelecido do repo; identidade
  local: Digital Scale / agenciadigitalscale@gmail.com). Mensagens descritivas, no
  imperativo, explicando o **porquê**. Termine com a linha de atribuição do harness
  quando houver.
- Ao terminar: diga o que foi feito, **o que foi verificado** e **o que só o Kaique
  pode conferir na tela** (suavidade de player, estética) — sem fingir que viu.

## Visão do produto (para priorizar bem)

O dono quer **conteúdo sempre novo** (efeitos sonoros, legendas, ícones, filtros,
transições) entregue **sem reinstalar** (o canal de novidades, `updates.py` + catálogo
no DS HUB) e **ferramentas de IA** (cortes, legendas inteligentes — já há base local
grátis). A **ponte com o DS HUB** puxa a fila de edição e entrega o export. Ao propor
melhorias, prefira o que rende para essa visão e o que dá para **verificar por teste**.
