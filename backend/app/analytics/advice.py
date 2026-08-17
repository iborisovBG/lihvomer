"""Изчисления, които отговарят на въпроса „аз добре ли съм?“.

Четири сметки, всяка стъпваща на реални публикувани данни:

1. Сравнение на лихвата на потребителя със средната пазарна (ЕЦБ MIR).
2. Струва ли си рефинансирането — с таксите и месеца на изравняване.
3. Колко губят спестяванията при лихва под инфлацията.
4. Колко спестява предсрочното погасяване.

Всички суми са в валутата на кредита; преобразуването в левове се прави в
слоя, който показва резултата.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.analytics.finance import (
    MONTHS_PER_YEAR,
    amortization_schedule,
    annual_percentage_rate,
    apr_from_cashflows,
    monthly_payment,
    total_interest,
)

# Под този праг разликата е в рамките на закръгленията по договора и не си
# заслужава да се представя като преплащане.
MATERIAL_RATE_GAP_PP = 0.15


def _years_bg(count: float) -> str:
    """Български словоформи: 1 година, но 2 години."""
    rounded = round(count)
    return "година" if rounded == 1 else "години"


@dataclass
class MarketComparison:
    your_rate_pct: float
    market_rate_pct: float
    market_period: str
    difference_pp: float
    is_above_market: bool
    monthly_difference: float
    remaining_term_difference: float
    verdict_bg: str


@dataclass
class RefinanceScenario:
    new_rate_pct: float
    new_monthly_payment: float
    monthly_saving: float
    upfront_cost: float
    break_even_month: int | None
    total_saving_over_term: float
    is_worth_it: bool
    verdict_bg: str


@dataclass
class SavingsErosion:
    amount: float
    deposit_rate_pct: float
    inflation_pct: float
    real_rate_pct: float
    annual_loss: float
    five_year_loss: float
    verdict_bg: str


@dataclass
class EarlyRepayment:
    extra_monthly: float
    months_saved: int
    interest_saved: float
    new_term_months: int
    verdict_bg: str


def compare_to_market(
    principal: float,
    months: int,
    your_rate_pct: float,
    market_rate_pct: float,
    market_period: str,
) -> MarketComparison:
    """Колко ви струва разликата спрямо средната пазарна лихва.

    Сравнението е с лихвата по НОВИ кредити — това е нивото, което бихте
    получили, ако отидете да преговаряте днес.
    """
    your_payment = monthly_payment(principal, your_rate_pct, months)
    market_payment = monthly_payment(principal, market_rate_pct, months)

    difference = your_rate_pct - market_rate_pct
    monthly_difference = your_payment - market_payment
    term_difference = monthly_difference * months

    above = difference > MATERIAL_RATE_GAP_PP

    if above:
        verdict = (
            f"Лихвата ви е с {difference:.2f} пункта над средната за нови "
            f"кредити. При вашата главница това е {abs(monthly_difference):.0f} "
            f"на месец, или {abs(term_difference):.0f} до края на срока. "
            "Струва си да поискате предоговаряне — банките рядко го предлагат "
            "сами."
        )
    elif difference < -MATERIAL_RATE_GAP_PP:
        verdict = (
            f"Лихвата ви е с {abs(difference):.2f} пункта ПОД средната за нови "
            f"кредити. Договорили сте се добре — предоговаряне най-вероятно "
            "би влошило условията ви."
        )
    else:
        verdict = (
            "Лихвата ви е на нивото на средната за нови кредити. Няма ясна "
            "полза от предоговаряне само заради лихвата."
        )

    return MarketComparison(
        your_rate_pct=round(your_rate_pct, 3),
        market_rate_pct=round(market_rate_pct, 3),
        market_period=market_period,
        difference_pp=round(difference, 3),
        is_above_market=above,
        monthly_difference=round(monthly_difference, 2),
        remaining_term_difference=round(term_difference, 2),
        verdict_bg=verdict,
    )


def evaluate_refinancing(
    principal: float,
    months: int,
    current_rate_pct: float,
    new_rate_pct: float,
    upfront_cost: float,
) -> RefinanceScenario:
    """Оставаш или мърдаш.

    Месецът на изравняване е първият, в който натрупаната икономия покрива
    таксите по прехвърлянето. Ако той е след края на срока, рефинансирането
    не се изплаща.
    """
    current_payment = monthly_payment(principal, current_rate_pct, months)
    new_payment = monthly_payment(principal, new_rate_pct, months)
    monthly_saving = current_payment - new_payment

    break_even: int | None = None
    if monthly_saving > 0:
        needed = upfront_cost / monthly_saving
        candidate = int(needed) + (0 if needed.is_integer() else 1)
        break_even = candidate if candidate <= months else None

    total_saving = monthly_saving * months - upfront_cost
    worth_it = break_even is not None and total_saving > 0

    if monthly_saving <= 0:
        verdict = (
            "Новата лихва не е по-ниска от текущата ви — рефинансирането само "
            "би добавило разходи."
        )
    elif break_even is None:
        verdict = (
            f"Икономията е {monthly_saving:.0f} на месец, но таксите от "
            f"{upfront_cost:.0f} не се покриват до края на срока. Не си струва."
        )
    elif worth_it and upfront_cost <= 0:
        # Без въведени такси сметката показва само чистата разлика в лихвата.
        verdict = (
            f"При пазарна лихва вноската ви пада с {monthly_saving:.0f} на "
            f"месец, което е {total_saving:.0f} до края на срока. Не сте "
            "въвели разходи по прехвърлянето — добавете ги по-горе, за да "
            "видите след колко месеца се изплащат."
        )
    elif worth_it:
        years = break_even / MONTHS_PER_YEAR
        stay = max(1, round(years))
        verdict = (
            f"Спестявате {monthly_saving:.0f} на месец. Таксите от "
            f"{upfront_cost:.0f} се покриват за {break_even} "
            f"{'месец' if break_even == 1 else 'месеца'}, а до края на срока "
            f"оставате на плюс с {total_saving:.0f}. Струва си, ако смятате да "
            f"останете в жилището поне {stay} {_years_bg(stay)}."
        )
    else:
        verdict = (
            f"Таксите се покриват чак на {break_even}-ия месец и общата полза е "
            "твърде малка. Не си струва."
        )

    return RefinanceScenario(
        new_rate_pct=round(new_rate_pct, 3),
        new_monthly_payment=round(new_payment, 2),
        monthly_saving=round(monthly_saving, 2),
        upfront_cost=round(upfront_cost, 2),
        break_even_month=break_even,
        total_saving_over_term=round(total_saving, 2),
        is_worth_it=worth_it,
        verdict_bg=verdict,
    )


def savings_erosion(
    amount: float, deposit_rate_pct: float, inflation_pct: float
) -> SavingsErosion:
    """Колко покупателна способност губят спестяванията за година и за пет.

    Реалната доходност се смята по Фишер, а не като проста разлика — при
    по-високи стойности разликата между двете е осезаема.
    """
    nominal = 1.0 + deposit_rate_pct / 100.0
    prices = 1.0 + inflation_pct / 100.0
    real_rate = (nominal / prices - 1.0) * 100.0

    annual_loss = amount * (nominal / prices - 1.0)
    five_year_loss = amount * ((nominal / prices) ** 5 - 1.0)

    if real_rate < -0.5:
        verdict = (
            f"При лихва {deposit_rate_pct:.2f}% и инфлация {inflation_pct:.2f}% "
            f"парите ви губят {abs(real_rate):.2f}% реална стойност годишно. "
            f"От {amount:.0f} това е около {abs(annual_loss):.0f} за година и "
            f"{abs(five_year_loss):.0f} за пет години. Числото в сметката не "
            "се променя — променя се какво можете да купите с него."
        )
    elif real_rate > 0.5:
        verdict = (
            f"Лихвата изпреварва инфлацията с {real_rate:.2f}% — спестяванията "
            "ви растат и в реални пари."
        )
    else:
        verdict = (
            "Лихвата и инфлацията се движат заедно; спестяванията ви горе-долу "
            "запазват стойността си."
        )

    return SavingsErosion(
        amount=round(amount, 2),
        deposit_rate_pct=round(deposit_rate_pct, 3),
        inflation_pct=round(inflation_pct, 3),
        real_rate_pct=round(real_rate, 3),
        annual_loss=round(annual_loss, 2),
        five_year_loss=round(five_year_loss, 2),
        verdict_bg=verdict,
    )


def evaluate_early_repayment(
    principal: float, months: int, annual_rate_pct: float, extra_monthly: float
) -> EarlyRepayment:
    """Колко скъсява срока и спестява лихва допълнителна вноска всеки месец.

    Симулира се реално погасяване месец по месец, вместо приближение —
    ефектът върху срока не е линеен.
    """
    base_interest = total_interest(principal, annual_rate_pct, months)
    payment = monthly_payment(principal, annual_rate_pct, months) + extra_monthly
    monthly_rate = annual_rate_pct / 100.0 / MONTHS_PER_YEAR

    balance = principal
    paid_interest = 0.0
    elapsed = 0

    while balance > 0.005 and elapsed < months:
        interest = balance * monthly_rate
        principal_part = payment - interest
        if principal_part <= 0:
            # Вноската не покрива дори лихвата; няма как да се погаси по-рано.
            elapsed = months
            paid_interest = base_interest
            break
        balance -= principal_part
        paid_interest += interest
        elapsed += 1

    months_saved = max(0, months - elapsed)
    interest_saved = max(0.0, base_interest - paid_interest)

    if extra_monthly <= 0:
        verdict = "Въведете допълнителна сума, за да видите ефекта."
    elif months_saved == 0:
        verdict = "Тази сума е твърде малка, за да скъси срока с цял месец."
    else:
        years = months_saved / MONTHS_PER_YEAR
        verdict = (
            f"С {extra_monthly:.0f} повече на месец изплащате кредита "
            f"{months_saved} месеца по-рано ({years:.1f} {_years_bg(years)}) и спестявате "
            f"{interest_saved:.0f} лихва. Проверете в договора си дали има "
            "такса за предсрочно погасяване — по закон тя отпада след първите "
            "12 месеца при жилищните кредити."
        )

    return EarlyRepayment(
        extra_monthly=round(extra_monthly, 2),
        months_saved=months_saved,
        interest_saved=round(interest_saved, 2),
        new_term_months=elapsed,
        verdict_bg=verdict,
    )


@dataclass
class WaitingCost:
    target_price: float
    down_payment_pct: float
    saved_now: float
    monthly_saving: float
    house_growth_pct: float
    deposit_rate_pct: float
    needed_now: float
    gap_now: float
    months_to_afford: int | None
    needed_in_year: float
    saved_in_year: float
    gap_in_year: float
    cost_of_one_year: float
    gap_is_widening: bool
    verdict_bg: str


# Догонването се търси най-много толкова напред; отвъд това хоризонтът е
# по-дълъг от смисленото планиране на покупка.
MAX_WAIT_MONTHS = 240


def cost_of_waiting(
    target_price: float,
    down_payment_pct: float,
    saved_now: float,
    monthly_saving: float,
    house_growth_pct: float,
    deposit_rate_pct: float,
) -> WaitingCost:
    """Колко струва отлагането на покупка с една година.

    Сравнява две скорости: с колко расте нужното самоучастие и с колко растат
    спестяванията. Когато първата е по-висока, разликата се разширява и
    спестяването само по себе си не догонва.
    """
    house_monthly = (1.0 + house_growth_pct / 100.0) ** (1 / MONTHS_PER_YEAR)
    deposit_monthly = (1.0 + deposit_rate_pct / 100.0) ** (1 / MONTHS_PER_YEAR)
    share = down_payment_pct / 100.0

    needed_now = target_price * share
    gap_now = needed_now - saved_now

    # Търсим първия месец, в който спестеното покрива нужното самоучастие.
    months_to_afford: int | None = None
    price = target_price
    savings = saved_now
    for month in range(1, MAX_WAIT_MONTHS + 1):
        price *= house_monthly
        savings = savings * deposit_monthly + monthly_saving
        if savings >= price * share:
            months_to_afford = month
            break

    if gap_now <= 0:
        months_to_afford = 0

    needed_in_year = target_price * (1.0 + house_growth_pct / 100.0) * share
    saved_in_year = saved_now * (1.0 + deposit_rate_pct / 100.0) + monthly_saving * 12
    gap_in_year = needed_in_year - saved_in_year
    # Цената на чакането е с колко повече самоучастие ще ви трябва, а не
    # нетното спрямо спестяванията — нетното число подвежда, защото първата
    # година разликата може да се свива, докато в дългосрочен план цената
    # изпреварва.
    cost_of_one_year = needed_in_year - needed_now

    # Разширява се тогава, когато догонване изобщо не се случва в хоризонта.
    widening = months_to_afford is None

    if gap_now <= 0:
        verdict = (
            f"Вече имате нужното самоучастие от {needed_now:,.0f}. Отлагането "
            f"само оскъпява имота — при текущия ръст същото жилище ще струва "
            f"{target_price * (1.0 + house_growth_pct / 100.0):,.0f} след година."
        ).replace(",", " ")
    elif months_to_afford is None:
        verdict = (
            f"При ръст на цените от {house_growth_pct:.1f}% и доходност на "
            f"спестяванията от {deposit_rate_pct:.2f}% разликата се разширява "
            f"по-бързо, отколкото спестявате. Само с този темп самоучастието "
            f"не се догонва в рамките на {MAX_WAIT_MONTHS // 12} години — "
            "нужна е по-висока месечна вноска или по-евтин имот."
        )
    else:
        years = months_to_afford / MONTHS_PER_YEAR
        verdict = (
            f"При тези условия ще съберете самоучастието след около "
            f"{months_to_afford} месеца ({years:.1f} {_years_bg(years)}). "
            f"Всяка година отлагане вдига нужното самоучастие с още "
            f"{cost_of_one_year:,.0f}."
        ).replace(",", " ")

    return WaitingCost(
        target_price=round(target_price, 2),
        down_payment_pct=round(down_payment_pct, 2),
        saved_now=round(saved_now, 2),
        monthly_saving=round(monthly_saving, 2),
        house_growth_pct=round(house_growth_pct, 3),
        deposit_rate_pct=round(deposit_rate_pct, 3),
        needed_now=round(needed_now, 2),
        gap_now=round(gap_now, 2),
        months_to_afford=months_to_afford,
        needed_in_year=round(needed_in_year, 2),
        saved_in_year=round(saved_in_year, 2),
        gap_in_year=round(gap_in_year, 2),
        cost_of_one_year=round(cost_of_one_year, 2),
        gap_is_widening=widening,
        verdict_bg=verdict,
    )


@dataclass
class OfferVerdict:
    amount: float
    months: int
    nominal_rate_pct: float
    monthly_payment: float
    monthly_fee: float
    monthly_insurance: float
    total_monthly_cost: float
    upfront_fee: float
    offer_aprc_pct: float
    market_aprc_pct: float
    market_period: str
    difference_pp: float
    is_above_market: bool
    monthly_difference: float
    total_difference: float
    hidden_cost_pp: float
    verdict_bg: str
    hidden_cost_note_bg: str


def evaluate_offer(
    amount: float,
    months: int,
    nominal_rate_pct: float,
    monthly_fee: float,
    upfront_fee: float,
    property_insurance_annual_pct: float,
    life_insurance_annual_pct: float,
    market_aprc_pct: float,
    market_period: str,
) -> OfferVerdict:
    """Оценява конкретна оферта срещу средния пазарен ГПР.

    Сравнението е по ГПР, а не по обявена лихва — таксите и застраховките
    често обръщат класацията. Затова първо се сглобява реалният паричен поток
    на офертата, а после се търси процентът, който го изравнява с усвоеното.
    """
    schedule = amortization_schedule(amount, nominal_rate_pct, months)
    base_payment = monthly_payment(amount, nominal_rate_pct, months)

    monthly_property = property_insurance_annual_pct / 100.0 * amount / 12.0
    life_rate_monthly = life_insurance_annual_pct / 100.0 / 12.0

    outflows: list[float] = []
    for row in schedule:
        life_premium = life_rate_monthly * (row.balance + row.principal)
        outflows.append(row.payment + monthly_fee + monthly_property + life_premium)

    offer_aprc = apr_from_cashflows(amount - upfront_fee, outflows)
    difference = offer_aprc - market_aprc_pct

    # Каква част от ГПР идва от такси и застраховки, а не от лихвата.
    hidden = offer_aprc - annual_percentage_rate(amount, months, base_payment)

    # Изразяваме разликата в пари чрез вноска при пазарния ГПР.
    market_payment = monthly_payment(amount, market_aprc_pct, months)
    offer_equivalent = monthly_payment(amount, offer_aprc, months)
    monthly_difference = offer_equivalent - market_payment

    above = difference > MATERIAL_RATE_GAP_PP

    if above:
        verdict = (
            f"ГПР на офертата е {offer_aprc:.2f}%, а средният на пазара — "
            f"{market_aprc_pct:.2f}% ({market_period} по данни на ЕЦБ). "
            f"Плащате с {difference:.2f} пункта повече, което при тази сума и "
            f"срок е около {abs(monthly_difference):.0f} на месец и "
            f"{abs(monthly_difference) * months:.0f} за целия период. "
            "Има смисъл да поискате по-добри условия или да проверите друга банка."
        )
    elif difference < -MATERIAL_RATE_GAP_PP:
        verdict = (
            f"ГПР на офертата е {offer_aprc:.2f}% при среден за пазара "
            f"{market_aprc_pct:.2f}%. Офертата е с {abs(difference):.2f} пункта "
            "по-добра от средното — това е конкурентно предложение."
        )
    else:
        verdict = (
            f"ГПР на офертата е {offer_aprc:.2f}%, практически на нивото на "
            f"средния пазарен {market_aprc_pct:.2f}%. Офертата е обичайна за "
            "пазара; разликата ще дойде от условията, не от цената."
        )

    if hidden > 0.5:
        hidden_note = (
            f"Внимание: {hidden:.2f} от {offer_aprc:.2f}% ГПР идват от такси и "
            f"застраховки, а не от лихвата. Обявената лихва "
            f"{nominal_rate_pct:.2f}% крие съществени допълнителни разходи."
        )
    elif hidden > 0.05:
        hidden_note = (
            f"Таксите и застраховките добавят {hidden:.2f} пункта над обявената "
            f"лихва от {nominal_rate_pct:.2f}%."
        )
    else:
        hidden_note = (
            "Офертата няма съществени такси над лихвата — ГПР и обявената "
            "лихва почти съвпадат."
        )

    return OfferVerdict(
        amount=round(amount, 2),
        months=months,
        nominal_rate_pct=round(nominal_rate_pct, 3),
        monthly_payment=round(base_payment, 2),
        monthly_fee=round(monthly_fee, 2),
        monthly_insurance=round(monthly_property + life_rate_monthly * amount, 2),
        total_monthly_cost=round(outflows[0] if outflows else 0.0, 2),
        upfront_fee=round(upfront_fee, 2),
        offer_aprc_pct=round(offer_aprc, 3),
        market_aprc_pct=round(market_aprc_pct, 3),
        market_period=market_period,
        difference_pp=round(difference, 3),
        is_above_market=above,
        monthly_difference=round(monthly_difference, 2),
        total_difference=round(monthly_difference * months, 2),
        hidden_cost_pp=round(hidden, 3),
        verdict_bg=verdict,
        hidden_cost_note_bg=hidden_note,
    )
