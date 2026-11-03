#!/usr/bin/env python3
"""Baixa capas (editoras) e retratos (Wikimedia) para a ficha Goncourt."""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CMS = Path(__file__).resolve().parent
ROOT = CMS.parent
DATA = CMS / "data" / "franca-prix-goncourt-obras.json"
OUT = ROOT / "img" / "premios" / "franca-prix-goncourt"
UA = "Mozilla/5.0 (compatible; LAB-IA-BR/1.0; +https://lab-ia-br.github.io/)"


def fetch(url: str, dest: Path) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = resp.read()
        if len(data) < 800:
            return False
        dest.write_bytes(data)
        return True
    except (urllib.error.URLError, OSError):
        return False


def wiki_thumb(title: str) -> str | None:
    enc = urllib.parse.quote(title.replace(" ", "_"))
    api = f"https://fr.wikipedia.org/api/rest_v1/page/summary/{enc}"
    req = urllib.request.Request(api, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        api = f"https://en.wikipedia.org/api/rest_v1/page/summary/{enc}"
        req = urllib.request.Request(api, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp)
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            return None
    thumb = data.get("thumbnail") or {}
    src = thumb.get("source")
    if not src:
        return None
    return re.sub(r"/(\d+)px-", r"/800px-", src, count=1)


def cover_urls(isbn: str, cover_url: str | None, autor_url: str | None = None) -> list[str]:
    urls: list[str] = []
    if cover_url:
        urls.append(cover_url)
    isbn = isbn.replace("-", "")
    urls.extend(
        [
            f"https://www.albin-michel.fr/sites/default/files/couvertures/{isbn}-j.jpg",
            f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg",
        ]
    )
    return urls


def main() -> int:
    spec = json.loads(DATA.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    ok_capa = ok_autor = 0
    for obra in spec["obras"]:
        oid = obra["id"]
        capa_path = OUT / f"{oid}-capa.jpg"
        autor_path = OUT / f"{oid}-autor.jpg"
        if not capa_path.is_file():
            for url in cover_urls(obra.get("isbn", ""), obra.get("cover_url")):
                if fetch(url, capa_path):
                    ok_capa += 1
                    print(f"capa {oid}: {url}")
                    break
            else:
                print(f"capa {oid}: FALHOU", file=sys.stderr)
        else:
            ok_capa += 1
        if not autor_path.is_file():
            thumb = obra.get("autor_url") or wiki_thumb(obra.get("wiki", ""))
            if thumb and fetch(thumb, autor_path):
                ok_autor += 1
                print(f"autor {oid}: {thumb}")
            else:
                print(f"autor {oid}: FALHOU", file=sys.stderr)
        else:
            ok_autor += 1
    print(f"Total capas: {ok_capa}/{len(spec['obras'])} · autores: {ok_autor}/{len(spec['obras'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
