from fast_version.app import init_fastapi_versioning
from fast_version.router import DecoratorVersionedRouter, InlineVersionedRouter

__all__ = [
    "DecoratorVersionedRouter",
    "InlineVersionedRouter",
    "init_fastapi_versioning",
]
