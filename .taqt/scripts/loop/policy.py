from __future__ import annotations

from typing import Any


def route_next_step(step: dict[str, Any], feedback: str | None) -> str:
    routes = step.get("routes")
    if not isinstance(routes, list):
        raise ValueError("policy step requires routes")
    selected = feedback or "unknown"
    fallback: str | None = None
    for route in routes:
        if not isinstance(route, dict):
            continue
        when = route.get("when")
        if when == selected:
            return _next(route)
        if when == "unknown":
            fallback = _next(route)
    if fallback:
        return fallback
    raise ValueError(f"no policy route for feedback: {selected}")


def _next(route: dict[str, Any]) -> str:
    value = route.get("next")
    if not isinstance(value, str) or not value:
        raise ValueError("policy route requires next")
    return value
