"""Plain-language explanations built from per-indicator comparisons (never model internals).

Wording rules (AGENTS.md): compare only with the person's own history; say "differs from your
usual", "worth reviewing", "collecting baseline"; never use diagnosis words.
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from app.ml.features import BASELINE_WINDOW, MIN_HISTORY, MIN_INDICATOR_VALUES, IndicatorFeatures
from app.ml.types import INDICATORS, Checkin

if TYPE_CHECKING:
    from app.ml.analyze import ContributingChange

NOT_VALIDATED = (
    "This compares you only with your own history; it is not validated on astronaut medical "
    "data and is not a diagnosis."
)

_SPECS = {s.field: s for s in INDICATORS}


def _fmt(value: float, decimals: int) -> str:
    return f"{value:.{decimals}f}"


def _value(field: str, value: float) -> str:
    spec = _SPECS[field]
    if field == "mood_rating":
        return f"{_fmt(value, 1 if value % 1 else 0)}/5"
    # Medians of an even count can be halves (63.5 bpm); show them as they are.
    decimals = spec.decimals if value == round(value, spec.decimals) else spec.decimals + 1
    return f"{_fmt(value, decimals)} {spec.unit}"


def _period(window: Sequence[Checkin]) -> str:
    first = window[0].recorded_at.date().isoformat()
    last = window[-1].recorded_at.date().isoformat()
    return (
        f"your usual = median of your last {len(window)} check-ins ({first} to {last}, UTC)"
        if len(window) == BASELINE_WINDOW
        else f"your usual = median of your {len(window)} earlier check-ins ({first} to {last}, UTC)"
    )


def _left_out(features: Sequence[IndicatorFeatures]) -> list[str]:
    notes = []
    for f in features:
        name = f.spec.name.capitalize()
        if f.status == "not_recorded":
            notes.append(f"{name} was not recorded in this check-in, so it was not compared.")
        elif f.status == "short_history":
            notes.append(
                f"{name} has only {f.n_values} recorded values in your recent check-ins "
                f"({MIN_INDICATOR_VALUES} needed), so it was left out."
            )
    return notes


def explain(
    label: str,
    features: Sequence[IndicatorFeatures],
    changes: "Sequence[ContributingChange]",
    window: Sequence[Checkin],
    *,
    n_earlier: int,
    has_target: bool,
) -> str:
    if label == "insufficient_data":
        if not has_target:
            return (
                "Collecting baseline: there are no check-ins yet. After "
                f"{MIN_HISTORY} check-ins, Pulsar starts comparing each new one with your usual "
                "pattern."
            )
        if n_earlier < MIN_HISTORY:
            return (
                f"Collecting baseline: {n_earlier} earlier check-in"
                f"{'' if n_earlier == 1 else 's'} so far; Pulsar needs {MIN_HISTORY} before it "
                "compares a check-in with your usual pattern."
            )
        return " ".join(
            ["Collecting baseline: no indicator in this check-in could be compared yet."]
            + _left_out(features)
        )

    parts: list[str] = []
    if label == "worth_reviewing":
        described = []
        for i, c in enumerate(changes):
            spec = _SPECS[c.feature]
            direction = "below" if c.observed < c.baseline else "above"
            name = spec.name.capitalize() if i == 0 else spec.name
            subject = (
                f"{name} was {_value(c.feature, c.observed)}"
                if c.basis == "this_checkin"
                else f"{name} averaged {_value(c.feature, c.observed)} over your last 3 check-ins"
            )
            described.append(f"{subject}, {direction} your usual {_value(c.feature, c.baseline)}")
        parts.append("This check-in differs from your usual pattern and is worth reviewing.")
        parts.append("; ".join(described) + ".")
    else:
        compared = [
            f"{f.spec.name} {_value(f.spec.field, f.observed)} "
            f"(usual {_value(f.spec.field, f.baseline)})"
            for f in features
            if f.status == "used" and f.observed is not None and f.baseline is not None
        ]
        parts.append("This check-in is close to your usual pattern: " + ", ".join(compared) + ".")
    parts.append(_period(window)[0].upper() + _period(window)[1:] + ".")
    parts.extend(_left_out(features))
    parts.append(NOT_VALIDATED)
    return " ".join(parts)
