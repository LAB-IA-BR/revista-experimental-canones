"""SEO da revista: etiquetas de compartilhamento, canonical, dados estruturados,
sitemap.xml e robots.txt.

Roda no fim de cms/build.py (e pode rodar sozinho: python3 cms/seo.py).
É idempotente: o bloco gerado fica entre <!-- seo:inicio --> e <!-- seo:fim -->
e é substituído a cada execução.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

DOMINIO = "https://revistadecritica.labiaes.com.br"
NOME = "Revista Experimental de Crítica e Teoria Literária"
IMAGEM_PADRAO = "img/compartilhar.jpg"
IGNORAR = ("admin/", "cms/", "conteudo/", "node_modules/", ".github/")
FORA_DO_SITEMAP = ("404.html", "redacao.html", "redacao/")
SECOES_ARTIGO = ("pecas/", "estudantina/", "premios/", "indicacoes/", "sala/")
CONTADOR = "https://revistadecritica.goatcounter.com/count"
INICIO, FIM = "<!-- seo:inicio -->", "<!-- seo:fim -->"
BLOCO_RE = re.compile(re.escape(INICIO) + r".*?" + re.escape(FIM) + r"\n?", re.S)


def _redirecionamento(texto: str) -> bool:
    return "location.replace" in texto and len(texto) < 2000


def _url(rel: str) -> str:
    if rel == "index.html":
        return DOMINIO + "/"
    if rel.endswith("/index.html"):
        return f"{DOMINIO}/{rel[: -len('index.html')]}"
    return f"{DOMINIO}/{rel}"


def _titulo(texto: str) -> str:
    m = re.search(r"<title>(.*?)</title>", texto, re.S)
    t = html.unescape(m.group(1).strip()) if m else NOME
    t = re.sub(r"\s+—\s+" + re.escape(NOME) + r"$", "", t)
    return t


def _descricao(texto: str) -> str:
    m = re.search(r'<meta name="description" content="([^"]*)"', texto)
    return html.unescape(m.group(1)) if m else ""


def _imagem(texto: str, rel: str) -> str:
    """Primeira imagem de conteúdo (dentro de <main>) que seja local; senão a padrão."""
    main = texto.split("<main", 1)[-1]
    for src in re.findall(r'<img[^>]*src="([^"]+)"', main):
        if src.startswith(("http://", "https://", "data:")) or "marca-ufes" in src or "logo" in src:
            continue
        alvo = (Path(rel).parent / src).as_posix()
        partes: list[str] = []
        for p in alvo.split("/"):
            if p == "..":
                if partes:
                    partes.pop()
            elif p not in ("", "."):
                partes.append(p)
        return f"{DOMINIO}/{'/'.join(partes)}"
    return f"{DOMINIO}/{IMAGEM_PADRAO}"


def _artigo(rel: str) -> bool:
    return rel.startswith(SECOES_ARTIGO) and not rel.endswith("index.html")


def _bloco(texto: str, rel: str) -> str:
    url = _url(rel)
    titulo = _titulo(texto)
    desc = _descricao(texto)
    img = f"{DOMINIO}/{IMAGEM_PADRAO}" if rel == "index.html" else _imagem(texto, rel)
    artigo = _artigo(rel)
    e = lambda s: html.escape(s, quote=True)  # noqa: E731
    linhas = [INICIO]
    if rel == "404.html":
        linhas.append('  <meta name="robots" content="noindex">')
    else:
        linhas.append(f'  <link rel="canonical" href="{e(url)}">')
    linhas += [
        f'  <meta property="og:site_name" content="{e(NOME)}">',
        '  <meta property="og:locale" content="pt_BR">',
        f'  <meta property="og:type" content="{"article" if artigo else "website"}">',
        f'  <meta property="og:title" content="{e(titulo)}">',
    ]
    if desc:
        linhas.append(f'  <meta property="og:description" content="{e(desc)}">')
    linhas += [
        f'  <meta property="og:url" content="{e(url)}">',
        f'  <meta property="og:image" content="{e(img)}">',
    ]
    if img.endswith(IMAGEM_PADRAO):
        linhas += [
            '  <meta property="og:image:width" content="1200">',
            '  <meta property="og:image:height" content="630">',
        ]
    linhas.append('  <meta name="twitter:card" content="summary_large_image">')
    periodico = {
        "@type": "Periodical",
        "name": NOME,
        "url": DOMINIO + "/",
        "inLanguage": "pt-BR",
        "publisher": {
            "@type": "Organization",
            "name": "Universidade Federal do Espírito Santo — Departamento de Letras",
        },
    }
    if rel == "index.html":
        dados = {"@context": "https://schema.org", **periodico, "description": desc}
    elif artigo:
        dados = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": titulo[:110],
            "description": desc,
            "url": url,
            "image": img,
            "inLanguage": "pt-BR",
            "isPartOf": periodico,
        }
    else:
        dados = None
    if dados:
        linhas.append('  <script type="application/ld+json">'
                      + json.dumps(dados, ensure_ascii=False)
                      + "</script>")
    if rel != "404.html":
        # Contador de visitas sem cookies (GoatCounter); ignora acessos locais.
        linhas.append(f'  <script data-goatcounter="{CONTADOR}" async src="//gc.zgo.at/count.js"></script>')
    linhas.append(FIM)
    return "\n".join(linhas) + "\n"


def aplicar(site: Path) -> int:
    paginas: list[str] = []
    n = 0
    for f in sorted(site.rglob("*.html")):
        rel = f.relative_to(site).as_posix()
        if rel.startswith(IGNORAR):
            continue
        texto = f.read_text(encoding="utf-8")
        if _redirecionamento(texto) or "</head>" not in texto:
            continue
        texto = BLOCO_RE.sub("", texto)
        # canonical relativo antigo (escrito à mão) sai: o bloco traz o absoluto
        texto = re.sub(r'\s*<link rel="canonical" href="(?!https?://)[^"]*">', "", texto)
        novo = texto.replace("</head>", _bloco(texto, rel) + "</head>", 1)
        if novo != f.read_text(encoding="utf-8"):
            f.write_text(novo, encoding="utf-8")
            n += 1
        if not rel.startswith(FORA_DO_SITEMAP) and rel not in FORA_DO_SITEMAP:
            paginas.append(rel)
    urls = "\n".join(f"  <url><loc>{html.escape(_url(r))}</loc></url>" for r in paginas)
    (site / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n</urlset>\n",
        encoding="utf-8",
    )
    (site / "robots.txt").write_text(
        "User-agent: *\nDisallow: /admin/\nDisallow: /cms/\nDisallow: /redacao/\n\n"
        f"Sitemap: {DOMINIO}/sitemap.xml\n",
        encoding="utf-8",
    )
    return n


if __name__ == "__main__":
    raiz = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
    print(f"seo: {aplicar(raiz)} páginas atualizadas", file=sys.stderr)
