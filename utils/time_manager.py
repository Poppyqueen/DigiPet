from .loc_datetime import datetime
# --- Updated get_time_tag function ---
def get_time_tag(hour: int) -> str | None:
    """
    Maps an hour (0-23) to a predefined time tag string
    with updated ranges including 'late night' wrapping midnight.
    Returns None if the hour is outside the 0-23 range.
    """
    # Validate input range first
    if not 0 <= hour <= 23:
        return None

    # Check the ranges chronologically, handling the late night wrap-around
    # Start with the hours just after midnight that are now late night
    if 0 <= hour <= 3:
        return 'late night'
    # Then the newly defined early morning range
    elif 4 <= hour <= 6:
        return 'early morning'
    # Then the adjusted morning range
    elif 7 <= hour <= 11:
        return 'morning'
    # The rest of the day follows the original structure
    elif hour == 12:
        return 'noon'
    elif 13 <= hour <= 16:
        return 'afternoon'
    elif 17 <= hour <= 19:
        return 'late afternoon'
    # The part of the night before late night starts (again, adjusted slightly)
    elif 20 <= hour <= 23:
        return 'night'

    # No need for an else here because 0-23 is fully covered by the checks above


def get_time_tag_from_now() -> str | None:
    """
    Gets the current time and returns the corresponding time tag.
    Returns None if the hour is outside the 0-23 range.

    Time tags:
    - 0-3: 'late night'
    - 4-6: 'early morning'
    - 7-11: 'morning'
    - 12: 'noon'
    - 13-16: 'afternoon'
    - 17-19: 'late afternoon'
    - 20-23: 'night'
    
    """
    now = datetime.now()
    current_hour = now.hour
    return get_time_tag(current_hour)