"""Каталог на публичните източници, от които идва всяко число.

Съдържанието се извежда от регистъра на редовете, а не се поддържа отделно —
така списъкът в интерфейса не може да се разминe с това, което реално се тегли.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models import SourceSystem

DISCLAIMER_BG = (
    "Всички изчисления в приложението стъпват изцяло на публично достъпни "
    "официални данни. Те нямат за цел да плашат, стряскат или да дават "
    "финансов съвет на когото и да било. Прогнозите са статистическа оценка "
    "с посочена несигурност, а не обещание. Преди решение за кредит се "
    "консултирайте с вашата банка или с лицензиран консултант."
)


@dataclass(frozen=True)
class Provider:
    key: str
    name_bg: str
    description_bg: str
    portal_url: str
    api_base_url: str
    licence_bg: str


PROVIDERS: dict[SourceSystem, Provider] = {
    SourceSystem.ECB: Provider(
        key="ECB",
        name_bg="Европейска централна банка",
        description_bg=(
            "Официалният портал за данни на ЕЦБ. От него вземаме Euribor, "
            "основната лихва на ЕЦБ, кривата на доходността, както и "
            "лихвената статистика за България, която БНБ подава на ЕЦБ."
        ),
        portal_url="https://data.ecb.europa.eu/",
        api_base_url="https://data-api.ecb.europa.eu/service/data",
        licence_bg="Свободно ползване с посочване на източника.",
    ),
    SourceSystem.BUNDESBANK: Provider(
        key="BUNDESBANK",
        name_bg="Германска федерална банка (Bundesbank)",
        description_bg=(
            "Дневната доходност по германските държавни облигации — еталонът, "
            "спрямо който се мери цената на дълга в цялата еврозона."
        ),
        portal_url="https://www.bundesbank.de/en/statistics",
        api_base_url="https://api.statistiken.bundesbank.de/rest/data",
        licence_bg="Свободно ползване с посочване на източника.",
    ),
    SourceSystem.EUROSTAT: Provider(
        key="EUROSTAT",
        name_bg="Евростат",
        description_bg=(
            "Статистическата служба на ЕС. От нея идват инфлацията, държавният "
            "дълг, бюджетният баланс и разбивката на публичните разходи."
        ),
        portal_url="https://ec.europa.eu/eurostat/web/main/data/database",
        api_base_url=(
            "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
        ),
        licence_bg="Свободно ползване с посочване на източника.",
    ),
    SourceSystem.US_TREASURY: Provider(
        key="US_TREASURY",
        name_bg="Министерство на финансите на САЩ",
        description_bg=(
            "Дневната крива на доходността по американския държавен дълг. "
            "Задава посоката на световните пазари и често изпреварва "
            "европейските движения."
        ),
        portal_url=(
            "https://home.treasury.gov/resource-center/data-chart-center/"
            "interest-rates/TextView?type=daily_treasury_yield_curve"
        ),
        api_base_url=(
            "https://home.treasury.gov/resource-center/data-chart-center/"
            "interest-rates/daily-treasury-rates.csv"
        ),
        licence_bg="Обществено достояние.",
    ),
}
