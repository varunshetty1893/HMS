"""Timezone-aware UTC timestamp helpers (`docs/11` Section 22).

The restaurant operates in India Standard Time (IST = UTC+05:30).  All timestamps are
stored as UTC in PostgreSQL.  When reports need to aggregate by *local business day*,
use ``ist_day_to_utc_range`` to convert IST calendar dates into UTC windows before
querying.  Never use plain midnight-to-midnight UTC for date-boundary queries.
"""

from datetime import date, datetime, time, timedelta, timezone

# India Standard Time = UTC + 5:30
IST = timezone(timedelta(hours=5, minutes=30), name="IST")

# Canonical reporting timezone.  If the restaurant ever moves, change this constant.
REPORTING_TZ = IST


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """Return the current UTC timestamp formatted as ISO-8601 with trailing 'Z'."""
    return utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")


def ist_day_to_utc_range(
    from_date: date | None = None,
    to_date: date | None = None,
) -> tuple[datetime, datetime]:
    """Convert IST local calendar dates to a UTC [start, end] window for DB queries.

    A sale at 00:30 IST (18:30 UTC previous day) is IST-local today but UTC yesterday.
    This function returns the UTC-aware datetimes that correctly bracket the IST day(s).

    Args:
        from_date: First IST calendar date (inclusive). Defaults to today in IST.
        to_date:   Last IST calendar date (inclusive). Defaults to ``from_date``.

    Returns:
        (start_utc, end_utc) as timezone-aware UTC datetimes ready for SQLAlchemy filters.
    """
    today_ist = datetime.now(REPORTING_TZ).date()
    f = from_date or today_ist
    t = to_date or f

    # 00:00:00.000000 IST on the first day → UTC
    start_ist = datetime.combine(f, time.min, tzinfo=REPORTING_TZ)
    # 23:59:59.999999 IST on the last day → UTC
    end_ist = datetime.combine(t, time.max, tzinfo=REPORTING_TZ)

    return start_ist.astimezone(timezone.utc), end_ist.astimezone(timezone.utc)
