from __future__ import annotations

import re
from collections.abc import Callable, Collection, Container

from lilya.datastructures import ALL, Header
from lilya.types import Scope

_forwarded_regex = re.compile(r'for="?([^";, ]+)', re.IGNORECASE)
_http_x_forwarded_regex = re.compile(r'[ "]*([^";, ]+)')
_ip6_port_cleanup_regex = re.compile(r"(?<=\]):[0-9]+$")
_ip4_port_cleanup_regex = re.compile(r":[0-9]+$")


def get_trusted_proxies(value: None | Collection[str] = None) -> Container[str]:
    # shortcut
    if value is ALL or isinstance(value, frozenset):
        return value
    if value is None:
        from lilya.conf import settings

        value = getattr(settings, "trusted_proxies", ["unix"])
    if "*" in value:
        return ALL
    else:
        return frozenset(value)


def get_ip(
    scope: Scope,
    *,
    trusted_proxies: None | Collection[str] = None,
    sanitize_clientip: Callable[[str], str] | None = None,
    sanitize_proxyip: Callable[[str], str] | None = None,
) -> str:
    """
    Get real client ip, using trustworthy proxies
    Args:
        scope (Scope): ASGI Scope
    Kwargs:
        trusted_proxies (Optional[Collection[str]]):  List of trusted proxy ips.
                                                    Leave None to use the lily settings.
                                                    Set to ["*"] for trusting all proxies.
                                                    Use "unix" for unix sockets.
        sanitize_proxyip (Optional[Callable[[str], str]]): Sanitize ip before comparing with proxies (ip of proxy).
        sanitize_clientip (Optional[Callable[[str], str]]): Sanitize ip retrieved from proxy for outputting.
                                                            This is probably what you want to provide.
    """
    client = scope.get("client")
    if client:
        client_ip = next(iter(client))  # only ip, the port is ignored
    else:
        client_ip = None
    if not client_ip:
        client_ip = "unix"

    proxy_ip = client_ip if sanitize_proxyip is None else sanitize_proxyip(client_ip)

    if proxy_ip in get_trusted_proxies(trusted_proxies):
        headers = Header.ensure_header_instance(scope)
        try:
            ip_matches = _forwarded_regex.search(headers["forwarded"])
            if ip_matches is not None:
                client_ip = ip_matches[1]
        except KeyError:
            try:
                ip_matches = _http_x_forwarded_regex.search(headers["x-forwarded-for"])
                if ip_matches is not None:
                    client_ip = ip_matches[1]
            except KeyError:
                pass
    if client_ip == "unix":
        raise ValueError("Could not determinate ip address")
    # strip ports
    if "." in client_ip and client_ip.count(":") <= 1:
        client_ip = _ip4_port_cleanup_regex.sub("", client_ip)
    elif ":" in client_ip:
        client_ip = _ip6_port_cleanup_regex.sub("", client_ip).strip("[]")

    return client_ip if sanitize_clientip is None else sanitize_clientip(client_ip)
