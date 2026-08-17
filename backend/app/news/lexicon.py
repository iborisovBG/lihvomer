"""Речников hawkish/dovish скоринг на икономически новини.

Подходът следва методиката на Apel и Blix Grimaldi за оценка на тона на
централнобанковата комуникация: вместо общ „позитивен/негативен" сентимент се
броят термини, които конкретно сочат посоката на лихвите. Затова речникът е
двуезичен и претеглен — не всяка дума тежи еднакво.

Знакът е от гледна точка на човек с кредит:
    отрицателно = натиск НАГОРЕ върху лихвите (лошо за вноската)
    положително = натиск НАДОЛУ върху лихвите (добре за вноската)
"""

from __future__ import annotations

import re
import unicodedata

# (термин, тегло). Теглата са в диапазона 0.2–1.0 според това колко пряко
# терминът предсказва посоката на лихвите.
HAWKISH: tuple[tuple[str, float], ...] = (
    # Парична политика
    ("rate hike", 1.0), ("raise interest rates", 1.0), ("rate increase", 0.9),
    ("tighten", 0.8), ("tightening", 0.8), ("restrictive", 0.7),
    ("hawkish", 0.9), ("higher for longer", 0.9),
    ("повишава лихвите", 1.0), ("вдига лихвите", 1.0), ("по-високи лихви", 0.9),
    ("затягане", 0.8), ("рестриктивна", 0.7), ("поскъпване на кредита", 0.9),
    # Инфлация
    ("inflation rose", 0.8), ("inflation accelerated", 0.9),
    ("inflationary pressure", 0.7), ("price pressures", 0.6),
    ("above target", 0.6), ("overheating", 0.7),
    ("инфлацията се ускорява", 0.9), ("инфлацията расте", 0.8),
    ("поскъпване", 0.5), ("над целта", 0.6), ("инфлационен натиск", 0.7),
    # Фискален риск
    ("excessive deficit", 1.0), ("excessive deficit procedure", 1.0),
    ("budget deficit", 0.6), ("fiscal slippage", 0.8), ("downgrade", 0.9),
    ("negative outlook", 0.8), ("debt sustainability", 0.6),
    ("spread widened", 0.9), ("bond yields rose", 0.8), ("sell-off", 0.7),
    ("infringement procedure", 0.6), ("credit rating cut", 1.0),
    ("прекомерен дефицит", 1.0), ("свръхдефицит", 1.0),
    ("наказателна процедура", 0.9), ("бюджетен дефицит", 0.6),
    ("понижен рейтинг", 1.0), ("негативна перспектива", 0.8),
    ("разширяване на спреда", 0.9), ("доходността се повиши", 0.8),
    ("фискален риск", 0.7), ("дългът расте", 0.7),
    # Голи термини с по-малка тежест: сигнализират тема, не категорична посока.
    ("дефицит", 0.35), ("deficit", 0.35), ("свръхразход", 0.5),
    ("ревизия на бюджета", 0.45), ("нов дълг", 0.45), ("emergency budget", 0.6),
    ("raises rates", 1.0), ("hikes", 0.8), ("borrowing costs rise", 0.8),
)

DOVISH: tuple[tuple[str, float], ...] = (
    # Парична политика
    ("rate cut", 1.0), ("lower interest rates", 1.0), ("rate reduction", 0.9),
    ("ease", 0.6), ("easing", 0.7), ("accommodative", 0.8), ("dovish", 0.9),
    ("понижава лихвите", 1.0), ("намалява лихвите", 1.0),
    ("по-ниски лихви", 0.9), ("разхлабване", 0.7), ("поевтиняване на кредита", 0.9),
    # Инфлация
    ("inflation fell", 0.8), ("inflation eased", 0.8), ("disinflation", 0.9),
    ("inflation slowed", 0.8), ("below target", 0.6), ("price stability", 0.4),
    ("инфлацията се забавя", 0.9), ("инфлацията спада", 0.8),
    ("поевтиняване", 0.5), ("под целта", 0.6), ("ценова стабилност", 0.4),
    # Фискален комфорт
    ("budget surplus", 0.8), ("fiscal consolidation", 0.7), ("upgrade", 0.9),
    ("positive outlook", 0.8), ("spread narrowed", 0.9),
    ("bond yields fell", 0.8), ("deficit reduction", 0.8),
    ("бюджетен излишък", 0.8), ("фискална консолидация", 0.7),
    ("повишен рейтинг", 1.0), ("положителна перспектива", 0.8),
    ("свиване на спреда", 0.9), ("доходността се понижи", 0.8),
    ("намаляване на дефицита", 0.8),
    ("cuts rates", 1.0), ("lowers rates", 1.0), ("borrowing costs fall", 0.8),
    ("stable", 0.3), ("стабилни", 0.3), ("забавя се", 0.4),
    ("излишък", 0.6), ("консолидация", 0.5),
)

# Отрицанието обръща знака на следващия термин в рамките на няколко думи.
NEGATIONS = (
    "not", "no", "without", "avoid", "avoided", "rules out", "ruled out",
    "unlikely",
    "не", "няма", "без", "избегна", "избягва", "малко вероятно", "отхвърли",
)

BULGARIA_TERMS = (
    "bulgaria", "bulgarian", "sofia", "bnb", "lev",
    "българия", "български", "българска", "софия", "бнб",
)

NEGATION_WINDOW_CHARS = 45


def normalise(text: str) -> str:
    lowered = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"\s+", " ", lowered)


def _is_negated(haystack: str, position: int) -> bool:
    window = haystack[max(0, position - NEGATION_WINDOW_CHARS) : position]
    return any(negation in window for negation in NEGATIONS)


def score_text(text: str) -> tuple[float, dict]:
    """Връща оценка в [-1, 1] и открити термини.

    Оценката е нормирана разлика между претеглените hawkish и dovish
    попадения, така че дълга новина с много термини не получава автоматично
    по-крайна оценка от кратка.
    """
    haystack = normalise(text)

    hawkish_hits: list[tuple[str, float]] = []
    dovish_hits: list[tuple[str, float]] = []

    for bucket, target in ((HAWKISH, "h"), (DOVISH, "d")):
        for term, weight in bucket:
            position = haystack.find(term)
            if position < 0:
                continue
            negated = _is_negated(haystack, position)
            # Отречен hawkish термин е сигнал в обратната посока.
            flipped = (target == "h") != negated
            (hawkish_hits if flipped else dovish_hits).append((term, weight))

    hawkish_weight = sum(weight for _, weight in hawkish_hits)
    dovish_weight = sum(weight for _, weight in dovish_hits)
    total = hawkish_weight + dovish_weight

    score = 0.0 if total == 0 else (dovish_weight - hawkish_weight) / total
    # Малко термини значи слаб сигнал; свиваме към нулата.
    confidence = min(1.0, total / 2.0)

    return round(score * confidence, 3), {
        "hawkish": [t for t, _ in hawkish_hits],
        "dovish": [t for t, _ in dovish_hits],
        "hawkish_weight": round(hawkish_weight, 2),
        "dovish_weight": round(dovish_weight, 2),
    }


def mentions_bulgaria(text: str) -> bool:
    haystack = normalise(text)
    return any(term in haystack for term in BULGARIA_TERMS)
