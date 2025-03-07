import typing
from enum import StrEnum
from typing import Callable

from fastapi.routing import APIRoute, APIRouter
from fastapi.types import DecoratedCallable
from starlette import types
from starlette.responses import JSONResponse
from starlette.routing import Match

from fast_version.helpers import ClassProperty

DEFAULT_VERSION: typing.Final = (1, 0)


class VersionedAPIRoute(APIRoute):
    @property
    def version(self) -> tuple[int, int]:
        return typing.cast(tuple[int, int], getattr(self.endpoint, "version"))

    @property
    def app_names(self) -> set[str]:
        return getattr(self.endpoint, "app_names")

    @property
    def version_str(self) -> str:
        return ".".join(str(x) for x in self.version)

    def matches(self, scope: types.Scope) -> tuple[Match, types.Scope]:
        match, child_scope = super().matches(scope)
        if match != Match.FULL:
            return match, child_scope

        request_version: tuple[int, int] = scope.get("version", DEFAULT_VERSION)
        app_name: str = scope.get("app_name")
        if request_version == self.version and app_name in self.app_names:
            return Match.FULL, child_scope
        return Match.NONE, {}


class VersionedRouter(APIRouter):
    VENDOR_MEDIA_TYPE = "application/vnd.{app_name}+json; version={version}"

    def api_route(
        self,
        path: str,
        **kwargs: typing.Any,  # noqa: ANN401
    ) -> typing.Callable[[DecoratedCallable], DecoratedCallable]:
        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            version_str = ".".join([str(x) for x in getattr(func, "version")])
            app_names = getattr(func, "app_names")

            class VersionedJSONResponse(JSONResponse):
                @ClassProperty
                def media_type(self) -> str:  # type: ignore[override]
                    """Media type for docs."""
                    return VersionedRouter.VENDOR_MEDIA_TYPE.format(app_name=app_names[0], version=version_str)

            kwargs["response_class"] = VersionedJSONResponse
            kwargs["route_class_override"] = VersionedAPIRoute
            if len(app_names) > 1:
                description = f"Версия `{version_str}` поддерживается: `{'`, `'.join(app_names)}`"
                kwargs["description"] = description + "\n\n - " + (kwargs["description"] or "")

            for route in self.routes:
                if version_str != route.version_str:
                    continue

                if kwargs["methods"][0] not in set(route.methods):
                    continue

                if path not in route.path:
                    continue

                for app_name in app_names:
                    if app_name not in route.app_names:
                        continue

                    raise ValueError(f"App with name {app_name!r} for version {version_str!r} already exists")

            self.add_api_route(path, func, **kwargs)
            return func

        return decorator

    @staticmethod
    def set_api_version(
        version: tuple[int, int],
        *,
        app_names: set[StrEnum] | StrEnum,
    ) -> typing.Callable[[DecoratedCallable], DecoratedCallable]:
        if not isinstance(app_names, set):
            app_names = {app_names}

        def decorator(func: DecoratedCallable) -> DecoratedCallable:
            setattr(func, "version", version)
            setattr(func, "app_names", list(app_names))
            return func

        return decorator


class InlineVersionedRouter(VersionedRouter):

    def _version_wrapper(
        self,
        original_decorator: DecoratedCallable,
        version: tuple[int, int],
        app_names: set[StrEnum] | StrEnum,
    ):
        def custom_decorator(func: Callable) -> Callable:
            decorated_func = self.set_api_version(version=version, app_names=app_names)(func)

            return original_decorator(decorated_func)

        return custom_decorator

    def get(
        self,
        path: str,
        version: tuple[int, int],
        app_names: set[StrEnum] | StrEnum,
        **kwargs: typing.Any,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        return self._version_wrapper(
            super().get(path, **kwargs),
            version,
            app_names,
        )

    def post(
        self,
        path: str,
        version: tuple[int, int],
        app_names: set[StrEnum] | StrEnum,
        **kwargs: typing.Any,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        return self._version_wrapper(
            super().post(path, **kwargs),
            version,
            app_names,
        )

    def patch(
        self,
        path: str,
        version: tuple[int, int],
        app_names: set[StrEnum] | StrEnum,
        **kwargs: typing.Any,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        return self._version_wrapper(
            super().patch(path, **kwargs),
            version,
            app_names,
        )

    def put(
        self,
        path: str,
        version: tuple[int, int],
        app_names: set[StrEnum] | StrEnum,
        **kwargs: typing.Any,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        return self._version_wrapper(
            super().put(path, **kwargs),
            version,
            app_names,
        )

    def delete(
        self,
        path: str,
        version: tuple[int, int],
        app_names: set[StrEnum] | StrEnum,
        **kwargs: typing.Any,
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        return self._version_wrapper(
            super().delete(path, **kwargs),
            version,
            app_names,
        )
