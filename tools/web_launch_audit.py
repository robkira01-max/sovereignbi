#!/usr/bin/env python3
"""Web launch audit — checks a deployed site against the owner's launch checklist.

Standard library only (copy this single file into any project).
Audit ONLY sites you own: the tool requests the page, its assets and its links.

    python3 tools/web_launch_audit.py https://example.org
    python3 tools/web_launch_audit.py http://localhost:8080 --json
    python3 tools/web_launch_audit.py https://example.org --external --fail-on warn

Exit code: 0 = no failure, 1 = at least one FAIL (or WARN with --fail-on warn),
2 = site unreachable / bad usage.

Limits (stated in the report): it reads the HTML *served*, not the DOM rendered by
JavaScript (single-page apps), and it does not measure Core Web Vitals, colour
contrast or keyboard navigation — use Lighthouse for those.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import struct
import sys
import zlib
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Callable
from urllib.parse import urljoin, urlparse

UA = "web-launch-audit/1.0 (owner audit)"
PASS, WARN, FAIL, INFO = "PASS", "WARN", "FAIL", "INFO"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]", "0.0.0.0"}
TRACKERS = ("googletagmanager", "google-analytics", "doubleclick", "facebook.net", "connect.facebook", "hotjar", "clarity.ms", "linkedin.com/px")
FONT_CDNS = ("fonts.googleapis.com", "fonts.gstatic.com", "use.typekit", "cdnjs.cloudflare.com", "cdn.jsdelivr.net", "unpkg.com")


# ───────────────────────────── HTTP ─────────────────────────────

@dataclass
class Response:
    url: str
    status: int = 0
    headers: dict[str, str] = field(default_factory=dict)
    set_cookies: list[str] = field(default_factory=list)
    body: bytes = b""
    error: str | None = None

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")

    @property
    def ctype(self) -> str:
        return self.headers.get("content-type", "").split(";")[0].strip().lower()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):  # noqa: D401
        return None


def http_fetch(url: str, *, method: str = "GET", follow: bool = True, timeout: float = 10.0, max_bytes: int = 3_000_000) -> Response:
    if urlparse(url).scheme not in ("http", "https"):
        return Response(url, error="schéma non supporté")
    handlers: list = [] if follow else [_NoRedirect()]
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA, "Accept-Encoding": "gzip", "Accept": "*/*"})
    try:
        r = opener.open(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        r = e
    except Exception as e:  # noqa: BLE001 - network errors are reported, not raised
        return Response(url, error=f"{type(e).__name__}: {e}")
    try:
        body = r.read(max_bytes) if method != "HEAD" else b""
        hdrs = {k.lower(): v for k, v in r.headers.items()}
        if body and hdrs.get("content-encoding", "").lower() == "gzip":
            try:  # max_length borne la taille décompressée (anti « zip bomb »)
                body = zlib.decompressobj(31).decompress(body, max_bytes)
            except zlib.error:
                return Response(url, r.status if hasattr(r, "status") else r.code, hdrs, error="corps gzip invalide")
        cookies = r.headers.get_all("Set-Cookie") or []
        final = getattr(r, "url", url) or url
        return Response(final, r.status if hasattr(r, "status") else r.code, hdrs, cookies, body)
    finally:
        r.close()


# ───────────────────────────── HTML ─────────────────────────────

class Doc(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.html_lang: str | None = None
        self.metas: dict[str, str] = {}
        self.links: list[dict[str, str]] = []
        self.imgs: list[dict[str, str | None]] = []
        self.anchors: list[tuple[str, str]] = []
        self.scripts: list[dict[str, str]] = []
        self.iframes: list[str] = []
        self.inputs: list[dict[str, str | bool | None]] = []
        self.label_for: set[str] = set()
        self.text_chars = 0
        self.has_root = False
        self._in_title = False
        self._in_body = False
        self._skip = 0
        self._label_depth = 0
        self._a_href: str | None = None
        self._a_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v if v is not None else "") for k, v in attrs}
        if tag == "html":
            self.html_lang = a.get("lang")
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or a.get("http-equiv") or "").lower()
            if key and "content" in a:
                self.metas.setdefault(key, a["content"])
        elif tag == "link":
            self.links.append(a)
        elif tag == "img":
            self.imgs.append({"src": a.get("src"), "alt": a.get("alt") if "alt" in a else None, "width": a.get("width"),
                              "height": a.get("height"), "loading": a.get("loading"), "aria-hidden": a.get("aria-hidden"), "role": a.get("role")})
        elif tag == "a" and "href" in a:
            self._a_href, self._a_text = a["href"], []
        elif tag == "script":
            self.scripts.append(a)
            self._skip += 1
        elif tag in ("style", "noscript"):
            self._skip += 1
        elif tag == "iframe" and a.get("src"):
            self.iframes.append(a["src"])
        elif tag == "label":
            self._label_depth += 1
            if a.get("for"):
                self.label_for.add(a["for"])
        elif tag in ("input", "textarea", "select"):
            self.inputs.append({"tag": tag, "type": (a.get("type") or "text").lower(), "id": a.get("id"), "aria-label": a.get("aria-label"),
                                "aria-labelledby": a.get("aria-labelledby"), "title": a.get("title"), "in_label": self._label_depth > 0})
        elif tag == "body":
            self._in_body = True
        if a.get("id") in ("root", "app", "__next", "___gatsby"):
            self.has_root = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1
        elif tag == "label" and self._label_depth:
            self._label_depth -= 1
        elif tag == "a" and self._a_href is not None:
            self.anchors.append((self._a_href, " ".join("".join(self._a_text).split())))
            self._a_href = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._a_href is not None:
            self._a_text.append(data)
        if self._in_body and not self._skip:
            self.text_chars += len(data.strip())

    @property
    def is_spa_shell(self) -> bool:
        return self.has_root and self.text_chars < 200


def parse_html(text: str) -> Doc:
    d = Doc()
    d.feed(text)
    d.close()
    return d


# ───────────────────────────── images ─────────────────────────────

def image_size(data: bytes) -> tuple[int, int] | None:
    """(width, height) of a PNG or JPEG from its bytes, else None."""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        return struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + seg_len
    return None


# ───────────────────────────── context & results ─────────────────────────────

@dataclass
class Result:
    id: str
    status: str
    message: str


@dataclass
class Ctx:
    base: str                      # normalised URL of the audited page
    page: Response
    doc: Doc
    fetch: Callable[..., Response]
    external: bool = False
    max_links: int = 30

    @property
    def host(self) -> str:
        return urlparse(self.base).hostname or ""

    @property
    def is_local(self) -> bool:
        return self.host in LOCAL_HOSTS

    @property
    def is_https(self) -> bool:
        return urlparse(self.base).scheme == "https"

    @property
    def origin(self) -> str:
        u = urlparse(self.base)
        return f"{u.scheme}://{u.netloc}"

    def abs(self, href: str) -> str:
        return urljoin(self.base, href)

    def same_host(self, url: str) -> bool:
        return urlparse(url).hostname == self.host

    @property
    def noindex(self) -> bool:
        return "noindex" in self.doc.metas.get("robots", "").lower() or "noindex" in self.page.headers.get("x-robots-tag", "").lower()


def _list(items: list[str], n: int = 4) -> str:
    return ", ".join(items[:n]) + (f" … (+{len(items) - n})" if len(items) > n else "")


# ───────────────────────────── checks ─────────────────────────────

def check_https(c: Ctx) -> list[Result]:
    if c.is_local:
        return [Result("https", INFO, "audit local : HTTPS/TLS non évalué (à vérifier sur l'URL publique)")]
    out = [Result("https", PASS if c.is_https else FAIL, "la page est servie en HTTPS" if c.is_https else "la page est servie en HTTP")]
    if c.is_https:
        r = c.fetch("http://" + urlparse(c.base).netloc + "/", follow=False)
        if r.error:
            out.append(Result("https-redirect", INFO, "port 80 injoignable (aucune redirection testable)"))
        elif r.status in (301, 302, 307, 308) and r.headers.get("location", "").startswith("https://"):
            out.append(Result("https-redirect", PASS, f"HTTP redirige vers HTTPS ({r.status})"))
        else:
            out.append(Result("https-redirect", FAIL, f"HTTP n'est pas redirigé vers HTTPS (statut {r.status})"))
    return out


def check_hsts(c: Ctx) -> list[Result]:
    if c.is_local or not c.is_https:
        return []
    h = c.page.headers.get("strict-transport-security")
    if not h:
        return [Result("hsts", FAIL, "en-tête Strict-Transport-Security absent")]
    m = re.search(r"max-age=(\d+)", h)
    age = int(m.group(1)) if m else 0
    if age < 15552000:
        return [Result("hsts", WARN, f"HSTS présent mais max-age={age} (< 6 mois)")]
    return [Result("hsts", PASS, f"HSTS actif (max-age={age})")]


def check_security_headers(c: Ctx) -> list[Result]:
    h, out = c.page.headers, []
    out.append(Result("hdr-nosniff", PASS if h.get("x-content-type-options", "").lower() == "nosniff" else WARN, "X-Content-Type-Options: nosniff" if h.get("x-content-type-options") else "X-Content-Type-Options absent"))
    out.append(Result("hdr-referrer", PASS if h.get("referrer-policy") else WARN, "Referrer-Policy défini" if h.get("referrer-policy") else "Referrer-Policy absent"))
    frame = h.get("x-frame-options") or "frame-ancestors" in h.get("content-security-policy", "")
    out.append(Result("hdr-frame", PASS if frame else WARN, "protection anti-clickjacking présente" if frame else "ni X-Frame-Options ni frame-ancestors (clickjacking)"))
    out.append(Result("hdr-csp", PASS if h.get("content-security-policy") else INFO, "Content-Security-Policy défini" if h.get("content-security-policy") else "pas de Content-Security-Policy (recommandé)"))
    return out


def check_cookies(c: Ctx) -> list[Result]:
    if not c.page.set_cookies:
        return [Result("cookies", PASS, "aucun cookie posé par la page d'accueil")]
    bad = []
    for sc in c.page.set_cookies:
        name, low = sc.split("=", 1)[0], sc.lower()
        miss = [f for f, ok in (("Secure", "secure" in low), ("HttpOnly", "httponly" in low), ("SameSite", "samesite" in low)) if not ok]
        if miss:
            bad.append(f"{name} (manque {'/'.join(miss)})")
    return [Result("cookies", WARN if bad else PASS, f"cookies sans attributs de sécurité : {_list(bad)}" if bad else f"{len(c.page.set_cookies)} cookie(s), attributs de sécurité présents")]


def check_title_description(c: Ctx) -> list[Result]:
    out = []
    t = " ".join(c.doc.title.split())
    if not t:
        out.append(Result("title", FAIL, "balise <title> absente ou vide"))
    elif len(t) > 60 or len(t) < 10:
        out.append(Result("title", WARN, f"titre de {len(t)} caractères (idéal 10-60) : « {t} »"))
    else:
        out.append(Result("title", PASS, f"titre : « {t} » ({len(t)} car.)"))
    d = c.doc.metas.get("description", "").strip()
    if not d:
        out.append(Result("description", FAIL, "meta description absente"))
    elif not 70 <= len(d) <= 160:
        out.append(Result("description", WARN, f"description de {len(d)} caractères (idéal 70-160)"))
    else:
        out.append(Result("description", PASS, f"description de {len(d)} caractères"))
    out.append(Result("lang", PASS if c.doc.html_lang else WARN, f"<html lang=\"{c.doc.html_lang}\">" if c.doc.html_lang else "attribut lang absent sur <html>"))
    out.append(Result("viewport", PASS if "viewport" in c.doc.metas else FAIL, "meta viewport présente" if "viewport" in c.doc.metas else "meta viewport absente (affichage mobile cassé)"))
    return out


def check_indexing(c: Ctx) -> list[Result]:
    if c.noindex:
        return [Result("indexing", INFO, "page non indexable (noindex) : voulu pour une application privée, pas pour un site vitrine")]
    canon = any(l.get("rel", "").lower() == "canonical" for l in c.doc.links)
    return [Result("indexing", PASS if canon else WARN, "page indexable, URL canonique déclarée" if canon else "page indexable sans <link rel=canonical>")]


def check_open_graph(c: Ctx) -> list[Result]:
    m, out = c.doc.metas, []
    missing = [k for k in ("og:title", "og:description", "og:image", "og:type", "twitter:card") if not m.get(k)]
    out.append(Result("og-tags", FAIL if "og:image" in missing or "og:title" in missing else (WARN if missing else PASS),
                      f"balises manquantes : {', '.join(missing)}" if missing else "balises Open Graph et Twitter Card complètes"))
    if not m.get("og:url"):
        out.append(Result("og-url", WARN, "og:url absent"))
    img = m.get("og:image")
    if not img:
        return out
    if not re.match(r"https?://", img):
        out.append(Result("og-image", FAIL, f"og:image n'est pas une URL absolue : {img} (refusée par LinkedIn/Facebook)"))
        return out
    r = c.fetch(img)
    if r.error or r.status != 200:
        out.append(Result("og-image", FAIL, f"og:image injoignable ({r.error or r.status}) : {img}"))
        return out
    if "svg" in r.ctype or img.lower().endswith(".svg"):
        out.append(Result("og-image", FAIL, "og:image est un SVG : non affiché par LinkedIn, Facebook, X (utiliser PNG/JPG 1200×630)"))
        return out
    size = image_size(r.body)
    kb = len(r.body) / 1024
    if size is None:
        out.append(Result("og-image", INFO, f"og:image {r.ctype}, {kb:.0f} Ko (dimensions non lisibles)"))
    elif size[0] < 600 or size[1] < 315 or abs(size[0] / size[1] - 1.91) > 0.15:
        out.append(Result("og-image", WARN, f"og:image {size[0]}×{size[1]} (recommandé 1200×630, ratio 1,91:1)"))
    elif kb > 1024:
        out.append(Result("og-image", WARN, f"og:image {size[0]}×{size[1]} mais {kb:.0f} Ko (> 1 Mo)"))
    else:
        out.append(Result("og-image", PASS, f"og:image {size[0]}×{size[1]}, {kb:.0f} Ko"))
    return out


def check_favicons(c: Ctx) -> list[Result]:
    out, rels = [], {}
    for l in c.doc.links:
        for rel in l.get("rel", "").lower().split():
            rels.setdefault(rel, []).append(l)
    icon = rels.get("icon", []) + rels.get("shortcut", [])
    out.append(Result("favicon", PASS if icon else WARN, "favicon déclaré" if icon else "aucun <link rel=icon>"))
    ico = c.fetch(c.origin + "/favicon.ico")
    out.append(Result("favicon-ico", PASS if ico.status == 200 and "html" not in ico.ctype else WARN, "/favicon.ico présent" if ico.status == 200 and "html" not in ico.ctype else "/favicon.ico absent (navigateurs et flux RSS le réclament)"))
    apple = rels.get("apple-touch-icon", [])
    if not apple:
        out.append(Result("apple-touch-icon", WARN, "apple-touch-icon absent (icône iOS)"))
    else:
        r = c.fetch(c.abs(apple[0].get("href", "")))
        out.append(Result("apple-touch-icon", PASS if r.status == 200 else FAIL, "apple-touch-icon présent" if r.status == 200 else f"apple-touch-icon injoignable ({r.status})"))
    man = rels.get("manifest", [])
    if not man:
        out.append(Result("manifest", WARN, "aucun manifeste web (icônes Android)"))
        return out
    r = c.fetch(c.abs(man[0].get("href", "")))
    try:
        data = json.loads(r.text) if r.status == 200 else None
    except ValueError:
        data = None
    if not isinstance(data, dict):
        out.append(Result("manifest", FAIL, "manifeste injoignable ou JSON invalide"))
        return out
    sizes = {i.get("sizes") for i in data.get("icons", [])}
    ok = {"192x192", "512x512"} <= sizes
    broken = [i["src"] for i in data.get("icons", []) if c.fetch(urljoin(c.abs(man[0]["href"]), i.get("src", ""))).status != 200]
    out.append(Result("manifest", FAIL if broken else (PASS if ok else WARN),
                      f"icônes du manifeste introuvables : {_list(broken)}" if broken else ("manifeste valide avec icônes 192 et 512" if ok else "manifeste sans icônes 192×192 et 512×512")))
    return out


def check_robots_sitemap(c: Ctx) -> list[Result]:
    out = []
    r = c.fetch(c.origin + "/robots.txt")
    sitemaps: list[str] = []
    if r.status != 200 or "html" in r.ctype:
        out.append(Result("robots", WARN if not c.noindex else INFO, "/robots.txt absent"))
    else:
        body = r.text
        sitemaps = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", body)
        rel = [s for s in sitemaps if not re.match(r"https?://", s)]
        blocks_all = re.search(r"(?im)^\s*disallow:\s*/\s*$", body)
        if rel:
            out.append(Result("robots", FAIL, f"Sitemap relatif dans robots.txt (doit être absolu) : {rel[0]}"))
        elif blocks_all:
            out.append(Result("robots", WARN, "robots.txt bloque tout le crawl (« Disallow: / ») : pas d'aperçus de partage ni de lecture du noindex"))
        else:
            out.append(Result("robots", PASS, "robots.txt présent" + (f", sitemap déclaré ({sitemaps[0]})" if sitemaps else "")))
    sm_url = sitemaps[0] if sitemaps and re.match(r"https?://", sitemaps[0]) else c.origin + "/sitemap.xml"
    s = c.fetch(sm_url)
    if s.status != 200 or "html" in s.ctype:
        out.append(Result("sitemap", INFO if c.noindex else WARN, "pas de sitemap" + (" (normal : site non indexable)" if c.noindex else " (à fournir pour un site public)")))
        return out
    locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", s.text)
    if not locs:
        out.append(Result("sitemap", FAIL, "sitemap sans aucune URL <loc>"))
        return out
    rel = [u for u in locs if not re.match(r"https?://", u)]
    if rel:
        out.append(Result("sitemap", FAIL, f"URL relatives dans le sitemap (doivent être absolues) : {_list(rel)}"))
        return out
    dead = [u for u in locs[:15] if c.fetch(u, follow=False).status != 200]
    out.append(Result("sitemap", FAIL if dead else PASS, f"URLs du sitemap en erreur ou redirigées : {_list(dead)}" if dead else f"sitemap valide ({len(locs)} URL, 15 premières testées)"))
    return out


def check_404(c: Ctx) -> list[Result]:
    r = c.fetch(f"{c.origin}/__audit-404-{random.randrange(10**9)}")
    if r.error:
        return [Result("404", WARN, f"test 404 impossible ({r.error})")]
    if r.status == 404:
        home = re.search(r"""href=["'](/|%s/?)["']""" % re.escape(c.origin), r.text)
        return [Result("404", PASS if home else WARN, "vrai code 404 avec lien de retour à l'accueil" if home else "vrai code 404 mais sans lien de retour à l'accueil")]
    if r.status == 200:
        return [Result("404", FAIL, "« soft 404 » : une URL inexistante répond 200 (contenu de l'accueil ?)")]
    return [Result("404", WARN, f"URL inexistante : statut {r.status} (attendu 404)")]


def check_images(c: Ctx) -> list[Result]:
    imgs = c.doc.imgs
    if not imgs:
        return [Result("images", INFO, "aucune <img> dans le HTML servi" + (" (application rendue par JavaScript : non analysée)" if c.doc.is_spa_shell else ""))]
    out = []
    no_alt = [str(i["src"]) for i in imgs if i["alt"] is None and i["role"] != "presentation" and i["aria-hidden"] != "true"]
    out.append(Result("img-alt", FAIL if no_alt else PASS, f"<img> sans attribut alt : {_list(no_alt)}" if no_alt else f"{len(imgs)} image(s), toutes avec alt (alt=\"\" = décorative)"))
    nodim = [str(i["src"]) for i in imgs if not (i["width"] and i["height"])]
    if nodim:
        out.append(Result("img-dims", WARN, f"images sans width/height (décalage de mise en page, CLS) : {_list(nodim)}"))
    heavy = []
    for i in imgs[:20]:
        if not i["src"] or str(i["src"]).startswith("data:"):
            continue
        r = c.fetch(c.abs(str(i["src"])), method="HEAD")
        n = int(r.headers.get("content-length", 0) or 0)
        if n > 200 * 1024:
            heavy.append(f"{i['src']} ({n // 1024} Ko)")
    out.append(Result("img-weight", WARN if heavy else PASS, f"images lourdes (> 200 Ko, WebP/AVIF conseillé) : {_list(heavy)}" if heavy else "poids des images raisonnable"))
    return out


def _resource_urls(c: Ctx) -> list[str]:
    urls = [s["src"] for s in c.doc.scripts if s.get("src")]
    urls += [l["href"] for l in c.doc.links if l.get("href") and l.get("rel", "").lower().split()[0:1] and l["rel"].lower().split()[0] in ("stylesheet", "preload", "modulepreload", "prefetch", "preconnect", "dns-prefetch")]
    urls += [i["src"] for i in c.doc.imgs if i.get("src")]
    urls += c.doc.iframes
    return urls


def check_mixed_content(c: Ctx) -> list[Result]:
    if not c.is_https:
        return []
    bad = [u for u in _resource_urls(c) if str(u).startswith("http://")]
    return [Result("mixed-content", FAIL if bad else PASS, f"ressources HTTP sur une page HTTPS : {_list(bad)}" if bad else "aucun contenu mixte HTTP/HTTPS")]


def check_third_party(c: Ctx) -> list[Result]:
    ext = sorted({u for u in (c.abs(x) for x in _resource_urls(c)) if urlparse(u).hostname and not c.same_host(u)})
    if not ext:
        return [Result("third-party", PASS, "aucune ressource tierce chargée par la page (aucune IP transmise à un tiers)")]
    trk = [u for u in ext if any(t in u for t in TRACKERS)]
    cdn = [u for u in ext if any(t in u for t in FONT_CDNS)]
    if trk:
        return [Result("third-party", WARN, f"traceurs chargés sans consentement visible dans le HTML : {_list(trk)}")]
    if cdn:
        return [Result("third-party", WARN, f"polices/CDN tiers (IP des visiteurs transmise) : {_list(cdn)}")]
    return [Result("third-party", INFO, f"ressources tierces : {_list(sorted({urlparse(u).hostname for u in ext}))}")]


def check_legal_links(c: Ctx) -> list[Result]:
    if c.doc.is_spa_shell:
        return [Result("legal-links", INFO, "application rendue par JavaScript : liens légaux non analysables dans le HTML servi (vérifier à la main ou avec Playwright)")]
    kinds = {"confidentialité": ("privacy", "confidential"), "CGU": ("terms", "cgu", "conditions"), "cookies": ("cookie",), "mentions légales": ("mentions", "legal-notice", "legal")}
    found = {k: False for k in kinds}
    for href, text in c.doc.anchors:
        blob = f"{href} {text}".lower()
        for k, pats in kinds.items():
            if any(p in blob for p in pats):
                found[k] = True
    missing = [k for k, ok in found.items() if not ok]
    return [Result("legal-links", WARN if missing else PASS, f"liens légaux introuvables : {', '.join(missing)}" if missing else "liens vers les 4 pages légales présents")]


def check_forms(c: Ctx) -> list[Result]:
    fields = [i for i in c.doc.inputs if i["type"] not in ("hidden", "submit", "button", "image", "reset")]
    if not fields:
        return [Result("forms", INFO, "aucun champ de formulaire dans le HTML servi" + (" (application rendue par JavaScript)" if c.doc.is_spa_shell else ""))]
    bad = [str(i["id"] or i["type"]) for i in fields if not (i["in_label"] or i["aria-label"] or i["aria-labelledby"] or i["title"] or (i["id"] and i["id"] in c.doc.label_for))]
    return [Result("forms", WARN if bad else PASS, f"champs sans étiquette accessible : {_list(bad)}" if bad else f"{len(fields)} champ(s), tous étiquetés")]


def check_links(c: Ctx) -> list[Result]:
    if c.doc.is_spa_shell:
        return [Result("links", INFO, "application rendue par JavaScript : liens non analysables dans le HTML servi")]
    seen: list[str] = []
    for href, _ in c.doc.anchors:
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
            continue
        u = c.abs(href).split("#")[0]
        if u not in seen and u != c.base and (c.external or c.same_host(u)):
            seen.append(u)
    broken, moved = [], []
    for u in seen[: c.max_links]:
        r = c.fetch(u)
        if r.error or r.status >= 400:
            broken.append(f"{u} ({r.error or r.status})")
        elif r.url.rstrip("/") != u.rstrip("/"):
            moved.append(u)
    out = [Result("links", FAIL if broken else PASS, f"liens cassés : {_list(broken)}" if broken else f"{min(len(seen), c.max_links)} lien(s) testé(s), aucun cassé")]
    if moved:
        out.append(Result("links-redirect", INFO, f"liens redirigés (mettre à jour vers l'URL finale) : {_list(moved)}"))
    return out


def check_weight(c: Ctx) -> list[Result]:
    out = []
    enc = c.page.headers.get("content-encoding", "")
    out.append(Result("compression", PASS if enc in ("gzip", "br", "zstd") else WARN, f"HTML compressé ({enc})" if enc else "HTML non compressé (activer gzip/brotli)"))
    js = [c.abs(s["src"]) for s in c.doc.scripts if s.get("src") and c.same_host(c.abs(s["src"]))]
    js += [c.abs(l["href"]) for l in c.doc.links if l.get("rel", "").lower() == "modulepreload" and l.get("href")]
    total = 0
    for u in dict.fromkeys(js):
        n = int(c.fetch(u, method="HEAD").headers.get("content-length", 0) or 0)
        total += n
    if js and total:
        kb = total // 1024
        out.append(Result("js-weight", FAIL if kb > 2048 else WARN if kb > 500 else PASS, f"JavaScript du premier chargement : {kb} Ko transférés" + (" (> 500 Ko : découper le code)" if kb > 500 else "")))
    out.append(Result("cwv", INFO, "LCP/INP/CLS, contraste WCAG et navigation clavier non mesurés : lancer Lighthouse (npx lighthouse <url> --view)"))
    return out


CHECKS: list[Callable[[Ctx], list[Result]]] = [
    check_https, check_hsts, check_security_headers, check_cookies, check_title_description, check_indexing,
    check_open_graph, check_favicons, check_robots_sitemap, check_404, check_images, check_mixed_content,
    check_third_party, check_legal_links, check_forms, check_links, check_weight,
]


# ───────────────────────────── runner ─────────────────────────────

def audit(url: str, *, external: bool = False, max_links: int = 30, fetch: Callable[..., Response] | None = None, skip: set[str] | None = None) -> list[Result]:
    fetch = fetch or http_fetch
    page = fetch(url)
    if page.error or not page.status:
        raise ConnectionError(page.error or "aucune réponse")
    ctx = Ctx(base=page.url, page=page, doc=parse_html(page.text), fetch=fetch, external=external, max_links=max_links)
    results: list[Result] = []
    if page.status >= 400:
        results.append(Result("page", FAIL, f"la page d'accueil répond {page.status}"))
    for chk in CHECKS:
        for r in chk(ctx):
            if not skip or r.id not in skip:
                results.append(r)
    return results


COLORS = {PASS: "32", WARN: "33", FAIL: "31", INFO: "36"}


def render(results: list[Result], url: str, color: bool) -> str:
    def c(s: str, st: str) -> str:
        return f"\033[{COLORS[st]}m{s}\033[0m" if color else s

    lines = [f"Audit de lancement web — {url}", ""]
    for r in results:
        lines.append(f"  {c(f'[{r.status}]', r.status):>{14 if color else 6}} {r.id:<16} {r.message}")
    n = {s: sum(1 for r in results if r.status == s) for s in (PASS, WARN, FAIL, INFO)}
    lines += ["", f"Bilan : {n[PASS]} PASS · {n[WARN]} WARN · {n[FAIL]} FAIL · {n[INFO]} INFO",
              "Limites : HTML servi (pas le DOM rendu par JavaScript) ; Core Web Vitals, contraste et clavier non mesurés."]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Audit de lancement web (checklist propriétaire).")
    ap.add_argument("url")
    ap.add_argument("--json", action="store_true", help="sortie JSON")
    ap.add_argument("--external", action="store_true", help="tester aussi les liens externes")
    ap.add_argument("--max-links", type=int, default=30)
    ap.add_argument("--skip", default="", help="ids à ignorer, séparés par des virgules")
    ap.add_argument("--fail-on", choices=("fail", "warn"), default="fail")
    ap.add_argument("--no-color", action="store_true")
    a = ap.parse_args(argv)
    if urlparse(a.url).scheme not in ("http", "https"):
        print("L'URL doit commencer par http:// ou https://", file=sys.stderr)
        return 2
    try:
        results = audit(a.url, external=a.external, max_links=a.max_links, skip={s for s in a.skip.split(",") if s})
    except ConnectionError as e:
        print(f"Site injoignable : {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps([r.__dict__ for r in results], ensure_ascii=False, indent=2))
    else:
        print(render(results, a.url, sys.stdout.isatty() and not a.no_color))
    bad = {FAIL} | ({WARN} if a.fail_on == "warn" else set())
    return 1 if any(r.status in bad for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
