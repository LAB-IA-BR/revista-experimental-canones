#!/usr/bin/env python3
"""Baixa capas (Electre via Mollat / Albin) e retratos (Wikimedia) — Goncourt 2026."""

from __future__ import annotations

import argparse
import io
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

BLOCKED_COVER_HOSTS = (
    "franceinfo.fr",
    "radiofrance.fr",
    "rfi.fr",
    "rts.ch",
    "laprovence.com",
    "lexpress.fr",
    "lalibre.be",
)


def as_jpeg(data: bytes) -> bytes:
    if data[:2] == b"\xff\xd8":
        return data
    try:
        from PIL import Image
    except ImportError:
        return data
    try:
        im = Image.open(io.BytesIO(data))
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=88, optimize=True)
        return out.getvalue()
    except OSError:
        return data


def fetch_bytes(url: str, referer: str | None = None) -> bytes | None:
    headers = {"User-Agent": UA}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = resp.read()
    except (urllib.error.URLError, OSError):
        return None
    if len(data) < 800:
        return None
    return data


def image_size(data: bytes) -> tuple[int, int] | None:
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        im = Image.open(io.BytesIO(data))
        return im.size
    except OSError:
        return None


def valid_cover(data: bytes, url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower()
    if any(b in host for b in BLOCKED_COVER_HOSTS):
        return False
    size = image_size(data)
    if not size:
        return "electre-ng.com" in host or "albin-michel.fr" in host
    w, h = size
    if w < 200 or h < 280:
        return False
    if w >= h:
        return False
    ratio = h / w
    return 1.15 <= ratio <= 2.05


def valid_portrait(data: bytes) -> bool:
    size = image_size(data)
    if not size:
        return True
    w, h = size
    if min(w, h) < 200:
        return False
    return max(w, h) / min(w, h) <= 2.8


def mollat_cover_url(page_url: str) -> str | None:
    html = fetch_bytes(page_url)
    if not html:
        return None
    text = html.decode("utf-8", "replace")
    m = re.search(r'property="og:image"\s+content="([^"]+)"', text)
    if not m:
        return None
    return m.group(1).replace("&amp;", "&")


def cover_candidates(obra: dict) -> list[str]:
    urls: list[str] = []
    mollat = obra.get("mollat_url")
    if mollat:
        og = mollat_cover_url(mollat)
        if og:
            urls.append(og)
    isbn = str(obra.get("isbn") or "").replace("-", "")
    if isbn.startswith("978222"):
        urls.append(
            f"https://www.albin-michel.fr/sites/default/files/couvertures/{isbn}-j.jpg"
        )
    return urls


def wiki_thumb(title: str) -> str | None:
    if not title.strip():
        return None
    enc = urllib.parse.quote(title.replace(" ", "_"))
    for lang in ("fr", "en"):
        api = (
            f"https://{lang}.wikipedia.org/w/api.php?"
            f"action=query&titles={enc}&prop=pageimages"
            f"&piprop=thumbnail&pithumbsize=960&format=json"
        )
        req = urllib.request.Request(api, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp)
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            continue
        pages = data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()), {})
        thumb = page.get("thumbnail") or {}
        src = thumb.get("source")
        if src:
            return src.split("?")[0]
    return None


def download_cover(obra: dict, dest: Path, force: bool) -> bool:
    if dest.is_file() and not force:
        data = dest.read_bytes()
        if valid_cover(data, dest.name):
            return True
    for url in cover_candidates(obra):
        data = fetch_bytes(url, referer=obra.get("mollat_url"))
        if data and valid_cover(data, url):
            dest.write_bytes(as_jpeg(data))
            print(f"capa {obra['id']}: {url}")
            return True
    print(f"capa {obra['id']}: FALHOU", file=sys.stderr)
    return False


def download_autor(obra: dict, dest: Path, force: bool) -> bool:
    if dest.is_file() and not force:
        data = dest.read_bytes()
        if valid_portrait(data):
            return True
    thumb = obra.get("autor_url") or wiki_thumb(str(obra.get("wiki") or ""))
    if not thumb:
        print(f"autor {obra['id']}: FALHOU (wiki)", file=sys.stderr)
        return False
    data = fetch_bytes(thumb)
    if not data or not valid_portrait(data):
        print(f"autor {obra['id']}: FALHOU (retrato)", file=sys.stderr)
        return False
    dest.write_bytes(as_jpeg(data))
    print(f"autor {obra['id']}: {thumb}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="re-baixa mesmo se o arquivo existir")
    args = parser.parse_args()
    spec = json.loads(DATA.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    ok_capa = ok_autor = 0
    for obra in spec["obras"]:
        oid = obra["id"]
        if download_cover(obra, OUT / f"{oid}-capa.jpg", args.force):
            ok_capa += 1
        if download_autor(obra, OUT / f"{oid}-autor.jpg", args.force):
            ok_autor += 1
    n = len(spec["obras"])
    print(f"Total capas: {ok_capa}/{n} · autores: {ok_autor}/{n}")
    return 0 if ok_capa == n else 1


if __name__ == "__main__":
    raise SystemExit(main())
