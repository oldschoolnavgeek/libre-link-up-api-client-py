"""Utility functions for LibreLinkUp API Client"""

from datetime import datetime
from typing import Optional
from .types import TrendType, LibreCgmData, GlucoseItem

TREND_MAP = [
    TrendType.NOT_COMPUTABLE,
    TrendType.SINGLE_DOWN,
    TrendType.FORTY_FIVE_DOWN,
    TrendType.FLAT,
    TrendType.FORTY_FIVE_UP,
    TrendType.SINGLE_UP,
    TrendType.NOT_COMPUTABLE,
]


def get_trend(trend: Optional[int], default_trend: TrendType = TrendType.FLAT) -> TrendType:
    """Convert numeric trend to TrendType enum"""
    if trend is not None and 0 <= trend < len(TREND_MAP):
        return TREND_MAP[trend]
    return default_trend


def to_date(date_string: str) -> datetime:
    """Convert timestamp string to datetime object"""
    # Handle various timestamp formats
    try:
        # Try parsing as ISO format first
        if 'UTC' in date_string:
            # Remove UTC and parse
            cleaned = date_string.replace(' UTC', '').strip()
            dt = datetime.fromisoformat(cleaned)
            # Assume UTC if no timezone info
            if dt.tzinfo is None:
                from datetime import timezone
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        else:
            # Try parsing without UTC
            dt = datetime.fromisoformat(date_string)
            if dt.tzinfo is None:
                from datetime import timezone
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
    except (ValueError, AttributeError):
        # Fallback: try parsing common formats
        from dateutil import parser
        return parser.parse(date_string)


def map_data(glucose_item: GlucoseItem) -> LibreCgmData:
    """Map API GlucoseItem to LibreCgmData"""
    return LibreCgmData(
        value=glucose_item.Value,
        is_high=glucose_item.isHigh,
        is_low=glucose_item.isLow,
        trend=get_trend(glucose_item.TrendArrow),
        date=to_date(f"{glucose_item.FactoryTimestamp} UTC")
    )

