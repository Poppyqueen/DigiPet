"""
Refactored Lighthouse Manager
==============================

This manager is now a THIN SHELL that:
1. Handles JSON persistence
2. Delegates to the clean IOVLamp
3. Delegates to the clean LanternRoom
4. Collects events for the game

Architecture:
    LighthouseManager (persistence + orchestration)
        ├─> IOVLamp (clean lamp simulation)
        └─> LanternRoom (clean lantern simulation)
"""

from typing import Dict, Any, List, Tuple
from dataclasses import asdict
import json
from pathlib import Path

# Import the NEW clean systems
from tools.tools_folder.tools_helpers.lighthouse.iov_lamp_sim import (
    IOVLamp, 
    PhysicalState as LampPhysics,
    Controls as LampControls,
    Event as LampEvent
)

from tools.tools_folder.tools_helpers.lighthouse.fresnel_lens import (
    LanternRoom,
    LanternRoomPhysics,
    LanternRoomControls,
    WeatherConditions,
    LanternEvent
)

from .models import ActionInternalResponse


class LighthouseManager:
    """
    Thin persistence layer for the lighthouse.
    
    Responsibilities:
    - Load/save state to JSON
    - Delegate actions to IOVLamp
    - Collect events for game engine
    - Coordinate with LanternRoomManager
    """
    
    def __init__(self, state_manager, open_meteo_handle=None, is_toolset_available=None):
        self.state_manager = state_manager
        self.json_filename = "lighthouse_data.json"
        self.base_path = state_manager.base_path
        self.filepath = Path(self.base_path) / self.json_filename
        self.is_toolset_available = is_toolset_available # New, method to check if a string matches a toolset or affordance block currently active based on the game state.

        # Create the clean lamp
        self.lamp = IOVLamp()
        
        # Create the clean lantern room
        self.lantern = LanternRoom(weather_provider=open_meteo_handle)
        
        # Load state from JSON if it exists
        self._load_state()
    
    def _load_state(self):
        """Load state from JSON and populate lamp + lantern."""
        if not self.filepath.exists():
            # First run - use defaults
            self._save_state()
            return
        
        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)
            
            lighthouse = data.get('lighthouse', {})
            
            # === Load Lamp State ===
            lamp_data = lighthouse.get('lamp', {})
            
            if 'physics' in lamp_data:
                self.lamp.physics = LampPhysics(**lamp_data['physics'])
            
            if 'controls' in lamp_data:
                self.lamp.controls = LampControls(**lamp_data['controls'])
            
            # Recompute lamp derived state
            from tools.tools_folder.tools_helpers.lighthouse.iov_lamp_sim import StateComputer
            self.lamp.derived = StateComputer.compute(
                self.lamp.physics, 
                self.lamp.controls
            )
            
            # === Load Lantern State ===
            lantern_data = lighthouse.get('lantern', {})
            
            if 'physics' in lantern_data:
                self.lantern.physics = LanternRoomPhysics(**lantern_data['physics'])
            
            if 'controls' in lantern_data:
                self.lantern.controls = LanternRoomControls(**lantern_data['controls'])
            
            # Recompute lantern derived state
            from tools.tools_folder.tools_helpers.lighthouse.fresnel_lens import LanternStateComputer
            self.lantern.derived = LanternStateComputer.compute(
                self.lantern.physics,
                self.lantern.controls,
                self.lantern.weather
            )
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Warning: Failed to load state: {e}. Using defaults.")
            self._save_state()
    
    def _save_state(self):
        """Save state to JSON."""
        # Only save the SOURCE state (physics + controls)
        # Derived state is NEVER saved (always computed)
        data = {
            'lighthouse': {
                'lamp': {
                    'physics': asdict(self.lamp.physics),
                    'controls': asdict(self.lamp.controls),
                    # NOTE: We do NOT save derived state!
                },
                'lantern': {
                    'physics': asdict(self.lantern.physics),
                    'controls': asdict(self.lantern.controls),
                    # NOTE: We do NOT save derived state or weather!
                }
            }
        }
        
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    # ========================================================================
    # GAME LOOP
    # ========================================================================
    
    def tick(self) -> Dict[str, Any]: # TODO: Change how this works.
        # What is calling this is turning everything into a string
        # We want to filter the events 
        # so... pass the events raw as a response here
        """
        Called every game tick.
        
        Returns events that happened this tick for the game engine to process.
        """
        messages = {}
        
        # Tick the lamp simulation
        lamp_events = self.lamp.tick()
        
        # Convert lamp events to game messages
        if lamp_events:
            messages['lamp'] = self._get_current_formatted_events(lamp_events)
        
        # Tick lantern room
        lantern_events = self.lantern.tick()
        
        # Convert lantern events to game messages
        if lantern_events:
            messages['lantern'] = lantern_events
        
        # Save state after tick
        self._save_state()
        
        return messages



    def _get_current_formatted_events(self, events: List) -> str:
        formatted_events = []
        for event in events:
            if any(self.is_toolset_available(key) for key in event.event_affordances_keys):
                formatted_events.append(event.message)
        return "\n".join(formatted_events)
    
    # ========================================================================
    # PLAYER ACTIONS - Thin delegation layer
    # ========================================================================
    
    def open_air_service_valve(self) -> ActionInternalResponse:
        """Open air service valve."""
        msg, events = self.lamp.open_air_valve()
        self._save_state()
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=True)
    
    def close_air_service_valve(self) -> ActionInternalResponse:
        """Close air service valve."""
        msg, events = self.lamp.close_air_valve()
        self._save_state()
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=True)
    
    def pump_air(self, strokes: int = 10) -> ActionInternalResponse:
        """Pump air into system."""
        msg, events, success = self.lamp.pump_air(strokes)
        print(f"DEBUG: pump_air returned: {msg}")
        print(f"DEBUG: events: {events}")
        print(f"DEBUG: success: {success}")
        self._save_state()
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=success)
    
    def open_main_valve(self) -> ActionInternalResponse:
        """Open main fuel valve."""
        msg, events = self.lamp.open_main_valve()
        self._save_state()
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=True)
    
    def close_main_valve(self) -> ActionInternalResponse:
        """Close main fuel valve."""
        msg, events = self.lamp.close_main_valve()
        self._save_state()
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=True)
    
    def place_spirit_pan(self) -> ActionInternalResponse:
        """Place spirit pan."""
        msg, events, success = self.lamp.place_spirit_pan()
        self._save_state()
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=success)
    
    def light_spirit_pan(self) -> ActionInternalResponse:
        """Light spirit pan."""
        msg, events = self.lamp.light_spirit_pan()
        self._save_state()
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=True)
    
    def open_valve(self, amount: float = 0.5) -> ActionInternalResponse:
        """Open control valve."""
        msg, events = self.lamp.open_control_valve(amount)
        self._save_state()
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=True)
    
    def close_valve(self, amount: float = 0.5) -> ActionInternalResponse:
        """Close control valve."""
        msg, events = self.lamp.close_control_valve(amount)
        self._save_state()
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=True)
    
    def install_mantle(self) -> ActionInternalResponse:
        """Install mantle."""
        msg, events, success = self.lamp.install_mantle()
        self._save_state()
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=success)
    
    def ignite_vapor(self) -> ActionInternalResponse:
        """Ignite vapor."""
        msg, events = self.lamp.ignite_vapor()
        self._save_state()
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=True)
    
    def add_fuel(self, amount: float = 0.5) -> ActionInternalResponse:
        """Add fuel."""
        msg, events, success = self.lamp.add_fuel(amount)
        self._save_state()
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=success)

    
    def oil_mechanism(self, amount: float = None) -> ActionInternalResponse:
        msg, events, success = self.lantern.oil_mechanism(amount)
        self._save_state()
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=success)


    # ========================================================================
    # LANTERN ROOM DELEGATION
    # ========================================================================
    
    
    def clean_wp(self, amount: float = 0.5) -> ActionInternalResponse: # wp = window panes, window panes or weather panes, or storm panes, in the lantern room, held by astragals, not to be confused with the Fresnel lens
        """Clean the fresnel lens (exterior)."""
        msg, events = self.lantern.clean_window_panes(amount)
        self._save_state()
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=True)
    
    def clean_condensation(self, amount: float = 0.5) -> ActionInternalResponse: # also cleans the wp
        """Clean condensation from interior glass."""
        msg, events = self.lantern.clean_condensation(amount)
        self._save_state()
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=True)
    
    def windup_clockwork(self, amount: float = 0.5) -> ActionInternalResponse:
        """Wind up the clockwork mechanism."""
        msg, events = self.lantern.windup_clockwork(amount)
        self._save_state()
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=True)
    
    def place_sheet(self) -> ActionInternalResponse:
        """Place protective sheet."""
        msg, events, success = self.lantern.place_sheet()
        self._save_state()
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=success)
    
    def remove_sheet(self) -> ActionInternalResponse:
        """Remove protective sheet."""
        msg, events, success = self.lantern.remove_sheet()
        self._save_state()
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=success)
    

# DATA RETURNING METHODS
    def remove_spirit_pan(self) -> ActionInternalResponse:
        """Remove spirit pan."""
        msg, pan_state, events, success = self.lamp.remove_spirit_pan()
        self._save_state()
        data_dict = {
            "pan_state": pan_state
        }
        # Could do something with pan_state ("full" or "empty") if needed
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=success, data=data_dict)
    

    def remove_mantle(self) -> ActionInternalResponse:
        """Remove mantle."""
        msg, was_fabric, events, success = self.lamp.remove_mantle()
        self._save_state()
        data_dict = {
            "was_fabric": was_fabric
        }
        # Could track the fabric if needed
        return ActionInternalResponse(message=msg, formatted_events=self._get_current_formatted_events(events), events=events, success=success, data=data_dict)
    
    # ========================================================================
    # STATUS QUERIES
    # ========================================================================

    def get_lantern_room_status(self) -> str:
        """Get lantern room status."""
        return self.lantern.get_status()
    
    def get_status(self) -> str:
        """Get IOV lamp status."""
        return self.lamp.get_status()
    
    def get_lamp_status(self) -> str:
        """Get lamp-specific status."""
        return self.lamp.get_lamp_status()
    
    def get_service_room_status(self) -> str:
        """Get service room status."""
        return self.lamp.get_service_room_status()
    
    def get_lantern_room_status(self) -> str: # lantern room is different from the lamp
        """Get lantern room status."""
        return self.lantern.get_status()

    # ========================================================================
    # ADVANCED: Direct state access for game engine #
    # ========================================================================
    
    def get_lamp_state(self) -> Dict[str, Any]:
        """
        Get complete lamp state for game engine.
        
        Returns all state in a structured format.
        """
        return {
            'physics': {
                'air_pressure': self.lamp.physics.air_pressure,
                'tube_temp': self.lamp.physics.tube_temp,
                'fuel_level': self.lamp.physics.fuel_level,
                "flame_lit": self.lamp.physics.flame_lit,
            },
            'controls': {
                'air_valve_open': self.lamp.controls.air_valve_open,
                'main_valve_open': self.lamp.controls.main_valve_open,
                'control_valve': self.lamp.controls.control_valve,
                'spirit_pan_present': self.lamp.controls.spirit_pan_present,
                'spirit_pan_lit': self.lamp.controls.spirit_pan_lit,
                'mantle_installed': self.lamp.controls.mantle_installed,
                'mantle_burned_in': self.lamp.controls.mantle_burned_in,
                #'vapor_ignited': self.lamp.controls.vapor_ignited,
            },
            'derived': {
                'piping_up': self.lamp.derived.piping_up,
                'vaporizing': self.lamp.derived.vaporizing,
                'bunsen_lit': self.lamp.derived.bunsen_lit,
                'light_intensity': self.lamp.derived.light_intensity,
                'is_liquid_spray': self.lamp.derived.is_liquid_spray,
                'hazard_multiplier': self.lamp.derived.hazard_multiplier,
            }
        }
    
    def get_hazard_status(self) -> Dict[str, Any]:
        """Get current hazard information from lamp."""
        if self.lamp.derived.is_liquid_spray:
            return {
                'is_hazardous': True,
                'hazard_level': self.lamp.derived.hazard_multiplier,
                'temp_level': self.lamp.derived.spray_temp_level,
                'flow_level': self.lamp.derived.spray_flow_level,
                'description': self.lamp.get_output_status()
            }
        return {
            'is_hazardous': False,
            'hazard_level': 0,
            'description': 'No hazards detected.'
        }
    
    def get_all_hazards(self) -> Dict[str, Any]:
        """Get all hazards from both lamp and lantern."""
        hazards = {
            'lamp': self.get_hazard_status(),
            'lantern': self.lantern.get_hazard_status()
        }
        
        # Check if any hazard is active
        hazards['any_active'] = (
            hazards['lamp']['is_hazardous'] or 
            hazards['lantern']['is_hazardous']
        )
        
        return hazards
    
    def get_complete_status(self) -> str:
        """Get complete lighthouse status (lamp + lantern)."""
        lines = [
            "=== LIGHTHOUSE STATUS ===",
            "",
            self.get_status(),  # Lamp status
            "",
            self.get_lantern_room_status(),  # Lantern status
        ]
        
        # Add hazard warnings
        hazards = self.get_all_hazards()
        if hazards['any_active']:
            lines.extend(["", "=== ACTIVE HAZARDS ==="])
            if hazards['lamp']['is_hazardous']:
                lines.append(f"⚠️  LAMP: {hazards['lamp']['description']}")
            if hazards['lantern']['is_hazardous']:
                lines.append(f"☀️  LANTERN: {hazards['lantern']['description']}")
        
        return "\n".join(lines)

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

class MockStateManager:
    """Mock for testing."""
    def __init__(self):
        self.base_path = '/tmp/lighthouse_test'


def example_usage():
    """Show how to use the refactored manager."""
    
    # Create manager
    state_mgr = MockStateManager()
    manager = LighthouseManager(state_mgr)
    
    print("=== Lighthouse Manager Refactored Demo ===\n")
    
    # Perform startup
    print(manager.add_fuel(1.0))
    print(manager.open_air_service_valve())
    print(manager.pump_air(130))
    print(manager.close_air_service_valve())
    
    print("\n" + manager.get_status())
    
    # Simulate some ticks
    print("\n=== Simulating 5 ticks ===")
    for i in range(5):
        events = manager.tick()
        if events:
            print(f"Tick {i}: {events}")
    
    print("\n" + manager.get_lamp_status())
    
    # Check state persistence
    print("\n=== State Snapshot ===")
    state = manager.get_lamp_state()
    print(f"Pressure: {state['physics']['air_pressure']:.1f} PSI")
    print(f"Temperature: {state['physics']['tube_temp']:.2f}")
    print(f"Piping: {state['derived']['piping_up']}")
    print(f"Light: {state['derived']['light_intensity']:.0%}")
    
    # Check hazards
    hazard = manager.get_hazard_status()
    print(f"\nHazardous: {hazard['is_hazardous']}")


if __name__ == "__main__":
    example_usage()