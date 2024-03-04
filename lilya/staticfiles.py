from __future__ import annotations

import importlib.util
import os
import stat
from email.utils import parsedate
from typing import Union

import anyio
import anyio.to_thread

from lilya._internal._path import get_route_path
from lilya.datastructures import URL, Header
from lilya.exceptions import HTTPException
from lilya.responses import FileResponse, RedirectResponse, Response
from lilya.types import Receive, Scope, Send

PathLike = Union[str, "os.PathLike[str]"]


class StaticResponse(Response):
    NOT_MODIFIED_HEADERS: tuple[str, ...] = (
        "cache-control",
        "content-location",
        "date",
        "etag",
        "expires",
        "vary",
    )

    def __init__(self, headers: Header):
        super().__init__(
            status_code=304,
            headers={
                name: value for name, value in headers.items() if name in self.NOT_MODIFIED_HEADERS
            },
        )


class StaticFiles:
    def __init__(
        self,
        *,
        directory: str | None = None,
        packages: list[str | tuple[str, str]] | None = None,
        html: bool = False,
        check_dir: bool = True,
        follow_symlink: bool = False,
    ) -> None:
        """
        Initialize StaticFiles middleware.

        Args:
            directory (str | None): Base directory for serving static files.
            packages (List[str | Tuple[str, str]] | None): List of packages containing static files.
            html (bool): Flag to enable HTML file handling for directories.
            check_dir (bool): Flag to check if the directory exists.
            follow_symlink (bool): Flag to follow symlinks.
        """
        self.directory = directory
        self.packages = packages
        self.all_directories = self.get_directories(directory, packages)
        self.html = html
        self.config_checked = False
        self.follow_symlink = follow_symlink
        if check_dir and directory is not None and not os.path.isdir(directory):
            raise RuntimeError(f"Directory '{directory}' does not exist")

    def get_directories(
        self,
        directory: str | None = None,
        packages: list[str | tuple[str, str]] | None = None,
    ) -> list[str]:
        """
        Given `directory` and `packages` arguments, return a list of all the
        directories that should be used for serving static files from.

        Args:
            directory (str | None): Base directory for serving static files.
            packages (List[str | Tuple[str, str]] | None): List of packages containing static files.

        Returns:
            List[str]: List of directories.
        """
        directories = []
        if directory is not None:
            directories.append(directory)

        for package in packages or []:
            if isinstance(package, tuple):
                package, statics_dir = package
            else:
                statics_dir = "statics"
            spec = importlib.util.find_spec(package)
            assert spec is not None, f"Package {package!r} could not be found."
            assert spec.origin is not None, f"Package {package!r} could not be found."
            package_directory = os.path.normpath(os.path.join(spec.origin, "..", statics_dir))
            assert os.path.isdir(
                package_directory
            ), f"Directory '{statics_dir!r}' in package {package!r} could not be found."
            directories.append(package_directory)

        return directories

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        The ASGI entry point.

        Args:
            scope (Scope): ASGI scope.
            receive (Receive): ASGI receive channel.
            send (Send): ASGI send channel.
        """
        assert scope["type"] == "http"

        if not self.config_checked:
            await self.check_config()
            self.config_checked = True

        path = self.get_path(scope)
        response = await self.get_response(path, scope)
        await response(scope, receive, send)

    def get_path(self, scope: Scope) -> str:
        """
        Given the ASGI scope, return the `path` string to serve up,
        with OS specific path separators, and any '..', '.' components removed.

        Args:
            scope (Scope): ASGI scope.

        Returns:
            str: Normalized path.
        """
        route_path = self.get_route_path(scope)
        return os.path.normpath(os.path.join(*route_path.split("/")))

    def get_route_path(self, scope: Scope) -> str:
        """
        Given the ASGI scope, return the route path.

        Args:
            scope (Scope): ASGI scope.

        Returns:
            str: Route path.
        """
        return get_route_path(scope)

    async def get_response(self, path: str, scope: Scope) -> Response:
        """
        Returns an HTTP response, given the incoming path, method and request headers.

        Args:
            path (str): Path to the static file.
            scope (Scope): ASGI scope.

        Returns:
            Response: HTTP response.
        """
        if scope["method"] not in ("GET", "HEAD"):
            raise HTTPException(status_code=405)

        try:
            full_path, stat_result = await anyio.to_thread.run_sync(self.lookup_path, path)
        except PermissionError:
            raise HTTPException(status_code=401) from None
        except OSError:
            raise

        if stat_result and stat.S_ISREG(stat_result.st_mode):
            return self.file_response(full_path, stat_result, scope)

        elif stat_result and stat.S_ISDIR(stat_result.st_mode) and self.html:
            index_path = os.path.join(path, "index.html")
            full_path, stat_result = await anyio.to_thread.run_sync(self.lookup_path, index_path)
            if stat_result is not None and stat.S_ISREG(stat_result.st_mode):
                if not scope["path"].endswith("/"):
                    url = URL.build_from_scope(scope=scope)
                    url = url.replace(path=url.path + "/")
                    return RedirectResponse(url=url)
                return self.file_response(full_path, stat_result, scope)

        if self.html:
            full_path, stat_result = await anyio.to_thread.run_sync(self.lookup_path, "404.html")
            if stat_result and stat.S_ISREG(stat_result.st_mode):
                return FileResponse(full_path, stat_result=stat_result, status_code=404)
        raise HTTPException(status_code=404)

    def lookup_path(self, path: str) -> tuple[str, os.stat_result | None]:
        """
        Look up the full path and stat result for a given path.

        Args:
            path (str): Path to be looked up.

        Returns:
            Tuple[str, os.stat_result | None]: Full path and stat result (or None if not found).
        """
        for directory in self.all_directories:
            joined_path = os.path.join(directory, path)
            full_path = self.get_full_path(directory, joined_path)
            stat_result = self.get_stat_result(full_path)
            if stat_result:
                return full_path, stat_result
        return "", None

    def get_full_path(self, directory: str, path: str) -> str:
        """
        Get the full path by joining the directory and path.

        Args:
            directory (str): Base directory.
            path (str): Relative path.

        Returns:
            str: Full path.
        """
        if self.follow_symlink:
            return os.path.abspath(path)
        return os.path.realpath(path)

    def get_stat_result(self, full_path: str) -> os.stat_result | None:
        """
        Get the stat result for a given path.

        Args:
            full_path (str): Full path.

        Returns:
            os.stat_result | None: Stat result or None if not found.
        """
        try:
            return os.stat(full_path)
        except (FileNotFoundError, NotADirectoryError):
            return None

    def file_response(
        self,
        full_path: str,
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        """
        Generate a file response.

        Args:
            full_path (str): Full path to the file.
            stat_result (os.stat_result): Stat result for the file.
            scope (Scope): ASGI scope.
            status_code (int): HTTP status code.

        Returns:
            Response: File response.
        """
        try:
            request_headers = Header.from_scope(scope=scope)
        except KeyError:
            raise HTTPException(status_code=404) from None

        response = FileResponse(full_path, status_code=status_code, stat_result=stat_result)
        if self.is_not_modified(response.headers, request_headers):
            return StaticResponse(response.headers)
        return response

    async def check_config(self) -> None:
        """
        Perform a one-off configuration check that StaticFiles is actually
        pointed at a directory, so that we can raise loud errors rather than
        just returning 404 responses.
        """
        if self.directory is None:
            return

        try:
            stat_result = await anyio.to_thread.run_sync(os.stat, self.directory)
        except FileNotFoundError:
            raise RuntimeError(
                f"StaticFiles directory '{self.directory}' does not exist."
            ) from None
        if not (stat.S_ISDIR(stat_result.st_mode) or stat.S_ISLNK(stat_result.st_mode)):
            raise RuntimeError(f"StaticFiles path '{self.directory}' is not a directory.")

    def is_not_modified(self, response_headers: Header, request_headers: Header) -> bool:
        """
        Given the request and response headers, return `True` if an HTTP
        "Not Modified" response could be returned instead.

        Args:
            response_headers (Header): Response headers.
            request_headers (Header): Request headers.

        Returns:
            bool: True if "Not Modified" response could be returned, False otherwise.
        """
        try:
            if_none_match = request_headers["if-none-match"]
            etag = response_headers["etag"]
            if etag in [tag.strip(" W/") for tag in if_none_match.split(",")]:
                return True
        except KeyError:
            pass

        try:
            if_modified_since = parsedate(request_headers["if-modified-since"])
            last_modified = parsedate(response_headers["last-modified"])
            if (
                if_modified_since is not None
                and last_modified is not None
                and if_modified_since >= last_modified
            ):
                return True
        except KeyError:
            pass

        return False
