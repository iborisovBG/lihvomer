"""Кредитна математика: ануитет, погасителен план, ГПР, реална стойност.

ГПР се смята по метода от Приложение № 1 към Закона за потребителския кредит
(транспониране на Директива 2008/48/ЕО): годишният процент на разходите е
дисконтовият процент, при който настоящата стойност на усвоеното изравнява
настоящата стойност на всички плащания на потребителя.
"""

from __future__ import annotations

from dataclasses import dataclass

from scipy.optimize import brentq

MONTHS_PER_YEAR = 12


@dataclass(frozen=True)
class ScheduleRow:
    month: int
    payment: float
    interest: float
    principal: float
    balance: float


def monthly_payment(principal: float, annual_rate_pct: float, months: int) -> float:
    """Ануитетна вноска: постоянна сума, в която делът на лихвата спада."""
    if months <= 0:
        raise ValueError("Срокът трябва да е поне един месец.")
    if principal <= 0:
        return 0.0

    monthly_rate = annual_rate_pct / 100.0 / MONTHS_PER_YEAR
    if monthly_rate == 0:
        return principal / months

    factor = (1.0 + monthly_rate) ** months
    return principal * monthly_rate * factor / (factor - 1.0)


def amortization_schedule(
    principal: float, annual_rate_pct: float, months: int
) -> list[ScheduleRow]:
    """Погасителен план в стотинки, както го води банката.

    Смятаме в цели стотинки, а не в плаваща запетая със закръгляне накрая.
    Причината е, че банката начислява закръглена сума всеки месец и следващата
    лихва се начислява върху вече закръгления остатък. Ако закръглим едва при
    показване, сборът на главниците се разминава с главницата — при 240 вноски
    разликата беше пет стотинки, а „общо платено" и „обща лихва" спираха да си
    съответстват.
    """
    payment = monthly_payment(principal, annual_rate_pct, months)
    monthly_rate = annual_rate_pct / 100.0 / MONTHS_PER_YEAR

    # Работим с цели стотинки, за да няма натрупване на грешка.
    balance_c = round(principal * 100)
    payment_c = round(payment * 100)

    rows: list[ScheduleRow] = []
    for month in range(1, months + 1):
        interest_c = round(balance_c * monthly_rate)

        if month == months:
            # Последната вноска покрива точно остатъка.
            principal_c = balance_c
            payment_this_c = balance_c + interest_c
        else:
            principal_c = payment_c - interest_c
            # При много ниска лихва и къс срок вноската може да надхвърли
            # остатъка; тогава плащаме само каквото дължим.
            if principal_c > balance_c:
                principal_c = balance_c
                payment_this_c = balance_c + interest_c
            else:
                payment_this_c = payment_c

        balance_c -= principal_c
        rows.append(
            ScheduleRow(
                month=month,
                payment=payment_this_c / 100.0,
                interest=interest_c / 100.0,
                principal=principal_c / 100.0,
                balance=balance_c / 100.0,
            )
        )
        if balance_c <= 0:
            break

    return rows


def total_interest(principal: float, annual_rate_pct: float, months: int) -> float:
    return sum(row.interest for row in amortization_schedule(principal, annual_rate_pct, months))


def apr_from_cashflows(net_received: float, monthly_outflows: list[float]) -> float:
    """ГПР при произволен профил на месечните плащания.

    Нужно е, когато плащането не е константно — например животозастраховка,
    начислявана върху намаляващата остатъчна главница.
    """
    if net_received <= 0:
        raise ValueError("Първоначалните такси не могат да надхвърлят кредита.")
    if not monthly_outflows or sum(monthly_outflows) <= 0:
        raise ValueError("Нужен е поне един положителен паричен поток.")

    def present_value_gap(annual_rate: float) -> float:
        total = sum(
            amount / (1.0 + annual_rate) ** (month / MONTHS_PER_YEAR)
            for month, amount in enumerate(monthly_outflows, start=1)
        )
        return total - net_received

    # Функцията намалява по дисконтовия процент: при 0% сумата на плащанията
    # е максимална, а с растежа на процента настоящата им стойност спада.
    low, high = 0.0, 1.0
    if present_value_gap(low) <= 0:
        # Изплатеното не надхвърля усвоеното — няма положителен ГПР.
        return 0.0

    while present_value_gap(high) > 0:
        high *= 2.0
        if high > 1e4:
            raise ValueError("ГПР не може да бъде определен за тези параметри.")

    return brentq(present_value_gap, low, high, xtol=1e-10) * 100.0


def annual_percentage_rate(
    principal: float,
    months: int,
    monthly_outflow: float,
    upfront_fees: float = 0.0,
) -> float:
    """ГПР при константно месечно плащане — вноска плюс такси и застраховки."""
    return apr_from_cashflows(principal - upfront_fees, [monthly_outflow] * months)


def real_value(nominal_amount: float, annual_inflation_pct: float, months: int) -> float:
    """Каква е покупателната способност на сума, платена след `months` месеца.

    Вноската остава същата в лева, но с годишна инфлация от например 3.5%
    след 20 години тя „тежи“ съществено по-малко в реални стоки и услуги.
    """
    years = months / MONTHS_PER_YEAR
    return nominal_amount / (1.0 + annual_inflation_pct / 100.0) ** years


def payment_delta(
    principal: float, months: int, old_rate_pct: float, new_rate_pct: float
) -> float:
    """Промяна в месечната вноска при преоценка на лихвата."""
    return monthly_payment(principal, new_rate_pct, months) - monthly_payment(
        principal, old_rate_pct, months
    )
