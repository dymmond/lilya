from __future__ import annotations

import importlib.util
import os
import stat
import typing
from email.utils import parsedate
from typing import Tuple, Union

import anyio
import anyio.to_thread

from lilya._internal._path import get_route_path
from lilya.datastructures import URL, Header
from lilya.enums import ScopeType
from lilya.exceptions import HTTPException
from lilya.responses import FileResponse, RedirectResponse, Response
from lilya.types import Receive, Scope, Send

PathLike = typing.Union[str, "os.PathLike[str]"]


class StaticResponse(Response):
    NOT_MODIFIED_HEADERS: Tuple[str, ...] = (
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
        directory: PathLike | None = None,
        packages: list[Union[str, Tuple[str, str], None]] = None,
        html: bool = False,
        check_dir: bool = True,
        follow_symlink: bool = False,
    ) -> None:
        self.directory = directory
        self.packages = packages
        self.all_directories = self._get_directories(directory, packages)
        self.html = html
        self.config_checked = False
        self.follow_symlink = follow_symlink
        if check_dir and directory is not None and not os.path.isdir(directory):
            raise RuntimeError(f"Directory '{directory}' does not exist")

    def _get_directories(
        self,
        directory: PathLike | None = None,
        packages: list[str | tuple[str, str]] | None = None,
    ) -> list[PathLike]:
        directories = []
        if directory is not None:
            directories.append(directory)

        for package in packages or []:
            package_directory = self._get_package_directory(package)
            directories.append(package_directory)

        return directories

    def _get_package_directory(self, package: str | tuple[str, str]) -> PathLike:
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
        return package_directory

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        assert scope["type"] == ScopeType.HTTP

        if not self.config_checked:
            await self._check_config()
            self.config_checked = True

        path = self._get_path(scope)
        response = await self._get_response(path, scope)
        await response(scope, receive, send)

    def _get_path(self, scope: Scope) -> str:
        route_path = get_route_path(scope)
        return os.path.normpath(os.path.join(*route_path.split("/")))

    async def _get_response(self, path: str, scope: Scope) -> Response:
        if scope["method"] not in ("GET", "HEAD"):
            raise HTTPException(status_code=405)

        try:
            full_path, stat_result = await anyio.to_thread.run_sync(self._lookup_path, path)
        except PermissionError:
            raise HTTPException(status_code=401) from None
        except OSError:
            raise

        if stat_result and stat.S_ISREG(stat_result.st_mode):
            return self._file_response(full_path, stat_result, scope)

        elif stat_result and stat.S_ISDIR(stat_result.st_mode) and self.html:
            index_path = os.path.join(path, "index.html")
            full_path, stat_result = await anyio.to_thread.run_sync(self._lookup_path, index_path)
            if stat_result is not None and stat.S_ISREG(stat_result.st_mode):
                if not scope["path"].endswith("/"):
                    url = URL(scope=scope)
                    url = url.replace(path=url.path + "/")
                    return RedirectResponse(url=url)
                return self._file_response(full_path, stat_result, scope)

        if self.html:
            full_path, stat_result = await anyio.to_thread.run_sync(self._lookup_path, "404.html")
            if stat_result and stat.S_ISREG(stat_result.st_mode):
                return FileResponse(full_path, stat_result=stat_result, status_code=404)
        raise HTTPException(status_code=404)

    def _lookup_path(self, path: str) -> tuple[str, os.stat_result | None]:
        for directory in self.all_directories:
            joined_path = os.path.join(directory, path)
            full_path = self._get_full_path(joined_path)
            if os.path.commonpath([full_path, directory]) != directory:
                continue
            try:
                return full_path, os.stat(full_path)
            except (FileNotFoundError, NotADirectoryError):
                continue
        return "", None

    def _get_full_path(self, joined_path: str) -> str:
        if self.follow_symlink:
            return os.path.abspath(joined_path)
        else:
            return os.path.realpath(joined_path)

    def _file_response(
        self,
        full_path: PathLike,
        stat_result: os.stat_result,
        scope: Scope,
        status_code: int = 200,
    ) -> Response:
        request_headers = Header.from_scope(scope=scope)

        response = FileResponse(full_path, status_code=status_code, stat_result=stat_result)
        if self._is_not_modified(response.headers, request_headers):
            return StaticResponse(response.headers)
        return response

    async def _check_config(self) -> None:
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

    def _is_not_modified(self, response_headers: Header, request_headers: Header) -> bool:
        try:
            if_none_match = request_headers["if-none-match"]
            etag = response_headers["etag"]
            if etag in [tag.strip(" W/") for tag in if_none_match.split(",")]:
                return True
        except KeyError:
            ...  # pragma: no cover

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
            ...  # pragma: no cover

        return False
