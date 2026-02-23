"""
IOV Lamp Simulation - Refactored
==================================

Refactor: Unified jet_psi as the canonical output force value.
Refactor: Explicit pipe line loss between tank and lamp head.

PRESSURE CHAIN (physically accurate):
  air_pressure (tank, service room below)
      × LINE_LOSS_FACTOR (~0.80, fixed pipe run loss between floors)
  = inlet_psi (pressure arriving at the lamp head)
      × fuel_factor (fuel column resistance, varies with fuel level)
      × control_valve (0–1)
  = jet_psi (output at the nozzle)

  upstream_gauge reads inlet_psi directly — that is what the physical
  gauge on the lamp head measures: pressure arriving before the control valve.
  It no longer uses (1 - control_valve) as a backpressure approximation.

Previously, valve position (0-1) was used as a proxy for flow/force in
multiple independent calculations, and line losses were approximated
implicitly via fuel_factor (which is not what fuel level represents).

Changes:
- Rules.calculate_inlet_psi()      — NEW: explicit pipe run loss step
- Rules.calculate_jet_psi()        — now routes through inlet_psi
- Rules.calculate_upstream_gauge() — now reads inlet_psi directly (no control_valve term)
- Constants.LINE_LOSS_FACTOR       — NEW: replaces the old implicit LINE_RESISTANCE
- is_bunsen_lit()                  — thresholds on jet_psi, not valve %
- calculate_light_intensity()      — scales on jet_psi, not valve %
- SprayTables.calculate_spray_hazard() — flow param is jet_psi, not valve 0-1
- Liquid spray mantle destruction  — requires jet_psi above threshold
- calculate_fuel_consumption()     — scales on jet_psi, not valve * 100
- calculate_pressure_leak()        — scales on jet_psi, not valve * 100
- DerivedState.control_gauge_pressure — renamed upstream_gauge_psi for clarity
"""

from dataclasses import dataclass, replace
from typing import Callable, Dict, List, Tuple, Optional
from enum import Enum, auto

import random

from .models import Event


# ============================================================================
# CORE STATE - Only Physical Reality
# ============================================================================

@dataclass(frozen=True)
class PhysicalState:
    """Actual physical quantities that change over time."""
    air_pressure: float = 0.0  # PSI
    tube_temp: float = 0.0     # 0=cold, 1=red hot
    fuel_level: float = 0.0   # 0-1
    flame_lit: bool = False
    mantle_burned_in: bool = False
    jet_soot_level: float = 0.0  # 0-1, accumulates while vaporizing


@dataclass(frozen=True)
class Controls:
    """Direct player inputs - what they can touch."""
    air_valve_open: bool = False
    main_valve_open: bool = False
    control_valve: float = 0.0  # 0-1

    spirit_pan_present: bool = False
    spirit_pan_lit: bool = False

    mantle_installed: bool = False


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

    # Renamed from control_gauge_pressure for clarity
    upstream_gauge_psi: float = 0.0

    is_air_blowing: bool = False
    air_flow_level: Optional[str] = None
    air_destroys_mantle: bool = False


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
    PRESSURE_DROP_SAFETY_VALVE_MIN = 2.0
    PRESSURE_DROP_SAFETY_VALVE_MAX = 17.0

    # Temperature
    TEMP_THRESHOLD_VAPORIZING = 0.95
    TEMP_THRESHOLD_READY = 0.95
    TEMP_THRESHOLD_HOT = 0.7
    TEMP_THRESHOLD_WARM = 0.4

    # Pipe run loss — tank (service room) → lamp head (above)
    # ~20% pressure lost over the vertical pipe run between floors.
    # Fixed constant: independent of valve, fuel, or flow state.
    LINE_LOSS_FACTOR = 0.80  # inlet_psi = air_pressure × LINE_LOSS_FACTOR

    # Fuel column resistance — applied after line losses, before the control valve.
    # More fuel = denser column = slightly higher delivery pressure at the nozzle.
    FUEL_LINE_RESISTANCE_EMPTY = 0.75   # fuel_factor when tank is empty
    FUEL_LINE_RESISTANCE_FULL  = 0.85   # fuel_factor when tank is full
    # fuel_factor = FUEL_LINE_RESISTANCE_EMPTY + fuel_level * (FULL - EMPTY)
    # Range 0.75–0.85

    # -----------------------------------------------------------------------
    # JET PSI THRESHOLDS
    # These replace the old valve-position proxies (MIN_VALVE_FOR_BUNSEN, etc.)
    # All downstream logic now gates on jet_psi, not control_valve %.
    # -----------------------------------------------------------------------

    # Minimum jet output pressure for the Bunsen to sustain ignition
    MIN_JET_PSI_FOR_BUNSEN = 10.0

    # Jet PSI at which light reaches full brightness (scales linearly below)
    MIN_JET_PSI_FOR_GOOD_LIGHT = 25.0

    # Jet PSI above which liquid spray will destroy the mantle
    MIN_JET_PSI_FOR_MANTLE_DESTRUCTION = 15.0

    # Reference PSI for normalising spray flow descriptions (maps to "powerful jet")
    MAX_SPRAY_PSI = 60.0

    MIN_FUEL_FOR_OPERATION = 0.1

    # Physics rates (per tick)
    TEMP_RISE_PREBURNER = 0.35
    TEMP_RISE_BUNSEN = 0.1
    TEMP_FALL_RATE = 0.20

    # Pressure leak model
    PRESSURE_LEAK_SERVICE = 2.0        # When air valve open (additive)
    PRESSURE_BASE_OPEN = 0.15          # Base open-system consumption
    PRESSURE_PER_JET_PSI = 0.0075     # Replaces PRESSURE_PER_VALVE_PERCENT

    # State modifiers on pressure leak
    PRESSURE_MOD_AIR_BLOW    = 2.0
    PRESSURE_MOD_VAPORIZING  = 1.0
    PRESSURE_MOD_LIQUID_SPRAY = 0.8

    MIN_PRESSURE_FOR_AIR_BLOW = 1.0

    # Fuel consumption model
    FUEL_BASE_VAPORIZING = 0.0015
    FUEL_BASE_SPRAYING   = 0.001
    FUEL_PER_JET_PSI     = 0.00005    # Replaces FUEL_PER_VALVE_PERCENT
    FUEL_BUNSEN_MULTIPLIER = 1.25

    # Jet soot model
    # Accumulates slowly while vaporizing; Bunsen (complete combustion) reduces rate.
    SOOT_RATE_VAPORIZING = 0.0001      # Base accumulation per tick while vaporizing
    SOOT_REDUCTION_BUNSEN = 0.00004   # Subtracted when Bunsen is lit (cleaner burn)


# ============================================================================
# RULES - Pure Functions
# ============================================================================

class Rules:
    """All game logic as pure, testable functions."""

    # ------------------------------------------------------------------
    # FUEL COLUMN RESISTANCE — shared helper
    # ------------------------------------------------------------------

    @staticmethod
    def _fuel_factor(phys: 'PhysicalState') -> float:
        """
        Resistance of the fuel column (applied after line losses).
        Range: 0.75 (empty) → 0.85 (full).
        More fuel = denser column = slightly higher nozzle pressure.
        """
        return (
            Constants.FUEL_LINE_RESISTANCE_EMPTY +
            phys.fuel_level * (Constants.FUEL_LINE_RESISTANCE_FULL -
                               Constants.FUEL_LINE_RESISTANCE_EMPTY)
        )

    # ------------------------------------------------------------------
    # CANONICAL PRESSURE CHAIN  ← single source of truth
    #
    #   air_pressure  (tank, service room)
    #       × LINE_LOSS_FACTOR
    #   = inlet_psi   (at lamp head, before control valve)
    #       × fuel_factor × control_valve
    #   = jet_psi     (at nozzle)
    #
    # upstream_gauge reads inlet_psi — that is what the physical gauge
    # on the lamp head measures.
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_inlet_psi(phys: 'PhysicalState') -> float:
        """
        Pressure arriving at the lamp head after the pipe run from the
        service room below. Fixed ~20% loss regardless of flow state.
        """
        return phys.air_pressure * Constants.LINE_LOSS_FACTOR

    @staticmethod
    def calculate_upstream_gauge(phys: 'PhysicalState', ctrl: 'Controls') -> float:
        """
        What the inlet gauge on the lamp head reads.
        This is inlet_psi — pressure before the control valve.
        Does NOT vary with control_valve position; the gauge reads
        the line, not the downstream backpressure.
        """
        if not ctrl.main_valve_open or phys.air_pressure <= 0:
            return 0.0
        return Rules.calculate_inlet_psi(phys) * Rules._fuel_factor(phys)

    @staticmethod
    def calculate_jet_psi(phys: 'PhysicalState', ctrl: 'Controls') -> float:
        """
        Actual output pressure at the jet nozzle.

        Canonical measure of "how hard is stuff coming out."
        All downstream calculations consume this value.

        Chain: tank → [line loss] → inlet → [fuel factor] → [control valve] → [soot restriction] → jet
        """
        if not ctrl.main_valve_open or phys.air_pressure <= 0:
            return 0.0
        raw = Rules.calculate_inlet_psi(phys) * Rules._fuel_factor(phys) * ctrl.control_valve
        return raw * (1.0 - phys.jet_soot_level)

    # ------------------------------------------------------------------
    # RUNTIME CEILINGS — normalize jet_psi before table lookups
    #
    # Tables use 0–1 normalized values so their thresholds remain stable
    # regardless of changes to LINE_LOSS_FACTOR, fuel resistance, or
    # safety valve threshold. The ceiling recalculates itself from constants.
    # ------------------------------------------------------------------

    @staticmethod
    def max_jet_psi() -> float:
        """
        Theoretical maximum jet output under best fuel conditions.
        Used to normalize jet_psi → 0-1 before spray flow table lookup.

        Assumes: safety threshold pressure, full tank (max fuel_factor),
        valve fully open, no soot.
        """
        return (
            Constants.SAFETY_VALVE_THRESHOLD *
            Constants.LINE_LOSS_FACTOR *
            Constants.FUEL_LINE_RESISTANCE_FULL *
            1.0  # control_valve fully open
        )

    @staticmethod
    def max_air_jet_psi() -> float:
        """
        Theoretical maximum jet output under air-blowing conditions.
        Used to normalize jet_psi → 0-1 before air flow table lookup.

        Air blowing only occurs when fuel_level < MIN_FUEL_FOR_OPERATION,
        so fuel_factor is at its minimum (FUEL_LINE_RESISTANCE_EMPTY).
        Soot doesn't accumulate without fuel so it's excluded here.
        """
        return (
            Constants.SAFETY_VALVE_THRESHOLD *
            Constants.LINE_LOSS_FACTOR *
            Constants.FUEL_LINE_RESISTANCE_EMPTY *
            1.0  # control_valve fully open
        )

    # ------------------------------------------------------------------
    # FLOW / STATE PREDICATES
    # ------------------------------------------------------------------

    @staticmethod
    def is_system_open(phys: 'PhysicalState', ctrl: 'Controls') -> bool:
        """The path from tank to jet is open — something is flowing."""
        return (
            ctrl.main_valve_open and
            ctrl.control_valve > 0 and
            phys.air_pressure > 0
        )

    @staticmethod
    def is_piping_up(phys: 'PhysicalState', ctrl: 'Controls') -> bool:
        """Fuel is flowing to the burner."""
        return (
            ctrl.main_valve_open and
            phys.air_pressure >= Constants.MIN_PRESSURE_FOR_PIPING and
            phys.fuel_level >= Constants.MIN_FUEL_FOR_OPERATION
        )

    @staticmethod
    def is_vaporizing(phys: 'PhysicalState', ctrl: 'Controls') -> bool:
        """Kerosene is being vaporized."""
        return (
            Rules.is_piping_up(phys, ctrl) and
            phys.tube_temp >= Constants.TEMP_THRESHOLD_VAPORIZING and
            ctrl.control_valve > 0
        )

    @staticmethod
    def is_bunsen_lit(phys: 'PhysicalState', ctrl: 'Controls') -> bool:
        """
        Bunsen burner is sustaining ignition.

        Previously gated on ctrl.control_valve >= MIN_VALVE_FOR_BUNSEN (20%).
        Now gates on jet_psi >= MIN_JET_PSI_FOR_BUNSEN so that a high valve
        position at low system pressure correctly fails to sustain a Bunsen.
        """
        if not (Rules.is_vaporizing(phys, ctrl) and phys.flame_lit):
            return False
        jet_psi = Rules.calculate_jet_psi(phys, ctrl)
        return jet_psi >= Constants.MIN_JET_PSI_FOR_BUNSEN

    @staticmethod
    def is_pressure_optimal(phys: 'PhysicalState') -> bool:
        """Pressure in ideal operating range."""
        return (
            (Constants.OPTIMAL_PRESSURE_MIN - Constants.GRACE_RANGE) <=
            phys.air_pressure <=
            (Constants.OPTIMAL_PRESSURE_MAX + Constants.GRACE_RANGE)
        )

    @staticmethod
    def is_safety_valve_popped(phys: 'PhysicalState', ctrl: 'Controls') -> bool:
        return phys.air_pressure > Constants.SAFETY_VALVE_THRESHOLD

    @staticmethod
    def calculate_light_intensity(
        phys: 'PhysicalState',
        ctrl: 'Controls',
        derived: 'DerivedState'
    ) -> float:
        """
        Calculate light intensity (0.0–1.0).

        Previously used valve position as a proxy for fuel flow, making
        pressure irrelevant to brightness. Now uses jet_psi so a low-pressure
        system produces dim light even with the valve wide open.
        """
        if not (ctrl.mantle_installed and
                phys.mantle_burned_in and
                phys.flame_lit and
                derived.bunsen_lit):
            return 0.0

        pressure_factor = 1.0 if Rules.is_pressure_optimal(phys) else 0.7

        # Scale linearly from 0 → MIN_JET_PSI_FOR_GOOD_LIGHT, cap at 1.0
        jet_psi = Rules.calculate_jet_psi(phys, ctrl)
        valve_factor = min(1.0, jet_psi / Constants.MIN_JET_PSI_FOR_GOOD_LIGHT)

        return pressure_factor * valve_factor

    @staticmethod
    def is_air_blowing(phys: 'PhysicalState', ctrl: 'Controls') -> bool:
        """Air is flowing through the top with no fuel — pure air jet."""
        return (
            ctrl.main_valve_open and
            ctrl.control_valve > 0 and
            phys.air_pressure >= Constants.MIN_PRESSURE_FOR_AIR_BLOW and
            phys.fuel_level < Constants.MIN_FUEL_FOR_OPERATION
        )


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

    # Flow levels keyed on normalized jet output (0–1).
    # Normalized against Rules.max_jet_psi() at lookup time so these
    # thresholds remain correct regardless of changes to physics constants.
    FLOW_LEVELS = [
        SprayLevel(0.0,  0.15, "slow drip",     1),
        SprayLevel(0.15, 0.40, "steady stream",  2),
        SprayLevel(0.40, 0.70, "strong spray",   4),
        SprayLevel(0.70, 1.0,  "powerful jet",   8),
    ]

    @staticmethod
    def find_level(value: float, levels: List[SprayLevel]) -> Optional[SprayLevel]:
        for level in levels:
            if level.min_val <= value <= level.max_val:
                return level
        return None

    @staticmethod
    def calculate_spray_hazard(
        temp: float,
        jet_psi: float
    ) -> Tuple[Optional[str], Optional[str], int, int, float]:
        """
        Returns: (temp_level_name, flow_level_name, temp_mult, flow_mult, hazard_mult)

        jet_psi is normalized against the runtime ceiling before lookup so
        the flow table thresholds stay stable across physics constant changes.
        A 50% valve at 80 PSI is far more dangerous than 50% valve at 10 PSI.
        """
        normalized_flow = min(1.0, jet_psi / Rules.max_jet_psi())

        temp_level = SprayTables.find_level(temp, SprayTables.TEMP_LEVELS)
        flow_level = SprayTables.find_level(normalized_flow, SprayTables.FLOW_LEVELS)

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
# LIGHT LEVEL CALCULATION
# ============================================================================

@dataclass(frozen=True)
class LightLevel:
    min_val: float
    max_val: float
    description: str


class LightTables:
    LEVELS = [
        LightLevel(0.0,  0.0,  "You can't notice any light coming from the IOV lamp."),
        LightLevel(0.01, 0.4,  "You can barely make out a dim light coming from the IOV lamp."),
        LightLevel(0.41, 0.9,  "A bright light is emanating from where the IOV lamp is."),
        LightLevel(0.91, 1.0,  "A brilliant light is shining from the IOV lamp."),
    ]

    @staticmethod
    def find_level(value: float, levels: List[LightLevel]) -> Optional[LightLevel]:
        for level in levels:
            if level.min_val <= value <= level.max_val:
                return level
        return None


@dataclass(frozen=True)
class AirFlowLevel:
    min_val: float
    max_val: float
    description: str
    destroys_mantle: bool


class AirFlowTables:
    # Levels keyed on normalized air jet output (0–1).
    # Normalized against Rules.max_air_jet_psi() at lookup time.
    # Air blowing uses FUEL_LINE_RESISTANCE_EMPTY as its fuel_factor
    # since it only occurs when the tank is nearly empty — so its ceiling
    # is lower than the spray ceiling and gets its own normalization.
    LEVELS = [
        AirFlowLevel(0.01, 0.25, "A faint breath of air escapes from the jet.",          False),
        AirFlowLevel(0.25, 0.55, "A steady stream of air hisses from the jet.",           False),
        AirFlowLevel(0.55, 0.80, "A strong jet of air blasts from the top of the IOV.",   True),
        AirFlowLevel(0.80, 1.0,  "A powerful pressurized air jet roars from the IOV top.", True),
    ]

    @staticmethod
    def find_level(jet_psi: float) -> Optional[AirFlowLevel]:
        """Normalizes jet_psi against the air-blowing ceiling before lookup."""
        normalized = min(1.0, jet_psi / Rules.max_air_jet_psi())
        for level in AirFlowTables.LEVELS:
            if level.min_val <= normalized <= level.max_val:
                return level
        return None


# ============================================================================
# DERIVED STATE COMPUTER
# ============================================================================

class StateComputer:
    """Computes all derived state from base state."""

    @staticmethod
    def compute(phys: PhysicalState, ctrl: Controls) -> DerivedState:
        """Pure function: base state -> derived state."""

        piping    = Rules.is_piping_up(phys, ctrl)
        vaporizing = Rules.is_vaporizing(phys, ctrl)
        bunsen    = Rules.is_bunsen_lit(phys, ctrl)

        # Compute jet_psi once — consumed by everything below
        jet_psi = Rules.calculate_jet_psi(phys, ctrl)

        # Spraying liquid if piping but not hot enough to vaporize
        is_spray = piping and not vaporizing and ctrl.control_valve > 0

        # Spray hazard — now passes jet_psi instead of ctrl.control_valve
        if is_spray:
            temp_desc, flow_desc, temp_mult, flow_mult, hazard = \
                SprayTables.calculate_spray_hazard(phys.tube_temp, jet_psi)
        else:
            temp_desc = flow_desc = None
            temp_mult = flow_mult = 0
            hazard = 0.0

        safety_popped   = Rules.is_safety_valve_popped(phys, ctrl)
        upstream_gauge  = Rules.calculate_upstream_gauge(phys, ctrl)

        # Air blowing state — also uses jet_psi for the flow table lookup
        air_blowing   = Rules.is_air_blowing(phys, ctrl)
        air_flow_desc = None
        air_destroys  = False
        if air_blowing:
            air_level = AirFlowTables.find_level(jet_psi)
            if air_level:
                air_flow_desc = air_level.description
                air_destroys  = air_level.destroys_mantle

        partial = DerivedState(
            piping_up=piping,
            vaporizing=vaporizing,
            bunsen_lit=bunsen,
            is_liquid_spray=is_spray,
            spray_temp_level=temp_desc,
            spray_flow_level=flow_desc,
            hazard_multiplier=hazard,
            safety_valve_popped=safety_popped,
            upstream_gauge_psi=upstream_gauge,
            is_air_blowing=air_blowing,
            air_flow_level=air_flow_desc,
            air_destroys_mantle=air_destroys,
        )

        light = Rules.calculate_light_intensity(phys, ctrl, partial)
        return replace(partial, light_intensity=light)


# ============================================================================
# PHYSICS ENGINE
# ============================================================================

class PhysicsEngine:
    """Applies physical laws to update physical state."""

    @staticmethod
    def resolve_stability(
        phys: PhysicalState,
        ctrl: Controls,
        derived: DerivedState
    ) -> Tuple[PhysicalState, Controls]:
        """Enforces immediate physical constraints."""

        # Flame dies if not vaporizing
        if phys.flame_lit and not derived.vaporizing:
            phys = replace(phys, flame_lit=False)

        # Safety valve pop
        if derived.safety_valve_popped:
            randy_pressure = round(
                random.uniform(
                    Constants.PRESSURE_DROP_SAFETY_VALVE_MIN,
                    Constants.PRESSURE_DROP_SAFETY_VALVE_MAX
                ), 3
            )
            print(f"Safety valve popped! Pressure dropped to {randy_pressure}")
            phys = replace(phys, air_pressure=randy_pressure)

        # Mantle destroyed by liquid spray above force threshold, or strong air jet
        jet_psi = Rules.calculate_jet_psi(phys, ctrl)
        mantle_destruction = (
            phys.mantle_burned_in and (
                # Air jet: table already gates on PSI via AirFlowTables
                derived.air_destroys_mantle or
                # Liquid spray: now requires minimum jet force (not just any spray)
                (derived.is_liquid_spray and
                 jet_psi >= Constants.MIN_JET_PSI_FOR_MANTLE_DESTRUCTION)
            )
        )
        if mantle_destruction:
            ctrl = replace(ctrl, mantle_installed=False)
            phys = replace(phys, mantle_burned_in=False)


        # Mantle burns in if flame is lit and vaporizing
        if (ctrl.mantle_installed and
                not phys.mantle_burned_in and
                phys.flame_lit and
                Rules.is_vaporizing(phys, ctrl)):
            phys = replace(phys, mantle_burned_in=True)

        return phys, ctrl

    @staticmethod
    def calculate_pressure_leak(
        phys: PhysicalState,
        ctrl: Controls,
        derived: DerivedState
    ) -> float:
        """
        Pressure consumed per tick.

        Previously scaled with ctrl.control_valve * 100 (valve as flow proxy).
        Now scales with jet_psi so actual system pressure drives consumption.
        High pressure + open valve = fast drain. Low pressure + open valve = slow drain.
        """
        consumption = 0.0

        # Service valve leak — additive, independent of everything else
        if ctrl.air_valve_open:
            consumption += Constants.PRESSURE_LEAK_SERVICE

        if not Rules.is_system_open(phys, ctrl):
            return consumption

        # Base + jet_psi scaling (replaces base + valve_percent * per_valve)
        jet_psi = Rules.calculate_jet_psi(phys, ctrl)
        base = Constants.PRESSURE_BASE_OPEN + (jet_psi * Constants.PRESSURE_PER_JET_PSI)

        # State modifier
        if derived.is_air_blowing:
            base *= Constants.PRESSURE_MOD_AIR_BLOW
        elif derived.vaporizing:
            base *= Constants.PRESSURE_MOD_VAPORIZING
        elif derived.is_liquid_spray:
            base *= Constants.PRESSURE_MOD_LIQUID_SPRAY

        consumption += base
        return consumption

    @staticmethod
    def calculate_temp_delta(ctrl: Controls, derived: DerivedState) -> float:
        """How much does temperature change per tick?"""
        if ctrl.spirit_pan_lit:
            return Constants.TEMP_RISE_PREBURNER
        elif derived.bunsen_lit:
            return Constants.TEMP_RISE_BUNSEN
        else:
            return -Constants.TEMP_FALL_RATE

    @staticmethod
    def calculate_soot_accumulation(derived: DerivedState) -> float:
        """
        Soot deposited on the jet orifice per tick.

        Only accumulates while vaporizing. Bunsen combustion is more complete
        (hotter, more efficient) so it slightly reduces the accumulation rate.
        Net rate is always >= 0 — soot never self-cleans.
        """
        if not derived.vaporizing:
            return 0.0
        rate = Constants.SOOT_RATE_VAPORIZING
        if derived.bunsen_lit:
            rate -= Constants.SOOT_REDUCTION_BUNSEN
        return max(0.0, rate)

    @staticmethod
    def calculate_fuel_consumption(
        phys: PhysicalState,
        ctrl: Controls,
        derived: DerivedState
    ) -> float:
        """
        Fuel consumed per tick.

        Previously scaled with ctrl.control_valve * 100 (valve as flow proxy).
        Now scales with jet_psi so actual delivery pressure drives burn rate.
        High pressure + open valve burns faster than same valve at low pressure.

        Note: phys is now a required argument so jet_psi can be computed here.
        """
        if not (derived.vaporizing or derived.is_liquid_spray):
            return 0.0

        base_rate = (
            Constants.FUEL_BASE_VAPORIZING if derived.vaporizing
            else Constants.FUEL_BASE_SPRAYING
        )

        jet_psi = Rules.calculate_jet_psi(phys, ctrl)
        consumption = base_rate + (jet_psi * Constants.FUEL_PER_JET_PSI)

        if derived.bunsen_lit:
            consumption *= Constants.FUEL_BUNSEN_MULTIPLIER

        return consumption

    @staticmethod
    def tick(
        phys: PhysicalState,
        ctrl: Controls,
        derived: DerivedState
    ) -> Tuple[PhysicalState, Controls]:
        """Apply physics for one tick."""

        # 1. Stability constraints first
        phys, ctrl = PhysicsEngine.resolve_stability(phys, ctrl, derived)

        # 2. Rates — all now indirectly driven by jet_psi
        pressure_leak = PhysicsEngine.calculate_pressure_leak(phys, ctrl, derived)
        new_pressure  = max(0.0, phys.air_pressure - pressure_leak)

        temp_delta = PhysicsEngine.calculate_temp_delta(ctrl, derived)
        new_temp   = max(0.0, min(1.0, phys.tube_temp + temp_delta))

        # calculate_fuel_consumption now receives phys for jet_psi calculation
        fuel_consumed = PhysicsEngine.calculate_fuel_consumption(phys, ctrl, derived)
        new_fuel      = max(0.0, phys.fuel_level - fuel_consumed)

        soot_delta = PhysicsEngine.calculate_soot_accumulation(derived)
        new_soot   = min(1.0, phys.jet_soot_level + soot_delta)

        return replace(phys,
            air_pressure=new_pressure,
            tube_temp=new_temp,
            fuel_level=new_fuel,
            jet_soot_level=new_soot
        ), ctrl


# ============================================================================
# EVENT DETECTOR
# ============================================================================

class EventDetector:
    """Detects state transitions and generates events."""

    @staticmethod
    def detect_transitions(
        old_phys: PhysicalState,
        old_derived: DerivedState,
        new_phys: PhysicalState,
        new_ctrl: Controls,
        new_derived: DerivedState
    ) -> List[Event]:
        """Compare old and new state, emit events for changes."""
        events = []

        def check_mantle_destroyed():
            if old_phys.mantle_burned_in and not new_phys.mantle_burned_in:
                events.append(Event(
                    event_affordances_keys=["lamp"],
                    type="mantle_destroyed",
                    message="The previous burned-in mantle is disturbed by the commotion and disintegrates instantly!"
                ))

        # Piping transitions
        if not old_derived.piping_up and new_derived.piping_up:
            events.append(Event(
                event_affordances_keys=["iov_pressure"],
                type="piping_started",
                message="You hear a gurgle of liquid, as you realize that pressurized liquid kerosene begins flowing through the service line to the IOV head."
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
                event_affordances_keys=["iov_pressure"],
                type="piping_stopped",
                message=f"Fuel flow stopped: {', '.join(reasons)}."
            ))

        # Vaporizing transitions
        if not old_derived.vaporizing and new_derived.vaporizing:
            events.append(Event(
                event_affordances_keys=["lamp"],
                type="vaporizing_started",
                message="Kerosene vapor begins flowing through the flash boiler of the IOV, its vaporizing tubes hiss and transmute the liquid into vapor."
            ))
        elif old_derived.vaporizing and not new_derived.vaporizing:
            events.append(Event(
                event_affordances_keys=["lamp"],
                type="vaporizing_stopped",
                message="Vaporization has stopped."
            ))
            if old_phys.flame_lit:
                events.append(Event(
                    event_affordances_keys=["lamp"],
                    type="flame_extinguished",
                    message="The vapor flame extinguishes."
                ))

        # Bunsen transitions
        if not old_derived.bunsen_lit and new_derived.bunsen_lit:
            events.append(Event(
                event_affordances_keys=["lamp"],
                type="bunsen_ignited",
                message="The Bunsen burner ignites with small, but piping-hot blue flames."
            ))
        elif old_derived.bunsen_lit and not new_derived.bunsen_lit:
            events.append(Event(
                event_affordances_keys=["lamp"],
                type="bunsen_extinguished",
                message="The Bunsen flames extinguish."
            ))

        # Temperature transitions
        if (old_phys.tube_temp < Constants.TEMP_THRESHOLD_READY and
                new_phys.tube_temp >= Constants.TEMP_THRESHOLD_READY):
            events.append(Event(
                event_affordances_keys=["lamp"],
                type="tubes_ready",
                message="The vaporizing tubes glow dull red. They're ready."
            ))
        elif (old_phys.tube_temp >= Constants.TEMP_THRESHOLD_READY and
              new_phys.tube_temp < Constants.TEMP_THRESHOLD_READY):
            events.append(Event(
                event_affordances_keys=["lamp"],
                type="tubes_cooling",
                message="The vaporizing tubes are cooling. No longer hot enough."
            ))

        # Pressure warnings
        if old_phys.air_pressure > 0 and new_phys.air_pressure <= 0:
            events.append(Event(
                event_affordances_keys=["iov_pressure"],
                type="pressure_depleted",
                message="Air pressure has completely bled out!"
            ))
        elif Rules.is_pressure_optimal(old_phys) and not Rules.is_pressure_optimal(new_phys):
            events.append(Event(
                event_affordances_keys=["iov_pressure"],
                type="pressure_suboptimal",
                message="Air pressure has dropped below optimal range."
            ))

        if (old_phys.air_pressure > Constants.SAFETY_VALVE_THRESHOLD and
                new_phys.air_pressure < old_phys.air_pressure):
            events.append(Event(
                event_affordances_keys=["iov_pressure"],
                type="safety_valve_popped",
                message=f"The safety valve pops open as it reaches {old_phys.air_pressure} PSI with a loud hiss! Suddenly, the pressure drops in a violent manner to {new_phys.air_pressure} PSI."
            ))

        # Fuel warnings
        if (old_phys.fuel_level >= Constants.MIN_FUEL_FOR_OPERATION and
                new_phys.fuel_level < Constants.MIN_FUEL_FOR_OPERATION):
            events.append(Event(
                event_affordances_keys=["iov_pressure"],
                type="fuel_critical",
                message="Fuel is running critically low."
            ))

        if not old_derived.is_liquid_spray and new_derived.is_liquid_spray:
            msg = f"The IOV top is spraying {new_derived.spray_temp_level} liquid kerosene in a {new_derived.spray_flow_level}!"
            events.append(Event(
                event_affordances_keys=["lamp"],
                type="liquid_spray_started",
                message=msg,
                data={
                    'hazard': new_derived.hazard_multiplier,
                    'temp_level': new_derived.spray_temp_level,
                    'flow_level': new_derived.spray_flow_level,
                }
            ))
            # Mantle destroyed by liquid spray (only if above force threshold)
            check_mantle_destroyed()

        elif old_derived.is_liquid_spray and new_derived.is_liquid_spray:
            msg = f"The IOV top is spraying {new_derived.spray_temp_level} liquid kerosene in a {new_derived.spray_flow_level}!"
            events.append(Event(
                event_affordances_keys=["lamp"],
                type="liquid_spray_changed",
                message=msg,
                data={
                    'hazard': new_derived.hazard_multiplier,
                    'temp_level': new_derived.spray_temp_level,
                    'flow_level': new_derived.spray_flow_level,
                }
            ))
            check_mantle_destroyed()

        # Light transitions
        if old_derived.light_intensity < 0.5 and new_derived.light_intensity >= 0.5:
            events.append(Event(
                event_affordances_keys=["lamp"],
                type="light_ignited",
                message="The mantle flashes brilliant light! For a second, everything you see is bleached white."
            ))
        elif old_derived.light_intensity > 0 and new_derived.light_intensity == 0:
            events.append(Event(
                event_affordances_keys=["lamp"],
                type="light_extinguished",
                message="The light goes out, the room being quickly robbed of light."
            ))

        # Mantle burn-in
        if (new_ctrl.mantle_installed and
                not old_phys.mantle_burned_in and
                new_phys.mantle_burned_in):
            events.append(Event(
                event_affordances_keys=["lamp"],
                type="mantle_burned_in",
                message="The mantle catches fire and burns down to a delicate ash skeleton instantly. 'A Welsbach mantle', you heard someone once call it."
            ))

        # Air jet transitions
        if not old_derived.is_air_blowing and new_derived.is_air_blowing:
            events.append(Event(
                event_affordances_keys=["lamp"],
                type="air_blowing_started",
                message=new_derived.air_flow_level
            ))
        elif old_derived.is_air_blowing and not new_derived.is_air_blowing:
            events.append(Event(
                event_affordances_keys=["lamp"],
                type="air_blowing_stopped",
                message="The air jet subsides."
            ))

        # Mantle destroyed by air jet
        print(f"old_derived.is_air_blowing: {old_derived.is_air_blowing}")
        print(f"old_phys.mantle_burned_in: {old_phys.mantle_burned_in}")
        print(f"new_phys.mantle_burned_in: {new_phys.mantle_burned_in}")
        if (old_derived.is_air_blowing and
                old_phys.mantle_burned_in and
                not new_phys.mantle_burned_in):
            print("Mantle destroyed by air jet!")
            events.append(Event(
                event_affordances_keys=["lamp"],
                type="mantle_destroyed",
                message="The powerful air jet scatters the delicate mantle ash into nothing!"
            ))

        return events


# ============================================================================
# LAMP SIMULATION
# ============================================================================

class IOVLamp:
    """The complete lamp simulation."""

    def __init__(self):
        self.physics  = PhysicalState()
        self.controls = Controls()
        self.derived  = StateComputer.compute(self.physics, self.controls)

    def tick(self) -> List[Event]:
        """Advance simulation by one tick."""
        old_phys    = self.physics
        old_derived = self.derived

        self.physics, self.controls = PhysicsEngine.tick(
            self.physics, self.controls, self.derived
        )
        self.derived = StateComputer.compute(self.physics, self.controls)

        return EventDetector.detect_transitions(
            old_phys, old_derived,
            self.physics, self.controls, self.derived
        )

    def _update_derived(self) -> List[Event]:
        """Recompute derived state and enforce immediate physical stability."""
        old_derived = self.derived
        old_ctrl    = self.controls
        old_phys    = self.physics

        self.derived = StateComputer.compute(self.physics, self.controls)
        self.physics, self.controls = PhysicsEngine.resolve_stability(
            self.physics, self.controls, self.derived
        )

        if self.physics != old_phys or self.controls != old_ctrl:
            self.derived = StateComputer.compute(self.physics, self.controls)

        return EventDetector.detect_transitions(
            old_phys, old_derived,
            self.physics, self.controls, self.derived
        )

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
        new_pressure  = min(100.0, self.physics.air_pressure + pressure_gain)
        self.physics  = replace(self.physics, air_pressure=new_pressure)
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
        self.controls = replace(self.controls,
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
        new_position  = min(1.0, self.controls.control_valve + amount)
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
        new_position  = max(0.0, self.controls.control_valve - amount)
        self.controls = replace(self.controls, control_valve=new_position)
        events = self._update_derived()
        return f"You close the control valve to {self.controls.control_valve * 100:.0f}%.", events

    def install_mantle(self) -> Tuple[str, List[Event]]:
        if self.controls.mantle_installed:
            return "A mantle is already installed.", [], False
        self.controls = replace(self.controls, mantle_installed=True)
        self.physics  = replace(self.physics, mantle_burned_in=False)
        events = self._update_derived()
        return "You install the fabric mesh mantle. It needs to be burned in.", events, True

    def remove_mantle(self) -> Tuple[str, bool, List[Event]]:
        if not self.controls.mantle_installed:
            return "There's no mantle to remove.", False, [], False
        if self.physics.flame_lit:
            return "Can't remove the mantle while vapor is lit.", False, [], False
        was_burned    = self.physics.mantle_burned_in
        self.controls = replace(self.controls, mantle_installed=False)
        self.physics  = replace(self.physics, mantle_burned_in=False)
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
        events = self._update_derived()
        return "You ignite the vapor. Blue flames dance at the burner.", events

    def add_fuel(self, amount: float = 0.5) -> Tuple[str, List[Event], bool]:
        if self.physics.fuel_level == 1.0:
            return "The fuel tank is full.", [], False
        new_level    = min(1.0, self.physics.fuel_level + amount)
        self.physics = replace(self.physics, fuel_level=new_level)
        events = self._update_derived()
        return f"You add kerosene. Fuel level: {self.physics.fuel_level * 100:.0f}%", events, True

    def clean_jet(self, amount: float = -0.2) -> Tuple[str, List[Event], bool]:
        if self.physics.jet_soot_level == 0.0:
            return "The jet is already clean.", [], False
        # Ensure amount is always treated as a reduction
        delta     = -abs(amount)
        new_soot  = max(0.0, self.physics.jet_soot_level + delta)
        self.physics = replace(self.physics, jet_soot_level=new_soot)
        events = self._update_derived()
        cleanliness = (1.0 - self.physics.jet_soot_level) * 100
        return f"You clear soot from the jet. Jet cleanliness: {cleanliness:.0f}%", events, True

    # ========================================================================
    # STATUS REPORTING
    # ========================================================================

    def get_output_status(self) -> str:
        if not Rules.is_system_open(self.physics, self.controls):
            return "The IOV top is not flowing with anything."

        if self.derived.is_air_blowing:
            return self.derived.air_flow_level or "Air is escaping from the jet."

        if self.derived.vaporizing:
            if self.physics.flame_lit:
                if self.physics.mantle_burned_in:
                    if self.derived.light_intensity >= 0.9:
                        return "On top of the IOV lamp, a source of brilliant white light blazes, reaching every cranny of the room, leaving everything under its revealing shine."
                    elif self.derived.light_intensity >= 0.6:
                        return "On top of the IOV lamp, a warm glow emanates from the mantle, illuminating the room with steady light."
                    elif self.derived.light_intensity >= 0.3:
                        return "The mantle glows dimly, casting weak shadows. The system pressure isn't high enough for full brightness."
                    elif self.derived.light_intensity > 0:
                        return "The mantle barely glows, producing only a faint flicker. More pressure or a wider valve is needed."
                    else:
                        return "The mantle is present but not glowing. Jet pressure is too low to sustain light."
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
        t = self.physics.tube_temp
        if t >= 0.95: return "Red hot"
        elif t >= 0.7: return "Very hot"
        elif t >= 0.4: return "Warm"
        elif t > 0:    return "Cool"
        return "Cold"

    def get_preburner_description(self) -> str:
        if self.controls.spirit_pan_lit:     return "LIT"
        elif self.controls.spirit_pan_present: return "present, unlit"
        return "not placed"

    def get_mantle_description(self) -> str:
        if not self.controls.mantle_installed: return "Not installed"
        elif self.physics.mantle_burned_in:    return "Burned-in (ready)"
        return "New (needs fire)"

    def get_service_room_status(self) -> str:
        pressure_status = (
            "OPTIMAL" if Rules.is_pressure_optimal(self.physics) else
            "TOO HIGH" if self.physics.air_pressure > Constants.OPTIMAL_PRESSURE_MAX else
            "TOO LOW"
        )
        air_valve_status = (
            "OPEN (Leaking...)" if self.controls.air_valve_open and self.physics.air_pressure > 0 else
            "OPEN (Silent)"     if self.controls.air_valve_open else
            "closed"
        )
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
        lines = [
            "=== Incandescent Oil Vapor Burner ===",
            #f"  Inlet (line):   {Rules.calculate_inlet_psi(self.physics):.1f} PSI",
            f"  Upstream Gauge: {self.derived.upstream_gauge_psi:.1f} PSI",
            f"  Jet Output:     {Rules.calculate_jet_psi(self.physics, self.controls):.1f} PSI",
            f"  Jet Soot:       {self.physics.jet_soot_level * 100:.1f}%",
            f"  Tubes Temperature: {self.get_temp_description()}",
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

    def get_light_state(self) -> str:
        level = LightTables.find_level(self.derived.light_intensity, LightTables.LEVELS)
        return level.description if level else "You can't see any light coming from the IOV lamp."

    def get_status(self) -> str:
        return self.get_service_room_status() + "\n" + self.get_lamp_status()


# ============================================================================
# DEMO / TESTING
# ============================================================================

def demo():
    """Demo showing jet_psi-driven simulation."""
    lamp = IOVLamp()

    print("=== IOV LAMP - JET_PSI REFACTOR ===\n")

    def do(action_name, result):
        print(f"[ACTION] {action_name}")
        if isinstance(result, tuple):
            msg = result[0]
            events = result[-1] if isinstance(result[-1], list) else []
            print(f"  → {msg}")
            for event in events:
                print(f"  📢 {event.message}")
        print()

    do("Add fuel",        lamp.add_fuel(1.0))
    do("Open air valve",  lamp.open_air_valve())
    do("Pump to 65 PSI",  lamp.pump_air(130))
    do("Close air valve", lamp.close_air_valve())
    do("Place spirit pan", lamp.place_spirit_pan())
    do("Light spirit pan", lamp.light_spirit_pan())

    print("[SIMULATION] Heating up...")
    for _ in range(5):
        events = lamp.tick()
        for e in events:
            print(f"  📢 {e.message}")
    print()

    do("Open main valve",  lamp.open_main_valve())
    do("Install mantle",   lamp.install_mantle())

    print("=" * 60)
    print("TEST 1: Valve at 10% — jet_psi will be low, Bunsen won't light")
    print("=" * 60)
    do("Open control valve 10%", lamp.open_control_valve(0.1))
    jet = Rules.calculate_jet_psi(lamp.physics, lamp.controls)
    print(f"  jet_psi = {jet:.1f} PSI (need >= {Constants.MIN_JET_PSI_FOR_BUNSEN} for Bunsen)")
    for _ in range(3):
        events = lamp.tick()
        for e in events:
            print(f"  📢 {e.message}")
        print(f"  Pressure: {lamp.physics.air_pressure:.1f} | jet_psi: {Rules.calculate_jet_psi(lamp.physics, lamp.controls):.1f} | Light: {lamp.derived.light_intensity * 100:.1f}%")
    print()

    do("Ignite vapor", lamp.ignite_vapor())

    print("=" * 60)
    print("TEST 2: Valve at 50% — jet_psi high enough for full operation")
    print("=" * 60)
    do("Open control valve to 50%", lamp.open_control_valve(0.4))
    for _ in range(5):
        events = lamp.tick()
        for e in events:
            print(f"  📢 {e.message}")
        print(f"  Pressure: {lamp.physics.air_pressure:.1f} | jet_psi: {Rules.calculate_jet_psi(lamp.physics, lamp.controls):.1f} | Light: {lamp.derived.light_intensity * 100:.1f}%")
    print()

    print(lamp.get_status())


if __name__ == "__main__":
    demo()