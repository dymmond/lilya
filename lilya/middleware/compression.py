import gzip
import io

from lilya.datastructures import Header
from lilya.protocols.middleware import MiddlewareProtocol
from lilya.types import ASGIApp, Message, Receive, Scope, Send


class GZipMiddleware(MiddlewareProtocol):
    """
    Middleware to compress responses with GZip.

    Args:
        app: The 'next' ASGI app to call.
        minimum_size: Minimum response size to trigger compression.
        compresslevel: GZip compression level (0 to 9).
    """

    def __init__(self, app: ASGIApp, minimum_size: int = 500, compresslevel: int = 9) -> None:
        """
        Initialize GZipMiddleware.

        Args:
            app: The 'next' ASGI app to call.
            minimum_size: Minimum response size to trigger compression.
            compresslevel: GZip compression level (0 to 9).
        """
        self.app = app
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Handles incoming requests, checks for GZip support, and processes the response accordingly.

        Args:
            scope: The ASGI scope.
            receive: The ASGI receive function.
            send: The ASGI send function.
        """
        if scope["type"] == "http":
            headers = Header.from_scope(scope=scope)
            if "gzip" in headers.get("Accept-Encoding", ""):
                responder = GZipResponder(
                    self.app, self.minimum_size, compresslevel=self.compresslevel
                )
                await responder(scope, receive, send)
                return
        await self.app(scope, receive, send)


class GZipResponder:
    """
    Responsible for compressing and responding with GZip-encoded content.

    Args:
        app: The 'next' ASGI app to call.
        minimum_size: Minimum response size to trigger compression.
        compresslevel: GZip compression level (0 to 9).
    """

    def __init__(self, app: ASGIApp, minimum_size: int, compresslevel: int = 9) -> None:
        """
        Initialize GZipResponder.

        Args:
            app: The 'next' ASGI app to call.
            minimum_size: Minimum response size to trigger compression.
            compresslevel: GZip compression level (0 to 9).
        """
        self.app = app
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        Compresses the response content with GZip and sends the compressed response.

        Args:
            scope: The ASGI scope.
            receive: The ASGI receive function.
            send: The ASGI send function.
        """
        response = await self.app(scope, receive, self.get_send_wrapper(send))  # type: ignore
        if "Content-Length" in response["headers"]:  # type: ignore
            del response["headers"]["Content-Length"]  # type: ignore

        response["headers"]["Content-Encoding"] = "gzip"  # type: ignore
        await send(response)

    def get_send_wrapper(self, send: Send) -> Send:
        """
        Wraps the original send function to compress the response content.

        Args:
            send: The original ASGI send function.

        Returns:
            Wrapped send function.
        """

        async def send_wrapper(message: Message) -> None:
            """
            Send function that wraps the original send to compress content.

            Args:
                message: An ASGI 'Message'

            Returns:
                None
            """
            if "body" in message:
                compressed_body = self.compress(message["body"])
                message["body"] = compressed_body

            await send(message)

        return send_wrapper

    def compress(self, body: bytes) -> bytes:
        """
        Compresses the given content using GZip.

        Args:
            body: The content to be compressed.

        Returns:
            Compressed content.
        """
        buffer = io.BytesIO()
        with gzip.GzipFile(
            mode="wb",
            fileobj=buffer,
            compresslevel=self.compresslevel,
        ) as f:
            f.write(body)
        return buffer.getvalue()
