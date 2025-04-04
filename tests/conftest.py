import typing
from enum import StrEnum

import fastapi
import pydantic
import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocket

from fastapi_header_version import InlineVersionedRouter, init_fastapi_versioning


DOCS_URL_PREFIX = "/api/doc/"
VERSION_HEADER = "application/vnd.test+json"
VERSION_HEADER_INLINE = "application/vnd.inline+json"
inline_router = InlineVersionedRouter()
ROUTER_OBJ = fastapi.APIRouter()

class AppTypes(StrEnum):
    test = "test"
    inline = "inline"


class Body(pydantic.BaseModel):
    field1: str | None = None
    field2: int | None = None


class Body2(Body):
    field3: bool = True


@ROUTER_OBJ.websocket("/ws/")
async def websocket_endpoint(session: WebSocket) -> None:
    await session.accept()
    await session.send_text("Hello, world!")
    await session.close()


@ROUTER_OBJ.get("/simple/")
async def route_get_simple() -> dict[str, typing.Any]:
    return {}


@inline_router.get("/test/", version=(1,0), app_names=AppTypes.test)
async def route_get() -> dict[str, typing.Any]:
    return {"version": (1, 0)}


@inline_router.get("/test/", version=1, app_names=AppTypes.inline)
async def route_get_v1() -> dict[str, typing.Any]:
    return {"version": 1}


@inline_router.get("/test/", version=(2,0), app_names=AppTypes.test)
async def route_get_v2() -> dict[str, typing.Any]:
    return {"version": (2, 0)}


@inline_router.post("/test/", version=(1,0), app_names=AppTypes.test)
async def route_post(_: Body) -> dict[str, typing.Any]:
    return {"version": (1, 0)}


@inline_router.post("/test/", version=(1,1), app_names=AppTypes.test)
async def route_post_v1_1(_: Body2) -> dict[str, typing.Any]:
    return {"version": (1, 1)}


@pytest.fixture
def test_client() -> TestClient:
    app: typing.Final = fastapi.FastAPI(docs_url=DOCS_URL_PREFIX)
    init_fastapi_versioning(app=app)
    app.include_router(ROUTER_OBJ)
    app.include_router(inline_router)

    return TestClient(app=app)