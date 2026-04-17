#!/usr/bin/env python3
"""
subenum — Subdomain + Directory + VHost Enumerator
Zero external dependencies. Python 3.8+
"""

import asyncio
import argparse
import hashlib
import http.client
import random
import re
import os
import socket
import ssl
import string
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Set, Tuple

os.system("clear")
# ─────────────────────────────────────────────
#  ANSI Colors
# ─────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    GREEN   = "\033[38;5;82m"
    RED     = "\033[38;5;196m"
    YELLOW  = "\033[38;5;220m"
    CYAN    = "\033[38;5;51m"
    GRAY    = "\033[38;5;240m"
    WHITE   = "\033[38;5;255m"
    ORANGE  = "\033[38;5;208m"
    BLUE    = "\033[38;5;39m"
    MAGENTA = "\033[38;5;213m"


# ─────────────────────────────────────────────
#  Takeover signatures
# ─────────────────────────────────────────────
TAKEOVER_SIGNATURES = {
    "GitHub Pages": ["There isn't a GitHub Pages site here"],
    "Heroku":       ["No such app", "herokucdn.com"],
    "Amazon S3":    ["NoSuchBucket", "The specified bucket does not exist"],
    "Netlify":      ["Not Found - Request ID"],
    "Shopify":      ["Sorry, this shop is currently unavailable"],
    "Ghost":        ["The thing you were looking for is no longer here"],
    "Zendesk":      ["Help Center Closed"],
    "Surge.sh":     ["project not found"],
    "Fastly":       ["Fastly error: unknown domain"],
    "Azure":        ["404 Web Site not found"],
    "Tumblr":       ["There's nothing here"],
    "WordPress":    ["Do you want to register"],
}


# ─────────────────────────────────────────────
#  Result dataclasses
# ─────────────────────────────────────────────
@dataclass
class SubdomainResult:
    subdomain: str
    ip: str
    status: Optional[int]           = None
    size: Optional[int]             = None
    title: Optional[str]            = None
    takeover: bool                  = False
    takeover_service: Optional[str] = None


@dataclass
class DirResult:
    path: str
    status: int
    size: int
    title: Optional[str]    = None
    redirect: Optional[str] = None


@dataclass
class VhostResult:
    vhost: str
    status: int
    size: int
    words: int
    lines: int
    title: Optional[str]    = None
    redirect: Optional[str] = None


# ─────────────────────────────────────────────
#  Banner
# ─────────────────────────────────────────────
def print_banner():
    print(f"""
{C.CYAN}{C.BOLD}\
  ███████╗██╗   ██╗██████╗ ███████╗███╗   ██╗██╗   ██╗███╗   ███╗
  ██╔════╝██║   ██║██╔══██╗██╔════╝████╗  ██║██║   ██║████╗ ████║
  ███████╗██║   ██║██████╔╝█████╗  ██╔██╗ ██║██║   ██║██╔████╔██║
  ╚════██║██║   ██║██╔══██╗██╔══╝  ██║╚██╗██║██║   ██║██║╚██╔╝██║
  ███████║╚██████╔╝██████╔╝███████╗██║ ╚████║╚██████╔╝██║ ╚═╝ ██║
  ╚══════╝ ╚═════╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝
{C.RESET}{C.GRAY}  Subdomain & Directory Enumerator v3.0  —  zero deps, pure Python{C.RESET}
""")


# ─────────────────────────────────────────────
#  Config headers
# ─────────────────────────────────────────────
def print_config_sub(args, total):
    sep = f"{C.GRAY}{'─' * 62}{C.RESET}"
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    print(sep)
    print(f"  {C.GRAY}Mode      {C.RESET}: {C.CYAN}subdomain{C.RESET}")
    print(f"  {C.GRAY}Target    {C.RESET}: {C.WHITE}{args.domain}{C.RESET}")
    print(f"  {C.GRAY}Wordlist  {C.RESET}: {C.WHITE}{args.wordlist}{C.RESET} {C.GRAY}({total} words){C.RESET}")
    print(f"  {C.GRAY}Threads   {C.RESET}: {C.WHITE}{args.threads}{C.RESET}")
    print(f"  {C.GRAY}Timeout   {C.RESET}: {C.WHITE}{args.timeout}s{C.RESET}")
    print(f"  {C.GRAY}HTTP probe{C.RESET}: {C.WHITE}{'no' if args.dns_only else 'yes'}{C.RESET}")
    print(f"  {C.GRAY}Started   {C.RESET}: {C.WHITE}{now}{C.RESET}")
    print(sep)
    print()
    print(f"  {C.GRAY}{'SUBDOMAIN':<45} {'IP':<18} {'STATUS':<8} {'SIZE':<8} TITLE{C.RESET}")
    print(f"  {C.GRAY}{'─'*45} {'─'*16} {'─'*6} {'─'*7} {'─'*20}{C.RESET}")


def print_config_dir(args, total):
    sep = f"{C.GRAY}{'─' * 62}{C.RESET}"
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    print(sep)
    print(f"  {C.GRAY}Mode      {C.RESET}: {C.BLUE}directory{C.RESET}")
    print(f"  {C.GRAY}Target    {C.RESET}: {C.WHITE}{args.url}{C.RESET}")
    print(f"  {C.GRAY}Wordlist  {C.RESET}: {C.WHITE}{args.wordlist}{C.RESET} {C.GRAY}({total} words){C.RESET}")
    print(f"  {C.GRAY}Threads   {C.RESET}: {C.WHITE}{args.threads}{C.RESET}")
    print(f"  {C.GRAY}Timeout   {C.RESET}: {C.WHITE}{args.timeout}s{C.RESET}")
    ext_str = args.ext if args.ext else "none"
    print(f"  {C.GRAY}Extensions{C.RESET}: {C.WHITE}{ext_str}{C.RESET}")
    print(f"  {C.GRAY}Started   {C.RESET}: {C.WHITE}{now}{C.RESET}")
    print(sep)
    print()
    print(f"  {C.GRAY}{'PATH':<45} {'STATUS':<8} {'SIZE':<10} TITLE / REDIRECT{C.RESET}")
    print(f"  {C.GRAY}{'─'*45} {'─'*6} {'─'*9} {'─'*25}{C.RESET}")


def print_config_vhost(args, total, target_ip):
    sep = f"{C.GRAY}{'─' * 62}{C.RESET}"
    now = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    fc_str = args.fc if args.fc else "none"
    ms_str = args.ms if args.ms else "none"
    mc_str = args.mc if args.mc else "200,301,302,307,401,403"
    fw_str = args.fw if args.fw else "none"
    fl_str = args.fl if args.fl else "none"
    fs_str = args.fs if args.fs else "none"
    print(sep)
    print(f"  {C.GRAY}Mode         {C.RESET}: {C.MAGENTA}vhost{C.RESET}")
    print(f"  {C.GRAY}Domain       {C.RESET}: {C.WHITE}{args.domain}{C.RESET}")
    print(f"  {C.GRAY}Target IP    {C.RESET}: {C.WHITE}{target_ip}:{args.port}{C.RESET}")
    print(f"  {C.GRAY}Wordlist     {C.RESET}: {C.WHITE}{args.wordlist}{C.RESET} {C.GRAY}({total} words){C.RESET}")
    print(f"  {C.GRAY}Threads      {C.RESET}: {C.WHITE}{args.threads}{C.RESET}")
    print(f"  {C.GRAY}Timeout      {C.RESET}: {C.WHITE}{args.timeout}s{C.RESET}")
    print(f"  {C.GRAY}SSL          {C.RESET}: {C.WHITE}{'yes' if args.ssl else 'no'}{C.RESET}")
    print(f"  {C.GRAY}Match codes  {C.RESET}: {C.WHITE}{mc_str}{C.RESET}")
    print(f"  {C.GRAY}Filter codes {C.RESET}: {C.WHITE}{fc_str}{C.RESET}")
    print(f"  {C.GRAY}Filter size  {C.RESET}: {C.WHITE}{fs_str}{C.RESET}")
    print(f"  {C.GRAY}Filter words {C.RESET}: {C.WHITE}{fw_str}{C.RESET}")
    print(f"  {C.GRAY}Filter lines {C.RESET}: {C.WHITE}{fl_str}{C.RESET}")
    print(f"  {C.GRAY}Match size   {C.RESET}: {C.WHITE}{ms_str}{C.RESET}")
    print(f"  {C.GRAY}Started      {C.RESET}: {C.WHITE}{now}{C.RESET}")
    print(sep)
    print()
    print(f"  {C.GRAY}{'VHOST':<45} {'STATUS':<8} {'SIZE':<10} {'WORDS':<8} {'LINES':<7} TITLE{C.RESET}")
    print(f"  {C.GRAY}{'─'*45} {'─'*6} {'─'*9} {'─'*7} {'─'*6} {'─'*20}{C.RESET}")


# ─────────────────────────────────────────────
#  Result printers
# ─────────────────────────────────────────────
def status_color(code):
    if code is None:       return C.GRAY
    if 200 <= code < 300:  return C.GREEN
    if 300 <= code < 400:  return C.CYAN
    if code == 403:        return C.ORANGE
    return C.YELLOW


def print_sub_result(r: SubdomainResult):
    code_str = str(r.status) if r.status else "—"
    size_str = str(r.size)   if r.size is not None else "—"
    sc       = status_color(r.status)
    tag      = f"  {C.RED}{C.BOLD}[TAKEOVER: {r.takeover_service}]{C.RESET}" if r.takeover else ""

    if r.title and r.title.startswith("→ "):
        loc       = r.title[2:]
        short     = (loc[:48] + "…") if len(loc) > 48 else loc
        title_fmt = f"{C.CYAN}→ {short}{C.RESET}"
    else:
        short     = (r.title[:28] + "…") if r.title and len(r.title) > 28 else (r.title or "")
        title_fmt = f"{C.DIM}{short}{C.RESET}"

    print(
        f"  {C.GREEN}{r.subdomain:<45}{C.RESET}"
        f"{C.WHITE}{r.ip:<18}{C.RESET}"
        f"{sc}{code_str:<8}{C.RESET}"
        f"{C.GRAY}{size_str:<8}{C.RESET}"
        f"{title_fmt}{tag}"
    )


def print_dir_result(r: DirResult):
    sc       = status_color(r.status)
    size_str = f"{r.size}B"
    extra    = ""
    if r.redirect:
        short = r.redirect[:35] + "…" if len(r.redirect) > 35 else r.redirect
        extra = f"{C.CYAN}→ {short}{C.RESET}"
    elif r.title:
        short = r.title[:35] + "…" if len(r.title) > 35 else r.title
        extra = f"{C.DIM}{short}{C.RESET}"
    print(
        f"  {C.GREEN}{r.path:<45}{C.RESET}"
        f"{sc}{r.status:<8}{C.RESET}"
        f"{C.GRAY}{size_str:<10}{C.RESET}"
        f"{extra}"
    )


def print_vhost_result(r: VhostResult):
    sc       = status_color(r.status)
    size_str = f"{r.size}B"
    extra    = ""
    if r.redirect:
        short = r.redirect[:25] + "…" if len(r.redirect) > 25 else r.redirect
        extra = f"{C.CYAN}→ {short}{C.RESET}"
    elif r.title:
        short = r.title[:25] + "…" if len(r.title) > 25 else r.title
        extra = f"{C.DIM}{short}{C.RESET}"
    print(
        f"  {C.MAGENTA}{r.vhost:<45}{C.RESET}"
        f"{sc}{r.status:<8}{C.RESET}"
        f"{C.GRAY}{size_str:<10}{C.RESET}"
        f"{C.GRAY}{r.words:<8}{C.RESET}"
        f"{C.GRAY}{r.lines:<7}{C.RESET}"
        f"{extra}"
    )


# ─────────────────────────────────────────────
#  Progress bar
# ─────────────────────────────────────────────
class Progress:
    def __init__(self, total: int):
        self.total   = total
        self.current = 0
        self.found   = 0
        self.start   = time.monotonic()
        self._lock   = asyncio.Lock()

    async def tick(self):
        async with self._lock:
            self.current += 1
            self._render()

    async def hit(self):
        async with self._lock:
            self.found += 1

    def _render(self):
        elapsed = time.monotonic() - self.start
        rate    = self.current / elapsed if elapsed > 0 else 0
        pct     = (self.current / self.total * 100) if self.total else 0
        bar_w   = 20
        filled  = int(bar_w * self.current / self.total) if self.total else 0
        bar     = "█" * filled + "░" * (bar_w - filled)
        eta     = (self.total - self.current) / rate if rate > 0 else 0
        line    = (
            f"\r  {C.GRAY}[{C.CYAN}{bar}{C.GRAY}]"
            f" {pct:5.1f}%"
            f"  {self.current}/{self.total}"
            f"  {rate:6.0f}/s"
            f"  ETA: {eta:4.0f}s"
            f"  Found: {C.GREEN}{self.found}{C.GRAY}{C.RESET}   "
        )
        sys.stderr.write(line)
        sys.stderr.flush()

    def clear(self):
        sys.stderr.write("\r" + " " * 100 + "\r")
        sys.stderr.flush()


# ─────────────────────────────────────────────
#  Low-level HTTP
# ─────────────────────────────────────────────
def _make_ssl_ctx() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode    = ssl.CERT_NONE
    return ctx


def _raw_request(
    host: str,
    port: int,
    use_ssl: bool,
    path: str,
    timeout: float,
    host_header: Optional[str] = None,
) -> Tuple[Optional[int], Optional[bytes], Optional[str]]:
    h = host_header or host
    try:
        if use_ssl:
            conn = http.client.HTTPSConnection(host, port, timeout=timeout, context=_make_ssl_ctx())
        else:
            conn = http.client.HTTPConnection(host, port, timeout=timeout)

        conn.request("GET", path, headers={
            "User-Agent": "subenum/3.0",
            "Host": h,
            "Accept": "*/*",
            "Connection": "keep-alive",  # 🔥 mudou aqui
        })

        resp   = conn.getresponse()
        status = resp.status
        loc    = resp.getheader("Location", None)
        body   = resp.read(50000)  # 🔥 reduzi de 500k → 50k

        conn.close()
        return status, body, loc
    except Exception:
        return None, None, None


def _follow_redirects(
    host: str,
    port: int,
    use_ssl: bool,
    path: str,
    timeout: float,
    max_hops: int = 5,
) -> Tuple[Optional[int], Optional[bytes], Optional[str]]:
    """Follow redirects up to max_hops. Returns (final_status, body, last_location)."""
    last_loc = None
    for _ in range(max_hops):
        status, body, loc = _raw_request(host, port, use_ssl, path, timeout)
        if status is None:
            return None, None, None
        if status in (301, 302, 303, 307, 308) and loc:
            last_loc = loc
            if loc.startswith("http"):
                m = re.match(r"(https?)://([^/]+)(.*)", loc)
                if m:
                    use_ssl = m.group(1) == "https"
                    hp      = m.group(2)
                    path    = m.group(3) or "/"
                    if ":" in hp:
                        host, port = hp.rsplit(":", 1)
                        port = int(port)
                    else:
                        host = hp
                        port = 443 if use_ssl else 80
            else:
                path = loc
            continue
        return status, body, last_loc
    return None, None, last_loc


def extract_title(body: bytes) -> Optional[str]:
    text = body.decode("utf-8", errors="replace")
    m    = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    return m.group(1).strip()[:80] if m else None


def body_stats(body: bytes) -> Tuple[int, int, int]:
    """Returns (size_bytes, word_count, line_count) — mirrors ffuf metrics."""
    text  = body.decode("utf-8", errors="replace") if body else ""
    size  = len(body) if body else 0
    words = len(text.split())
    lines = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    return size, words, lines


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


# ─────────────────────────────────────────────
#  Subdomain helpers
# ─────────────────────────────────────────────
async def dns_resolve(host: str, loop, timeout: float) -> Optional[str]:
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, socket.gethostbyname, host),
            timeout=timeout,
        )
    except Exception:
        return None


async def detect_wildcard_dns(domain: str, loop, timeout: float) -> Set[str]:
    ips = set()
    for _ in range(3):
        rand = "".join(random.choices(string.ascii_lowercase, k=14))
        ip   = await dns_resolve(f"{rand}.{domain}", loop, timeout)
        if ip:
            ips.add(ip)
    return ips


def _wildcard_body_hash(domain: str, timeout: float) -> Optional[str]:
    rand = "".join(random.choices(string.ascii_lowercase, k=14))
    host = f"{rand}.{domain}"
    for use_ssl, port in ((True, 443), (False, 80)):
        _, body, _ = _raw_request(host, port, use_ssl, "/", timeout)
        if body is not None:
            return md5(body)
    return None


def _probe_subdomain(host: str, timeout: float, wildcard_hash: Optional[str], filter_codes: Set[int]):
    """Try HTTPS then HTTP. Returns (status, size, title_or_redirect, takeover, service)."""
    status = size = title = None
    takeover, service = False, None

    for use_ssl, port in ((True, 443), (False, 80)):
        s, body, loc = _raw_request(host, port, use_ssl, "/", timeout)
        if s is None:
            continue

        # Follow a single HTTP→HTTPS upgrade
        if not use_ssl and s in (301, 302, 303, 307, 308) and loc and loc.startswith("https://"):
            s2, body2, loc2 = _raw_request(host, 443, True, "/", timeout)
            if s2 is not None:
                s, body, loc = s2, body2, loc2

        if s in filter_codes:
            return None, None, None, False, None

        if wildcard_hash and body and md5(body) == wildcard_hash:
            return None, None, None, False, None

        size = len(body) if body else 0

        if loc and s in (301, 302, 303, 307, 308):
            title = f"→ {loc}"
        else:
            title = extract_title(body) if body else None

        # Takeover check
        text = (body or b"").decode("utf-8", errors="replace")
        for svc, sigs in TAKEOVER_SIGNATURES.items():
            for sig in sigs:
                if sig.lower() in text.lower():
                    return s, size, title, True, svc

        return s, size, title, False, None

    return None, None, None, False, None


# ─────────────────────────────────────────────
#  Directory helpers
# ─────────────────────────────────────────────
def parse_url(url: str):
    m = re.match(r"(https?)://([^/]+)(.*)", url)
    if not m:
        raise ValueError(f"Invalid URL: {url}")
    scheme, hostpart, path = m.group(1), m.group(2), m.group(3) or "/"
    use_ssl = scheme == "https"
    if ":" in hostpart:
        host, port = hostpart.rsplit(":", 1)
        port = int(port)
    else:
        host = hostpart
        port = 443 if use_ssl else 80
    return host, port, use_ssl, path.rstrip("/")


def _get_baseline_dir(host: str, port: int, use_ssl: bool, base_path: str, timeout: float):
    rand   = "".join(random.choices(string.ascii_lowercase, k=16))
    path   = f"{base_path}/{rand}"
    s, body, loc = _raw_request(host, port, use_ssl, path, timeout)
    if body is None:
        return None, None, None, None
    size, words, lines = body_stats(body)
    return s, md5(body), size, loc


def _probe_dir(
    host, port, use_ssl, path, timeout,
    baseline_status, baseline_hash, baseline_size, baseline_redirect,
    home_hash, filter_codes,
):
    status, body, loc = _raw_request(host, port, use_ssl, path, timeout)
    if status is None or status in filter_codes:
        return None

    if not body:
        return None

    bsize = len(body)
    bh = md5(body)

    if home_hash and bh == home_hash:
        return None
    if baseline_hash and bh == baseline_hash:
        return None
    if baseline_status is not None and status == baseline_status and baseline_size is not None:
        ratio = abs(bsize - baseline_size) / (baseline_size + 1)
        if ratio < 0.05:
            return None
    if baseline_redirect and loc and baseline_redirect == loc:
        return None

    title = extract_title(body) if 200 <= status < 300 else None
    return DirResult(path=path, status=status, size=bsize, title=title, redirect=loc)


# ─────────────────────────────────────────────
#  Async native HTTP for dir mode  ← TURBO ENGINE
# ─────────────────────────────────────────────
async def _async_http_request(
    host: str, port: int, use_ssl: bool, path: str, timeout: float
) -> Tuple[Optional[int], Optional[bytes], Optional[str]]:
    """
    Fully async HTTP/1.1 GET using asyncio.open_connection.
    No threads, no blocking — genuine concurrency.
    """
    try:
        if use_ssl:
            ssl_ctx = _make_ssl_ctx()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port, ssl=ssl_ctx), timeout=timeout
            )
        else:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=timeout
            )

        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n"
            f"User-Agent: subenum/3.0\r\n"
            f"Accept: */*\r\n"
            f"Connection: close\r\n\r\n"
        )
        writer.write(request.encode())
        await writer.drain()

        raw = await asyncio.wait_for(reader.read(65536), timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass

        return _parse_http_response(raw)

    except Exception:
        return None, None, None


def _parse_http_response(raw: bytes) -> Tuple[Optional[int], Optional[bytes], Optional[str]]:
    """Parse a raw HTTP/1.1 response. Returns (status, body, location)."""
    if not raw:
        return None, None, None

    sep = raw.find(b"\r\n\r\n")
    if sep == -1:
        return None, None, None

    header_bytes = raw[:sep]
    body         = raw[sep + 4:]

    first_line = header_bytes.split(b"\r\n", 1)[0]
    parts      = first_line.split(b" ", 2)
    if len(parts) < 2:
        return None, None, None
    try:
        status = int(parts[1])
    except ValueError:
        return None, None, None

    loc = None
    content_length = None
    connection_close = False
    for line in header_bytes.split(b"\r\n")[1:]:
        ll = line.lower()
        if ll.startswith(b"location:"):
            loc = line[9:].strip().decode("utf-8", errors="replace")
        elif ll.startswith(b"content-length:"):
            try:
                content_length = int(line[15:].strip())
            except ValueError:
                pass
        elif ll.startswith(b"connection:") and b"close" in ll:
            connection_close = True

    return status, body, loc, content_length, connection_close


class AsyncConnection:
    """
    Persistent async HTTP/1.1 connection with keep-alive.
    Automatically reconnects on failure or server close.
    One instance per dir_worker — no sharing, no locks needed.
    """
    MAX_REQS = 200  # reconnect after this many requests (avoids server-side idle close)

    def __init__(self, host: str, port: int, use_ssl: bool, timeout: float):
        self.host    = host
        self.port    = port
        self.use_ssl = use_ssl
        self.timeout = timeout
        self._reader = None
        self._writer = None
        self._req_count = 0

    async def _connect(self):
        self._reader = self._writer = None
        try:
            if self.use_ssl:
                ssl_ctx = _make_ssl_ctx()
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port, ssl=ssl_ctx),
                    timeout=self.timeout,
                )
            else:
                self._reader, self._writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, self.port),
                    timeout=self.timeout,
                )
            self._req_count = 0
        except Exception:
            self._reader = self._writer = None

    def _is_alive(self) -> bool:
        if self._writer is None or self._writer.is_closing():
            return False
        if self._req_count >= self.MAX_REQS:
            return False
        return True

    async def _close(self):
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._reader = self._writer = None

    async def get(self, path: str) -> Tuple[Optional[int], Optional[bytes], Optional[str]]:
        for attempt in range(3):
            if not self._is_alive():
                await self._close()
                await self._connect()
                if not self._is_alive():
                    return None, None, None

            try:
                request = (
                    f"GET {path} HTTP/1.1\r\n"
                    f"Host: {self.host}:{self.port}\r\n"
                    f"User-Agent: subenum/3.0\r\n"
                    f"Accept: */*\r\n"
                    f"Connection: keep-alive\r\n\r\n"
                )
                self._writer.write(request.encode())
                await asyncio.wait_for(self._writer.drain(), timeout=self.timeout)

                # Read response with Content-Length awareness
                raw = await asyncio.wait_for(
                    self._reader.read(131072), timeout=self.timeout
                )
                self._req_count += 1

                parsed = _parse_http_response(raw)
                if parsed[0] is None:
                    # Bad response — reconnect next round
                    await self._close()
                    continue

                status, body, loc, content_length, conn_close = parsed

                # If server signals close, mark for reconnect
                if conn_close:
                    await self._close()

                return status, body, loc

            except Exception:
                await self._close()
                continue

        return None, None, None

    async def get_vhost(self, path: str, host_header: str) -> Tuple[Optional[int], Optional[bytes], Optional[str]]:
        """Same as get() but sends a custom Host header (for vhost enumeration)."""
        for attempt in range(3):
            if not self._is_alive():
                await self._close()
                await self._connect()
                if not self._is_alive():
                    return None, None, None

            try:
                request = (
                    f"GET {path} HTTP/1.1\r\n"
                    f"Host: {host_header}\r\n"
                    f"User-Agent: subenum/3.0\r\n"
                    f"Accept: */*\r\n"
                    f"Connection: keep-alive\r\n\r\n"
                )
                self._writer.write(request.encode())
                await asyncio.wait_for(self._writer.drain(), timeout=self.timeout)

                raw = await asyncio.wait_for(
                    self._reader.read(131072), timeout=self.timeout
                )
                self._req_count += 1

                parsed = _parse_http_response(raw)
                if parsed[0] is None:
                    await self._close()
                    continue

                status, body, loc, content_length, conn_close = parsed
                if conn_close:
                    await self._close()

                return status, body, loc

            except Exception:
                await self._close()
                continue

        return None, None, None

    async def close(self):
        await self._close()


async def _async_probe_dir(
    conn: "AsyncConnection", path: str,
    baseline_status, baseline_hash, baseline_size, baseline_redirect,
    home_hash, filter_codes: set,
) -> Optional[DirResult]:
    """Async version of _probe_dir — reuses persistent AsyncConnection."""
    status, body, loc = await conn.get(path)
    if status is None or status in filter_codes:
        return None
    if not body:
        # allow empty-body redirects through
        if status not in (301, 302, 303, 307, 308):
            return None
        body = b""

    bsize = len(body)
    bh    = md5(body) if body else ""

    if home_hash and bh == home_hash:
        return None
    if baseline_hash and bh == baseline_hash:
        return None
    if baseline_status is not None and status == baseline_status and baseline_size is not None:
        ratio = abs(bsize - baseline_size) / (baseline_size + 1)
        if ratio < 0.05:
            return None
    if baseline_redirect and loc and baseline_redirect == loc:
        return None

    title = extract_title(body) if body and 200 <= status < 300 else None
    return DirResult(path=path, status=status, size=bsize, title=title, redirect=loc)


# ─────────────────────────────────────────────
#  VHost helpers  ← REWRITTEN
# ─────────────────────────────────────────────
class VhostBaseline:
    """
    Holds multiple baseline samples to robustly detect catch-all responses.
    Mirrors what ffuf does: collect N random-vhost responses, then use
    size / word / line thresholds to filter false positives.
    """
    def __init__(self):
        self.samples: list = []  # list of (status, size, words, lines, body_hash, redirect)

    def add(self, status, body, redirect):
        if body is None:
            return
        size, words, lines = body_stats(body)
        self.samples.append((status, size, words, lines, md5(body), redirect))

    def _avg(self, idx):
        vals = [s[idx] for s in self.samples if s[idx] is not None]
        return sum(vals) / len(vals) if vals else 0

    @property
    def statuses(self) -> Set[int]:
        return {s[0] for s in self.samples if s[0] is not None}

    @property
    def hashes(self) -> Set[str]:
        return {s[4] for s in self.samples}

    @property
    def redirects(self) -> Set[str]:
        return {s[5] for s in self.samples if s[5]}

    @property
    def avg_size(self) -> float:
        return self._avg(1)

    @property
    def avg_words(self) -> float:
        return self._avg(2)

    @property
    def avg_lines(self) -> float:
        return self._avg(3)

    def is_false_positive(
        self,
        status: int,
        size: int,
        words: int,
        lines: int,
        body_hash: str,
        redirect: Optional[str],
        filter_codes: Set[int],
        match_codes: Set[int],
        filter_sizes: Optional[Set[int]],
        filter_words: Optional[Set[int]],
        filter_lines: Optional[Set[int]],
        match_sizes: Optional[Set[int]],
    ) -> bool:
        # ── explicit match/filter rules (ffuf-style) ──────────────────────
        if match_codes and status not in match_codes:
            return True
        if filter_codes and status in filter_codes:
            return True
        if filter_sizes and size in filter_sizes:
            return True
        if filter_words and words in filter_words:
            return True
        if filter_lines and lines in filter_lines:
            return True
        if match_sizes and size not in match_sizes:
            return True

        # ── baseline-based automatic filtering ────────────────────────────
        if not self.samples:
            return False

        # Identical body hash to any baseline sample
        if body_hash in self.hashes:
            return True

        # Redirect to same target as baseline
        if redirect and redirect in self.redirects:
            return True

        # Same status AND (size similar OR words similar) — must be consistent
        # across ALL baseline samples to avoid false filtering.
        # We only auto-filter when BOTH size AND words are close to the baseline.
        if status in self.statuses:
            avg_s = self.avg_size
            avg_w = self.avg_words
            size_close  = avg_s > 0 and abs(size  - avg_s) / (avg_s + 1) < 0.05
            words_close = avg_w > 0 and abs(words - avg_w) / (avg_w + 1) < 0.05
            # Only filter when BOTH metrics are close (reduces false filtering)
            if size_close and words_close:
                return True

        return False


async def _collect_vhost_baseline_async(
    ip: str, port: int, use_ssl: bool, domain: str, timeout: float, n: int = 3
) -> VhostBaseline:
    bl   = VhostBaseline()
    conn = AsyncConnection(ip, port, use_ssl, timeout)
    for _ in range(n):
        rand = "".join(random.choices(string.ascii_lowercase, k=14))
        fake = f"{rand}.{domain}"
        s, body, loc = await conn.get_vhost("/", fake)
        bl.add(s, body, loc)
    await conn.close()
    return bl


async def _async_probe_vhost(
    conn: AsyncConnection,
    host_header: str,
    baseline: VhostBaseline,
    filter_codes: Set[int],
    match_codes: Set[int],
    filter_sizes: Optional[Set[int]],
    filter_words: Optional[Set[int]],
    filter_lines: Optional[Set[int]],
    match_sizes: Optional[Set[int]],
) -> Optional[VhostResult]:
    status, body, redirect = await conn.get_vhost("/", host_header)
    if status is None:
        return None

    size, words, lines = body_stats(body)
    bh = md5(body) if body else ""

    if baseline.is_false_positive(
        status, size, words, lines, bh, redirect,
        filter_codes, match_codes,
        filter_sizes, filter_words, filter_lines, match_sizes,
    ):
        return None

    title = extract_title(body) if body and 200 <= status < 300 else None
    return VhostResult(
        vhost=host_header,
        status=status,
        size=size,
        words=words,
        lines=lines,
        title=title,
        redirect=redirect,
    )


# ─────────────────────────────────────────────
#  Workers
# ─────────────────────────────────────────────
async def sub_worker(queue, domain, loop, wildcard_ips, wildcard_hash,
                     results, progress, timeout, dns_only, filter_codes, semaphore):
    while True:
        word = await queue.get()
        if word is None:
            queue.task_done()
            break
        async with semaphore:
            subdomain = f"{word}.{domain}"
            ip = await dns_resolve(subdomain, loop, timeout)

            if not ip or (wildcard_ips and ip in wildcard_ips):
                await progress.tick()
                queue.task_done()
                continue

            if not dns_only:
                status, size, title, takeover, svc = await loop.run_in_executor(
                    None, _probe_subdomain, subdomain, timeout, wildcard_hash, filter_codes
                )
                if status is None and not takeover:
                    await progress.tick()
                    queue.task_done()
                    continue
            else:
                status = size = title = None
                takeover, svc = False, None

            r = SubdomainResult(subdomain, ip, status, size, title, takeover, svc)
            results.append(r)
            await progress.hit()
            progress.clear()
            print_sub_result(r)

        await progress.tick()
        queue.task_done()


async def dir_worker(queue, host, port, use_ssl, base_path,
                     baseline_status, baseline_hash, baseline_size, baseline_redirect,
                     home_hash, results, progress, timeout, filter_codes, semaphore, loop):
    # Each worker owns one persistent connection — keep-alive, no TCP overhead per request
    conn = AsyncConnection(host, port, use_ssl, timeout)
    try:
        while True:
            word = await queue.get()
            if word is None:
                queue.task_done()
                break
            async with semaphore:
                full_path = f"{base_path.rstrip('/')}{word}" if base_path else word

                result = await _async_probe_dir(
                    conn, full_path,
                    baseline_status, baseline_hash, baseline_size, baseline_redirect,
                    home_hash, filter_codes,
                )

                if result:
                    results.append(result)
                    await progress.hit()
                    progress.clear()
                    print_dir_result(result)

            await progress.tick()
            queue.task_done()
    finally:
        await conn.close()


async def vhost_worker(
    queue, ip, port, use_ssl, baseline,
    filter_codes, match_codes,
    filter_sizes, filter_words, filter_lines, match_sizes,
    results, progress, timeout, semaphore, loop, domain,
):
    # One persistent connection per worker — same trick as dir mode
    conn = AsyncConnection(ip, port, use_ssl, timeout)
    try:
        while True:
            word = await queue.get()
            if word is None:
                queue.task_done()
                break
            async with semaphore:
                host_header = f"{word}.{domain}"
                result = await _async_probe_vhost(
                    conn, host_header, baseline,
                    filter_codes, match_codes,
                    filter_sizes, filter_words, filter_lines, match_sizes,
                )
                if result:
                    results.append(result)
                    await progress.hit()
                    progress.clear()
                    print_vhost_result(result)

            await progress.tick()
            queue.task_done()
    finally:
        await conn.close()


# ─────────────────────────────────────────────
#  Mode runners
# ─────────────────────────────────────────────
async def run_subdomain(args):
    try:
        with open(args.wordlist, "r", errors="ignore") as f:
            words = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    except FileNotFoundError:
        print(f"\n  {C.RED}[!] Wordlist not found: {args.wordlist}{C.RESET}\n")
        sys.exit(1)

    print_banner()
    print_config_sub(args, len(words))

    loop         = asyncio.get_event_loop()
    filter_codes = _parse_ints(args.fc) if args.fc else {404}
    semaphore    = asyncio.Semaphore(args.threads)

    wildcard_ips = await detect_wildcard_dns(args.domain, loop, args.timeout)
    if wildcard_ips:
        print(f"\n  {C.YELLOW}[!] Wildcard DNS → {', '.join(wildcard_ips)}  (filtering){C.RESET}\n")

    wildcard_hash = None
    if not args.dns_only:
        wildcard_hash = await loop.run_in_executor(
            None, _wildcard_body_hash, args.domain, args.timeout
        )

    queue    = asyncio.Queue()
    results  = []
    progress = Progress(len(words))

    for w in words:
        await queue.put(w)
    for _ in range(args.threads):
        await queue.put(None)

    tasks = [
        asyncio.create_task(sub_worker(
            queue, args.domain, loop, wildcard_ips, wildcard_hash,
            results, progress, args.timeout, args.dns_only, filter_codes, semaphore,
        ))
        for _ in range(args.threads)
    ]
    await queue.join()
    await asyncio.gather(*tasks)

    _print_footer(progress, len(words), results)

    takeovers = [r for r in results if r.takeover]
    if takeovers:
        print(f"\n  {C.RED}{C.BOLD}[!] Potential takeovers ({len(takeovers)}):{C.RESET}")
        for r in takeovers:
            print(f"      {C.RED}→ {r.subdomain}  [{r.takeover_service}]{C.RESET}")

    _save_output(args, results, mode="sub")


async def run_dir(args):
    try:
        with open(args.wordlist, "r", errors="ignore") as f:
            raw = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    except FileNotFoundError:
        print(f"\n  {C.RED}[!] Wordlist not found: {args.wordlist}{C.RESET}\n")
        sys.exit(1)

    extensions = [e.lstrip(".") for e in args.ext.split(",")] if args.ext else []
    paths_set  = []
    for word in raw:
        word = word.lstrip("/")
        paths_set.append(f"/{word}")
        for ext in extensions:
            paths_set.append(f"/{word}.{ext}")

    try:
        host, port, use_ssl, base_path = parse_url(args.url)
    except ValueError as e:
        print(f"\n  {C.RED}[!] {e}{C.RESET}\n")
        sys.exit(1)

    print_banner()
    print_config_dir(args, len(paths_set))

    loop         = asyncio.get_event_loop()
    filter_codes = _parse_ints(args.fc) if args.fc else {404}
    semaphore    = asyncio.Semaphore(args.threads)

    print(f"  {C.GRAY}[*] Probing baseline (soft-404 detection)...{C.RESET}", end="", flush=True)
    _bl_conn = AsyncConnection(host, port, use_ssl, args.timeout)
    rand = "".join(random.choices(string.ascii_lowercase, k=16))
    _bs_path = f"{base_path.rstrip('/')}/{rand}"
    _bs_status, _bs_body, _bs_loc = await _bl_conn.get(_bs_path)
    if _bs_body is not None:
        _bs_size, _, _ = body_stats(_bs_body)
        baseline_status   = _bs_status
        baseline_hash     = md5(_bs_body)
        baseline_size     = _bs_size
        baseline_redirect = _bs_loc
    else:
        baseline_status = baseline_hash = baseline_size = baseline_redirect = None

    _home_status, home_body, _ = await _bl_conn.get(base_path or "/")
    home_hash = md5(home_body) if home_body else None
    await _bl_conn.close()

    lbl = "catch-all detected" if baseline_status == 200 else "ok"
    print(f"\r  {C.GRAY}[*] Baseline: status={baseline_status}  size={baseline_size}B  {lbl}{C.RESET}          ")
    print()

    queue    = asyncio.Queue()
    results  = []
    progress = Progress(len(paths_set))

    for p in paths_set:
        await queue.put(p)
    for _ in range(args.threads):
        await queue.put(None)

    tasks = [
        asyncio.create_task(dir_worker(
            queue, host, port, use_ssl, base_path,
            baseline_status, baseline_hash, baseline_size, baseline_redirect,
            home_hash, results, progress, args.timeout, filter_codes, semaphore, loop,
        ))
        for _ in range(args.threads)
    ]
    await queue.join()
    await asyncio.gather(*tasks)

    _print_footer(progress, len(paths_set), results)
    _save_output(args, results, mode="dir")


async def run_vhost(args):
    try:
        with open(args.wordlist, "r", errors="ignore") as f:
            words = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    except FileNotFoundError:
        print(f"\n  {C.RED}[!] Wordlist not found: {args.wordlist}{C.RESET}\n")
        sys.exit(1)

    # ── Normalise domain: accept bare domain or full URL ───────────────────
    domain  = args.domain
    use_ssl = args.ssl
    port    = args.port

    if domain.startswith("https://"):
        domain  = domain[len("https://"):].rstrip("/").split("/")[0]
        use_ssl = True
        if port == 80:
            port = 443
    elif domain.startswith("http://"):
        domain = domain[len("http://"):].rstrip("/").split("/")[0]

    # Split embedded port e.g. creative.thm:8080
    if ":" in domain:
        domain, _p = domain.rsplit(":", 1)
        try:
            port = int(_p)
        except ValueError:
            pass

    args.domain = domain  # keep clean for display

    # Resolve target IP
    target_ip = args.ip
    if not target_ip:
        print(f"  {C.GRAY}[*] Resolving {domain}...{C.RESET}", end="", flush=True)
        try:
            target_ip = socket.gethostbyname(domain)
            print(f"\r  {C.GRAY}[*] Resolved → {target_ip}{C.RESET}                    ")
        except Exception:
            print(f"\r  {C.RED}[!] Could not resolve {domain}. Use --ip.{C.RESET}\n")
            sys.exit(1)
    filter_codes = _parse_ints(args.fc) if args.fc else set()
    match_codes  = _parse_ints(args.mc) if args.mc else {200, 301, 302, 307, 401, 403}
    filter_sizes = _parse_ints(args.fs) if args.fs else None
    filter_words = _parse_ints(args.fw) if args.fw else None
    filter_lines = _parse_ints(args.fl) if args.fl else None
    match_sizes  = _parse_ints(args.ms) if args.ms else None
    semaphore    = asyncio.Semaphore(args.threads)
    loop         = asyncio.get_event_loop()

    print_banner()
    print_config_vhost(args, len(words), target_ip)

    # Collect baseline (3 random vhosts)
    print(f"  {C.GRAY}[*] Collecting baseline responses (3 random vhosts)...{C.RESET}", end="", flush=True)
    baseline = await _collect_vhost_baseline_async(target_ip, port, use_ssl, args.domain, args.timeout, 3)

    if baseline.samples:
        sample = baseline.samples[0]
        lbl    = "catch-all" if sample[0] == 200 else "ok"
        print(
            f"\r  {C.GRAY}[*] Baseline: status={sample[0]}  "
            f"size≈{baseline.avg_size:.0f}B  "
            f"words≈{baseline.avg_words:.0f}  "
            f"lines≈{baseline.avg_lines:.0f}  [{lbl}]{C.RESET}          "
        )
    else:
        print(f"\r  {C.GRAY}[*] Baseline: no response from server{C.RESET}                    ")
    print()

    queue    = asyncio.Queue()
    results  = []
    progress = Progress(len(words))

    for w in words:
        await queue.put(w)
    for _ in range(args.threads):
        await queue.put(None)

    tasks = [
        asyncio.create_task(vhost_worker(
            queue, target_ip, port, use_ssl, baseline,
            filter_codes, match_codes,
            filter_sizes, filter_words, filter_lines, match_sizes,
            results, progress, args.timeout, semaphore, loop, args.domain,
        ))
        for _ in range(args.threads)
    ]
    await queue.join()
    await asyncio.gather(*tasks)

    _print_footer(progress, len(words), results)

    if args.output:
        with open(args.output, "w") as f:
            for r in results:
                line = f"{r.vhost} [{r.status}] {r.size}B {r.words}W {r.lines}L"
                if r.redirect:
                    line += f" -> {r.redirect}"
                f.write(line + "\n")
        print(f"\n  {C.GRAY}Results saved → {args.output}{C.RESET}")
    print()


# ─────────────────────────────────────────────
#  Shared helpers
# ─────────────────────────────────────────────
def _parse_ints(s: str) -> Set[int]:
    return {int(x.strip()) for x in s.split(",") if x.strip().isdigit()}


def _print_footer(progress: Progress, total: int, results: list):
    progress.clear()
    elapsed = time.monotonic() - progress.start
    sep     = f"{C.GRAY}{'─' * 62}{C.RESET}"
    print()
    print(sep)
    print(
        f"  {C.GRAY}Done{C.RESET}  "
        f"{C.WHITE}{total}{C.RESET}{C.GRAY} words  ·  {C.RESET}"
        f"{C.WHITE}{elapsed:.1f}s{C.RESET}{C.GRAY}  ·  {C.RESET}"
        f"{C.GREEN}{len(results)} found{C.RESET}"
    )


def _save_output(args, results: list, mode: str):
    if not args.output:
        print()
        return
    with open(args.output, "w") as f:
        for r in results:
            if mode == "sub":
                line = r.subdomain
                if r.status:   line += f" [{r.status}]"
                if r.takeover: line += f" [TAKEOVER:{r.takeover_service}]"
            else:
                line = r.path
                line += f" [{r.status}] {r.size}B"
                if r.redirect: line += f" -> {r.redirect}"
            f.write(line + "\n")
    print(f"\n  {C.GRAY}Results saved → {args.output}{C.RESET}")
    print()


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        prog="subenum",
        description="Subdomain, Directory & VHost Enumerator — zero deps, pure Python",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    sub_parsers = parser.add_subparsers(dest="mode", required=True)

    # ── subdomain ──────────────────────────────────────────────────────────
    sp = sub_parsers.add_parser("sub", help="Subdomain enumeration via DNS + HTTP probe")
    sp.add_argument("domain")
    sp.add_argument("-w", "--wordlist",  required=True)
    sp.add_argument("-t", "--threads",   type=int, default=100)
    sp.add_argument("--timeout",         type=int, default=5)
    sp.add_argument("--dns-only",        action="store_true")
    sp.add_argument("--fc",              metavar="CODES",  help="Filter status codes  e.g. 404,403")
    sp.add_argument("-o", "--output",    metavar="FILE")

    # ── directory ──────────────────────────────────────────────────────────
    dp = sub_parsers.add_parser("dir", help="Directory / path enumeration")
    dp.add_argument("url")
    dp.add_argument("-w", "--wordlist",  required=True)
    dp.add_argument("-t", "--threads",   type=int, default=300)
    dp.add_argument("--timeout",         type=int, default=5)
    dp.add_argument("-x", "--ext",       metavar="EXTS",  help="Extensions  e.g. php,html,txt")
    dp.add_argument("--fc",              metavar="CODES",  help="Filter status codes")
    dp.add_argument("-o", "--output",    metavar="FILE")

    # ── vhost ──────────────────────────────────────────────────────────────
    vp = sub_parsers.add_parser("vhost", help="Virtual host enumeration (ffuf-compatible filters)")
    vp.add_argument("domain",            help="Base domain  e.g. cybercrafted.thm")
    vp.add_argument("-w", "--wordlist",  required=True)
    vp.add_argument("--ip",             metavar="IP",    help="Target IP (skip DNS)")
    vp.add_argument("--port",           type=int, default=80)
    vp.add_argument("--ssl",            action="store_true")
    vp.add_argument("-t", "--threads",   type=int, default=50)
    vp.add_argument("--timeout",         type=int, default=5)
    # ffuf-style filter / match flags
    vp.add_argument("--mc",  metavar="CODES",   help="Match status codes      (default: 200,301,302,307,401,403)")
    vp.add_argument("--fc",  metavar="CODES",   help="Filter status codes     e.g. 400,404")
    vp.add_argument("--fs",  metavar="SIZES",   help="Filter response sizes   e.g. 301")
    vp.add_argument("--fw",  metavar="WORDS",   help="Filter word counts      e.g. 236")
    vp.add_argument("--fl",  metavar="LINES",   help="Filter line counts      e.g. 35")
    vp.add_argument("--ms",  metavar="SIZES",   help="Match response sizes")
    vp.add_argument("-o", "--output",    metavar="FILE")

    args = parser.parse_args()

    try:
        if args.mode == "sub":
            asyncio.run(run_subdomain(args))
        elif args.mode == "dir":
            asyncio.run(run_dir(args))
        else:
            asyncio.run(run_vhost(args))
    except KeyboardInterrupt:
        print(f"\n\n  {C.YELLOW}[!] Interrupted.{C.RESET}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
