"""Единен регистър на всички времеви редове, които теглим.

Всеки ключ тук е проверен срещу живото API. Кодовете се ползват навсякъде
другаде в приложението, така че смяна на източник не изисква промени в API слоя.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models import Frequency, SourceSystem, Unit

# --- Кодове на серии (ползвай тези константи, не низове) -------------------
DE10Y_BUND = "DE10Y_BUND"
EA_AAA_10Y = "EA_AAA_10Y"
ECB_DFR = "ECB_DFR"
EURIBOR_3M = "EURIBOR_3M"
EURIBOR_6M = "EURIBOR_6M"
EURIBOR_12M = "EURIBOR_12M"
BG_MORTGAGE_EUR = "BG_MORTGAGE_EUR"
BG_MORTGAGE_BGN = "BG_MORTGAGE_BGN"
BG_CONSUMER_EUR = "BG_CONSUMER_EUR"
BG_CONSUMER_BGN = "BG_CONSUMER_BGN"
BG_10Y_GOVT_EUR = "BG_10Y_GOVT_EUR"
BG_10Y_GOVT_BGN = "BG_10Y_GOVT_BGN"
DE_10Y_GOVT_M = "DE_10Y_GOVT_M"
HICP_BG = "HICP_BG"
HICP_EU = "HICP_EU"
BG_GOV_BALANCE = "BG_GOV_BALANCE"
BG_GOV_DEBT = "BG_GOV_DEBT"
BG_GOV_DEBT_Q = "BG_GOV_DEBT_Q"
BG_GOV_BALANCE_Q = "BG_GOV_BALANCE_Q"
BG_DEPOSIT_TERM = "BG_DEPOSIT_TERM"
BG_DEPOSIT_OVERNIGHT = "BG_DEPOSIT_OVERNIGHT"
BG_HOUSE_PRICES = "BG_HOUSE_PRICES"
BG_MORTGAGE_APRC = "BG_MORTGAGE_APRC"
BG_CONSUMER_APRC = "BG_CONSUMER_APRC"
BG_MORTGAGE_VOLUME = "BG_MORTGAGE_VOLUME"
US_10Y = "US_10Y"


@dataclass(frozen=True)
class SeriesDef:
    code: str
    name_bg: str
    plain_bg: str
    source: SourceSystem
    source_ref: str
    frequency: Frequency
    unit: Unit
    # Допълнителни query параметри (ползва се от Eurostat).
    params: dict[str, str] = field(default_factory=dict)
    # Ред, който вече не се публикува, защото е заместен от друг. Не е
    # застоял — просто е приключил и не бива да вдига тревога.
    superseded_by: str | None = None

    @property
    def browse_url(self) -> str:
        """Публичен адрес, на който всеки може да провери самите числа."""
        if self.source is SourceSystem.ECB:
            flow, _, key = self.source_ref.partition("/")
            return f"https://data.ecb.europa.eu/data/datasets/{flow}/{flow}.{key}"
        if self.source is SourceSystem.EUROSTAT:
            return (
                "https://ec.europa.eu/eurostat/databrowser/view/"
                f"{self.source_ref}/default/table"
            )
        if self.source is SourceSystem.BUNDESBANK:
            # Дълбок линк към конкретната серия. Идентификаторът е същият като
            # в API-то, но с точки вместо наклонена черта.
            series_id = self.source_ref.replace("/", ".")
            return (
                "https://www.bundesbank.de/dynamic/action/en/statistics/"
                "time-series-databases/time-series-databases/759784/759784"
                f"?tsId={series_id}"
            )
        return (
            "https://home.treasury.gov/resource-center/data-chart-center/"
            "interest-rates/TextView?type=daily_treasury_yield_curve"
        )


SERIES: tuple[SeriesDef, ...] = (
    SeriesDef(
        code=DE10Y_BUND,
        name_bg="Германска 10-годишна държавна облигация (Bund)",
        plain_bg=(
            "Лихвата, при която Германия взема заеми за 10 години. Тя е "
            "еталонът за цялата еврозона — когато тя се качва, поскъпват и "
            "кредитите в България."
        ),
        source=SourceSystem.BUNDESBANK,
        source_ref="BBSIS/D.I.ZAR.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A",
        frequency=Frequency.DAILY,
        unit=Unit.PERCENT_PER_ANNUM,
    ),
    SeriesDef(
        code=EA_AAA_10Y,
        name_bg="Крива на доходността в еврозоната, 10 г. (AAA емитенти)",
        plain_bg=(
            "Средната цена на дългосрочните заеми за най-стабилните държави в "
            "еврозоната. Публикува се всеки работен ден от ЕЦБ."
        ),
        source=SourceSystem.ECB,
        source_ref="YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y",
        frequency=Frequency.DAILY,
        unit=Unit.PERCENT_PER_ANNUM,
    ),
    SeriesDef(
        code=ECB_DFR,
        name_bg="Основна депозитна лихва на ЕЦБ",
        plain_bg=(
            "Лихвата, която ЕЦБ плаща на банките. Това е основният лост, с "
            "който ЕЦБ управлява цената на парите в еврозоната."
        ),
        source=SourceSystem.ECB,
        source_ref="FM/D.U2.EUR.4F.KR.DFR.LEV",
        frequency=Frequency.DAILY,
        unit=Unit.PERCENT_PER_ANNUM,
    ),
    SeriesDef(
        code=EURIBOR_3M,
        name_bg="Euribor 3 месеца",
        plain_bg=(
            "Лихвата, при която банките си заемат пари за 3 месеца. Ако "
            "кредитът ви е с Euribor 3M, вноската ви се преизчислява по нея."
        ),
        source=SourceSystem.ECB,
        source_ref="FM/M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA",
        frequency=Frequency.MONTHLY,
        unit=Unit.PERCENT_PER_ANNUM,
    ),
    SeriesDef(
        code=EURIBOR_6M,
        name_bg="Euribor 6 месеца",
        plain_bg="Същото като Euribor 3M, но за период от 6 месеца.",
        source=SourceSystem.ECB,
        source_ref="FM/M.U2.EUR.RT.MM.EURIBOR6MD_.HSTA",
        frequency=Frequency.MONTHLY,
        unit=Unit.PERCENT_PER_ANNUM,
    ),
    SeriesDef(
        code=EURIBOR_12M,
        name_bg="Euribor 12 месеца",
        plain_bg="Същото като Euribor 3M, но за период от 1 година.",
        source=SourceSystem.ECB,
        source_ref="FM/M.U2.EUR.RT.MM.EURIBOR1YD_.HSTA",
        frequency=Frequency.MONTHLY,
        unit=Unit.PERCENT_PER_ANNUM,
    ),
    SeriesDef(
        code=BG_MORTGAGE_EUR,
        name_bg="Средна лихва по нови ипотечни кредити в България (евро)",
        plain_bg=(
            "Средната лихва, на която българските банки отпускат нови жилищни "
            "кредити в евро. Това е числото, което ви касае пряко."
        ),
        source=SourceSystem.ECB,
        source_ref="MIR/M.BG.B.A2C.A.R.A.2250.EUR.N",
        frequency=Frequency.MONTHLY,
        unit=Unit.PERCENT_PER_ANNUM,
    ),
    SeriesDef(
        code=BG_MORTGAGE_BGN,
        name_bg="Средна лихва по нови ипотечни кредити в България (лева)",
        plain_bg=(
            "Историческият ред в лева. Спира с приемането на еврото от "
            "България — след това се следи серията в евро."
        ),
        source=SourceSystem.ECB,
        source_ref="MIR/M.BG.B.A2C.A.R.A.2250.BGN.N",
        frequency=Frequency.MONTHLY,
        unit=Unit.PERCENT_PER_ANNUM,
        superseded_by=BG_MORTGAGE_EUR,
    ),
    SeriesDef(
        code=BG_CONSUMER_EUR,
        name_bg="Средна лихва по нови потребителски кредити в България (евро)",
        plain_bg=(
            "Средната лихва по новите потребителски кредити в евро. Тя е "
            "чувствително по-висока от ипотечната, защото няма обезпечение."
        ),
        source=SourceSystem.ECB,
        source_ref="MIR/M.BG.B.A2B.A.R.A.2250.EUR.N",
        frequency=Frequency.MONTHLY,
        unit=Unit.PERCENT_PER_ANNUM,
    ),
    SeriesDef(
        code=BG_CONSUMER_BGN,
        name_bg="Средна лихва по нови потребителски кредити в България (лева)",
        plain_bg="Историческият ред в лева за потребителските кредити.",
        source=SourceSystem.ECB,
        source_ref="MIR/M.BG.B.A2B.A.R.A.2250.BGN.N",
        frequency=Frequency.MONTHLY,
        unit=Unit.PERCENT_PER_ANNUM,
        superseded_by=BG_CONSUMER_EUR,
    ),
    SeriesDef(
        code=BG_10Y_GOVT_EUR,
        name_bg="Българска 10-годишна държавна облигация (евро)",
        plain_bg=(
            "Лихвата, на която българската държава взема заеми за 10 години. "
            "Разликата спрямо германската показва как пазарът оценява риска на "
            "страната."
        ),
        source=SourceSystem.ECB,
        source_ref="IRS/M.BG.L.L40.CI.0000.EUR.N.Z",
        frequency=Frequency.MONTHLY,
        unit=Unit.PERCENT_PER_ANNUM,
    ),
    SeriesDef(
        code=BG_10Y_GOVT_BGN,
        name_bg="Българска 10-годишна държавна облигация (лева)",
        plain_bg="Историческият ред в лева преди приемането на еврото.",
        source=SourceSystem.ECB,
        source_ref="IRS/M.BG.L.L40.CI.0000.BGN.N.Z",
        frequency=Frequency.MONTHLY,
        unit=Unit.PERCENT_PER_ANNUM,
        superseded_by=BG_10Y_GOVT_EUR,
    ),
    SeriesDef(
        code=DE_10Y_GOVT_M,
        name_bg="Германска 10-годишна облигация (месечна, Маастрихт)",
        plain_bg=(
            "Месечното официално отчитане на германската дългосрочна лихва, "
            "по което ЕС сравнява държавите."
        ),
        source=SourceSystem.ECB,
        source_ref="IRS/M.DE.L.L40.CI.0000.EUR.N.Z",
        frequency=Frequency.MONTHLY,
        unit=Unit.PERCENT_PER_ANNUM,
    ),
    SeriesDef(
        code=HICP_BG,
        name_bg="Инфлация в България (ХИПЦ, годишна)",
        plain_bg=(
            "С колко процента са поскъпнали стоките и услугите за последната "
            "година. Ако инфлацията е по-висока от лихвата ви, кредитът "
            "реално поевтинява."
        ),
        source=SourceSystem.EUROSTAT,
        # Ползваме краткосрочния набор, а не prc_hicp_manr: вторият изостава
        # с месеци (последно наблюдение декември 2025 при проверка през август
        # 2026), докато този носи миналия месец. Стойностите съвпадат.
        source_ref="ei_cphi_m",
        frequency=Frequency.MONTHLY,
        unit=Unit.PERCENT_CHANGE,
        params={"geo": "BG", "unit": "RT12", "indic": "TOTAL"},
    ),
    SeriesDef(
        code=HICP_EU,
        name_bg="Инфлация в ЕС (ХИПЦ, годишна)",
        plain_bg="Същото измерване, но за целия Европейски съюз.",
        source=SourceSystem.EUROSTAT,
        source_ref="ei_cphi_m",
        frequency=Frequency.MONTHLY,
        unit=Unit.PERCENT_CHANGE,
        params={"geo": "EU27_2020", "unit": "RT12", "indic": "TOTAL"},
    ),
    SeriesDef(
        code=BG_GOV_BALANCE,
        name_bg="Бюджетен баланс на България (% от БВП)",
        plain_bg=(
            "Отрицателно число значи дефицит — държавата харчи повече, "
            "отколкото събира. Голям дефицит оскъпява заемите на държавата, "
            "а с тях и вашите."
        ),
        source=SourceSystem.EUROSTAT,
        source_ref="gov_10dd_edpt1",
        frequency=Frequency.ANNUAL,
        unit=Unit.PERCENT_OF_GDP,
        params={"geo": "BG", "na_item": "B9", "sector": "S13", "unit": "PC_GDP"},
    ),
    SeriesDef(
        code=BG_GOV_DEBT,
        name_bg="Държавен дълг на България (% от БВП)",
        plain_bg=(
            "Колко дължи държавата спрямо това, което произвежда за година. "
            "България традиционно е сред най-ниско задлъжнелите в ЕС."
        ),
        source=SourceSystem.EUROSTAT,
        source_ref="gov_10dd_edpt1",
        frequency=Frequency.ANNUAL,
        unit=Unit.PERCENT_OF_GDP,
        params={"geo": "BG", "na_item": "GD", "sector": "S13", "unit": "PC_GDP"},
    ),
    SeriesDef(
        code=BG_GOV_DEBT_Q,
        name_bg="Държавен дълг на България (тримесечен, % от БВП)",
        plain_bg=(
            "Същият дълг, но отчитан на всеки три месеца вместо веднъж "
            "годишно. Показва накъде върви задлъжнялостта много по-рано от "
            "годишната статистика."
        ),
        source=SourceSystem.EUROSTAT,
        source_ref="gov_10q_ggdebt",
        frequency=Frequency.QUARTERLY,
        unit=Unit.PERCENT_OF_GDP,
        params={"geo": "BG", "na_item": "GD", "sector": "S13", "unit": "PC_GDP"},
    ),
    SeriesDef(
        code=BG_GOV_BALANCE_Q,
        name_bg="Бюджетен баланс на България (тримесечен, % от БВП)",
        plain_bg=(
            "Колко харчи държавата спрямо това, което събира, отчетено на "
            "тримесечие. Отрицателното число е дефицит. Прагът на ЕС е -3%; "
            "трайното му надхвърляне води до наказателна процедура."
        ),
        source=SourceSystem.EUROSTAT,
        source_ref="gov_10q_ggnfa",
        frequency=Frequency.QUARTERLY,
        unit=Unit.PERCENT_OF_GDP,
        params={
            "geo": "BG",
            "na_item": "B9",
            "sector": "S13",
            "unit": "PC_GDP",
            "s_adj": "NSA",
        },
    ),
    SeriesDef(
        code=BG_MORTGAGE_APRC,
        name_bg="Среден ГПР по нови ипотечни кредити в България",
        plain_bg=(
            "Годишният процент на разходите включва не само лихвата, а и "
            "таксите и застраховките. Това е числото, по което трябва да "
            "сравнявате оферти — лихвата сама по себе си подвежда."
        ),
        source=SourceSystem.ECB,
        source_ref="MIR/M.BG.B.A2C.A.C.A.2250.EUR.N",
        frequency=Frequency.MONTHLY,
        unit=Unit.PERCENT_PER_ANNUM,
    ),
    SeriesDef(
        code=BG_CONSUMER_APRC,
        name_bg="Среден ГПР по нови потребителски кредити в България",
        plain_bg=(
            "Пълната годишна цена на потребителския кредит, с всички такси. "
            "Разликата с обявената лихва тук обикновено е най-голяма."
        ),
        source=SourceSystem.ECB,
        source_ref="MIR/M.BG.B.A2B.A.C.A.2250.EUR.N",
        frequency=Frequency.MONTHLY,
        unit=Unit.PERCENT_PER_ANNUM,
    ),
    SeriesDef(
        code=BG_MORTGAGE_VOLUME,
        name_bg="Обем нови ипотечни кредити в България (млн. евро)",
        plain_bg=(
            "Колко нови жилищни кредита са отпуснали банките за месеца. "
            "Растящият обем показва, че пазарът е активен и банките се "
            "конкурират за клиенти."
        ),
        source=SourceSystem.ECB,
        source_ref="MIR/M.BG.B.A2C.A.B.A.2250.EUR.N",
        frequency=Frequency.MONTHLY,
        unit=Unit.MILLION_EUR,
    ),
    SeriesDef(
        code=BG_DEPOSIT_TERM,
        name_bg="Лихва по срочни депозити на домакинствата",
        plain_bg=(
            "Колко ви плаща банката, ако вържете парите си за определен срок. "
            "Ако инфлацията е по-висока от тази лихва, спестяванията ви губят "
            "покупателна способност всяка година."
        ),
        source=SourceSystem.ECB,
        source_ref="MIR/M.BG.B.L22.A.R.A.2250.EUR.N",
        frequency=Frequency.MONTHLY,
        unit=Unit.PERCENT_PER_ANNUM,
    ),
    SeriesDef(
        code=BG_DEPOSIT_OVERNIGHT,
        name_bg="Лихва по разплащателни сметки на домакинствата",
        plain_bg=(
            "Лихвата по обикновената сметка, в която повечето хора държат "
            "парите си. Тя е практически нулева, а инфлацията върви — това е "
            "най-тихата загуба в семейния бюджет."
        ),
        source=SourceSystem.ECB,
        source_ref="MIR/M.BG.B.L21.A.R.A.2250.EUR.N",
        frequency=Frequency.MONTHLY,
        unit=Unit.PERCENT_PER_ANNUM,
    ),
    SeriesDef(
        code=BG_HOUSE_PRICES,
        name_bg="Цени на жилищата в България (годишна промяна)",
        plain_bg=(
            "С колко процента са поскъпнали жилищата за последната година. "
            "Когато имотите растат по-бързо от спестяванията ви, чакането "
            "също струва пари."
        ),
        source=SourceSystem.EUROSTAT,
        source_ref="prc_hpi_q",
        frequency=Frequency.QUARTERLY,
        unit=Unit.PERCENT_CHANGE,
        params={"geo": "BG", "purchase": "TOTAL", "unit": "RCH_A"},
    ),
    SeriesDef(
        code=US_10Y,
        name_bg="Американска 10-годишна държавна облигация",
        plain_bg=(
            "Лихвата по американския държавен дълг. Задава посоката на "
            "световните пазари и често изпреварва европейските движения."
        ),
        source=SourceSystem.US_TREASURY,
        source_ref="10 Yr",
        frequency=Frequency.DAILY,
        unit=Unit.PERCENT_PER_ANNUM,
    ),
)

BY_CODE: dict[str, SeriesDef] = {s.code: s for s in SERIES}

INDEX_SERIES_FOR_LOANS = {
    "EURIBOR_3M": EURIBOR_3M,
    "EURIBOR_6M": EURIBOR_6M,
    "EURIBOR_12M": EURIBOR_12M,
}
