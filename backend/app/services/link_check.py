"""Проверка дали външните адреси още работят.

Линковете, които приложението показва, не се ползват от кода — данните се
теглят от други адреси. Затова един портал може да премести страницата си и
линкът да гние месеци, докато приложението работи безупречно. Тази проверка
хваща точно това.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass

# Някои портали отказват заявки без разпознаваем браузър. Представяме се
# честно — име на приложението и адрес, на който да ни намерят.
USER_AGENT = (
    "Mozilla/5.0 (compatible; Lihvomer/1.0; +https://xbotics.ai) link-check"
)
TIMEOUT_SECONDS = 25


@dataclass
class LinkStatus:
    label: str
    url: str
    status: int | None
    ok: bool
    error: str | None = None


def check(label: str, url: str) -> LinkStatus:
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT}, method="GET"
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            # Четем малко от тялото: някои сървъри отговарят 200 и после падат.
            response.read(2048)
            return LinkStatus(label, url, response.status, 200 <= response.status < 400)
    except urllib.error.HTTPError as exc:
        return LinkStatus(label, url, exc.code, False, f"HTTP {exc.code}")
    except Exception as exc:
        return LinkStatus(label, url, None, False, type(exc).__name__)


def collect_links() -> list[tuple[str, str]]:
    """Всички външни адреси, които приложението показва на потребителя."""
    from app.ingestion.registry import SERIES
    from app.news.sources import FEEDS
    from app.services.partners import ACTIVE_PARTNERS
    from app.services.sources_catalog import PROVIDERS

    links: list[tuple[str, str]] = []
    for provider in PROVIDERS.values():
        links.append((f"портал:{provider.key}", provider.portal_url))
    for series in SERIES:
        links.append((f"серия:{series.code}", series.browse_url))
    for feed in FEEDS:
        links.append((f"фийд:{feed.code}", feed.url))
    for partner in ACTIVE_PARTNERS:
        links.append((f"партньор:{partner.key}", partner.url))
    return links


def check_all() -> list[LinkStatus]:
    # Адресите се повтарят (много серии сочат един портал); проверяваме всеки
    # уникален адрес по веднъж, за да не тормозим източниците.
    seen: dict[str, LinkStatus] = {}
    results: list[LinkStatus] = []
    for label, url in collect_links():
        if url in seen:
            results.append(LinkStatus(label, url, seen[url].status, seen[url].ok, seen[url].error))
            continue
        status = check(label, url)
        seen[url] = status
        results.append(status)
    return results
