import os
import json
import uuid
import pickle
from typing import Any

CACHE_DIR = ".runtime/cache"

class RuntimeCache:
    """Manages large payload storage to prevent state bloat."""
    
    @staticmethod
    def _ensure_dir():
        if not os.path.exists(CACHE_DIR):
            os.makedirs(CACHE_DIR, exist_ok=True)
            
    @staticmethod
    def save_json(data: Any, prefix: str = "obj") -> str:
        """Saves data to JSON and returns a reference ID."""
        RuntimeCache._ensure_dir()
        ref_id = f"{prefix}_{uuid.uuid4().hex[:8]}"
        path = os.path.join(CACHE_DIR, f"{ref_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return ref_id
        
    @staticmethod
    def load_json(ref_id: str) -> Any:
        """Loads JSON data from a reference ID."""
        path = os.path.join(CACHE_DIR, f"{ref_id}.json")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def save_pickle(data: Any, prefix: str = "obj") -> str:
        """Saves data to Pickle (for complex objects) and returns a reference ID."""
        RuntimeCache._ensure_dir()
        ref_id = f"{prefix}_{uuid.uuid4().hex[:8]}"
        path = os.path.join(CACHE_DIR, f"{ref_id}.pkl")
        with open(path, "wb") as f:
            pickle.dump(data, f)
        return ref_id
        
    @staticmethod
    def load_pickle(ref_id: str) -> Any:
        """Loads Pickle data from a reference ID."""
        path = os.path.join(CACHE_DIR, f"{ref_id}.pkl")
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return pickle.load(f)
