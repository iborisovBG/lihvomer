"""RSS източници. Всеки адрес е проверен, че връща записи."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeedDef:
    code: str
    name_bg: str
    url: str
    language: str
    # Ако е True, вземаме само записите, които споменават България.
    bulgaria_only: bool = False


FEEDS: tuple[FeedDef, ...] = (
    FeedDef(
        code="EC_PRESS",
        name_bg="Европейска комисия",
        url="https://ec.europa.eu/commission/presscorner/api/rss?language=en",
        language="en",
        bulgaria_only=True,
    ),
    FeedDef(
        code="ECB_PRESS",
        name_bg="Европейска централна банка",
        url="https://www.ecb.europa.eu/rss/press.html",
        language="en",
    ),
    FeedDef(
        code="ECB_BLOG",
        name_bg="ЕЦБ — анализи",
        url="https://www.ecb.europa.eu/rss/blog.html",
        language="en",
    ),
    FeedDef(
        code="CAPITAL",
        name_bg="Capital.bg",
        url="https://www.capital.bg/rss/",
        language="bg",
    ),
    FeedDef(
        code="DNEVNIK",
        name_bg="Дневник",
        url="https://www.dnevnik.bg/rss/",
        language="bg",
    ),
    FeedDef(
        code="24CHASA",
        name_bg="24 часа",
        url="https://www.24chasa.bg/rss",
        language="bg",
    ),
)

BY_CODE = {feed.code: feed for feed in FEEDS}

# Общоинформационните издания пускат стотици новини дневно, затова искаме
# поне един недвусмислено икономически термин. Съзнателно НЕ включваме голи
# „евро" и „кредит" — те съвпадат с „европейски" и „кредитна карта" и
# наводняват фийда с несвързани заглавия.
TOPIC_TERMS = (
    # Лихви и парична политика
    "лихв", "ипотек", "еврибор", "euribor", "рефинансиран", "предоговар",
    "парична политика", "основен лихвен", "блп", "лихвен", "кредитиран",
    "заем", "кредитополучател", "жилищен кредит", "потребителски кредит",
    # Цени
    "инфлаци", "дефлаци", "поскъпва", "поевтиня", "потребителск цени",
    "хипц", "ипц",
    # Публични финанси
    "бюджет", "дефицит", "държавен дълг", "фискал", "свръхдефицит",
    "прекомерен дефицит", "данъчн", "осигурителн", "пенсионн",
    # Пазари и институции
    "еврозон", "еврото", "облигаци", "дцк", "кредитен рейтинг", "спред",
    "бнб", "ецб", "евростат", "мвф",
    # Английски еквиваленти
    "interest rate", "inflation", "deficit", "government debt", "budget",
    "euro area", "monetary policy", "bond yield", "credit rating",
    "mortgage", "lending rate", "fiscal", "euribor",
)
