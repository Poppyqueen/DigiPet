"""
provider.py
------------------
OutdoorsProvider implementation for Xeno-canto wildlife sounds.

Plugs into the OutdoorsPerception framework exactly like EarthWeatherProvider.
outdoors_type identifier: "xeno-canto"
"""

from __future__ import annotations

import random
import threading
import time

from tools.tools_folder.tools_helpers.outdoors_helpers.base_provider import OutdoorsProvider
from utils.xeno_canto_api import XenoCantoLoc, download_audio
from utils.time_manager import get_time_tag_from_now

from utils.loc_datetime import datetime

# import traceback

# --- Import our clean sub-modules ---
from .xeno_canto_system.config import (
    _ACTIVITY_THRESHOLD_FULL,
    _ACTIVITY_THRESHOLD_LIMITED,
    _TIME_MOOD
)
from .xeno_canto_system.cache import (
    _purge_expired_filesystem_cache,
    _save_selection,
    _load_selection,
    _evict_audio_for_selection
)
from .xeno_canto_system.engine import (
    WeatherContext,
    _ticks_for_recording,
    _tokenise_type,
    _threshold_for,
    _filter_recordings,
    _weighted_sample,
    _selection_size_for,
    _build_grp_hint
)

class XenoCantoProvider(OutdoorsProvider):
    outdoors_type = "xeno-canto"
    tick_every: int = 1

    def __init__(self, xeno_canto_loc: XenoCantoLoc, open_meteo=None):
        print("[XenoCantoProvider] Initialising provider.")
        self._loc                               = xeno_canto_loc
        self._open_meteo                        = open_meteo
        self._weather_context: WeatherContext   = WeatherContext()
        self._active_selection: list[dict]      =[]
        self._selection_index: int              = 0
        self._active_time_tag: str | None       = None
        self._ticks_on_current: int             = 0
        self._activity_level: float             = 0.0
        self._active_time_tag_for_activity: str = "morning"
        self._seen_indices: set[int]            = set()
        self._selection_id: int                 = 0
        self._lock                              = threading.Lock()

        self._refreshing = False  


        _purge_expired_filesystem_cache(".cache/xeno_canto_audio")
        print(f"[XenoCantoProvider] Ready. lat={xeno_canto_loc.lat}, "
              f"lon={xeno_canto_loc.long}, "
              f"weather={'yes' if open_meteo else 'no'}")
        
    def _display_attribution_message(self, recording: dict) -> None:
        """Prints a beautifully formatted, clickable attribution block to the terminal."""
        # 1. Extraction
        en_name  = recording.get("en", "Unknown species")
        gen      = recording.get("gen", "")
        sp       = recording.get("sp", "")
        sci_name = f"{gen} {sp}".strip()
        name     = f"{en_name} ({sci_name})" if sci_name else en_name
        
        loc      = recording.get("loc", "")
        cnt      = recording.get("cnt", "")
        location = ", ".join(filter(None, [loc, cnt])) or "Unknown Location"
        
        rec      = recording.get("rec", "Unknown Recordist")
        xc_id    = recording.get("id", "Unknown ID")
        sound_type = recording.get("type", "")

        raw_time = recording.get("time", "")
        try:
            # Parse "14:10" and format to "2:10 PM"
            formatted_time = datetime.strptime(raw_time, "%H:%M").strftime("%I:%M %p").lstrip('0')
        except (ValueError, TypeError):
            formatted_time = "Unknown time"
        # 2. URL Formatting
        # We ensure the URL has https: so the terminal identifies it as a clickable link.
        raw_url  = recording.get("url", "")
        url      = f"https:{raw_url}" if raw_url.startswith("//") else raw_url
        
        # We strip the protocol only for display if we want, but for CLICKABILITY, 
        # it is safer to leave the protocol or ensure it starts with 'www.'
        clickable_url = url if url else "https://www.xeno-canto.org"

        raw_lic  = recording.get("lic", "")
        lic      = f"https:{raw_lic}" if raw_lic.startswith("//") else raw_lic



        # 3. The Print Block
        
        print("======================================================================")
        print(f"NOW PLAYING WILDLIFE (provided by xeno-canto)")
        print("----------------------------------------------------------------------")
        print(f"Citation:\n{rec}, XC{xc_id}. Accessible at {clickable_url}\n")
        print("----------------------------------------------------------------------")
        print(f"Recordist : {rec}")
        print(f"Time of day for recording : {formatted_time}")
        print(f"Species  : {name}")
        print(f"Sound type : {sound_type}")
        print(f"Location : {location}")
        print(f"License  : {lic}")
        print()
        print("Audio provided by xeno-canto, sharing wildlife sounds from")
        print("   around the world. Explore more at: https://xeno-canto.org")
        print("======================================================================")
        print()

    def _refresh_weather(self) -> None:
        if not self._open_meteo:
            return
        try:
            d = self._open_meteo.get_structured_weather()
            self._weather_context = WeatherContext(
                wind_speed=    d.get("wind_speed")    or 0.0,
                precipitation= d.get("precipitation") or 0.0,
                cloud_cover=   d.get("cloud_cover")   or 0.0,
                temperature=   d.get("temperature")   or 15.0,
                is_day=        d.get("is_day", True),
            )
            w = self._weather_context
            print(f"[XenoCantoProvider] Weather: wind={w.wind_speed:.1f}km/h "
                  f"rain={'yes' if w.is_raining else 'no'}")
        except Exception as e:
            print(f"[XenoCantoProvider] Weather refresh failed (neutral context): {e}")

    def tick(self) -> None:
        with self._lock:
            selection = self._active_selection
            if not selection:
                return

            current  = selection[self._selection_index]
            allotted = _ticks_for_recording(current)
            self._ticks_on_current += 1

            if self._ticks_on_current >= allotted:
                self._ticks_on_current = 0
                if len(selection) > 1:
                    if self._selection_id != id(selection):
                        self._seen_indices = set()
                        self._selection_id = id(selection)

                    self._seen_indices.add(self._selection_index)
                    unseen =[i for i in range(len(selection)) if i not in self._seen_indices]

                    if not unseen:
                        self._seen_indices.clear()
                        self._seen_indices.add(self._selection_index)
                        unseen =[i for i in range(len(selection)) if i != self._selection_index]

                    self._selection_index = random.choice(unseen)
                else:
                    self._selection_index = 0

            self._active_time_tag_for_activity = get_time_tag_from_now() or "morning"
            self._activity_level               = random.random()

    def _refresh_selection(self) -> None:
        self._refresh_weather()
        _purge_expired_filesystem_cache(".cache/xeno_canto_audio")

        time_tag = get_time_tag_from_now() or "morning"
        lat, lon = self._loc.lat, self._loc.long

        restored = _load_selection(time_tag, lat, lon)
        
        if restored:
            with self._lock:
                old_selection = list(self._active_selection)
            if old_selection:
                _evict_audio_for_selection(old_selection)
            with self._lock:
                self._active_selection = restored
                self._selection_index  = random.randrange(len(restored)) if restored else 0
                self._ticks_on_current = 0
                self._active_time_tag  = time_tag
                self._seen_indices     = set()
                self._selection_id     = id(restored)
            return

        with self._lock:
            old_selection = list(self._active_selection)
        if old_selection:
            _evict_audio_for_selection(old_selection)

        recordings     = self._loc.get_recordings()
        filtered       = _filter_recordings(recordings, time_tag)
        selection_size = _selection_size_for(time_tag, self._weather_context)
        selection      = _weighted_sample(filtered, time_tag, selection_size, self._weather_context)

        with self._lock:
            self._active_selection = selection
            self._selection_index  = random.randrange(len(selection)) if selection else 0
            self._ticks_on_current = 0
            self._active_time_tag  = time_tag
            self._seen_indices     = set()
            self._selection_id     = id(selection)

        _save_selection(selection, time_tag, lat, lon)

        if selection:
            self._prefetch_audio_async(selection)

    def _prefetch_audio_async(self, selection: list[dict]) -> None:
        print(f"[XenoCantoProvider] Starting background audio prefetch "
              f"for {len(selection)} recordings...")
        
        def _download_all():
            for recording in selection:
                print(f"[XenoCantoProvider] Prefetching XC{recording.get('id')}...")
                download_audio(recording)
                
                # Sleep to be polite to the Xeno-canto API and avoid rate limits!
                time.sleep(1.5) 
                
            print("[XenoCantoProvider] Background audio prefetch complete.")
            
        threading.Thread(target=_download_all, daemon=True).start()


    def _ensure_selection(self) -> None:
        current_tag = get_time_tag_from_now() or "morning"
        with self._lock:
            needs_refresh = (not self._active_selection or self._active_time_tag != current_tag)
            if needs_refresh:
                if self._refreshing:
                    return  # another thread is already refreshing, bail out
                self._refreshing = True
        if needs_refresh:
            try:
                self._refresh_selection()
            finally:
                with self._lock:
                    self._refreshing = False

    def _fetch_sound_bytes(self, recording: dict) -> tuple[bytes, int] | None:
        audio_bytes = download_audio(recording)
        smp         = int(recording.get("smp", 44100))
        if audio_bytes:
            print(f"[XenoCantoProvider] Audio ready: {len(audio_bytes)} bytes.")
            self._display_attribution_message(recording=recording)
            return audio_bytes, smp
            
        print(f"[XenoCantoProvider] Audio unavailable for XC{recording.get('id')}.")
        return None

    def get_limited_perception(self) -> tuple[str, str | None]:
        self._ensure_selection()

        with self._lock:
            selection      = list(self._active_selection)
            index          = self._selection_index
            activity_level = self._activity_level
            time_tag       = self._active_time_tag_for_activity

        if not selection:
            return "The outside world sounds quiet — no wildlife stirs near this opening.", None

        w          = self._weather_context
        r          = selection[index % len(selection)]
        raw_type   = r.get("type") or ""
        tokens     = _tokenise_type(raw_type)
        threshold  = _threshold_for(_ACTIVITY_THRESHOLD_LIMITED, time_tag, 1/6, tokens, w)

        if activity_level > threshold:
            if w.is_raining:
                return "The rain outside muffles all wildlife sound into a soft, continuous wash of white noise.", None
            return "Coming from the outdoors is the stillness of animals, insects and other living creatures.", None

        grp_hint = _build_grp_hint(selection)
        mood     = _TIME_MOOD.get(time_tag, "alive with the sounds of nature")

        if (w.wind_speed or 0) > 20:
            mood = "alive with sound, though the wind carries it in broken gusts"

        text = f"Through the opening, the outside world feels {mood}. You catch a fleeting impression of wildlife nearby"
        if grp_hint:
            text += f" — {grp_hint}"
        text += "."
        
        return text, None

    def get_full_perception(self) -> tuple[str, str | None, tuple[bytes, int] | None]:
        self._ensure_selection()

        with self._lock:
            selection      = list(self._active_selection)
            index          = self._selection_index
            activity_level = self._activity_level
            time_tag       = self._active_time_tag_for_activity

        if not selection:
            return "No wildlife sounds are detectable in this area.", None, None

        w         = self._weather_context
        r         = selection[index % len(selection)]
        tokens    = _tokenise_type(r.get("type", ""))
        threshold = _threshold_for(_ACTIVITY_THRESHOLD_FULL, time_tag, 1/4, tokens, w)

        if activity_level > threshold:
            if w.is_raining:
                return "Rain sheets across the landscape outside. The wildlife has gone quiet — only the percussion of water on leaves and stone.", None, None
            return "You wait and expect to catch the sounds of wild beasts around, but they seem to be quiet right now.", None, None

        en_name    = r.get("en") or ""
        gen        = r.get("gen", "").strip()
        sp         = r.get("sp", "").strip()
        sci_name   = f"{gen} {sp}".strip() if (gen or sp) else ""
        name       = en_name or sci_name or "Unknown species"
        sound_type = r.get("type", "").strip() or "call"
        grp        = (r.get("grp") or "").strip()
        rec        = r.get("rec", "").strip()
        length     = r.get("length", "")
        seen       = r.get("animal-seen", "")
        also       = r.get("also",[])
        group_note = f" [{grp}]" if grp and grp != "birds" else ""

        freq_note   = ""
        ann_set     = r.get("annotation-set")
        annotations = ann_set.get("annotations", []) if isinstance(ann_set, dict) else[]
        if annotations:
            f_low  = annotations[0].get("frequency_low")
            f_high = annotations[0].get("frequency_high")
            if f_low is not None and f_high is not None:
                freq_note = f", freq {f_low}–{f_high} Hz"

        parts = [f"Nearby you can hear a {name}{group_note}"]
        if sci_name and en_name:
            parts[0] += f" ({sci_name})"
        parts.append(f"{sound_type}")
        if length:
            parts.append(f"length {length}")
        if seen.lower() in ("yes", "no"):
            parts.append(f"animal {'seen' if seen.lower() == 'yes' else 'not seen'}")
            
        text = f"{parts[0]} — {', '.join(parts[1:])}{freq_note}."

        if also:
            text += f" Also audible in the background: {', '.join(also[:5])}."

        if w.wind_speed > 20:
            text += " The wind makes it hard to hear clearly."

        popup = f"Listening to '{name}' recorded by '{rec}'" if rec else f"Listening to '{name}'"
        audio = self._fetch_sound_bytes(r)
        

        return text, popup, audio