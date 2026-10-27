#!/usr/bin/env python3
"""Gera HTML da revista a partir de markdown em conteudo/."""

from __future__ import annotations

import argparse
import html
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

import markdown
import yaml

CMS_DIR = Path(__file__).resolve().parent
ROOT = CMS_DIR.parent
MESES = (
    "",
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)

SECOES = (
    ("edicao", "Edição zero", "index.html"),
    ("manifesto", "Manifesto", "pecas/o-que-pode-a-critica.html"),
    ("critica", "Crítica", "pecas/index.html"),
    ("estudantina", "Estudantina", "estudantina/index.html"),
    ("clipping", "Clipping", "clipping/index.html"),
    ("sala", "Sala", "sala/index.html"),
    ("indicacoes", "Indicações", "indicacoes/index.html"),
    ("premios", "Prêmios", "premios/index.html"),
    ("equipes", "Equipes", "equipes.html"),
    ("colaborar", "Colaborar", "colaborar.html"),
    ("expediente", "Expediente", "expediente.html"),
)

LISTAGENS: dict[str, dict[str, str]] = {
    "pecas": {
        "eyebrow": "Crítica",
        "title": "Peças",
        "deck": (
            "O gesto em público. Cada texto é instrumento de leitura e, ao mesmo "
            "tempo, objeto histórico — candidato, também ele, a cânone."
        ),
        "description": "Peças de crítica da Revista Experimental de Crítica Literária.",
        "nav": "critica",
        "before": "",
        "after": (
            '<p class="prose">Aqui só entram textos da turma. O que a redação '
            'guardou de outros veículos está no <a href="../clipping/index.html">Clipping</a>.</p>\n'
            '<p class="prose">Quem escreve começa em '
            '<a href="../submeter.html">Submeter proposta</a> ou na '
            '<a href="../redacao.html">mesa da redação</a>. '
            "O texto só vai ao ar depois do editor responsável aceitar.</p>\n"
            '<p class="prose">Rascunhos ainda em elaboração ficam na '
            '<a href="../estudantina/index.html">Estudantina</a>.</p>\n'
        ),
    },
    "estudantina": {
        "eyebrow": "Bancada da turma",
        "title": "Estudantina",
        "deck": (
            "Colaborações ainda em fase embrionária. Cada nota registra o que já "
            "chegou à redação — título, gesto e estado — sem fingir peça acabada."
        ),
        "description": (
            "Estudantina: rascunhos e pautas da turma na Revista Experimental "
            "de Crítica Literária."
        ),
        "nav": "estudantina",
        "before": (
            '<p class="prose">Aqui entra o que ainda não está pronto para '
            "<em>Crítica</em> nem para <em>Indicações</em>. Quando o texto "
            "amadurece, sobe de seção. Enquanto isso, a bancada fica visível "
            "para a turma e para quem acompanha a edição zero.</p>\n"
        ),
        "after": (
            '<p class="prose">Quer acrescentar ou atualizar um rascunho? '
            'Envie pela página <a href="../submeter.html">Submeter proposta</a> '
            '(sem senha) ou pela <a href="../redacao.html">mesa da redação</a>. '
            'Cadastro, se ainda não fez: '
            '<a href="../colaborar.html">ficha editorial</a>.</p>\n'
        ),
    },
    "sala": {
        "eyebrow": "Diário da disciplina",
        "title": "Notas de sala",
        "deck": (
            "O que a turma já fez em público. Não é ata. Cada nota registra o "
            "gesto da manhã — e o que fica para a redação."
        ),
        "description": "Notas de sala da optativa Cânones da crítica internacional.",
        "nav": "sala",
        "before": "",
        "after": (
            '<p class="prose">O <a href="https://docs.google.com/document/d/'
            "1I5Ybu2rNf_n_gFVQfd7LbW5SNqcljrD9nsHUGacFt9o/edit\" "
            'rel="noopener noreferrer">plano de curso</a> traz o calendário '
            "das terças e é atualizado ao longo do semestre.</p>\n"
        ),
    },
    "indicacoes": {
        "eyebrow": "Redação",
        "title": "Indicações",
        "deck": (
            "Duas mesas. Uma vê; a outra ouve. Não são canais da revista: cada "
            "nota aponta um sinal fora da página e diz por que a crítica "
            "internacional precisa dele agora."
        ),
        "description": "Indicações da Revista Experimental de Crítica Literária.",
        "nav": "indicacoes",
        "before": """<div class="galeria-hub">
      <a href="../videos/index.html">
        <p class="eyebrow">Tela</p>
        <h2>Galeria de vídeos</h2>
        <p>Atila Iamarino e Miguel Nicolelis. A glosa é da redação; o original continua no YouTube.</p>
      </a>
      <a href="../podcasts/index.html">
        <p class="eyebrow">Ouvido</p>
        <h2>Galeria de podcasts</h2>
        <p>Episódios do 451 MHz em que a crítica literária é o objeto — o veículo-modelo, no ouvido.</p>
      </a>
    </div>
    <p class="section-label">Na mesa</p>
""",
        "after": "",
    },
}

EQUIPES = (
    ("america-do-sul", "América do Sul",
     "Português e espanhol em primeiro plano. Suplementos, revistas independentes, "
     "universidades, o que circula como valor aqui perto."),
    ("america-do-norte", "América do Norte",
     "NYRB, n+1, magazines universitários, a indústria do review em inglês — e o que "
     "essa indústria deixa de fora."),
    ("europa", "Europa",
     "O arquivo vivo: TLS, NRF, revistas alemãs, italianas, ibéricas. Herança que o "
     "curso lê e, ao mesmo tempo, historiciza."),
    ("africa", "África",
     "Crítica em inglês, francês, português e árabe. Revistas pan-africanas, imprensa "
     "de Lagos, Joanesburgo, Dacar, Maputo, Cairo."),
    ("asia", "Ásia",
     "Do Japão à Índia, da China ao mundo árabe asiático: onde o cânone ocidental "
     "encontra outras máquinas de valor."),
    ("oceania", "Oceania",
     "Austrália, Aotearoa, Pacífico. Equipe ainda em formação — vaga aberta no cadastro."),
)

MD = markdown.Markdown(extensions=["extra", "sane_lists", "smarty"])


def site_dir() -> Path:
    if (ROOT / "site" / "conteudo").is_dir():
        return ROOT / "site"
    return ROOT


def split_front_matter(text: str) -> tuple[dict[str, Any], str]:
    text = text.lstrip("\ufeff")
    if not text.startswith("---"):
        return {}, text
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.DOTALL)
    if not match:
        return {}, text
    meta = yaml.safe_load(match.group(1)) or {}
    if not isinstance(meta, dict):
        raise ValueError("front matter precisa ser um mapa YAML")
    return meta, match.group(2)


def data_iso(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if value is None:
        return ""
    text = str(value).strip()
    return text[:10] if re.match(r"\d{4}-\d{2}-\d{2}", text) else text


def data_curta(iso: str) -> str:
    if not re.match(r"\d{4}-\d{2}-\d{2}", iso or ""):
        return iso or ""
    _year, month, day = iso.split("-")[:3]
    return f"{int(day):02d} de {MESES[int(month)]}"


def data_longa(iso: str) -> str:
    curta = data_curta(iso)
    if not re.match(r"\d{4}-\d{2}-\d{2}", iso or ""):
        return curta
    return f"{curta} de {iso[:4]}"


def prefix_for(out_path: Path, site: Path) -> str:
    depth = len(out_path.parent.relative_to(site).parts)
    if depth <= 0:
        return ""
    return "../" * depth


def nav_html(prefix: str, current: str) -> str:
    links = []
    for key, label, href in SECOES:
        current_attr = ' aria-current="page"' if key == current else ""
        links.append(f'<a href="{prefix}{href}"{current_attr}>{label}</a>')
    return "\n      ".join(links)


def footer_nav_html(prefix: str) -> str:
    links = [f'<a href="{prefix}{href}">{label}</a>' for _, label, href in SECOES]
    return "\n          ".join(links)


def chrome(title: str, description: str, prefix: str, current: str, main: str) -> str:
    title_esc = html.escape(title)
    desc_esc = html.escape(description)
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{desc_esc}">
  <title>{title_esc} — Revista Experimental de Crítica Literária</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,400..800;1,14..32,400..700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{prefix}css/site.css">
</head>
<body>
  <a class="skip" href="#conteudo">Ir ao conteúdo</a>
  <div class="wrap">
    <header class="site-head">
      <div class="kicker-bar">
        <a class="kicker-logo" href="https://www.ufes.br/" rel="noopener noreferrer">
          <img src="{prefix}img/marca-ufes-header.svg" alt="UFES — Universidade Federal do Espírito Santo" width="104" height="57">
        </a>
        <p class="kicker-text">
          <span class="kicker-title">Cânones da crítica internacional</span>
          <span class="kicker-meta">UFES · Departamento de Letras · T01 · 2026/2</span>
        </p>
      </div>
      <div class="masthead">
        <div class="masthead-brand">
          <a class="wordmark" href="{prefix}index.html">Revista Experimental <span>de Crítica Literária</span></a>
          <p class="tagline">{{ a revista da turma }}</p>
        </div>
        <p class="masthead-issue"><strong>00</strong><span>Edição zero · agosto a dezembro de 2026</span></p>
      </div>
      <nav class="sections" aria-label="Seções">
      {nav_html(prefix, current)}
      </nav>
    </header>
    <main id="conteudo">

{main}
    </main>
  </div>
  <footer class="site">
    <div class="wrap footer-inner">
      <div class="footer-col">
        <p class="footer-wordmark">Revista Experimental de Crítica Literária</p>
        <p>Órgão da optativa Cânones da crítica internacional. Universidade Federal do Espírito Santo · Departamento de Letras.</p>
      </div>
      <div class="footer-col">
        <p class="footer-label">Seções</p>
        <nav aria-label="Rodapé">
          {footer_nav_html(prefix)}
        </nav>
      </div>
      <div class="footer-col">
        <p class="footer-label">Redação</p>
        <div class="footer-links">
          <a href="{prefix}colaborar.html">Cadastro editorial</a>
          <a href="{prefix}submeter.html">Submeter proposta</a>
          <a href="{prefix}redacao.html">Mesa da redação</a>
          <a href="https://docs.google.com/document/d/1I5Ybu2rNf_n_gFVQfd7LbW5SNqcljrD9nsHUGacFt9o/edit" rel="noopener noreferrer">Plano de curso</a>
          <a href="mailto:orlando.albertino@ufes.br">orlando.albertino@ufes.br</a>
        </div>
      </div>
    </div>
    <div class="wrap">
      <p class="footer-legal">UFES · DLL · T01 · 2026/2 · Vitória, ES · © <span id="ano">2026</span></p>
    </div>
  </footer>
  <script src="{prefix}js/site.js"></script>
</body>
</html>
"""


def render_markdown(body: str) -> str:
    stripped = body.strip()
    if not stripped:
        return ""
    if stripped.startswith("<") and not stripped.startswith("<http"):
        return stripped
    MD.reset()
    html_body = add_external_rel(MD.convert(stripped))
    return embed_inline_videos(html_body)


YOUTUBE_P = re.compile(
    r'<p><a href="https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})(?:[^"]*)"[^>]*>.*?</a></p>',
    re.I,
)


def embed_inline_videos(body_html: str) -> str:
    def repl(match: re.Match[str]) -> str:
        return video_block({"youtube": match.group(1), "title": "Vídeo"})

    return YOUTUBE_P.sub(repl, body_html)


def add_external_rel(text: str) -> str:
    def _rel(match: re.Match[str]) -> str:
        tag = match.group(0)
        if "rel=" in tag:
            return tag
        return tag[:-1] + ' rel="noopener noreferrer">'

    return re.sub(r'<a href="https?://[^"]+"[^>]*>', _rel, text)


def video_block(meta: dict[str, Any]) -> str:
    video_id = str(meta.get("youtube") or "").strip()
    if not video_id:
        return ""
    title = html.escape(str(meta.get("youtube_title") or meta.get("title") or "Vídeo"))
    credit = html.escape(str(meta.get("video_credit") or ""))
    origin = html.escape(str(meta.get("origem") or f"https://youtu.be/{video_id}"), quote=True)
    credit_html = f'\n      <p class="video-credit">{credit}</p>' if credit else ""
    return f"""      <figure class="video-frame">
        <iframe src="https://www.youtube-nocookie.com/embed/{html.escape(video_id, quote=True)}" title="{title}" allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen loading="lazy"></iframe>
      </figure>{credit_html}
"""


def inject_video(body_html: str, meta: dict[str, Any]) -> str:
    block = video_block(meta)
    if not block or "youtube-nocookie.com/embed/" in body_html:
        return body_html
    parts = body_html.split("</p>", 1)
    if len(parts) == 2:
        return parts[0] + "</p>\n" + block + parts[1]
    return block + body_html


def load_entries(folder: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not folder.is_dir():
        return entries
    for path in sorted(folder.glob("*.md")):
        meta, body = split_front_matter(path.read_text(encoding="utf-8"))
        meta = dict(meta)
        meta["_path"] = path
        meta["_slug"] = path.stem
        meta["_body"] = body
        meta["date"] = data_iso(meta.get("date"))
        entries.append(meta)
    entries.sort(key=lambda e: e["_slug"])
    entries.sort(key=lambda e: int(e.get("ordem") or 99))
    entries.sort(key=lambda e: e.get("date") or "", reverse=True)
    return entries


def cover_block(entry: dict[str, Any], prefix: str) -> str:
    cover = str(entry.get("cover") or "").strip()
    if not cover:
        return ""
    alt = str(entry.get("cover_alt") or entry.get("title") or "").strip()
    credit = str(entry.get("cover_credit") or "").strip()
    credit_html = (
        f'\n      <p class="cover-credit">{html.escape(credit)}</p>' if credit else ""
    )
    src = html.escape(f"{prefix}img/{cover}", quote=True)
    return f"""    <figure class="piece-cover">
      <img src="{src}" alt="{html.escape(alt)}" width="960" height="960" loading="lazy">{credit_html}
    </figure>
"""


def piece_html(entry: dict[str, Any], prefix: str) -> str:
    title = str(entry.get("title") or entry["_slug"])
    eyebrow = str(entry.get("eyebrow") or "")
    deck = str(entry.get("deck") or "")
    byline = str(entry.get("byline") or "")
    body_html = inject_video(render_markdown(entry["_body"]), entry)
    situacao = str(entry.get("situacao") or "")
    fonte = str(entry.get("fonte") or "")
    ficha = ""
    if situacao:
        link = (
            f' · <a href="{html.escape(fonte, quote=True)}" rel="noopener noreferrer">lista oficial</a>'
            if fonte
            else ""
        )
        ficha = f'\n      <p class="premio-situacao">{html.escape(situacao)}{link}</p>'
    main = f"""    <header class="piece-head">
      <p class="eyebrow">{html.escape(eyebrow)}</p>
      <h1>{html.escape(title)}</h1>
      <p class="deck">{inline(deck)}</p>
      <p class="byline">{byline_html(byline)}</p>{ficha}
    </header>
{cover_block(entry, prefix)}
    <div class="prose">
{body_html}
    </div>
"""
    description = str(entry.get("description") or deck or title).replace("*", "")
    nav = str(entry.get("nav") or "")
    return chrome(title, description, prefix, nav, main)


def inline(text: str) -> str:
    return re.sub(r"\*([^*]+)\*", r"<em>\1</em>", html.escape(text))


def byline_html(byline: str) -> str:
    """Nome do autor em negrito; o restante (ex.: · rascunho) fica normal."""
    text = byline.strip()
    if not text:
        return ""
    if " · " in text:
        nome, resto = text.split(" · ", 1)
        return (
            f"<strong>{html.escape(nome)}</strong>"
            f" · {html.escape(resto)}"
        )
    return f"<strong>{html.escape(text)}</strong>"


def note_row(
    entry: dict[str, Any],
    href: str,
    *,
    with_byline: bool = False,
    img_prefix: str = "",
) -> str:
    iso = entry.get("date") or ""
    kicker = str(entry.get("kicker") or entry.get("eyebrow") or "")
    resumo = str(entry.get("resumo") or entry.get("deck") or "")
    title = str(entry.get("title") or entry["_slug"])
    byline = str(entry.get("byline") or "").strip() if with_byline else ""
    byline_block = (
        f'\n          <p class="byline">{byline_html(byline)}</p>' if byline else ""
    )
    thumb = str(entry.get("thumb") or entry.get("cover") or "").strip()
    thumb_html = ""
    has_thumb = ""
    if thumb:
        alt = str(entry.get("cover_alt") or title).strip()
        src = html.escape(f"{img_prefix}img/{thumb}", quote=True)
        thumb_html = (
            f'\n        <img class="note-thumb" src="{src}" '
            f'alt="{html.escape(alt)}" width="240" height="240" loading="lazy">'
        )
        has_thumb = " has-thumb"
    return f"""      <article class="note-row{has_thumb}">
        <time datetime="{html.escape(iso)}">{html.escape(data_curta(iso))}</time>{thumb_html}
        <div>
          <p class="note-kicker">{html.escape(kicker)}</p>
          <h2><a href="{html.escape(href)}">{html.escape(title)}</a></h2>{byline_block}
          <p>{inline(resumo)}</p>
        </div>
      </article>"""


def listing_html(secao: str, entries: list[dict[str, Any]], prefix: str) -> str:
    info = LISTAGENS[secao]
    with_byline = secao == "estudantina"
    rows = [
        note_row(
            entry,
            f"{entry['_slug']}.html",
            with_byline=with_byline,
            img_prefix=prefix,
        )
        for entry in entries
    ]
    main = f"""    <header class="page-intro">
      <p class="eyebrow">{html.escape(info["eyebrow"])}</p>
      <h1 class="page-title">{html.escape(info["title"])}</h1>
      <p class="deck">{html.escape(info["deck"])}</p>
    </header>
    {info.get("before") or ""}<div class="notes">
{chr(10).join(rows)}
    </div>
    {info.get("after") or ""}"""
    return chrome(info["title"], info["description"], prefix, info["nav"], main)


def premios_html(entries: list[dict[str, Any]]) -> str:
    atalhos = []
    secoes = []
    for slug, nome, _descricao in EQUIPES:
        do_continente = sorted(
            (e for e in entries if str(e.get("equipe") or "").strip() == nome),
            key=lambda e: str(e.get("pais") or ""),
        )
        if not do_continente:
            continue
        atalhos.append(f'<a href="#{slug}">{html.escape(nome)}</a>')
        linhas = []
        for e in do_continente:
            linhas.append(
                f"""      <article class="note-row">
        <p class="premio-pais">{html.escape(str(e.get("pais") or ""))}</p>
        <div>
          <h2><a href="{html.escape(e['_slug'])}.html">{html.escape(str(e.get("title") or e["_slug"]))}</a></h2>
          <p>{inline(str(e.get("resumo") or e.get("deck") or ""))}</p>
          <p class="premio-linha">{html.escape(str(e.get("situacao") or ""))}</p>
        </div>
      </article>"""
            )
        secoes.append(
            f"""    <section class="continente" id="{slug}" aria-labelledby="{slug}-titulo">
      <header class="continente-head">
        <p class="eyebrow">Continente</p>
        <h2 id="{slug}-titulo">{html.escape(nome)}</h2>
      </header>
      <div class="notes">
{chr(10).join(linhas)}
      </div>
    </section>"""
        )
    main = f"""    <header class="page-intro">
      <p class="eyebrow">Redação</p>
      <h1 class="page-title">Prêmios</h1>
      <p class="deck">Os finalistas de 2026 dos maiores prêmios literários de cada país, com uma nota da redação para cada obra. Um prêmio é uma máquina de cânone: decide o que entra na conversa antes de a crítica chegar.</p>
    </header>

    <div class="prose">
      <p>As notas dizem o que cada obra propõe e o que júri e crítica destacaram, sempre com a fonte. Ninguém da turma leu ainda esses livros, e as notas não fingem leitura. Quando sai o vencedor, a página do prêmio é atualizada.</p>
    </div>

    <nav class="premios-atalhos" aria-label="Continentes">{" ".join(atalhos)}</nav>

{chr(10).join(secoes)}
    <p class="prose">Falta um país ou um prêmio? As <a href="../equipes.html">equipes</a> podem propor pela <a href="../redacao.html">mesa da redação</a>.</p>
"""
    return chrome(
        "Prêmios",
        "Finalistas 2026 dos maiores prêmios literários de cada país, comentados pela redação.",
        "../",
        "premios",
        main,
    )


def equipes_html(publicadas: list[tuple[str, dict[str, Any]]]) -> str:
    def da_equipe(nome: str) -> list[tuple[str, dict[str, Any]]]:
        return [(secao, e) for secao, e in publicadas if str(e.get("equipe") or "").strip() == nome]

    def contagem(n: int) -> str:
        if n == 0:
            return "Sem peça no ar ainda"
        return "1 peça no ar" if n == 1 else f"{n} peças no ar"

    cards = []
    secoes = []
    for slug, nome, descricao in EQUIPES:
        pecas = da_equipe(nome)
        titulo = f'<a href="#{slug}">{html.escape(nome)}</a>' if pecas else html.escape(nome)
        cards.append(
            f"""      <article class="team">
        <h3>{titulo}</h3>
        <p>{html.escape(descricao)}</p>
        <p class="team-count">{contagem(len(pecas))}</p>
      </article>"""
        )
        if not pecas:
            continue
        corpo = "\n".join(note_row(e, f"{secao}/{e['_slug']}.html") for secao, e in pecas)
        secoes.append(
            f"""    <section class="continente" id="{slug}" aria-labelledby="{slug}-titulo">
      <header class="continente-head">
        <p class="eyebrow">Equipe</p>
        <h2 id="{slug}-titulo">{html.escape(nome)}</h2>
      </header>
      <div class="notes">
{corpo}
      </div>
    </section>"""
        )
    main = f"""    <header class="page-intro">
      <p class="eyebrow">Monitoramento</p>
      <h1 class="page-title">Equipes de monitoramento de publicações de crítica literária</h1>
      <p class="deck">O mapa saiu de uma enquete no grupo da turma: não para cobrir o planeta, e sim para treinar o olho onde a crítica se publica — revistas, cadernos, newsletters, blogs, podcasts, prêmios, dossiês.</p>
    </header>

    <div class="prose">
      <p>Cada equipe devolve à redação o que viu: uma peça que importa, um gesto crítico reconhecível, uma ausência. O recorte continental é método, não destino. Os achados viram peça na <a href="redacao.html">mesa da redação</a>, e cada peça publicada aparece aqui, na seção da sua equipe.</p>
    </div>

    <div class="teams">
{chr(10).join(cards)}
    </div>

{chr(10).join(secoes)}
    <p class="prose"><a href="colaborar.html">Confirmar ou trocar de equipe no cadastro editorial →</a></p>
"""
    return chrome(
        "Equipes",
        "Equipes de monitoramento de publicações de crítica literária da revista experimental DLT13973.",
        "",
        "equipes",
        main,
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build(site: Path) -> int:
    content = site / "conteudo"
    n = 0
    publicadas: list[tuple[str, dict[str, Any]]] = []
    for secao in ("pecas", "estudantina", "sala", "indicacoes", "premios"):
        entries = load_entries(content / secao)
        if secao not in ("sala", "estudantina"):
            publicadas.extend((secao, e) for e in entries)
        dest = site / secao
        dest.mkdir(parents=True, exist_ok=True)
        for entry in entries:
            out = dest / f"{entry['_slug']}.html"
            write(out, piece_html(entry, prefix_for(out, site)))
            n += 1
        index = dest / "index.html"
        if secao == "premios":
            write(index, premios_html(entries))
        else:
            write(index, listing_html(secao, entries, prefix_for(index, site)))
        n += 1
        print(f"{secao}: {len(entries)} peças + índice", file=sys.stderr)
    publicadas.sort(key=lambda item: item[1].get("date") or "", reverse=True)
    write(site / "equipes.html", equipes_html(publicadas))
    n += 1
    print("equipes: página por continente", file=sys.stderr)
    return n


def main() -> int:
    parser = argparse.ArgumentParser(description="Monta o HTML editorial da revista.")
    parser.add_argument("--site", type=Path, default=None)
    args = parser.parse_args()
    site = args.site.resolve() if args.site else site_dir()
    if not (site / "conteudo").is_dir():
        print(f"não achei conteudo/ em {site}", file=sys.stderr)
        return 1
    n = build(site)
    print(f"ok {n} arquivos em {site}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
