from __future__ import annotations

import ipaddress

from lilya.transformers import Transformer, register_path_transformer


class IPTransformer(Transformer[str]):
    regex = r"((25[0-5]|(2[0-4]|1[0-9]|[1-9]|)[0-9])(\.(?!$)|$)){4}$"

    def transform(self, value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address:
        return ipaddress.ip_address(value)

    def normalise(self, value: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str:
        return str(value)


register_path_transformer("ipaddress", IPTransformer())
