from typing import Optional

from starlette.staticfiles import StaticFiles


class CachedStaticFiles(StaticFiles):
    """StaticFiles with configurable Cache-Control header."""

    def __init__(self, *args, cache_control: Optional[str] = None, **kwargs):
        self.cache_control = cache_control
        super().__init__(*args, **kwargs)

    async def get_response(self, path, scope):  # type: ignore[override]
        response = await super().get_response(path, scope)
        if (
            self.cache_control
            and response.status_code == 200
            and path  # Avoid setting header on directory responses
        ):
            response.headers.setdefault("Cache-Control", self.cache_control)
        return response
