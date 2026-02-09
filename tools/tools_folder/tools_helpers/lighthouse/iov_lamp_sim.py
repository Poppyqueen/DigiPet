"""
IOV Lamp Simulation - Improved Version
========================================

Fixes:
1. Dynamic light descriptions based on actual light_intensity
2. Pressure consumption scales with control_valve position
3. Fuel consumption varies by mode (vaporizing vs bunsen)
4. Better physical realism
"""

from dataclasses import dataclass, replace
from typing import Callable, Dict, List, Tuple, Optional
from enum import Enum, auto


# ============================================================================
# CORE STATE - Only Physical Reality
# ============================================================================

@dataclass(frozen=True)
class PhysicalState:
    """Actual physical quantities that change over time."""
    air_pressure: float = 0.0  # PSI
    tube_temp: float = 0.0  # 0=cold, 1=red hot
    fuel_level: float = 0.0  # 0-1
    flame_lit: bool = False


@dataclass(frozen=True)
class Controls:
    """Direct player inputs - what they can touch."""
    air_valve_open: bool = False
    main_valve_open: bool = False
    control_valve: float = 0.0  # 0-1
    
    spirit_pan_present: bool = False
    spirit_pan_lit: bool = False
    
    mantle_installed: bool = False
    mantle_burned_in: bool = False


@dataclass(frozen=True)
class DerivedState:
    """Computed values - never stored, always calculated."""
    piping_up: bool = False
    vaporizing: bool = False
    bunsen_lit: bool = False
    light_intensity: float = 0.0
    
    # Output characteristics
    is_liquid_spray: bool = False
    spray_temp_level: Optional[str] = None
    spray_flow_level: Optional[str] = None
    hazard_multiplier: float = 0.0
    safety_valve_popped: bool = False


# ============================================================================
# EVENTS - What Changed
# ============================================================================

@dataclass(frozen=True)
class Event:
    """Something that happened this tick."""
    type: str
    message: str
    data: Dict = None
    
    def __post_init__(self):
        if self.data is None:
            object.__setattr__(self, 'data', {})


# ============================================================================
# CONSTANTS & THRESHOLDS
# ============================================================================

class Constants:
    """All magic numbers in one place."""
    
    # Pressure
    OPTIMAL_PRESSURE_MIN = 60
    OPTIMAL_PRESSURE_MAX = 70
    GRACE_RANGE = 15
    MIN_PRESSURE_FOR_PIPING = 40

    SAFETY_VALVE_THRESHOLD = OPTIMAL_PRESSURE_MAX + GRACE_RANGE + 5
    PRESSURE_DROP_SAFETY_VALVE = 10.0 # The pressure level after a pop
    
    # Temperature
    TEMP_THRESHOLD_VAPORIZING = 0.95
    TEMP_THRESHOLD_READY = 0.95
    TEMP_THRESHOLD_HOT = 0.7
    TEMP_THRESHOLD_WARM = 0.4
    
    # Valve
    MIN_VALVE_FOR_BUNSEN = 0.2  # 20% minimum for Bunsen to light
    MIN_VALVE_FOR_GOOD_LIGHT = 0.4  # 40% for optimal light output
    MIN_FUEL_FOR_OPERATION = 0.1
    
    # Physics rates (per tick)
    TEMP_RISE_PREBURNER = 0.35
    TEMP_RISE_BUNSEN = 0.1
    TEMP_FALL_RATE = 0.20
    
    # NEW: Improved pressure consumption model
    PRESSURE_LEAK_SERVICE = 2.0  # When air valve open
    PRESSURE_BASE_OPERATING = 0.15  # Base consumption when flowing
    PRESSURE_PER_VALVE_PERCENT = 0.0075  # Additional per 1% valve opening
    
    # NEW: Improved fuel consumption model
    FUEL_BASE_VAPORIZING = 0.0015  # Base rate when vaporizing
    FUEL_BASE_SPRAYING = 0.001  # Base rate when spraying liquid
    FUEL_PER_VALVE_PERCENT = 0.00005  # Additional per 1% valve opening
    FUEL_BUNSEN_MULTIPLIER = 1.25  # Extra consumption when bunsen lit


# ============================================================================
# RULES - Pure Functions
# ============================================================================

class Rules:
    """All game logic as pure, testable functions."""
    
    @staticmethod
    def is_piping_up(phys: PhysicalState, ctrl: Controls) -> bool:
        """Fuel is flowing to the burner."""
        return (
            ctrl.main_valve_open and
            phys.air_pressure >= Constants.MIN_PRESSURE_FOR_PIPING and
            phys.fuel_level >= Constants.MIN_FUEL_FOR_OPERATION
        )
    
    @staticmethod
    def is_vaporizing(phys: PhysicalState, ctrl: Controls) -> bool:
        """Kerosene is being vaporized."""
        return (
            Rules.is_piping_up(phys, ctrl) and
            phys.tube_temp >= Constants.TEMP_THRESHOLD_VAPORIZING and
            ctrl.control_valve > 0
        )
    
    @staticmethod
    def is_bunsen_lit(phys: PhysicalState, ctrl: Controls) -> bool:
        """Bunsen burner is producing heat."""
        return (
            Rules.is_vaporizing(phys, ctrl) and
            phys.flame_lit and
            ctrl.control_valve >= Constants.MIN_VALVE_FOR_BUNSEN
        )
    
    @staticmethod
    def is_pressure_optimal(phys: PhysicalState) -> bool:
        """Pressure in ideal operating range."""
        return (
            (Constants.OPTIMAL_PRESSURE_MIN-Constants.GRACE_RANGE) <= 
            phys.air_pressure <= 
            (Constants.OPTIMAL_PRESSURE_MAX+Constants.GRACE_RANGE)
        )
    
    @staticmethod
    def is_safety_valve_popped(phys: PhysicalState, ctrl: Controls) -> bool:
        return phys.air_pressure > Constants.SAFETY_VALVE_THRESHOLD
    

    @staticmethod
    def calculate_light_intensity(phys: PhysicalState, ctrl: Controls, derived: DerivedState) -> float:
        """
        Calculate light intensity based on multiple factors.
        Returns 0.0 to 1.0
        """
        if not (ctrl.mantle_installed and 
                ctrl.mantle_burned_in and 
                phys.flame_lit and
                derived.bunsen_lit):
            return 0.0
        
        # Base intensity from pressure
        pressure_factor = 1.0 if Rules.is_pressure_optimal(phys) else 0.7
        
        # NEW: Valve position affects light intensity
        # Below 40% valve, light is weak even if everything else is perfect
        valve_factor = min(1.0, ctrl.control_valve / Constants.MIN_VALVE_FOR_GOOD_LIGHT)
        
        return pressure_factor * valve_factor


# ============================================================================
# SPRAY HAZARD CALCULATION
# ============================================================================

@dataclass(frozen=True)
class SprayLevel:
    """Characteristics of a spray level."""
    min_val: float
    max_val: float
    description: str
    multiplier: int


class SprayTables:
    """Lookup tables for spray hazards."""
    
    TEMP_LEVELS = [
        SprayLevel(0.0, 0.2, "almost cold", 0),
        SprayLevel(0.2, 0.4, "lukewarm", 1),
        SprayLevel(0.4, 0.6, "warm", 2),
        SprayLevel(0.6, 0.7, "hot", 4),
        SprayLevel(0.7, 1.0, "scalding hot", 8),
    ]
    
    FLOW_LEVELS = [
        SprayLevel(0.0, 0.05, "slow drip", 1),
        SprayLevel(0.05, 0.2, "steady stream", 2),
        SprayLevel(0.2, 0.5, "spraying", 4),
        SprayLevel(0.5, 1.0, "powerful jet", 8),
    ]
    
    @staticmethod
    def find_level(value: float, levels: List[SprayLevel]) -> Optional[SprayLevel]:
        """Find which level a value falls into."""
        for level in levels:
            if level.min_val <= value <= level.max_val:
                return level
        return None
    
    @staticmethod
    def calculate_spray_hazard(temp: float, valve: float) -> Tuple[Optional[str], Optional[str], int, int, float]:
        """
        Returns: (temp_level_name, flow_level_name, temp_mult, flow_mult, hazard_mult)
        """
        temp_level = SprayTables.find_level(temp, SprayTables.TEMP_LEVELS)
        flow_level = SprayTables.find_level(valve, SprayTables.FLOW_LEVELS)
        
        if not temp_level or not flow_level:
            return None, None, 0, 0, 0.0
        
        temp_mult = temp_level.multiplier
        flow_mult = flow_level.multiplier
        hazard = float(temp_mult * flow_mult)
        
        return (
            temp_level.description,
            flow_level.description,
            temp_mult,
            flow_mult,
            hazard
        )


# ============================================================================
# DERIVED STATE COMPUTER
# ============================================================================

class StateComputer:
    """Computes all derived state from base state."""
    
    @staticmethod
    def compute(phys: PhysicalState, ctrl: Controls) -> DerivedState:
        """Pure function: base state -> derived state."""
        
        piping = Rules.is_piping_up(phys, ctrl)
        vaporizing = Rules.is_vaporizing(phys, ctrl)
        bunsen = Rules.is_bunsen_lit(phys, ctrl)
        
        # Determine if spraying liquid
        is_spray = piping and not vaporizing and ctrl.control_valve > 0
        
        # Calculate spray hazard if applicable
        if is_spray:
            temp_desc, flow_desc, temp_mult, flow_mult, hazard = \
                SprayTables.calculate_spray_hazard(phys.tube_temp, ctrl.control_valve)
        else:
            temp_desc = flow_desc = None
            temp_mult = flow_mult = 0
            hazard = 0.0

        safety_popped = Rules.is_safety_valve_popped(phys, ctrl)

        # Partial derived state for light calculation
        partial = DerivedState(
            piping_up=piping,
            vaporizing=vaporizing,
            bunsen_lit=bunsen,
            is_liquid_spray=is_spray,
            spray_temp_level=temp_desc,
            spray_flow_level=flow_desc,
            hazard_multiplier=hazard,
            safety_valve_popped=safety_popped 
        )
        
        light = Rules.calculate_light_intensity(phys, ctrl, partial)
        
        return replace(partial, light_intensity=light)


# ============================================================================
# PHYSICS ENGINE
# ============================================================================

class PhysicsEngine:
    """Applies physical laws to update physical state."""
    
    @staticmethod
    def resolve_stability(phys: PhysicalState, derived: DerivedState) -> PhysicalState:
        """
        Pure function: Enforces immediate physical constraints.
        If fuel stops, fire dies immediately.
        """
        if phys.flame_lit and not derived.vaporizing:
            return replace(phys, flame_lit=False)
                # IMMEDIATELY clamp the pressure down.
        if derived.safety_valve_popped:
            phys = replace(phys, air_pressure=Constants.PRESSURE_DROP_SAFETY_VALVE)
        return phys

    @staticmethod
    def calculate_pressure_leak(phys: PhysicalState, ctrl: Controls, derived: DerivedState) -> float:
        """
        NEW: Improved pressure consumption model.
        Pressure consumption scales with valve position.
        """
        if ctrl.air_valve_open:
            return Constants.PRESSURE_LEAK_SERVICE
        
        if not (derived.vaporizing or derived.is_liquid_spray):
            return 0.0
        
        # Base consumption + proportional to valve opening
        valve_percent = ctrl.control_valve * 100
        consumption = Constants.PRESSURE_BASE_OPERATING + (valve_percent * Constants.PRESSURE_PER_VALVE_PERCENT)
        
        return consumption
    
    @staticmethod
    def calculate_temp_delta(ctrl: Controls, derived: DerivedState) -> float:
        """How much does temperature change?"""
        if ctrl.spirit_pan_lit:
            return Constants.TEMP_RISE_PREBURNER
        elif derived.bunsen_lit:
            return Constants.TEMP_RISE_BUNSEN
        else:
            return -Constants.TEMP_FALL_RATE
    
    @staticmethod
    def calculate_fuel_consumption(ctrl: Controls, derived: DerivedState) -> float:
        """
        NEW: Improved fuel consumption model.
        - Base rate depends on mode (vaporizing vs spraying)
        - Scales with valve position
        - Extra consumption when bunsen is lit (more efficient burn)
        """
        if not (derived.vaporizing or derived.is_liquid_spray):
            return 0.0
        
        # Choose base rate
        if derived.vaporizing:
            base_rate = Constants.FUEL_BASE_VAPORIZING
        else:
            base_rate = Constants.FUEL_BASE_SPRAYING
        
        # Scale with valve position
        valve_percent = ctrl.control_valve * 100
        consumption = base_rate + (valve_percent * Constants.FUEL_PER_VALVE_PERCENT)
        
        # Bunsen burning consumes more fuel (hotter, more efficient)
        if derived.bunsen_lit:
            consumption *= Constants.FUEL_BUNSEN_MULTIPLIER
        
        return consumption
    
    @staticmethod
    def tick(phys: PhysicalState, ctrl: Controls, derived: DerivedState) -> PhysicalState:
        """Apply physics for one tick."""
        # 1. Apply stability first
        phys = PhysicsEngine.resolve_stability(phys, derived)
        
        # 2. Calculate standard rates with NEW models
        pressure_leak = PhysicsEngine.calculate_pressure_leak(phys, ctrl, derived)
        new_pressure = max(0.0, phys.air_pressure - pressure_leak)
        
        temp_delta = PhysicsEngine.calculate_temp_delta(ctrl, derived)
        new_temp = max(0.0, min(1.0, phys.tube_temp + temp_delta))
        
        fuel_consumed = PhysicsEngine.calculate_fuel_consumption(ctrl, derived)
        new_fuel = max(0.0, phys.fuel_level - fuel_consumed)
        
        # 3. Return new state
        return replace(phys,
            air_pressure=new_pressure,
            tube_temp=new_temp,
            fuel_level=new_fuel
        )


# ============================================================================
# EVENT DETECTOR
# ============================================================================

class EventDetector:
    """Detects state transitions and generates events."""
    
    @staticmethod
    def detect_transitions(
        old_phys: PhysicalState,
        old_ctrl: Controls,
        old_derived: DerivedState,
        new_phys: PhysicalState,
        new_ctrl: Controls,
        new_derived: DerivedState
    ) -> List[Event]:
        """Compare old and new state, emit events for changes."""
        events = []
        
        # Piping transitions
        if not old_derived.piping_up and new_derived.piping_up:
            events.append(Event(
                "piping_started",
                "You hear a gurgle of liquid, as you realize that pressurized liquid kerosene begins flowing through the service line to the IOV head."
            ))
        elif old_derived.piping_up and not new_derived.piping_up:
            reasons = []
            if not new_ctrl.main_valve_open:
                reasons.append("main valve closed")
            if new_phys.air_pressure < Constants.MIN_PRESSURE_FOR_PIPING:
                reasons.append(f"pressure too low ({new_phys.air_pressure:.1f} PSI)")
            if new_phys.fuel_level < Constants.MIN_FUEL_FOR_OPERATION:
                reasons.append("fuel depleted")
            events.append(Event(
                "piping_stopped",
                f"Fuel flow stopped: {', '.join(reasons)}."
            ))
        
        # Vaporizing transitions
        if not old_derived.vaporizing and new_derived.vaporizing:
            events.append(Event(
                "vaporizing_started",
                "Kerosene vapor begins flowing through the flash boiler of the IOV, its vaporizing tubes hiss and transmute the liquid into vapor."
            ))
        elif old_derived.vaporizing and not new_derived.vaporizing:
            events.append(Event(
                "vaporizing_stopped",
                "Vaporization has stopped."
            ))
            if old_phys.flame_lit:
                events.append(Event(
                    "flame_extinguished",
                    "The vapor flame extinguishes."
                ))
        
        # Bunsen transitions
        if not old_derived.bunsen_lit and new_derived.bunsen_lit:
            events.append(Event(
                "bunsen_ignited",
                "The Bunsen burner ignites with small, but piping-hot blue flames."
            ))
        elif old_derived.bunsen_lit and not new_derived.bunsen_lit:
            events.append(Event(
                "bunsen_extinguished",
                "The Bunsen flames extinguish."
            ))
        
        # Temperature transitions
        if (old_phys.tube_temp < Constants.TEMP_THRESHOLD_READY and 
            new_phys.tube_temp >= Constants.TEMP_THRESHOLD_READY):
            events.append(Event(
                "tubes_ready",
                "The vaporizing tubes glow dull red. They're ready."
            ))
        elif (old_phys.tube_temp >= Constants.TEMP_THRESHOLD_READY and 
              new_phys.tube_temp < Constants.TEMP_THRESHOLD_READY):
            events.append(Event(
                "tubes_cooling",
                "The vaporizing tubes are cooling. No longer hot enough."
            ))
        
        # Pressure warnings
        if old_phys.air_pressure > 0 and new_phys.air_pressure <= 0:
            events.append(Event(
                "pressure_depleted",
                "Air pressure has completely bled out!"
            ))
        elif (Rules.is_pressure_optimal(old_phys) and 
              not Rules.is_pressure_optimal(new_phys)):
            events.append(Event(
                "pressure_suboptimal",
                "Air pressure has dropped below optimal range."
            ))

        if (old_phys.air_pressure > Constants.SAFETY_VALVE_THRESHOLD and 
            new_phys.air_pressure < old_phys.air_pressure):
            events.append(Event(
                "safety_valve_popped",
                f"The safety valve pops open as it reaches {old_phys.air_pressure} PSI with a loud hiss! Suddenly, the pressure drops in a violent manner to {new_phys.air_pressure} PSI."
            ))
        
        # Fuel warnings
        if (old_phys.fuel_level >= Constants.MIN_FUEL_FOR_OPERATION and 
            new_phys.fuel_level < Constants.MIN_FUEL_FOR_OPERATION):
            events.append(Event(
                "fuel_critical",
                "Fuel is running critically low."
            ))
        
        # Liquid spray transitions
        if not old_derived.is_liquid_spray and new_derived.is_liquid_spray:
            msg = f"The IOV top is spraying {new_derived.spray_temp_level} liquid kerosene in a {new_derived.spray_flow_level}!"
            events.append(Event(
                "liquid_spray_started",
                msg,
                {
                    'hazard': new_derived.hazard_multiplier,
                    'temp_level': new_derived.spray_temp_level,
                    'flow_level': new_derived.spray_flow_level,
                }
            ))
            
            if new_ctrl.mantle_burned_in:
                events.append(Event(
                    "mantle_destroyed",
                    "The previous burned-in mantle is disturbed by the commotion and disintegrates instantly!"
                ))
        
        # Light transitions
        if old_derived.light_intensity < 0.5 and new_derived.light_intensity >= 0.5:
            events.append(Event(
                "light_ignited",
                "The mantle flashes brilliant light! For a second, everything you see is bleached white."
            ))
        elif old_derived.light_intensity > 0 and new_derived.light_intensity == 0:
            events.append(Event(
                "light_extinguished",
                "The light goes out, the room being quickly robbed of light."
            ))
        
        # Mantle burn-in
        if (new_ctrl.mantle_installed and 
            not old_ctrl.mantle_burned_in and 
            new_ctrl.mantle_burned_in):
            events.append(Event(
                "mantle_burned_in",
                "The mantle catches fire and burns down to a delicate ash skeleton instantly. 'A Welsbach mantle', you heard someone once call it."
            ))
        
        return events


# ============================================================================
# LAMP SIMULATION
# ============================================================================

class IOVLamp:
    """The complete lamp simulation."""
    
    def __init__(self):
        self.physics = PhysicalState()
        self.controls = Controls()
        self.derived = StateComputer.compute(self.physics, self.controls)
    
    def tick(self) -> List[Event]:
        """Advance simulation by one tick."""
        old_phys = self.physics
        old_ctrl = self.controls
        old_derived = self.derived
        
        self.physics = PhysicsEngine.tick(self.physics, self.controls, self.derived)
        self.derived = StateComputer.compute(self.physics, self.controls)
        
        events = EventDetector.detect_transitions(
            old_phys, old_ctrl, old_derived,
            self.physics, self.controls, self.derived
        )
        
        return events
    
    def _update_derived(self) -> List[Event]:
        """Recompute derived state and enforce immediate physical stability."""
        old_derived = self.derived
        old_ctrl = self.controls
        old_phys = self.physics
        
        self.derived = StateComputer.compute(self.physics, self.controls)
        self.physics = PhysicsEngine.resolve_stability(self.physics, self.derived)
        
        if self.physics != old_phys:
            self.derived = StateComputer.compute(self.physics, self.controls)
        
        events = EventDetector.detect_transitions(
            old_phys, old_ctrl, old_derived,
            self.physics, self.controls, self.derived
        )
        
        return events
    
    # ========================================================================
    # PLAYER ACTIONS
    # ========================================================================
    
    def open_air_valve(self) -> Tuple[str, List[Event]]:
        if self.controls.air_valve_open:
            return "The air service valve is already open.", []
        
        self.controls = replace(self.controls, air_valve_open=True)
        events = self._update_derived()
        return "You open the air service valve. Ready for pumping.", events
    
    def close_air_valve(self) -> Tuple[str, List[Event]]:
        if not self.controls.air_valve_open:
            return "The air service valve is already closed.", []
        
        self.controls = replace(self.controls, air_valve_open=False)
        events = self._update_derived()
        return "You close the air service valve.", events
    
    def pump_air(self, strokes: int = 10) -> Tuple[str, List[Event], bool]:
        if not self.controls.air_valve_open:
            return "Air service valve is closed. Open it first.", [], False
        
        pressure_gain = strokes * 0.5
        new_pressure = min(100.0, self.physics.air_pressure + pressure_gain)
        self.physics = replace(self.physics, air_pressure=new_pressure)
        
        events = self._update_derived()
        
        msg = f"You pump {strokes} strokes. Pressure: {self.physics.air_pressure:.1f} PSI"
        if Rules.is_pressure_optimal(self.physics):
            msg += " ✓ OPTIMAL"
        else:
            msg += f" (need {Constants.OPTIMAL_PRESSURE_MIN}-{Constants.OPTIMAL_PRESSURE_MAX})"
        
        return msg, events, True
    
    def open_main_valve(self) -> Tuple[str, List[Event]]:
        if self.controls.main_valve_open:
            return "The main valve is already open.", []
        
        self.controls = replace(self.controls, main_valve_open=True)
        events = self._update_derived()
        return "You open the main valve.", events
    
    def close_main_valve(self) -> Tuple[str, List[Event]]:
        if not self.controls.main_valve_open:
            return "The main valve is already closed.", []
        
        self.controls = replace(self.controls, main_valve_open=False)
        events = self._update_derived()
        return "You close the main valve.", events
    
    def place_spirit_pan(self) -> Tuple[str, List[Event]]:
        if self.controls.spirit_pan_present:
            return "The spirit pan is already in place.", [], False
        
        self.controls = replace(self.controls, spirit_pan_present=True)
        events = self._update_derived()
        return "You place the pre-burner pan beneath the vaporizing tubes.", events, True
    
    def remove_spirit_pan(self) -> Tuple[str, Optional[str], List[Event]]:
        if not self.controls.spirit_pan_present:
            return "There's no spirit pan to remove.", None, [], False
        
        was_lit = self.controls.spirit_pan_lit
        self.controls = replace(
            self.controls,
            spirit_pan_present=False,
            spirit_pan_lit=False
        )
        events = self._update_derived()
        
        if was_lit:
            return "You remove the spirit pan. Its fuel is spent.", "empty", events, True
        return "You remove the spirit pan.", "full", events, True
    
    def light_spirit_pan(self) -> Tuple[str, List[Event]]:
        if not self.controls.spirit_pan_present:
            return "There's no spirit pan to light.", []
        if self.controls.spirit_pan_lit:
            return "The spirit pan is already burning.", []
        
        self.controls = replace(self.controls, spirit_pan_lit=True)
        events = self._update_derived()
        return "You ignite the methylated spirits. Blue flames start heating the vaporizing tubes.", events
    
    def open_control_valve(self, amount: float = 0.5) -> Tuple[str, List[Event]]:
        new_position = min(1.0, self.controls.control_valve + amount)
        self.controls = replace(self.controls, control_valve=new_position)
        
        events = self._update_derived()
        
        msg = f"You open the control valve to {self.controls.control_valve * 100:.0f}%."
        
        if self.derived.piping_up:
            if self.physics.tube_temp >= Constants.TEMP_THRESHOLD_VAPORIZING:
                msg += " The vaporizing tubes are hot enough to vaporize the kerosene. Vaporized kerosene is now flowing into the vaporizing tubes, and out of the jet."
            else:
                msg += " The vaporizing tubes are not hot enough to vaporize the kerosene. Liquid kerosene is now flowing into the vaporizing tubes, and out of the jet."
        
        return msg, events
    
    def close_control_valve(self, amount: float = 0.5) -> Tuple[str, List[Event]]:
        new_position = max(0.0, self.controls.control_valve - amount)
        self.controls = replace(self.controls, control_valve=new_position)
        
        events = self._update_derived()
        msg = f"You close the control valve to {self.controls.control_valve * 100:.0f}%."
        
        return msg, events
    
    def install_mantle(self) -> Tuple[str, List[Event]]:
        if self.controls.mantle_installed:
            return "A mantle is already installed.", [], False
        
        self.controls = replace(
            self.controls,
            mantle_installed=True,
            mantle_burned_in=False
        )
        events = self._update_derived()
        return "You install the fabric mesh mantle. It needs to be burned in.", events, True
    
    def remove_mantle(self) -> Tuple[str, bool, List[Event]]:
        if not self.controls.mantle_installed:
            return "There's no mantle to remove.", False, [], False
        if self.physics.flame_lit:
            return "Can't remove the mantle while vapor is lit.", False, [], False
        
        was_burned = self.controls.mantle_burned_in
        self.controls = replace(
            self.controls,
            mantle_installed=False,
            mantle_burned_in=False
        )
        events = self._update_derived()
        
        if was_burned:
            return "The burned-in mantle crumbles to dust as you touch it. Leaving the bare mantle cage on top of the burner.", False, events
        return "You remove the fabric mantle.", True, events, True
    
    def ignite_vapor(self) -> Tuple[str, List[Event]]:
        if not self.derived.vaporizing:
            return "There's no vapor flowing to ignite.", []
        if self.physics.flame_lit:
            return "The vapor is already burning.", []
        
        self.physics = replace(self.physics, flame_lit=True)
        
        will_burn_mantle = (self.controls.mantle_installed and 
                           not self.controls.mantle_burned_in)
        if will_burn_mantle:
            self.controls = replace(self.controls, mantle_burned_in=True)
            
        events = self._update_derived()
        
        if self.controls.mantle_installed:
            msg = "You ignite the vapor. "
            if will_burn_mantle:
                msg += "The mantle catches fire..."
            else:
                msg += "The mantle glows..."
            return msg, events
        else:
            return "You ignite the vapor. Blue flames dance at the burner.", events
    
    def add_fuel(self, amount: float = 0.5) -> Tuple[str, List[Event], bool]:
        new_level = min(1.0, self.physics.fuel_level + amount)
        self.physics = replace(self.physics, fuel_level=new_level)
        
        events = self._update_derived()
        msg = f"You add kerosene. Fuel level: {self.physics.fuel_level * 100:.0f}%"
        
        return msg, events
    
    # ========================================================================
    # STATUS REPORTING - NEW IMPROVED VERSION
    # ========================================================================
    
    def get_output_status(self) -> str:
        """
        NEW: Dynamic output description based on actual light_intensity.
        No more false claims of bright white light when intensity is 0%!
        """
        if not self.derived.piping_up or self.controls.control_valve == 0:
            return "The IOV top is not flowing with anything."
        
        if self.derived.vaporizing:
            # Vaporizing mode - check actual light levels
            if self.physics.flame_lit:
                if self.controls.mantle_burned_in:
                    # Describe light based on actual intensity
                    if self.derived.light_intensity >= 0.9:
                        return "On top of the IOV lamp, a source of brilliant white light blazes, reaching every cranny of the room, leaving everything under its revealing shine."
                    elif self.derived.light_intensity >= 0.6:
                        return "On top of the IOV lamp, a warm glow emanates from the mantle, illuminating the room with steady light."
                    elif self.derived.light_intensity >= 0.3:
                        return "The mantle glows dimly, casting weak shadows. The valve isn't open enough for full brightness."
                    elif self.derived.light_intensity > 0:
                        return "The mantle barely glows, producing only a faint flicker. More fuel flow is needed."
                    else:
                        return "The mantle is present but not glowing. The flame is too weak."
                else:
                    return "A flame out of the top of the IOV lamp burns fiercely."
            else:
                return "The IOV top is flowing with vaporized kerosene."
        
        elif self.derived.is_liquid_spray:
            temp_desc = self.derived.spray_temp_level or "unknown temperature"
            flow_desc = self.derived.spray_flow_level or "unknown flow"
            return f"The IOV top is spraying {temp_desc} liquid kerosene in a {flow_desc}!"
        
        return "The IOV top is not flowing with anything."
    
    def get_temp_description(self) -> str:
        """Human-readable temperature."""
        t = self.physics.tube_temp
        if t >= 0.95: return "Red hot"
        elif t >= 0.7: return "Very hot"
        elif t >= 0.4: return "Warm"
        elif t > 0: return "Cool"
        return "Cold"
    
    def get_preburner_description(self) -> str:
        """Human-readable preburner state."""
        if self.controls.spirit_pan_lit: return "LIT"
        elif self.controls.spirit_pan_present: return "present, unlit"
        return "not placed"
    
    def get_mantle_description(self) -> str:
        """Human-readable mantle state."""
        if not self.controls.mantle_installed: return "Not installed"
        elif self.controls.mantle_burned_in: return "Burned-in (ready)"
        return "New (needs fire)"

    def get_service_room_status(self) -> str:
        """Get service room status."""
        # Build lamp status from components
        pressure_status = "OPTIMAL" if Rules.is_pressure_optimal(self.physics) else \
                         "TOO HIGH" if self.physics.air_pressure > Constants.OPTIMAL_PRESSURE_MAX else \
                         "TOO LOW"
        
        air_valve_status = "OPEN (Leaking...)" if self.controls.air_valve_open and self.physics.air_pressure > 0 else \
                          "OPEN (Silent)" if self.controls.air_valve_open else \
                          "closed"
        
        lines = [
            "=== PRESSURE SYSTEM ===",
            f"Air Pressure: {self.physics.air_pressure:.1f} PSI {pressure_status}",
            f"Air Service Valve: {air_valve_status}",
            f"Fuel: {self.physics.fuel_level * 100:.0f}%",
            f"Main Valve: {'OPEN' if self.controls.main_valve_open else 'closed'}",
            f"Piping Up: {'TRUE' if self.derived.piping_up else 'FALSE'}",
            ""
        ]
        return "\n".join(lines)

    def get_lamp_status(self) -> str:
        """Get burner-specific status."""
        lines = [
            "=== IOV LAMP TOP ===",
            f"  Tubes Temp: {self.get_temp_description()}",
            f"  Pre-burner: {self.get_preburner_description()}",
            f"  Control Valve: {self.controls.control_valve * 100:.0f}%",
            f"  Vaporizing: {'TRUE' if self.derived.vaporizing else 'FALSE'}",
            f"  Vapor Flame: {'LIT' if self.physics.flame_lit else 'out'}",
            f"  Bunsen: {'LIT' if self.derived.bunsen_lit else 'out'}",
            f"  Mantle: {self.get_mantle_description()}",
            f"  Light: {self.derived.light_intensity * 100:.0f}%",
            "",
            f"Output: {self.get_output_status()}",
            ""
        ]
        return "\n".join(lines)
    
    def get_status(self) -> str:
        """Complete status report."""
        return self.get_service_room_status() + "\n" + self.get_lamp_status()


# ============================================================================
# DEMO / TESTING
# ============================================================================

def demo():
    """Demo showing the improvements."""
    lamp = IOVLamp()
    
    print("=== IOV LAMP - IMPROVED VERSION ===")
    print("Fixes: Dynamic light descriptions + Better pressure/fuel consumption\n")
    
    def do(action_name: str, result):
        print(f"[ACTION] {action_name}")
        if isinstance(result, tuple):
            msg = result[0]
            events = result[-1] if isinstance(result[-1], list) else []
            print(f"  → {msg}")
            for event in events:
                print(f"  📢 {event.message}")
        else:
            print(f"  → {result}")
        print()
    
    # Startup with PLENTY of pressure
    do("Add fuel", lamp.add_fuel(1.0))
    do("Open air valve", lamp.open_air_valve())
    do("Pump air to 70 PSI", lamp.pump_air(140))
    do("Close air valve", lamp.close_air_valve())
    do("Place spirit pan", lamp.place_spirit_pan())
    do("Light spirit pan", lamp.light_spirit_pan())
    
    # Heat up
    print("[SIMULATION] Heating up...")
    for i in range(5):
        events = lamp.tick()
        for event in events:
            print(f"  📢 {event.message}")
    print()
    
    do("Open main valve", lamp.open_main_valve())
    do("Install mantle", lamp.install_mantle())
    
    # TEST 1: Open valve only 10% (too little for good light)
    print("=" * 60)
    print("TEST 1: Opening valve to only 10% (below minimum for Bunsen)")
    print("=" * 60)
    do("Open control valve 10%", lamp.open_control_valve(0.1))
    
    print(f"Current pressure: {lamp.physics.air_pressure:.1f} PSI")
    print(f"Current fuel: {lamp.physics.fuel_level * 100:.0f}%")
    print()
    
    print("[SIMULATION] A few ticks...")
    for i in range(3):
        events = lamp.tick()
        for event in events:
            print(f"  📢 {event.message}")
        print(f"  Pressure: {lamp.physics.air_pressure:.1f} PSI, Fuel: {lamp.physics.fuel_level * 100:.1f}%")
    print()
    
    do("Ignite vapor", lamp.ignite_vapor())
    
    print("[SIMULATION] A few more ticks with flame...")
    for i in range(5):
        events = lamp.tick()
        for event in events:
            print(f"  📢 {event.message}")
        print(f"  Pressure: {lamp.physics.air_pressure:.1f} PSI, Fuel: {lamp.physics.fuel_level * 100:.1f}%, Light: {lamp.derived.light_intensity * 100:.1f}%")
    print()
    
    print(lamp.get_status())
    
    print("\n" + "=" * 60)
    print("NOTICE: Light is 0% because valve < 20% (can't sustain Bunsen)")
    print("Output description correctly says 'mantle present but not glowing'")
    print("Pressure draining slowly (10% valve = low consumption)")
    print("=" * 60)
    
    # TEST 2: Increase to 50% for proper operation
    print("\n" + "=" * 60)
    print("TEST 2: Increasing valve to 50% (proper operation)")
    print("=" * 60)
    do("Open control valve to 50%", lamp.open_control_valve(0.4))
    
    print("[SIMULATION] System stabilizing...")
    for i in range(5):
        events = lamp.tick()
        for event in events:
            print(f"  📢 {event.message}")
        print(f"  Pressure: {lamp.physics.air_pressure:.1f} PSI, Fuel: {lamp.physics.fuel_level * 100:.1f}%, Light: {lamp.derived.light_intensity * 100:.1f}%")
    print()
    
    print(lamp.get_status())
    
    print("\n" + "=" * 60)
    print("NOTICE: Now light is at full brightness!")
    print("Pressure draining FASTER (50% valve = higher consumption)")
    print("Fuel consumption INCREASED (Bunsen lit = multiplier active)")
    print("Description: 'brilliant white light blazes'")
    print("=" * 60)


if __name__ == "__main__":
    demo()