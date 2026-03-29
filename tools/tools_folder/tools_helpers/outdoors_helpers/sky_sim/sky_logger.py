import os
from datetime import datetime
from . import render_snapshot

class SkyLogger:
    def __init__(self, location_name):
        # 1. Define the folder name ONCE
        log_dir = "sky_logs"
        
        # 2. Ensure it exists
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # 3. Build the filename using that same folder variable
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        safe_name = location_name.replace(" ", "_").replace(",", "")
        self.filename = os.path.join(log_dir, f"Expedition_{safe_name}_{timestamp}.txt")
        
        # Initialize the file
        with open(self.filename, "w", encoding="utf-8") as f:
            f.write(f"=== STARGAZING EXPEDITION LOG: {location_name} ===\n")
            f.write(f"Session Started at device local time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("="*60 + "\n\n")

    def log_snapshot(self, name, snap):
        """Appends the report to the file."""
        # This now uses self.filename which is guaranteed to point to the right place
        with open(self.filename, "a", encoding="utf-8") as f:
            f.write(f"--- LOG ENTRY: {snap.local_time} ---\n")
            
            status_text = snap.condition.value.replace('_', ' ').upper()
            f.write(f"CONDITIONS: {status_text}\n")
            f.write(f"Bortle: Class {snap.bortle_class.value} | Limit: {snap.limiting_magnitude:.2f} mag\n")
            f.write(f"Stars Visible: {snap.total_stars_visible} | Above Horizon: {snap.stars_above_horizon}\n")
            
            f.write(render_snapshot(snap, compact=True))
            f.write("\n" + "-"*60 + "\n\n")