import copy
import re
import typing
from types import MethodType

import fastapi
from fastapi.openapi.utils import get_openapi
from starlette import types
from starlette.responses import JSONResponse

from fast_version import helpers
from fast_version.router import DecoratorVersionedRouter, VersionedAPIRoute

_APP_RE: typing.Final = r"application/vnd\.(?P<app_name>.+)\+json; version=(?P<version>.+)$"
_VERSION_RE: typing.Final = re.compile(r"^\d+\.\d+$")


def _get_vendor_media_type() -> str:
    return DecoratorVersionedRouter.VENDOR_MEDIA_TYPE


def init_fastapi_versioning(*, app: fastapi.FastAPI) -> None:
    app.add_middleware(FastAPIVersioningMiddleware)
    app.openapi = MethodType(_custom_openapi, app)  # type: ignore[method-assign]


class FastAPIVersioningMiddleware:
    def __init__(self, app: fastapi.FastAPI) -> None:
        self.app = app

    async def __call__(
        self,
        scope: types.Scope,
        receive: types.Receive,
        send: types.Send,
    ) -> None:
        error_response: JSONResponse | None = None
        while True:
            if scope["type"] != "http":
                break

            accept_header_from_request = helpers.get_accept_header_from_scope(scope)
            if not accept_header_from_request or accept_header_from_request == "*/*":
                break

            if len(accept_header_from_request.split(";")) != 2:
                break

            match = re.search(_APP_RE, accept_header_from_request)

            if not match:
                error_response = JSONResponse(
                    {"detail": "Wrong media type or no version in Accept header"},
                    status_code=406,
                )
                break

            group_match = match.groupdict()
            version = group_match["version"]
            app_name = group_match["app_name"]

            if not _VERSION_RE.match(version):
                error_response = JSONResponse(
                    {"detail": "Version should be in <major>.<minor> format"},
                    status_code=400,
                )
                break

            scope["version"] = tuple(int(version_part) for version_part in version.split("."))
            scope["app_name"] = app_name
            break
        if error_response:
            return await error_response(scope, receive, send)
        return await self.app(scope, receive, send)


def _custom_openapi(self: fastapi.FastAPI) -> dict[str, typing.Any]:
    if self.openapi_schema:
        return self.openapi_schema

    routes = []
    for route_item in self.routes:
        if not isinstance(route_item, VersionedAPIRoute):
            routes.append(route_item)
            continue

        # trick to avoid merging routes
        route_copy = copy.copy(route_item)
        route_copy.path_format = f"{route_copy.path_format}:{','.join(route_copy.app_names)}:{route_copy.version_str}"
        routes.append(route_copy)

    self.openapi_schema = get_openapi(
        title=self.title,
        version=self.version,
        openapi_version=self.openapi_version,
        summary=self.summary,
        description=self.description,
        terms_of_service=self.terms_of_service,
        contact=self.contact,
        license_info=self.license_info,
        routes=routes,
        webhooks=self.webhooks.routes,
        tags=self.openapi_tags,
        servers=self.servers,
    )
    paths_dict = {}
    for raw_path, methods in self.openapi_schema["paths"].items():
        if ":" not in raw_path:
            paths_dict[raw_path] = methods
            continue

        clean_path, app_names_str, version = raw_path.split(":")
        app_names = [app_name.strip() for app_name in app_names_str.split(",")]
        for method, payload in methods.items():
            if method.lower() == "get":
                continue

            if "requestBody" not in payload:
                payload["requestBody"] = {}
                payload["requestBody"]["content"] = {
                    _get_vendor_media_type().format(app_name=app_name, version=version): {"schema": {}}
                    for app_name in app_names
                }
                continue
            payload["requestBody"]["content"] = {
                _get_vendor_media_type().format(app_name=app_name, version=version): v
                for app_name in app_names
                for k, v in payload["requestBody"]["content"].items()
            }

        if clean_path not in paths_dict:
            paths_dict[clean_path] = methods
        else:
            for method, payload in methods.items():
                if method in paths_dict[clean_path]:
                    if "description" in payload and "description" in paths_dict[clean_path][method]:
                        existing_desc = paths_dict[clean_path][method]["description"]
                        new_desc = payload["description"]

                        if new_desc not in existing_desc:
                            paths_dict[clean_path][method]["description"] = f"{existing_desc}\n\n{new_desc}"
                else:
                    paths_dict[clean_path][method] = payload

        helpers.dict_merge(paths_dict[clean_path], methods)
    self.openapi_schema["paths"] = paths_dict
    return self.openapi_schema
