import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

SESSION_FILE = Path.home() / ".wms_session.json"

def get_token() -> str:
    """Retrieves the active JWT token from either the WMS_TOKEN env var or local session file."""
    # Priority 1: Environment variable
    env_token = os.getenv("WMS_TOKEN")
    if env_token:
        return env_token

    # Priority 2: Persistent local session file
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("access_token", "")
        except Exception:
            pass
    return ""

def get_cached_user() -> Optional[Dict[str, Any]]:
    """Retrieves cached user metadata if logged in."""
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("user")
        except Exception:
            pass
    return None

def save_session(access_token: str, user_metadata: Optional[Dict[str, Any]] = None) -> None:
    """Saves access token and optional user metadata securely in user's home directory."""
    session_data = {
        "access_token": access_token
    }
    if user_metadata:
        session_data["user"] = user_metadata

    try:
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Write to file
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2)
        
        # Restrict permissions (read/write by owner only)
        if hasattr(os, "chmod"):
            try:
                os.chmod(SESSION_FILE, 0o600)
            except Exception:
                pass
    except Exception:
        pass

def clear_session() -> None:
    """Clears the persistent local session file."""
    if SESSION_FILE.exists():
        try:
            SESSION_FILE.unlink()
        except Exception:
            pass
