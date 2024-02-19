from lilya.routing import Path, WebSocketPath

from .views import another, home, update_product, world_socket

my_urls = [
    Path(
        "/product/{product_id}",
        handler=update_product,
        methods=["PUT"],
    ),
    Path("/", handler=home),
    Path("/another", handler=another),
    WebSocketPath(
        "/{path_param:str}",
        handler=world_socket,
    ),
]
