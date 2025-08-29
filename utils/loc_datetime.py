
from datetime import datetime as _datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# Import your timezone function
from utils.open_meteo_handle import OpenMeteoLoc

class CoordinateDateTime:
    """
    A complete datetime replacement that uses coordinates to determine timezone.
    Supports all standard datetime patterns and methods.
    """
    
    def __init__(self, lat, lon):
        """
        Initialize with latitude and longitude coordinates.
        
        Args:
            lat (float): Latitude (-90 to 90)
            lon (float): Longitude (-180 to 180)
        """
        self.lat = lat
        self.lon = lon
        self.open_meteo = OpenMeteoLoc(long=lon, lat=lat)
        self.timezone_info = self._get_timezone_from_coordinates(lat, lon)
        self.timezone = self.timezone_info['tz_obj']

    def _get_timezone_from_coordinates(self, lat, lon):
        """
        Get timezone using your open_meteo_handle function first, with fallbacks.
        """
        try:
            # Try to use your get_timezone function
            tz_data = self.open_meteo.get_timezone(lat, lon)  # Assumes this function takes lat, lon
            tz_name = tz_data['timezone'].decode('utf-8') if isinstance(tz_data['timezone'], bytes) else tz_data['timezone']
            tz_abbrev = tz_data['timezone_abbreviation'].decode('utf-8') if isinstance(tz_data['timezone_abbreviation'], bytes) else tz_data['timezone_abbreviation']
            
            try:
                tz_obj = ZoneInfo(tz_name)
                print(f"Timezone found: {tz_name} ({tz_abbrev})")
                print("Using provided timezone information.")
                return {
                    'name': tz_name,
                    'abbreviation': tz_abbrev,
                    'tz_obj': tz_obj
                }
            except Exception as e:
                print(f"Warning: Could not create timezone object for {tz_name}, falling back to coordinate calculation")
        except Exception as e:
            print(f"Warning: get_timezone failed ({e}), falling back to coordinate calculation")
        
        # Fallback to coordinate-based timezone estimation
        return self._fallback_timezone_from_coordinates(lat, lon)
    
    def _fallback_timezone_from_coordinates(self, lat, lon):
        """
        Fallback timezone estimation when get_timezone fails.
        """
        # Simple UTC offset based on longitude
        utc_offset_hours = round(lon / 15)
        utc_offset_hours = max(-12, min(12, utc_offset_hours))
        
        # Fallback to simple UTC offset
        tz_obj = timezone(timedelta(hours=utc_offset_hours))
        return {
            'name': f'UTC{utc_offset_hours:+d}',
            'abbreviation': f'UTC{utc_offset_hours:+d}',
            'tz_obj': tz_obj
        }
    

    
    def now(self):
        """Get current datetime in the coordinate's timezone."""
        utc_now = _datetime.now(timezone.utc)
        local_now = utc_now.astimezone(self.timezone)
        return local_now
    
    def fromtimestamp(self, timestamp):
        """Create datetime from timestamp in the coordinate's timezone."""
        utc_dt = _datetime.fromtimestamp(timestamp, tz=timezone.utc)
        local_dt = utc_dt.astimezone(self.timezone)
        return local_dt
    
    def fromisoformat(self, iso_string):
        """Parse ISO format string and convert to coordinate's timezone if needed."""
        dt = _datetime.fromisoformat(iso_string)
        if dt.tzinfo is None:
            # Naive datetime - assume it's in coordinate's timezone
            dt = dt.replace(tzinfo=self.timezone)
        else:
            # Timezone-aware datetime - convert to coordinate's timezone
            dt = dt.astimezone(self.timezone)
        return dt
    
    def strftime(self, format_string):
        """Format current time using the coordinate's timezone."""
        return self.now().strftime(format_string)
    
    def isoformat(self):
        """Get current time in ISO format using coordinate's timezone."""
        return self.now().isoformat()


class datetime:
    """
    Drop-in replacement for datetime.datetime that uses coordinates.
    Supports all your existing usage patterns.
    """
    
    # Class variable to store the coordinate datetime instance
    _coord_dt = None
    
    @classmethod
    def set_coordinates(cls, lat, lon):
        """Set the coordinates for all datetime operations."""
        cls._coord_dt = CoordinateDateTime(lat, lon)
    
    @classmethod
    def now(cls):
        """Current datetime in coordinate's timezone."""
        if cls._coord_dt is None:
            # Fallback to standard datetime if no coordinates set
            return _datetime.now()
        return cls._coord_dt.now()
    
    @classmethod
    def fromtimestamp(cls, timestamp):
        """Create datetime from timestamp."""
        if cls._coord_dt is None:
            return _datetime.fromtimestamp(timestamp)
        return cls._coord_dt.fromtimestamp(timestamp)
    
    @classmethod
    def fromisoformat(cls, iso_string):
        """Parse ISO format string."""
        if cls._coord_dt is None:
            return _datetime.fromisoformat(iso_string)
        return cls._coord_dt.fromisoformat(iso_string)
    
    @classmethod
    def isoformat(cls):
        """Current time in ISO format."""
        return cls.now().isoformat()
    
    @classmethod
    def strftime(cls, format_string):
        """Format current time."""
        return cls.now().strftime(format_string)

