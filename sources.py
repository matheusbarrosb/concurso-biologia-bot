from __future__ import annotations

import logging
import time
import unicodedata
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import (
    DISCOVERY_TERMS,
    MAX_ARTICLES_PER_DISCOVERY_TERM,
    MAX_RECENT_ARTICLES_SECONDARY_SOURCE,
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT,
    USER_AGENT,
)
from models import Opportunity

log = logging.getLogger(__name__)


@dataclass
class CandidateLink:
    source: str
    title: str
    url: str


class Http:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "pt-BR,pt;q=0.9"})

    def get(self, url: str) -> requests.Response:
        response = self.session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        response.raise_for_status()
        time.sleep(REQUEST_DELAY_SECONDS)
        return response


def _visible_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "noscript", "form"]):
        tag.decompose()
    return "\n".join(line.strip() for line in soup.stripped_strings if line.strip())


def _first_external_link(soup: BeautifulSoup, own_host: str) -> str | None:
    ignored_suffixes = (
        own_host,
        "pci.app.br",
        "facebook.com",
        "instagram.com",
        "youtube.com",
        "twitter.com",
        "x.com",
        "google.com",
        "googlesyndication.com",
    )
    preferred_words = ("edital", "inscri", "banca", "site oficial", "instituto", "prefeitura", "universidade")
    fallback = None
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href.startswith("http"):
            continue
        host = urlparse(href).netloc.lower()
        if not host or any(host == suf or host.endswith("." + suf) for suf in ignored_suffixes):
            continue
        anchor = " ".join(a.stripped_strings).strip().lower()
        if any(word in anchor for word in preferred_words):
            return href
        if fallback is None:
            fallback = href
    return fallback


def _extract_title(soup: BeautifulSoup, fallback: str) -> str:
    h1 = soup.find("h1")
    if h1:
        title = " ".join(h1.stripped_strings).strip()
        if title:
            return title
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return fallback


def _slugify(text: str) -> str:
    """Slug ASCII compatível com as URLs públicas do PCI (ex.: biólogo -> biologo)."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(c for c in normalized if not unicodedata.combining(c))
    ascii_text = ascii_text.lower().strip()
    return "-".join(ascii_text.split())


def discover_pci(http: Http) -> list[CandidateLink]:
    """Descobre notícias recentes relacionadas a cargos/termos no PCI Concursos."""
    found: dict[str, CandidateLink] = {}
    seen_slugs: set[str] = set()

    for term in DISCOVERY_TERMS:
        slug = _slugify(term)
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        # /cargos e /vagas são as páginas mais úteis para profissão/cargo;
        # /pesquisa fica como fallback para termos mais genéricos.
        urls = [
            f"https://www.pciconcursos.com.br/cargos/{slug}",
            f"https://www.pciconcursos.com.br/vagas/{slug}",
            f"https://www.pciconcursos.com.br/pesquisa/{slug}",
        ]

        term_count = 0
        for search_url in urls:
            try:
                soup = BeautifulSoup(http.get(search_url).text, "html.parser")
            except requests.HTTPError as exc:
                # Alguns termos simplesmente não têm uma página própria; 404 não é fatal.
                status = exc.response.status_code if exc.response is not None else None
                if status != 404:
                    log.warning("PCI discovery falhou para %s: %s", search_url, exc)
                continue
            except Exception as exc:
                log.warning("PCI discovery falhou para %s: %s", search_url, exc)
                continue

            before = term_count
            for a in soup.find_all("a", href=True):
                href = urljoin(search_url, a["href"])
                if "/noticias/" not in href:
                    continue
                title = " ".join(a.stripped_strings).strip()
                if not title or len(title) < 12:
                    continue
                key = href.rstrip("/")
                found[key] = CandidateLink("PCI Concursos", title, key)
                term_count += 1
                if term_count >= MAX_ARTICLES_PER_DISCOVERY_TERM:
                    break

            # Se esta página trouxe notícias, não precisamos consultar as seguintes
            # para o mesmo termo. Isso reduz tráfego e tempo de execução.
            if term_count > before:
                break

    return list(found.values())


def discover_cnb_recent(http: Http) -> list[CandidateLink]:
    """Usa a capa de Concursos no Brasil como segunda fonte de descobertas recentes."""
    url = "https://concursosnobrasil.com/"
    found: dict[str, CandidateLink] = {}
    try:
        soup = BeautifulSoup(http.get(url).text, "html.parser")
    except Exception as exc:
        log.warning("Concursos no Brasil discovery falhou: %s", exc)
        return []

    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        parsed = urlparse(href)
        if parsed.netloc not in {"concursosnobrasil.com", "www.concursosnobrasil.com"}:
            continue
        # Artigos têm /concursos/<uf|br>/<ano>/<mes>/<dia>/<slug>/.
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 6 or parts[0] != "concursos" or not parts[2].isdigit():
            continue
        title = " ".join(a.stripped_strings).strip()
        if len(title) < 12:
            continue
        key = href.rstrip("/")
        found[key] = CandidateLink("Concursos no Brasil", title, key)
        if len(found) >= MAX_RECENT_ARTICLES_SECONDARY_SOURCE:
            break
    return list(found.values())


def fetch_article(http: Http, candidate: CandidateLink) -> Opportunity | None:
    try:
        response = http.get(candidate.url)
        soup = BeautifulSoup(response.text, "html.parser")
        title = _extract_title(soup, candidate.title)
        text = _visible_text(soup)
        if len(text) < 120:
            return None
        official = _first_external_link(soup, urlparse(response.url).netloc.lower())
        return Opportunity(
            source=candidate.source,
            title=title,
            url=response.url.rstrip("/"),
            text=text,
            official_url=official,
        )
    except Exception as exc:
        log.warning("Falha ao ler artigo %s: %s", candidate.url, exc)
        return None


def collect_all() -> list[Opportunity]:
    http = Http()
    candidates = discover_pci(http)
    candidates.extend(discover_cnb_recent(http))

    dedup: dict[str, CandidateLink] = {}
    for c in candidates:
        dedup[c.url.rstrip("/")] = c

    log.info("%d links candidatos descobertos", len(dedup))
    result: list[Opportunity] = []
    for candidate in dedup.values():
        op = fetch_article(http, candidate)
        if op:
            result.append(op)
    return result
