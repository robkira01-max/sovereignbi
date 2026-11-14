"""Tests for tools/web_launch_audit.py — run against local fixture servers (no internet)."""
from __future__ import annotations

import gzip
import importlib.util
import json
import struct
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("web_launch_audit", Path(__file__).parent.parent / "tools" / "web_launch_audit.py")
wla = importlib.util.module_from_spec(_spec)
sys.modules["web_launch_audit"] = wla  # requis par @dataclass + `from __future__ import annotations`
_spec.loader.exec_module(wla)


def png(w: int, h: int) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", w, h) + b"\x08\x06\x00\x00\x00" + b"\x00" * 4


def jpeg(w: int, h: int) -> bytes:
    sof = b"\xff\xc0" + struct.pack(">HBHHB", 11, 8, h, w, 1) + b"\x01\x11\x00"
    return b"\xff\xd8" + b"\xff\xe0" + struct.pack(">H", 4) + b"\x00\x00" + sof


class Site:
    """Tiny HTTP fixture: routes maps path -> (status, headers, body); unknown paths use `fallback`."""

    def __init__(self, routes_for, fallback=(404, {"Content-Type": "text/html"}, b"<a href='/'>Accueil</a> introuvable")):
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):  # silence
                pass

            def _serve(self, head: bool):
                routes = outer.routes
                status, headers, body = routes.get(self.path.split("?")[0], outer.fallback)
                if callable(body):
                    body = body(self)
                self.send_response(status)
                for k, v in headers.items():
                    if k == "Set-Cookie":
                        for c in ([v] if isinstance(v, str) else v):
                            self.send_header("Set-Cookie", c)
                    else:
                        self.send_header(k, v)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if not head:
                    self.wfile.write(body)

            def do_GET(self):
                self._serve(False)

            def do_HEAD(self):
                self._serve(True)

        self.fallback = fallback
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.routes = routes_for(self.base)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


HTML = {"Content-Type": "text/html; charset=utf-8"}
SECURE = {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "same-origin", "X-Frame-Options": "DENY"}


def good_routes(base: str) -> dict:
    index = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width">
<title>MizanBI | Business Intelligence souveraine et IA</title>
<meta name="description" content="Analysez vos données avec MizanBI, plateforme de Business Intelligence assistée par intelligence artificielle, conçue pour garder le contrôle.">
<link rel="canonical" href="{base}/">
<meta property="og:title" content="MizanBI"><meta property="og:description" content="BI souveraine"><meta property="og:type" content="website">
<meta property="og:url" content="{base}/"><meta property="og:image" content="{base}/og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg"><link rel="apple-touch-icon" href="/apple.png"><link rel="manifest" href="/site.webmanifest">
</head><body><h1>Bonjour</h1>
<p>{'texte ' * 60}</p>
<img src="/logo.png" alt="Logo MizanBI" width="40" height="40"><img src="/deco.png" alt="" width="10" height="10">
<form><label for="e">Email</label><input id="e" type="email"><label>Mot de passe <input type="password"></label></form>
<a href="/about">À propos</a>
<footer><a href="/privacy">Politique de confidentialité</a> <a href="/terms">CGU</a> <a href="/cookies">Cookies</a> <a href="/legal-notice">Mentions légales</a></footer>
</body></html>""".encode()
    manifest = json.dumps({"name": "x", "icons": [{"src": "/i192.png", "sizes": "192x192"}, {"src": "/i512.png", "sizes": "512x512"}]}).encode()
    ok = (200, HTML, b"<html><body>ok</body></html>")
    return {
        "/": (200, {**HTML, **SECURE, "Content-Encoding": "gzip"}, gzip.compress(index)),
        "/og.png": (200, {"Content-Type": "image/png"}, png(1200, 630)),
        "/favicon.ico": (200, {"Content-Type": "image/x-icon"}, b"ico"),
        "/favicon.svg": (200, {"Content-Type": "image/svg+xml"}, b"<svg/>"),
        "/apple.png": (200, {"Content-Type": "image/png"}, png(180, 180)),
        "/site.webmanifest": (200, {"Content-Type": "application/manifest+json"}, manifest),
        "/i192.png": (200, {"Content-Type": "image/png"}, png(192, 192)),
        "/i512.png": (200, {"Content-Type": "image/png"}, png(512, 512)),
        "/logo.png": (200, {"Content-Type": "image/png"}, png(40, 40)),
        "/deco.png": (200, {"Content-Type": "image/png"}, png(10, 10)),
        "/robots.txt": (200, {"Content-Type": "text/plain"}, f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n".encode()),
        "/sitemap.xml": (200, {"Content-Type": "application/xml"}, f"<urlset><url><loc>{base}/</loc></url><url><loc>{base}/about</loc></url></urlset>".encode()),
        "/about": ok, "/privacy": ok, "/terms": ok, "/cookies": ok, "/legal-notice": ok,
    }


def bad_routes(base: str) -> dict:
    index = b"""<!doctype html><html><head>
<meta property="og:image" content="/og.svg">
<script src="https://www.googletagmanager.com/gtm.js"></script></head><body>
<p>""" + b"texte " * 60 + b"""</p>
<img src="/photo.jpg"><form><input type="text" id="q"></form>
<a href="/missing-page">Lien mort</a></body></html>"""
    return {
        "/": (200, {**HTML, "Set-Cookie": "sid=abc123; Path=/"}, index),
        "/og.svg": (200, {"Content-Type": "image/svg+xml"}, b"<svg/>"),
        "/photo.jpg": (200, {"Content-Type": "image/jpeg"}, b"x" * 250_000),
        "/missing-page": (404, HTML, b"nope"),
        "/robots.txt": (200, {"Content-Type": "text/plain"}, b"User-agent: *\nDisallow: /\nSitemap: /sitemap.xml\n"),
    }


def run(site: Site, **kw):
    return {r.id: r for r in wla.audit(site.base, **kw)}


@pytest.fixture()
def good():
    s = Site(good_routes)
    yield s
    s.close()


@pytest.fixture()
def bad():
    # soft 404: unknown URLs answer 200 with the home page
    s = Site(bad_routes, fallback=(200, HTML, b"<html><body>home</body></html>"))
    yield s
    s.close()


def test_good_site_has_no_failure_or_warning(good):
    res = run(good)
    problems = {k: (r.status, r.message) for k, r in res.items() if r.status in (wla.FAIL, wla.WARN)}
    assert problems == {}
    for k in ("title", "description", "og-image", "favicon-ico", "manifest", "robots", "sitemap", "404", "img-alt", "forms", "links", "legal-links"):
        assert res[k].status == wla.PASS, (k, res[k].message)


def test_bad_site_is_flagged(bad):
    res = run(bad)
    for k in ("title", "description", "viewport", "og-tags", "og-image", "404", "img-alt", "links", "robots"):
        assert res[k].status == wla.FAIL, (k, res[k].message)
    assert "soft 404" in res["404"].message
    assert "SVG" in res["og-image"].message or "absolue" in res["og-image"].message
    assert "missing-page" in res["links"].message
    assert res["img-weight"].status == wla.WARN and "photo.jpg" in res["img-weight"].message
    for k in ("cookies", "forms", "third-party", "img-dims"):
        assert res[k].status == wla.WARN, (k, res[k].message)
    assert "googletagmanager" in res["third-party"].message
    assert "sid" in res["cookies"].message


def test_local_audit_skips_tls_checks(good):
    res = run(good)
    assert res["https"].status == wla.INFO
    assert "hsts" not in res and "mixed-content" not in res


def test_skip_option_removes_checks(good):
    assert "title" not in run(good, skip={"title"})


def test_gzip_responses_are_decoded(good):
    # Regression: the tool announces Accept-Encoding: gzip and must decompress, otherwise
    # every check on a compressing server (nginx, Caddy) fails on garbage bytes.
    assert good.routes["/"][1]["Content-Encoding"] == "gzip"
    res = run(good)
    assert res["title"].status == wla.PASS
    assert res["compression"].status == wla.PASS


def test_uncompressed_html_is_warned():
    def routes(base):
        r = good_routes(base)
        r["/"] = (200, {**HTML, **SECURE}, gzip.decompress(r["/"][2]))
        return r

    s = Site(routes)
    try:
        res = run(s)
        assert res["title"].status == wla.PASS
        assert res["compression"].status == wla.WARN
    finally:
        s.close()


def test_hsts_and_mixed_content_on_https_context():
    doc = wla.parse_html('<img src="http://cdn.example/a.png"><script src="https://ok.example/a.js"></script>')

    def ctx(headers):
        page = wla.Response("https://site.example/", 200, headers, [], b"")
        return wla.Ctx("https://site.example/", page, doc, fetch=lambda *a, **k: wla.Response("", 404))

    assert wla.check_hsts(ctx({}))[0].status == wla.FAIL
    assert wla.check_hsts(ctx({"strict-transport-security": "max-age=300"}))[0].status == wla.WARN
    assert wla.check_hsts(ctx({"strict-transport-security": "max-age=63072000; includeSubDomains"}))[0].status == wla.PASS
    mc = wla.check_mixed_content(ctx({}))[0]
    assert mc.status == wla.FAIL and "http://cdn.example/a.png" in mc.message


def test_http_to_https_redirect_check_on_non_local_host():
    def fetch(url, **kw):
        if url.startswith("http://"):
            return wla.Response(url, 301, {"location": "https://site.example/"})
        return wla.Response(url, 200, {}, [], b"")

    doc = wla.parse_html("<html></html>")
    page = wla.Response("https://site.example/", 200, {}, [], b"")
    res = wla.check_https(wla.Ctx("https://site.example/", page, doc, fetch=fetch))
    assert [r.status for r in res] == [wla.PASS, wla.PASS]

    def no_redirect(url, **kw):
        return wla.Response(url, 200, {}, [], b"") if url.startswith("http://") else wla.Response(url, 200)

    res = wla.check_https(wla.Ctx("https://site.example/", page, doc, fetch=no_redirect))
    assert res[1].status == wla.FAIL


def test_fetch_does_not_follow_redirects_when_asked():
    s = Site(lambda base: {"/r": (301, {"Location": base + "/x"}, b""), "/x": (200, HTML, b"x")})
    try:
        assert wla.http_fetch(s.base + "/r", follow=False).status == 301
        assert wla.http_fetch(s.base + "/r", follow=True).status == 200
    finally:
        s.close()


def test_image_size_png_and_jpeg():
    assert wla.image_size(png(1200, 630)) == (1200, 630)
    assert wla.image_size(jpeg(800, 418)) == (800, 418)
    assert wla.image_size(b"not an image") is None


def test_og_image_wrong_ratio_is_warned():
    s = Site(lambda base: {
        "/": (200, HTML, f'<html lang="fr"><head><title>Titre de test ok</title><meta property="og:title" content="t"><meta property="og:description" content="d">'
                         f'<meta property="og:type" content="website"><meta name="twitter:card" content="x"><meta property="og:image" content="{base}/sq.png"></head><body></body></html>'.encode()),
        "/sq.png": (200, {"Content-Type": "image/png"}, png(600, 600)),
    })
    try:
        assert run(s)["og-image"].status == wla.WARN
    finally:
        s.close()


def test_spa_shell_is_reported_honestly():
    html = b'<!doctype html><html lang="fr"><head><title>App | X</title></head><body><div id="root"></div><script src="/a.js"></script></body></html>'
    s = Site(lambda base: {"/": (200, HTML, html)})
    try:
        res = run(s)
        for k in ("legal-links", "forms", "links", "images"):
            assert res[k].status == wla.INFO
        assert "JavaScript" in res["legal-links"].message
    finally:
        s.close()


def test_parser_handles_label_nesting_and_anchor_text():
    d = wla.parse_html('<label>Nom <input id="a"></label><input id="b"><label for="c">C</label><input id="c"><a href="/x">  Mentions\n légales </a>')
    assert d.inputs[0]["in_label"] is True and d.inputs[1]["in_label"] is False
    assert "c" in d.label_for
    assert d.anchors == [("/x", "Mentions légales")]


def test_cli_exit_codes_and_json(good, bad, capsys):
    assert wla.main([good.base, "--no-color"]) == 0
    assert wla.main([bad.base, "--no-color"]) == 1
    capsys.readouterr()
    assert wla.main([good.base, "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert {"id", "status", "message"} <= set(data[0])
    assert wla.main(["http://127.0.0.1:1/", "--no-color"]) == 2
    assert wla.main(["ftp://x"]) == 2


def test_fail_on_warn_makes_warnings_fatal(bad):
    # a site with only warnings: valid title/description/og, but cookie without flags
    def routes(base):
        r = good_routes(base)
        r["/"] = (200, {**r["/"][1], "Set-Cookie": "sid=1"}, r["/"][2])
        return r

    s = Site(routes)
    try:
        assert wla.main([s.base, "--no-color"]) == 0
        assert wla.main([s.base, "--no-color", "--fail-on", "warn"]) == 1
    finally:
        s.close()
