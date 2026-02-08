"""
Refactored Lantern Room System
===============================

Clean architecture for Fresnel lens management:
- Immutable state
- Pure functions for rules
- Event system for transitions
- Weather integration
"""

# TODO: Add oil level for clockwork mechanism

from dataclasses import dataclass, replace
from typing import List, Tuple, Optional, Dict, Any
from bisect import bisect_left


# ============================================================================
# CORE STATE - Immutable
# ============================================================================

@dataclass(frozen=True)
class LanternRoomPhysics:
    """Physical state that changes over time."""
    outdoor_cleanliness: float = 1.0  # 0=dirty, 1=clean
    interior_condensation: float = 0.0  # 0=dry, 1=wet
    clockwork_tension: float = 0.0  # 0=unwound, 1=fully wound


@dataclass(frozen=True)
class LanternRoomControls:
    """Direct player controls."""
    sheet_covering: bool = False


@dataclass(frozen=True)
class WeatherConditions:
    """Current weather from external source."""
    is_day: bool = False
    temperature: float = 20.0  # Celsius
    humidity: float = 0.5  # 0-1
    precipitation: float = 0.0  # mm
    wind_speed: float = 0.0  # m/s
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


@dataclass(frozen=True)
class LanternRoomDerived:
    """Computed state."""
    # Lens rotation speed (based on clockwork) TODO: Remove this rotation speed, lens rotation is managed by a careful timed mechanism in the clockwork apparatus instead of the weights in the clockwork, this is an intrinsic and unique identifiable feature of the lighthouse.
    rotation_active: bool = False
    #rotation_speed: float = 0.0  # 0-1
    
    # Light transmission (based on cleanliness + condensation)
    light_transmission: float = 1.0  # 0-1
    
    # Sun hazard (focused light danger)
    sun_hazard_active: bool = False
    sun_hazard_level: float = 0.0  # 0-1


# ============================================================================
# EVENTS
# ============================================================================

@dataclass(frozen=True)
class LanternEvent:
    """Something that happened in the lantern room."""
    type: str
    message: str
    data: Dict = None
    
    def __post_init__(self):
        if self.data is None:
            object.__setattr__(self, 'data', {})


# ============================================================================
# CONSTANTS
# ============================================================================

class LanternConstants:
    """All magic numbers."""
    
    # Decay rates per tick
    CLEANLINESS_DECAY_RATE = 0.0025
    CLOCKWORK_DECAY_RATE = 0.0025
    CONDENSATION_DECAY_RATE = 0.0001  # Slowly dries
    
    # Condensation increase (based on humidity)
    CONDENSATION_INCREASE_BASE = 0.005
    
    # Cleaning amounts
    CLEAN_AMOUNT_DEFAULT = 0.5
    WINDUP_AMOUNT_DEFAULT = 0.5
    
    # Rotation thresholds
    MIN_TENSION_FOR_ROTATION = 0.1
    
    # Sun hazard
    SUN_HAZARD_CLEANLINESS_THRESHOLD = 0.5  # Need clean lens for hazard


# ============================================================================
# LOOKUP TABLES
# ============================================================================

class LanternTables:
    """Lookup tables for descriptions."""
    
    CLEANLINESS_LEVELS = [
        (0.0, "filthy", "The window panes are completely obscured by grime."),
        (0.25, "dirty", "The window panes are dirty."),
        (0.50, "somewhat clean", "The window panes are somewhat clean."),
        (0.75, "clean", "The window panes are clean."),
        (0.95, "spotless", "The window panes are spotless."),
    ]
    
    CONDENSATION_LEVELS = [
        (0.0, "dry", "The interior of the glass panes are dry."),
        (0.25, "slightly damp", "The interior of the glass panes are slightly damp."),
        (0.50, "damp", "The interior of the glass panes are damp."),
        (0.75, "wet", "The interior of the glass panes are wet."),
        (0.95, "dripping", "The interior of the glass panes are dripping with condensation."),
    ]
    
    CLOCKWORK_LEVELS = [
        (0.0, "unwound", "The clockwork is completely unwound."),
        (0.25, "barely wound", "The clockwork is barely wound up."),
        (0.50, "half wound", "The clockwork is half wound up."),
        (0.75, "mostly wound", "The clockwork is mostly wound up."),
        (0.95, "fully wound", "The clockwork is fully wound up."),
    ]
    
    @staticmethod
    def find_level(value: float, levels: List[Tuple[float, str, str]]) -> Tuple[str, str]:
        """
        Find the appropriate level for a value.
        Returns (level_name, description).
        """
        threshold_values = [t[0] for t in levels]
        idx = bisect_left(threshold_values, value)
        
        if idx == 0:
            return levels[0][1], levels[0][2]
        
        idx = min(idx, len(levels) - 1)
        return levels[idx][1], levels[idx][2]


# ============================================================================
# RULES
# ============================================================================

class LanternRules:
    """Pure functions for game logic."""
    
    @staticmethod
    def is_rotation_active(phys: LanternRoomPhysics) -> bool:
        """Is the clockwork rotating the lens?"""
        return phys.clockwork_tension >= LanternConstants.MIN_TENSION_FOR_ROTATION
    
    # @staticmethod
    # def calculate_rotation_speed(phys: LanternRoomPhysics) -> float:
    #     """How fast is the lens rotating?"""
    #     if not LanternRules.is_rotation_active(phys):
    #         return 0.0
    #     # Speed proportional to tension
    #     return phys.clockwork_tension
    
    @staticmethod
    def calculate_light_transmission(phys: LanternRoomPhysics) -> float:
        """
        How much light passes through?
        Reduced by dirt and condensation.
        """
        # Both cleanliness and lack of condensation contribute
        clean_factor = phys.outdoor_cleanliness
        dry_factor = 1.0 - phys.interior_condensation
        
        # Combined (multiplicative - both affect transmission)
        return clean_factor * dry_factor
    
    @staticmethod
    def is_sun_hazard_active(
        weather: WeatherConditions,
        ctrl: LanternRoomControls,
        phys: LanternRoomPhysics
    ) -> bool:
        """
        Is focused sunlight creating a hazard?
        
        Requires:
        - Daytime
        - No sheet covering
        - Reasonably clean lens
        """
        return (
            weather.is_day and
            not ctrl.sheet_covering and
            phys.outdoor_cleanliness >= LanternConstants.SUN_HAZARD_CLEANLINESS_THRESHOLD
        )
    
    @staticmethod
    def calculate_sun_hazard_level(
        weather: WeatherConditions,
        phys: LanternRoomPhysics
    ) -> float:
        """
        How dangerous is the focused sunlight?
        
        Higher with:
        - Cleaner lens (more focus)
        - Less condensation (more transmission)
        """
        from utils.time_manager import get_time_tag_from_now

        # TODO: Instead of using this day flag, use the... time provider to make a map 
        # tags are 'late night', 'early morning', 'morning', 'noon', 'afternoon', 'late afternoon', 'night'
        time_tag = get_time_tag_from_now()

        if time_tag in ['late night', 'early morning', 'night', 'late afternoon']:
            return 0.0
        
        # if not weather.is_day:
        #     return 0.0
        
        # Base hazard is light transmission
        return LanternRules.calculate_light_transmission(phys)

    @staticmethod
    def calculate_condensation_rate(weather: WeatherConditions) -> float:
        """
        How fast does condensation form?
        
        Factors:
        - High humidity increases condensation
        - Precipitation (rain) increases condensation dramatically
        - Temperature differences (not modeled yet) would also matter
        """
        # Base rate from humidity (your current approach)
        humidity_rate = LanternConstants.CONDENSATION_INCREASE_BASE * weather.humidity
        
        # Rain dramatically increases condensation
        if weather.precipitation > 0.0:
            # Even light rain (0.1mm) increases condensation
            # Heavy rain (10mm+) increases it much more
            rain_factor = 1.0 + min(weather.precipitation * 0.5, 5.0)
            humidity_rate *= rain_factor
            print(f"DEBUG: Rain factor: {rain_factor}")

        # DEBUG: 
        print(f"DEBUG: Condensation rate: {humidity_rate}")
        print(f"DEBUG: Weather: {weather}")
        print(f"DEBUG: Humidity: {weather.humidity}")
        print(f"DEBUG: Precipitation: {weather.precipitation}")

        print(f"DEBUG: Humidity rate: {humidity_rate}")
        
        
        return humidity_rate


# ============================================================================
# STATE COMPUTER
# ============================================================================

class LanternStateComputer:
    """Computes all derived state."""
    
    @staticmethod
    def compute(
        phys: LanternRoomPhysics,
        ctrl: LanternRoomControls,
        weather: WeatherConditions
    ) -> LanternRoomDerived:
        """Pure function: base state -> derived state."""
        
        rotation_active = LanternRules.is_rotation_active(phys)
        #rotation_speed = LanternRules.calculate_rotation_speed(phys)
        light_transmission = LanternRules.calculate_light_transmission(phys)
        sun_hazard_active = LanternRules.is_sun_hazard_active(weather, ctrl, phys)
        sun_hazard_level = LanternRules.calculate_sun_hazard_level(weather, phys) if sun_hazard_active else 0.0
        
        return LanternRoomDerived(
            rotation_active=rotation_active,
            #rotation_speed=rotation_speed,
            light_transmission=light_transmission,
            sun_hazard_active=sun_hazard_active,
            sun_hazard_level=sun_hazard_level
        )


# ============================================================================
# PHYSICS ENGINE
# ============================================================================

class LanternPhysicsEngine:
    """Applies physical laws."""
    
    @staticmethod
    def tick(
        phys: LanternRoomPhysics,
        ctrl: LanternRoomControls,
        weather: WeatherConditions
    ) -> LanternRoomPhysics:
        """Apply physics for one tick."""
        
        # Cleanliness decays (gets dirty over time)
        new_cleanliness = max(0.0, phys.outdoor_cleanliness - LanternConstants.CLEANLINESS_DECAY_RATE)
        
        # Clockwork tension decays (winds down)
        new_tension = max(0.0, phys.clockwork_tension - LanternConstants.CLOCKWORK_DECAY_RATE)
        
        # Condensation
        if ctrl.sheet_covering:
            # Sheet prevents new condensation, allows drying
            condensation_delta = -LanternConstants.CONDENSATION_DECAY_RATE
        else:
            # Condensation forms based on humidity, minus natural drying
            condensation_rate = LanternRules.calculate_condensation_rate(weather)
            condensation_delta = condensation_rate - LanternConstants.CONDENSATION_DECAY_RATE
        
        new_condensation = max(0.0, min(1.0, phys.interior_condensation + condensation_delta))
        
        return LanternRoomPhysics(
            outdoor_cleanliness=new_cleanliness,
            interior_condensation=new_condensation,
            clockwork_tension=new_tension
        )


# ============================================================================
# EVENT DETECTOR
# ============================================================================

class LanternEventDetector:
    """Detects state transitions."""
    
    @staticmethod
    def detect_transitions(
        old_phys: LanternRoomPhysics,
        old_ctrl: LanternRoomControls,
        old_derived: LanternRoomDerived,
        old_weather: WeatherConditions,
        new_phys: LanternRoomPhysics,
        new_ctrl: LanternRoomControls,
        new_derived: LanternRoomDerived,
        new_weather: WeatherConditions
    ) -> List[LanternEvent]:
        """Compare states and emit events."""
        events = []
        
        # Rotation changes
        if not old_derived.rotation_active and new_derived.rotation_active:
            events.append(LanternEvent(
                "rotation_started",
                "The clockwork mechanism engages. The Fresnel lens begins to rotate slowly."
            ))
        elif old_derived.rotation_active and not new_derived.rotation_active:
            events.append(LanternEvent(
                "rotation_stopped",
                "The clockwork winds down. The Fresnel lens stops rotating."
            ))
        
        # # Rotation speed changes (if active)
        # if old_derived.rotation_active and new_derived.rotation_active:
        #     if new_derived.rotation_speed < 0.25 and old_derived.rotation_speed >= 0.25:
        #         events.append(LanternEvent(
        #             "rotation_slowing",
        #             "The lens rotation is slowing down significantly."
        #         ))
        
        # Sun hazard changes
        if not old_derived.sun_hazard_active and new_derived.sun_hazard_active:
            events.append(LanternEvent(
                "sun_hazard_started",
                "The Fresnel lens focuses the sun's rays into a concentrated beam! Danger!",
                {'hazard_level': new_derived.sun_hazard_level}
            ))
        elif old_derived.sun_hazard_active and not new_derived.sun_hazard_active:
            events.append(LanternEvent(
                "sun_hazard_ended",
                "The focused sunlight hazard has passed."
            ))
        
        # Sheet covering changes
        if not old_ctrl.sheet_covering and new_ctrl.sheet_covering:
            if old_weather.is_day:
                events.append(LanternEvent(
                    "sheet_placed_day",
                    "The sheet covers the storm panes, protecting everything from the Fresnel lens's concentrated rays."
                ))
            else:
                events.append(LanternEvent(
                    "sheet_placed_night",
                    "The sheet covers the lens, obscuring it from view."
                ))
        elif old_ctrl.sheet_covering and not new_ctrl.sheet_covering:
            if new_weather.is_day:
                events.append(LanternEvent(
                    "sheet_removed_day",
                    "The sheet is removed. Everything is now exposed to the Fresnel lens's concentrated rays!"
                ))
            else:
                events.append(LanternEvent(
                    "sheet_removed_night",
                    "The sheet is removed. The lens is now visible through the glass."
                ))
        
        # Cleanliness warnings
        if (old_phys.outdoor_cleanliness >= 0.5 and 
            new_phys.outdoor_cleanliness < 0.5):
            events.append(LanternEvent(
                "lens_dirty",
                "The lens has become quite dirty."
            ))
        
        # Condensation warnings
        if (old_phys.interior_condensation < 0.5 and 
            new_phys.interior_condensation >= 0.5):
            events.append(LanternEvent(
                "condensation_heavy",
                "Heavy condensation is forming on the interior of the glass."
            ))
        
        # Day/night transitions
        if not old_weather.is_day and new_weather.is_day:
            events.append(LanternEvent(
                "sunrise",
                "The sun rises. The Fresnel lens begins to catch the light."
            ))
        elif old_weather.is_day and not new_weather.is_day:
            events.append(LanternEvent(
                "sunset",
                "The sun sets. The danger of focused sunlight passes."
            ))
        
        return events


# ============================================================================
# LANTERN ROOM SIMULATION
# ============================================================================

class LanternRoom:
    """
    Complete lantern room simulation.
    
    Architecture matches IOVLamp:
    - Immutable state
    - Pure functions
    - Events for transitions
    """
    
    def __init__(self, weather_provider=None):
        self.physics = LanternRoomPhysics()
        self.controls = LanternRoomControls()
        self.weather = WeatherConditions()
        self.weather_provider = weather_provider
        
        # Compute initial derived state
        self.derived = LanternStateComputer.compute(
            self.physics, 
            self.controls, 
            self.weather
        )
    
    def tick(self) -> List[LanternEvent]:
        """
        Advance simulation by one tick.
        Returns events that occurred.
        """
        # Store old state
        old_phys = self.physics
        old_ctrl = self.controls
        old_derived = self.derived
        old_weather = self.weather
        
        # Update weather from provider
        if self.weather_provider:
            weather_data = self.weather_provider.get_structured_weather()
            self.weather = WeatherConditions.from_weather_data(weather_data)
        
        # Apply physics
        self.physics = LanternPhysicsEngine.tick(
            self.physics, 
            self.controls, 
            self.weather
        )
        
        # Recompute derived state
        self.derived = LanternStateComputer.compute(
            self.physics, 
            self.controls, 
            self.weather
        )
        
        # Detect transitions
        events = LanternEventDetector.detect_transitions(
            old_phys, old_ctrl, old_derived, old_weather,
            self.physics, self.controls, self.derived, self.weather
        )
        
        return events
    
    def _update_derived(self) -> List[LanternEvent]:
        """
        Recompute derived state immediately (player action).
        Returns events from state transitions.
        """
        old_derived = self.derived
        old_ctrl = self.controls
        
        self.derived = LanternStateComputer.compute(
            self.physics, 
            self.controls, 
            self.weather
        )
        
        # Detect transitions
        events = LanternEventDetector.detect_transitions(
            self.physics, old_ctrl, old_derived, self.weather,
            self.physics, self.controls, self.derived, self.weather
        )
        
        return events
    
    # ========================================================================
    # PLAYER ACTIONS
    # ========================================================================
    
    def clean_window_panes(self, amount: float = None) -> Tuple[str, List[LanternEvent]]:
        """Clean the exterior window panes."""
        if amount is None:
            amount = LanternConstants.CLEAN_AMOUNT_DEFAULT
        
        if self.physics.outdoor_cleanliness >= 1.0:
            return "The window panes are already spotless.", []
        
        new_cleanliness = min(1.0, self.physics.outdoor_cleanliness + amount)
        self.physics = replace(self.physics, outdoor_cleanliness=new_cleanliness)
        
        events = self._update_derived()
        
        level, desc = LanternTables.find_level(
            self.physics.outdoor_cleanliness, 
            LanternTables.CLEANLINESS_LEVELS
        )
        
        msg = f"You clean the window panes. They are now {level}."
        return msg, events
    
    def clean_condensation(self, amount: float = None) -> Tuple[str, List[LanternEvent]]:
        """Clean condensation from interior glass."""
        if amount is None:
            amount = LanternConstants.CLEAN_AMOUNT_DEFAULT
        
        if self.physics.interior_condensation <= 0.0:
            return "The interior glass is already dry.", []
        
        new_condensation = max(0.0, self.physics.interior_condensation - amount)
        self.physics = replace(self.physics, interior_condensation=new_condensation)
        
        events = self._update_derived()
        
        level, desc = LanternTables.find_level(
            self.physics.interior_condensation, 
            LanternTables.CONDENSATION_LEVELS
        )
        
        msg = f"You wipe away the condensation. The interior is now {level}. {self.physics.interior_condensation:.0%} of the interior is covered in condensation."
        return msg, events
    
    def windup_clockwork(self, amount: float = None) -> Tuple[str, List[LanternEvent]]:
        """Wind up the clockwork mechanism."""
        if amount is None:
            amount = LanternConstants.WINDUP_AMOUNT_DEFAULT
        
        if self.physics.clockwork_tension >= 1.0:
            return "The clockwork is already fully wound.", []
        
        new_tension = min(1.0, self.physics.clockwork_tension + amount)
        self.physics = replace(self.physics, clockwork_tension=new_tension)
        
        events = self._update_derived()
        
        level, desc = LanternTables.find_level(
            self.physics.clockwork_tension, 
            LanternTables.CLOCKWORK_LEVELS
        )
        
        msg = f"You wind the clockwork. It is now {level}. {self.physics.clockwork_tension:.0%} of the clockwork is wound."
        return msg, events
    
    def place_sheet(self) -> Tuple[str, List[LanternEvent]]:
        """Place protective sheet over lens."""
        if self.controls.sheet_covering:
            return "The sheet is already in place.", [], False
        
        self.controls = replace(self.controls, sheet_covering=True)
        events = self._update_derived()
        
        msg = "You place the protective sheet over the storm panes."
        return msg, events, True
    
    def remove_sheet(self) -> Tuple[str, List[LanternEvent]]:
        """Remove protective sheet."""
        if not self.controls.sheet_covering:
            return "There is no sheet to remove.", [], False
        
        self.controls = replace(self.controls, sheet_covering=False)
        events = self._update_derived()
        
        msg = "You remove the protective sheet."
        return msg, events, True
    
    # ========================================================================
    # STATUS REPORTING
    # ========================================================================

    def get_hazardous_weather(self) -> str:
        if self.derived.sun_hazard_active:
            lines = [
                "⚠️  SUN HAZARD ACTIVE",
                f"Hazard Level: {self.derived.sun_hazard_level:.0%}",
                "The Fresnel lens is focusing sunlight into a dangerous beam!"
            ]
        else:
            lines = []
        return "\n".join(lines)

    def get_sheets(self) -> str:
        lines = [
            "--- Protection ---",
            f"Sheet Covering: {'Yes' if self.controls.sheet_covering else 'No'}",
        ]
        return "\n".join(lines)

    def get_outdoor_cleanliness(self) -> float:
        """Get the current cleanliness of the exterior."""
        clean_level, clean_desc = LanternTables.find_level(
            self.physics.outdoor_cleanliness,
            LanternTables.CLEANLINESS_LEVELS
        )
        lines = [
            f"Exterior Cleanliness: {self.physics.outdoor_cleanliness:.0%} ({clean_level})",
            f"  {clean_desc}",
            "",
            f"Light Transmission: {self.derived.light_transmission:.0%}",
            "",
        ]
        return "\n".join(lines)

    def get_interior_condensation(self) -> float:
        """Get the current condensation level of the interior."""
        condensation_level, condensation_desc = LanternTables.find_level(
            self.physics.interior_condensation,
            LanternTables.CONDENSATION_LEVELS
        )
        lines = [
            f"Interior Condensation: {self.physics.interior_condensation:.0%} ({condensation_level})",
            f"  {condensation_desc}",
            "",
            f"Light Transmission: {self.derived.light_transmission:.0%}",
        ]
        return "\n".join(lines)

    def get_fresnel_rotation(self) -> str:
        """Get the current rotation state of the Fresnel lens."""
        lines = [
            "--- Fresnel Rotation ---",
            f"Rotation: {'Active' if self.derived.rotation_active else 'Stopped'}",
        ]
        # if self.derived.rotation_active:
        #     lines.append(f"Speed: {self.derived.rotation_speed:.0%}")
        #     lines.append("")
        return "\n".join(lines)

    def get_clockwork_tension(self) -> float:
        """Get the current tension of the clockwork."""
        clockwork_level, clockwork_desc = LanternTables.find_level(
            self.physics.clockwork_tension,
            LanternTables.CLOCKWORK_LEVELS
        )
        lines = [
            "--- Clockwork Mechanism ---",
            f"Tension: {self.physics.clockwork_tension:.0%} ({clockwork_level})",
            f"  {clockwork_desc}",
            
        ]
        # if self.derived.rotation_active:
        #     lines.append(f"Speed: {self.derived.rotation_speed:.0%}")
        return "\n".join(lines)

    def get_interior_status(self) -> float:
        """Get the current interior status."""
        lines = [
            "--- Weather Facing Glass Panes ---",
            self.get_interior_condensation(),
            self.get_sheets(),
            self.get_hazardous_weather(),
            "",
        ]
        return "\n".join(lines)
    
    def get_status(self) -> str:
        """Complete status report."""
        lines = []

        lines.extend([
            "=== LANTERN ROOM ===",
            "--- Exterior Panes ---",
            self.get_outdoor_cleanliness(),
            "--- Interior Panes ---",
            self.get_interior_condensation(),
            "--- Fresnel Lens Clockwork ---",
            self.get_clockwork_tension(),
            self.get_fresnel_rotation(),
            "",
            "--- Protection ---",
            self.get_sheets(),
            "",
            "--- Environment ---",
            self.get_hazardous_weather(),
            "",
        ])
        
        return "\n".join(lines)
    
    def get_hazard_status(self) -> Dict[str, Any]:
        """Get current hazard information."""
        if self.derived.sun_hazard_active:
            return {
                'is_hazardous': True,
                'hazard_type': 'focused_sunlight',
                'hazard_level': self.derived.sun_hazard_level,
                'description': 'The Fresnel lens is focusing sunlight into a dangerous beam!'
            }
        return {
            'is_hazardous': False,
            'hazard_level': 0.0,
            'description': 'No hazards detected.'
        }


# ============================================================================
# DEMO
# ============================================================================

def demo():
    """Show the refactored lantern room in action."""
    
    print("=== LANTERN ROOM REFACTORED DEMO ===\n")
    
    # Create lantern room (no weather provider for demo)
    lantern = LanternRoom()
    
    # Simulate daytime
    lantern.weather = WeatherConditions(is_day=True, temperature=25.0, humidity=0.6)
    lantern.derived = LanternStateComputer.compute(
        lantern.physics, lantern.controls, lantern.weather
    )
    
    print(lantern.get_status())
    print("\n" + "="*60 + "\n")
    
    # Clean the lens
    msg, events = lantern.clean_window_panes(0.8)
    print(f"[ACTION] {msg}")
    for event in events:
        print(f"  📢 {event.message}")
    
    # Wind clockwork
    msg, events = lantern.windup_clockwork(0.6)
    print(f"\n[ACTION] {msg}")
    for event in events:
        print(f"  📢 {event.message}")
    
    # Check hazard
    print("\n" + "="*60 + "\n")
    hazard = lantern.get_hazard_status()
    if hazard['is_hazardous']:
        print(f"⚠️  {hazard['description']}")
        print(f"Hazard Level: {hazard['hazard_level']:.0%}")
    
    # Place sheet to protect
    print()
    msg, events = lantern.place_sheet()
    print(f"[ACTION] {msg}")
    for event in events:
        print(f"  📢 {event.message}")
    
    # Check hazard again
    print()
    hazard = lantern.get_hazard_status()
    print(f"Hazardous: {hazard['is_hazardous']}")
    
    print("\n" + "="*60 + "\n")
    print(lantern.get_status())


if __name__ == "__main__":
    demo()