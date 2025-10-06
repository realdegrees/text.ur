# Source: https://github.com/fastapi/fastapi/discussions/7298#discussioncomment-5135711
# ? Any routes defined in the backend should not have a trailing slash.
# ? Say we have a route `/api/users/` and a request comes in for `/api/users` (trailing slash) then FastAPI will respond with a redirect instead of the expected answer.
# ? Redirecting slashes can be turned off in the fastapi config but then it just results in a 404 instead.

# ! The source was heavily modified in order to allow different methods on the same path with and without a trailing slash.

# To avoid any future issues the FastAPIRouter has been extended to automatically duplicate all routes with and without a trailing slash per the issue above.
# Eventually this workaround can be removed as there is already an approved pull request on the fastapi repo (https://github.com/fastapi/fastapi/pull/12145) that will fix this with a single flag
# `app = FastAPI(ignore_trailing_slash=True)`.
# ! USE THIS INSTEAD OF FASTAPIROUTER WHEN ADDING NEW ROUTERS TO THE APP

# ! WARNING: Using this creates N*2 duplicate routes for each route where N is the route depth, I don't know how much of a performance impact this is but it seems to be negligible.
# ! The main benefit is that clients can use both versions of the route without any issues due to redirects

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter as FastAPIRouter
from fastapi.types import DecoratedCallable


class APIRouter(FastAPIRouter):
    """A custom router that automatically registers routes with and without a trailing slash."""

    def add_api_route(
        self,
        path: str,
        endpoint: str,
        *,
        include_in_schema: bool = True,
        **kwargs: dict[str, Any],
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        """Register a new route with and without a trailing slash."""
        if path.endswith("/"):
            path = path[:-1]

        # Register both versions of the route
        super().add_api_route(path, endpoint, include_in_schema=include_in_schema, **kwargs)
        super().add_api_route(
            path + "/", endpoint, include_in_schema=False, **kwargs
        )
