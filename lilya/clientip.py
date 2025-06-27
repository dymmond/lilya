from __future__ import annotations

import re
from collections.abc import Sequence

from lilya.datastructures import ALL, Header
from lilya.types import Scope

_forwarded_regex = re.compile(r'for="?([^";, ]+)', re.IGNORECASE)
_http_x_forwarded_regex = re.compile(r'[ "]*([^";, ]+)')
_ip6_port_cleanup_regex = re.compile(r"(?<=\]):[0-9]+$")
_ip4_port_cleanup_regex = re.compile(r":[0-9]+$")


def get_trusted_proxies(value: None | Sequence[str] = None) -> frozenset:
    if value is None:
        from lilya.conf import settings

        value = getattr(settings, "trusted_proxies", ["unix"])
    if "*" in value:
        return ALL
    else:
        return frozenset(value)


def get_ip(scope: Scope, trusted_proxies: None | Sequence[str] = None) -> str:
    """
    Get real client ip, using trustworthy proxies
    Args:
        trusted_proxies (Optional[Sequence[str]]):  List of trusted proxy ips.
                                                    Leave None to use the lily settings.
                                                    Set to ["*"] for trusting all proxies.
                                                    Use "unix" for unix sockets.
    """
    client = scope.get("client")
    if client:
        client_ip = next(iter(client))  # only ip, the port is ignored
    else:
        client_ip = None
    if not client_ip:
        client_ip = "unix"

    if client_ip in get_trusted_proxies(trusted_proxies):
        headers = Header.ensure_header_instance(scope)
        try:
            ip_matches = _forwarded_regex.search(headers["forwarded"])
            client_ip = ip_matches[1]
        except KeyError:
            try:
                ip_matches = _http_x_forwarded_regex.search(headers["x-forwarded-for"])
                client_ip = ip_matches[1]
            except KeyError:
                pass
    if client_ip == "unix":
        raise ValueError("Could not determinate ip address")
    if "." in client_ip and client_ip.count(":") <= 1:
        client_ip = _ip4_port_cleanup_regex.sub("", client_ip)
    else:
        client_ip = _ip6_port_cleanup_regex.sub("", client_ip).strip("[]")

    return client_ip
