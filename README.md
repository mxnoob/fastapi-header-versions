# fastapi-header-versions

This package adds versioning by Accept-header into FastAPI

### Defining app and routes

```python
from enum import StrEnum
import fastapi

from fast_version import VersionedRouter, InlineVersionedRouter, init_fastapi_versioning


class AppType(StrEnum):
    some_name: "some.name"
    some_name2: "some.name2"


decorate_router = VersionedRouter()
inline_router = InlineVersionedRouter()


@decorate_router.get("/test/")
@decorate_router.set_api_version((1, 0), app_names={AppType.some_name, AppType.some_name2})
async def test_get() -> dict:
    return {"version": (1, 0)}


@inline_router.get("/test/", (2, 0), app_names=AppType.some_name)
async def test_get_v2() -> dict:
    return {"version": (2, 0)}


app = fastapi.FastAPI()
app.include_router(inline_router)
init_fastapi_versioning(app=app)
```

### Query Examples
```bash
# call 1.0 version
curl -X 'GET' 'https://test.ru/test/' -H 'accept: application/vnd.some.name+json; version=1.0'

# call 2.0 version
curl -X 'GET' 'https://test.ru/test/' -H 'accept: application/vnd.some.name+json; version=2.0'
```
