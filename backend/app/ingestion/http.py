from __future__ import annotations

import logging

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()


class UpstreamError(RuntimeError):
    """Публичният източник не върна използваеми данни."""


RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class RetryableStatus(UpstreamError):
    pass


@retry(
    retry=retry_if_exception_type((httpx.TransportError, RetryableStatus)),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1.5, min=2, max=20),
    reraise=True,
)
def fetch_text(url: str, params: dict[str, str] | None = None) -> str:
    headers = {"User-Agent": _settings.http_user_agent}
    with httpx.Client(
        timeout=_settings.http_timeout_seconds, follow_redirects=True
    ) as client:
        response = client.get(url, params=params, headers=headers)

    if response.status_code in RETRYABLE_STATUS:
        raise RetryableStatus(
            f"{url} върна {response.status_code}; ще опитаме отново."
        )
    if response.status_code == 404:
        raise UpstreamError(
            f"{url} върна 404 — серията не съществува или няма данни за периода."
        )
    if response.status_code >= 400:
        raise UpstreamError(f"{url} върна {response.status_code}: {response.text[:200]}")

    body = response.text
    if not body.strip():
        raise UpstreamError(f"{url} върна празен отговор.")
    return body


def fetch_json(url: str, params: dict[str, str] | None = None) -> dict:
    import json

    body = fetch_text(url, params)
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise UpstreamError(f"{url} не върна валиден JSON: {body[:200]}") from exc
