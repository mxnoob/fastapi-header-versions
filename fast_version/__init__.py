from fast_version.app import init_fastapi_versioning
from fast_version.router import VersionedRouter, InlineVersionedRouter

__all__ = [
    "VersionedRouter",
    "InlineVersionedRouter",
    "init_fastapi_versioning",
]
