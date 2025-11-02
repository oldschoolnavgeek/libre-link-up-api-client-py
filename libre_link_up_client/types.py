"""Type definitions for LibreLinkUp API Client"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class TrendType(str, Enum):
    """Glucose trend direction"""
    SINGLE_DOWN = 'SingleDown'
    FORTY_FIVE_DOWN = 'FortyFiveDown'
    FLAT = 'Flat'
    FORTY_FIVE_UP = 'FortyFiveUp'
    SINGLE_UP = 'SingleUp'
    NOT_COMPUTABLE = 'NotComputable'


@dataclass
class LibreCgmData:
    """Continuous Glucose Monitor data"""
    value: int
    is_high: bool
    is_low: bool
    trend: TrendType
    date: datetime

    def __str__(self) -> str:
        return f"{self.value} mg/dL ({self.trend}) - {self.date.strftime('%Y-%m-%d %H:%M:%S')}"


@dataclass
class Connection:
    """Connection/Patient information"""
    id: str
    patient_id: str
    country: str
    status: int
    first_name: str
    last_name: str
    target_low: int
    target_high: int
    uom: int

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass
class ActiveSensor:
    """Active sensor information"""
    device_id: str
    sensor_number: str


@dataclass
class GlucoseItem:
    """Raw glucose measurement from API"""
    FactoryTimestamp: str
    Timestamp: str
    type: int
    ValueInMgPerDl: int
    TrendArrow: Optional[int]
    TrendMessage: Optional[str]
    MeasurementColor: int
    GlucoseUnits: int
    Value: int
    isHigh: bool
    isLow: bool

