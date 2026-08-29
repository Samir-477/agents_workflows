from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit, urlunsplit


class UnsafeTargetError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ValidatedTarget:
    url: str
    origin: str


def normalize_http_url(raw_url: str) -> str:
    candidate = raw_url.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parsed = urlsplit(candidate)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise UnsafeTargetError("Only http and https URLs are supported")
    if not parsed.hostname:
        raise UnsafeTargetError("The URL must include a hostname")
    if parsed.username or parsed.password:
        raise UnsafeTargetError("URLs containing credentials are not accepted")
    try:
        port = parsed.port
    except ValueError as exc:
        raise UnsafeTargetError("The URL contains an invalid port") from exc
    hostname = parsed.hostname.rstrip(".").lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".localhost"):
        raise UnsafeTargetError("Localhost targets are not allowed")
    netloc = hostname
    if ":" in hostname and not hostname.startswith("["):
        netloc = f"[{hostname}]"
    if port is not None and not (
        parsed.scheme.lower() == "http" and port == 80
        or parsed.scheme.lower() == "https" and port == 443
    ):
        netloc = f"{netloc}:{port}"
    path = parsed.path or "/"
    normalized = SplitResult(
        scheme=parsed.scheme.lower(),
        netloc=netloc,
        path=path,
        query=parsed.query,
        fragment="",
    )
    return urlunsplit(normalized)


async def validate_public_target(
    raw_url: str, *, allow_private_networks: bool = False
) -> ValidatedTarget:
    url = normalize_http_url(raw_url)
    parsed = urlsplit(url)
    hostname = parsed.hostname
    assert hostname is not None
    try:
        addresses = await asyncio.to_thread(
            socket.getaddrinfo,
            hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise UnsafeTargetError(f"Could not resolve hostname: {hostname}") from exc
    if not addresses:
        raise UnsafeTargetError(f"Could not resolve hostname: {hostname}")
    if not allow_private_networks:
        for address in {item[4][0] for item in addresses}:
            ip = ipaddress.ip_address(address)
            if not ip.is_global:
                raise UnsafeTargetError(
                    "The target resolves to a private, local, reserved, or otherwise unsafe address"
                )
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return ValidatedTarget(url=url, origin=origin)
