from __future__ import annotations

import ipaddress
import socket
import urllib.parse
import urllib.request
from html.parser import HTMLParser


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._in_title = False
        self._title_parts: list[str] = []
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        t = (tag or "").lower()
        if t in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if t == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        t = (tag or "").lower()
        if t in {"script", "style", "noscript", "svg"} and self._skip_depth > 0:
            self._skip_depth -= 1
        if t == "title":
            self._in_title = False
        if t in {"p", "br", "div", "li", "h1", "h2", "h3", "h4"}:
            self._text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not data:
            return
        if self._in_title:
            self._title_parts.append(data)
        if self._skip_depth > 0:
            return
        self._text_parts.append(data)

    def result(self) -> tuple[str, str]:
        title = " ".join(" ".join(self._title_parts).split()).strip()
        text = "\n".join(line.strip() for line in "".join(self._text_parts).splitlines())
        # Collapse excessive whitespace but keep line breaks.
        text = "\n".join(" ".join(line.split()) for line in text.splitlines())
        text = "\n".join([ln for ln in text.splitlines() if ln.strip()])
        return title, text.strip()


def _is_public_hostname(hostname: str) -> bool:
    h = (hostname or "").strip().lower().strip(".")
    if not h:
        return False
    if h in {"localhost", "localhost.localdomain"}:
        return False
    if h.endswith(".local"):
        return False
    try:
        # If it's a literal IP, validate directly.
        ip = ipaddress.ip_address(h)
        return _is_public_ip(ip)
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(h, None)
    except Exception:
        return False
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            return False
        if not _is_public_ip(ip):
            return False
    return True


def _is_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
        return False
    return True


def validate_public_url(url: str) -> urllib.parse.SplitResult:
    raw = str(url or "").strip()
    if not raw:
        raise ValueError("missing_url")
    parsed = urllib.parse.urlsplit(raw)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("invalid_scheme")
    if not parsed.netloc:
        raise ValueError("invalid_url")
    hostname = parsed.hostname or ""
    if not _is_public_hostname(hostname):
        raise ValueError("url_not_allowed")
    return parsed


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_url_bytes(url: str, *, timeout_s: float = 10.0, max_bytes: int = 1_500_000) -> tuple[str, str, bytes]:
    """Fetch URL content with a conservative size cap. Returns (final_url, content_type, body_bytes)."""
    _ = validate_public_url(url)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "LangHeroBot/0.1 (+https://example.invalid)",
            "Accept": "text/html, text/plain;q=0.9, application/json;q=0.7, */*;q=0.1",
        },
        method="GET",
    )
    opener = urllib.request.build_opener(_SafeRedirectHandler())
    with opener.open(req, timeout=timeout_s) as resp:
        final_url = str(getattr(resp, "geturl", lambda: url)() or url)
        # Validate final URL as well (redirect safety).
        _ = validate_public_url(final_url)
        headers = getattr(resp, "headers", None)
        content_type = ""
        if headers is not None:
            try:
                content_type = str(headers.get("Content-Type") or "")
            except Exception:
                content_type = ""
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise ValueError("content_too_large")
        body = b"".join(chunks)
    return final_url, content_type, body


def extract_text_from_html(html_bytes: bytes, *, max_chars: int = 60_000) -> tuple[str, str]:
    parser = _VisibleTextParser()
    try:
        decoded = html_bytes.decode("utf-8", errors="replace")
    except Exception:
        decoded = str(html_bytes)
    parser.feed(decoded)
    title, text = parser.result()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit("\n", 1)[0].strip() or text[:max_chars]
    return title, text


def fetch_url_text(url: str, *, timeout_s: float = 10.0, max_bytes: int = 1_500_000) -> dict:
    """Fetch and normalize text content from a URL (HTML -> visible text; other -> decoded text)."""
    final_url, content_type, body = fetch_url_bytes(url, timeout_s=timeout_s, max_bytes=max_bytes)
    ctype = (content_type or "").lower()

    title = ""
    text = ""
    if "text/html" in ctype or "application/xhtml+xml" in ctype or (b"<html" in body[:5000].lower()):
        title, text = extract_text_from_html(body)
    else:
        try:
            text = body.decode("utf-8", errors="replace").strip()
        except Exception:
            text = str(body)

    if not text.strip():
        raise ValueError("no_text_found")

    return {
        "url": str(url),
        "final_url": final_url,
        "content_type": content_type,
        "title": title,
        "text": text,
    }
