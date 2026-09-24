from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from fractions import Fraction


TICKS_PER_SECOND = 1_000_000


class TimebaseError(ValueError):
    pass


def _decimal(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise TimebaseError(f"Valeur temporelle invalide : {value!r}") from exc
    if not result.is_finite():
        raise TimebaseError(f"Valeur temporelle non finie : {value!r}")
    return result


def seconds_to_ticks(value: object) -> int:
    """Convertit des secondes en ticks entiers à 1 MHz.

    La conversion passe par Decimal(str(value)) afin que les artefacts binaires
    usuels (par ex. 0.1 + 0.2) ne contaminent pas les opérations de montage.
    """

    scaled = _decimal(value) * TICKS_PER_SECOND
    return int(scaled.to_integral_value(rounding=ROUND_HALF_UP))


def ticks_to_seconds(ticks: int) -> float:
    """Convertit les ticks internes vers le format public historique en secondes."""

    return float(Decimal(int(ticks)) / TICKS_PER_SECOND)


def frame_time_ticks(
    frame_index: int,
    fps_numerator: int,
    fps_denominator: int = 1,
) -> int:
    """Position déterministe d'une frame dans le timebase 1 MHz.

    Le calcul reste rationnel jusqu'au dernier arrondi. Cela permet de gérer
    proprement les cadences entières comme 24/25/30 fps et les cadences
    rationnelles comme 24000/1001 sans accumulation de flottants.
    """

    if frame_index < 0:
        raise TimebaseError("frame_index doit être >= 0.")
    if fps_numerator <= 0 or fps_denominator <= 0:
        raise TimebaseError("La cadence doit être strictement positive.")
    value = Fraction(
        int(frame_index) * TICKS_PER_SECOND * int(fps_denominator),
        int(fps_numerator),
    )
    quotient, remainder = divmod(value.numerator, value.denominator)
    if remainder * 2 >= value.denominator:
        quotient += 1
    return quotient
