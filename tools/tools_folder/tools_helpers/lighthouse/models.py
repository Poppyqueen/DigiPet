from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ActionInternalResponse:
    """
    Standard response object returned by all LighthouseManager action methods.

    Fields:
        message         Player-facing string describing what happened.
        formatted_events  Pre-joined string of event messages, or None if no events fired.
        events          Raw event list, if the caller needs to inspect individual events.
        success         Whether the action completed successfully. None = not applicable.
        data            Arbitrary action-specific payload for the controller to act on.
                        Only populated when the controller needs structured info beyond
                        success/failure to decide what to do next (e.g. item state after removal).
                        Leave as None for actions where success alone is sufficient.
    """
    message: str
    formatted_events: Optional[str] = None
    events: Optional[List] = None
    success: Optional[bool] = None
    data: Optional[Dict[str, Any]] = None

@dataclass(frozen=True)
class Event:
    event_affordances_keys: list[str]
    type: str
    message: str
    data: Optional[Dict] = None

    def __post_init__(self):
        if self.data is None:
            object.__setattr__(self, 'data', {})




@dataclass(frozen=True)
class WeatherConditions:
    """Current weather from external source."""
    is_day: bool = False
    temperature: float = 20.0  # Celsius
    humidity: float = 0.5  # 0-1
    precipitation: float = 0.0  # mm Preceding 15 minutes sum
    wind_speed: float = 0.0  # km/h
    cloud_cover: float = 0.0  # 0-1
    
    @classmethod
    def from_weather_data(cls, weather_data: Dict[str, Any]) -> 'WeatherConditions':
        """Create from OpenMeteo data."""
        return cls(
            is_day=weather_data.get("is_day", "False") == "True",
            temperature=float(weather_data.get("temperature", 20.0)),
            humidity=float(weather_data.get("humidity", 50.0)) / 100.0,
            precipitation=float(weather_data.get("precipitation", 0.0)),
            wind_speed=float(weather_data.get("wind_speed", 0.0)),
            cloud_cover=float(weather_data.get("cloud_cover", 0.0)) / 100.0
        )
