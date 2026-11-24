from datetime import UTC, datetime, timedelta

from app.ml import Checkin

START = datetime(2026, 9, 1, 7, tzinfo=UTC)


def make_checkins(
    rows: list[tuple[float | None, float | None, float | None]], prefix: str = "c"
) -> list[Checkin]:
    """One check-in per day from (sleep h, resting HR bpm, mood) tuples, oldest first."""
    return [
        Checkin(f"{prefix}{i}", START + timedelta(days=i), sleep, rhr, mood)
        for i, (sleep, rhr, mood) in enumerate(rows)
    ]


def steady_rows(n: int) -> list[tuple[float, float, float]]:
    """Ordinary small day-to-day variation around 6.5 h / 60 bpm / mood 4."""
    sleeps = [6.4, 6.6, 6.5, 6.3, 6.7, 6.5, 6.4, 6.6, 6.5, 6.2, 6.8, 6.5, 6.4, 6.6]
    rhrs = [60, 61, 59, 60, 62, 58, 60, 61, 59, 60, 61, 60, 59, 61]
    moods = [4, 4, 3, 4, 4, 5, 4, 4, 3, 4, 4, 4, 5, 4]
    return [(sleeps[i % 14], float(rhrs[i % 14]), float(moods[i % 14])) for i in range(n)]


def steady(n: int, prefix: str = "c") -> list[Checkin]:
    return make_checkins(steady_rows(n), prefix)
