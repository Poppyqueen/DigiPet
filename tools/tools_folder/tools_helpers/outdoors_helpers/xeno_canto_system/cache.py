# cache.py
import os
import time 
import json
from utils.xeno_canto_api import _audio_cache

from .config import _SELECTION_TTL, _SELECTION_CACHE_DIR

def _purge_expired_filesystem_cache(cache_dir: str) -> int:
    import glob
    from datetime import datetime, timezone

    print(f"[CachePurge] Starting purge for dir: {cache_dir!r}")

    if not os.path.isdir(cache_dir):
        print(f"[CachePurge] Directory does not exist: {cache_dir!r} — skipping.")
        return 0

    all_files = glob.glob(os.path.join(cache_dir, "*.json"))
    print(f"[CachePurge] Found {len(all_files)} .json files")

    if not all_files:
        print("[CachePurge] No files to process.")
        return 0

    deleted = 0
    now = datetime.now(timezone.utc)

    for path in all_files:
        filename = os.path.basename(path)
        try:
            with open(path) as f:
                data = json.load(f)

            expires_raw = data.get("expires")
            if expires_raw is None:
                print(f"[CachePurge] {filename} — no expiry field, skipping.")
                continue

            expires = datetime.fromisoformat(expires_raw)
            if expires < now:
                os.remove(path)
                deleted += 1
                print(f"[CachePurge] DELETED: {filename} (expired {(now - expires).seconds}s ago)")
            else:
                print(f"[CachePurge] {filename} — still valid for {(expires - now).seconds}s")

        except json.JSONDecodeError as e:
            print(f"[CachePurge] Could not parse {filename}: {e}")
        except OSError as e:
            print(f"[CachePurge] Could not delete {filename}: {e}")
        except Exception as e:
            print(f"[CachePurge] Unexpected error for {filename}: {e} (type={type(e).__name__})")

    print(f"[CachePurge] Done. Deleted {deleted}/{len(all_files)} files.")
    return deleted



def _save_selection(selection: list[dict], time_tag: str, lat: float, lon: float) -> None:
    os.makedirs(_SELECTION_CACHE_DIR, exist_ok=True) # Ensure directory exists
    path = _get_selection_path(lat, lon)
    try:
        payload = {
            "time_tag":  time_tag,
            "saved_at":  time.time(),
            "selection": selection,
        }
        with open(path, "w") as f:
            json.dump(payload, f)
        print(f"[XenoCantoCache] Selection persisted to {path}")
    except Exception as e:
        print(f"[XenoCantoCache] Could not persist selection: {e}")




def _load_selection(current_time_tag: str, lat: float, lon: float) -> list[dict] | None:
    path = _get_selection_path(lat, lon)
    try:
        with open(path) as f:
            payload = json.load(f)
            
        age = time.time() - payload.get("saved_at", 0)
        tag = payload.get("time_tag")
        saved = payload.get("selection",[])

        if age > _SELECTION_TTL:
            print("[XenoCantoCache] Persisted selection expired.")
            return None
        if tag != current_time_tag:
            print(f"[XenoCantoCache] Time tag mismatch ({tag!r} vs {current_time_tag!r}).")
            return None

        print(f"[XenoCantoCache] Loaded persisted selection from {path}.")
        return saved

    except FileNotFoundError:
        return None
    except Exception as e:
        print(f"[XenoCantoCache] Could not load persisted selection: {e}")
        return None




def _evict_audio_for_selection(selection: list[dict]) -> None:
    if not selection:
        return

    from requests import Request

    evicted = 0
    for r in selection:
        file_url = r.get("file", "")
        if not file_url:
            continue
        if file_url.startswith("//"):
            file_url = "https:" + file_url
        try:
            req       = Request("GET", file_url).prepare()
            cache_key = _audio_cache.cache.create_key(req)
            _audio_cache.cache.delete(cache_key)
            evicted += 1
        except Exception as e:
            print(f"[XenoCantoProvider] Audio eviction error for {file_url!r}: {e}")

    print(f"[XenoCantoProvider] Evicted {evicted}/{len(selection)} audio cache entries.")



def _get_selection_path(lat: float, lon: float) -> str:
    """Generates a unique cache file for these specific coordinates."""
    # Rounding to 2 decimal places (~1.1km) groups nearby rooms into the same biome cache
    return os.path.join(
        _SELECTION_CACHE_DIR, 
        f"xeno_canto_selection_{lat:.2f}_{lon:.2f}.json"
    )